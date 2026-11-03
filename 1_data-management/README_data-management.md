# README: ssecr-shifting-bases/1_data-management

## Purpose

This folder handles raw data intake, cleaning, reshaping, and creation of derived datasets used by later analysis steps.

## Status / To-do
- [ ] Add more datasets to the wrangle script if we want to use them ex MESI
- [ ] dead with the non-numeric durations of experiments better in the wrangle scripts before harmonizing
- [ ] decide how we want to use the harmonized data to compare the datasets
- [ ] Decide on shape of the combined output needed downstream for ERA 5, particularly around the experiment duration and start date (lat, long, site name, study duration, etc.)
- [x] draft a wrangle script
- [x] draft a harmonize script
- [x] draft an import data from drive script
- [x] start the column key

## Workflow

1. **Add new data in Google Drive:** Add new data to the [`00_DATA`](https://drive.google.com/drive/folders/1wNL7DGYT2yF_ZPlCjBWsvaF3cFHXLZMx?usp=drive_link) folder on google-drive. Follow the naming conventions described in the [`README.md`](https://github.com/lter/ssecr-shifting-bases/blob/main/README.md). Each *dataset* should be given a kebab-case shortname and located in its own sub folder in the google drive data folder. A *dataset* may have multiple *data-products* including different metadata and data .csv.
2. **Update the Data Log:** Enter new dataset in the [shifting-baselines_data-log](https://docs.google.com/spreadsheets/d/1RZ5IbneqZOQX13Wmcu3APHuFADN8i4pLsiqoCRovDT8/edit?usp=sharing). For datasets with multiple sheets or lots of metadata it is only necessary to make a row for the data products we plan to use.The team's data log (tracked in Drive as a Google Sheet) lists every dataset we use, where it lives on Drive, and whether it should be pulled into this repo (`read_into_git == TRUE`).
3. **Pull data to work locally:** Run `tools/import-drive-data.R` to download the data log and every flagged dataset into `data/drive_download/`. This folder is git-ignored, so nothing downloaded here is committed. Do this before working with data to ensure you have the latest version
4. **Wrangle each dataset:** Run `scripts/01_wrangle-datasets.R` to clean and reshape each raw dataset individually (reading from the local `data/` folder, not from Drive directly) and write the results to `data/derived_data/`.
5. **Add relevant col to the col_key:** Update the [column key](https://docs.google.com/spreadsheets/d/16993pe8Aqfo3DOoS8FhS1_wv1pn5TnBQRmwOcwuJewo/edit?usp=sharing) in google drive with the desired tidy names that came from your wrangled dataset. 
6. **Harmonize the derived datasets:** Run `scripts/02_harmonize-datasets.R` to rename columns across the derived datasets into a shared, combined format using `ltertools::harmonize()`. Must be run after `01_wrangle-datasets.R`, since it reads from `data/derived_data/`.

## Sub Folder Structure

| Item | Description |
| --- | --- |
| `tools/` | Reusable utility scripts that support the workflow but aren't part of the numbered cleaning/combining pipeline |
| `scripts/` | Numbered workflow scripts that read, clean, combine, and reshape data into derived outputs |
| `data/` | Git-ignored local storage for downloaded and derived data |
| `drive-folder-locations.csv` | Key/ID lookup for important Drive folders (raw data root, derived data root, etc.) |

## Script & Tool Explanations
See the overall [`README.md`](https://github.com/lter/ssecr-shifting-bases/blob/main/README.md) file for a description of script.
