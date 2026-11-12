# PURPOSE AND USE:
# This does some manipulation on each dataset to get it ready to harmonize. This may include attaching metadata.

# PART 1: SETUP ---- (libraries and sourcing using `here`)
librarian::shelf(googledrive, tidyr, dplyr, stringr, here, readr)

# PART 2: USER INPUTS ---- (keep user inputs and switches in one place)

## Set the place to read data from. This should stay the same as the import-drive-data.R script.
drive_download_path <- here::here("1_data-management", "data", "drive_download")
derived_data_path <- here::here("1_data-management", "data", "derived_data")
dir.create(derived_data_path, recursive = TRUE, showWarnings = FALSE)

# PART 3: READ IN FILES ----

## Source the import-drive-data.R script to download the most recent data
source(here::here("1_data-management", "tools", "import-drive-data.R"))

# PART 4: DEFINE FUNCTIONS ---- (if not sourced from another script)
# Converts `col` to numeric in place and logs any non-numeric entries that get coerced to NA
coerce_numeric_with_note <- function(df, col) {
  col_name <- rlang::as_name(rlang::ensym(col))

  df %>%
    mutate(
      .numeric_tmp = suppressWarnings(as.numeric({{ col }})),
      qaqc_note = if_else(
        !is.na({{ col }}) & is.na(.numeric_tmp),
        paste0(coalesce(qaqc_note, ""), "non-numeric entry in ", col_name, " coerced to NA; "),
        qaqc_note
      ),
      "{col_name}" := .numeric_tmp
    ) %>%
    select(-.numeric_tmp)
}


# PART 5: Song Data ----
## Source Deni's python script here eventually and make it a tool. for Now the compiled dataset is read in.
song_main <- read_csv(here::here(drive_download_path, "song_compiled.csv"))
str(song_main)

## add a qaqc_note col on the far right of main dataset and the dataset name on far left
song_main <- song_main %>%
  mutate(dataset = "song", 
         qaqc_note = NA_character_) %>%
  relocate(dataset)

# check sampling years
unique(song_main$SamplingY)

## lots of non-numeric values here. for test data wrangling we exclude them but need a better solution in the future.
song_main <- song_main %>%
  coerce_numeric_with_note(SamplingY)

unique(song_main$SamplingY)

## manipulate to get the experiment years

## for each unique Site_number: get min SamplingY (start_year), max (end_year), and the difference (experiment_length_years)
song_summary <- song_main %>%
  mutate(SamplingY = na_if(SamplingY, 0)) %>%   # treat 0 as a missing year
  group_by(dataset, Site, Site_number, Latitude, Longitude, Elevation_m, Ecosystem) %>%
  summarise(
    start_year = if (all(is.na(SamplingY))) NA_real_ else min(SamplingY, na.rm = TRUE),
    end_year   = if (all(is.na(SamplingY))) NA_real_ else max(SamplingY, na.rm = TRUE),
    experiment_length_years = end_year - start_year + 1,   # single-year site = 1, not 0
    qaqc_note  = paste(unique(na.omit(qaqc_note)), collapse = "") %>% na_if(""),
    .groups = "drop"
  )

song_wrangled <- song_summary
message("Song data wrangled. Check the qaqc_note column for any issues.")

# PART 6: Corre Data ----

## Read in the corre data
corre_main <- read_csv(here::here(drive_download_path, "corre_main.csv"))
corre_metadata <- read_csv(here::here(drive_download_path, "corre_metadata.csv"))

str(corre_main)
str(corre_metadata)

## rename really ugly cols
corre_metadata <- corre_metadata %>%
  rename(experiment_length_years = `experiment length in years (not including pre-treatment)`)


##define cols to join
cols_to_join <- c("site_code", "experiment years", "end_year", "experiment_length_years")

## join experimet year, end_year, experiment length in years from metadata to main by site_code 
corre_main <- corre_main %>%
  left_join(
    corre_metadata %>%
      select(cols_to_join) %>%
      distinct(),
    by = "site_code"
  )

## add a qaqc_note col on the far right of main dataset and the dataset name on far left
corre_main <- corre_main %>%
  mutate(dataset = "corre", 
         qaqc_note = NA_character_) %>%
  relocate(dataset)

## Make length in years numeric
unique(corre_main$experiment_length_years)

corre_main <- corre_main %>%
  coerce_numeric_with_note(experiment_length_years)   # no quotes

unique(corre_main$experiment_length_years)

corre_wrangled <- corre_main
message("Corre data wrangled. Check the qaqc_note column for any issues.")

# PART 7: MESI Data ----
mesi_main <- read_csv(here::here(drive_download_path, "mesi_main.csv"))
mesi_metadata <- read_csv(here::here(drive_download_path, "mesi_metadata.csv"))

# check sampling years
unique(mesi_main$start_year)

## for each unique exp: extract experiment start (start_year), duration (duration), and the end date (end_year)
mesi_summary_raw <- mesi_main %>%
  filter(experiment_type=="field")  %>%
  group_by(study,lat,lon,ecosystem_type) %>%
  summarise(
    start_year = min(start_year),
    duration   = max(duration),
    end_year = max(as.numeric(str_extract(as.character(sampling_date),"\\d{4}$"))),
    citations = paste(unique(citation), collapse=","),
    treatments = paste(unique(treatment), collapse = ","),
    elevation = max(elevation) +
    .groups = "drop",
  )

## fill in missing values by calcuting from existing columns
mesi_summary <- mesi_summary_raw %>%
  mutate(
    start_year = coalesce(start_year, end_year-duration+1),
    end_year = coalesce(end_year, start_year+duration-1),
    duration = coalesce(duration, end_year-start_year+1)
  )

## add a qaqc_note col on the far right of main dataset and the dataset name on far left
mesi_summary <- mesi_summary %>%
  mutate(dataset = "mesi", 
         qaqc_note = NA_character_) %>%
  relocate(dataset)

## how many datasets have full start, end date - 630
length(mesi_summary$start_year) - sum(is.na(mesi_summary$start_year))

mesi_wrangled <- mesi_summary
message("Mesi data wrangled")

# PART X: SAVE OUTPUTS ---- (and report out that script is done. This always last.)

#Define datasets to save
datasets_to_save <- c("corre_wrangled", "song_wrangled","mesi_wrangled")

## save wrangled datasets to derived_data_path as .csv files
for (dataset_name in datasets_to_save) {
  dataset <- get(dataset_name)
  write.csv(dataset, file = here::here(derived_data_path, paste0(dataset_name, ".csv")), row.names = FALSE)
}

message(paste("All datasets have been wrangled and saved to:", derived_data_path))
