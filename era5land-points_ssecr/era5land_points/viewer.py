"""viewer.html: a map of the locations and, beside it, charts of the chosen location's hourly,
daily, monthly and yearly series, all four whichever the config asks the CSV files for.

The page opens in a browser from the output folder, with no server. It loads Leaflet, the map's
library, from cdnjs, and the map's background from Esri, so the map needs the internet; the
charts don't.

Each chart draws one statistic of each of its variables: a temperature's or other variable's
mean, an amount's total. The page holds each aggregation but hourly inside itself, coarsest
first, while it stays within about 15 MB. The rest, hourly always, go in viewer-data/, a file per
location and aggregation, which the page loads as a script when it needs one: a page opened from
a file can load scripts beside it, though not read other files. So the page needs its viewer-data
folder beside it.

A series is packed small: rounded to four significant digits of its largest value, as whole
numbers of its last digit's unit, each written as its step from the value before.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from era5land_points.config import Config
from era5land_points.variables import VARIABLES, column, statistics

BUDGET = 15_000_000
# Coarsest first: the order aggregations are taken into the page while it fits.
ORDER = ("yearly", "monthly", "daily", "hourly")
TEMPLATE = Path(__file__).with_name("viewer.html")
DATA_FOLDER = "viewer-data"
_ROW_KEYS = ("name", "latitude", "longitude", "grid_latitude", "grid_longitude", "distance_km",
             "time_zone", "utc_offset_hours", "first_day", "last_day", "status")  # fmt: skip


class Page:
    def __init__(self, config: Config):
        self.config = config
        # By location, each aggregation's packed series as JSON text but hourly's, which is
        # written to its file at once.
        self.series: list[dict[str, str]] = []
        self.rows: list[dict] = []

    def add(self, row: dict, slug: str, frames: dict[str, pd.DataFrame]) -> None:
        """A location's row of locations.csv, the name its files take, and its tables by
        aggregation (none if it failed)."""
        self.rows.append({key: row.get(key) for key in _ROW_KEYS} | {"slug": slug})
        texts = {}
        for aggregation, frame in frames.items():
            if not len(frame):
                continue
            text = json.dumps(_series(frame, aggregation, row, self.config.variables))
            if aggregation == "hourly":
                self._write_data(slug, aggregation, text)
            else:
                texts[aggregation] = text
        self.series.append(texts)

    def write(self, about: dict) -> Path:
        """The page, with what fits inside it, and the rest written to viewer-data/."""
        sizes = {a: sum(len(s.get(a, "")) for s in self.series) for a in ORDER[:-1]}
        inside, total = [], 0
        for aggregation in ORDER[:-1]:
            if total + sizes[aggregation] > BUDGET:
                break
            inside.append(aggregation)
            total += sizes[aggregation]
        locations = []
        for row, texts in zip(self.rows, self.series, strict=True):
            for aggregation, text in texts.items():
                if aggregation not in inside:
                    self._write_data(row["slug"], aggregation, text)
            data = ", ".join(f'"{a}": {texts[a]}' for a in inside if a in texts)
            locations.append(f"{json.dumps(row, allow_nan=False)[:-1]}, \"data\": {{{data}}}}}")
        head = {
            "made": about["made"],
            "dataset": about["dataset"],
            "doi": about["dataset_doi"],
            "citation": about["citation"],
            "licence": about["licence"],
            "attribution": about["attribution"],
            "days": "local standard time" if self.config.time_zone == "local" else "UTC",
            "aggregations": list(ORDER),
            "inside": inside,
            "data_folder": DATA_FOLDER,
            "groups": _groups(self.config.variables, ORDER),
        }
        text = f"{json.dumps(head, allow_nan=False)[:-1]}, \"locations\": [{', '.join(locations)}]}}"
        # Every < escaped, so no name can end or alter the script element that holds the data.
        page = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/", text.replace("<", "\\u003c"))
        target = self.config.output_folder / "viewer.html"
        target.write_text(page, encoding="utf-8")
        return target

    def _write_data(self, slug: str, aggregation: str, text: str) -> None:
        """A script that hands the page one location's series at one aggregation."""
        folder = self.config.output_folder / DATA_FOLDER
        folder.mkdir(parents=True, exist_ok=True)
        call = f'era5landData("{slug}", "{aggregation}", {text});\n'
        (folder / f"{slug}-{aggregation}.js").write_text(call, encoding="utf-8")


def _series(frame: pd.DataFrame, aggregation: str, row: dict, variables: list[str]) -> dict:
    """A location's packed values at an aggregation, by variable, and its first period. The
    tables have a row for every period from the first, so the page counts them on from it."""
    first = frame.index[0]
    if aggregation == "hourly":
        start = (first.tz_localize(None) + pd.Timedelta(hours=row["utc_offset_hours"])).strftime(
            "%Y-%m-%dT%H"
        )
    elif aggregation == "daily":
        start = first.strftime("%Y-%m-%d")
    elif aggregation == "monthly":
        start = f"{first[0]:04d}-{first[1]:02d}"
    else:
        start = f"{first:04d}"
    decimals, steps = {}, {}
    for name in variables:
        variable = VARIABLES[name]
        source = name if aggregation == "hourly" else column(variable, statistics(variable, aggregation)[0])
        decimals[name], steps[name] = packed(frame[source].to_numpy(dtype="float64"))
    return {"start": start, "decimals": decimals, "steps": steps}


def packed(values: np.ndarray) -> tuple[int, list]:
    """The decimals that keep four significant digits of the largest value, and each value as a
    whole number of the last decimal's unit, written as its step from the value before (the
    first from 0), with None where there's no value."""
    present = np.isfinite(values)
    if not present.any():
        return 0, [None] * len(values)
    top = float(np.abs(values[present]).max())
    decimals = max(0, 3 - math.floor(math.log10(top))) if top > 0 else 0
    whole = np.round(values[present] * 10**decimals).astype(np.int64)
    out = np.full(len(values), None, dtype=object)
    out[present] = np.diff(whole, prepend=0).tolist()
    return decimals, out.tolist()


def _groups(variables: list[str], aggregations: list[str]) -> list[dict]:
    """The charts: one per group of variables, in the config's order."""
    groups: dict[str, dict] = {}
    for name in variables:
        variable = VARIABLES[name]
        group = groups.setdefault(variable.group, {
            "name": variable.group,
            "unit": variable.unit,
            "bars": variable.kind == "amount",
            # Soil layers are ordered by depth, so their colours step from light to dark.
            "ordinal": variable.group in ("Soil temperature", "Soil water"),
            "statistic": {a: statistics(variable, a)[0] or "value" for a in aggregations},
            "series": [],
        })  # fmt: skip
        group["series"].append({"key": name, "label": variable.label})
    return list(groups.values())
