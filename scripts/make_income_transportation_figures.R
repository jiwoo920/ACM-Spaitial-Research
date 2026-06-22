library(ggplot2)

root_prefix <- if (file.exists("outputs/main_experiment_gpt_acs_200/income_transportation_mode_analysis.csv")) "" else "project/"
analysis_path <- paste0(root_prefix, "outputs/main_experiment_gpt_acs_200/income_transportation_mode_analysis.csv")
figure_dir <- paste0(root_prefix, "figures/main_experiment_gpt_acs_200")

analysis <- read.csv(analysis_path)
analysis$income_condition <- factor(
  paste(analysis$income_group, analysis$condition, sep = " / "),
  levels = c(
    "Lower income / Baseline",
    "Lower income / Spatially grounded",
    "Higher income / Baseline",
    "Higher income / Spatially grounded"
  )
)
analysis$transportation_mode <- factor(
  analysis$transportation_mode,
  levels = c(
    "Private vehicle",
    "Public transit",
    "Ride with family/friend",
    "Emergency transport",
    "Walk",
    "Mixed/other",
    "No transportation"
  )
)

palette <- c(
  "Private vehicle" = "#4E79A7",
  "Public transit" = "#F28E2B",
  "Ride with family/friend" = "#59A14F",
  "Emergency transport" = "#E15759",
  "Walk" = "#76B7B2",
  "Mixed/other" = "#B07AA1",
  "No transportation" = "#9D9D9D"
)

stacked <- ggplot(analysis, aes(x = income_condition, y = percentage, fill = transportation_mode)) +
  geom_col(width = 0.72, color = "white", linewidth = 0.25) +
  scale_fill_manual(values = palette, drop = FALSE) +
  scale_y_continuous(labels = function(x) paste0(x, "%"), limits = c(0, 100), expand = c(0, 0)) +
  labs(
    title = "Transportation mode recommendations by income group",
    subtitle = "Existing GPT-4.1-mini 400-response main experiment",
    x = NULL,
    y = "Percentage of responses",
    fill = "Transportation mode"
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 15),
    axis.text.x = element_text(angle = 18, hjust = 1),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    legend.position = "right",
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA)
  )

ggsave(
  file.path(figure_dir, "income_transportation_mode_stackedbar.png"),
  stacked,
  width = 9,
  height = 5.5,
  dpi = 160,
  bg = "white"
)

pie_data <- subset(analysis, count > 0)
pies <- ggplot(pie_data, aes(x = "", y = percentage, fill = transportation_mode)) +
  geom_col(width = 1, color = "white", linewidth = 0.3) +
  coord_polar(theta = "y") +
  facet_wrap(~ income_condition, ncol = 2) +
  scale_fill_manual(values = palette, drop = FALSE) +
  labs(
    title = "Transportation mode mix by income group",
    subtitle = "Pie small multiples; percentages based on responses within each income/condition group",
    fill = "Transportation mode"
  ) +
  theme_void(base_size = 11) +
  theme(
    plot.title = element_text(face = "bold", size = 15, color = "black"),
    plot.subtitle = element_text(color = "black"),
    strip.text = element_text(face = "bold", size = 10, color = "black"),
    legend.position = "right",
    legend.text = element_text(color = "black"),
    legend.title = element_text(color = "black"),
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA)
  )

ggsave(
  file.path(figure_dir, "income_transportation_mode_pies.png"),
  pies,
  width = 9,
  height = 6,
  dpi = 160,
  bg = "white"
)
