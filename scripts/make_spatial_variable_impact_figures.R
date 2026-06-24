library(ggplot2)

root_prefix <- if (file.exists("outputs/main_experiment_gpt_acs_200/paired_prompt_change_plot_data.csv")) "" else "project/"
out_dir <- paste0(root_prefix, "outputs/main_experiment_gpt_acs_200")
fig_dir <- paste0(root_prefix, "figures/main_experiment_gpt_acs_200")

baseline_color <- "#A3BEFA"
spatial_color <- "#F0986E"
single_color <- "#5477C4"
ink <- "#1F2430"
muted <- "#6F768A"
grid <- "#E6E8F0"

theme_candidate <- function(base_size = 11) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 2, color = ink),
      plot.subtitle = element_text(size = base_size - 1, color = muted),
      axis.title = element_text(color = ink),
      axis.text = element_text(color = muted),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(color = grid, linewidth = 0.35),
      legend.position = "bottom",
      legend.title = element_blank(),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(14, 18, 12, 14)
    )
}

save_plot <- function(plot, filename, width = 10, height = 6) {
  ggsave(file.path(fig_dir, filename), plot, width = width, height = height, dpi = 170, bg = "white")
}

paired <- read.csv(file.path(out_dir, "paired_prompt_change_plot_data.csv"), check.names = FALSE)
paired$change_metric <- factor(
  paired$change_metric,
  levels = c(
    "decision changed",
    "mode changed",
    "destination changed",
    "urgency changed",
    "reasoning spatial keyword mention changed"
  ),
  labels = c("Decision", "Mode", "Destination", "Urgency", "Spatial reasoning\nkeyword mention")
)

p1 <- ggplot(paired, aes(x = change_metric, y = rate)) +
  geom_col(fill = single_color, color = ink, linewidth = 0.25, width = 0.62) +
  geom_text(aes(label = paste0(sprintf("%.1f", rate), "%")), vjust = -0.35, size = 3.4) +
  scale_y_continuous(limits = c(0, max(100, max(paired$rate) * 1.18)), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Paired responses changed more in plan details than decisions",
    subtitle = "Baseline vs spatially grounded responses for the same 200 personas",
    x = NULL,
    y = "Changed rate"
  ) +
  theme_candidate()
save_plot(p1, "paired_prompt_change_bar.png")

transit <- read.csv(file.path(out_dir, "transit_access_impact_plot_data.csv"))
transit$condition_label <- factor(transit$condition_label, levels = c("Baseline", "Spatially grounded"))
transit$transit_access <- factor(transit$transit_access, levels = c("Good", "Moderate", "Limited", "None"))

p2 <- ggplot(transit, aes(x = transit_access, y = public_transit_selected_rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = paste0(sprintf("%.1f", public_transit_selected_rate), "%")),
    position = position_dodge(width = 0.72),
    vjust = -0.35,
    size = 3.2
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Transit access information changes public-transit selection",
    subtitle = "Public transit recommendation rate by stated transit access",
    x = "Transit access",
    y = "Public transit selected"
  ) +
  theme_candidate()
save_plot(p2, "transit_access_impact_bar.png")

shelter <- read.csv(file.path(out_dir, "shelter_accessibility_plot_data.csv"))
shelter$condition_label <- factor(shelter$condition_label, levels = c("Baseline", "Spatially grounded"))
shelter$group <- factor(shelter$group, levels = c("Short", "Medium", "Long"))
shelter_long <- rbind(
  data.frame(condition_label = shelter$condition_label, group = shelter$group, metric = "Public shelter selected", rate = shelter$public_shelter_selected_rate),
  data.frame(condition_label = shelter$condition_label, group = shelter$group, metric = "Violation/inconsistency", rate = shelter$spatial_inconsistency_rate)
)

p3 <- ggplot(shelter_long, aes(x = group, y = rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  facet_wrap(~metric, nrow = 1) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Shelter travel time is an exploratory destination-feasibility signal",
    subtitle = "Approximate road travel-time groups; use cautiously for SRC selection",
    x = "Road travel-time group",
    y = "Rate"
  ) +
  theme_candidate(10)
save_plot(p3, "shelter_accessibility_bar.png", width = 11, height = 5.4)

hazard <- read.csv(file.path(out_dir, "hazard_distance_plot_data.csv"))
hazard <- hazard[hazard$condition_label != "Paired change", ]
hazard$condition_label <- factor(hazard$condition_label, levels = c("Baseline", "Spatially grounded"))
hazard$group <- factor(hazard$group, levels = c("Near", "Medium", "Far"))

p4 <- ggplot(hazard, aes(x = group, y = high_urgency_rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = paste0(sprintf("%.1f", high_urgency_rate), "%")),
    position = position_dodge(width = 0.72),
    vjust = -0.35,
    size = 3.2
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Urgency by approximate hazard distance",
    subtitle = "Exploratory hazard-distance grouping, not verified active wildfire exposure",
    x = "Hazard distance group",
    y = "High urgency response"
  ) +
  theme_candidate()
save_plot(p4, "hazard_distance_urgency_bar.png")

p5 <- ggplot(hazard, aes(x = group, y = hazard_keyword_mention_rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  geom_text(
    aes(label = paste0(sprintf("%.1f", hazard_keyword_mention_rate), "%")),
    position = position_dodge(width = 0.72),
    vjust = -0.35,
    size = 3.2
  ) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Hazard-distance reasoning salience",
    subtitle = "Share of responses mentioning fire, hazard, distance, urgency, or evacuation zone",
    x = "Hazard distance group",
    y = "Keyword mention rate"
  ) +
  theme_candidate()
save_plot(p5, "hazard_reasoning_salience_bar.png")

combined <- read.csv(file.path(out_dir, "combined_spatial_constraint_plot_data.csv"))
combined$condition_label <- factor(combined$condition_label, levels = c("Baseline", "Spatially grounded"))
combined$subgroup_wrapped <- gsub(" \\+ ", "\n+ ", combined$subgroup)

p6 <- ggplot(combined, aes(x = subgroup_wrapped, y = violation_spatial_inconsistency_rate, fill = condition_label)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color)) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Combined constraints identify high-risk exploratory subgroups",
    subtitle = "Violation/spatial-inconsistency rate; small subgroup n requires caution",
    x = NULL,
    y = "Risk rate"
  ) +
  theme_candidate(9) +
  theme(axis.text.x = element_text(angle = 25, hjust = 1))
save_plot(p6, "combined_spatial_constraint_bar.png", width = 12, height = 6.6)

if (requireNamespace("png", quietly = TRUE)) {
  library(grid)
  paths <- file.path(
    fig_dir,
    c(
      "paired_prompt_change_bar.png",
      "transit_access_impact_bar.png",
      "shelter_accessibility_bar.png",
      "hazard_distance_urgency_bar.png",
      "combined_spatial_constraint_bar.png"
    )
  )
  png(file.path(fig_dir, "result_candidate_overview.png"), width = 1800, height = 2100, res = 160, bg = "white")
  grid.newpage()
  pushViewport(viewport(layout = grid.layout(3, 2, widths = unit(c(1, 1), "null"), heights = unit(c(1, 1, 1), "null"))))
  grid.text("Spatial variable impact result candidates", x = unit(0.02, "npc"), y = unit(0.985, "npc"), just = c("left", "top"), gp = gpar(fontsize = 16, fontface = "bold", col = ink))
  for (i in seq_along(paths)) {
    img <- png::readPNG(paths[i])
    row <- ceiling(i / 2)
    col <- ifelse(i %% 2 == 1, 1, 2)
    pushViewport(viewport(layout.pos.row = row, layout.pos.col = col))
    grid.raster(img, interpolate = TRUE)
    popViewport()
  }
  dev.off()
} else {
  message("Package 'png' not installed; skipping result_candidate_overview.png")
}
