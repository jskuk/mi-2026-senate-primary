# Michigan 2026 U.S. Senate Democratic primary — what predicts El-Sayed's margin.
# Vote-weighted precinct scatter with a binscatter overlay, faceted by predictor.
#
#   Rscript make_figures.R
#
# Colours: violet = El-Sayed, orange = Stevens. Deliberately NOT blue/red — both
# candidates are Democrats, so partisan colours would misread. The pair was checked
# for colour-vision-deficiency separation (CVD dE 29.5, well clear of the 8 threshold).
#
# r is printed in the panel strip rather than inside the plot: with 2,864 points
# there is no reliably empty corner to put it in.

suppressPackageStartupMessages({
  library(ggplot2); library(dplyr); library(tidyr); library(scales); library(readr)
})

args <- commandArgs(FALSE)
f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

EL_SAYED <- "#4a3aa7"; STEVENS <- "#eb6834"; NEUTRAL <- "#b9b8b2"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUTED <- "#898781"
GRID <- "#e1e0d9"; SURFACE <- "#fcfcfb"

PANELS <- tribble(
  ~key,                   ~label,
  "pct_vap_black",        "Black share of voting-age population",
  "pct_age_18_34",        "Age 18–34 share of population",
  "pct_ba_plus",          "Bachelor's degree or higher",
  "pct_arab_ancestry",    "Arab ancestry share (ACS)",
  "swing_pres_2020_2016", "Presidential swing 2016 → 2020",
  "swing_pres_2024_2020", "Presidential swing 2020 → 2024"
)

d <- read_csv("figure_data.csv", show_col_types = FALSE)

long <- d %>%
  select(jurisdiction, votes_total, margin_elsayed, all_of(PANELS$key)) %>%
  pivot_longer(all_of(PANELS$key), names_to = "key", values_to = "x") %>%
  filter(!is.na(x), !is.na(margin_elsayed)) %>%
  left_join(PANELS, by = "key")

wcor <- function(x, y, w) {
  mx <- weighted.mean(x, w); my <- weighted.mean(y, w)
  weighted.mean((x - mx) * (y - my), w) /
    sqrt(weighted.mean((x - mx)^2, w) * weighted.mean((y - my)^2, w))
}

# --- statistics on the FULL data, before any axis trimming ---
stats <- long %>%
  group_by(key, label) %>%
  summarise(r = wcor(x, margin_elsayed, votes_total),
            lo = quantile(x, .01), hi = quantile(x, .99), .groups = "drop") %>%
  mutate(pad = (hi - lo) * .04, lo = lo - pad, hi = hi + pad,
         strip = sprintf("%s  (r = %+.2f)", label, r))

# --- binscatter on the full data too ---
binned <- long %>%
  group_by(key) %>% arrange(x, .by_group = TRUE) %>%
  mutate(bin = cut(cumsum(votes_total) / sum(votes_total),
                   breaks = seq(0, 1, length.out = 21),
                   include.lowest = TRUE, labels = FALSE)) %>%
  group_by(key, bin) %>%
  summarise(x = weighted.mean(x, votes_total),
            y = weighted.mean(margin_elsayed, votes_total), .groups = "drop") %>%
  left_join(stats %>% select(key, strip, lo, hi), by = "key") %>%
  filter(x >= lo, x <= hi)

long <- long %>% left_join(stats %>% select(key, strip, lo, hi), by = "key")
n_trim <- sum(long$x < long$lo | long$x > long$hi)
plotted <- long %>% filter(x >= lo, x <= hi)

lev <- stats$strip[match(PANELS$key, stats$key)]
plotted$strip <- factor(plotted$strip, levels = lev)
binned$strip  <- factor(binned$strip,  levels = lev)

p <- ggplot(plotted, aes(x, margin_elsayed)) +
  geom_hline(yintercept = 0, colour = MUTED, linewidth = 0.4) +
  geom_point(aes(size = votes_total, colour = margin_elsayed), alpha = 0.28, stroke = 0) +
  geom_smooth(aes(weight = votes_total), method = "lm", formula = y ~ x,
              se = FALSE, colour = INK, linewidth = 0.6, linetype = "22") +
  geom_line(data = binned, aes(x, y), colour = INK, linewidth = 0.9) +
  geom_point(data = binned, aes(x, y), colour = INK, fill = SURFACE,
             shape = 21, size = 2.3, stroke = 0.9) +
  scale_colour_gradient2(low = STEVENS, mid = NEUTRAL, high = EL_SAYED,
                         midpoint = 0, limits = c(-1, 1), guide = "none") +
  scale_size_area(max_size = 5, guide = "none") +
  scale_x_continuous(labels = percent_format(accuracy = 1), n.breaks = 5,
                     expand = expansion(mult = .02)) +
  scale_y_continuous(labels = percent_format(accuracy = 1),
                     limits = c(-1, 1), breaks = seq(-1, 1, .5)) +
  facet_wrap(~strip, scales = "free_x", ncol = 3) +
  labs(
    title = "What predicted Abdul El-Sayed's margin, precinct by precinct",
    subtitle = paste0(
      "Michigan 2026 U.S. Senate Democratic primary · ", format(nrow(d), big.mark = ","),
      " precincts, ", format(sum(d$votes_total), big.mark = ","),
      " votes · dot area = votes cast · violet = El-Sayed led, orange = Stevens led\n",
      "Black line: vote-weighted mean within 20 equal-weight bins.  Dashed: weighted linear fit.  ",
      "r is vote-weighted."),
    x = NULL, y = "El-Sayed margin over Stevens",
    caption = paste0(
      "Axes trimmed to the 1st–99th percentile of each predictor (", n_trim,
      " of ", format(nrow(long), big.mark = ","),
      " point-panels off-scale); all statistics computed on the full data.\n",
      "Demographics: 2020 Census P.L. 94-171 and ACS 2019–2023. Past vote: VEST/ALARM and ",
      "Redistricting Data Hub, reallocated onto 2026 precincts via census blocks.")
  ) +
  theme_minimal(base_size = 11) +
  theme(
    plot.background  = element_rect(fill = SURFACE, colour = NA),
    panel.background = element_rect(fill = SURFACE, colour = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(colour = GRID, linewidth = .3),
    panel.spacing.x  = unit(1.4, "lines"), panel.spacing.y = unit(1.6, "lines"),
    strip.text   = element_text(face = "bold", hjust = 0, size = 10,
                                colour = INK, margin = margin(b = 6)),
    axis.text    = element_text(colour = MUTED, size = 8.5),
    axis.title.y = element_text(colour = INK2, size = 9.5, margin = margin(r = 8)),
    plot.title    = element_text(face = "bold", size = 15.5, colour = INK,
                                 margin = margin(b = 5)),
    plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.4,
                                 margin = margin(b = 14)),
    plot.caption  = element_text(colour = MUTED, size = 7.5, hjust = 0,
                                 lineheight = 1.35, margin = margin(t = 12)),
    plot.caption.position = "plot", plot.title.position = "plot",
    plot.margin = margin(16, 20, 12, 14)
  )

ggsave("elsayed_predictors_R.png", p, width = 11.5, height = 8, dpi = 200, bg = SURFACE)
ggsave("elsayed_predictors_R.pdf", p, width = 11.5, height = 8, bg = SURFACE)
cat(sprintf("wrote elsayed_predictors_R.png / .pdf  (%d point-panels trimmed)\n", n_trim))
print(stats %>% select(label, r) %>% arrange(desc(abs(r))), n = 6)
