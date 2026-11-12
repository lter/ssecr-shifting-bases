"""Days, months and years from a location's hours.

A day is the 24 hours stamped 01:00 to 24:00 (the midnight that ends it), as each hour is stamped
with its end: an amount is the hour's total, and a temperature its value at that moment. So a
day's precipitation is the sum of the hours stamped 01:00 through the next day's 00:00. The US
National Weather Service's climate day is the same 24 hours, in local standard time.

By default, days are in each location's local standard time: its time zone's offset from UTC
without daylight saving time, which would give some days 23 or 25 hours, as the IANA time-zone
database defines it (so Ireland's is Irish Standard Time, UTC+1). The offset is this year's,
held for the whole record so that no day shifts within it. The data are hourly, so an offset that
isn't a whole number of hours is rounded to the nearest one, a half-hour toward UTC: India's
+5:30 becomes +5. With time_zone: utc in the config, days are UTC days.

A day gets a value only if all its 24 hours have one; a month or year only if all its days do,
so a partial month or year at either end of the record is left out, not summed short.
"""

import functools
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from era5land_points.config import Location
from era5land_points.variables import VARIABLES, column, statistics

HOUR = pd.Timedelta(hours=1)


@functools.cache
def _finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


def time_zone(location: Location) -> tuple[str, int]:
    """The location's time zone, by name, and its standard offset from UTC in whole hours."""
    name = _finder().timezone_at(lng=location.longitude, lat=location.latitude)
    if name is None:
        return "UTC", 0
    zone = ZoneInfo(name)
    year = datetime.now(timezone.utc).year
    # The offset less daylight saving time, as the time-zone database defines it, most often
    # through the year: Morocco's clocks go back an hour for Ramadan, which the database counts
    # as daylight saving time below standard time, though not always so in every month.
    standard = []
    for month in range(1, 13):
        moment = datetime(year, month, 15, 12, tzinfo=timezone.utc).astimezone(zone)
        standard.append((moment.utcoffset() - moment.dst()) // timedelta(minutes=1))
    minutes = Counter(standard).most_common(1)[0][0]
    hours = (abs(minutes) + 29) // 60
    return name, hours if minutes >= 0 else -hours


def day_of(times: pd.DatetimeIndex, offset_hours: int) -> pd.DatetimeIndex:
    """The day each hour belongs to, as midnight starting it: the hour ending at a time is in
    the day of the hour before it."""
    return (times.tz_localize(None) + pd.Timedelta(hours=offset_hours) - HOUR).floor("D")


def daily(hours: pd.DataFrame, offset_hours: int) -> pd.DataFrame:
    """Each day's statistics, a row a day, indexed by the day's date."""
    grouped = hours.groupby(day_of(hours.index, offset_hours))
    complete = grouped.count() == 24
    columns = {}
    for name in hours.columns:
        variable = VARIABLES[name]
        for statistic in statistics(variable, "daily"):
            values = grouped[name].agg("sum" if statistic == "total" else statistic)
            columns[column(variable, statistic)] = values.where(complete[name])
    table = pd.DataFrame(columns)
    table.index.name = "date"
    return _trimmed(table)


def longer(days: pd.DataFrame, variables: list[str], aggregation: str) -> pd.DataFrame:
    """Each month's or year's statistics from the daily ones, indexed by (year, month) or year:
    a temperature's means of the daily means, minimums and maximums, an amount's total, and
    another variable's mean."""
    index = days.index
    if aggregation == "monthly":
        keys = [index.year.rename("year"), index.month.rename("month")]
        length = index.days_in_month
    else:
        keys = [index.year.rename("year")]
        length = 365 + index.is_leap_year
    grouped = days.groupby(keys)
    # Days outside the record aren't rows, so a period they fall in has too few.
    complete = grouped.count().eq(pd.Series(length, index=index).groupby(keys).first(), axis=0)
    columns = {}
    for name in variables:
        variable = VARIABLES[name]
        how = "sum" if variable.kind == "amount" else "mean"
        sources = [column(variable, s) for s in statistics(variable, "daily")]
        for statistic, source in zip(statistics(variable, aggregation), sources, strict=True):
            columns[column(variable, statistic)] = grouped[source].agg(how).where(complete[source])
    return _trimmed(pd.DataFrame(columns))


def _trimmed(table: pd.DataFrame) -> pd.DataFrame:
    """The table without its leading and trailing rows that hold no value."""
    have = table.notna().any(axis=1).to_numpy()
    if not have.any():
        return table.iloc[0:0]
    first, last = have.argmax(), len(have) - have[::-1].argmax()
    return table.iloc[first:last]
