"""Synthetic CDS answers, laid out as live ones are: a zip of a CSV file per group of variables,
each with valid_time, the variables' short names, and the grid point's latitude and longitude."""

import io
import zipfile
from datetime import date

import numpy as np
import pandas as pd

from era5land_points.variables import VARIABLES


def hours(first: date, last: date) -> pd.DatetimeIndex:
    """Every hour of the dates, 00:00 on the first to 23:00 on the last, as answers have."""
    return pd.date_range(pd.Timestamp(first), pd.Timestamp(last) + pd.Timedelta(hours=23), freq="h")


def build(
    times: pd.DatetimeIndex,
    values: dict[str, np.ndarray],
    latitude: float,
    longitude: float,
) -> bytes:
    """An answer holding the values, by short name, on the times; NaN is written empty. Each
    variable goes in its group's file."""
    groups: dict[str, list[str]] = {}
    for short in values:
        group = next(v.group for v in VARIABLES.values() if v.column == short)
        groups.setdefault(group, []).append(short)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for n, (group, shorts) in enumerate(groups.items()):
            frame = pd.DataFrame({"valid_time": times.strftime("%Y-%m-%d %H:%M:%S")})
            for short in shorts:
                frame[short] = values[short]
            # The live answers' grid points carry float noise, as 40.00000000000114.
            frame["latitude"] = latitude + 1.1e-12
            frame["longitude"] = longitude - 1.0e-11
            archive.writestr(f"reanalysis-era5-land-timeseries-sfc-{n}.csv",
                             frame.to_csv(index=False))  # fmt: skip
    return buffer.getvalue()


def typical(times: pd.DatetimeIndex) -> dict[str, np.ndarray]:
    """Plausible values of the default variables, in the dataset's units: kelvin and metres."""
    hour = times.hour.to_numpy()
    air = 283.15 + 5 * np.sin((hour - 9) / 24 * 2 * np.pi)
    values = {"t2m": air, "tp": np.where(hour % 6 == 0, 0.0005, 0.0)}
    for n in range(1, 5):
        values[f"stl{n}"] = air - n
    return values
