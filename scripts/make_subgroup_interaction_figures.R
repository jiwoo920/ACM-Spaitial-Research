library(ggplot2)

root_prefix <- if (file.exists("outputs/main_experiment_gpt_acs_200/no_vehicle_household_size_analysis.csv")) "" else "project/"
out_dir <- paste0(root_prefix, "outputs/main_experiment_gpt_acs_200")
fig_dir <- paste0(root_prefix, "figures/main_experiment_gpt_acs_200")

baseline_color <- "#A3BEFA"
spatial_color <- "#F0986E"
ink <- "#1F2430"
muted <- "#6F768A"
grid <- "#E6E8F0"

theme_candidate <- function(base_size = 10) {
  theme_minimal(base_size = base_size) +
    theme(
      plot.title = element_text(face = "bold", size = base_size + 3, color = ink),
      plot.subtitle = element_text(size = base_size, color = muted),
      axis.title = element_text(color = ink),
      axis.text = element_text(color = muted),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(color = grid, linewidth = 0.35),
      legend.position = "bottom",
      legend.title = element_blank(),
      strip.text = element_text(face = "bold", color = ink),
      plot.background = element_rect(fill = "white", color = NA),
      panel.background = element_rect(fill = "white", color = NA),
      plot.margin = margin(14, 18, 12, 14)
    )
}

save_plot <- function(plot, filename, width = 10.5, height = 6) {
  ggsave(file.path(fig_dir, filename), plot, width = width, height = height, dpi = 170, bg = "white")
}

condition_scale <- scale_fill_manual(values = c("Baseline" = baseline_color, "Spatially grounded" = spatial_color))

nv <- read.csv(file.path(out_dir, "no_vehicle_household_size_analysis.csv"))
nv$condition <- factor(nv$condition, levels = c("Baseline", "Spatially grounded"))
nv$household_size_group <- factor(nv$household_size_group, levels = c("Single-person", "Large household (4+)"))
nv_long <- rbind(
  data.frame(group = nv$household_size_group, condition = nv$condition, metric = "Violation / spatial inconsistency", rate = nv$violation_spatial_inconsistency_rate),
  data.frame(group = nv$household_size_group, condition = nv$condition, metric = "Soft feasibility issue", rate = nv$soft_feasibility_issue_rate),
  data.frame(group = nv$household_size_group, condition = nv$condition, metric = "Public transit", rate = nv$public_transit_rate),
  data.frame(group = nv$household_size_group, condition = nv$condition, metric = "Ride/family", rate = nv$ride_family_friend_rate)
)

p1 <- ggplot(nv_long, aes(x = group, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  facet_wrap(~metric, nrow = 1) +
  condition_scale +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "No-vehicle household size changes transportation-feasibility patterns",
    subtitle = "Large no-vehicle household cells are small, so use this as exploratory evidence",
    x = NULL,
    y = "Rate"
  ) +
  theme_candidate(9) +
  theme(axis.text.x = element_text(angle = 18, hjust = 1))
save_plot(p1, "no_vehicle_household_size_grouped_bar.png", width = 13, height = 5.7)

vh <- read.csv(file.path(out_dir, "vulnerable_household_interaction_analysis.csv"))
vh$condition <- factor(vh$condition, levels = c("Baseline", "Spatially grounded"))
vh$household_group <- factor(vh$household_group, levels = c("General household", "Complex vulnerable household"))
vh_long <- rbind(
  data.frame(group = vh$household_group, condition = vh$condition, metric = "Violation / spatial inconsistency", rate = vh$violation_spatial_inconsistency_rate),
  data.frame(group = vh$household_group, condition = vh$condition, metric = "Soft feasibility issue", rate = vh$soft_feasibility_issue_rate),
  data.frame(group = vh$household_group, condition = vh$condition, metric = "Public shelter", rate = vh$public_shelter_rate)
)

p2 <- ggplot(vh_long, aes(x = group, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  facet_wrap(~metric, nrow = 1) +
  condition_scale +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Complex vulnerability plus long shelter travel time raises feasibility risk",
    subtitle = "General control vs care/mobility need with long shelter travel time",
    x = NULL,
    y = "Rate"
  ) +
  theme_candidate(9) +
  theme(axis.text.x = element_text(angle = 15, hjust = 1))
save_plot(p2, "vulnerable_household_interaction_bar.png", width = 12.5, height = 5.8)

cc <- read.csv(file.path(out_dir, "combined_constraints_with_control.csv"))
cc$condition <- factor(cc$condition, levels = c("Baseline", "Spatially grounded"))
cc$constraint_group_wrapped <- gsub(" \\+ ", "\n+ ", cc$constraint_group)
cc$constraint_group_wrapped <- gsub("Safe control", "Safe\ncontrol", cc$constraint_group_wrapped)
cc$constraint_group_wrapped <- factor(cc$constraint_group_wrapped, levels = unique(cc$constraint_group_wrapped))

p3 <- ggplot(cc, aes(x = constraint_group_wrapped, y = violation_spatial_inconsistency_rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  condition_scale +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Overlapping constraints separate high-risk households from a safe control",
    subtitle = "Violation/spatial-inconsistency rate; small subgroups are exploratory",
    x = NULL,
    y = "Risk rate"
  ) +
  theme_candidate(9) +
  theme(axis.text.x = element_text(angle = 25, hjust = 1))
save_plot(p3, "combined_constraints_with_control_bar.png", width = 13, height = 6.3)

wf <- read.csv(file.path(out_dir, "wildfire_risk_decision_check.csv"))
wf$condition <- factor(wf$condition, levels = c("Baseline", "Spatially grounded"))
wf$wildfire_risk_level <- factor(wf$wildfire_risk_level, levels = c("Moderate", "High"))
wf_long <- rbind(
  data.frame(risk = wf$wildfire_risk_level, condition = wf$condition, metric = "Evacuate now", rate = wf$evacuate_now_rate),
  data.frame(risk = wf$wildfire_risk_level, condition = wf$condition, metric = "High urgency", rate = wf$high_urgency_rate),
  data.frame(risk = wf$wildfire_risk_level, condition = wf$condition, metric = "Hazard reasoning keywords", rate = wf$hazard_fire_reasoning_keyword_rate)
)

p4 <- ggplot(wf_long, aes(x = risk, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62, color = ink, linewidth = 0.25) +
  facet_wrap(~metric, nrow = 1) +
  condition_scale +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%")) +
  labs(
    title = "Wildfire risk has little decision variation in this scenario",
    subtitle = "Use as reasoning-salience support, not as a main figure candidate",
    x = "Wildfire risk level",
    y = "Rate"
  ) +
  theme_candidate(9)
save_plot(p4, "wildfire_risk_decision_check_bar.png", width = 12, height = 5.2)
