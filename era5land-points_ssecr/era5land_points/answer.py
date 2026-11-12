"""Reading and checking CDS's answer to a request: a location's hourly series.

The answer is a zip of CSV files, one per group of variables (2 m temperature, soil temperature,
and so on). Each file has the columns valid_time, in UTC, written as 1991-01-01 00:00:00;
latitude and longitude, the grid point's; and one column per variable, by its short name. The
dataset uses the grid point nearest the location asked for, on its 0.1° grid, and skips any date
with fewer than 24 hourly values.

The answer gives no units, so each variable's values are checked against the range expected in
its documented unit before they are converted.
"""

import io
import math
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from era5land_points.config import Location
from era5land_points.variables import VARIABLES

_TIME, _LATITUDE, _LONGITUDE = "valid_time", "latitude", "longitude"
# The grid's spacing: the nearest grid point is at most half of it away in each direction.
_HALF_STEP = 0.05 + 1e-6
_EARTH_KM = 6371.0


class AnswerError(ValueError):
    pass


class NoValues(AnswerError):
    pass


class Unreadable(AnswerError):
    """A file that isn't a zip of CSV files, as a download cut off part way."""


@dataclass(frozen=True)
class Series:
    # Every hour from the first with values to the last, in UTC; a column per variable, by the
    # config's name, in its written unit; NaN where the answer has no value.
    hours: pd.DataFrame
    # The grid point CDS used.
    latitude: float
    longitude: float

    def distance_km(self, location: Location) -> float:
        """How far the grid point is from the location."""
        phi1, phi2 = math.radians(location.latitude), math.radians(self.latitude)
        dphi = phi2 - phi1
        dlambda = math.radians(_lon_difference(self.longitude, location.longitude))
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * _EARTH_KM * math.asin(math.sqrt(a))


def read(path: Path, location: Location, variables: list[str]) -> Series:
    """The series in a saved answer, checked. Raises AnswerError, or NoValues for a grid point
    with no values, as one over the sea."""
    wanted = {VARIABLES[name].column: name for name in variables}
    frames, nodes = [], set()
    try:
        for member, data in _files(path):
            frame, node = _checked(pd.read_csv(io.BytesIO(data)), member, wanted)
            frames.append(frame)
            nodes.add(node)
    except (
        zipfile.BadZipFile, pd.errors.ParserError, pd.errors.EmptyDataError, UnicodeDecodeError,
        OSError,
    ) as error:  # fmt: skip
        raise Unreadable(f"{path.name} can't be read ({type(error).__name__})") from None
    if len(nodes) != 1:
        raise AnswerError(f"{path.name}'s files give {len(nodes)} grid points, not one")
    (latitude, longitude), = nodes
    if (
        abs(latitude - location.latitude) > _HALF_STEP
        or abs(_lon_difference(longitude, location.longitude)) > _HALF_STEP
    ):
        raise AnswerError(f"{path.name}'s grid point isn't the one nearest the location")

    hours = pd.concat(frames, axis=1, join="outer").sort_index()
    found = list(hours.columns)
    if sorted(found) != sorted(wanted):
        missing = sorted(set(wanted) - set(found))
        raise AnswerError(f"{path.name} lacks {', '.join(missing) or 'nothing'}, or repeats one")
    if hours.isna().all().all():
        raise NoValues(
            f"the nearest grid point ({latitude:.2f}, {longitude:.2f}) has no values, as one over "
            "the sea or a large lake does; move the location onto land"
        )

    converted = {}
    for short, name in wanted.items():
        variable = VARIABLES[name]
        values = hours[short]
        if not pd.api.types.is_numeric_dtype(values):
            raise AnswerError(f"{name}'s values in {path.name} aren't all numbers")
        present = values.dropna()
        outside = int(((present < variable.low) | (present > variable.high)).sum())
        if outside:
            raise AnswerError(
                f"{outside} of {name}'s values are outside {variable.low} to {variable.high}, so "
                f"they aren't in the unit expected"
            )
        written = values.astype("float64") * variable.scale + variable.offset
        converted[name] = written.clip(lower=0) if variable.never_negative else written
    table = pd.DataFrame(converted)[variables]

    # Every hour from the first with a value to the last, so that missing hours are rows of NaN.
    have = table.notna().any(axis=1)
    first, last = have.idxmax(), have[::-1].idxmax()
    table = table.reindex(pd.date_range(first, last, freq="h", name="time"))
    return Series(table, latitude, longitude)


def _files(path: Path):
    """Each CSV file in an answer, by name, as bytes: several zipped, or one alone."""
    data = path.read_bytes()
    if not data.startswith(b"PK\x03\x04"):
        yield path.name, data
        return
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = [m for m in archive.infolist() if not m.is_dir()]
        if not members or not all(m.filename.endswith(".csv") for m in members):
            raise Unreadable(f"{path.name} should hold CSV files only, and at least one")
        for member in members:
            yield member.filename, archive.read(member)


def _checked(frame: pd.DataFrame, member: str, wanted: dict) -> tuple[pd.DataFrame, tuple]:
    """One file's values, indexed by UTC time, and its grid point."""
    values = [c for c in frame.columns if c not in (_TIME, _LATITUDE, _LONGITUDE)]
    if (
        not {_TIME, _LATITUDE, _LONGITUDE} <= set(frame.columns)
        or not values
        or not set(values) <= set(wanted)
    ):
        raise AnswerError(
            f"{member}'s columns should be {_TIME}, {_LATITUDE}, {_LONGITUDE} and some of "
            f"{', '.join(wanted)}"
        )
    try:
        times = pd.DatetimeIndex(
            pd.to_datetime(frame[_TIME], format="%Y-%m-%d %H:%M:%S", utc=True), name="time"
        )
    except (ValueError, TypeError):
        raise AnswerError(f"{member}'s times aren't written as YYYY-MM-DD HH:MM:SS") from None
    if (
        not len(times)
        or not times.is_monotonic_increasing
        or times.has_duplicates
        or (times != times.floor("h")).any()
    ):
        raise AnswerError(f"{member}'s times should be whole hours, each once, in order")
    if frame[_LATITUDE].nunique() != 1 or frame[_LONGITUDE].nunique() != 1:
        raise AnswerError(f"{member} should give one grid point")
    # Rounded: the files write the grid point with float noise, as 40.00000000000114.
    node = (round(float(frame[_LATITUDE].iloc[0]), 6), round(float(frame[_LONGITUDE].iloc[0]), 6))
    return frame[values].set_axis(times), node


def _lon_difference(a: float, b: float) -> float:
    """a - b in degrees of longitude, across the 180° meridian the short way."""
    return (a - b + 180.0) % 360.0 - 180.0
