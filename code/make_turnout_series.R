# August-primary turnout by age of a precinct's registrants, 2018-2026.
#
#   Rscript make_turnout_series.R
#
# Four Trump-era August primaries with a near-identical age skew, then 2026.

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2)
  library(scales); library(patchwork)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

BLU <- c("#104281","#1c5cab","#2a78d6","#5598e7","#86b6ef")   # oldest -> youngest, validated
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUT <- "#898781"; GRD <- "#e1e0d9"; SRF <- "#fcfcfb"
ACC <- "#4a3aa7"

long <- read_csv("../analysis/turnout_series_all.csv", show_col_types = FALSE) %>%
  rename(grp = 1) %>% pivot_longer(-grp, names_to = "year", values_to = "t") %>%
  mutate(year = as.integer(year),
         grp = factor(grp, levels = c("Q1 oldest","Q2","Q3","Q4","Q5 youngest")))
ends <- long %>% filter(year == 2026)

# only the two extremes are labelled: in 2026 the middle three converge to within a
# point of each other, so labelling them would just stack text on itself.
LAB <- c("Q1 oldest"="Oldest fifth", "Q2"="", "Q3"="", "Q4"="", "Q5 youngest"="Youngest fifth")

pA <- ggplot(long, aes(year, t, colour = grp, group = grp)) +
  annotate("rect", xmin = 2025, xmax = 2026.9, ymin = -Inf, ymax = Inf,
           fill = ACC, alpha = .05) +
  geom_line(linewidth = 1.15) +
  geom_point(size = 2.3) +
  geom_text(data = ends %>% filter(LAB[as.character(grp)] != ""),
            aes(label = LAB[as.character(grp)]), hjust = 0, nudge_x = .12,
            size = 3.2, fontface = "bold", show.legend = FALSE) +
  scale_colour_manual(values = BLU, guide = "none") +
  scale_x_continuous(breaks = c(2018, 2020, 2022, 2024, 2026), limits = c(2017.7, 2028.6)) +
  scale_y_continuous(labels = percent_format(accuracy = 1), limits = c(.12, .40)) +
  labs(title = "Four primaries with the same age gap, then 2026",
       subtitle = paste0("ALL primary ballots divided by registered voters, every year including 2026.\n",
                         "Precincts grouped into fifths by the share of registrants aged 18-34."),
       x = NULL, y = "Share of registrants who voted") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = GRD, linewidth = .3),
        axis.text = element_text(colour = MUT, size = 9),
        axis.title = element_text(colour = INK2, size = 9.5),
        plot.title = element_text(face = "bold", size = 12.5, colour = INK, margin = margin(b = 4)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                     margin = margin(b = 12)))

rat <- bind_rows(
  read_csv("../analysis/turnout_series_dem70.csv", show_col_types = FALSE) %>%
    rename(grp = 1) %>% pivot_longer(-grp, names_to = "year", values_to = "t") %>%
    group_by(year) %>% summarise(r = t[grp == "Q5 youngest"] / t[grp == "Q1 oldest"]) %>%
    mutate(set = "Democratic-leaning precincts"),
  read_csv("../analysis/turnout_series_all.csv", show_col_types = FALSE) %>%
    rename(grp = 1) %>% pivot_longer(-grp, names_to = "year", values_to = "t") %>%
    group_by(year) %>% summarise(r = t[grp == "Q5 youngest"] / t[grp == "Q1 oldest"]) %>%
    mutate(set = "All precincts")) %>%
  mutate(year = as.integer(year))

pB <- ggplot(rat, aes(year, r, colour = set, linetype = set, group = set)) +
  geom_hline(yintercept = 1, colour = MUT, linewidth = .4) +
  annotate("text", x = 2017.9, y = 1.05, label = "gap closed", hjust = 0, size = 3, colour = MUT) +
  geom_line(linewidth = 1.1) + geom_point(size = 2.3) +
  geom_text(aes(label = sprintf("%.2f", r),
                vjust = ifelse(set == "All precincts", -1.25, 1.9)),
            size = 3.05, fontface = "bold", show.legend = FALSE) +
  scale_colour_manual(values = c("Democratic-leaning precincts" = MUT,
                                 "All precincts" = ACC), name = NULL) +
  scale_linetype_manual(values = c("Democratic-leaning precincts" = "22",
                                   "All precincts" = "solid"), name = NULL) +
  scale_x_continuous(breaks = c(2018, 2020, 2022, 2024, 2026), limits = c(2017.6, 2026.5)) +
  scale_y_continuous(limits = c(.4, 1.12), breaks = seq(.4, 1.0, .2)) +
  labs(title = "The youngest fifth's turnout, as a share of the oldest fifth's",
       subtitle = paste0("Flat at 0.54-0.61 across four elections, then a break to 0.67. The dashed line\n",
                         "restricts to Democratic-leaning precincts and lands in the same place."),
       x = NULL, y = "Youngest / oldest") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = GRD, linewidth = .3),
        axis.text = element_text(colour = MUT, size = 9),
        axis.title = element_text(colour = INK2, size = 9.5),
        legend.position = "top", legend.justification = "left",
        legend.text = element_text(colour = INK2, size = 8.5),
        legend.margin = margin(b = -4, l = -8),
        plot.title = element_text(face = "bold", size = 12.5, colour = INK, margin = margin(b = 4)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                     margin = margin(b = 8)))

p <- pA + pB +
  plot_annotation(
    title = "Young voters closed a quarter of Michigan's primary turnout gap",
    subtitle = paste0(
      "The age skew of August-primary turnout barely moved across four Trump-era elections. In 2026 it broke - but from a low base: ",
      "the youngest fifth of\nprecincts still turned out 12 points below the oldest. Everyone voted more in 2026; the young simply ",
      "rose faster, 1.46x against 1.18x."),
    caption = paste0(
      "Turnout is each year's voters divided by one fixed denominator (registered voters in the 2024 L2 file), so the series is ",
      "internally comparable; levels are not the rates reported at the time.\n",
      "Every year counts ALL primary ballots. 2026 Republican gubernatorial votes and reported ballot totals come from county canvass PDFs, which cover 1,894 of the 2,857 ",
      "analysis precincts - 65% of the Democratic primary vote.\nCoverage is a county-level pattern, and Oakland, Macomb, Kalamazoo and Calhoun are absent entirely. ",
      "An independent check on the FULL precinct set, restricted instead to Democratic-leaning\nprecincts so that Democratic-only 2026 ballots stay comparable, gives the same answer: 0.54 in 2024 to 0.67 in 2026.\n",
      "Age is a precinct characteristic - the share of its registrants aged 18-34 - not a voter-level measure. Voter-level rates by ",
      "age bracket exist for 2024 only; there, registered 65-74s voted at 47.5%\nagainst 8.0% for 20-24s. L2 credits vote history to a ",
      "voter's address at the file snapshot rather than at the election, so attribution loosens for the earliest years.\n",
      "Sources: L2 voter file via Redistricting Data Hub, aggregated to 2020 census blocks; 2026 results from Michigan Secretary of State via VoteHub."),
    theme = theme(
      plot.background = element_rect(fill = SRF, colour = NA),
      plot.title = element_text(face = "bold", size = 16.5, colour = INK, margin = margin(b = 5)),
      plot.subtitle = element_text(colour = INK2, size = 10, lineheight = 1.45, margin = margin(b = 14)),
      plot.caption = element_text(colour = MUT, size = 7.5, hjust = 0, lineheight = 1.4,
                                  margin = margin(t = 14)),
      plot.caption.position = "plot", plot.title.position = "plot",
      plot.margin = margin(16, 20, 12, 14)))

ggsave("turnout_series_R.png", p, width = 12, height = 6.6, dpi = 200, bg = SRF)
ggsave("turnout_series_R.pdf", p, width = 12, height = 6.6, bg = SRF)
cat("wrote turnout_series_R.png / .pdf\n")
