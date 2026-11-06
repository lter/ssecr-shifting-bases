from datetime import date
from pathlib import Path

import pytest

from era5land_points.config import ConfigError, load
from era5land_points.variables import DEFAULT

EXAMPLE = Path(__file__).parents[1] / "config.example.yaml"


def write(tmp_path, text: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(text)
    return path


def test_the_example_loads():
    config = load(EXAMPLE)
    assert config.variables == DEFAULT
    assert config.aggregations == ["daily", "monthly", "yearly"]
    assert config.time_zone == "local"
    assert (config.start, config.end) == (None, None)
    assert config.output_folder == (EXAMPLE.parent / "results").resolve()
    assert config.locations[0].slug == "Boulder-Colorado"


def test_defaults_and_dates(tmp_path):
    config = load(write(tmp_path, """
locations: [{name: A, latitude: 1, longitude: 2}]
start: 1991-01-01
end: "2020-12-31"
aggregations: [yearly, hourly]
time_zone: utc
"""))
    assert config.variables == DEFAULT
    assert (config.start, config.end) == (date(1991, 1, 1), date(2020, 12, 31))
    assert config.aggregations == ["hourly", "yearly"]


@pytest.mark.parametrize(
    "text, words",
    [
        ("locations: []", "locations should be a list"),
        ("locations: [{name: A, latitude: 91, longitude: 0}]", "latitude should be from"),
        ("locations: [{name: A, latitude: 1}]", "name, latitude and longitude"),
        ("locations: [{name: A, latitude: 1, longitude: 2}, {name: A, latitude: 3, longitude: 4}]",
         "different name"),
        ("locations: [{name: Lake, latitude: 1, longitude: 2}, {name: lake!, latitude: 3, longitude: 4}]",
         "apart from punctuation and capitals"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\nvariables: [air_temp]",
         "unknown variables: air_temp"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\naggregations: [weekly]",
         "unknown aggregations"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\nstart: 1 March 1990", "YYYY-MM-DD"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\nstart: 2001-01-01\nend: 2000-01-01",
         "on or before"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\ntime_zone: EST", "local or utc"),
        ("locations: [{name: A, latitude: 1, longitude: 2}]\nstrat: 2000-01-01", "unknown settings"),
    ],
)
def test_mistakes_are_named(tmp_path, text, words):
    with pytest.raises(ConfigError, match=words):
        load(write(tmp_path, text))


def test_locations_can_be_read_from_csv(tmp_path):
    sites = tmp_path / "sites.csv"
    sites.write_text(
        "site_code,Latitude,Longitude\nAlberta,53.00124,-111.52\nANG,39.73825,-123.63\n",
        encoding="utf-8",
    )
    config = load(write(tmp_path, """
locations_file: sites.csv
location_columns:
  name: site_code
  latitude: Latitude
  longitude: Longitude
"""))
    assert [location.name for location in config.locations] == ["Alberta", "ANG"]
    assert config.locations[0].latitude == 53.00124
    assert config.locations[0].longitude == -111.52


def test_locations_csv_missing_column_is_reported(tmp_path):
    (tmp_path / "sites.csv").write_text("site_code,Latitude\nA,1\n")
    with pytest.raises(ConfigError, match="missing CSV column"):
        load(write(tmp_path, """
locations_file: sites.csv
location_columns:
  name: site_code
  latitude: Latitude
  longitude: Longitude
"""))
