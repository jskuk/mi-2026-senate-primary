"""August-primary turnout, 2018-2026, split by how young a precinct's registrants are.

Starts at 2018: the first Trump-era midterm primary, and also the earliest year whose
L2 vote-history attribution is defensible (see the caveat below).

The 2010-2022 L2 file carries only total voter counts per election - no age brackets -
so age here is a precinct CHARACTERISTIC (share of registrants aged 18-34, taken from
the 2024 L2 file), not a voter-level measure. The voter-level age rates live in
turnout_by_age.py and exist for 2024 only.

Every year is divided by the SAME denominator (2024 L2 registered, `reg_all`) so the
series is internally comparable. Levels are therefore "share of today's registrants who
voted in year X", not the turnout rate reported at the time.

CAVEAT: L2 attributes vote history to a person's address at the SNAPSHOT date. The
2010-2022 file was snapshotted in Apr 2023, so 2022 is well attributed, 2018 less so,
and 2016 is a decade of residential moves away. Read the early years as indicative.
"""
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
OUT  = f'{BASE}/precinct_demographics/analysis'

AUG = {'p20180807': 2018, 'p20200804': 2020, 'p20220802': 2022}  # Trump-era August primaries

xw = pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet').rename(
    columns={'PrecinctID': 'precinct_id'}).dropna(subset=['precinct_id'])
xw['GEOCODE'] = xw.GEOCODE.astype(str)

hist = pd.read_csv(f'{BASE}/mi_turnout_2010to2022_elc_2020_block_request/'
                   'mi_turnout_2010to2022_elc_2020_block.csv',
                   usecols=['geoid20'] + list(AUG), dtype={'geoid20': str})
YOUNG = ['18_19', '20_24', '25_29', '30_34']
l2 = pd.read_csv(f'{BASE}/MI_l2_2024_pri_stats_2020block/MI_l2_2024_pri_stats_2020block.csv',
                 usecols=['geoid20', 'voted_all', 'reg_all'] + [f'{p_}_age_{a}' for a in
                          ['18_19','20_24','25_29','30_34','35_44','45_54','55_64','65_74','75_84','85over']
                          for p_ in ('reg','voted')],
                 dtype={'geoid20': str})

b = xw.merge(hist, left_on='GEOCODE', right_on='geoid20', how='left') \
      .merge(l2, on='geoid20', how='left')
num = [c for c in b.columns if c not in ('GEOCODE', 'precinct_id', 'geoid20')]
p = b.groupby('precinct_id', as_index=False)[num].sum()

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
r = d.merge(p, on='precinct_id', how='left')
r = r[r.has_results & (r.votes_total >= 25) & (r.reg_all > 0)].copy()
r['pct_reg_young'] = r[[f'reg_age_{a}' for a in YOUNG]].sum(axis=1) / r.reg_all
print(f'{len(r)} precincts, {r.votes_total.sum():,.0f} votes in the 2026 primary\n')

def series(df, label):
    q = df.assign(g=pd.qcut(df.pct_reg_young, 5,
                            labels=['Q1 oldest', 'Q2', 'Q3', 'Q4', 'Q5 youngest']))
    rows = {}
    for k, s in q.groupby('g', observed=True):
        den = s.reg_all.sum()
        rows[k] = {y: s[c].sum() / den for c, y in AUG.items()}
        rows[k][2024] = s.voted_all.sum() / den
        rows[k][2026] = s.votes_total.sum() / den
    t = pd.DataFrame(rows).T[[2018, 2020, 2022, 2024, 2026]]
    print(label)
    print('  share of 2024-registered voters who cast an August-primary ballot')
    print('  ' + ''.join(f'{y:>9}' for y in t.columns))
    for k, row in t.iterrows():
        print(f'  {k:<12}' + ''.join(f'{v*100:>8.1f}%' for v in row))
    ratio = t.loc['Q5 youngest'] / t.loc['Q1 oldest']
    print('  youngest / oldest ratio' + ''.join(f'{v:>8.2f} ' for v in ratio))
    return t, ratio

t_all, ratio_all = series(r, 'ALL PRECINCTS  (2026 column is Democratic ballots only)')
print()
h = r[r.pres24_dem2p > .70]
t_dem, ratio_dem = series(h, f'HEAVILY DEMOCRATIC PRECINCTS ONLY, 2024 Dem two-party > 70%  '
                             f'(n={len(h)}, {h.votes_total.sum():,.0f} votes)')

def wc(x, y, w):
    m = x.notna() & y.notna(); x, y, w = x[m], y[m], w[m]
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return np.average((x-mx)*(y-my), weights=w)/np.sqrt(
        np.average((x-mx)**2, weights=w)*np.average((y-my)**2, weights=w))
print('\nCorrelation of young-registrant share with each year\'s turnout, all precincts:')
for c, y in list(AUG.items()):
    print(f'  {y}: {wc(r[c]/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}')
print(f'  2024: {wc(r.voted_all/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}')
print(f'  2026: {wc(r.votes_total/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}   '
      '<- Democratic ballots only')
print('\nAnd with the 2026-vs-prior-year ratio:')
for c, y in list(AUG.items()) + [('voted_all', 2024)]:
    v = r.votes_total / r[c].replace(0, np.nan)
    print(f'  2026 / {y}: {wc(v, r.pct_reg_young, r.votes_total):+.3f}')

import json
YEARS = [2018, 2020, 2022, 2024, 2026]
payload = dict(
    years=YEARS,
    all=dict(n=int(len(r)), votes=int(r.votes_total.sum()),
             rows=[dict(k=k, young=round(float(np.average(
                 r.assign(g=pd.qcut(r.pct_reg_young,5,labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest']))
                  .query("g == @k").pct_reg_young,
                 weights=r.assign(g=pd.qcut(r.pct_reg_young,5,labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest']))
                  .query("g == @k").votes_total)),4),
                 v=[round(float(t_all.loc[k, y]),5) for y in YEARS]) for k in t_all.index]),
    dem=dict(n=int(len(h)), votes=int(h.votes_total.sum()),
             rows=[dict(k=k, young=round(float(np.average(
                 h.assign(g=pd.qcut(h.pct_reg_young,5,labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest']))
                  .query("g == @k").pct_reg_young,
                 weights=h.assign(g=pd.qcut(h.pct_reg_young,5,labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest']))
                  .query("g == @k").votes_total)),4),
                 v=[round(float(t_dem.loc[k, y]),5) for y in YEARS]) for k in t_dem.index]),
    ratio_all=[round(float(ratio_all[y]),4) for y in YEARS],
    ratio_dem=[round(float(ratio_dem[y]),4) for y in YEARS],
    age2024=[dict(age=a.replace('_','-').replace('85over','85+'),
                  turnout=round(float(r[f'voted_age_{a}'].sum()/r[f'reg_age_{a}'].sum()),4),
                  reg=int(r[f'reg_age_{a}'].sum()))
             for a in ['18_19','20_24','25_29','30_34','35_44','45_54','55_64','65_74','75_84','85over']])
json.dump(payload, open(f'{OUT}/turnout_series.json','w'), separators=(',',':'))
print('wrote turnout_series.json')

t_all.to_csv(f'{OUT}/turnout_series_all.csv')
t_dem.to_csv(f'{OUT}/turnout_series_dem70.csv')
print(f'\nwrote turnout_series_all.csv and turnout_series_dem70.csv')
