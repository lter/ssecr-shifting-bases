

# ============================================================
# ERA5-LAND POINT EXTRACTION
# Standalone RStudio runner for the custom ERA5 Python package
# ============================================================

# 1. PACKAGES -------------------------------------------------

if (!requireNamespace("reticulate", quietly = TRUE)) {
  install.packages("reticulate")
}

library(reticulate)


# 2. PROJECT SETTINGS -----------------------------------------

project_dir <- file.path(
  "C:/Users/deni_/OneDrive - USNH/Desktop/post doc",
  "SSECR - course _ project/era5land-points_ssecr"
)

config_file <- file.path(project_dir, "my-config.yaml")

results_dir <- file.path(project_dir, "results")
results_file <- file.path(results_dir, "locations.csv")

# IMPORTANT:
# Replace this with your exact Python path to the environment you created from the readme:
# import sys
# print(sys.executable)

python_exe <- "C:/Users/deni_/anaconda3/envs/era5land-points/python.exe"

# 3. CHECK FILES AND ENVIRONMENT ------------------------------

cat("\n")
cat("============================================================\n")
cat("ERA5-LAND EXTRACTION\n")
cat("============================================================\n")

if (!dir.exists(project_dir)) {
  stop("Project directory not found: ", project_dir)
}

if (!file.exists(config_file)) {
  stop("Configuration file not found: ", config_file)
}

if (!file.exists(python_exe)) {
  stop("Python executable not found. Check python_exe: ", python_exe)
}

# Set working directory
setwd(project_dir)

# Connect to Python environment
use_python(python_exe, required = TRUE)

cat("\nPython environment:", py_config()$python, "\n")
cat("Project directory:", getwd(), "\n")
cat("Configuration:", config_file, "\n")


# 4. LOAD PYTHON PACKAGE --------------------------------------

cat("\nChecking ERA5-Land package...\n")

cli <- import("era5land_points.cli", convert = FALSE)

cat("ERA5-Land package successfully loaded.\n")


# 5. RUN EXTRACTION -------------------------------------------

cat("\n")
cat("============================================================\n")
cat("STARTING ERA5-LAND EXTRACTION\n")
cat("============================================================\n\n")

start_time <- Sys.time()

# Run the package's actual CLI function.
# Python output is directed to the RStudio console.
exit_code <- cli$main(as.list(config_file))

end_time <- Sys.time()

runtime <- difftime(end_time, start_time, units = "mins")


# 6. EXTRACTION SUMMARY ---------------------------------------

cat("\n")
cat("============================================================\n")
cat("EXTRACTION SUMMARY\n")
cat("============================================================\n")

if (exit_code == 0) {
  
  cat("Status: SUCCESS\n")
  cat("All locations completed successfully.\n")
  
} else if (exit_code == 1) {
  
  cat("Status: PARTIAL SUCCESS\n")
  cat("One or more locations failed.\n")
  
} else {
  
  cat("Status: SETUP OR CONFIGURATION ERROR\n")
  cat("The extraction did not complete normally.\n")
  
}

cat("Exit code:", exit_code, "\n")
cat("Runtime:", round(as.numeric(runtime), 2), "minutes\n")


# 7. READ LOCATION RESULTS ------------------------------------

if (file.exists(results_file)) {
  
  results <- read.csv(
    results_file,
    stringsAsFactors = FALSE
  )
  
  successful <- results[results$status == "ok", ]
  
  failed <- results[
    grepl("^failed:", results$status),
    ,
    drop = FALSE
  ]
  
  cat("\n")
  cat("------------------------------------------------------------\n")
  cat("LOCATION RESULTS\n")
  cat("------------------------------------------------------------\n")
  
  cat("Total locations:", nrow(results), "\n")
  cat("Successful:", nrow(successful), "\n")
  cat("Failed:", nrow(failed), "\n")
  
  # Print failed locations and reasons
  if (nrow(failed) > 0) {
    
    cat("\nFAILED LOCATIONS:\n")
    cat("------------------------------------------------------------\n")
    
    for (i in seq_len(nrow(failed))) {
      
      reason <- sub(
        "^failed:",
        "",
        failed$status[i]
      )
      
      cat(
        sprintf(
          "%02d. %s: %s\n",
          i,
          failed$name[i],
          trimws(reason)
        )
      )
    }
    
  } else {
    
    cat("\nAll locations completed successfully!\n")
    
  }
  
  # Print results file location
  cat("\nFull location report:\n")
  cat(results_file, "\n")
  
} else {
  
  cat("\nWARNING: locations.csv was not generated.\n")
  cat("The package may have stopped before processing locations.\n")
  
}


# 8. FINISH ---------------------------------------------------

cat("\n")
cat("============================================================\n")
cat("RUN FINISHED\n")
cat("============================================================\n")

