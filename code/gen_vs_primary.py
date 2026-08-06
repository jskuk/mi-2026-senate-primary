"""General-election turnout vs primary turnout, by age of a precinct's registrants.

All three elections divided by the same denominator (2024 L2 registered voters) and
all counting ALL ballots, both parties, so the three are directly comparable.
"""
import pandas as pd, numpy as np
B = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'

g = pd.read_csv(f'{B}/mi_sen_dem_primary_2026_with_republican_turnout_'
                'priority_counties_2026-08-06.csv')
g = g[(g.geography_type == 'precinct') & g.TOTAL_TURNOUT_MEASURE.notna()][
    ['GEO_KEY', 'TOTAL_TURNOUT_MEASURE']]
t = pd.read_csv('turnout_by_age_precincts.csv')[
    ['precinct_id','pct_reg_young','reg_all','voted_all','votes_total','p20220802','total_reg']]
d = pd.read_csv(f'{B}/precinct_demographics/mi_precinct_demographics_2026.csv')[
    ['precinct_id','pres24_total','registered']]
r = t.merge(d, on='precinct_id').merge(g, left_on='precinct_id', right_on='GEO_KEY', how='inner')
r = r[r.pres24_total > 0].copy()
r['q'] = pd.qcut(r.pct_reg_young, 5, labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest'])
print(f'{len(r)} precincts, {r.votes_total.sum():,.0f} Democratic primary votes')
print(f"\n{'':<13}{'young':>7}{'Nov24 GEN':>11}{'Aug24 PRI':>11}{'Aug26 PRI':>11}")
for k, s in r.groupby('q', observed=True):
    print(f'  {k:<11}{np.average(s.pct_reg_young, weights=s.votes_total):>7.2f}'
          f'{s.pres24_total.sum()/s.reg_all.sum():>11.3f}'
          f'{s.voted_all.sum()/s.reg_all.sum():>11.3f}'
          f'{s.TOTAL_TURNOUT_MEASURE.sum()/s.reg_all.sum():>11.3f}')
o, y = r[r.q == 'Q1 oldest'], r[r.q == 'Q5 youngest']
f = lambda s, c, den: s[c].sum()/s[den].sum()
print(f"\nyoungest/oldest:  Nov-2024 general {f(y,'pres24_total','reg_all')/f(o,'pres24_total','reg_all'):.2f}"
      f" | Aug-2024 primary {f(y,'voted_all','reg_all')/f(o,'voted_all','reg_all'):.2f}"
      f" | Aug-2026 primary {f(y,'TOTAL_TURNOUT_MEASURE','reg_all')/f(o,'TOTAL_TURNOUT_MEASURE','reg_all'):.2f}")
r.to_csv('gen_vs_primary.csv', index=False)
