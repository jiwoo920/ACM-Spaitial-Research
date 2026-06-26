library(ggplot2)

root_prefix <- if (file.exists("data/selected_la_tracts_map_polygons.csv")) "" else "project/"
data_dir <- paste0(root_prefix, "data")
out_dir <- paste0(root_prefix, "outputs")
fig_dir <- paste0(root_prefix, "figures")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

ink <- "#1F2430"
muted <- "#5D667A"
grid <- "#E7EAF0"
blue <- "#2E4780"
blue_light <- "#EAF1FE"
green <- "#4F9A58"
yellow <- "#E2B72E"
red <- "#C84C3A"
baseline_color <- "#6B8FD6"
spatial_color <- "#E68A5A"

theme_src <- function(base_size = 10) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 3, color = ink),
      plot.subtitle = element_text(size = base_size, color = muted, margin = margin(b = 8)),
      axis.title = element_text(color = ink),
      axis.text = element_text(color = muted),
      panel.grid.major = element_line(color = grid, linewidth = 0.28),
      panel.grid.minor = element_blank(),
      legend.position = "bottom",
      legend.title = element_blank(),
      legend.text = element_text(size = base_size - 1, color = ink),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(12, 14, 12, 14)
    )
}

save_plot <- function(plot, filename, width = 9, height = 5.5) {
  ggsave(file.path(fig_dir, filename), plot, width = width, height = height, dpi = 220, bg = "white")
}

pct <- function(x) paste0(sprintf("%.1f", x), "%")
bool_rate <- function(x) if (length(x) == 0) 0 else round(mean(x, na.rm = TRUE) * 100, 1)
write_md <- function(path, lines) writeLines(lines, path, useBytes = TRUE)

polys <- read.csv(file.path(data_dir, "selected_la_tracts_map_polygons.csv"))
background_path <- file.path(data_dir, "la_county_tract_background_outline.csv")
la_background <- if (file.exists(background_path)) read.csv(background_path) else NULL
centroids <- read.csv(file.path(data_dir, "selected_la_tracts_gis_distances.csv"))
shelters <- read.csv(file.path(data_dir, "candidate_shelter_service_points.csv"))
stops <- read.csv(file.path(data_dir, "la_metro_transit_stops_or_proxy.csv"))
responses <- read.csv(file.path(out_dir, "gis_enriched_llm_results.csv"))
audit <- read.csv(file.path(out_dir, "gis_label_audit.csv"))
tract_summary <- read.csv(file.path(out_dir, "tract_level_spatial_feasibility_summary.csv"))
shelter_summary <- read.csv(file.path(out_dir, "shelter_distance_inconsistency_summary.csv"))

responses$condition_label <- ifelse(responses$condition == "baseline", "Baseline", "Spatially grounded")
responses$condition_label <- factor(responses$condition_label, levels = c("Baseline", "Spatially grounded"))
responses$any_violation_or_spatial_inconsistency <- responses$any_violation == 1 | responses$spatial_inconsistency_count > 0
responses$no_vehicle <- tolower(responses$vehicle_access) == "no"
responses$public_transit_selected <- responses$transportation_mode == "Public transit"

fire <- data.frame(name = "Representative wildfire point", lat = 34.1366, lon = -118.2942)
map_breaks <- c(
  "Tract centroid",
  "Candidate service point",
  "Transit proxy",
  "Representative wildfire point"
)
nearest_stop_ids <- unique(centroids$nearest_transit_stop_id)
stops_nearest <- stops[stops$stop_id %in% nearest_stop_ids, ]
map_x <- range(c(polys$lon, shelters$lon, stops_nearest$stop_lon, fire$lon), na.rm = TRUE)
map_y <- range(c(polys$lat, shelters$lat, stops_nearest$stop_lat, fire$lat), na.rm = TRUE)
map_x <- map_x + c(-0.03, 0.03)
map_y <- map_y + c(-0.03, 0.03)

# 1. Polished spatial positioning map.
map_plot <- ggplot()
if (!is.null(la_background)) {
  map_plot <- map_plot +
    geom_path(
      data = la_background,
      aes(x = lon, y = lat, group = background_id),
      color = "#D4D9E2",
      linewidth = 0.08,
      alpha = 0.28
    )
}
map_plot <- map_plot +
  geom_polygon(
    data = polys,
    aes(x = lon, y = lat, group = interaction(GEOID, poly_id)),
    fill = blue_light,
    color = blue,
    linewidth = 0.28,
    alpha = 0.86
  ) +
  geom_point(
    data = centroids,
    aes(x = centroid_lon, y = centroid_lat, shape = "Tract centroid", fill = "Tract centroid", color = "Tract centroid"),
    size = 2.7,
    stroke = 0.35
  ) +
  geom_point(
    data = shelters,
    aes(x = lon, y = lat, shape = "Candidate service point", fill = "Candidate service point", color = "Candidate service point"),
    size = 3.0,
    stroke = 0.35
  ) +
  geom_point(
    data = stops_nearest,
    aes(x = stop_lon, y = stop_lat, shape = "Transit proxy", fill = "Transit proxy", color = "Transit proxy"),
    size = 2.9,
    stroke = 0.35
  ) +
  geom_point(
    data = fire,
    aes(x = lon, y = lat, shape = "Representative wildfire point", color = "Representative wildfire point"),
    fill = red,
    size = 4.0,
    stroke = 1.05
  ) +
  scale_shape_manual(breaks = map_breaks, values = c(
    "Tract centroid" = 21,
    "Candidate service point" = 24,
    "Transit proxy" = 22,
    "Representative wildfire point" = 8
  )) +
  scale_fill_manual(breaks = map_breaks, values = c(
    "Tract centroid" = blue,
    "Candidate service point" = green,
    "Transit proxy" = yellow,
    "Representative wildfire point" = red
  )) +
  scale_color_manual(breaks = map_breaks, values = c(
    "Tract centroid" = blue,
    "Candidate service point" = green,
    "Transit proxy" = "#9B7A00",
    "Representative wildfire point" = red
  )) +
  guides(
    shape = guide_legend(
      override.aes = list(
        fill = c(blue, green, yellow, red),
        color = c(blue, green, "#9B7A00", red),
        size = c(3.0, 3.2, 3.1, 4.2)
      )
    ),
    fill = "none",
    color = "none"
  ) +
  coord_equal(xlim = map_x, ylim = map_y, expand = FALSE) +
  labs(
    title = "Selected LA County tracts and spatial proxy points",
    subtitle = "Tract centroids, representative wildfire point, candidate service points, and transit proxy locations",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_src(9) +
  theme(legend.position = "bottom")
save_plot(map_plot, "selected_tracts_fire_shelter_transit_map_polished.png", width = 8.2, height = 6.3)
save_plot(map_plot, "selected_tracts_fire_shelter_transit_map_polished_v2.png", width = 8.2, height = 6.3)

# 2. Simplified no-vehicle transit-risk figure.
nv <- responses[responses$no_vehicle, ]
nv$stop_distance_group <- ifelse(
  nv$transit_stop_access_group %in% c("far", "no nearby stop"),
  "far/no nearby transit-stop proxy",
  "near/moderate transit-stop proxy"
)
nv$stop_distance_group <- factor(
  nv$stop_distance_group,
  levels = c("near/moderate transit-stop proxy", "far/no nearby transit-stop proxy")
)
nv_summary <- aggregate(
  any_violation_or_spatial_inconsistency ~ condition_label + stop_distance_group,
  data = nv,
  FUN = function(x) c(rate = bool_rate(x), n = length(x))
)
nv_plot <- data.frame(
  condition_label = nv_summary$condition_label,
  stop_distance_group = nv_summary$stop_distance_group,
  rate = nv_summary$any_violation_or_spatial_inconsistency[, "rate"],
  n = nv_summary$any_violation_or_spatial_inconsistency[, "n"]
)
nv_plot$label <- paste0(pct(nv_plot$rate), "\n", "n=", nv_plot$n)
write.csv(nv_plot, file.path(out_dir, "no_vehicle_transit_proxy_risk_simple.csv"), row.names = FALSE)
nv_plot_v2 <- nv_plot
nv_plot_v2$stop_distance_group <- ifelse(
  nv_plot_v2$stop_distance_group == "near/moderate transit-stop proxy",
  "Near/Moderate Proximity",
  "Transit Desert (Far/No Stop)"
)
nv_plot_v2$stop_distance_group <- factor(
  nv_plot_v2$stop_distance_group,
  levels = c("Near/Moderate Proximity", "Transit Desert (Far/No Stop)")
)
write.csv(nv_plot_v2, file.path(out_dir, "no_vehicle_transit_proxy_risk_simple_v2.csv"), row.names = FALSE)

simple_nv_plot <- ggplot(nv_plot, aes(x = stop_distance_group, y = rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.58, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = label),
    position = position_dodge(width = 0.72),
    vjust = -0.18,
    size = 3.0,
    color = ink,
    lineheight = 0.9
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 116), breaks = seq(0, 100, 25), labels = function(x) paste0(x, "%")) +
  labs(
    title = "No-vehicle feasibility risk by transit-stop proximity proxy",
    subtitle = "Tract-centroid proxy analysis; not route-level reachability",
    x = NULL,
    y = "Violation / spatial-inconsistency rate"
  ) +
  theme_src(10)
save_plot(simple_nv_plot, "no_vehicle_transit_proxy_risk_simple.png", width = 8.0, height = 5.2)

annot <- nv_plot_v2[
  nv_plot_v2$condition_label == "Spatially grounded" &
    nv_plot_v2$stop_distance_group == "Transit Desert (Far/No Stop)",
]
simple_nv_plot_v2 <- ggplot(nv_plot_v2, aes(x = stop_distance_group, y = rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.54, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = label),
    position = position_dodge(width = 0.7),
    vjust = -0.18,
    size = 3.2,
    color = ink,
    lineheight = 0.9
  ) +
  geom_label(
    data = annot,
    aes(x = stop_distance_group, y = 120, label = "Persistently High Risk"),
    inherit.aes = FALSE,
    color = red,
    fill = "white",
    linewidth = 0,
    fontface = "bold",
    size = 3.1
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 128), breaks = seq(0, 100, 25), labels = function(x) paste0(x, "%")) +
  labs(
    title = "No-vehicle feasibility risk by transit-stop proximity proxy",
    subtitle = "Tract-centroid proxy analysis; not route-level reachability",
    x = NULL,
    y = "Violation / spatial inconsistency rate (%)"
  ) +
  theme_src(10) +
  theme(axis.text.x = element_text(size = 10, color = muted))
save_plot(simple_nv_plot_v2, "no_vehicle_transit_proxy_risk_simple_v2.png", width = 8.0, height = 5.15)

# 3. Polished tract-level risk map.
risk_polys <- merge(polys, tract_summary, by = "GEOID")
risk_map <- ggplot(risk_polys, aes(x = lon, y = lat, group = interaction(GEOID, poly_id))) +
  geom_polygon(aes(fill = violation_spatial_inconsistency_rate), color = blue, linewidth = 0.28) +
  geom_point(data = centroids, aes(x = centroid_lon, y = centroid_lat), inherit.aes = FALSE, size = 1.25, color = ink, alpha = 0.78) +
  geom_point(data = fire, aes(x = lon, y = lat), inherit.aes = FALSE, shape = 8, size = 4.0, stroke = 1.1, color = red) +
  scale_fill_gradient(low = "#F2F6FE", high = red, limits = c(0, 100), labels = function(x) paste0(x, "%")) +
  coord_equal() +
  labs(
    title = "LLM feasibility risk across selected LA County tracts",
    subtitle = "Violation/spatial-inconsistency rate aggregated from 400 GIS-enriched responses",
    x = "Longitude",
    y = "Latitude",
    fill = "Risk rate"
  ) +
  theme_src(9) +
  theme(legend.position = "right")
save_plot(risk_map, "tract_level_feasibility_risk_map_polished.png", width = 8.0, height = 6.2)

# 4. Transit distance vs feasibility risk scatter.
tract_no_vehicle <- aggregate(no_vehicle ~ GEOID, data = responses, FUN = sum)
names(tract_no_vehicle)[2] <- "no_vehicle_responses"
scatter_summary <- merge(tract_summary, tract_no_vehicle, by = "GEOID", all.x = TRUE)
scatter_summary$no_vehicle_responses[is.na(scatter_summary$no_vehicle_responses)] <- 0
scatter_summary <- scatter_summary[order(-scatter_summary$violation_spatial_inconsistency_rate), ]
write.csv(scatter_summary, file.path(out_dir, "transit_distance_vs_feasibility_risk_summary.csv"), row.names = FALSE)

scatter_plot <- ggplot(
  scatter_summary,
  aes(
    x = nearest_transit_stop_distance_km,
    y = violation_spatial_inconsistency_rate,
    size = no_vehicle_responses
  )
) +
  geom_point(shape = 21, fill = baseline_color, color = ink, alpha = 0.82, stroke = 0.35) +
  scale_size_continuous(range = c(2.5, 7.5), breaks = c(4, 6, 8, 10), name = "No-vehicle responses") +
  scale_y_continuous(limits = c(0, 105), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Transit-stop distance vs. tract-level feasibility risk",
    subtitle = "One point per tract; exploratory proxy analysis, not causal evidence",
    x = "Nearest transit-stop proxy distance (km)",
    y = "Violation / spatial-inconsistency rate"
  ) +
  theme_src(10) +
  theme(legend.position = "right")
save_plot(scatter_plot, "transit_distance_vs_feasibility_risk_scatter.png", width = 8.0, height = 5.4)

# 5. GIS label audit figures.
audit$original_transit_access <- factor(audit$original_transit_access, levels = c("Good", "Moderate", "Limited", "None"))
audit_transit <- ggplot(audit, aes(x = original_transit_access, y = nearest_transit_stop_distance_km)) +
  geom_boxplot(width = 0.56, fill = "#EAF1FE", color = blue, outlier.shape = NA) +
  geom_jitter(width = 0.12, height = 0, size = 2.3, shape = 21, fill = yellow, color = ink, alpha = 0.86) +
  labs(
    title = "Original transit labels vs. transit-stop proxy distance",
    subtitle = "Proxy comparison audits approximate labels; not route-level reachability",
    x = "Original transit access label",
    y = "Nearest transit-stop proxy distance (km)"
  ) +
  theme_src(10)
save_plot(audit_transit, "gis_label_audit_transit.png", width = 7.4, height = 5.0)
audit_transit_boxplot <- audit_transit +
  labs(
    title = "Transit prompt labels vs. GIS stop-proximity proxy",
    subtitle = "Exploratory GIS-supported audit; not route-level reachability",
    x = "Original prompt transit label",
    y = "Nearest transit-stop proxy distance (km)"
  )
save_plot(audit_transit_boxplot, "gis_label_audit_transit_boxplot.png", width = 7.4, height = 5.0)

audit$original_shelter_prompt_label <- cut(
  audit$original_shelter_distance_km,
  breaks = c(-Inf, 4, 8, Inf),
  labels = c("Original Near", "Original Moderate", "Original Far")
)
audit$original_shelter_prompt_label <- factor(
  audit$original_shelter_prompt_label,
  levels = c("Original Near", "Original Moderate", "Original Far")
)
audit$shelter_distance_group <- factor(audit$shelter_distance_group, levels = c("near", "medium", "far"))
audit_shelter <- ggplot(audit, aes(x = shelter_distance_group, y = nearest_candidate_shelter_distance_km)) +
  geom_boxplot(width = 0.56, fill = "#EDF7EA", color = green, outlier.shape = NA) +
  geom_jitter(width = 0.12, height = 0, size = 2.3, shape = 24, fill = green, color = ink, alpha = 0.86) +
  labs(
    title = "Shelter-distance labels vs. candidate service distance",
    subtitle = "Candidate shelter/service proximity proxy; not verified shelter reachability",
    x = "GIS-derived candidate service distance group",
    y = "Nearest candidate service distance (km)"
  ) +
  theme_src(10)
save_plot(audit_shelter, "gis_label_audit_shelter.png", width = 7.4, height = 5.0)
audit_shelter_boxplot <- ggplot(audit, aes(x = original_shelter_prompt_label, y = nearest_candidate_shelter_distance_km)) +
  geom_boxplot(width = 0.56, fill = "#EDF7EA", color = green, outlier.shape = NA) +
  geom_jitter(width = 0.12, height = 0, size = 2.3, shape = 24, fill = green, color = ink, alpha = 0.86) +
  labs(
    title = "Shelter prompt labels vs. candidate service proximity",
    subtitle = "Candidate shelter/service proximity proxy; not verified shelter reachability",
    x = "Original prompt shelter-distance label",
    y = "Nearest candidate service distance (km)"
  ) +
  theme_src(10)
save_plot(audit_shelter_boxplot, "gis_label_audit_shelter_boxplot.png", width = 7.8, height = 5.0)

audit$wildfire_risk_level <- factor(audit$wildfire_risk_level, levels = c("Low", "Moderate", "High"))
audit_fire <- ggplot(audit, aes(x = wildfire_risk_level, y = distance_to_fire_km)) +
  geom_boxplot(width = 0.56, fill = "#FCEEE9", color = red, outlier.shape = NA) +
  geom_jitter(width = 0.12, height = 0, size = 2.3, shape = 21, fill = red, color = ink, alpha = 0.82) +
  labs(
    title = "Wildfire-risk labels vs. representative fire distance",
    subtitle = "Representative wildfire point; not an active fire perimeter",
    x = "Original wildfire risk label",
    y = "Distance to representative fire point (km)"
  ) +
  theme_src(10)
save_plot(audit_fire, "gis_label_audit_fire.png", width = 7.4, height = 5.0)
audit_fire_boxplot <- audit_fire +
  labs(
    title = "Wildfire prompt labels vs. representative fire distance",
    subtitle = "Representative wildfire point; not an active fire perimeter",
    x = "Original prompt wildfire risk label",
    y = "Distance to representative fire point (km)"
  )
save_plot(audit_fire_boxplot, "gis_label_audit_fire_boxplot.png", width = 7.4, height = 5.0)

transit_mismatch_rate <- bool_rate(audit$transit_label_alignment == "potential_mismatch")
shelter_diff_mean <- round(mean(audit$shelter_distance_abs_difference_km, na.rm = TRUE), 2)
fire_diff_mean <- round(mean(audit$hazard_fire_distance_abs_difference_km, na.rm = TRUE), 2)
write_md(
  file.path(out_dir, "gis_label_audit_interpretation.md"),
  c(
    "# GIS Label Audit Interpretation",
    "",
    "This audit compares original approximate spatial labels with GIS-derived proxy distances from LA County tract centroids. It should be read as a spatial context extension rather than operational validation.",
    "",
    paste0("- Transit label audit: ", transit_mismatch_rate, "% of selected tracts are potential mismatches under the major transit-stop proximity proxy."),
    paste0("- Shelter distance audit: the mean absolute difference between original approximate shelter distance and nearest candidate service distance is ", shelter_diff_mean, " km."),
    paste0("- Fire distance audit: the mean absolute difference between original approximate hazard distance and representative fire-point distance is ", fire_diff_mean, " km."),
    "",
    "If a figure is used in the SRC paper, the safest wording is that GIS enrichment makes the spatial assumptions auditable. It does not prove route-level reachability, verified shelter access, active wildfire exposure, or operational evacuation feasibility."
  )
)
write_md(
  file.path(out_dir, "gis_label_audit_boxplot_interpretation.md"),
  c(
    "# GIS Label Audit Boxplot Interpretation",
    "",
    "These boxplots compare original approximate prompt labels with GIS-derived tract-centroid proxy distances. They are an exploratory GIS-supported audit, not operational validation.",
    "",
    paste0("- Transit prompt labels show ", transit_mismatch_rate, "% potential mismatch under the major transit-stop proximity proxy. This suggests partial alignment but also supports treating GIS enrichment as a spatial context extension."),
    paste0("- Shelter prompt labels have a mean absolute difference of ", shelter_diff_mean, " km against nearest candidate shelter/service proximity. This should not be interpreted as verified shelter reachability."),
    paste0("- Wildfire risk labels are only weakly comparable to the representative fire-point distance; the mean absolute hazard/fire distance difference is ", fire_diff_mean, " km. This should not be interpreted as active wildfire exposure."),
    "",
    "Safe claim: the GIS audit makes approximate spatial assumptions visible and partially checkable. Avoid claiming route-level reachability, verified wildfire evacuation shelters, active wildfire perimeters, or operational evacuation feasibility."
  )
)

# 6. Simplified nearby shelter claim figure.
shelter_summary$condition <- factor(shelter_summary$condition, levels = c("Baseline", "Spatially grounded"))
shelter_summary$shelter_distance_group <- factor(shelter_summary$shelter_distance_group, levels = c("near", "medium", "far"))
shelter_simple <- ggplot(shelter_summary, aes(x = shelter_distance_group, y = nearby_shelter_claim_rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.58, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = pct(nearby_shelter_claim_rate)),
    position = position_dodge(width = 0.72),
    vjust = -0.28,
    size = 3.0,
    color = ink
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, max(10, max(shelter_summary$nearby_shelter_claim_rate) + 12)), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Nearby-shelter claims by candidate service proximity",
    subtitle = "Candidate shelter/service proximity proxy; not verified shelter reachability",
    x = "Candidate service distance group",
    y = "Nearby-shelter claim rate"
  ) +
  theme_src(10)
save_plot(shelter_simple, "nearby_shelter_claim_by_distance_simple.png", width = 8.0, height = 5.1)

# 7. Recommendation updates.
ranking_lines <- c(
  "# GIS Result Candidate Ranking",
  "",
  "This ranking uses only the existing 400-response GPT-4.1-mini dataset enriched with LA County Open Data tract geometries, tract centroids, a representative wildfire point, candidate shelter/service points, and transit-stop proximity proxies. No new LLM calls were made.",
  "",
  "## 1. Best Main SRC Figure Candidate",
  "",
  "**`project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`**",
  "",
  "This is the strongest paper-ready analytical figure. It directly answers whether mobility-constrained households remain risky under a transit-stop proximity proxy, uses a simple two-group comparison, includes n labels, and avoids the visual complexity of the earlier three-panel figure. It should be described as tract-centroid proxy analysis, not route-level reachability.",
  "",
  "## 2. Best Supporting Spatial Figure",
  "",
  "**`project/figures/selected_tracts_fire_shelter_transit_map_polished_v2.png`**",
  "",
  "This is the best SIGSPATIAL positioning figure. It shows selected LA County tracts, tract centroids, the representative wildfire point, candidate service points, and transit proxy locations with clearer marker styles and legend matching. It should supplement the main analytical result rather than replace it if only one figure can fit.",
  "",
  "## 3. Best Method/Audit Support",
  "",
  "**`project/figures/gis_label_audit_transit_boxplot.png`, `project/figures/gis_label_audit_shelter_boxplot.png`, and `project/figures/gis_label_audit_fire_boxplot.png`**",
  "",
  "The GIS label audit boxplots are useful for advisor review and methods support because they compare original prompt labels with GIS-derived proxy distances. They should be framed as an exploratory GIS-supported audit, not validation of operational accessibility or exposure.",
  "",
  "## 4. Best Exploratory Figure",
  "",
  "**`project/figures/transit_distance_vs_feasibility_risk_scatter.png`**",
  "",
  "This tract-level scatter is useful for exploratory spatial interpretation because it asks whether tracts farther from transit proxy points also show higher feasibility risk. It should not be framed causally and should not be used to claim route-level transit access.",
  "",
  "## 5. Additional Exploratory Checks",
  "",
  "- `project/figures/tract_level_feasibility_risk_map_polished.png`: useful if the paper needs a spatial risk map, but tract-level aggregation over synthetic personas should not be overread.",
  "- `project/figures/nearby_shelter_claim_by_distance_simple.png`: useful for reasoning/proxy consistency, but candidate service points are not verified wildfire shelters.",
  "- `project/figures/gis_label_audit_transit.png`, `project/figures/gis_label_audit_shelter.png`, and `project/figures/gis_label_audit_fire.png`: earlier audit variants kept for comparison; the boxplot `_boxplot.png` versions are clearer.",
  "",
  "## Not Recommended For 2-Page Main Result",
  "",
  "- `project/figures/fire_distance_reasoning_salience_bar.png`: evacuation decision and urgency are close to ceiling, so it is weaker as a main result.",
  "- The original multi-panel no-vehicle stop-distance figure: analytically useful, but too dense for the 2-page SRC abstract.",
  "- The v1 simplified figure without annotation: useful, but the v2 version is clearer for SRC.",
  "",
  "## Claims To Avoid",
  "",
  "- Do not claim actual route-level reachability.",
  "- Do not claim verified wildfire evacuation shelter access.",
  "- Do not call the representative fire point an active wildfire or verified perimeter.",
  "- Do not claim the LLM used exact GIS distances unless those values were included in the original prompt.",
  "- Do not claim GIS analysis proves operational evacuation feasibility.",
  "",
  "## Recommended SRC Framing",
  "",
  "Use the v2 simplified no-vehicle transit-risk figure as the main analytical result candidate. Use the v2 polished spatial positioning map if the abstract needs a stronger SIGSPATIAL visual signal. Use the GIS label audit boxplots as methods/advisor support. Keep shelter-claim, fire-distance, and scatter outputs as exploratory GIS-supported analyses."
)
write_md(file.path(out_dir, "gis_result_candidate_ranking.md"), ranking_lines)

index_lines <- c(
  "# GIS-Supported Output Index",
  "",
  "## Polished Main Candidate Figures",
  "",
  "- `project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`: v2 simplified no-vehicle feasibility risk by transit-stop proximity proxy, with percentage, n labels, and annotation.",
  "- `project/figures/selected_tracts_fire_shelter_transit_map_polished_v2.png`: v2 polished spatial positioning map with selected tracts and proxy points.",
  "- `project/figures/tract_level_feasibility_risk_map_polished.png`: polished tract-level risk map.",
  "",
  "## Additional Result Candidate Figures",
  "",
  "- `project/figures/transit_distance_vs_feasibility_risk_scatter.png`: tract-level scatter of transit-stop proxy distance against feasibility risk.",
  "- `project/figures/nearby_shelter_claim_by_distance_simple.png`: nearby-shelter claim rate by candidate service proximity.",
  "- `project/figures/gis_label_audit_transit.png`: original transit label versus nearest transit-stop proxy distance.",
  "- `project/figures/gis_label_audit_shelter.png`: candidate service distance audit figure.",
  "- `project/figures/gis_label_audit_fire.png`: wildfire-risk label versus representative fire-point distance.",
  "- `project/figures/gis_label_audit_transit_boxplot.png`: v2 transit label audit boxplot.",
  "- `project/figures/gis_label_audit_shelter_boxplot.png`: v2 shelter-distance label audit boxplot.",
  "- `project/figures/gis_label_audit_fire_boxplot.png`: v2 wildfire-risk label audit boxplot.",
  "",
  "## New Tables And Interpretation Files",
  "",
  "- `project/outputs/no_vehicle_transit_proxy_risk_simple.csv`: source data for the simplified no-vehicle risk figure.",
  "- `project/outputs/no_vehicle_transit_proxy_risk_simple_v2.csv`: source data for the v2 simplified no-vehicle risk figure.",
  "- `project/outputs/transit_distance_vs_feasibility_risk_summary.csv`: tract-level source data for the scatter plot.",
  "- `project/outputs/gis_label_audit_interpretation.md`: interpretation of label/proxy alignment and limitations.",
  "- `project/outputs/gis_label_audit_boxplot_interpretation.md`: interpretation for the v2 audit boxplots.",
  "- `project/outputs/gis_result_candidate_ranking.md`: ranked recommendation for SRC use.",
  "",
  "## Existing GIS-Enriched Tables Kept In Use",
  "",
  "- `project/outputs/gis_enriched_llm_results.csv`: one row per existing LLM response with GIS variables merged in.",
  "- `project/outputs/mode_proxy_feasibility_by_response.csv`: response-level transportation proxy feasibility flags.",
  "- `project/outputs/mode_proxy_feasibility_summary.csv`: condition-level mode proxy feasibility rates.",
  "- `project/outputs/shelter_claim_proxy_check_by_response.csv`: nearby-shelter claim proxy checks.",
  "- `project/outputs/shelter_distance_inconsistency_summary.csv`: shelter-distance group summary metrics.",
  "- `project/outputs/fire_distance_reasoning_by_response.csv`: fire/hazard/distance reasoning keyword checks.",
  "- `project/outputs/fire_distance_reasoning_summary.csv`: representative fire-distance group summary metrics.",
  "- `project/outputs/tract_level_spatial_feasibility_summary.csv`: tract-level aggregated feasibility metrics.",
  "- `project/outputs/tract_level_spatial_feasibility_summary.geojson`: tract geometry with aggregated risk metrics for mapping.",
  "",
  "## Interpretation Boundary",
  "",
  "These outputs strengthen spatial positioning and make assumptions auditable. They do not prove route-level reachability, verified wildfire shelter access, active wildfire exposure, or operational evacuation feasibility."
)
write_md(file.path(out_dir, "gis_supported_output_index.md"), index_lines)
