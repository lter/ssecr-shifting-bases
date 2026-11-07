# Deni Murray; 11/7/26

# This script calculates summary trend statistics on ERA5 timeseries data
# receives a time series and outputs summary metrics (trends, averages, etc.)
# Returns 8 statistics per metric:
#   _senn_slp     = Theil-Sen slope (robust non-parametric trend)
#   _linear_slp   = Linear regression slope (parametric trend)
#   _spearman_rho = Spearman's rank correlation coefficient
#   _spearman_pval= Spearman's p-value for trend significance
#   _mk_rho       = Mann-Kendall tau (non-parametric trend correlation)
#   _mk_pval      = Mann-Kendall p-value for trend significance
#   _mean         = Arithmetic mean across water years
#   _median       = Median across water years

# Load statistical functions
source("C:/Users/deni_/OneDrive - USNH/Desktop/post doc/SSECR - course _ project/era5land-points_ssecr/Functions_R/statistical_functions.R")

# Load required packages
library(dplyr)
library(purrr)
library(readr)
library(tidyr)

# Read annual data
annual_data <- read_csv("C:/Users/deni_/OneDrive - USNH/Desktop/post doc/SSECR - course _ project/era5land-points_ssecr/results/yearly.csv")

# Identify variables
value_cols <- annual_data %>%
  select(where(is.numeric)) %>%
  select(-year) %>%
  names()

# Calculate stats for each site
site_trends <- annual_data %>%
  group_by(location) %>%
  group_split() %>%
  map_dfr(function(site_data) {
    
    stats <- generate_stats(
      data = site_data,
      value_cols = value_cols,
      year_col = "year",
      min_rows = 3
    )
    
    stats %>%
      mutate(site_code = unique(site_data$location),
             .before = 1)
  })

# Export
write_csv(site_trends, "C:/Users/deni_/OneDrive - USNH/Desktop/post doc/SSECR - course _ project/era5land-points_ssecr/results/annual_site_trends.csv")

