# era5land-points

Downloads ERA5-Land's hourly data at the points you list, sums them up into days, months and
years, and writes CSV files and a page with a map and charts. You choose the points, variables,
dates and summaries in one config file.

ERA5-Land is ECMWF's land reanalysis: hourly, on a 0.1° grid (about 9 km), from 1950 to about a
week ago. This tool reads it from the Copernicus Climate Data Store's time-series dataset, which
serves one grid point's whole record in a single request.

## Set up, once

1. **Python 3.10 or newer.** Download here: https://www.python.org/downloads/
**You must do this step even if running package in R because package is written in Python **

For windows: open Start menu and search for Anaconda Prompt
Navigate to the directory to where you want the tool to live (eg where you downloaded the code from git)

Example (in Anaconda Prompt command line):

cd C:\Users\YourName\Documents\your-tool-folder

(cd is linux for go to this working directory)

In this folder, make an environment and install the tool (type these into Anaconda Prompt line by line, pressing enter after each):

   ```
   py -m venv .venv
   .venv\Scripts\activate  #non-windows users:   python3 -m venv .venv, then source .venv/bin/activate        
   python -m pip install --upgrade pip
   python -m pip install .
   python -m pip list
   ```
   You should see the installed package and its dependencies.

2. **A Copernicus account.** Register at https://cds.climate.copernicus.eu (free).

3. **Accept the dataset's licence.** Signed in, open
   https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-timeseries?tab=download,
   scroll to the bottom of the form and accept the terms of use. Without this, every request
   is refused.

4. **Save your API key.** Signed in, open https://cds.climate.copernicus.eu/how-to-api. It shows
   two lines, `url: ...` and `key: ...`, with your own key. Copy them into a plain text file named
   `.cdsapirc` in your home folder (on Windows, `C:\Users\<you>\.cdsapirc`, with no `.txt` at
   the end). Keep this file private: it is your password to the Climate Data Store.

## Update site.csv file and package specifications

Copy/edit `my-config.yaml`, fill it in (its comments explain each setting), and run. Locations are read in from a CSV file. `locations_file: sites.csv`
and map the three CSV headers with `location_columns`, for example:

```yaml
locations_file: sites.csv
location_columns:
  name: site_code
  latitude: Latitude
  longitude: Longitude
```

# Run 01_run_era5land.py or the Rstudio version
This script 01_run_era5land.py runs the package, described in more detail below. Script must be run in the same environment as above.
You should be able to just edit the file path of where the tool is living and then run entire script

```
era5land-points my-config.yaml
```

Each location is one request. The Climate Data Store queues requests, so one can take from a
minute to an hour or more; in a test, 50 locations' whole records took 13 minutes, 4 at a time.
The answers are saved in `downloads/` in the output folder, and a
later run with the same locations, variables and dates reuses them, so changing the summaries or
the time zone is quick. To get newer data, delete `downloads/`. Each run replaces the CSV files
and the page, so keep the output folder for the tool's files alone.

If some locations fail, the others still finish, and `locations.csv` says why. The command ends
with exit code 0 if every location worked, 1 if any failed (as every one does when the key is
refused or the licence isn't accepted), and 2 if the config has a mistake or `.cdsapirc` is
missing.

## The variables

| Name | Unit | Daily | Monthly and yearly |
|---|---|---|---|
| `air_temperature` (2 m), `dew_point_temperature` (2 m), `skin_temperature` | °C | mean, min, max | means of the daily mean, min and max |
| `soil_temperature_0_7cm`, `_7_28cm`, `_28_100cm`, `_100_289cm` | °C | mean, min, max | means of the daily mean, min and max |
| `precipitation`, `snowfall` | mm of water | total | total |
| `soil_water_0_7cm`, `_7_28cm`, `_28_100cm`, `_100_289cm` | m³/m³ | mean | mean |
| `snow_depth` | m | mean | mean |
| `snow_cover` | % | mean | mean |
| `surface_pressure` | hPa | mean | mean |
| `solar_radiation`, `thermal_radiation` (downward, at the ground) | W/m² | mean | mean |
| `wind_eastward`, `wind_northward` (10 m) | m/s | mean | mean |

## What you get

In the output folder, with the CSV files that `aggregations` asks for:

- `daily.csv`, `monthly.csv`, `yearly.csv`: one row per location and period. Columns are named
  variable, statistic and unit, such as `air_temperature_mean_C` or `precipitation_total_mm`.
  A file with no complete period, as `yearly.csv` for dates within one year, isn't written.
- `hourly/<location>.csv`, such as `hourly/Boulder-Colorado.csv`: one file per location, about
  60 MB each for the whole record with the six default variables, its times in the time zone
  its days use, such as `2020-07-01T13:00-07:00`.
- `locations.csv`: each location, the ERA5-Land grid point used and its distance, the time zone,
  the first and last day, the date it was downloaded, and whether it worked.
- `about.json`: what every column holds, how the data were made, and how to cite them.
- `viewer.html` and its `viewer-data` folder: open `viewer.html` in a browser. Click a point on
  the map to see its hourly, daily, monthly or yearly charts beside it, whatever `aggregations`
  says. Drag across a chart to zoom in; hourly charts open on the last 30 days. The map's
  background (topographic or satellite imagery) needs the internet; the charts don't. The page
  loads hourly values, and anything else too big to hold, from `viewer-data`, so keep the two
  together: to share the page, share the folder or a zip of it.

## Good to know

- **Grid points.** Each location gets the values of the nearest grid point, without blending
  neighbours. The grid point's height can differ from your location's, which matters for
  temperature in hilly country. A point whose nearest grid point is over the sea or a large
  lake has no values; move it onto land.
- **Hours.** Each hour is stamped with its end. Precipitation, snowfall and radiation are the
  hour's total or mean; temperatures and the rest are the value at that moment.
- **Days.** A day is the 24 hours stamped 01:00 to 24:00, as the US National Weather Service's
  climate day is. With `time_zone: local`, that's in local standard time: the time zone's offset
  without daylight saving time, as the IANA time-zone database defines it, so every day has 24
  hours. Offsets that aren't whole hours are rounded to the nearest hour, a half hour toward
  UTC: India's +5:30 becomes +5.
- **Incomplete periods.** A day has a value only if all 24 of its hours do; a month or year
  only if all its days do. A month or year cut by your dates or the end of the record is left
  out, so a partial year is never summed short.
- **Recent data.** The record runs to about a week ago. ECMWF may still revise its last two to
  three months.
- **Tiny negatives.** Precipitation, snowfall and solar radiation can come out a hair below 0
  from the way ECMWF turns running totals into hourly values; they are set to 0.

## Citing the data

ERA5-Land data are free to use under the CC BY 4.0 licence. Cite:

- Muñoz-Sabater, J., et al. (2021). ERA5-Land: a state-of-the-art global reanalysis dataset
  for land applications. *Earth System Science Data*, 13, 4349–4383.
  https://doi.org/10.5194/essd-13-4349-2021
- The time-series dataset: https://doi.org/10.24381/ee82e357

and include this notice: "Contains modified Copernicus Climate Change Service information
[year]. Neither the European Commission nor ECMWF is responsible for any use that may be made of
the Copernicus information or data it contains."

## Tests

```
python -m pip install ".[test]"
python -m pytest tests
```

The tests use made-up data and send nothing to the Climate Data Store.

## Sharing it

To send the tool to someone, zip this folder and its subfolders alone. In a git clone of the
repository that holds it, run:

```
git fetch origin
git archive --format=zip --prefix=era5land-points/ -o ~/Desktop/era5land-points.zip origin/main:standalone/era5land-points
```

This writes `era5land-points.zip` to your Desktop, about 50 KB, with the folder's committed
files and nothing else: no history, no other part of the repository, and no outputs. Your
clone's files don't change. If the folder sits elsewhere in the repository, change
`standalone/era5land-points` to its path; on Windows, give the zip a full path, such as
`C:\Users\<you>\Desktop\era5land-points.zip`. Send this zip, not a site's download of the
whole repository.
