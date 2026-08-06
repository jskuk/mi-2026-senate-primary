# Primary turnout against the Democratic general-election vote, plus the age-gap series.
#
#   Rscript make_dem_turnout.R

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2)
  library(scales); library(patchwork)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

BLU <- c("#104281","#1c5cab","#2a78d6","#5598e7","#86b6ef")
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUT <- "#898781"; GRD <- "#e1e0d9"; SRF <- "#fcfcfb"
ACC <- "#4a3aa7"

q <- read_csv("../analysis/dem_turnout_quintiles.csv", show_col_types = FALSE) %>%
  mutate(group = factor(group, levels = rev(c("Q1 oldest","Q2","Q3","Q4","Q5 youngest"))),
         lab = c("Oldest fifth","","Middle","","Youngest fifth")[
                 match(as.character(group), c("Q1 oldest","Q2","Q3","Q4","Q5 youngest"))])
sw <- sum(q$primary) / sum(q$harris)

pA <- ggplot(q, aes(dem_based, group, fill = group)) +
  geom_vline(xintercept = sw, colour = MUT, linewidth = .5, linetype = "22") +
  annotate("text", x = sw + .004, y = .62, label = sprintf("statewide %.0f%%", sw*100),
           hjust = 0, size = 3, colour = MUT) +
  geom_col(width = .68) +
  geom_text(aes(label = percent(dem_based, accuracy = .1)), hjust = -.18,
            size = 3.4, fontface = "bold", colour = INK) +
  scale_fill_manual(values = rev(BLU), guide = "none") +
  scale_x_continuous(labels = percent_format(accuracy = 1), limits = c(0, .70),
                     breaks = seq(0, .6, .2), expand = expansion(mult = c(0, .02))) +
  scale_y_discrete(labels = function(v) c("Q1 oldest"="Oldest fifth\n20% young",
      "Q2"="\n24% young", "Q3"="Middle\n26% young", "Q4"="\n29% young",
      "Q5 youngest"="Youngest fifth\n36% young")[v]) +
  labs(title = "Younger precincts convert the fewest Democrats",
       subtitle = paste0("2026 Democratic primary votes as a share of the same precinct's 2024 Harris vote.\n",
                         "Democratic numbers on both sides, so Republican primary ballots cannot distort it."),
       x = "Share of 2024 Harris voters who cast a 2026 primary ballot", y = NULL) +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),
        panel.grid.major.x = element_line(colour = GRD, linewidth = .3),
        axis.text.y = element_text(colour = INK2, size = 9, lineheight = 1.15, hjust = 1),
        axis.text.x = element_text(colour = MUT, size = 9),
        axis.title = element_text(colour = INK2, size = 9.5),
        plot.title = element_text(face = "bold", size = 12.5, colour = INK, margin = margin(b = 4)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                     margin = margin(b = 12)))

rat <- bind_rows(
  read_csv("../analysis/turnout_series_dem70.csv", show_col_types = FALSE) %>%
    rename(grp = 1) %>% pivot_longer(-grp, names_to = "year", values_to = "t") %>%
    group_by(year) %>% summarise(r = t[grp == "Q5 youngest"]/t[grp == "Q1 oldest"]) %>%
    mutate(set = "Democratic-leaning precincts"),
  read_csv("../analysis/turnout_series_all.csv", show_col_types = FALSE) %>%
    rename(grp = 1) %>% pivot_longer(-grp, names_to = "year", values_to = "t") %>%
    group_by(year) %>% summarise(r = t[grp == "Q5 youngest"]/t[grp == "Q1 oldest"]) %>%
    mutate(set = "All precincts")) %>%
  mutate(year = as.integer(year))

pB <- ggplot(rat, aes(year, r, colour = set, linetype = set, group = set)) +
  geom_hline(yintercept = 1, colour = MUT, linewidth = .4) +
  annotate("text", x = 2017.9, y = 1.05, label = "gap closed", hjust = 0, size = 3, colour = MUT) +
  geom_line(linewidth = 1.1) + geom_point(size = 2.4) +
  geom_text(aes(label = sprintf("%.2f", r), vjust = ifelse(set == "All precincts", -1.25, 1.95)),
            size = 3.05, fontface = "bold", show.legend = FALSE) +
  scale_colour_manual(values = c("Democratic-leaning precincts" = ACC,
                                 "All precincts" = MUT), name = NULL) +
  scale_linetype_manual(values = c("Democratic-leaning precincts" = "solid",
                                   "All precincts" = "22"), name = NULL) +
  scale_x_continuous(breaks = c(2018, 2020, 2022, 2024, 2026), limits = c(2017.6, 2026.5)) +
  scale_y_continuous(limits = c(.40, 1.14), breaks = seq(.4, 1.0, .2)) +
  labs(title = "The age gap in primary participation, 2018-2026",
       subtitle = paste0("Youngest fifth of precincts' turnout divided by the oldest fifth's. Flat for four\n",
                         "elections, then a break - but this is the GROWTH measure, so read it as \"young\n",
                         "precincts rose fastest from the smallest base\", not \"young voters now show up\"."),
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
    title = "Young precincts grew the fastest and still turn out the least",
    subtitle = paste0(
      "Measured against the Democratic general-election vote, the youngest fifth of precincts converted 51% of their 2024 Harris voters into\n",
      "2026 primary voters; the oldest fifth converted 61%. Measured against 2024 primary voters instead, the young look best - because in older,\n",
      "more Republican precincts that denominator is swollen with people who took a Republican ballot in Michigan's open primary."),
    caption = paste0(
      "Left: all 2,857 reporting precincts. Right: turnout as a share of 2024-registered voters, one fixed denominator, so the series is internally comparable.\n",
      "Partisanship is not the whole story: within precincts that were over 70% Democratic in 2024, conversion still falls from 59% in the oldest fifth to 47% in the youngest.\n",
      "Harris votes are a proxy for the Democratic electorate, not an identity - Michigan has no party registration and its primaries are open. Age is a precinct characteristic\n",
      "(share of registrants aged 18-34), not a voter-level measure; voter-level rates exist for Aug 2024 only, where registered 65-74s voted at 47.5% against 8.0% for 20-24s.\n",
      "Sources: L2 voter file via Redistricting Data Hub aggregated to 2020 census blocks; 2024 results via RDH; 2026 results from Michigan Secretary of State via VoteHub."),
    theme = theme(
      plot.background = element_rect(fill = SRF, colour = NA),
      plot.title = element_text(face = "bold", size = 16.5, colour = INK, margin = margin(b = 5)),
      plot.subtitle = element_text(colour = INK2, size = 9.5, lineheight = 1.45, margin = margin(b = 14)),
      plot.caption = element_text(colour = MUT, size = 7.3, hjust = 0, lineheight = 1.4,
                                  margin = margin(t = 14)),
      plot.caption.position = "plot", plot.title.position = "plot",
      plot.margin = margin(16, 20, 12, 14)))

ggsave("dem_turnout_R.png", p, width = 12.5, height = 6.8, dpi = 200, bg = SRF)
ggsave("dem_turnout_R.pdf", p, width = 12.5, height = 6.8, bg = SRF)
cat("wrote dem_turnout_R.png / .pdf\n")
