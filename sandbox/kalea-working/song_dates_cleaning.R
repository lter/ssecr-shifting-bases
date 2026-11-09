
library(tidyverse)


# Part 1: Filtering and wrangling song_sites_no_years ---------------------


## reading in completed years for missing song sites

song_sites_updated_years <- read_csv(here::here(drive_download_path, "song_sites_with_no_years_completed.csv"))
  
## grouping data and changing names to match song_wrangled so we can add in missing years

song_sites_no_years_summary <- song_sites_updated_years %>% 
  group_by(Citations, References, Latitude, Longitude) %>% 
  rename(start_year = Experiment_start,
         end_year = Experiment_end,
         experiment_length_years = experiment_length) %>% 
  subset(select = -c(...1, missing_data, notes, investigator)) %>% 
  ungroup()

song_sites_no_years_wrangled <- song_sites_no_years_summary

# Part 2: joining song_wrangled and song_sites_no_years_wrangled ----------

## running Nyika's code to get song_wrangled

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


####### function to coerce to numeric value ################33
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

## lots of non-numeric values here. for test data wrangling we exclude them but need a better solution in the future.
song_main <- song_main %>%
  coerce_numeric_with_note(SamplingY)

unique(song_main$SamplingY)

## manipulate to get the experiment years

## for each unique Site_number: get min SamplingY (start_year), max (end_year), and the difference (experiment_length_years)

#########################################################
## NOTE: KC editing this line of code to include citation, so it will group with additional data
#########################################################

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

song_wrangled <- song_summary
message("Song data wrangled. Check the qaqc_note column for any issues.")

### dropping all columns from song_sites_no_years_wrangled except for Citations, start_year, end_year, and experiment_length_years

song_sites_for_join <- song_sites_no_years_wrangled %>% 
  subset(select = c(Citations, start_year, end_year, experiment_length_years, fit_scope))

## joining into one dataset

song_joined <- left_join(song_wrangled, song_sites_for_join, by = "Citations") %>% 
  mutate(start_year = coalesce(start_year.x, start_year.y),
         end_year = coalesce(end_year.x, end_year.y),
         experiment_length_years = coalesce(experiment_length_years.x, 
                                            experiment_length_years.y)) %>% 
  select(-ends_with(".x"), -ends_with(".y"))

## filtering out sites that did not meet project scope

song_complete <- song_joined %>% 
  filter(is.na(fit_scope) | fit_scope!= "no")

## in song_complete, still missing sites that were not in the "no years" file - filtered out all sites that were missing data from no years OR didn't fit project scope

