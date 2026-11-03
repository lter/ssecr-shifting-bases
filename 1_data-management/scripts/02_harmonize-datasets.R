# PURPOSE AND USE:
# This script uses the `ltertools::harmonize()` function to harmonize the datasets cleaned in
# 01_wrangle-datasets.R. 

# PART 1: SETUP ---- (libraries and sourcing using `here`)
librarian::shelf(googledrive, dplyr, stringr, readr, here, lter/ltertools)

# PART 2: USER INPUTS ---- (keep user inputs and switches in one place)
derived_data_path <- here::here("1_data-management", "data", "derived_data")
column_key_path    <- here::here("1_data-management", "data", "drive_download", "column_key.csv")

# PART 3: READ IN FILES ----

## list all datasets in the derived_data folder
## (harmonize() reads directly from this folder later, this list is just so we know what's there)
datasets <- list.files(derived_data_path, pattern = "\\.csv$", full.names = TRUE)
datasets

## read in the column key for renaming and subsetting columns
column_key<- read_csv(column_key_path, show_col_types = FALSE)

# PART 4: DEFINE FUNCTIONS ---- (if not sourced from another script)
# none needed here -- ltertools::harmonize() does the harmonizing

# PART 5: HARMONIZE THE DATASETS ----

## harmonize() reads every file in `raw_folder` referenced by the key, renames columns per the key,
## and row-binds everything into one long data frame with a `source` column marking provenance
harmonized_data <- ltertools::harmonize(
  key         = column_key,
  raw_folder  = derived_data_path,
  data_format = "csv",
  quiet       = FALSE # set TRUE once the key is finalized, to silence key/data mismatch messages
)

glimpse(harmonized_data)

# PART X: SAVE OUTPUTS ---- (and report out that script is done. This always last.)
out_path <- here::here("1_data-management", "data", "derived_data", "harmonized_data.csv")
write_csv(harmonized_data, out_path)

message(
  "Harmonized ", length(datasets), " datasets into ", nrow(harmonized_data),
  " rows. Saved to: ", out_path
)

## Still open (see repo README to-do): what shape does the harmonized output need to be in for
## matching against ERA5? At minimum this likely means: lat, long, site name, and study duration.
