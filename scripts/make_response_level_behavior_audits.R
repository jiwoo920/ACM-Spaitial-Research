library(ggplot2)
library(grid)

root_prefix <- if (file.exists("outputs/gis_enriched_llm_results.csv")) "" else "project/"
data_dir <- paste0(root_prefix, "data")
out_dir <- paste0(root_prefix, "outputs")
fig_dir <- paste0(root_prefix, "figures")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)
dir.create(fig_dir, showWarnings = FALSE, recursive = TRUE)

ink <- "#1F2430"
muted <- "#5D667A"
grid_col <- "#E7EAF0"
blue <- "#2E4780"
blue_light <- "#EAF1FE"
green <- "#4F9A58"
yellow <- "#E2B72E"
red <- "#C84C3A"
baseline_color <- "#6B8FD6"
spatial_color <- "#E68A5A"

theme_audit <- function(base_size = 10) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 3, color = ink),
      plot.subtitle = element_text(size = base_size, color = muted, margin = margin(b = 8)),
      axis.title = element_text(color = ink),
      axis.text = element_text(color = muted),
      panel.grid.major = element_line(color = grid_col, linewidth = 0.28),
      panel.grid.minor = element_blank(),
      legend.position = "bottom",
      legend.title = element_text(color = ink),
      legend.text = element_text(color = ink),
      strip.text = element_text(face = "bold", color = ink),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(12, 14, 12, 14)
    )
}

pct <- function(x) paste0(sprintf("%.1f", x), "%")
rate <- function(x) if (length(x) == 0) 0 else round(mean(x, na.rm = TRUE) * 100, 1)
write_md <- function(path, lines) writeLines(lines, path, useBytes = TRUE)

save_plot <- function(plot, filename, width = 9, height = 5.5) {
  ggsave(file.path(fig_dir, filename), plot, width = width, height = height, dpi = 220, bg = "white")
}

responses <- read.csv(file.path(out_dir, "gis_enriched_llm_results.csv"))
shelter_claims <- read.csv(file.path(out_dir, "shelter_claim_proxy_check_by_response.csv"))
mode_proxy <- read.csv(file.path(out_dir, "mode_proxy_feasibility_by_response.csv"))
polys <- read.csv(file.path(data_dir, "selected_la_tracts_map_polygons.csv"))
background_path <- file.path(data_dir, "la_county_tract_background_outline.csv")
la_background <- if (file.exists(background_path)) read.csv(background_path) else NULL
centroids <- read.csv(file.path(data_dir, "selected_la_tracts_gis_distances.csv"))
shelters <- read.csv(file.path(data_dir, "candidate_shelter_service_points.csv"))
stops <- read.csv(file.path(data_dir, "la_metro_transit_stops_or_proxy.csv"))
tract_summary <- read.csv(file.path(out_dir, "tract_level_spatial_feasibility_summary.csv"))

responses$condition_label <- ifelse(responses$condition == "baseline", "Baseline", "Spatially grounded")
responses$condition_label <- factor(responses$condition_label, levels = c("Baseline", "Spatially grounded"))
responses$no_vehicle <- tolower(responses$vehicle_access) == "no"
responses$any_violation_or_spatial_inconsistency <- responses$any_violation == 1 | responses$spatial_inconsistency_count > 0
responses$prompt_transit_group <- ifelse(
  responses$transit_access %in% c("Good", "Moderate"),
  "Good/Moderate Transit Access",
  "Limited/No Transit Access"
)
responses$prompt_transit_group <- factor(
  responses$prompt_transit_group,
  levels = c("Good/Moderate Transit Access", "Limited/No Transit Access")
)
responses$gis_transit_group <- ifelse(
  responses$transit_stop_access_group %in% c("far", "no nearby stop"),
  "Transit Desert (Far/No Stop)",
  "Near/Moderate Transit Proximity"
)
responses$gis_transit_group <- factor(
  responses$gis_transit_group,
  levels = c("Near/Moderate Transit Proximity", "Transit Desert (Far/No Stop)")
)
mode_levels <- c("Public Transit", "Ride with family/friend", "Walking", "Taxi/Uber", "Other")
responses$transport_mode_group <- ifelse(
  responses$transportation_mode == "Public transit", "Public Transit",
  ifelse(
    responses$transportation_mode == "Ride with family/friend", "Ride with family/friend",
    ifelse(responses$transportation_mode == "Walk", "Walking", "Other")
  )
)
responses$transport_mode_group <- factor(responses$transport_mode_group, levels = mode_levels)

no_vehicle <- responses[responses$no_vehicle, ]

complete_mode_grid <- function(df, x_field) {
  out <- aggregate(
    run_id ~ condition_label + get(x_field) + transport_mode_group,
    data = df,
    FUN = length
  )
  names(out) <- c("condition", "x_group", "transportation_mode", "n")
  grid_df <- expand.grid(
    condition = levels(df$condition_label),
    x_group = levels(df[[x_field]]),
    transportation_mode = mode_levels,
    stringsAsFactors = FALSE
  )
  merged <- merge(grid_df, out, by = c("condition", "x_group", "transportation_mode"), all.x = TRUE)
  merged$n[is.na(merged$n)] <- 0
  totals <- aggregate(n ~ condition + x_group, data = merged, FUN = sum)
  names(totals)[3] <- "cell_total"
  merged <- merge(merged, totals, by = c("condition", "x_group"), all.x = TRUE)
  merged$percent <- ifelse(merged$cell_total > 0, round(merged$n / merged$cell_total * 100, 1), 0)
  merged$label <- ifelse(merged$n > 0, paste0(merged$n, " (", pct(merged$percent), ")"), "")
  merged$condition <- factor(merged$condition, levels = c("Baseline", "Spatially grounded"))
  merged$x_group <- factor(merged$x_group, levels = levels(df[[x_field]]))
  merged$transportation_mode <- factor(merged$transportation_mode, levels = rev(mode_levels))
  merged
}

# Task 1. Prompt-label transportation behavior.
prompt_behavior <- complete_mode_grid(no_vehicle, "prompt_transit_group")
write.csv(prompt_behavior, file.path(out_dir, "no_vehicle_prompt_label_transport_behavior.csv"), row.names = FALSE)

prompt_plot <- ggplot(prompt_behavior, aes(x = x_group, y = transportation_mode)) +
  geom_point(aes(size = n, fill = condition), shape = 21, color = ink, stroke = 0.28, alpha = 0.88) +
  geom_text(aes(label = ifelse(n >= 5, n, "")), size = 2.8, color = ink) +
  facet_wrap(~condition, nrow = 1) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_size_continuous(range = c(0, 11), breaks = c(5, 20, 40, 60), limits = c(0, max(prompt_behavior$n))) +
  scale_x_discrete(labels = c(
    "Good/Moderate Transit Access" = "Good/Moderate\nTransit Access",
    "Limited/No Transit Access" = "Limited/No\nTransit Access"
  )) +
  labs(
    title = "Prompt-label transportation behavior for no-vehicle households",
    subtitle = "Prompt-label sensitivity under original transit-access labels",
    x = "Original prompt transit label group",
    y = "LLM-selected transportation mode",
    size = "Responses",
    fill = NULL
  ) +
  theme_audit(9) +
  theme(axis.text.x = element_text(size = 8.4))
save_plot(prompt_plot, "no_vehicle_prompt_label_transport_behavior.png", width = 9.2, height = 5.4)

# Task 2. GIS-proxy transportation behavior and risk.
gis_behavior <- complete_mode_grid(no_vehicle, "gis_transit_group")
write.csv(gis_behavior, file.path(out_dir, "no_vehicle_gis_proxy_transport_behavior.csv"), row.names = FALSE)

gis_bubble <- ggplot(gis_behavior, aes(x = x_group, y = transportation_mode)) +
  geom_point(aes(size = n, fill = condition), shape = 21, color = ink, stroke = 0.28, alpha = 0.88) +
  geom_text(aes(label = ifelse(n >= 5, n, "")), size = 2.8, color = ink) +
  facet_wrap(~condition, nrow = 1) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_size_continuous(range = c(0, 11), breaks = c(5, 20, 40, 60), limits = c(0, max(gis_behavior$n))) +
  scale_x_discrete(labels = c(
    "Near/Moderate Transit Proximity" = "Near/Moderate\nTransit Proximity",
    "Transit Desert (Far/No Stop)" = "Transit Desert\n(Far/No Stop)"
  )) +
  labs(
    title = "GIS-proxy transportation behavior for no-vehicle households",
    subtitle = "Transit-stop proximity proxy; not route-level reachability",
    x = "Tract-centroid transit-stop proximity proxy",
    y = "LLM-selected transportation mode",
    size = "Responses",
    fill = NULL
  ) +
  theme_audit(9) +
  theme(axis.text.x = element_text(size = 8.4))
save_plot(gis_bubble, "no_vehicle_gis_proxy_transport_behavior_bubble.png", width = 9.2, height = 5.4)

risk <- aggregate(
  any_violation_or_spatial_inconsistency ~ condition_label + gis_transit_group,
  data = no_vehicle,
  FUN = function(x) c(rate = rate(x), n = length(x))
)
risk_plot_data <- data.frame(
  condition = risk$condition_label,
  gis_transit_group = risk$gis_transit_group,
  rate = risk$any_violation_or_spatial_inconsistency[, "rate"],
  n = risk$any_violation_or_spatial_inconsistency[, "n"]
)
risk_plot_data$label <- paste0(pct(risk_plot_data$rate), "\n", "n=", risk_plot_data$n)
risk_plot_data$condition <- factor(risk_plot_data$condition, levels = c("Baseline", "Spatially grounded"))
risk_plot_data$gis_transit_group <- factor(
  risk_plot_data$gis_transit_group,
  levels = c("Near/Moderate Transit Proximity", "Transit Desert (Far/No Stop)")
)

gis_risk_bar <- ggplot(risk_plot_data, aes(x = gis_transit_group, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.7), width = 0.54, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = label),
    position = position_dodge(width = 0.7),
    vjust = -0.18,
    size = 3.0,
    color = ink,
    lineheight = 0.9
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 116), breaks = seq(0, 100, 25), labels = function(x) paste0(x, "%")) +
  scale_x_discrete(labels = c(
    "Near/Moderate Transit Proximity" = "Near/Moderate\nTransit Proximity",
    "Transit Desert (Far/No Stop)" = "Transit Desert\n(Far/No Stop)"
  )) +
  labs(
    title = "GIS-proxy feasibility risk for no-vehicle households",
    subtitle = "Violation/spatial inconsistency under tract-centroid transit-stop proximity proxy",
    x = NULL,
    y = "Violation / spatial inconsistency rate (%)",
    fill = NULL
  ) +
  theme_audit(9) +
  theme(axis.text.x = element_text(size = 8.5))
save_plot(gis_risk_bar, "no_vehicle_gis_proxy_transport_risk_bar.png", width = 8.2, height = 5.1)

# Task 3. Spatial auditing map with mismatch callouts.
fire <- data.frame(name = "Representative wildfire point", lat = 34.1366, lon = -118.2942)
nearest_stop_ids <- unique(centroids$nearest_transit_stop_id)
stops_nearest <- stops[stops$stop_id %in% nearest_stop_ids, ]
map_x <- range(c(polys$lon, shelters$lon, stops_nearest$stop_lon, fire$lon), na.rm = TRUE) + c(-0.03, 0.03)
map_y <- range(c(polys$lat, shelters$lat, stops_nearest$stop_lat, fire$lat), na.rm = TRUE) + c(-0.03, 0.03)

mode_examples <- responses[
  responses$no_vehicle &
    responses$gis_transit_group == "Transit Desert (Far/No Stop)" &
    responses$transportation_mode == "Public transit",
]
mode_example <- mode_examples[order(-mode_examples$nearest_transit_stop_distance_km), ][1, ]
shelter_join <- merge(
  responses,
  shelter_claims[, c("run_id", "nearby_shelter_claim", "nearby_shelter_claim_proxy_issue")],
  by = "run_id",
  all.x = TRUE
)
shelter_join$nearby_shelter_claim <- tolower(as.character(shelter_join$nearby_shelter_claim)) == "true"
shelter_join$nearby_shelter_claim_proxy_issue <- tolower(as.character(shelter_join$nearby_shelter_claim_proxy_issue)) == "true"
shelter_examples <- shelter_join[
  shelter_join$nearby_shelter_claim == TRUE &
    shelter_join$shelter_distance_group == "far",
]
shelter_example <- shelter_examples[order(-shelter_examples$nearest_candidate_shelter_distance_km), ][1, ]
high_tract <- tract_summary[order(-tract_summary$violation_spatial_inconsistency_rate), ][1, ]

callouts <- data.frame(
  lon = c(mode_example$centroid_lon, shelter_example$centroid_lon, high_tract$centroid_lon),
  lat = c(mode_example$centroid_lat, shelter_example$centroid_lat, high_tract$centroid_lat),
  label = c(
    "Public transit\nrecommended;\nfar/no stop proxy",
    paste0("'Nearby shelter'\nclaim; service = ", sprintf("%.1f", shelter_example$nearest_candidate_shelter_distance_km), " km"),
    paste0("High tract risk:\n", sprintf("%.1f", high_tract$violation_spatial_inconsistency_rate), "%")
  ),
  nudge_x = c(-0.075, -0.035, 0.048),
  nudge_y = c(0.055, 0.085, -0.028)
)
map_x <- range(c(map_x, callouts$lon + callouts$nudge_x), na.rm = TRUE) + c(-0.03, 0.07)
map_y <- range(c(map_y, callouts$lat + callouts$nudge_y), na.rm = TRUE) + c(-0.025, 0.025)
segments <- data.frame(
  x = callouts$lon + callouts$nudge_x * 0.72,
  y = callouts$lat + callouts$nudge_y * 0.72,
  xend = callouts$lon,
  yend = callouts$lat
)

map_breaks <- c("Tract centroid", "Candidate service point", "Transit proxy", "Representative wildfire point")
audit_map <- ggplot()
if (!is.null(la_background)) {
  audit_map <- audit_map +
    geom_path(
      data = la_background,
      aes(x = lon, y = lat, group = background_id),
      color = "#D4D9E2",
      linewidth = 0.08,
      alpha = 0.22
    )
}
audit_map <- audit_map +
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
    size = 2.5,
    stroke = 0.35
  ) +
  geom_point(
    data = shelters,
    aes(x = lon, y = lat, shape = "Candidate service point", fill = "Candidate service point", color = "Candidate service point"),
    size = 2.8,
    stroke = 0.35
  ) +
  geom_point(
    data = stops_nearest,
    aes(x = stop_lon, y = stop_lat, shape = "Transit proxy", fill = "Transit proxy", color = "Transit proxy"),
    size = 2.7,
    stroke = 0.35
  ) +
  geom_point(
    data = fire,
    aes(x = lon, y = lat, shape = "Representative wildfire point", color = "Representative wildfire point"),
    fill = red,
    size = 3.8,
    stroke = 1.05
  ) +
  geom_segment(data = segments, aes(x = x, y = y, xend = xend, yend = yend), color = ink, linewidth = 0.3) +
  geom_label(
    data = callouts,
    aes(x = lon + nudge_x, y = lat + nudge_y, label = label),
    size = 2.45,
    lineheight = 0.9,
    color = ink,
    fill = "white",
    linewidth = 0.22,
    label.padding = unit(0.12, "lines")
  ) +
  scale_shape_manual(name = NULL, breaks = map_breaks, values = c(
    "Tract centroid" = 21,
    "Candidate service point" = 24,
    "Transit proxy" = 22,
    "Representative wildfire point" = 8
  )) +
  scale_fill_manual(name = NULL, breaks = map_breaks, values = c(
    "Tract centroid" = blue,
    "Candidate service point" = green,
    "Transit proxy" = yellow,
    "Representative wildfire point" = red
  )) +
  scale_color_manual(name = NULL, breaks = map_breaks, values = c(
    "Tract centroid" = blue,
    "Candidate service point" = green,
    "Transit proxy" = "#9B7A00",
    "Representative wildfire point" = red
  )) +
  guides(
    shape = guide_legend(override.aes = list(
      fill = c(blue, green, yellow, red),
      color = c(blue, green, "#9B7A00", red),
      size = c(2.7, 3.0, 2.9, 4.0)
    )),
    fill = "none",
    color = "none"
  ) +
  coord_equal(xlim = map_x, ylim = map_y, expand = FALSE, clip = "off") +
  labs(
    title = "Spatial feasibility audit with response-level mismatch callouts",
    subtitle = "Tract centroid proxy examples; not route-level or verified shelter reachability",
    x = "Longitude",
    y = "Latitude"
  ) +
  theme_audit(9) +
  theme(legend.position = "bottom")
save_plot(audit_map, "spatial_auditing_map_with_mismatch_callouts.png", width = 9.2, height = 6.6)

# Task 4. Shelter behavior audit.
shelter_df <- merge(
  responses,
  shelter_claims[, c("run_id", "nearby_shelter_claim", "nearby_shelter_claim_proxy_issue")],
  by = "run_id",
  all.x = TRUE
)
shelter_df$nearby_shelter_claim <- tolower(as.character(shelter_df$nearby_shelter_claim)) == "true"
shelter_df$nearby_shelter_claim_proxy_issue <- tolower(as.character(shelter_df$nearby_shelter_claim_proxy_issue)) == "true"
shelter_df$nearby_shelter_claim[is.na(shelter_df$nearby_shelter_claim)] <- FALSE
shelter_df$nearby_shelter_claim_proxy_issue[is.na(shelter_df$nearby_shelter_claim_proxy_issue)] <- FALSE
shelter_df$public_shelter_selected <- shelter_df$destination_type == "Public shelter"
shelter_df$walking_to_shelter <- shelter_df$transportation_mode == "Walk" & shelter_df$destination_type == "Public shelter"
shelter_df$no_shelter_claim <- !shelter_df$nearby_shelter_claim
shelter_df$shelter_distance_group <- factor(shelter_df$shelter_distance_group, levels = c("near", "medium", "far"))
categories <- c(
  "Public shelter selected" = "public_shelter_selected",
  "Nearby shelter claim" = "nearby_shelter_claim",
  "Walking to shelter" = "walking_to_shelter",
  "No shelter claim" = "no_shelter_claim"
)
shelter_rows <- list()
for (cat_name in names(categories)) {
  field <- categories[[cat_name]]
  tmp <- aggregate(
    shelter_df[[field]],
    by = list(condition = shelter_df$condition_label, shelter_distance_group = shelter_df$shelter_distance_group),
    FUN = function(x) c(rate = rate(as.logical(x)), n = length(x), count = sum(as.logical(x), na.rm = TRUE))
  )
  shelter_rows[[cat_name]] <- data.frame(
    condition = tmp$condition,
    shelter_distance_group = tmp$shelter_distance_group,
    behavior_category = cat_name,
    rate = tmp$x[, "rate"],
    n = tmp$x[, "n"],
    count = tmp$x[, "count"]
  )
}
shelter_behavior <- do.call(rbind, shelter_rows)
shelter_behavior$condition <- factor(shelter_behavior$condition, levels = c("Baseline", "Spatially grounded"))
shelter_behavior$shelter_distance_group <- factor(shelter_behavior$shelter_distance_group, levels = c("near", "medium", "far"))
shelter_behavior$behavior_category <- factor(shelter_behavior$behavior_category, levels = rev(names(categories)))
write.csv(shelter_behavior, file.path(out_dir, "shelter_proxy_behavior_audit.csv"), row.names = FALSE)

shelter_plot <- ggplot(shelter_behavior, aes(x = shelter_distance_group, y = behavior_category)) +
  geom_point(aes(size = rate, fill = condition), shape = 21, color = ink, stroke = 0.28, alpha = 0.88) +
  geom_text(aes(label = ifelse(rate >= 10, pct(rate), "")), size = 2.6, color = ink) +
  facet_wrap(~condition, nrow = 1) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_size_continuous(range = c(1, 11), breaks = c(25, 50, 75, 100), limits = c(0, 100)) +
  labs(
    title = "Shelter behavior under candidate service proximity proxy",
    subtitle = "Candidate shelter/service proximity proxy; not verified shelter reachability",
    x = "Candidate service proximity group",
    y = NULL,
    size = "Rate",
    fill = NULL
  ) +
  theme_audit(9)
save_plot(shelter_plot, "shelter_proxy_behavior_audit.png", width = 9.4, height = 5.5)

# Task 5. Combined figure option.
panel_a <- prompt_plot +
  labs(title = "A. Prompt-label sensitivity", subtitle = NULL) +
  theme(legend.position = "none", plot.title = element_text(size = 12))
panel_b <- gis_risk_bar +
  labs(title = "B. GIS-proxy feasibility audit", subtitle = NULL) +
  theme(legend.position = "bottom", plot.title = element_text(size = 12))
png(file.path(fig_dir, "figure2_prompt_vs_gis_transport_audit_combined.png"), width = 2200, height = 900, res = 220)
grid.newpage()
pushViewport(viewport(layout = grid.layout(1, 2, widths = unit(c(1.15, 1), "null"))))
print(panel_a, vp = viewport(layout.pos.row = 1, layout.pos.col = 1))
print(panel_b, vp = viewport(layout.pos.row = 1, layout.pos.col = 2))
dev.off()

ranking_path <- file.path(out_dir, "gis_result_candidate_ranking.md")
write_md(
  ranking_path,
  c(
    "# GIS Result Candidate Ranking",
    "",
    "This ranking uses only the existing 400-response GPT-4.1-mini dataset enriched with LA County Open Data tract geometries, tract centroids, a representative wildfire point, candidate shelter/service points, and transit-stop proximity proxies. No new LLM calls were made.",
    "",
    "## 1. Best Main SRC Figure Candidate",
    "",
    "**`project/figures/figure2_prompt_vs_gis_transport_audit_combined.png`**",
    "",
    "The combined response-level figure is now the strongest SRC candidate because it separates prompt-label sensitivity from GIS-proxy feasibility audit for no-vehicle households. Panel (a) shows transportation choices under original transit-access labels, while Panel (b) audits the same response set against tract-centroid transit-stop proximity proxies. This directly communicates that plausible prompt-following behavior can still leave spatial feasibility risks.",
    "",
    "## 2. Best Single-Panel Main Figure",
    "",
    "**`project/figures/no_vehicle_gis_proxy_transport_risk_bar.png`** or **`project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`**",
    "",
    "Use a single-panel bar chart if space is too tight for the combined figure. The chart is easy to read in a 2-page SRC abstract and keeps the claim focused on no-vehicle feasibility risk under a transit-stop proximity proxy.",
    "",
    "## 3. Best Supporting Spatial Figure",
    "",
    "**`project/figures/spatial_auditing_map_with_mismatch_callouts.png`**",
    "",
    "The map is useful for advisor discussion and can support the paper if space allows. It is more explanatory than the plain spatial positioning map because it overlays selected response-level mismatch examples. It may be too visually dense for the main 2-page abstract unless the paper needs a stronger GIS-facing figure.",
    "",
    "## 4. Best Method/Audit Support",
    "",
    "**GIS label audit boxplots**: `project/figures/gis_label_audit_transit_boxplot.png`, `project/figures/gis_label_audit_shelter_boxplot.png`, and `project/figures/gis_label_audit_fire_boxplot.png`.",
    "",
    "These are useful methods/advisor-support figures. They compare original prompt labels with GIS-derived proxy distances and should be framed as exploratory GIS-supported audits, not validation of operational accessibility or exposure.",
    "",
    "## 5. Advisor Discussion Figures",
    "",
    "- `project/figures/no_vehicle_prompt_label_transport_behavior.png`: useful for showing prompt-label sensitivity.",
    "- `project/figures/no_vehicle_gis_proxy_transport_behavior_bubble.png`: useful for showing response-level mode choices under GIS proxy groups.",
    "- `project/figures/shelter_proxy_behavior_audit.png`: useful for discussing shelter language and candidate service proximity.",
    "",
    "## 6. Exploratory-Only / Not Recommended As Main Figure",
    "",
    "- `project/figures/transit_distance_vs_feasibility_risk_scatter.png`: exploratory spatial association only; do not frame causally.",
    "- `project/figures/fire_distance_reasoning_salience_bar.png`: evacuation decision and urgency are close to ceiling, so it is weaker as a main result.",
    "- `project/figures/nearby_shelter_claim_by_distance_simple.png`: useful support, but weaker than the response-level shelter audit.",
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
    "Use the combined prompt-label vs GIS-proxy transportation audit if space allows. If the 2-page layout is tight, use the GIS-proxy risk bar as the main analytical figure and keep the response-level bubbles/map for advisor discussion or appendix material."
  )
)

index_path <- file.path(out_dir, "gis_supported_output_index.md")
write_md(
  index_path,
  c(
    "# GIS-Supported Output Index",
    "",
    "## Response-Level Behavior Audit Figures",
    "",
    "- `project/figures/no_vehicle_prompt_label_transport_behavior.png`: bubble/count plot of no-vehicle transportation choices by original prompt transit labels.",
    "- `project/figures/no_vehicle_gis_proxy_transport_behavior_bubble.png`: bubble/count plot of no-vehicle transportation choices by GIS-derived transit-stop proximity proxy.",
    "- `project/figures/no_vehicle_gis_proxy_transport_risk_bar.png`: no-vehicle violation/spatial-inconsistency risk by GIS transit proxy group.",
    "- `project/figures/figure2_prompt_vs_gis_transport_audit_combined.png`: combined paper-ready figure separating prompt-label sensitivity from GIS-proxy feasibility audit.",
    "- `project/figures/spatial_auditing_map_with_mismatch_callouts.png`: spatial audit map with selected response-level mismatch callouts.",
    "- `project/figures/shelter_proxy_behavior_audit.png`: shelter behavior audit by candidate shelter/service proximity group.",
    "",
    "## Response-Level Behavior Audit Tables",
    "",
    "- `project/outputs/no_vehicle_prompt_label_transport_behavior.csv`: source counts and percentages for prompt-label transportation behavior.",
    "- `project/outputs/no_vehicle_gis_proxy_transport_behavior.csv`: source counts and percentages for GIS-proxy transportation behavior.",
    "- `project/outputs/shelter_proxy_behavior_audit.csv`: source rates for shelter-related behavior categories.",
    "",
    "## Polished Existing Candidate Figures",
    "",
    "- `project/figures/no_vehicle_transit_proxy_risk_simple_v2.png`: v2 simplified no-vehicle feasibility risk by transit-stop proximity proxy.",
    "- `project/figures/selected_tracts_fire_shelter_transit_map_polished_v2.png`: v2 polished spatial positioning map.",
    "- `project/figures/gis_label_audit_transit_boxplot.png`: transit label audit boxplot.",
    "- `project/figures/gis_label_audit_shelter_boxplot.png`: shelter-distance label audit boxplot.",
    "- `project/figures/gis_label_audit_fire_boxplot.png`: wildfire-risk label audit boxplot.",
    "",
    "## Interpretation Boundary",
    "",
    "These outputs distinguish prompt-label sensitivity from GIS-proxy feasibility auditing. They use tract centroid proxies, candidate shelter/service proximity proxies, and transit-stop proximity proxies. They do not prove route-level reachability, verified wildfire shelter access, active wildfire exposure, or operational evacuation feasibility."
  )
)
