import io
import zipfile
from datetime import date

import numpy as np
import pytest
from answers import build, hours, typical

from era5land_points.answer import AnswerError, NoValues, read
from era5land_points.config import Location
from era5land_points.variables import DEFAULT, VARIABLES

BOULDER = Location("Boulder", 40.015, -105.2705)
TIMES = hours(date(2020, 1, 1), date(2020, 1, 3))


def save(tmp_path, data: bytes):
    path = tmp_path / "answer.zip"
    path.write_bytes(data)
    return path


def test_reads_and_converts(tmp_path):
    values = typical(TIMES)
    values["tp"][5] = -1e-7  # what de-accumulation can leave
    series = read(save(tmp_path, build(TIMES, values, 40.0, -105.3)), BOULDER, DEFAULT)
    assert list(series.hours.columns) == DEFAULT
    assert len(series.hours) == 72
    assert series.hours.index[0] == TIMES[0].tz_localize("UTC")
    assert series.hours["air_temperature"].iloc[9] == pytest.approx(10.0)
    assert series.hours["precipitation"].iloc[6] == pytest.approx(0.5)
    assert series.hours["precipitation"].iloc[5] == 0.0
    assert (series.latitude, series.longitude) == pytest.approx((40.0, -105.3))
    assert series.distance_km(BOULDER) == pytest.approx(3.0, abs=0.1)


def test_missing_dates_become_empty_hours(tmp_path):
    values = typical(TIMES)
    keep = TIMES.date != date(2020, 1, 2)
    data = build(TIMES[keep], {k: v[keep] for k, v in values.items()}, 40.0, -105.3)
    series = read(save(tmp_path, data), BOULDER, DEFAULT)
    assert len(series.hours) == 72
    assert series.hours["air_temperature"].isna().sum() == 24


def test_a_point_over_the_sea(tmp_path):
    empty = {k: np.full(len(TIMES), np.nan) for k in typical(TIMES)}
    with pytest.raises(NoValues, match="move the location onto land"):
        read(save(tmp_path, build(TIMES, empty, 30.0, -40.0)), Location("Sea", 30.0, -40.0),
             DEFAULT)  # fmt: skip


def test_a_grid_point_that_isnt_the_nearest(tmp_path):
    with pytest.raises(AnswerError, match="nearest"):
        read(save(tmp_path, build(TIMES, typical(TIMES), 40.1, -105.3)), BOULDER, DEFAULT)


def test_values_in_another_unit(tmp_path):
    values = typical(TIMES)
    values["t2m"] = values["t2m"] - 273.15  # °C, where kelvin is expected
    with pytest.raises(AnswerError, match="air_temperature"):
        read(save(tmp_path, build(TIMES, values, 40.0, -105.3)), BOULDER, DEFAULT)


def test_a_variable_missing(tmp_path):
    values = typical(TIMES)
    del values["stl4"]
    with pytest.raises(AnswerError, match="stl4"):
        read(save(tmp_path, build(TIMES, values, 40.0, -105.3)), BOULDER, DEFAULT)


@pytest.mark.parametrize(
    "name, raw, written",
    [
        ("air_temperature", 273.15, 0.0),
        ("soil_temperature_100_289cm", 283.15, 10.0),
        ("precipitation", 0.0012, 1.2),
        ("precipitation", -1e-8, 0.0),
        ("snowfall", -1e-8, 0.0),
        ("snow_depth", 0.5, 0.5),
        ("snow_cover", 50.0, 50.0),
        ("soil_water_0_7cm", 0.3, 0.3),
        ("surface_pressure", 101325.0, 1013.25),
        ("solar_radiation", 1_800_000.0, 500.0),
        ("solar_radiation", -2.0, 0.0),
        ("thermal_radiation", 1_080_000.0, 300.0),
        ("wind_eastward", -3.5, -3.5),
    ],
)
def test_each_variables_unit(tmp_path, name, raw, written):
    short = VARIABLES[name].column
    data = build(TIMES, {short: np.full(len(TIMES), raw)}, 40.0, -105.3)
    series = read(save(tmp_path, data), BOULDER, [name])
    assert series.hours[name].iloc[0] == pytest.approx(written)


def test_an_answer_of_one_csv_file_unzipped(tmp_path):
    with zipfile.ZipFile(io.BytesIO(build(TIMES, typical(TIMES), 40.0, -105.3))) as archive:
        members = archive.namelist()
        assert len(members) == 3
    values = {"t2m": typical(TIMES)["t2m"]}
    with zipfile.ZipFile(io.BytesIO(build(TIMES, values, 40.0, -105.3))) as archive:
        (member,) = archive.namelist()
        path = tmp_path / "answer.zip"
        path.write_bytes(archive.read(member))
    assert len(read(path, BOULDER, ["air_temperature"]).hours) == 72


def test_across_the_180th_meridian(tmp_path):
    fiji = Location("Fiji", -16.5, 179.98)
    values = {"t2m": typical(TIMES)["t2m"]}
    series = read(save(tmp_path, build(TIMES, values, -16.5, -180.0)), fiji, ["air_temperature"])
    assert series.distance_km(fiji) < 3
