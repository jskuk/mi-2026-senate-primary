# Presidential winner sequence 2016-2020-2024 vs primary vote share.
#
#   Rscript make_winner_combos.R
#
# Intervals are a nonparametric bootstrap over PRECINCTS (2,000 draws, percentile
# method), not a binomial interval on votes. The votes are a census, so a binomial
# interval on ~200k ballots would be meaninglessly tight and would answer a
# question nobody asked. What we actually want to know is how much a differently
# drawn set of precincts of this type might differ.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(tidyr); library(scales); library(readr)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

EL_SAYED <- "#4a3aa7"; STEVENS <- "#eb6834"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUTED <- "#898781"
GRID <- "#e1e0d9"; SURFACE <- "#fcfcfb"

t <- read_csv("winner_combos.csv", show_col_types = FALSE)
prec <- read_csv("winner_combos_precincts.csv", show_col_types = FALSE)
sw_el <- sum(prec[["C_TOT_Abdul_El-Sayed"]]) / sum(prec$votes_total)
sw_st <- sum(prec[["C_TOT_Haley_Stevens"]])  / sum(prec$votes_total)

lab <- function(cmb) paste(strsplit(cmb, "")[[1]], collapse = " → ")
t <- t %>%
  mutate(seq = vapply(combo, lab, ""),
         row = sprintf("%s\n%s precincts · %s votes (%s of all)",
                       seq, format(n_precincts, big.mark = ","),
                       format(votes, big.mark = ","), percent(share_of_votes, accuracy = .1))) %>%
  arrange(elsayed)
t$row <- factor(t$row, levels = t$row)

long <- bind_rows(
  t %>% transmute(row, cand = "El-Sayed", v = elsayed, lo = elsayed_lo, hi = elsayed_hi),
  t %>% transmute(row, cand = "Stevens",  v = stevens, lo = stevens_lo, hi = stevens_hi)
) %>% mutate(cand = factor(cand, levels = c("El-Sayed", "Stevens")))

p <- ggplot(long, aes(v, row, colour = cand)) +
  geom_vline(xintercept = sw_el, colour = EL_SAYED, linewidth = .4, alpha = .35) +
  geom_vline(xintercept = sw_st, colour = STEVENS,  linewidth = .4, alpha = .35) +
  geom_linerange(aes(xmin = lo, xmax = hi),
                 position = position_dodge(width = .55), linewidth = 1.5, alpha = .40) +
  geom_point(position = position_dodge(width = .55), size = 3.1) +
  geom_text(aes(label = percent(v, accuracy = .1)),
            position = position_dodge(width = .55),
            hjust = -.35, size = 3, show.legend = FALSE, fontface = "bold") +
  scale_colour_manual(values = c("El-Sayed" = EL_SAYED, "Stevens" = STEVENS), name = NULL) +
  scale_x_continuous(labels = percent_format(accuracy = 1),
                     limits = c(.20, .80), breaks = seq(.2, .8, .1)) +
  labs(
    title = "Where a precinct's presidential winner changed, so did the primary",
    subtitle = paste0(
      "Two-party presidential winner in 2016 → 2020 → 2024, against each candidate's share of the ",
      "2026 U.S. Senate Democratic primary vote.\n",
      "Bars are 95% bootstrap intervals resampling precincts (2,000 draws). Faint vertical lines mark ",
      "each candidate's statewide share.\n",
      "Shares do not sum to 100: Mallory McMorrow took the remainder."),
    x = "Share of primary vote", y = NULL,
    caption = paste0(
      "No precinct produced the sequence Dem → Rep → Dem, so only seven of the eight combinations appear. ",
      "Dem → Dem → Rep is overwhelmingly Dearborn and Dearborn Heights\n",
      "(mean Arab ancestry 30%, against 2% statewide); Rep → Rep → Dem is college suburbs ",
      "(mean 43% with a bachelor's degree, against 32%). Dem → Rep → Rep rests on just 9 precincts — ",
      "read its interval with care.\n",
      "Presidential results: VEST/ALARM and Redistricting Data Hub, reallocated onto 2026 precincts via census blocks.")
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.background = element_rect(fill = SURFACE, colour = NA),
    panel.background = element_rect(fill = SURFACE, colour = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major.y = element_blank(),
    panel.grid.major.x = element_line(colour = GRID, linewidth = .3),
    axis.text.y = element_text(colour = INK, size = 9, hjust = 1, lineheight = 1.35),
    axis.text.x = element_text(colour = MUTED, size = 9),
    axis.title.x = element_text(colour = INK2, size = 9.5, margin = margin(t = 9)),
    legend.position = "top", legend.justification = "left",
    legend.text = element_text(size = 10, colour = INK2),
    legend.margin = margin(b = 2, l = -6),
    plot.title = element_text(face = "bold", size = 15.5, colour = INK, margin = margin(b = 5)),
    plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.45, margin = margin(b = 8)),
    plot.caption = element_text(colour = MUTED, size = 7.5, hjust = 0, lineheight = 1.4,
                                margin = margin(t = 12)),
    plot.caption.position = "plot", plot.title.position = "plot",
    plot.margin = margin(16, 22, 12, 14)
  )

ggsave("winner_combos_R.png", p, width = 11, height = 7.2, dpi = 200, bg = SURFACE)
ggsave("winner_combos_R.pdf", p, width = 11, height = 7.2, bg = SURFACE)
cat("wrote winner_combos_R.png / .pdf\n")
print(t %>% select(combo, n_precincts, votes, elsayed, stevens) %>% arrange(desc(elsayed)))
