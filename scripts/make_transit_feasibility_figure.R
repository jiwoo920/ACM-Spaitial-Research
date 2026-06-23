library(ggplot2)

root_prefix <- if (file.exists("outputs/main_experiment_gpt_acs_200/transit_feasibility_figure_data.csv")) "" else "project/"
data_path <- paste0(root_prefix, "outputs/main_experiment_gpt_acs_200/transit_feasibility_figure_data.csv")
figure_dir <- paste0(root_prefix, "figures/main_experiment_gpt_acs_200")

df <- read.csv(data_path)
df$check <- factor(
  df$check,
  levels = c(
    "Public transit selected\nwhen transit is limited",
    "Public transit selected for\nno-vehicle + limited/no transit",
    "Violation/inconsistency for\nno-vehicle + limited/no transit"
  )
)
df$condition <- factor(df$condition, levels = c("Baseline", "Spatially grounded"))

p <- ggplot(df, aes(x = check, y = rate, fill = condition)) +
  geom_col(position = position_dodge(width = 0.72), width = 0.62) +
  geom_text(
    aes(label = paste0(sprintf("%.1f", rate), "%")),
    position = position_dodge(width = 0.72),
    vjust = -0.35,
    size = 3.7
  ) +
  scale_fill_manual(values = c("Baseline" = "#6BAED6", "Spatially grounded" = "#F28E2B")) +
  scale_y_continuous(limits = c(0, 110), labels = function(x) paste0(x, "%"), expand = c(0, 0)) +
  labs(
    title = "Transit-aware prompting reduces mismatches but leaves residual risk",
    subtitle = "No-vehicle + limited/no transit subgroup uses n = 8 personas per condition",
    x = NULL,
    y = "Rate",
    fill = NULL
  ) +
  theme_minimal(base_size = 12) +
  theme(
    plot.title = element_text(face = "bold", size = 13),
    plot.subtitle = element_text(size = 10),
    axis.text.x = element_text(size = 10, lineheight = 0.95),
    panel.grid.major.x = element_blank(),
    panel.grid.minor = element_blank(),
    legend.position = "bottom",
    plot.background = element_rect(fill = "white", color = NA),
    panel.background = element_rect(fill = "white", color = NA),
    plot.margin = margin(14, 18, 12, 14)
  )

ggsave(
  file.path(figure_dir, "transit_feasibility_figure1_candidate.png"),
  p,
  width = 9.2,
  height = 5.7,
  dpi = 170,
  bg = "white"
)
