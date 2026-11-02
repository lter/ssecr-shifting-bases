## PURPOSE AND USE:
#This script reads in data from our data log (in google drive) using the googledrive package and saves it to a local folder which is automatically git ignored
# PART 1: SETUP ---- (libraries and sourcing using `here`)
librarian::shelf(googledrive, dplyr, stringr, here)

# PART 2: USER INPUTS ---- (keep user inputs and switches in one place)

## Set where to save the datadownloaded for drive locally. any folder names 'data' will be automatically gitignored
drive_download_path <- here::here("1_data-management", "data", "drive_download")
# make the path if it doesn't exist
dir.create(drive_download_path, recursive = TRUE, showWarnings = FALSE)


# PART 3: READ IN FILES ----

# Fist Read in the Data Log
## Watch the terminal this requires a login the first time you run it 
drive_download("https://docs.google.com/spreadsheets/d/1RZ5IbneqZOQX13Wmcu3APHuFADN8i4pLsiqoCRovDT8/edit?gid=0#gid=0", 
    type = "csv",
    path = here::here(drive_download_path, "data_log.csv"),
    overwrite = TRUE)
    

## Read in the other datasets as defined in the data log. Update datalog to change read-in
# Read in the data log (downloaded above)
data_log <- read.csv(here::here(drive_download_path, "data_log.csv"))

# Use googledrive package to download a local copy of each dataset using the datalog to specify the file path and new file nam
# Download each dataset flagged for read_into_git == TRUE, coerce into csv
for (i in seq_len(nrow(data_log))) {
  if (isTRUE(data_log$read_into_git[i])) {
    drive_download(
      data_log$g_drive_url[i],
      type = "csv",
      path = here::here(drive_download_path, paste0(data_log$internal_data_product_name[i], ".csv")),
      overwrite = TRUE
    )
  }
}
# PART X: SAVE OUTPUTS ---- (and report out that script is done. This always last.)
message(paste("All datasets have been downloaded. Check the data_log.csv file for details on each dataset. Download location:", drive_download_path))