"""Presidential winner sequence 2016-2020-2024, and how each primary candidate did there.

Winner is two-party (D vs R) in each year, so eight possible sequences.

Confidence intervals: the votes are a census, not a sample, so a binomial interval
on ~200k votes would be meaninglessly tight and would answer the wrong question.
The real uncertainty is between-precinct heterogeneity - how much a differently
drawn set of precincts of this type might differ - so the interval is a
nonparametric bootstrap resampling PRECINCTS with replacement (2,000 draws),
recomputing the aggregate share each time. Percentile method.
"""
import json, os
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
FIG  = f'{BASE}/precinct_demographics/figures'
os.makedirs(FIG, exist_ok=True)
rng = np.random.default_rng(20260805)

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
need = ['pres16_clinton','pres16_trump','pres20_biden','pres20_trump',
        'pres24_harris','pres24_trump','C_TOT_Abdul_El-Sayed','C_TOT_Haley_Stevens',
        'C_TOT_Mallory_McMorrow','votes_total']
r = d[d.has_results & (d.votes_total >= 25)].dropna(subset=need).copy()
print(f'precincts with all three elections + results: {len(r)} | votes {r.votes_total.sum():,.0f}')

r['w16'] = np.where(r.pres16_clinton > r.pres16_trump, 'D', 'R')
r['w20'] = np.where(r.pres20_biden   > r.pres20_trump, 'D', 'R')
r['w24'] = np.where(r.pres24_harris  > r.pres24_trump, 'D', 'R')
r['combo'] = r.w16 + r.w20 + r.w24

CAND = {'C_TOT_Abdul_El-Sayed':'elsayed', 'C_TOT_Haley_Stevens':'stevens',
        'C_TOT_Mallory_McMorrow':'mcmorrow'}

def boot(sub, col, B=2000):
    v = sub[col].values; t = sub.votes_total.values
    n = len(sub)
    idx = rng.integers(0, n, size=(B, n))
    num = v[idx].sum(axis=1); den = t[idx].sum(axis=1)
    s = num / np.where(den == 0, np.nan, den)
    return np.nanpercentile(s, [2.5, 97.5])

order = ['DDD','DDR','DRD','DRR','RDD','RDR','RRD','RRR']
rows = []
for c in order:
    sub = r[r.combo == c]
    if len(sub) == 0:
        print(f'  {c}: none'); continue
    tot = sub.votes_total.sum()
    rec = dict(combo=c, n_precincts=len(sub), votes=int(tot),
               share_of_votes=tot / r.votes_total.sum())
    for col, name in CAND.items():
        rec[name] = sub[col].sum() / tot
        if len(sub) >= 3:
            lo, hi = boot(sub, col)
        else:
            lo = hi = np.nan
        rec[name + '_lo'], rec[name + '_hi'] = lo, hi
    rows.append(rec)

t = pd.DataFrame(rows)
t['margin'] = t.elsayed - t.stevens
print()
hdr = f"{'combo':<7}{'precincts':>10}{'votes':>11}{'%of vote':>10}   {'El-Sayed':>22}   {'Stevens':>22}"
print(hdr); print('-' * len(hdr))
for _, x in t.iterrows():
    print(f"{x.combo:<7}{x.n_precincts:>10,}{x.votes:>11,}{x.share_of_votes*100:>9.1f}%"
          f"   {x.elsayed*100:>6.1f}% [{x.elsayed_lo*100:>4.1f}, {x.elsayed_hi*100:>4.1f}]"
          f"   {x.stevens*100:>6.1f}% [{x.stevens_lo*100:>4.1f}, {x.stevens_hi*100:>4.1f}]")

t.to_csv(f'{FIG}/winner_combos.csv', index=False)
LBL = {'D':'Dem','R':'Rep'}
payload = dict(
    total_votes=int(r.votes_total.sum()), total_precincts=int(len(r)),
    rows=[dict(combo=x.combo,
               parts=[LBL[ch] for ch in x.combo],
               n=int(x.n_precincts), votes=int(x.votes),
               share_of_votes=round(float(x.share_of_votes), 5),
               cands=[dict(k='elsayed', v=round(float(x.elsayed), 5),
                           lo=round(float(x.elsayed_lo), 5), hi=round(float(x.elsayed_hi), 5)),
                      dict(k='stevens', v=round(float(x.stevens), 5),
                           lo=round(float(x.stevens_lo), 5), hi=round(float(x.stevens_hi), 5))],
               mcmorrow=round(float(x.mcmorrow), 5))
          for _, x in t.iterrows()])
json.dump(payload, open(f'{FIG}/winner_combos.json', 'w'), separators=(',', ':'))
r[['precinct_id','jurisdiction','combo','votes_total','C_TOT_Abdul_El-Sayed',
   'C_TOT_Haley_Stevens','C_TOT_Mallory_McMorrow','pct_arab_ancestry',
   'pct_vap_black','pct_ba_plus']].to_csv(f'{FIG}/winner_combos_precincts.csv', index=False)
print(f'\nwrote winner_combos.csv / .json')
