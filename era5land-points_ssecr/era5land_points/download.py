"""Requests to the Copernicus Climate Data Store (CDS), one per location, through cdsapi.

Each answer is saved under downloads/ in the output folder (path_for), so a later run with the
same location, variables and dates reuses it instead of downloading again.

CDS queues each request as a job; a job can wait minutes to hours. Several are sent at once
(parallel_requests in the config), each waiting in its own thread.
"""

import hashlib
import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from era5land_points.config import Config, Location
from era5land_points.variables import VARIABLES

DATASET = "reanalysis-era5-land-timeseries"
# The dataset's first date, as its download form offers it.
FIRST_DATE = date(1950, 1, 2)


def request(location: Location, variables: list[str], first: date, last: date) -> dict:
    """The CDS request for a location's hourly series of the variables, first to last."""
    return {
        "variable": [VARIABLES[name].request for name in variables],
        "location": {"latitude": location.latitude, "longitude": location.longitude},
        "date": [f"{first.isoformat()}/{last.isoformat()}"],
        "data_format": "csv",
    }


def path_for(folder: Path, location: Location, config: Config) -> Path:
    """Where a location's answer is saved: named by what sets it, the point, the variables and
    the config's dates. Not by the request's dates, so that a run with no end date reuses what
    an earlier one downloaded; deleting downloads/ fetches the latest data again."""
    key = [location.latitude, location.longitude, config.variables, str(config.start),
           str(config.end)]  # fmt: skip
    digest = hashlib.sha256(json.dumps(key).encode()).hexdigest()[:12]
    return folder / "downloads" / f"{location.slug}-{digest}.zip"


def fetch_all(
    jobs: dict[str, tuple[dict, Path]],
    make_client: Callable,
    parallel: int,
    say: Callable[[str], None] = print,
) -> dict[str, Path | Exception]:
    """Each job's answer, by name: its saved file, or the error that stopped it. jobs maps a
    location's name to its request and the file its answer is saved as."""
    results: dict[str, Path | Exception] = {}
    todo = {name: job for name, job in jobs.items() if not job[1].exists()}
    for name in jobs.keys() - todo.keys():
        results[name] = jobs[name][1]
    if len(results):
        say(f"{len(results)} of {len(jobs)} locations already downloaded")
    if not todo:
        return results
    say(f"Sending {len(todo)} requests to CDS, {parallel} at a time; each can wait in CDS's "
        "queue for minutes to hours")  # fmt: skip
    with ThreadPoolExecutor(max_workers=parallel) as pool:
        futures = {
            pool.submit(_fetch, make_client, inputs, target): name
            for name, (inputs, target) in todo.items()
        }
        for done, future in enumerate(as_completed(futures), start=1):
            name = futures[future]
            try:
                results[name], seconds = future.result()
                size = results[name].stat().st_size / 1e6
                say(f"  [{done}/{len(todo)}] {name}: {size:.1f} MB in {seconds / 60:.1f} min")
            except Exception as error:  # one location's failure doesn't stop the others
                results[name] = error
                say(f"  [{done}/{len(todo)}] {name}: failed: {error}")
    return results


def _fetch(make_client: Callable, inputs: dict, target: Path) -> tuple[Path, float]:
    started = time.monotonic()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(".part")
    make_client().retrieve(DATASET, inputs, str(partial))
    partial.replace(target)
    return target, time.monotonic() - started
