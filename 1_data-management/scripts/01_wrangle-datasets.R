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
## Keeping in NA values in SamplingY to retain data for join with missing song data
## adding Citation as a grouping factor for join

song_summary <- song_main %>%
  mutate(SamplingY = na_if(SamplingY, 0)) %>%   # treat 0 as a missing year
  group_by(dataset, Citations, Site, Site_number, Latitude, Longitude, Elevation_m, Ecosystem) %>%
  summarise(
    start_year = if (all(is.na(SamplingY))) NA_real_ else min(SamplingY, na.rm = FALSE),
    end_year   = if (all(is.na(SamplingY))) NA_real_ else max(SamplingY, na.rm = FALSE),
    experiment_length_years = end_year - start_year + 1,   # single-year site = 1, not 0
    qaqc_note  = paste(unique(na.omit(qaqc_note)), collapse = "") %>% na_if(""),
    .groups = "drop"
  )


message("Song data wrangled. Check the qaqc_note column for any issues.")

## adding in song data for missing years
song_sites_updated_years <- read_csv(here::here(drive_download_path, "song_sites_with_no_years_completed.csv"))

## grouping data and changing names to match song_wrangled 

song_sites_no_years_summary <- song_sites_updated_years %>% 
  group_by(Citations, References, Latitude, Longitude) %>% 
  rename(start_year = Experiment_start,
         end_year = Experiment_end,
         experiment_length_years = experiment_length) %>% 
  subset(select = -c(...1, missing_data, notes, investigator)) %>% 
  ungroup()

song_sites_no_years_wrangled <- song_sites_no_years_summary

### subsetting song_sites_no_years_wrangled for join 
song_sites_for_join <- song_sites_no_years_wrangled %>% 
  subset(select = c(Citations, start_year, end_year, experiment_length_years, fit_scope))

## joining song datasets
song_joined <- left_join(song_summary, song_sites_for_join, by = "Citations") %>% 
  mutate(start_year = coalesce(start_year.x, start_year.y),
         end_year = coalesce(end_year.x, end_year.y),
         experiment_length_years = coalesce(experiment_length_years.x, 
                                            experiment_length_years.y)) %>% 
  select(-ends_with(".x"), -ends_with(".y"))

## filtering out sites that did not meet project scope or missing data from year search
song_complete <- song_joined %>% 
  filter(is.na(fit_scope) | fit_scope!= "no")

## removing fit scope column - unneccessary after filtering
song_complete_02 <- song_complete %>% 
  subset(select = -c(fit_scope))

## still missing some dates that weren't in the original "no dates" .csv
song_wrangled <- song_complete_02


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
## add later

# PART X: SAVE OUTPUTS ---- (and report out that script is done. This always last.)

#Define datasets to save
datasets_to_save <- c("corre_wrangled", "song_wrangled")

## save wrangled datasets to derived_data_path as .csv files
for (dataset_name in datasets_to_save) {
  dataset <- get(dataset_name)
  write.csv(dataset, file = here::here(derived_data_path, paste0(dataset_name, ".csv")), row.names = FALSE)
}

message(paste("All datasets have been wrangled and saved to:", derived_data_path))
