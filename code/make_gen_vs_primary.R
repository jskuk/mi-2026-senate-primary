# General-election turnout vs primary turnout, by age of a precinct's registrants.
#
#   Rscript make_gen_vs_primary.R
#
# The point: the age gap is modest in a general election and triples in a primary.

suppressPackageStartupMessages({
  library(dplyr); library(tidyr); library(readr); library(ggplot2)
  library(scales); library(patchwork)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

GEN <- "#c9c8c2"; P24 <- "#86b6ef"; P26 <- "#104281"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUT <- "#898781"; GRD <- "#e1e0d9"; SRF <- "#fcfcfb"

r <- read_csv("../analysis/gen_vs_primary.csv", show_col_types = FALSE) %>%
  mutate(q = factor(q, levels = rev(c("Q1 oldest","Q2","Q3","Q4","Q5 youngest"))))

agg <- r %>% group_by(q) %>%
  summarise(young = weighted.mean(pct_reg_young, votes_total),
            gen  = sum(pres24_total) / sum(reg_all),
            p24  = sum(voted_all) / sum(reg_all),
            p26  = sum(TOTAL_TURNOUT_MEASURE) / sum(reg_all), .groups = "drop") %>%
  mutate(lab = c("Youngest fifth","","Middle","","Oldest fifth")[as.integer(q)],
         ylab = sprintf("%s\n%.0f%% aged 18-34", ifelse(lab == "", " ", lab), young*100))

pA <- ggplot(agg, aes(y = q)) +
  geom_segment(aes(x = 0, xend = gen, yend = q), colour = GEN, linewidth = 7) +
  geom_point(aes(x = gen), colour = GEN, size = 5) +
  geom_point(aes(x = p24), colour = P24, size = 4.4) +
  geom_point(aes(x = p26), colour = P26, size = 4.4) +
  geom_segment(aes(x = p24, xend = p26, yend = q), colour = P26, linewidth = .55,
               arrow = arrow(length = unit(.13, "cm"), type = "closed")) +
  geom_text(aes(x = gen, label = percent(gen, accuracy = 1)), hjust = -.4,
            size = 3.1, colour = INK2) +
  geom_text(data = agg %>% filter(q == "Q5 youngest"),
            aes(x = p24, y = 5.42, label = "Aug 2024\nprimary"), size = 2.95,
            colour = P24, fontface = "bold", lineheight = 1.05) +
  geom_text(data = agg %>% filter(q == "Q5 youngest"),
            aes(x = p26, y = 5.42, label = "Aug 2026\nprimary"), size = 2.95,
            colour = P26, fontface = "bold", lineheight = 1.05, hjust = -.05) +
  geom_text(data = agg %>% filter(q == "Q5 youngest"),
            aes(x = gen, y = 5.42, label = "Nov 2024\ngeneral"), size = 2.95,
            colour = "#8f8e88", fontface = "bold", lineheight = 1.05) +
  scale_y_discrete(labels = setNames(agg$ylab, agg$q), expand = expansion(add = c(.6, 1.15))) +
  scale_x_continuous(labels = percent_format(accuracy = 1), limits = c(0, .92),
                     breaks = seq(0, .75, .25), expand = expansion(mult = c(0, .01))) +
  labs(title = "Primaries lose young voters far faster than general elections do",
       subtitle = paste0("Share of registered voters who cast a ballot. The grey bar is the November 2024 general;\n",
                         "the two dots are the August primaries that bracket it."),
       x = NULL, y = NULL) +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(), panel.grid.major.y = element_blank(),
        panel.grid.major.x = element_line(colour = GRD, linewidth = .3),
        axis.text.y = element_text(colour = INK2, size = 9, lineheight = 1.15, hjust = 1),
        axis.text.x = element_text(colour = MUT, size = 9),
        plot.title = element_text(face = "bold", size = 12.5, colour = INK, margin = margin(b = 4)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                     margin = margin(b = 12)))

o <- agg %>% filter(q == "Q1 oldest"); y <- agg %>% filter(q == "Q5 youngest")
rat <- tibble(
  what = factor(c("Nov 2024\ngeneral","Aug 2024\nprimary","Aug 2026\nprimary"),
                levels = c("Nov 2024\ngeneral","Aug 2024\nprimary","Aug 2026\nprimary")),
  r = c(y$gen/o$gen, y$p24/o$p24, y$p26/o$p26),
  col = c(GEN, P24, P26))

pB <- ggplot(rat, aes(what, r, fill = what)) +
  geom_hline(yintercept = 1, colour = MUT, linewidth = .4) +
  annotate("text", x = -Inf, y = 1.035, label = "  no age gap", hjust = 0, size = 3, colour = MUT) +
  geom_col(width = .58) +
  geom_text(aes(label = sprintf("%.2f", r)), vjust = -.7, size = 4, fontface = "bold",
            colour = INK) +
  scale_fill_manual(values = setNames(rat$col, rat$what), guide = "none") +
  scale_y_continuous(limits = c(0, 1.12), breaks = seq(0, 1, .25),
                     expand = expansion(mult = c(0, .02))) +
  labs(title = "The age gap triples in a primary",
       subtitle = paste0("Youngest fifth's turnout divided by the oldest fifth's. A general election\n",
                         "loses relatively few young voters; an August primary loses many more.\n",
                         "2026 recovered about half of the extra primary penalty."),
       x = NULL, y = "Youngest / oldest") +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(), panel.grid.major.x = element_blank(),
        panel.grid.major.y = element_line(colour = GRD, linewidth = .3),
        axis.text.x = element_text(colour = INK2, size = 9, lineheight = 1.1),
        axis.text.y = element_text(colour = MUT, size = 9),
        axis.title.y = element_text(colour = INK2, size = 9.5),
        plot.title = element_text(face = "bold", size = 12.5, colour = INK, margin = margin(b = 4)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                     margin = margin(b = 12)))

p <- pA + pB + plot_layout(widths = c(1.35, 1)) +
  plot_annotation(
    title = "It is the primary, not the electorate, that ages the vote",
    subtitle = paste0(
      "In November 2024 the youngest fifth of precincts turned out at 77% of the oldest fifth's rate. In the August 2024 primary that fell to 54%. ",
      "Turnout drops for\neveryone in a primary - from 78% to 32% among the oldest precincts - but it drops much further among the young, from 60% to 17%."),
    caption = paste0(
      "1,894 precincts with a reported 2026 total-ballot count, 65% of the Democratic primary vote; Oakland, Macomb, Kalamazoo and Calhoun are absent. ",
      "All three elections are divided by the\nsame denominator, registered voters in the 2024 L2 file. Every figure counts ALL ballots, both parties. ",
      "Age is a precinct characteristic - the share of its registrants aged 18-34 - not a voter-level\nmeasure. ",
      "Sources: L2 voter file via Redistricting Data Hub aggregated to 2020 census blocks; 2024 general results via RDH; 2026 results from Michigan county canvass reports."),
    theme = theme(
      plot.background = element_rect(fill = SRF, colour = NA),
      plot.title = element_text(face = "bold", size = 16.5, colour = INK, margin = margin(b = 5)),
      plot.subtitle = element_text(colour = INK2, size = 9.5, lineheight = 1.45, margin = margin(b = 14)),
      plot.caption = element_text(colour = MUT, size = 7.3, hjust = 0, lineheight = 1.4,
                                  margin = margin(t = 14)),
      plot.caption.position = "plot", plot.title.position = "plot",
      plot.margin = margin(16, 20, 12, 14)))

ggsave("gen_vs_primary_R.png", p, width = 12.5, height = 6.4, dpi = 200, bg = SRF)
ggsave("gen_vs_primary_R.pdf", p, width = 12.5, height = 6.4, bg = SRF)
cat("wrote gen_vs_primary_R.png / .pdf\n"); print(as.data.frame(agg %>% select(q, young, gen, p24, p26)))
