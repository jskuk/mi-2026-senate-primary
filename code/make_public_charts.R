# Public-facing pair: the same finding, written for a general reader.
#
#   Rscript make_public_charts.R
#
# Two differences from the analyst versions:
#   1. Named places do the work. A reader who knows Ferndale and Birmingham needs no
#      statistics to see the point.
#   2. Everything an analyst wants and a reader does not - cell counts, quintile
#      language, "margin" as a term of art - is gone or moved to a footnote.

suppressPackageStartupMessages({
  library(dplyr); library(readr); library(ggplot2); library(scales); library(ggrepel)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))

EL <- "#4a3aa7"; ST <- "#eb6834"; NEU <- "#efeeea"
INK <- "#0b0b0b"; INK2 <- "#52514e"; MUT <- "#898781"; GRD <- "#e1e0d9"; SRF <- "#fcfcfb"
FOOT <- paste(
  "Michigan reported precinct-level results in only 34 of its 83 counties, mostly urban and suburban ones,",
  "so rural voters are under-represented.\nSome of the income gap is really age: richer suburbs skew older,",
  "and holding age constant cuts it roughly in half. Sources: Michigan Secretary of State via VoteHub,",
  "2020 Census, American Community Survey 2019-2023.")

d <- read_csv("../mi_precinct_demographics_2026.csv", show_col_types = FALSE) %>%
  filter(has_results, votes_total >= 25,
         !is.na(margin_elsayed), !is.na(pct_ba_plus), !is.na(mean_hh_income))

# ---------------------------------------------------------------- chart 1: places
j <- d %>%
  group_by(jurisdiction) %>%
  summarise(votes = sum(votes_total),
            inc = weighted.mean(mean_hh_income, votes_total) / 1000,
            ba  = weighted.mean(pct_ba_plus, votes_total) * 100,
            mar = (sum(`C_TOT_Abdul_El-Sayed`) - sum(`C_TOT_Haley_Stevens`)) / sum(votes_total) * 100,
            .groups = "drop") %>%
  filter(ba >= 45, votes >= 2000) %>%
  mutate(short = gsub(" Township$", " Twp.", jurisdiction))

SHOW <- c("Ypsilanti","East Lansing","Ferndale","Traverse City","Royal Oak","Ann Arbor",
          "Berkley","Canton Township","Troy","Rochester Hills","Novi","Northville Township",
          "Huntington Woods","Bloomfield Township","Birmingham","West Bloomfield Township","Saline")
lab  <- j %>% filter(jurisdiction %in% SHOW)
mark <- j %>% filter(jurisdiction %in% c("Ferndale","Birmingham"))

# preempt the obvious objection: is this just university towns?
UNI <- c("Ann Arbor","East Lansing","Ypsilanti")
jn  <- j %>% filter(!jurisdiction %in% UNI)
r_all <- cov.wt(j[c("inc","mar")],  wt = j$votes,  cor = TRUE)$cor[1,2]
r_nou <- cov.wt(jn[c("inc","mar")], wt = jn$votes, cor = TRUE)$cor[1,2]

p1 <- ggplot(j, aes(inc, mar)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = 0, ymax = Inf, fill = EL, alpha = .045) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = -Inf, ymax = 0, fill = ST, alpha = .045) +
  geom_hline(yintercept = 0, colour = MUT, linewidth = .5) +
  annotate("text", x = 67, y = 3.5, label = "EL-SAYED AHEAD", hjust = 0, size = 2.9,
           colour = EL, fontface = "bold") +
  annotate("text", x = 67, y = -4, label = "STEVENS AHEAD", hjust = 0, size = 2.9,
           colour = ST, fontface = "bold") +
  geom_smooth(aes(weight = votes), method = "lm", formula = y ~ x, se = FALSE,
              colour = INK, linewidth = .7, linetype = "22") +
  geom_point(aes(size = votes, fill = mar), shape = 21, colour = SRF, stroke = .8, alpha = .92) +
  geom_point(data = mark, aes(size = votes), shape = 21, fill = NA, colour = INK, stroke = 1.15) +
  geom_text_repel(data = lab, aes(label = short), size = 3.15, colour = INK,
                  seed = 12, min.segment.length = .1, box.padding = .5, point.padding = .3,
                  segment.colour = MUT, segment.size = .3, max.overlaps = 30) +
  annotate("label", x = 258, y = 52, hjust = 1, vjust = 1, size = 3.05, colour = INK2,
           lineheight = 1.3, label.size = 0, fill = SRF, alpha = .85,
           label = paste("Ferndale and Birmingham sit seven miles apart",
                         "on Woodward Avenue. Birmingham is the MORE",
                         "educated of the two - 77% of adults hold a degree,",
                         "against 58% - and more than twice as rich.",
                         "They voted 83 points apart. (circled)", sep = "\n")) +
  scale_fill_gradient2(low = ST, mid = NEU, high = EL, midpoint = 0, guide = "none") +
  scale_size_area(max_size = 11, guide = "none") +
  scale_x_continuous(labels = function(v) paste0("$", v, "k"),
                     breaks = seq(75, 250, 25), limits = c(65, 260)) +
  scale_y_continuous(breaks = seq(-30, 45, 15), limits = c(-40, 56),
                     labels = function(v) ifelse(v == 0, "tie",
                              ifelse(v > 0, paste0("+", v), as.character(v)))) +
  labs(
    title = "Among Michigan's most educated communities, the richer ones broke for Stevens",
    subtitle = paste0(
      "Every place shown is in Michigan's top third for college degrees - at least 45% of adults hold one.\n",
      "Each bubble is a city or township in the August 2026 Democratic Senate primary; bubble size is votes cast."),
    x = "Average household income", y = "Winning margin, percentage points",
    caption = paste0(
      "The pattern is not just university towns: drop Ann Arbor, East Lansing and Ypsilanti and the ",
      "correlation moves only from ", sprintf("%.2f to %.2f", r_all, r_nou), ".\n", FOOT)) +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = GRD, linewidth = .3),
        axis.text = element_text(colour = MUT, size = 9),
        axis.title = element_text(colour = INK2, size = 10),
        axis.title.x = element_text(margin = margin(t = 8)),
        axis.title.y = element_text(margin = margin(r = 6)),
        plot.title = element_text(face = "bold", size = 16.5, colour = INK, margin = margin(b = 6)),
        plot.subtitle = element_text(colour = INK2, size = 10, lineheight = 1.45, margin = margin(b = 16)),
        plot.caption = element_text(colour = MUT, size = 7.5, hjust = 0, lineheight = 1.4,
                                    margin = margin(t = 14)),
        plot.caption.position = "plot", plot.title.position = "plot",
        plot.margin = margin(18, 22, 12, 16))
ggsave("public_places.png", p1, width = 11, height = 7.4, dpi = 200, bg = SRF)
ggsave("public_places.pdf", p1, width = 11, height = 7.4, bg = SRF)

# ---------------------------------------------------------------- chart 2: the grid
eb <- quantile(d$pct_ba_plus, seq(0,1,.2)); ib <- quantile(d$mean_hh_income, seq(0,1,.2))
ED <- c("Fewest\ncollege grads","","Middle","","Most\ncollege grads")
IN <- c("Poorest","","Middle","","Richest")
g <- d %>%
  mutate(e = cut(pct_ba_plus, eb, include.lowest = TRUE, labels = FALSE),
         i = cut(mean_hh_income, ib, include.lowest = TRUE, labels = FALSE)) %>%
  group_by(e, i) %>%
  summarise(mar = weighted.mean(margin_elsayed, votes_total) * 100, n = n(), .groups = "drop") %>%
  tidyr::complete(e = 1:5, i = 1:5) %>%
  mutate(thin = is.na(n) | n < 15,
         shown = ifelse(thin, NA, mar),
         lab = ifelse(is.na(n), "no places\nlike this",
               ifelse(n < 15, "too few\nto say",
                      ifelse(mar > 0, paste0("El-Sayed\n+", round(mar)),
                                      paste0("Stevens\n+", round(abs(mar)))))))

p2 <- ggplot(g, aes(factor(i), factor(e))) +
  geom_tile(aes(fill = shown), colour = SRF, linewidth = 2.4) +
  geom_text(aes(label = lab, colour = !is.na(shown) & abs(shown) > 26),
            size = 3.2, lineheight = 1.1, fontface = "bold", show.legend = FALSE) +
  scale_fill_gradient2(low = ST, mid = NEU, high = EL, midpoint = 0, limits = c(-50, 50),
                       oob = squish, na.value = "#eeedea", name = NULL,
                       breaks = c(-45, 0, 45),
                       labels = c("Stevens\nby 45", "tied", "El-Sayed\nby 45")) +
  scale_colour_manual(values = c(`TRUE` = "white", `FALSE` = INK)) +
  scale_x_discrete(labels = IN) + scale_y_discrete(labels = ED) +
  guides(fill = guide_colourbar(barheight = unit(4.6,"cm"), barwidth = unit(.45,"cm"),
                                ticks.colour = NA, frame.colour = NA)) +
  labs(
    title = "A college degree pushed one way. Money pushed back.",
    subtitle = paste0(
      "Read DOWN a column: education rises, income stays put, and El-Sayed does better.\n",
      "Read ACROSS a row: income rises, education stays put, and Stevens does better.\n",
      "Along the top row alone, El-Sayed's lead falls from 43 points to 3 as income climbs."),
    x = "Average household income  →", y = "Share of adults with a college degree  →",
    caption = paste0("Michigan's cities and townships grouped into five equal bands on each measure. ",
                     "The two measures overlap heavily, so a few\ncombinations barely exist. ",
                     "The poorest, least-educated square is mostly Black neighbourhoods, where race ",
                     "rather than income drove the result.\n", FOOT)) +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid = element_blank(),
        axis.text = element_text(colour = INK2, size = 9.5, lineheight = 1.1),
        axis.title = element_text(colour = INK2, size = 10),
        axis.title.x = element_text(margin = margin(t = 10)),
        axis.title.y = element_text(margin = margin(r = 10)),
        legend.text = element_text(colour = MUT, size = 8, lineheight = 1.1),
        plot.title = element_text(face = "bold", size = 17, colour = INK, margin = margin(b = 6)),
        plot.subtitle = element_text(colour = INK2, size = 9.5, lineheight = 1.45, margin = margin(b = 16)),
        plot.caption = element_text(colour = MUT, size = 7.5, hjust = 0, lineheight = 1.4,
                                    margin = margin(t = 14)),
        plot.caption.position = "plot", plot.title.position = "plot",
        plot.margin = margin(18, 22, 12, 16))
ggsave("public_grid.png", p2, width = 10.5, height = 7.2, dpi = 200, bg = SRF)
ggsave("public_grid.pdf", p2, width = 10.5, height = 7.2, bg = SRF)

cat("wrote public_places.png/.pdf and public_grid.png/.pdf\n")
cat(sprintf("chart 1: %d places, %s votes | corr %+.2f, without university towns %+.2f\n",
            nrow(j), format(sum(j$votes), big.mark = ","), r_all, r_nou))
