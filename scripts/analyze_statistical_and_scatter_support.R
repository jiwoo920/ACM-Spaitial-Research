library(ggplot2)

root_prefix <- if (file.exists("outputs/gis_enriched_llm_results.csv")) "" else "project/"
out_dir <- paste0(root_prefix, "outputs")
fig_dir <- paste0(root_prefix, "figures")
dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

ink <- "#1F2430"
muted <- "#5D667A"
grid_col <- "#E7EAF0"
blue <- "#6B8FD6"
orange <- "#E68A5A"
green <- "#4F9A58"

theme_src <- function(base_size = 10) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 3, color = ink),
      plot.subtitle = element_text(size = base_size, color = muted, margin = margin(b = 8)),
      axis.title = element_text(color = ink),
      axis.text = element_text(color = muted),
      panel.grid.major = element_line(color = grid_col, linewidth = 0.28),
      panel.grid.minor = element_blank(),
      legend.position = "bottom",
      legend.title = element_blank(),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(12, 14, 12, 14)
    )
}

p_fmt <- function(p) {
  if (is.na(p)) return(NA_character_)
  if (p < 0.001) return("<0.001")
  sprintf("%.3f", p)
}

rate <- function(x) if (length(x) == 0) 0 else round(mean(x, na.rm = TRUE) * 100, 1)
safe_num <- function(x) ifelse(is.null(x) || length(x) == 0 || is.na(x), NA_real_, as.numeric(x)[1])

cramers_v <- function(tbl) {
  chi <- suppressWarnings(chisq.test(tbl, correct = FALSE))
  n <- sum(tbl)
  k <- min(nrow(tbl), ncol(tbl))
  if (n == 0 || k <= 1) return(NA_real_)
  sqrt(as.numeric(chi$statistic) / (n * (k - 1)))
}

phi_2x2 <- function(tbl) {
  if (!all(dim(tbl) == c(2, 2))) return(NA_real_)
  chi <- suppressWarnings(chisq.test(tbl, correct = FALSE))
  sqrt(as.numeric(chi$statistic) / sum(tbl))
}

test_2x2 <- function(tbl, prefer = "auto") {
  expected <- suppressWarnings(chisq.test(tbl, correct = FALSE)$expected)
  if (prefer == "fisher" || any(expected < 5)) {
    ft <- fisher.test(tbl)
    list(
      test = "Fisher exact",
      p = ft$p.value,
      statistic = NA_real_,
      effect_name = "odds_ratio",
      effect = safe_num(ft$estimate)
    )
  } else {
    ct <- chisq.test(tbl, correct = FALSE)
    list(
      test = "Chi-square",
      p = ct$p.value,
      statistic = as.numeric(ct$statistic),
      effect_name = "phi",
      effect = phi_2x2(tbl)
    )
  }
}

write_md <- function(path, lines) writeLines(lines, path, useBytes = TRUE)

df <- read.csv(file.path(out_dir, "gis_enriched_llm_results.csv"))
df$condition_label <- ifelse(df$condition == "baseline", "Baseline", "Spatially grounded")
df$condition_label <- factor(df$condition_label, levels = c("Baseline", "Spatially grounded"))
df$violation_spatial_inconsistency <- df$any_violation == 1 | df$spatial_inconsistency_count > 0
df$vehicle_group <- ifelse(tolower(df$vehicle_access) == "yes", "Vehicle access", "No vehicle")
df$public_transit_selected <- df$transportation_mode == "Public transit"
df$transit_label_group <- factor(df$transit_access, levels = c("Good", "Moderate", "Limited", "None"))
df$transit_stop_proxy_group <- ifelse(
  df$transit_stop_access_group %in% c("far", "no nearby stop"),
  "Transit-desert proxy",
  "Near/moderate proxy"
)
df$transit_stop_proxy_group <- factor(df$transit_stop_proxy_group, levels = c("Near/moderate proxy", "Transit-desert proxy"))
df$no_vehicle <- tolower(df$vehicle_access) == "no"

rows <- list()
binary_rates <- function(tbl) {
  if (!all(dim(tbl) == c(2, 2))) {
    return(list(group_a = NA_character_, group_b = NA_character_, group_a_positive_rate = NA_real_, group_b_positive_rate = NA_real_, risk_difference_pp = NA_real_))
  }
  positive_col <- if ("TRUE" %in% colnames(tbl)) "TRUE" else colnames(tbl)[2]
  group_a <- rownames(tbl)[1]
  group_b <- rownames(tbl)[2]
  a_rate <- if (sum(tbl[group_a, ]) > 0) as.numeric(tbl[group_a, positive_col]) / sum(tbl[group_a, ]) * 100 else NA_real_
  b_rate <- if (sum(tbl[group_b, ]) > 0) as.numeric(tbl[group_b, positive_col]) / sum(tbl[group_b, ]) * 100 else NA_real_
  list(
    group_a = group_a,
    group_b = group_b,
    group_a_positive_rate = round(a_rate, 1),
    group_b_positive_rate = round(b_rate, 1),
    risk_difference_pp = round(a_rate - b_rate, 1)
  )
}

add_result <- function(test_id, question, condition, tbl, result, notes = "", include_binary_rates = TRUE) {
  br <- if (include_binary_rates) {
    binary_rates(tbl)
  } else {
    list(group_a = NA_character_, group_b = NA_character_, group_a_positive_rate = NA_real_, group_b_positive_rate = NA_real_, risk_difference_pp = NA_real_)
  }
  rows[[length(rows) + 1]] <<- data.frame(
    test_id = test_id,
    question = question,
    condition = condition,
    test = result$test,
    p_value = result$p,
    p_value_formatted = p_fmt(result$p),
    statistic = result$statistic,
    effect_size_name = result$effect_name,
    effect_size = result$effect,
    group_a = br$group_a,
    group_a_positive_rate = br$group_a_positive_rate,
    group_b = br$group_b,
    group_b_positive_rate = br$group_b_positive_rate,
    risk_difference_pp = br$risk_difference_pp,
    table = paste(capture.output(print(tbl)), collapse = " | "),
    notes = notes,
    stringsAsFactors = FALSE
  )
}

# 1. vehicle_access vs violation/spatial inconsistency, condition-specific.
for (cond in levels(df$condition_label)) {
  sub <- df[df$condition_label == cond, ]
  sub$vehicle_group <- factor(sub$vehicle_group, levels = c("No vehicle", "Vehicle access"))
  tbl <- table(sub$vehicle_group, sub$violation_spatial_inconsistency)
  res <- test_2x2(tbl, prefer = "fisher")
  add_result(
    "vehicle_access_vs_risk",
    "Vehicle access vs violation/spatial inconsistency",
    cond,
    tbl,
    res,
    "Condition-specific 2x2 test; Fisher used by design because one vehicle-access cell can be small or zero-risk."
  )
}

# 2. transit_access label vs public transit recommendation, condition-specific.
for (cond in levels(df$condition_label)) {
  sub <- df[df$condition_label == cond, ]
  tbl <- table(sub$transit_label_group, sub$public_transit_selected)
  expected <- suppressWarnings(chisq.test(tbl, correct = FALSE)$expected)
  if (any(expected < 5)) {
    set.seed(20260625)
    ft <- fisher.test(tbl, simulate.p.value = TRUE, B = 10000)
    res <- list(test = "Fisher exact simulated p-value", p = ft$p.value, statistic = NA_real_, effect_name = "Cramers_V", effect = cramers_v(tbl))
  } else {
    ct <- chisq.test(tbl, correct = FALSE)
    res <- list(test = "Chi-square", p = ct$p.value, statistic = as.numeric(ct$statistic), effect_name = "Cramers_V", effect = cramers_v(tbl))
  }
  add_result(
    "transit_label_vs_public_transit",
    "Original transit_access label vs public transit recommendation",
    cond,
    tbl,
    res,
    "Tests prompt-label sensitivity; labels are ACS-informed approximate transit-access labels, not GTFS or route-level access."
  )
}

# 3. paired baseline vs spatial public-transit recommendation for same personas.
wide <- reshape(
  df[, c("persona_id", "condition", "public_transit_selected")],
  idvar = "persona_id",
  timevar = "condition",
  direction = "wide"
)
if (all(c("public_transit_selected.baseline", "public_transit_selected.spatial_grounded") %in% names(wide))) {
  tbl <- table(wide$public_transit_selected.baseline, wide$public_transit_selected.spatial_grounded)
  mt <- mcnemar.test(tbl, correct = TRUE)
  discordant_b <- ifelse("FALSE" %in% rownames(tbl) && "TRUE" %in% colnames(tbl), tbl["FALSE", "TRUE"], 0)
  discordant_c <- ifelse("TRUE" %in% rownames(tbl) && "FALSE" %in% colnames(tbl), tbl["TRUE", "FALSE"], 0)
  paired_or <- ifelse(discordant_c == 0, Inf, discordant_b / discordant_c)
  res <- list(test = "McNemar", p = mt$p.value, statistic = as.numeric(mt$statistic), effect_name = "paired_discordant_odds_ratio", effect = paired_or)
  add_result(
    "paired_baseline_vs_spatial_public_transit",
    "Paired baseline vs spatially grounded public-transit recommendation",
    "Paired personas",
    tbl,
    res,
    "Persona-level paired test comparing whether public transit was selected in baseline vs spatially grounded responses.",
    include_binary_rates = FALSE
  )
}

# 4. transit_stop_proxy_group vs risk among no-vehicle households.
nv <- df[df$no_vehicle, ]
for (cond in c("All", levels(df$condition_label))) {
  sub <- if (cond == "All") nv else nv[nv$condition_label == cond, ]
  sub$transit_stop_proxy_group <- factor(sub$transit_stop_proxy_group, levels = c("Transit-desert proxy", "Near/moderate proxy"))
  tbl <- table(sub$transit_stop_proxy_group, sub$violation_spatial_inconsistency)
  res <- test_2x2(tbl, prefer = "fisher")
  add_result(
    "transit_proxy_group_vs_no_vehicle_risk",
    "Transit-stop proxy group vs violation/spatial inconsistency among no-vehicle households",
    cond,
    tbl,
    res,
    "Exploratory GIS-proxy feasibility audit using tract-centroid distance to major transit-stop proxy points."
  )
}

summary <- do.call(rbind, rows)
summary$p_value <- signif(summary$p_value, 6)
summary$statistic <- round(summary$statistic, 4)
summary$effect_size <- round(summary$effect_size, 4)
write.csv(summary, file.path(out_dir, "statistical_tests_summary.csv"), row.names = FALSE)

# Tract-level scatter data.
shelter_claims <- read.csv(file.path(out_dir, "shelter_claim_proxy_check_by_response.csv"))
shelter_claims$nearby_shelter_claim <- tolower(as.character(shelter_claims$nearby_shelter_claim)) == "true"
df_shelter <- merge(df, shelter_claims[, c("run_id", "nearby_shelter_claim", "nearby_shelter_claim_proxy_issue")], by = "run_id", all.x = TRUE)
df_shelter$nearby_shelter_claim[is.na(df_shelter$nearby_shelter_claim)] <- FALSE

tract_rows <- aggregate(
  cbind(violation_spatial_inconsistency, public_transit_selected, nearby_shelter_claim) ~
    GEOID + census_tract_id + neighborhood_label,
  data = df_shelter,
  FUN = function(x) c(rate = rate(x), n = length(x), count = sum(x, na.rm = TRUE))
)
tract <- data.frame(
  GEOID = tract_rows$GEOID,
  census_tract_id = tract_rows$census_tract_id,
  neighborhood_label = tract_rows$neighborhood_label,
  violation_spatial_inconsistency_rate = tract_rows$violation_spatial_inconsistency[, "rate"],
  n_responses = tract_rows$violation_spatial_inconsistency[, "n"],
  nearby_shelter_claim_rate = tract_rows$nearby_shelter_claim[, "rate"]
)
dist_cols <- unique(df[, c(
  "GEOID",
  "nearest_transit_stop_distance_km",
  "nearest_candidate_shelter_distance_km",
  "distance_to_fire_km"
)])
tract <- merge(tract, dist_cols, by = "GEOID", all.x = TRUE)

persona_unique <- unique(df[, c("persona_id", "GEOID", "vehicle_access")])
nv_by_tract <- aggregate(tolower(persona_unique$vehicle_access) == "no", by = list(GEOID = persona_unique$GEOID), FUN = function(x) c(share = rate(x), n = length(x), count = sum(x)))
nv_df <- data.frame(
  GEOID = nv_by_tract$GEOID,
  no_vehicle_persona_share = nv_by_tract$x[, "share"],
  n_personas = nv_by_tract$x[, "n"],
  no_vehicle_personas = nv_by_tract$x[, "count"]
)
tract <- merge(tract, nv_df, by = "GEOID", all.x = TRUE)
write.csv(tract, file.path(out_dir, "tract_level_scatter_data.csv"), row.names = FALSE)

cor_rows <- list()
add_cor <- function(metric_id, x, y) {
  ok <- complete.cases(x, y)
  if (sum(ok) >= 3 && length(unique(x[ok])) > 1 && length(unique(y[ok])) > 1) {
    pearson <- cor.test(x[ok], y[ok], method = "pearson")
    spearman <- suppressWarnings(cor.test(x[ok], y[ok], method = "spearman", exact = FALSE))
    cor_rows[[length(cor_rows) + 1]] <<- data.frame(
      metric_id = metric_id,
      n_tracts = sum(ok),
      pearson_r = as.numeric(pearson$estimate),
      pearson_p = pearson$p.value,
      spearman_rho = as.numeric(spearman$estimate),
      spearman_p = spearman$p.value
    )
  } else {
    cor_rows[[length(cor_rows) + 1]] <<- data.frame(metric_id = metric_id, n_tracts = sum(ok), pearson_r = NA, pearson_p = NA, spearman_rho = NA, spearman_p = NA)
  }
}
add_cor("transit_proxy_distance_vs_risk", tract$nearest_transit_stop_distance_km, tract$violation_spatial_inconsistency_rate)
add_cor("shelter_distance_vs_nearby_claim", tract$nearest_candidate_shelter_distance_km, tract$nearby_shelter_claim_rate)
add_cor("no_vehicle_share_vs_risk", tract$no_vehicle_persona_share, tract$violation_spatial_inconsistency_rate)
cors <- do.call(rbind, cor_rows)
write.csv(cors, file.path(out_dir, "tract_level_scatter_correlations.csv"), row.names = FALSE)

subtitle_for <- function(metric_id) {
  row <- cors[cors$metric_id == metric_id, ][1, ]
  paste0("Exploratory tract-level association; Pearson r=", sprintf("%.2f", row$pearson_r),
         " (p=", p_fmt(row$pearson_p), "), Spearman rho=", sprintf("%.2f", row$spearman_rho),
         " (p=", p_fmt(row$spearman_p), ")")
}

scatter_plot <- function(data, x, y, size, title, subtitle, xlab, ylab, filename, color = blue, show_size_legend = TRUE) {
  if (show_size_legend) {
    p <- ggplot(data, aes(x = .data[[x]], y = .data[[y]], size = .data[[size]])) +
      geom_point(shape = 21, fill = color, color = ink, alpha = 0.82, stroke = 0.35) +
      scale_size_continuous(range = c(2.5, 8), name = "Responses per tract")
    legend_position <- "right"
  } else {
    p <- ggplot(data, aes(x = .data[[x]], y = .data[[y]])) +
      geom_point(shape = 21, fill = color, color = ink, alpha = 0.82, stroke = 0.35, size = 5.2)
    legend_position <- "none"
  }
  p <- p +
    geom_smooth(
      data = data,
      aes(x = .data[[x]], y = .data[[y]]),
      inherit.aes = FALSE,
      method = "lm",
      se = FALSE,
      linewidth = 0.5,
      color = muted,
      linetype = "dashed"
    ) +
    scale_y_continuous(labels = function(v) paste0(v, "%")) +
    labs(title = title, subtitle = subtitle, x = xlab, y = ylab) +
    theme_src(10) +
    theme(legend.position = legend_position)
  ggsave(file.path(fig_dir, filename), p, width = 8.0, height = 5.4, dpi = 220, bg = "white")
}

scatter_plot(
  tract,
  "nearest_transit_stop_distance_km",
  "violation_spatial_inconsistency_rate",
  "no_vehicle_personas",
  "Transit proxy distance vs. feasibility risk",
  subtitle_for("transit_proxy_distance_vs_risk"),
  "Nearest transit-stop proxy distance (km)",
  "Violation / spatial-inconsistency rate",
  "transit_proxy_distance_vs_risk_scatter.png",
  blue
)
scatter_plot(
  tract,
  "nearest_candidate_shelter_distance_km",
  "nearby_shelter_claim_rate",
  "n_responses",
  "Candidate service distance vs. nearby-shelter claims",
  subtitle_for("shelter_distance_vs_nearby_claim"),
  "Nearest candidate shelter/service distance (km)",
  "Nearby shelter claim rate",
  "shelter_distance_vs_nearby_claim_scatter.png",
  green
)
scatter_plot(
  tract,
  "no_vehicle_persona_share",
  "violation_spatial_inconsistency_rate",
  "n_personas",
  "No-vehicle persona share vs. feasibility risk",
  subtitle_for("no_vehicle_share_vs_risk"),
  "No-vehicle persona share by tract (%)",
  "Violation / spatial-inconsistency rate",
  "no_vehicle_share_vs_risk_scatter.png",
  orange,
  show_size_legend = FALSE
)

sig_rows <- summary[!is.na(summary$p_value) & summary$p_value < 0.05, ]
write_md(
  file.path(out_dir, "statistical_tests_summary.md"),
  c(
    "# Statistical Tests Summary",
    "",
    "These tests use the existing 400-response GIS-enriched dataset. They provide statistical support for feasibility-audit findings, not ground-truth evacuation prediction accuracy.",
    "",
    "## Main Tests",
    "",
    "- Vehicle access vs. violation/spatial inconsistency was tested separately for baseline and spatially grounded conditions using Fisher's exact test.",
    "- Original `transit_access` label vs. public transit recommendation was tested separately by condition using chi-square or simulated Fisher exact tests depending on expected cell counts.",
    "- Baseline vs. spatially grounded public-transit recommendation was tested as a paired persona-level comparison using McNemar's test.",
    "- Transit-stop proxy group vs. violation/spatial inconsistency among no-vehicle households was tested using Fisher's exact test.",
    "",
    "## Significant Results At p < 0.05",
    if (nrow(sig_rows) == 0) "- No test reached p < 0.05." else paste0("- ", sig_rows$question, " (", sig_rows$condition, "): ", sig_rows$test, ", p = ", sig_rows$p_value_formatted, ", ", sig_rows$effect_size_name, " = ", sig_rows$effect_size),
    "",
    "## Interpretation Boundary",
    "",
    "These tests support subgroup differences and prompt/proxy associations within the experiment. They do not validate LLM decisions against real evacuation behavior, and they do not establish route-level transit reachability or verified shelter access."
  )
)

write_md(
  file.path(out_dir, "statistical_and_scatter_interpretation.md"),
  c(
    "# Statistical And Scatter Interpretation",
    "",
    "This analysis adds statistical support and optional tract-level scatter figures to the feasibility-audit framing. No new LLM responses were generated.",
    "",
    "## Statistical Support",
    "",
    "The strongest statistical support remains the relationship between vehicle access and violation/spatial inconsistency. This aligns with the paper's core finding that no-vehicle households are the clearest feasibility-risk group. Tests involving `transit_access` should be interpreted as prompt-label sensitivity tests because the original label is ACS-informed and approximate, not GTFS-derived.",
    "",
    "McNemar's test evaluates paired changes between baseline and spatially grounded responses for the same personas. It is useful for checking whether prompt condition changed public-transit recommendation behavior, but it should not be interpreted as external predictive validity.",
    "",
    "The transit-stop proxy group tests among no-vehicle households are GIS-proxy feasibility audits. They use tract-centroid distance to major transit-stop proxy points and do not represent route-level reachability.",
    "",
    "## Exploratory Scatter Figures",
    "",
    "- `project/figures/transit_proxy_distance_vs_risk_scatter.png` shows an exploratory tract-level association between nearest transit-stop proxy distance and feasibility risk.",
    "- `project/figures/shelter_distance_vs_nearby_claim_scatter.png` shows whether candidate shelter/service distance aligns with nearby-shelter language.",
    "- `project/figures/no_vehicle_share_vs_risk_scatter.png` shows whether tracts with more no-vehicle personas also show higher feasibility risk.",
    "",
    "The correlation coefficients in these scatter plots are exploratory tract-level associations. They are not model prediction accuracy, do not use real evacuation ground truth, and should not be framed as validating LLM behavior.",
    "",
    "## Why Feasibility Rates, Not Prediction-Correlation Metrics",
    "",
    "This study evaluates whether LLM-generated evacuation decisions contain obvious feasibility risks under household constraints and spatial proxy checks. Because there is no real evacuation ground truth in the dataset, prediction-correlation metrics would overstate what the experiment can support. Feasibility rates are more appropriate because they audit internal consistency and constraint violations rather than claiming behavioral prediction accuracy.",
    "",
    "## Recommended Wording",
    "",
    "Use the statistical tests as support for feasibility-audit contrasts, especially vehicle access and no-vehicle transit-proxy risk. Use tract-level scatter plots as exploratory visual diagnostics only. Avoid claiming predictive accuracy, real evacuation validity, operational feasibility, route-level reachability, or verified shelter accessibility."
  )
)
