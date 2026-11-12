# PURPOSE AND USE:
# Deleting overlapping experiments

# PART 1: SETUP ---- (libraries and sourcing using `here`)
librarian::shelf(googledrive, tidyr, dplyr, stringr, here, readr,sf)

# PART 2: USER INPUTS ---- (keep user inputs and switches in one place)

## Set the place to read data from. This should stay the same as the import-drive-data.R script.
derived_data_path <- here::here("1_data-management", "data", "derived_data")

# PART 3: READ IN FILES ----
gce_harmonized <- read.csv(here::here("1_data-management", "data", "derived_data","harmonized_data.csv"))

# PART 4: CLEAN EXPERIMENT DATES ----
# fill in missing start, end durations for each experiment
gce_harmonized <- gce_harmonized %>%
  mutate(
    start_year = coalesce(start_year, end_year-experiment_length_years+1),
    end_year = coalesce(end_year, start_year+experiment_length_years-1),
    experiment_length_years = coalesce(experiment_length_years, end_year-start_year+1)
  )

#remove experiments with insufficient date data
gce_harmonized <- gce_harmonized %>% 
  drop_na(start_year, end_year, experiment_length_years,lattitude_dd,longitude_dd)

# PART 5: HOW MANY EXPERIMENTS OVELAP IN TIME AND SPACE ---
# generate lists of experiments nearby one another
sites <- st_as_sf(gce_harmonized, coords=c("longitude_dd","lattitude_dd"), crs=4326)
neighbors <- st_is_within_distance(sites, dist=1000)
groups <- components(graph_from_adj_list(neighbors, mode="all"))$membership

#populate experiment list with spatial group coding
gce_harmonized$spatial_group <- NA_integer_
gce_harmonized$spatial_group <- groups

# PART 6: FILTER OUT OVERLAPPING EXPERIMENTS ---
# remove experiments with overlapping locations and start years
gce_unique <- gce_harmonized %>%
  group_by(spatial_group, start_year) %>%
  filter(n() > 1, !is.na(start_year)) %>%
  ungroup() %>%
  arrange(spatial_group, start_year, source)

#complie a list of removed overlapping experiments to manually analyze
overlap_summary <- gce_harmonized %>%
  mutate(row_id=row_number(),
         experiment_id=paste(source,site,row_id,sep="_")) %>%
  filter(!is.na(spatial_group),!is.na(start_year)) %>%
  group_by(spatial_group,start_year) %>%
  summarise(
    n_rows=n(),
    n_sources=n_distinct(source),
    experiment_ids=paste(experiment_id,collapse=", "),
    .groups="drop"
  ) %>%
  filter(n_sources>1) %>%
  arrange(desc(n_rows))