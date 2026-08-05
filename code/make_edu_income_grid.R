# Education and income pull in opposite directions: a 5x5 grid.
#
#   Rscript make_edu_income_grid.R
#
# Read DOWN a column (income held roughly constant, education rising) and El-Sayed's
# margin climbs. Read ACROSS a row (education held constant, income rising) and it
# falls. That is the whole regression finding in one picture, with no model imposed:
# these are raw vote-weighted means inside each cell.
#
# The cell counts are printed on purpose. Education and income correlate at +0.77, so
# the off-diagonal corners are thin, and one corner is empty. That sparsity is exactly
# why the linear coefficients are fragile and worth showing rather than hiding.

suppressPackageStartupMessages({
  library(dplyr); library(readr); library(ggplot2); library(scales)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

EL <- "#4a3aa7"; ST <- "#eb6834"; NEU <- "#f0efec"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUT <- "#898781"; SRF <- "#fcfcfb"

d <- read_csv("../mi_precinct_demographics_2026.csv", show_col_types = FALSE) %>%
  filter(has_results, votes_total >= 25,
         !is.na(margin_elsayed), !is.na(pct_ba_plus), !is.na(mean_hh_income))

qlab <- function(x, n = 5, fmt) {
  b <- quantile(x, seq(0, 1, length.out = n + 1))
  sprintf("%s–%s", fmt(b[-(n+1)]), fmt(b[-1]))
}
ed_lab  <- qlab(d$pct_ba_plus, 5, function(v) percent(v, accuracy = 1))
inc_lab <- qlab(d$mean_hh_income, 5, function(v) paste0("$", round(v/1000), "k"))

g <- d %>%
  mutate(ed  = cut(pct_ba_plus, quantile(pct_ba_plus, seq(0,1,.2)),
                   include.lowest = TRUE, labels = ed_lab),
         inc = cut(mean_hh_income, quantile(mean_hh_income, seq(0,1,.2)),
                   include.lowest = TRUE, labels = inc_lab)) %>%
  group_by(ed, inc) %>%
  summarise(margin = weighted.mean(margin_elsayed, votes_total) * 100,
            n = n(), votes = sum(votes_total), .groups = "drop") %>%
  tidyr::complete(ed, inc) %>%
  mutate(thin  = is.na(n) | n < 15,
         shown = ifelse(thin, NA, margin),
         lab   = ifelse(is.na(n), "no\nprecincts",
                 sprintf("%+.0f\n%s", margin, ifelse(n < 15, paste0("n=", n, " ⚠"),
                                                     paste0("n=", n)))))

p <- ggplot(g, aes(inc, ed)) +
  geom_tile(aes(fill = shown), colour = SRF, linewidth = 2) +
  geom_text(aes(label = lab, colour = abs(shown) > 28), size = 3.1, lineheight = 1.05,
            fontface = "bold", show.legend = FALSE) +
  scale_fill_gradient2(low = ST, mid = NEU, high = EL, midpoint = 0,
                       limits = c(-50, 50), oob = squish, na.value = "#efeeea",
                       name = "El-Sayed margin\nover Stevens (pts)",
                       breaks = c(-50,-25,0,25,50),
                       labels = c("-50","-25","tied","+25","+50")) +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = INK)) +
  guides(fill = guide_colourbar(barheight = unit(4.2,"cm"), barwidth = unit(.42,"cm"),
                                title.position = "top", ticks.colour = NA, frame.colour = NA)) +
  labs(
    title = "Education and income pulled in opposite directions",
    subtitle = paste0(
      "Each cell is the vote-weighted El-Sayed margin among precincts in that education and income band.\n",
      "Read DOWN a column: holding income roughly fixed, more educated precincts favoured El-Sayed.  ",
      "Read ACROSS a row: holding\neducation fixed, richer precincts favoured Stevens. ",
      "Raw cell means — no model, no controls beyond the grid itself."),
    x = "Mean household income (quintile)",
    y = "Bachelor's degree or higher (quintile)",
    caption = paste0(
      "2,856 precincts, 1,295,342 votes, from the 34 Michigan counties that reported precinct-level results. ",
      "n is precincts per cell.\n",
      "Education and income correlate at +0.77, so the off-diagonal corners are thin; cells under 15 precincts ",
      "are marked and greyed, and the low-education /\nhigh-income corner is empty. The bottom-left cell is ",
      "mostly heavily-Black precincts, where race rather than income drives the result.")
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.background = element_rect(fill = SRF, colour = NA),
    panel.background = element_rect(fill = SRF, colour = NA),
    panel.grid = element_blank(),
    axis.text = element_text(colour = INK2, size = 9),
    axis.title = element_text(colour = INK2, size = 9.5),
    axis.title.x = element_text(margin = margin(t = 9)),
    axis.title.y = element_text(margin = margin(r = 9)),
    legend.title = element_text(colour = INK2, size = 8.5, lineheight = 1.2),
    legend.text = element_text(colour = MUT, size = 8.5),
    plot.title = element_text(face = "bold", size = 16, colour = INK, margin = margin(b = 5)),
    plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.45, margin = margin(b = 14)),
    plot.caption = element_text(colour = MUT, size = 7.5, hjust = 0, lineheight = 1.4,
                                margin = margin(t = 12)),
    plot.caption.position = "plot", plot.title.position = "plot",
    plot.margin = margin(16, 20, 12, 14)
  )

ggsave("edu_income_grid_R.png", p, width = 10, height = 7, dpi = 200, bg = SRF)
ggsave("edu_income_grid_R.pdf", p, width = 10, height = 7, bg = SRF)
write_csv(g %>% select(ed, inc, margin, n, votes), "edu_income_grid.csv")
cat("wrote edu_income_grid_R.png / .pdf and edu_income_grid.csv\n")
print(g %>% select(ed, inc, margin, n) %>% tidyr::pivot_wider(names_from = inc, values_from = c(margin, n)),
      width = 200)
