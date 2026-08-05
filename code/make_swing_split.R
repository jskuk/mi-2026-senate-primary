# The 2020 -> 2024 presidential swing, split by Arab ancestry share.
#
#   Rscript make_swing_split.R
#
# Point: the negative swing/El-Sayed relationship in the pooled data is carried
# entirely by 115 precincts (4.5% of votes). Below a 10% Arab-ancestry threshold
# the sign REVERSES. This is a Simpson's paradox, not a robustness footnote.
#
# NOTE: x-scales differ across panels by design — each subset occupies a very
# different swing range, and forcing a common scale would collapse the middle
# panel into a sliver. Read each panel's slope, not their relative widths.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(scales); library(readr)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

EL_SAYED <- "#4a3aa7"; STEVENS <- "#eb6834"; NEUTRAL <- "#b9b8b2"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUTED <- "#898781"
GRID <- "#e1e0d9"; SURFACE <- "#fcfcfb"

d <- read_csv("swing_split_data.csv", show_col_types = FALSE) %>%
  filter(!is.na(swing_pres_2024_2020), !is.na(pct_arab_ancestry), !is.na(margin_elsayed))

subsets <- bind_rows(
  d %>% mutate(grp = "All precincts"),
  d %>% filter(pct_arab_ancestry <= .10) %>% mutate(grp = "Arab ancestry 10% or less"),
  d %>% filter(pct_arab_ancestry >  .10) %>% mutate(grp = "Arab ancestry above 10%")
)

wcor <- function(x, y, w) {
  mx <- weighted.mean(x, w); my <- weighted.mean(y, w)
  weighted.mean((x - mx) * (y - my), w) /
    sqrt(weighted.mean((x - mx)^2, w) * weighted.mean((y - my)^2, w))
}

stats <- subsets %>%
  group_by(grp) %>%
  summarise(r = wcor(swing_pres_2024_2020, margin_elsayed, votes_total),
            n = n(), votes = sum(votes_total),
            lo = quantile(swing_pres_2024_2020, .01),
            hi = quantile(swing_pres_2024_2020, .99), .groups = "drop") %>%
  mutate(pad = (hi - lo) * .05, lo = lo - pad, hi = hi + pad,
         strip = sprintf("%s\nr = %+.2f  ·  %s precincts, %s votes",
                         grp, r, format(n, big.mark = ","), format(votes, big.mark = ",")))

binned <- subsets %>%
  left_join(stats %>% select(grp, strip), by = "grp") %>%
  group_by(grp) %>% arrange(swing_pres_2024_2020, .by_group = TRUE) %>%
  mutate(nb = if_else(grp == "Arab ancestry above 10%", 10, 20),
         bin = cut(cumsum(votes_total) / sum(votes_total),
                   breaks = seq(0, 1, length.out = first(nb) + 1),
                   include.lowest = TRUE, labels = FALSE)) %>%
  group_by(grp, strip, bin) %>%
  summarise(x = weighted.mean(swing_pres_2024_2020, votes_total),
            y = weighted.mean(margin_elsayed, votes_total), .groups = "drop")

plotted <- subsets %>%
  left_join(stats %>% select(grp, strip, lo, hi), by = "grp") %>%
  filter(swing_pres_2024_2020 >= lo, swing_pres_2024_2020 <= hi)

lev <- stats$strip[match(c("All precincts", "Arab ancestry 10% or less",
                           "Arab ancestry above 10%"), stats$grp)]
plotted$strip <- factor(plotted$strip, levels = lev)
binned$strip  <- factor(binned$strip,  levels = lev)

p <- ggplot(plotted, aes(swing_pres_2024_2020, margin_elsayed)) +
  geom_hline(yintercept = 0, colour = MUTED, linewidth = .4) +
  geom_vline(xintercept = 0, colour = GRID, linewidth = .4) +
  geom_point(aes(size = votes_total, colour = margin_elsayed), alpha = .28, stroke = 0) +
  geom_smooth(aes(weight = votes_total), method = "lm", formula = y ~ x, se = FALSE,
              colour = INK, linewidth = .6, linetype = "22") +
  geom_line(data = binned, aes(x, y), colour = INK, linewidth = .9) +
  geom_point(data = binned, aes(x, y), colour = INK, fill = SURFACE,
             shape = 21, size = 2.3, stroke = .9) +
  scale_colour_gradient2(low = STEVENS, mid = NEUTRAL, high = EL_SAYED,
                         midpoint = 0, limits = c(-1, 1), guide = "none") +
  scale_size_area(max_size = 5, guide = "none") +
  scale_x_continuous(labels = percent_format(accuracy = 1), n.breaks = 5) +
  scale_y_continuous(labels = percent_format(accuracy = 1),
                     limits = c(-1, 1), breaks = seq(-1, 1, .5)) +
  facet_wrap(~strip, scales = "free_x", ncol = 3) +
  labs(
    title = "Drop 115 precincts and the swing relationship reverses sign",
    subtitle = paste0(
      "Presidential swing 2020 → 2024 against El-Sayed's primary margin, Michigan 2026 U.S. Senate Democratic primary.\n",
      "Pooled, El-Sayed ran better where Democrats LOST ground (r = -0.25). Among the 96% of precincts under 10% Arab\n",
      "ancestry the sign flips to +0.18: he ran better where Democrats GAINED. The pooled result is a Simpson's paradox."),
    x = "Democratic two-party swing, 2020 → 2024   (left = moved toward Republicans)",
    y = "El-Sayed margin over Stevens",
    caption = paste0(
      "Dot area = votes cast · violet = El-Sayed led, orange = Stevens led · black line = vote-weighted mean ",
      "within equal-weight bins · dashed = weighted linear fit.\n",
      "x-scales differ by panel: each subset spans a very different swing range, and a common scale would collapse ",
      "the middle panel. Compare slopes, not panel widths.\n",
      "Axes trimmed to the 1st–99th percentile within each subset; statistics computed on all precincts in the subset.")
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.background = element_rect(fill = SURFACE, colour = NA),
    panel.background = element_rect(fill = SURFACE, colour = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(colour = GRID, linewidth = .3),
    panel.spacing.x = unit(1.5, "lines"),
    strip.text = element_text(face = "bold", hjust = 0, size = 10, colour = INK,
                              lineheight = 1.45, margin = margin(b = 7)),
    axis.text = element_text(colour = MUTED, size = 8.5),
    axis.title = element_text(colour = INK2, size = 9.5),
    axis.title.x = element_text(margin = margin(t = 9)),
    axis.title.y = element_text(margin = margin(r = 8)),
    plot.title = element_text(face = "bold", size = 15.5, colour = INK, margin = margin(b = 5)),
    plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.45, margin = margin(b = 14)),
    plot.caption = element_text(colour = MUTED, size = 7.5, hjust = 0, lineheight = 1.35,
                                margin = margin(t = 12)),
    plot.caption.position = "plot", plot.title.position = "plot",
    plot.margin = margin(16, 20, 12, 14)
  )

ggsave("swing_split_R.png", p, width = 11.5, height = 5.6, dpi = 200, bg = SURFACE)
ggsave("swing_split_R.pdf", p, width = 11.5, height = 5.6, bg = SURFACE)
cat("wrote swing_split_R.png / .pdf\n")
print(stats %>% select(grp, n, votes, r))
