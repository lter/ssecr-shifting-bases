"""The files a run writes to the output folder.

- daily.csv, monthly.csv, yearly.csv: every location's values, a row per location and period.
- hourly/<location>.csv: each location's hours, a file per location, since they are large.
- locations.csv: each location, the grid point used, its distance, time zone, first and last
  day, the date its answer was downloaded, and its status.
- about.json: what the columns hold, how they were made, and the data's licence and citation.
- viewer.html and viewer-data/: the map and charts (viewer.py).
- downloads/: CDS's answers, reused by later runs (download.py).
"""

import json
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd

from era5land_points import download
from era5land_points.config import Config
from era5land_points.variables import VARIABLES, column, statistics

# Six significant digits: ERA5-Land's values are single-precision, about seven.
FLOAT_FORMAT = "%.6g"
DOI = "https://doi.org/10.24381/ee82e357"
CITATION = (
    "Muñoz-Sabater, J., et al. (2021): ERA5-Land: a state-of-the-art global reanalysis dataset "
    "for land applications. Earth System Science Data, 13, 4349–4383, "
    "https://doi.org/10.5194/essd-13-4349-2021"
)
# ECMWF's wording for data that were modified, which the CC BY 4.0 licence asks to be given
# with them ("How to acknowledge and cite a Climate Data Store (CDS) catalogue entry").
NOTICE = (
    "Contains modified Copernicus Climate Change Service information {year}. Neither the "
    "European Commission nor ECMWF is responsible for any use that may be made of the "
    "Copernicus information or data it contains."
)
_STATISTICS = {
    "": "the hour's value: an instant's for temperatures, pressure, wind, snow and soil water; "
    "the hour's total for amounts; the hour's mean for radiation",
    "mean": "the mean",
    "min": "the day's lowest hourly value",
    "max": "the day's highest hourly value",
    "mean_daily_min": "the mean of the days' lowest hourly values",
    "mean_daily_max": "the mean of the days' highest hourly values",
    "total": "the total",
}


def clear(folder: Path) -> None:
    """Delete the CSV files and viewer data an earlier run wrote, so none is left beside this
    run's."""
    for aggregation in ("daily", "monthly", "yearly"):
        (folder / f"{aggregation}.csv").unlink(missing_ok=True)
    for path in [*(folder / "hourly").glob("*.csv"), *(folder / "viewer-data").glob("*.js")]:
        path.unlink()


def hourly(folder: Path, name: str, slug: str, hours: pd.DataFrame, offset_hours: int) -> None:
    """A location's hours, in the time zone its days use."""
    local = hours.index.tz_localize(None) + pd.Timedelta(hours=offset_hours)
    sign = "+" if offset_hours >= 0 else "-"
    stamps = local.strftime("%Y-%m-%dT%H:%M") + f"{sign}{abs(offset_hours):02d}:00"
    table = hours.set_axis([column(VARIABLES[c], "") for c in hours.columns], axis=1)
    table.insert(0, "time", stamps)
    table.insert(0, "location", name)
    (folder / "hourly").mkdir(parents=True, exist_ok=True)
    table.to_csv(folder / "hourly" / f"{slug}.csv", index=False, float_format=FLOAT_FORMAT)


def table(folder: Path, aggregation: str, parts: dict[str, pd.DataFrame]) -> None:
    """One aggregation's values at every location, as one CSV."""
    frames = [frame.assign(location=name) for name, frame in parts.items() if len(frame)]
    if not frames:
        return
    combined = pd.concat(frames).reset_index()
    if aggregation == "daily":
        combined["date"] = combined["date"].dt.strftime("%Y-%m-%d")
    keys = ["location", *[c for c in ("date", "year", "month") if c in combined.columns]]
    combined = combined[keys + [c for c in combined.columns if c not in keys]]
    combined.to_csv(folder / f"{aggregation}.csv", index=False, float_format=FLOAT_FORMAT)


def about(folder: Path, config: Config) -> dict:
    """What the outputs hold, written as about.json, and returned for the viewer."""
    now = datetime.now(timezone.utc)
    columns = {}
    for aggregation in config.aggregations:
        for name in config.variables:
            variable = VARIABLES[name]
            for statistic in statistics(variable, aggregation):
                columns.setdefault(column(variable, statistic), {
                    "variable": name,
                    "description": variable.description,
                    "unit": variable.unit,
                    "statistic": _STATISTICS[statistic],
                    "dataset_variable": variable.request,
                })  # fmt: skip
    days = (
        "each location's local standard time, without daylight saving time"
        if config.time_zone == "local"
        else "UTC"
    )
    made = {
        "made": now.isoformat(timespec="seconds"),
        "made_by": f"era5land-points {_version('era5land-points')}, cdsapi {_version('cdsapi')}",
        "dataset": f"ERA5-Land hourly time-series data from 1950 to present ({download.DATASET})",
        "dataset_doi": DOI,
        "citation": CITATION,
        "licence": "CC BY 4.0, https://creativecommons.org/licenses/by/4.0/",
        "attribution": NOTICE.format(year=now.year),
        "dates": f"{config.start or 'the start of the record'} to "
        f"{config.end or 'the end of the record when downloaded (locations.csv)'}",
        "time": (
            "Each hour is stamped with its end: an amount or radiation is the hour's total or "
            "mean, and any other variable its value at that moment. A day is the 24 hours "
            f"ending 01:00 to 24:00, in {days}. A day has a value only if all its hours do, and "
            "a month or year only if all its days do."
        ),
        "grid_point": "the dataset's grid point nearest each location, on its 0.1° grid",
        "preliminary_data": (
            "ERA5-Land's last two to three months are preliminary and may be revised by ECMWF"
        ),
        "columns": columns,
    }
    (folder / "about.json").write_text(json.dumps(made, indent=2, ensure_ascii=False) + "\n")
    return made


def _version(package: str) -> str:
    try:
        return version(package)
    except PackageNotFoundError:
        return "(not installed)"
