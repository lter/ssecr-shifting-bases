"""The variables ERA5-Land's hourly time-series dataset offers, by the names the config uses.

Each variable has a kind, which sets how hours are summarised into days, months and years:

- "temperature": a day's mean, minimum and maximum; a month's or year's mean of the daily means,
  minimums and maximums.
- "amount" (precipitation, snowfall): a day's, month's or year's total.
- "mean" (everything else): a day's, month's or year's mean.

The dataset gives amounts and radiation already as hourly values ("de-accumulated"), not as
running totals, so they are never differenced again. Each value is stamped with the end of the
hour it covers. De-accumulation can leave tiny negative values, which are set to 0.

Sources, read on 2026-10-28: the dataset's request schema (the 20 names below); its user guide's
variable table (units, and which variables are de-accumulated); and live answers (the columns'
short names). https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries and
https://confluence.ecmwf.int/pages/viewpage.action?pageId=536218894
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Variable:
    # The config's name, also used in the output's column names.
    name: str
    # The dataset's name for it in a request, and its column in the answer.
    request: str
    column: str
    kind: str
    # The unit it is written in, and its tag in column names.
    unit: str
    tag: str
    # The viewer draws variables of one group in one chart, so they share a unit; label names
    # the variable in that chart's legend.
    group: str
    label: str
    description: str
    # The range of plausible values in the dataset's own unit. The answer carries no units, so a
    # value outside it means the data aren't in the unit expected.
    low: float
    high: float
    # value written = value in the dataset * scale + offset
    scale: float = 1.0
    offset: float = 0.0
    # Set values below 0 to 0: tiny negatives that de-accumulation leaves.
    never_negative: bool = False


_DEPTHS = {1: ("0_7cm", "0–7 cm"), 2: ("7_28cm", "7–28 cm"), 3: ("28_100cm", "28–100 cm"),
           4: ("100_289cm", "100–289 cm")}  # fmt: skip
# Kelvin to °C, and a range no temperature at the ground leaves.
_CELSIUS = {"unit": "°C", "tag": "C", "low": 150.0, "high": 350.0, "offset": -273.15}
# J/m² over an hour to its mean in W/m².
_WATTS = {"unit": "W/m²", "tag": "W_m2", "scale": 1 / 3600}

_ALL = [
    Variable("air_temperature", "2m_temperature", "t2m", "temperature", group="Air temperature",
             label="Air", description="Air temperature 2 m above the ground", **_CELSIUS),
    Variable("dew_point_temperature", "2m_dewpoint_temperature", "d2m", "temperature",
             group="Air temperature", label="Dew point",
             description="Dew point temperature 2 m above the ground", **_CELSIUS),
    Variable("skin_temperature", "skin_temperature", "skt", "temperature",
             group="Skin temperature", label="Skin",
             description="Temperature of the ground's surface", **_CELSIUS),
    *[
        Variable(f"soil_temperature_{depth}", f"soil_temperature_level_{n}", f"stl{n}",
                 "temperature", group="Soil temperature", label=words,
                 description=f"Soil temperature, {words} below the surface", **_CELSIUS)
        for n, (depth, words) in _DEPTHS.items()
    ],
    # An hour's amount, which de-accumulation can leave a little below 0: at most 6.3e-8 m below
    # in 42 points' whole records (2026-10-28), so -0.1 mm leaves a wide margin.
    Variable("precipitation", "total_precipitation", "tp", "amount", unit="mm", tag="mm",
             group="Precipitation", label="Precipitation",
             description="Rain and snow, as liquid water", low=-1e-4, high=0.5, scale=1000.0,
             never_negative=True),
    Variable("snowfall", "snowfall", "sf", "amount", unit="mm water equivalent", tag="mm_we",
             group="Snowfall", label="Snowfall", description="Snowfall, as liquid water",
             low=-1e-4, high=0.5, scale=1000.0, never_negative=True),
    Variable("snow_depth", "snow_depth", "sde", "mean", unit="m", tag="m", group="Snow depth",
             label="Snow depth", description="Depth of the snow on the ground", low=0.0,
             high=1000.0),
    Variable("snow_cover", "snow_cover", "snowc", "mean", unit="%", tag="pct",
             group="Snow cover", label="Snow cover",
             description="Share of the ground covered by snow", low=0.0, high=100.0),
    *[
        Variable(f"soil_water_{depth}", f"volumetric_soil_water_level_{n}", f"swvl{n}", "mean",
                 unit="m³/m³", tag="m3_m3", group="Soil water", label=words,
                 description=f"Volume of water per volume of soil, {words} below the surface",
                 low=0.0, high=1.0)
        for n, (depth, words) in _DEPTHS.items()
    ],
    Variable("surface_pressure", "surface_pressure", "sp", "mean", unit="hPa", tag="hPa",
             group="Surface pressure", label="Pressure", description="Air pressure at the ground",
             low=30000.0, high=110000.0, scale=0.01),
    # Downward shortwave can be a little below 0 after de-accumulation; longwave never is.
    Variable("solar_radiation", "surface_solar_radiation_downwards", "ssrd", "mean",
             group="Radiation", label="Solar",
             description="Sunlight reaching the ground, direct and diffuse, as the hour's mean",
             low=-1e5, high=6e6, never_negative=True, **_WATTS),
    Variable("thermal_radiation", "surface_thermal_radiation_downwards", "strd", "mean",
             group="Radiation", label="Thermal",
             description="Heat radiation from the sky reaching the ground, as the hour's mean",
             low=0.0, high=6e6, **_WATTS),
    Variable("wind_eastward", "10m_u_component_of_wind", "u10", "mean", unit="m/s", tag="m_s",
             group="Wind at 10 m", label="Eastward",
             description="Wind toward the east, 10 m above the ground", low=-100.0, high=100.0),
    Variable("wind_northward", "10m_v_component_of_wind", "v10", "mean", unit="m/s", tag="m_s",
             group="Wind at 10 m", label="Northward",
             description="Wind toward the north, 10 m above the ground", low=-100.0, high=100.0),
]  # fmt: skip
VARIABLES: dict[str, Variable] = {variable.name: variable for variable in _ALL}

# The variables a config has when it names none.
DEFAULT = ["air_temperature", "precipitation", *(f"soil_temperature_{d}" for d, _ in
                                                 _DEPTHS.values())]  # fmt: skip


def statistics(variable: Variable, aggregation: str) -> list[str]:
    """The statistics written for a variable at an aggregation, in column order: the first is
    the one the viewer draws."""
    if aggregation == "hourly":
        return [""]
    if variable.kind == "amount":
        return ["total"]
    if variable.kind == "temperature":
        if aggregation == "daily":
            return ["mean", "min", "max"]
        return ["mean", "mean_daily_min", "mean_daily_max"]
    return ["mean"]


def column(variable: Variable, statistic: str) -> str:
    """An output column's name, such as air_temperature_mean_C, or precipitation_mm for an
    hour."""
    return "_".join(part for part in (variable.name, statistic, variable.tag) if part)
