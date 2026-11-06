"""Whole runs, with a stand-in for CDS that answers from synthetic data."""

import json
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
import pytest
from answers import build, hours, typical

from era5land_points import cli, config, pipeline, viewer
from era5land_points.variables import VARIABLES

# The stand-in's record ends here, as the real one ends about a week before today.
RECORD_END = date(2021, 3, 5)


class FakeCDS:
    """Answers every request at its location's nearest grid point; over the sea with no
    values, and at latitude 10 with an error, as CDS gives for a failed job."""

    requests: list = []

    def retrieve(self, dataset, request, target):
        FakeCDS.requests.append(request)
        assert dataset == "reanalysis-era5-land-timeseries"
        assert request["data_format"] == "csv"
        first, last = (date.fromisoformat(d) for d in request["date"][0].split("/"))
        times = hours(first, min(last, RECORD_END))
        lat, lon = (round(request["location"][k], 1) for k in ("latitude", "longitude"))
        if lat == 10.0:
            raise RuntimeError("the job failed")
        asked = {v.column for v in VARIABLES.values() if v.request in request["variable"]}
        values = {k: v for k, v in typical(times).items() if k in asked}
        if lat == 30.0:
            values = {k: np.full(len(times), np.nan) for k in values}
        with open(target, "wb") as f:
            f.write(build(times, values, lat, lon))


@pytest.fixture
def write(tmp_path):
    def writing(text: str):
        path = tmp_path / "config.yaml"
        path.write_text("output_folder: out\n" + text)
        FakeCDS.requests = []
        return path

    return writing


def run(path) -> int:
    return pipeline.run(config.load(path), make_client=FakeCDS, say=lambda line: None)


def test_a_run(write, tmp_path):
    path = write("""
locations:
  - {name: Boulder, latitude: 40.015, longitude: -105.27}
  - {name: Out at sea, latitude: 30.0, longitude: -40.0}
  - {name: Job fails, latitude: 10.0, longitude: 20.0}
start: 2020-01-01
aggregations: [hourly, daily, monthly, yearly]
""")
    assert run(path) == 2
    assert len(FakeCDS.requests) == 3
    # A day either side of the dates, for local days that start or end in another UTC day.
    assert FakeCDS.requests[0]["date"][0].startswith("2019-12-31/")
    out = tmp_path / "out"

    places = pd.read_csv(out / "locations.csv")
    assert list(places["status"].str[:6]) == ["ok", "failed", "failed"]
    assert "move the location onto land" in places["status"][1]
    assert "the job failed" in places["status"][2]
    assert places["time_zone"][0] == "America/Denver"

    daily = pd.read_csv(out / "daily.csv")
    assert daily["date"].iloc[0] == "2020-01-01"
    # The record ends 2021-03-05 23:00 UTC, 16:00 in Denver, so the 4th is the last whole day.
    assert daily["date"].iloc[-1] == "2021-03-04"
    assert set(daily["location"]) == {"Boulder"}
    monthly = pd.read_csv(out / "monthly.csv")
    assert (monthly["year"].iloc[-1], monthly["month"].iloc[-1]) == (2021, 2)
    yearly = pd.read_csv(out / "yearly.csv")
    assert list(yearly["year"]) == [2020]
    assert yearly["precipitation_total_mm"].iloc[0] == pytest.approx(366 * 4 * 0.5)

    hourly = pd.read_csv(out / "hourly" / "Boulder.csv")
    assert list(hourly.columns[:3]) == ["location", "time", "air_temperature_C"]
    assert hourly["time"].iloc[0] == "2020-01-01T01:00-07:00"
    assert sorted(p.name for p in (out / "hourly").iterdir()) == ["Boulder.csv"]

    about = json.loads((out / "about.json").read_text())
    assert about["columns"]["precipitation_total_mm"]["unit"] == "mm"
    page = (out / "viewer.html").read_text()
    assert "/*DATA*/" not in page and '"name": "Boulder"' in page

    # A second run takes the saved answers, and asks only for the one that failed.
    FakeCDS.requests = []
    assert run(path) == 2
    assert [r["location"]["latitude"] for r in FakeCDS.requests] == [10.0]


def test_utc_days_and_an_end(write, tmp_path):
    path = write("""
locations: [{name: Boulder, latitude: 40.015, longitude: -105.27}]
start: 2020-03-01
end: 2020-12-31
aggregations: [hourly, daily, yearly]
time_zone: utc
""")
    assert run(path) == 0
    assert FakeCDS.requests[0]["date"] == ["2020-02-29/2021-01-01"]
    out = tmp_path / "out"
    daily = pd.read_csv(out / "daily.csv")
    assert (daily["date"].iloc[0], daily["date"].iloc[-1]) == ("2020-03-01", "2020-12-31")
    assert len(daily) == 306
    # 2020 is cut by the start date, so it has no yearly value, and the file isn't written.
    assert not (out / "yearly.csv").exists()
    hourly = pd.read_csv(out / "hourly" / "Boulder.csv")
    assert (hourly["time"].iloc[0], hourly["time"].iloc[-1]) == (
        "2020-03-01T01:00+00:00", "2021-01-01T00:00+00:00"
    )


def test_a_rerun_leaves_no_earlier_files(write, tmp_path):
    run(write("""
locations: [{name: A, latitude: 40.015, longitude: -105.27}]
start: 2020-01-01
aggregations: [hourly, daily, monthly, yearly]
"""))
    path = write("""
locations: [{name: B, latitude: 40.015, longitude: -105.27}]
start: 2020-01-01
variables: [air_temperature]
aggregations: [monthly]
""")
    assert run(path) == 0
    # Another variable list is another request; the earlier answer isn't used.
    assert FakeCDS.requests[0]["variable"] == ["2m_temperature"]
    out = tmp_path / "out"
    assert not (out / "daily.csv").exists() and not (out / "yearly.csv").exists()
    assert not list((out / "hourly").iterdir())
    assert sorted(p.name for p in (out / "viewer-data").iterdir()) == ["B-hourly.js"]
    assert list(pd.read_csv(out / "monthly.csv").columns)[3:] == [
        "air_temperature_mean_C", "air_temperature_mean_daily_min_C",
        "air_temperature_mean_daily_max_C",
    ]  # fmt: skip


def test_saved_answers(write, tmp_path):
    text = """
locations: [{name: A, latitude: 40.015, longitude: -105.27}]
start: 2020-01-01
end: 2020-06-30
aggregations: [monthly]
"""
    assert run(write(text)) == 0
    places = pd.read_csv(tmp_path / "out" / "locations.csv")
    assert places["downloaded"][0] == datetime.now(timezone.utc).date().isoformat()
    # One cut off part way is deleted, and downloaded again by the next run.
    (saved,) = (tmp_path / "out" / "downloads").iterdir()
    saved.write_bytes(saved.read_bytes()[:1000])
    assert run(write(text)) == 1
    assert "deleted it" in pd.read_csv(tmp_path / "out" / "locations.csv")["status"][0]
    assert not saved.exists()
    assert run(write(text)) == 0 and len(FakeCDS.requests) == 1
    # Other dates are another request.
    assert run(write(text.replace("2020-06-30", "2020-07-31"))) == 0
    assert len(FakeCDS.requests) == 1
    assert len(list((tmp_path / "out" / "downloads").iterdir())) == 2


def test_dates_with_no_whole_day_of_values(write, tmp_path):
    path = write("locations: [{name: A, latitude: 40.015, longitude: -105.27}]\nstart: 2021-03-05\n")
    assert run(path) == 1
    assert "no whole day" in pd.read_csv(tmp_path / "out" / "locations.csv")["status"][0]


def test_the_page_puts_what_doesnt_fit_in_files_beside_it(write, tmp_path, monkeypatch):
    path = write("""
locations: [{name: A, latitude: 40.015, longitude: -105.27}]
start: 2020-01-01
aggregations: [yearly]
""")
    # Room for the year and the 14 months, not the 430 days.
    monkeypatch.setattr(viewer, "BUDGET", 3_000)
    run(path)
    out = tmp_path / "out"
    page = (out / "viewer.html").read_text()
    # All four, though the config asks for yearly CSV files alone.
    assert '"aggregations": ["yearly", "monthly", "daily", "hourly"]' in page
    assert '"inside": ["yearly", "monthly"]' in page
    assert sorted(p.name for p in (out / "viewer-data").iterdir()) == ["A-daily.js", "A-hourly.js"]
    script = (out / "viewer-data" / "A-hourly.js").read_text()
    assert script.startswith('era5landData("A", "hourly", {"start": "2020-01-01T01", ')
    data = json.loads(script[script.index("{"):script.rindex(")")])
    # The air's hourly values, packed as steps of 0.01 °C, and unpacked by summing them: the
    # stand-in's 10 + 5 sin(2π (h - 9) / 24) °C at UTC hours 08 to 10, 01:00 to 03:00 in Denver.
    assert data["decimals"]["air_temperature"] == 2
    air = np.cumsum(data["steps"]["air_temperature"][:24]) / 100
    assert list(air[:3]) == pytest.approx([8.71, 10.0, 11.29], abs=0.005)


def test_packing():
    values = np.array([12.345, np.nan, 12.355, -3.0, np.nan])
    decimals, steps = viewer.packed(values)
    assert (decimals, steps) == (2, [1234, None, 2, -1536, None])  # 12.345 rounds to even
    assert viewer.packed(np.array([np.nan, np.nan])) == (0, [None, None])
    assert viewer.packed(np.array([0.0, 0.0])) == (0, [0, 0])


def test_the_commands_exit_codes(write, tmp_path, monkeypatch, capsys):
    good = write("locations: [{name: A, latitude: 40.015, longitude: -105.27}]\nstart: 2021-01-01\n")
    monkeypatch.setattr(pipeline, "default_client", FakeCDS)
    assert cli.main([str(good)]) == 0
    at_sea = write("locations: [{name: S, latitude: 30.0, longitude: -40.0}]\nstart: 2021-01-01\n")
    assert cli.main([str(at_sea)]) == 1

    bad = tmp_path / "bad.yaml"
    bad.write_text("locations: []\n")
    assert cli.main([str(bad)]) == 2
    assert "The config has a problem" in capsys.readouterr().err

    def no_key():
        raise Exception("Missing/incomplete configuration file: ~/.cdsapirc")

    monkeypatch.setattr(pipeline, "default_client", no_key)
    fresh = write("locations: [{name: B, latitude: 42.0, longitude: -93.6}]\n")
    assert cli.main([str(fresh)]) == 2
    assert ".cdsapirc" in capsys.readouterr().err
