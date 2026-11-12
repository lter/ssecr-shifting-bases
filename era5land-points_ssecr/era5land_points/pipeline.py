"""A run: download each location's hours, summarise them, and write the outputs."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from era5land_points import answer, download, outputs, process, viewer
from era5land_points.config import Config

DAY = timedelta(days=1)


class SetupError(RuntimeError):
    pass


def default_client():
    """A CDS client set up from ~/.cdsapirc, as the README shows."""
    import cdsapi

    return cdsapi.Client(quiet=True, progress=False)


def run(config: Config, make_client: Callable | None = None, say=print) -> int:
    """Run the config; the number of locations that failed. Raises SetupError if a download is
    needed and no CDS client can be made, as without ~/.cdsapirc."""
    make_client = make_client or default_client
    folder = config.output_folder
    # A day in local time can start or end in the UTC day before or after, so a day either side.
    today = datetime.now(timezone.utc).date()
    first = max(download.FIRST_DATE, (config.start or download.FIRST_DATE) - DAY)
    last = min(today, (config.end or today) + DAY)

    jobs = {
        location.name: (
            download.request(location, config.variables, first, last),
            download.path_for(folder, location, config),
        )
        for location in config.locations
    }
    if any(not path.exists() for _, path in jobs.values()):
        try:
            make_client()
        except Exception as error:
            raise SetupError(f"{error} (see the README's 'Set up' steps)") from None
    folder.mkdir(parents=True, exist_ok=True)
    answers = download.fetch_all(jobs, make_client, config.parallel_requests, say)

    say("Processing")
    outputs.clear(folder)
    # The CSV files the config asks for; the viewer takes all four aggregations.
    longer = [a for a in config.aggregations if a in ("daily", "monthly", "yearly")]
    tables: dict[str, dict[str, pd.DataFrame]] = {a: {} for a in longer}
    page = viewer.Page(config)
    rows, failed = [], 0
    for location in config.locations:
        row = {"name": location.name, "latitude": location.latitude,
               "longitude": location.longitude}  # fmt: skip
        frames = {}
        try:
            found = answers[location.name]
            if isinstance(found, Exception):
                raise found
            series = _read(found, location, config.variables)
            zone, offset = (
                process.time_zone(location) if config.time_zone == "local" else ("UTC", 0)
            )
            # The hours of the days from start to end, whole.
            day = process.day_of(series.hours.index, offset)
            keep = (day >= pd.Timestamp(config.start or download.FIRST_DATE)) & (
                day <= pd.Timestamp(config.end or today)
            )
            hours = series.hours[keep]
            days = process.daily(hours, offset)
            if not len(days):
                raise ValueError("no whole day from start to end has values")
            frames = {
                "hourly": hours,
                "daily": days,
                "monthly": process.longer(days, config.variables, "monthly"),
                "yearly": process.longer(days, config.variables, "yearly"),
            }
            row |= {
                "grid_latitude": series.latitude,
                "grid_longitude": series.longitude,
                "distance_km": round(series.distance_km(location), 2),
                "time_zone": zone,
                "utc_offset_hours": offset,
                "first_day": days.index[0].strftime("%Y-%m-%d"),
                "last_day": days.index[-1].strftime("%Y-%m-%d"),
                "downloaded": _modified(found),
                "status": "ok",
            }
        except Exception as error:  # report it, and go on with the other locations
            failed += 1
            row["status"] = f"failed: {error}"
            frames = {}  # none of a failed location's tables is written
            say(f"  {location.name}: {row['status']}")
        if frames:
            if "hourly" in config.aggregations:
                outputs.hourly(folder, location.name, location.slug, frames["hourly"], offset)
            for aggregation in longer:
                tables[aggregation][location.name] = frames[aggregation]
        rows.append(row)
        page.add(row, location.slug, frames)

    for aggregation, parts in tables.items():
        outputs.table(folder, aggregation, parts)
    pd.DataFrame(rows).to_csv(folder / "locations.csv", index=False)
    about = outputs.about(folder, config)
    target = page.write(about)
    say(f"Done: {len(rows) - failed} of {len(rows)} locations; outputs in {folder}")
    say(f"Open {target} in a browser to see them")
    return failed


def _read(path: Path, location, variables) -> answer.Series:
    """The saved answer's series. One that can't be read, as a download cut off, is deleted, so
    the next run downloads it again; any other is kept, since downloading it again would give
    the same."""
    try:
        return answer.read(path, location, variables)
    except answer.Unreadable as error:
        path.unlink(missing_ok=True)
        raise answer.Unreadable(f"{error}; deleted it, so the next run downloads it again")


def _modified(path: Path) -> str:
    """The UTC date a saved answer was downloaded."""
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).strftime("%Y-%m-%d")
