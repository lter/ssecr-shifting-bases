"""Reading and checking the config file. config.example.yaml shows every setting."""

import csv
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from era5land_points.variables import DEFAULT, VARIABLES

AGGREGATIONS = ("hourly", "daily", "monthly", "yearly")
TIME_ZONES = ("local", "utc")
_KNOWN = {
    "output_folder", "locations", "locations_file", "location_columns", "variables",
    "start", "end", "aggregations", "time_zone", "parallel_requests",
}  # fmt: skip


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float

    @property
    def slug(self) -> str:
        """The name as it can appear in a file name."""
        return re.sub(r"[^A-Za-z0-9_-]+", "-", self.name).strip("-") or "location"


@dataclass(frozen=True)
class Config:
    output_folder: Path
    locations: list[Location]
    variables: list[str]
    # None for the start or end of the record.
    start: date | None
    end: date | None
    aggregations: list[str]
    time_zone: str
    parallel_requests: int


def load(path: str | Path) -> Config:
    path = Path(path)
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as error:
        raise ConfigError(f"can't read {path}: {error}") from None
    if not isinstance(raw, dict):
        raise ConfigError(f"{path} should hold settings such as 'locations:' and 'variables:'")
    unknown = sorted(set(raw) - _KNOWN)
    if unknown:
        raise ConfigError(f"unknown settings: {', '.join(unknown)}")

    folder = raw.get("output_folder", "results")
    if not isinstance(folder, str) or not folder:
        raise ConfigError("output_folder should be a folder's path")
    variables = raw.get("variables", DEFAULT)
    aggregations = raw.get("aggregations", ["daily", "monthly", "yearly"])
    time_zone = raw.get("time_zone", "local")
    parallel = raw.get("parallel_requests", 4)
    start, end = _date(raw, "start"), _date(raw, "end")

    _names(variables, VARIABLES, "variables")
    _names(aggregations, AGGREGATIONS, "aggregations")
    if time_zone not in TIME_ZONES:
        raise ConfigError("time_zone should be local or utc")
    if not isinstance(parallel, int) or isinstance(parallel, bool) or not 1 <= parallel <= 16:
        raise ConfigError("parallel_requests should be a whole number from 1 to 16")
    if start and end and start > end:
        raise ConfigError("start should be on or before end")

    has_list = "locations" in raw
    has_file = "locations_file" in raw
    if has_list == has_file:
        raise ConfigError("provide exactly one of 'locations' or 'locations_file'")
    if has_file:
        csv_name = raw["locations_file"]
        if not isinstance(csv_name, str) or not csv_name.strip():
            raise ConfigError("locations_file should be a CSV file path")
        columns = raw.get("location_columns", {
            "name": "name", "latitude": "latitude", "longitude": "longitude"
        })
        locations = _locations_from_csv(path.parent / csv_name, columns)
    else:
        if "location_columns" in raw:
            raise ConfigError("location_columns can only be used with locations_file")
        locations = _locations(raw.get("locations"))

    return Config(
        output_folder=(path.parent / folder).resolve(),
        locations=locations,
        variables=list(dict.fromkeys(variables)),
        start=start,
        end=end,
        aggregations=[a for a in AGGREGATIONS if a in aggregations],
        time_zone=time_zone,
        parallel_requests=parallel,
    )


def _names(given, allowed, setting: str) -> None:
    if not isinstance(given, list) or not given or not all(isinstance(n, str) for n in given):
        raise ConfigError(f"{setting} should be a list of names")
    unknown = [name for name in given if name not in allowed]
    if unknown:
        raise ConfigError(
            f"unknown {setting}: {', '.join(unknown)}; choose from {', '.join(allowed)}"
        )


def _date(raw: dict, key: str) -> date | None:
    value = raw.get(key)
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = date.fromisoformat(value)
        except ValueError:
            pass
    if type(value) is not date:
        raise ConfigError(f"{key} should be a date written as YYYY-MM-DD")
    return value


def _locations(raw) -> list[Location]:
    if not isinstance(raw, list) or not raw:
        raise ConfigError("locations should be a list, each with a name, latitude and longitude")
    found = []
    for number, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or set(item) != {"name", "latitude", "longitude"}:
            raise ConfigError(f"location {number} should have a name, latitude and longitude")
        name, lat, lon = str(item["name"]).strip(), item["latitude"], item["longitude"]
        for value, low, high, what in ((lat, -90, 90, "latitude"), (lon, -180, 180, "longitude")):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ConfigError(f"location {number}'s {what} should be a number")
            if not low <= value <= high:
                raise ConfigError(f"location {number}'s {what} should be from {low} to {high}")
        if not name:
            raise ConfigError(f"location {number} needs a name")
        found.append(Location(name, float(lat), float(lon)))
    # Names become file names, which Mac and Windows disks compare without case.
    slugs = [location.slug.lower() for location in found]
    if len(set(slugs)) != len(slugs):
        raise ConfigError(
            "each location needs a different name, apart from punctuation and capitals"
        )
    return found


def _locations_from_csv(path: Path, columns) -> list[Location]:
    """Read named locations from a CSV file next to the config (or at its given path)."""
    if not isinstance(path, Path):
        path = Path(path)
    if not isinstance(columns, dict) or set(columns) != {"name", "latitude", "longitude"}:
        raise ConfigError("location_columns should map name, latitude and longitude to CSV headers")
    if not all(isinstance(value, str) and value.strip() for value in columns.values()):
        raise ConfigError("location_columns values should be non-empty CSV column names")
    if len(set(columns.values())) != 3:
        raise ConfigError("location_columns must refer to three different CSV columns")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ConfigError(f"{path} is empty or has no CSV header")
            missing = [header for header in columns.values() if header not in reader.fieldnames]
            if missing:
                raise ConfigError(f"{path} is missing CSV column(s): {', '.join(missing)}")
            rows = []
            for number, row in enumerate(reader, start=2):
                if not any((value or "").strip() for value in row.values() if isinstance(value, str)):
                    continue
                try:
                    rows.append({
                        "name": row[columns["name"]].strip(),
                        "latitude": float(row[columns["latitude"]]),
                        "longitude": float(row[columns["longitude"]]),
                    })
                except (TypeError, ValueError, AttributeError):
                    raise ConfigError(
                        f"{path}, row {number}: site name, latitude and longitude must be present; "
                        "coordinates must be numbers"
                    ) from None
    except OSError as error:
        raise ConfigError(f"can't read locations CSV {path}: {error}") from None
    return _locations(rows)
