library(ggplot2)

root_prefix <- if (file.exists("outputs/gis_enriched_llm_results.csv")) "" else "project/"
out_dir <- paste0(root_prefix, "outputs")
fig_dir <- paste0(root_prefix, "figures")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

ink <- "#1F2430"
muted <- "#5D667A"
grid_col <- "#E7EAF0"
baseline_color <- "#6B8FD6"
spatial_color <- "#E68A5A"

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
      legend.text = element_text(color = ink),
      strip.text = element_text(face = "bold", color = ink),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(12, 14, 12, 14)
    )
}

rate <- function(x) if (length(x) == 0) 0 else round(mean(x, na.rm = TRUE) * 100, 1)
pct <- function(x) paste0(sprintf("%.1f", x), "%")
write_md <- function(path, lines) writeLines(lines, path, useBytes = TRUE)

responses <- read.csv(file.path(out_dir, "gis_enriched_llm_results.csv"))
responses$condition_label <- ifelse(responses$condition == "baseline", "Baseline", "Spatially grounded")
responses$condition_label <- factor(responses$condition_label, levels = c("Baseline", "Spatially grounded"))
responses$no_vehicle <- tolower(responses$vehicle_access) == "no"
responses$any_violation_or_spatial_inconsistency <- responses$any_violation == 1 | responses$spatial_inconsistency_count > 0
responses$public_transit_selected <- responses$transportation_mode == "Public transit"
responses$private_vehicle_without_vehicle <- responses$transportation_mode == "Private vehicle" & responses$no_vehicle
responses$walking_long_shelter <- responses$transportation_mode == "Walk" & responses$nearest_candidate_shelter_distance_km > 2

no_vehicle <- responses[responses$no_vehicle, ]
cutoffs <- c(1.0, 1.5, 2.0)
rows <- list()

for (cutoff in cutoffs) {
  df <- no_vehicle
  df$threshold_group <- ifelse(
    df$nearest_transit_stop_distance_km <= cutoff,
    paste0("Within ", cutoff, " km"),
    paste0("Beyond ", cutoff, " km")
  )
  df$threshold_group <- factor(df$threshold_group, levels = c(paste0("Within ", cutoff, " km"), paste0("Beyond ", cutoff, " km")))
  df$mode_proxy_issue_at_cutoff <- df$private_vehicle_without_vehicle |
    (df$public_transit_selected & df$nearest_transit_stop_distance_km > cutoff) |
    df$walking_long_shelter

  grouped <- aggregate(
    cbind(
      any_violation_or_spatial_inconsistency,
      public_transit_selected,
      mode_proxy_issue_at_cutoff
    ) ~ condition_label + threshold_group,
    data = df,
    FUN = function(x) c(rate = rate(x), n = length(x))
  )
  for (i in seq_len(nrow(grouped))) {
    rows[[length(rows) + 1]] <- data.frame(
      cutoff_km = cutoff,
      condition = grouped$condition_label[i],
      threshold_group = as.character(grouped$threshold_group[i]),
      n = grouped$any_violation_or_spatial_inconsistency[i, "n"],
      violation_spatial_inconsistency_rate = grouped$any_violation_or_spatial_inconsistency[i, "rate"],
      public_transit_recommendation_rate = grouped$public_transit_selected[i, "rate"],
      mode_proxy_issue_rate = grouped$mode_proxy_issue_at_cutoff[i, "rate"]
    )
  }
}

sensitivity <- do.call(rbind, rows)
sensitivity$condition <- factor(sensitivity$condition, levels = c("Baseline", "Spatially grounded"))
sensitivity$cutoff_label <- paste0(sensitivity$cutoff_km, " km cutoff")
sensitivity$cutoff_label <- factor(sensitivity$cutoff_label, levels = paste0(cutoffs, " km cutoff"))
sensitivity$threshold_group <- factor(
  sensitivity$threshold_group,
  levels = unique(unlist(lapply(cutoffs, function(cutoff) c(paste0("Within ", cutoff, " km"), paste0("Beyond ", cutoff, " km")))))
)
write.csv(sensitivity, file.path(out_dir, "transit_proxy_threshold_sensitivity.csv"), row.names = FALSE)

plot_data <- sensitivity
plot_data$metric <- "Violation / spatial inconsistency"
plot_data$rate <- plot_data$violation_spatial_inconsistency_rate
plot_data2 <- sensitivity
plot_data2$metric <- "Mode proxy issue"
plot_data2$rate <- plot_data2$mode_proxy_issue_rate
plot_data3 <- sensitivity
plot_data3$metric <- "Public transit selected"
plot_data3$rate <- plot_data3$public_transit_recommendation_rate
long <- rbind(plot_data, plot_data2, plot_data3)
long$metric <- factor(long$metric, levels = c("Violation / spatial inconsistency", "Mode proxy issue", "Public transit selected"))
long$label <- paste0(pct(long$rate), "\n", "n=", long$n)

p <- ggplot(long, aes(x = threshold_group, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.58, color = ink, linewidth = 0.22) +
  facet_grid(metric ~ cutoff_label, scales = "free_x", space = "free_x") +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), breaks = seq(0, 100, 25), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Transit proxy threshold sensitivity for no-vehicle households",
    subtitle = "Exploratory transit-stop proximity proxy; not route-level reachability",
    x = "Distance group under threshold",
    y = "Rate (%)"
  ) +
  theme_src(8) +
  theme(
    axis.text.x = element_text(angle = 28, hjust = 1, size = 7),
    panel.spacing.x = unit(0.8, "lines"),
    panel.spacing.y = unit(0.55, "lines")
  )
ggsave(file.path(fig_dir, "transit_proxy_threshold_sensitivity.png"), p, width = 11.5, height = 7.2, dpi = 220, bg = "white")

main_cutoff <- sensitivity[sensitivity$cutoff_km == 1.5, ]
beyond_main <- main_cutoff[grepl("^Beyond", main_cutoff$threshold_group), ]
alt_1 <- sensitivity[sensitivity$cutoff_km == 1.0 & grepl("^Beyond", sensitivity$threshold_group), ]
alt_2 <- sensitivity[sensitivity$cutoff_km == 2.0 & grepl("^Beyond", sensitivity$threshold_group), ]

write_md(
  file.path(out_dir, "transit_proxy_threshold_definition.md"),
  c(
    "# Transit-Stop Proximity Threshold Definition",
    "",
    "This memo documents the threshold used to group tract-centroid distance to transit-stop proxy points. The current transit layer uses major transit-stop proxy points rather than full GTFS `stops.txt`, so all results should be described as an exploratory transit-stop proximity proxy, not full transit accessibility or route-level reachability.",
    "",
    "## Working Definition",
    "",
    "- Near: `nearest_transit_stop_distance_km <= 0.5 km`.",
    "- Moderate: `0.5 < nearest_transit_stop_distance_km <= 1.5 km`.",
    "- Far: `nearest_transit_stop_distance_km > 1.5 km`.",
    "- No nearby stop: no transit proxy within 2 km.",
    "- Simplified figure grouping: Near + Moderate are combined as `Near/Moderate Proximity`; Far + No nearby stop are combined as `Transit-Desert Proxy`.",
    "",
    "## Why the Main Figure Uses 1.5 km",
    "",
    "The 1.5 km cutoff is a conservative walking-proximity threshold for a lightweight tract-centroid audit. It is wide enough to avoid treating every tract-centroid offset as inaccessible, but still separates tracts with clearly distant major transit proxy points. Because these are major transit-stop proxy points rather than full GTFS stops, the cutoff should not be interpreted as a formal transit-accessibility standard.",
    "",
    "## Sensitivity Check",
    "",
    "The sensitivity output recalculates no-vehicle household groups at 1.0 km, 1.5 km, and 2.0 km cutoffs. For each cutoff, the audit reports n per group, violation/spatial-inconsistency rate, public-transit recommendation rate, and mode proxy issue rate by condition.",
    "",
    paste0("- At the main 1.5 km cutoff, the beyond-threshold group has n = ", paste(beyond_main$n, collapse = "/"), " responses across baseline/spatially grounded cells, with violation/spatial-inconsistency rates of ", paste(pct(beyond_main$violation_spatial_inconsistency_rate), collapse = " and "), "."),
    paste0("- At the stricter 1.0 km cutoff, the beyond-threshold group remains high risk, with violation/spatial-inconsistency rates of ", paste(pct(alt_1$violation_spatial_inconsistency_rate), collapse = " and "), "."),
    paste0("- At the looser 2.0 km cutoff, only the clearest distant-proxy cases remain beyond-threshold, with violation/spatial-inconsistency rates of ", paste(pct(alt_2$violation_spatial_inconsistency_rate), collapse = " and "), "."),
    "",
    "## Interpretation",
    "",
    "The conclusion does not depend on treating 1.5 km as an exact accessibility boundary: no-vehicle households remain a high-risk group under all tested thresholds. What changes is the size of the beyond-threshold subgroup. Therefore, the main claim should be framed as threshold-sensitive exploratory screening: transit-stop proximity proxies help audit feasibility risks, but they do not prove actual route-level reachability.",
    "",
    "## Claims To Avoid",
    "",
    "- Do not claim route-level reachability.",
    "- Do not claim full transit accessibility.",
    "- Do not claim the LLM used exact GIS distances unless those distances were in the prompt.",
    "- Do not claim operational evacuation feasibility."
  )
)
