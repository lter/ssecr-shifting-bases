
# ============================================================
# 03a_plot_trends_expdur.R
# Create interactive maps of annual site-level trends
# ============================================================

library(dplyr)
library(readr)
library(plotly)
library(htmlwidgets)

# ------------------------------------------------------------
# 1. Read input data
# ------------------------------------------------------------

annual_trends <- read_csv(
  "results/annual_site_trends_expdur.csv",
  show_col_types = FALSE
)

sites <- read_csv(
  "sites.csv",
  show_col_types = FALSE
)

# Ensure coordinates are numeric
sites <- sites %>%
  mutate(
    Latitude = as.numeric(Latitude),
    Longitude = as.numeric(Longitude)
  )

# Check for duplicate site codes in the coordinate file
if (anyDuplicated(sites$site_code)) {
  stop("Duplicate site_code values found in sites.csv.")
}

# ------------------------------------------------------------
# 2. Join trend statistics with site coordinates
# ------------------------------------------------------------

trend_data <- annual_trends %>%
  left_join(sites, by = "site_code")

# Check for sites without coordinates
missing_coordinates <- trend_data %>%
  filter(is.na(Latitude) | is.na(Longitude))

if (nrow(missing_coordinates) > 0) {
  warning(
    nrow(missing_coordinates),
    " sites have missing coordinates and will be excluded from maps."
  )
}

trend_data <- trend_data %>%
  filter(!is.na(Latitude), !is.na(Longitude))

# ------------------------------------------------------------
# 3. Identify annual variables
# ------------------------------------------------------------

slope_columns <- grep(
  "_senn_slp$",
  names(trend_data),
  value = TRUE
)

# Trend categories and colors
trend_levels <- c(
  "Significant increase",
  "Nonsignificant increase",
  "Significant decrease",
  "Nonsignificant decrease",
  "No trend",
  "Missing statistics"
)

trend_colors <- c(
  "Significant increase" = "#D73027",
  "Nonsignificant increase" = "#FDAE61",
  "Significant decrease" = "#4575B4",
  "Nonsignificant decrease" = "#ABD9E9",
  "No trend" = "grey60",
  "Missing statistics" = "grey85"
)

# ------------------------------------------------------------
# 4. Create output directory
# ------------------------------------------------------------

output_dir <- "results/trend_maps_expdur"

dir.create(
  output_dir,
  recursive = TRUE,
  showWarnings = FALSE
)

# ------------------------------------------------------------
# 5. Generate one interactive map per variable
# ------------------------------------------------------------

for (slope_col in slope_columns) {
  
  # Identify corresponding Mann-Kendall p-value column
  variable_name <- sub("_senn_slp$", "", slope_col)
  pval_col <- paste0(variable_name, "_mk_pval")
  
  if (!pval_col %in% names(trend_data)) {
    warning("Missing p-value column for: ", variable_name)
    next
  }
  
  # Prepare plotting data
  plot_data <- trend_data %>%
    mutate(
      slope = .data[[slope_col]],
      p_value = .data[[pval_col]],
      
      trend_class = case_when(
        is.na(slope) | is.na(p_value) ~ "Missing statistics",
        
        slope > 0 & p_value < 0.05 ~ "Significant increase",
        slope > 0 ~ "Nonsignificant increase",
        
        slope < 0 & p_value < 0.05 ~ "Significant decrease",
        slope < 0 ~ "Nonsignificant decrease",
        
        slope == 0 ~ "No trend"
      ),
      
      trend_class = factor(
        trend_class,
        levels = trend_levels
      ),
      
      hover_text = paste0(
        "<b>Site: </b>", site_code,
        "<br><b>Variable: </b>", variable_name,
        "<br><b>Theil-Sen slope: </b>",
        signif(slope, 5),
        "<br><b>MK p-value: </b>",
        signif(p_value, 5),
        "<br><b>Trend: </b>", trend_class
      )
    )
  
  # Create interactive global map
  p <- plot_ly(
    data = plot_data,
    type = "scattergeo",
    mode = "markers",
    lon = ~Longitude,
    lat = ~Latitude,
    color = ~trend_class,
    colors = unname(trend_colors),
    text = ~hover_text,
    hoverinfo = "text",
    marker = list(
      size = 9,
      opacity = 0.85,
      line = list(width = 0.5, color = "black")
    )
  ) %>%
    layout(
      title = list(
        text = paste0(
          variable_name,
          "<br><sup>Experiment Duration: Theil-Sen slope | Mann-Kendall significance (p < 0.05)</sup>"
        )
      ),
      geo = list(
        projection = list(type = "natural earth"),
        showland = TRUE,
        landcolor = "rgb(235, 235, 235)",
        showocean = TRUE,
        oceancolor = "rgb(245, 248, 250)",
        showcountries = TRUE,
        countrycolor = "white",
        showcoastlines = TRUE
      ),
      legend = list(
        title = list(text = "Trend classification")
      )
    )
  
  # Save interactive HTML
  safe_name <- gsub("[^A-Za-z0-9_-]", "_", variable_name)
  
  saveWidget(
    p,
    file = file.path(
      output_dir,
      paste0(safe_name, "_trend_map_expdur.html")
    ),
    selfcontained = TRUE
  )
  
  message("Saved map: ", variable_name)
}

# ------------------------------------------------------------
# 6. Completion message
# ------------------------------------------------------------

message("All trend maps generated successfully.")
