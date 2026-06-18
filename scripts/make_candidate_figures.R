library(jsonlite)
library(ggplot2)

dir.create("figures/result_candidates", recursive = TRUE, showWarnings = FALSE)

geo <- fromJSON("outputs/result_candidates/selected_tracts_fire_map.geojson", simplifyVector = FALSE)
poly_rows <- list()
centroid_rows <- list()
fire <- NULL
idx <- 1

for (feat in geo$features) {
  props <- feat$properties
  geom <- feat$geometry
  if (geom$type == "Point") {
    fire <- data.frame(lon = geom$coordinates[[1]], lat = geom$coordinates[[2]], name = props$name)
  } else {
    geoid <- props$GEOID
    dist <- props$distance_to_nearest_fire_km
    centroid_rows[[length(centroid_rows) + 1]] <- data.frame(
      geoid = geoid,
      lon = as.numeric(props$CENTLON),
      lat = as.numeric(props$CENTLAT),
      distance = dist
    )
    polygons <- if (geom$type == "Polygon") list(geom$coordinates) else geom$coordinates
    part <- 1
    for (poly in polygons) {
      ring <- poly[[1]]
      coords <- do.call(rbind, lapply(ring, function(x) c(as.numeric(x[[1]]), as.numeric(x[[2]]))))
      poly_rows[[idx]] <- data.frame(
        lon = coords[, 1],
        lat = coords[, 2],
        group = paste0(geoid, "_", part),
        geoid = geoid,
        distance = dist
      )
      idx <- idx + 1
      part <- part + 1
    }
  }
}

poly_df <- do.call(rbind, poly_rows)
centroids <- do.call(rbind, centroid_rows)
qs <- quantile(centroids$distance, probs = c(1 / 3, 2 / 3), na.rm = TRUE)
poly_df$distance_group <- ifelse(poly_df$distance <= qs[[1]], "Near", ifelse(poly_df$distance <= qs[[2]], "Medium", "Far"))

map_plot <- ggplot() +
  geom_polygon(data = poly_df, aes(x = lon, y = lat, group = group, fill = distance_group), color = "white", linewidth = 0.25, alpha = 0.9) +
  geom_point(data = centroids, aes(x = lon, y = lat), color = "#111827", size = 1.2, alpha = 0.8) +
  geom_point(data = fire, aes(x = lon, y = lat), color = "#d73027", size = 4, shape = 8, stroke = 1.2) +
  annotate("text", x = fire$lon, y = fire$lat + 0.012, label = "Representative\nwildfire point", color = "#991b1b", size = 3.4, fontface = "bold") +
  coord_equal() +
  scale_fill_manual(values = c("Near" = "#fee8c8", "Medium" = "#fdbb84", "Far" = "#e34a33")) +
  labs(
    title = "Selected LA census tracts and representative wildfire point",
    subtitle = "Distance groups use tract centroids and an exploratory point near Griffith Park",
    x = "Longitude",
    y = "Latitude",
    fill = "Distance to fire"
  ) +
  theme_minimal(base_size = 12) +
  theme(plot.title = element_text(face = "bold", size = 15), panel.grid = element_line(color = "#eeeeee"), legend.position = "right")

ggsave("figures/result_candidates/selected_tracts_fire_map.png", map_plot, width = 8.5, height = 6.2, dpi = 160)

cm <- read.csv("outputs/result_candidates/cross_model_comparison_summary.csv")
metrics_keep <- c(
  "mode_feasibility_rate",
  "soft_feasibility_issue_rate",
  "spatial_inconsistency_rate",
  "no_vehicle_violation_or_spatial_inconsistency_rate",
  "limited_transit_public_transit_rate",
  "lower_income_public_shelter_rate"
)
cm <- cm[cm$metric %in% metrics_keep, ]
cm$metric_label <- factor(
  cm$metric,
  levels = metrics_keep,
  labels = c("Mode feasible", "Soft issue", "Spatial inconsistency", "No-vehicle risk", "Limited-transit public transit", "Lower-income shelter")
)
cm$model_condition <- paste(cm$model, cm$condition, sep = "\n")

heatmap_plot <- ggplot(cm, aes(x = model_condition, y = metric_label, fill = value_percent)) +
  geom_tile(color = "white", linewidth = 0.5) +
  geom_text(aes(label = paste0(sprintf("%.1f", value_percent), "%")), size = 3.1) +
  scale_fill_gradient(low = "#f7fbff", high = "#08519c", limits = c(0, 100), name = "Rate") +
  labs(
    title = "Cross-model candidate metrics",
    subtitle = "Existing GPT-4.1-mini subset vs gpt-4o-mini validation subset",
    x = NULL,
    y = NULL
  ) +
  theme_minimal(base_size = 11) +
  theme(axis.text.x = element_text(angle = 25, hjust = 1), plot.title = element_text(face = "bold", size = 15), panel.grid = element_blank())

ggsave("figures/result_candidates/cross_model_heatmap.png", heatmap_plot, width = 9, height = 5.5, dpi = 160)

income <- read.csv("outputs/result_candidates/income_group_analysis.csv")
income_long <- rbind(
  data.frame(group = income$group, condition = income$condition, metric = "Violation / spatial inconsistency", value = income$violation_or_spatial_inconsistency_rate),
  data.frame(group = income$group, condition = income$condition, metric = "Soft issue", value = income$soft_feasibility_issue_rate),
  data.frame(group = income$group, condition = income$condition, metric = "Public shelter", value = income$public_shelter_destination_rate),
  data.frame(group = income$group, condition = income$condition, metric = "Hotel / motel", value = income$hotel_motel_destination_rate)
)
income_long$group <- factor(income_long$group, levels = c("lower_income", "higher_income"), labels = c("Lower income", "Higher income"))
income_long$condition <- factor(income_long$condition, levels = c("baseline", "spatial_grounded"), labels = c("Baseline", "Spatially grounded"))

income_plot <- ggplot(income_long, aes(x = group, y = value, fill = condition)) +
  geom_col(position = position_dodge(width = .72), width = .62) +
  geom_text(aes(label = paste0(sprintf("%.1f", value), "%")), position = position_dodge(width = .72), vjust = -.35, size = 3) +
  facet_wrap(~ metric, ncol = 2) +
  scale_fill_manual(values = c("Baseline" = "#6baed6", "Spatially grounded" = "#f28e2b")) +
  scale_y_continuous(limits = c(0, 105), labels = function(x) paste0(x, "%")) +
  labs(title = "Income subgroup candidate metrics", subtitle = "Existing GPT-4.1-mini main experiment; destination patterns are exploratory", x = NULL, y = "Rate", fill = NULL) +
  theme_minimal(base_size = 11) +
  theme(plot.title = element_text(face = "bold", size = 15), legend.position = "bottom", panel.grid.major.x = element_blank())

ggsave("figures/result_candidates/income_comparison_figure.png", income_plot, width = 8.5, height = 6.2, dpi = 160)

transit <- read.csv("outputs/result_candidates/no_vehicle_transit_access_analysis.csv")
transit_long <- rbind(
  data.frame(condition = transit$condition, metric = "Violation / spatial inconsistency", value = transit$violation_or_spatial_inconsistency_rate),
  data.frame(condition = transit$condition, metric = "Public transit mode", value = transit$public_transit_mode_rate),
  data.frame(condition = transit$condition, metric = "Ride with family/friend", value = transit$ride_with_family_friend_rate),
  data.frame(condition = transit$condition, metric = "Public shelter destination", value = transit$public_shelter_destination_rate)
)
transit_long$condition <- factor(transit_long$condition, levels = c("baseline", "spatial_grounded"), labels = c("Baseline", "Spatially grounded"))

transit_plot <- ggplot(transit_long, aes(x = metric, y = value, fill = condition)) +
  geom_col(position = position_dodge(width = .72), width = .62) +
  geom_text(aes(label = paste0(sprintf("%.1f", value), "%")), position = position_dodge(width = .72), vjust = -.35, size = 3) +
  scale_fill_manual(values = c("Baseline" = "#6baed6", "Spatially grounded" = "#f28e2b")) +
  scale_y_continuous(limits = c(0, 105), labels = function(x) paste0(x, "%")) +
  labs(title = "No-vehicle + limited/no transit candidate metrics", subtitle = "Exploratory subgroup: n = 8 personas per condition", x = NULL, y = "Rate", fill = NULL) +
  theme_minimal(base_size = 11) +
  theme(plot.title = element_text(face = "bold", size = 15), axis.text.x = element_text(angle = 18, hjust = 1), legend.position = "bottom", panel.grid.major.x = element_blank())

ggsave("figures/result_candidates/transit_subgroup_figure.png", transit_plot, width = 8.5, height = 5.5, dpi = 160)
