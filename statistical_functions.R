

################################################################
# STATISTICAL PROCESSING FUNCTIONS
#
# generate_stats()
#
# Returns 8 statistics per variable:
#   _senn_slp      = Theil-Sen slope
#   _linear_slp    = Linear regression slope
#   _spearman_rho  = Spearman rank correlation
#   _spearman_pval = Spearman p-value
#   _mk_rho        = Mann-Kendall tau
#   _mk_pval       = Mann-Kendall p-value
#   _mean          = Arithmetic mean
#   _median        = Median
#
################################################################

# ============================================================
# THEIL-SEN SLOPE FUNCTION
# ============================================================

calculate_sen_slope <- function(working_data) {
  
  sen_result <- try(
    zyp::zyp.sen(value ~ year, data = working_data),
    silent = TRUE
  )
  
  if (inherits(sen_result, "try-error")) {
    return(NA_real_)
  }
  
  as.numeric(sen_result$coefficients[2])
}


# ============================================================
# GENERATE MULTIPLE STATS FUNCTION
# ============================================================

generate_stats <- function(data, value_cols = NULL, year_col = "year",
                           min_rows = 3) {
  
  # Check packages
  if (!requireNamespace("zyp", quietly = TRUE)) {
    stop("Install package 'zyp' with install.packages('zyp')")
  }
  
  if (!requireNamespace("Kendall", quietly = TRUE)) {
    stop("Install package 'Kendall' with install.packages('Kendall')")
  }
  
  # Validate inputs
  if (!is.data.frame(data)) {
    stop("Input 'data' must be a data frame")
  }
  
  if (!year_col %in% names(data)) {
    stop(paste("Year column", year_col, "not found"))
  }
  
  # Sort chronologically
  data <- data[order(data[[year_col]]), ]
  
  # Identify numeric variables
  if (is.null(value_cols)) {
    numeric_cols <- names(data)[sapply(data, is.numeric)]
    value_cols <- setdiff(numeric_cols, year_col)
  }
  
  results <- list()
  
  # Process each variable
  for (col in value_cols) {
    
    if (!col %in% names(data)) {
      warning(paste("Column", col, "not found. Skipping."))
      next
    }
    
    # Preserve original numeric precision
    working_data <- data.frame(
      year = as.numeric(data[[year_col]]),
      value = as.numeric(data[[col]])
    )
    
    # Remove missing observations
    working_data <- working_data[
      !is.na(working_data$value) &
        !is.na(working_data$year), ]
    
    # Insufficient observations
    if (nrow(working_data) < min_rows) {
      
      stats <- rep(NA_real_, 8)
      
      names(stats) <- c(
        "senn_slp", "linear_slp",
        "spearman_rho", "spearman_pval",
        "mk_rho", "mk_pval",
        "mean", "median"
      )
      
    } else {
      
      ##########################################################
      # THEIL-SEN SLOPE
      ##########################################################
      
      sen_result <- try(
        zyp::zyp.sen(value ~ year, data = working_data),
        silent = TRUE
      )
      
      sen_slope <- if (inherits(sen_result, "try-error")) {
        NA_real_
      } else {
        as.numeric(sen_result$coefficients[2])
      }
      
      ##########################################################
      # LINEAR REGRESSION SLOPE
      ##########################################################
      
      lm_result <- try(
        lm(value ~ year, data = working_data),
        silent = TRUE
      )
      
      linear_slope <- if (inherits(lm_result, "try-error")) {
        NA_real_
      } else {
        as.numeric(coef(lm_result)[2])
      }
      
      ##########################################################
      # SPEARMAN CORRELATION
      ##########################################################
      
      spearman_result <- try(
        cor.test(
          working_data$year,
          working_data$value,
          method = "spearman",
          exact = FALSE
        ),
        silent = TRUE
      )
      
      spearman_rho <- if (inherits(spearman_result, "try-error")) {
        NA_real_
      } else {
        as.numeric(spearman_result$estimate)
      }
      
      spearman_pval <- if (inherits(spearman_result, "try-error")) {
        NA_real_
      } else {
        spearman_result$p.value
      }
      
      ##########################################################
      # MANN-KENDALL TREND TEST
      ##########################################################
      
      mk_result <- try(
        Kendall::MannKendall(working_data$value),
        silent = TRUE
      )
      
      if (inherits(mk_result, "try-error")) {
        
        mk_tau <- NA_real_
        mk_pval <- NA_real_
        
      } else {
        
        # Extract Mann-Kendall statistics
        mk_tau <- as.numeric(mk_result$tau)
        mk_S <- as.numeric(mk_result$S)
        mk_varS <- as.numeric(mk_result$varS)
        
        # Calculate continuity-corrected Z statistic
        if (is.finite(mk_varS) && mk_varS > 0) {
          
          if (mk_S > 0) {
            mk_z <- (mk_S - 1) / sqrt(mk_varS)
            
          } else if (mk_S < 0) {
            mk_z <- (mk_S + 1) / sqrt(mk_varS)
            
          } else {
            mk_z <- 0
          }
          
          # Numerically stable two-sided p-value
          mk_pval <- 2 * stats::pnorm(
            abs(mk_z),
            lower.tail = FALSE
          )
          
        } else if (is.finite(mk_S) && mk_S == 0) {
          
          mk_pval <- 1
          
        } else {
          
          mk_pval <- NA_real_
        }
      }
      
      ##########################################################
      # DESCRIPTIVE STATISTICS
      ##########################################################
      
      mean_val <- mean(working_data$value)
      median_val <- median(working_data$value)
      
      ##########################################################
      # COMBINE RESULTS
      ##########################################################
      
      stats <- c(
        sen_slope,
        linear_slope,
        spearman_rho,
        spearman_pval,
        mk_tau,
        mk_pval,
        mean_val,
        median_val
      )
      
      names(stats) <- c(
        "senn_slp", "linear_slp",
        "spearman_rho", "spearman_pval",
        "mk_rho", "mk_pval",
        "mean", "median"
      )
    }
    
    # Store results
    for (stat in names(stats)) {
      results[[paste0(col, "_", stat)]] <- stats[stat]
    }
  }
  
  # Return results as data frame
  return(as.data.frame(results))
}
