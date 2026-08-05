# Precinct-level regressions: what predicted El-Sayed's margin over Stevens.
#
#   Rscript regressions.R
#
# Design notes
# ------------
# DV is the margin in PERCENTAGE POINTS (El-Sayed share minus Stevens share, x100).
# Predictors stay as proportions, so a coefficient is the point change in margin for a
# full 0-to-1 move; divide by 10 to read it per 10 percentage points.
#
# Weighted by votes cast: unweighted, a 30-vote precinct would count as much as a
# 2,000-vote one.
#
# SEs clustered by COUNTY. Precincts in a county share election administration, media
# markets and campaign effort, so treating 2,864 precincts as independent overstates
# precision. CAVEAT: only 34 counties reported precinct-level results, and 34 clusters
# is near the low end for cluster-robust inference, so a cluster bootstrap is run for
# the coefficients the argument rests on.
#
# Continuous predictors are centred at their VOTE-WEIGHTED means, so in the interaction
# model each main effect reads at the average precinct rather than at a nonexistent
# precinct with zero of everything.
#
# These are ecological relationships. Nothing here licenses an individual-level claim.

suppressPackageStartupMessages({
  library(dplyr); library(readr); library(fixest); library(car)
  library(modelsummary); library(ggplot2)
})
args <- commandArgs(FALSE); f <- grep("--file=", args, value = TRUE)
if (length(f)) setwd(dirname(normalizePath(sub("--file=", "", f[1]))))
set.seed(20260805)

d <- read_csv("../mi_precinct_demographics_2026.csv", show_col_types = FALSE) %>%
  filter(has_results, votes_total >= 25, !is.na(margin_elsayed))

X <- c("pct_vap_black","pct_vap_hisp","pct_vap_asian","pct_age_18_34","pct_age_65p",
       "pct_ba_plus","log_income","pct_foreign_born","log_density","pct_owner_occ",
       "pct_arab_ancestry","swing_pres_2020_2016","swing_pres_2024_2020")
dd <- d %>%
  select(all_of(X), margin_elsayed, votes_total, county_fips, jurisdiction, precinct_id) %>%
  filter(if_all(all_of(X), ~ !is.na(.))) %>%
  mutate(margin = margin_elsayed * 100, county = factor(county_fips))
cat(sprintf("N = %d precincts, %s votes, %d counties (clusters)\n\n",
            nrow(dd), format(sum(dd$votes_total), big.mark = ","), n_distinct(dd$county)))

wm  <- function(x) weighted.mean(x, dd$votes_total)
ctr <- sapply(dd[X], wm)
dd  <- dd %>% mutate(across(all_of(X), ~ . - wm(.), .names = "c_{.col}"))

BASE <- "c_pct_vap_black + c_pct_vap_hisp + c_pct_vap_asian + c_pct_age_18_34 +
         c_pct_age_65p + c_pct_ba_plus + c_log_income + c_pct_foreign_born +
         c_log_density + c_pct_owner_occ"
PAST <- "c_pct_arab_ancestry + c_swing_pres_2020_2016 + c_swing_pres_2024_2020"
INT  <- "c_pct_vap_black:c_pct_age_18_34"
fml  <- function(s) as.formula(paste("margin ~", s))

m1 <- feols(fml(BASE), dd, weights = ~votes_total, cluster = ~county)
m2 <- feols(fml(paste(BASE, "+ c_pct_arab_ancestry")), dd, weights = ~votes_total, cluster = ~county)
m3 <- feols(fml(paste(BASE, "+", PAST)), dd, weights = ~votes_total, cluster = ~county)
m4 <- feols(fml(paste(BASE, "+", PAST, "+", INT)), dd, weights = ~votes_total, cluster = ~county)
m5 <- feols(fml(paste(BASE, "+", PAST, "+", INT, "| county")), dd, weights = ~votes_total, cluster = ~county)

LAB <- c(
  "c_pct_vap_black"="Black share of VAP", "c_pct_vap_hisp"="Hispanic share of VAP",
  "c_pct_vap_asian"="Asian share of VAP", "c_pct_age_18_34"="Age 18-34 share",
  "c_pct_age_65p"="Age 65+ share", "c_pct_ba_plus"="Bachelor's degree or higher",
  "c_log_income"="Log mean household income", "c_pct_foreign_born"="Foreign-born share",
  "c_log_density"="Log population density", "c_pct_owner_occ"="Owner-occupied share",
  "c_pct_arab_ancestry"="Arab ancestry share",
  "c_swing_pres_2020_2016"="Presidential swing 2016-2020",
  "c_swing_pres_2024_2020"="Presidential swing 2020-2024",
  "c_pct_vap_black:c_pct_age_18_34"="Black x Age 18-34")
models <- list("(1) Demographics"=m1, "(2) + Arab"=m2, "(3) + Past vote"=m3,
               "(4) + Interaction"=m4, "(5) + County FE"=m5)

for (ext in c("txt","md"))
  modelsummary(models, coef_map = LAB, stars = c('*'=.05,'**'=.01,'***'=.001),
               gof_map = c("nobs","r.squared","adj.r.squared"),
               output = paste0("regression_table.", ext),
               title = paste("El-Sayed margin over Stevens in percentage points.",
                             "WLS by votes cast; SEs clustered by county."))
cat(readLines("regression_table.txt"), sep = "\n")

cat("\n\n--- Variance inflation factors, model 3 ---\n")
print(round(sort(vif(lm(fml(paste(BASE, "+", PAST)), dd)), decreasing = TRUE), 2))

# ---------- does the Black effect vary with age? ----------
cat("\n\n--- Marginal effect of Black VAP, across the age distribution ---\n")
cat("points of margin per 10-point rise in Black VAP share (model 4)\n")
b <- coef(m4); V <- vcov(m4)
qs <- c(.05,.25,.5,.75,.95)
age_q <- quantile(dd$pct_age_18_34, qs)          # dd$pct_* are the UNcentred originals
cage  <- as.numeric(age_q - ctr["pct_age_18_34"])
est <- (b["c_pct_vap_black"] + b[INT] * cage) / 10
se  <- sqrt(V["c_pct_vap_black","c_pct_vap_black"] + cage^2 * V[INT,INT] +
            2*cage*V["c_pct_vap_black",INT]) / 10
me <- data.frame(pctile = sprintf("%d%%", qs*100),
                 age_18_34 = sprintf("%.1f%%", age_q*100),
                 effect = round(est,2), lo = round(est-1.96*se,2), hi = round(est+1.96*se,2))
print(me, row.names = FALSE); write_csv(me, "interaction_marginal_effects.csv")

# a linear interaction can miss a threshold effect, so check the 2x2 directly
cat("\n--- Non-parametric check: mean margin by Black VAP x age quartile ---\n")
q2 <- dd %>%
  mutate(blk = cut(pct_vap_black, c(-1,.05,.25,.6,2),
                   labels = c("<5%","5-25%","25-60%",">60%")),
         age = cut(pct_age_18_34, quantile(pct_age_18_34, c(0,.33,.67,1)),
                   include.lowest = TRUE,
                   labels = c("young: low","mid","young: high"))) %>%
  group_by(blk, age) %>%
  summarise(margin = round(weighted.mean(margin, votes_total),1), n = n(), .groups="drop") %>%
  tidyr::pivot_wider(names_from = age, values_from = c(margin, n))
print(as.data.frame(q2), row.names = FALSE)

# The 2x2 shows the age gradient is ~+24 to +30 points in the first three Black-share
# bins and ~+5 in the >60% bin. A LINEAR interaction cannot represent "flat until 60%,
# then collapses", which is why model 4 reads as null. Model 6 tests the threshold form.
cat("\n--- Model 6: age interacted with a majority-Black indicator ---\n")
dd <- dd %>% mutate(maj_black = as.numeric(pct_vap_black > .60))
m6 <- feols(fml(paste(BASE, "+", PAST, "+ maj_black + maj_black:c_pct_age_18_34")),
            dd, weights = ~votes_total, cluster = ~county)
IX <- grep("maj_black", grep(":", rownames(coeftable(m6)), value=TRUE), value=TRUE)[1]
print(coeftable(m6)[c("c_pct_age_18_34","maj_black",IX),])
cat(sprintf("\nAge 18-34 gradient (points per 10-pt rise in young share):\n"))
ba <- coef(m6)["c_pct_age_18_34"]; bi <- coef(m6)[IX]
Vm <- vcov(m6)
cat(sprintf("  precincts under 60%% Black : %+.1f  (SE %.1f)\n", ba/10,
            sqrt(Vm["c_pct_age_18_34","c_pct_age_18_34"])/10))
cat(sprintf("  precincts over  60%% Black : %+.1f  (SE %.1f)\n", (ba+bi)/10,
            sqrt(Vm["c_pct_age_18_34","c_pct_age_18_34"] +
                 Vm[IX,IX] +
                 2*Vm["c_pct_age_18_34",IX])/10))
modelsummary(list("(4) Linear interaction"=m4, "(6) Threshold interaction"=m6),
             coef_map = c(LAB, "maj_black"="Majority Black (>60% VAP)",
                          "c_pct_age_18_34:maj_black"="Majority Black x Age 18-34"),
             stars = c('*'=.05,'**'=.01,'***'=.001),
             gof_map = c("nobs","r.squared","adj.r.squared"),
             output = "interaction_models.md")

# Caveat worth testing: young share in low-Black precincts partly means COLLEGE TOWNS,
# which is a different thing from young non-students in Detroit.
cat("\n--- Same threshold model, dropping the big college towns ---\n")
COLLEGE <- c("Ann Arbor","East Lansing","Ypsilanti","Mount Pleasant","Kalamazoo",
             "Big Rapids","Houghton","Marquette","Allendale Township","Ypsilanti Township")
dc <- dd %>% filter(!jurisdiction %in% COLLEGE)
m7 <- feols(fml(paste(BASE, "+", PAST, "+ maj_black + maj_black:c_pct_age_18_34")),
            dc, weights = ~votes_total, cluster = ~county)
cat(sprintf("  N = %d (dropped %d precincts)\n", nrow(dc), nrow(dd)-nrow(dc)))
IX7 <- grep("maj_black", grep(":", rownames(coeftable(m7)), value=TRUE), value=TRUE)[1]
print(coeftable(m7)[c("c_pct_age_18_34",IX7),])

# ---------- cluster bootstrap, since 34 clusters is few ----------
cat("\n--- Cluster bootstrap (2,000 resamples of counties), model 4 ---\n")
KEY <- c("c_pct_vap_black","c_pct_arab_ancestry","c_pct_ba_plus","c_pct_age_18_34", INT)
cl <- unique(dd$county)
bs <- replicate(2000, {
  s <- sample(cl, length(cl), TRUE)
  b <- do.call(rbind, lapply(s, function(k) dd[dd$county==k,]))
  tryCatch(coef(feols(fml(paste(BASE,"+",PAST,"+",INT)), b, weights=~votes_total))[KEY],
           error=function(e) rep(NA_real_,length(KEY)))
})
bt <- data.frame(term = LAB[KEY], estimate = round(coef(m4)[KEY],2),
                 analytic_se = round(se(m4)[KEY],2),
                 boot_se = round(apply(bs,1,sd,na.rm=TRUE),2),
                 lo = round(apply(bs,1,quantile,.025,na.rm=TRUE),2),
                 hi = round(apply(bs,1,quantile,.975,na.rm=TRUE),2))
print(bt, row.names = FALSE); write_csv(bt, "cluster_bootstrap.csv")

# Where a predictor lives in only a few counties, resampling counties is brutal.
cat("\n--- Concentration of each key predictor across the 34 counties ---\n")
conc <- sapply(c("pct_arab_ancestry","pct_vap_black","pct_ba_plus","pct_age_18_34"), function(v){
  by_cty <- dd %>% group_by(county) %>%
    summarise(s = sum(.data[[v]] * votes_total), .groups="drop") %>% arrange(desc(s))
  round(sum(head(by_cty$s,1))/sum(by_cty$s), 3)
})
print(data.frame(predictor = names(conc), share_in_top_county = conc), row.names = FALSE)

# ---------- figure: the youth gradient, inside and outside majority-Black precincts ----------
EL <- "#4a3aa7"; ST <- "#eb6834"; INK <- "#0b0b0b"; INK2 <- "#52514e"
MUT <- "#898781"; GRD <- "#e1e0d9"; SRF <- "#fcfcfb"
pf <- dd %>%
  mutate(grp = factor(maj_black, 0:1,
                      c("Under 60% Black VAP", "Majority Black (>60% VAP)"))) %>%
  filter(pct_age_18_34 <= quantile(pct_age_18_34, .99))
bins <- pf %>% group_by(grp) %>% arrange(pct_age_18_34, .by_group = TRUE) %>%
  mutate(b = cut(cumsum(votes_total)/sum(votes_total), seq(0,1,length.out=13),
                 include.lowest=TRUE, labels=FALSE)) %>%
  group_by(grp, b) %>%
  summarise(x = weighted.mean(pct_age_18_34, votes_total),
            y = weighted.mean(margin, votes_total),
            v = sum(votes_total), .groups="drop")
g <- ggplot(pf, aes(pct_age_18_34, margin)) +
  geom_hline(yintercept = 0, colour = MUT, linewidth = .4) +
  geom_point(aes(size = votes_total), colour = MUT, alpha = .13, stroke = 0) +
  geom_smooth(aes(weight = votes_total), method = "lm", formula = y~x, se = TRUE,
              colour = EL, fill = EL, alpha = .13, linewidth = .9) +
  geom_point(data = bins, aes(x, y), colour = INK, fill = SRF, shape = 21,
             size = 2.4, stroke = .9) +
  facet_wrap(~grp) +
  scale_x_continuous(labels = scales::percent_format(accuracy = 1)) +
  scale_y_continuous(labels = function(v) paste0(v, " pts"), limits = c(-100,100)) +
  scale_size_area(max_size = 4.5, guide = "none") +
  labs(title = "The youth premium disappears in majority-Black precincts",
       subtitle = paste0("El-Sayed's margin against the 18-34 share of population. Model 6 gradient: ",
                         "+5.9 points per 10-point rise in the young share outside\nmajority-Black precincts, ",
                         "+0.8 (indistinguishable from zero) inside them. Dropping the big college towns ",
                         "strengthens the contrast rather than explaining it."),
       x = "Age 18-34 share of population", y = "El-Sayed margin over Stevens",
       caption = paste0("Dots are precincts, area = votes cast; hollow circles are vote-weighted means ",
                        "within 12 equal-weight bins; line is a weighted linear fit with 95% band.\n",
                        "The plotted lines are UNCONDITIONAL, so they are steeper than the model-6 ",
                        "gradients quoted above, which hold race, education, income, age 65+,\n",
                        "nativity, density, tenure, Arab ancestry and both presidential swings fixed. ",
                        "Axis trimmed at the 99th percentile of the young share.")) +
  theme_minimal(base_size = 11) +
  theme(plot.background = element_rect(fill = SRF, colour = NA),
        panel.background = element_rect(fill = SRF, colour = NA),
        panel.grid.minor = element_blank(),
        panel.grid.major = element_line(colour = GRD, linewidth = .3),
        panel.spacing.x = unit(1.4, "lines"),
        strip.text = element_text(face = "bold", hjust = 0, size = 11, colour = INK,
                                  margin = margin(b = 6)),
        axis.text = element_text(colour = MUT, size = 8.5),
        axis.title = element_text(colour = INK2, size = 9.5),
        plot.title = element_text(face = "bold", size = 15, colour = INK, margin = margin(b = 5)),
        plot.subtitle = element_text(colour = INK2, size = 9, lineheight = 1.45,
                                     margin = margin(b = 12)),
        plot.caption = element_text(colour = MUT, size = 7.5, hjust = 0, lineheight = 1.35,
                                    margin = margin(t = 10)),
        plot.caption.position = "plot", plot.title.position = "plot",
        plot.margin = margin(16, 20, 12, 14))
ggsave("interaction_black_age.png", g, width = 10, height = 5.4, dpi = 200, bg = SRF)
ggsave("interaction_black_age.pdf", g, width = 10, height = 5.4, bg = SRF)
cat("\nwrote interaction_black_age.png / .pdf\n")

saveRDS(models, "models.rds")
cat("\nwrote regression_table.txt/.md, interaction_marginal_effects.csv, cluster_bootstrap.csv\n")
