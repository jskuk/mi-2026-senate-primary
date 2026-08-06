# What decided the 2026 Michigan U.S. Senate Democratic primary

**→ [Read the interactive report](https://jskuk.github.io/mi-2026-senate-primary/)**

Precinct-level analysis of Abdul El-Sayed vs Haley Stevens vs Mallory McMorrow,
joining 2,864 reporting precincts to exact 2020 Census demographics, ACS estimates,
and three presidential elections reallocated onto 2026 precinct boundaries.

## Coverage — read this first

Only **34 of Michigan's 83 counties** reported results at the precinct level. The
other 49 reported county totals only and are **excluded from the entire analysis**.
That drops 205,533 votes, 13.7% of everything reported, and the omission is not
random — the missing counties are disproportionately rural, and Stevens led them
48.8% to 46.0% while El-Sayed leads the included precincts 49.0% to 47.2%. Treat
everything here as a description of Michigan's urban and suburban electorate.

## Three findings

**The 2020 Census codes Middle Eastern and North African respondents as White.**
Dearborn's precincts are 86% "white" by Census race, 41% Arab by ACS ancestry, and
voted 78% for El-Sayed. A specification using race alone reads that as *El-Sayed's
base is white voters* — exactly backwards. Adding Arab ancestry to the regression
doesn't refine it, it rewrites it: Asian share goes from −69.4\* to +8.7 (n.s.),
foreign-born flips from +55.4 to −46.3.

**The pooled 2020→2024 swing coefficient is a Simpson's paradox.** Across all
precincts, El-Sayed ran better where Democrats lost ground (r = −0.25). Among the
96% of precincts at or under 10% Arab ancestry the sign flips to +0.18. The pooled
figure is produced entirely by 115 precincts holding 4.5% of the vote.

**Education and income pulled in opposite directions.** Holding education roughly
fixed, richer precincts favoured Stevens; holding income fixed, more educated
precincts favoured El-Sayed. Among the most educated fifth of precincts he wins the
poorest income band by 50 points and the richest by 3. This survives matching on
race and age and excluding college towns — 18 of 18 matched jurisdiction pairs run
the same way — though the gap shrinks from about 21 points to about 12 once age is
held constant. See `edu_income_grid_R.png` and `code/income_check.py`.

**The youth premium disappears in majority-Black precincts.** A linear Black × age
interaction is null (−1.5, SE 64), but that is a functional-form artefact: the age
gradient is +24 to +30 points across the first three Black-share bins and +4.8 in
the >60% bin. A threshold specification gives +5.9 points per 10-point rise in the
young share outside majority-Black precincts against +0.8 inside them
(interaction −51.0, SE 19.3, p = 0.012). Dropping the ten largest college towns
strengthens it rather than explaining it.

## For a general audience

Two charts written for readers rather than analysts. `public_places.png` names the
towns — Ferndale and Birmingham sit seven miles apart on Woodward Avenue, Birmingham
is the *more* educated of the two and more than twice as rich, and they voted 83
points apart. `public_grid.png` is the same finding as a five-by-five grid with the
jargon stripped out.

**Young voters closed a quarter of the primary turnout gap — from a very low base.**
Counting *all* primary ballots in every year, the youngest fifth of precincts turned
out at 0.54–0.61 of the oldest fifth's rate across 2018, 2020, 2022 and 2024, then
0.67 in 2026. The youngest fifth still voted 12 points below the oldest. Everyone
turned out more in 2026; the young simply rose faster, 1.46× against 1.18×.
Counting Democratic ballots alone would badly flatter young precincts: Michigan runs
an open primary and 47% of 2026 ballots in the oldest fifth were Republican, against
21% in the youngest. Voter-file rates for August 2024 show the depth of the hole —
registered 65–74s voted at 47.5%, registered 20–24s at 8.0%.

## What's here

| Path | Contents |
| --- | --- |
| `index.html` | The interactive report |
| `regression_table.md` | Six models, WLS by votes, SEs clustered by county |
| `public_places.png`, `public_grid.png` | Charts for a general audience |
| `turnout_series_R.png` | August-primary turnout by age, 2018-2026 |
| `*_R.png` | Analyst figures (PDFs in the working repo) |
| `code/income_check.py` | Non-parametric check on the education/income result |
| `code/` | Full pipeline: census parsing, block assignment, reallocation, figures, regressions |

The precinct data file itself is not published here. Everything in `code/` rebuilds
it from public sources.

## Method

Demographics are exact counts from the 2020 Census P.L. 94-171 file, with all
254,730 census blocks assigned to 2026 precincts by internal point — not
interpolated from voting districts, which silently drops ~530,000 people whose 2020
VTDs had no 2026 successor. ACS 2019–2023 variables are allocated from block group
or tract weighted by block population. Past-vote results (VEST/ALARM for 2016 and
2020, Redistricting Data Hub for 2024) were reallocated onto 2026 boundaries through
the same blocks, weighted by block voting-age population; every contest carries
through at 100% of its statewide total. The crosswalk was validated independently
against actual 2026 registration (r = 0.985, median error +0.8%).

Regressions are weighted by votes cast with standard errors clustered by county.
Only 34 clusters exist, so a cluster bootstrap accompanies the key coefficients; it
agrees for education and Black share but **not** for Arab ancestry, whose magnitude
is weakly identified because 52% of the relevant population sits in one county.

These are ecological relationships. Nothing here supports an individual-level claim.

## Sources

2020 Census P.L. 94-171 · TIGER/Line 2020 tabblock20 · ACS 2019–2023 5-year
table-based summary files · Michigan 2026 Voting Precincts shapefile ·
[VoteHub](https://votehub.com) 2026 primary results ·
[VEST](https://dataverse.harvard.edu/dataverse/electionscience) /
[ALARM Project](https://github.com/alarm-redist/census-2020) ·
[Redistricting Data Hub](https://redistrictingdatahub.org/state/michigan/),
*Michigan 2024 General Election Precinct-Level Results and Boundaries*.

RDH and VEST ask that you cite them and the underlying state source.
