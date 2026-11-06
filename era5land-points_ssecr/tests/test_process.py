import numpy as np
import pandas as pd
import pytest

from era5land_points import process
from era5land_points.config import Location

VARIABLES = ["air_temperature", "precipitation"]


def frame(first: str, last: str, rain: float = 1.0) -> pd.DataFrame:
    """Hours stamped from first to last, UTC, with the air at 10 °C plus the hour of the day,
    and the same rain every hour."""
    times = pd.date_range(first, last, freq="h", tz="UTC")
    return pd.DataFrame(
        {"air_temperature": 10.0 + times.hour, "precipitation": rain}, index=times
    )


def test_an_hour_belongs_to_the_day_it_ends_in():
    times = pd.DatetimeIndex(["2020-01-01 00:00", "2020-01-01 01:00", "2020-01-02 00:00"],
                             tz="UTC")  # fmt: skip
    assert list(process.day_of(times, 0).strftime("%m-%d")) == ["12-31", "01-01", "01-01"]
    # At UTC-6, 07:00 UTC is 01:00 local, the day's first hour; 06:00 UTC ends the day before.
    times = pd.DatetimeIndex(["2020-01-01 06:00", "2020-01-01 07:00"], tz="UTC")
    assert list(process.day_of(times, -6).strftime("%m-%d")) == ["12-31", "01-01"]


def test_a_day_is_the_24_hours_ending_0100_to_2400():
    days = process.daily(frame("2020-01-01 01:00", "2020-01-03 00:00"), 0)
    assert list(days.index.strftime("%Y-%m-%d")) == ["2020-01-01", "2020-01-02"]
    assert list(days["precipitation_total_mm"]) == [24.0, 24.0]
    first = days.iloc[0]
    # The day's hours are stamped 01:00 to 23:00 and then 00:00: 11 to 33 and 10 °C.
    assert first["air_temperature_min_C"] == 10.0
    assert first["air_temperature_max_C"] == 33.0
    assert first["air_temperature_mean_C"] == pytest.approx((sum(range(11, 34)) + 10) / 24)


def test_days_in_local_standard_time():
    days = process.daily(frame("2020-01-01 07:00", "2020-01-03 06:00"), -6)
    assert list(days.index.strftime("%Y-%m-%d")) == ["2020-01-01", "2020-01-02"]
    assert list(days["precipitation_total_mm"]) == [24.0, 24.0]


def test_a_day_missing_an_hour_has_no_values():
    hours = frame("2020-01-01 01:00", "2020-01-03 00:00")
    hours.iloc[30, 1] = np.nan  # an hour of 2 January's rain
    days = process.daily(hours, 0)
    assert days["precipitation_total_mm"].isna().tolist() == [False, True]
    assert days["air_temperature_mean_C"].notna().all()


def test_partial_days_at_the_ends_are_left_out():
    days = process.daily(frame("2020-01-01 05:00", "2020-01-04 03:00"), 0)
    assert list(days.index.strftime("%Y-%m-%d")) == ["2020-01-02", "2020-01-03"]


def test_months_and_years_need_every_day():
    hours = frame("2020-01-01 01:00", "2021-03-02 00:00", rain=0.5)
    days = process.daily(hours, 0)
    months = process.longer(days, VARIABLES, "monthly")
    # March 2021 has one day only, so it's left out.
    assert months.index[0] == (2020, 1) and months.index[-1] == (2021, 2)
    assert months.loc[(2020, 2), "precipitation_total_mm"] == pytest.approx(29 * 12)
    assert months.loc[(2020, 1), "air_temperature_mean_daily_max_C"] == 33.0
    years = process.longer(days, VARIABLES, "yearly")
    assert list(years.index) == [2020]
    assert years.loc[2020, "precipitation_total_mm"] == pytest.approx(366 * 12)


def test_a_month_missing_a_day_has_no_value():
    hours = frame("2020-01-01 01:00", "2020-03-01 00:00")
    hours.loc["2020-01-15 05:00", "precipitation"] = np.nan
    months = process.longer(process.daily(hours, 0), VARIABLES, "monthly")
    assert months["precipitation_total_mm"].isna().tolist() == [True, False]
    assert months["air_temperature_mean_C"].notna().all()


@pytest.mark.parametrize(
    "latitude, longitude, zone, offsets",
    [
        (40.015, -105.27, "America/Denver", {-7}),  # daylight saving time left out
        (-33.87, 151.21, "Australia/Sydney", {10}),  # southern summer time left out
        (28.61, 77.21, "Asia/Kolkata", {5}),  # +5:30, a half hour toward UTC
        (27.70, 85.32, "Asia/Kathmandu", {6}),  # +5:45, to the nearest hour
        (47.56, -52.71, "America/St_Johns", {-3}),  # -3:30
        # Irish Standard Time is the summer's, and Morocco's clocks go back to UTC for Ramadan:
        # +1 from the time-zone database as most systems build it, 0 as some older ones do;
        # either way the same all year.
        (53.35, -6.26, "Europe/Dublin", {0, 1}),
        (33.57, -7.59, "Africa/Casablanca", {0, 1}),
    ],
)
def test_time_zones(latitude, longitude, zone, offsets):
    name, offset = process.time_zone(Location("x", latitude, longitude))
    assert name == zone and offset in offsets
