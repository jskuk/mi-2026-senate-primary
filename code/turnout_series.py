"""August-primary turnout, 2018-2026, split by how young a precinct's registrants are.

ALL BALLOTS in every year, including 2026. Earlier drafts had to compare all-party
turnout in 2018-2024 against Democratic-only ballots in 2026, and worked around it by
restricting to Democratic-leaning precincts. The county-PDF file supplies 2026
Republican gubernatorial votes and reported poll-book ballot totals, so 2026 can now be
counted the same way as every other year and the restriction is gone.

That mattered: Michigan runs an open primary, and among these precincts 47% of 2026
ballots in the oldest fifth were Republican against 21% in the youngest. Dividing
Democratic-only 2026 ballots by registration flattered young precincts badly.

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

# 2026 total ballots, from the county-PDF compilation. Keep only rows whose measure is a
# real reported poll-book count; the alternative is a valid-votes proxy that misses
# undervotes, and mixing two definitions in one series is what this file exists to avoid.
gop = pd.read_csv(f'{BASE}/mi_sen_dem_primary_2026_with_republican_turnout_2026-08-06.csv')
# Keep any row with a turnout measure, not only reported poll-book counts. The stricter
# filter would also drop Washtenaw and Ingham - Ann Arbor and East Lansing - which for an
# age analysis is a worse problem than the proxy's missing undervotes. Reported-only
# gives 0.61 rather than 0.66 on the headline ratio.
gop = gop[(gop.geography_type == 'precinct') & gop.TOTAL_TURNOUT_MEASURE.notna()][
          ['GEO_KEY', 'TOTAL_TURNOUT_MEASURE']]
r = r.merge(gop, left_on='precinct_id', right_on='GEO_KEY', how='inner')
print(f'restricted to {len(r)} precincts with a 2026 total-ballot count '
      f'({r.votes_total.sum():,.0f} Democratic votes)')
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
        rows[k][2026] = s.TOTAL_TURNOUT_MEASURE.sum() / den   # ALL 2026 ballots
    t = pd.DataFrame(rows).T[[2018, 2020, 2022, 2024, 2026]]
    print(label)
    print('  share of 2024-registered voters who cast an August-primary ballot')
    print('  ' + ''.join(f'{y:>9}' for y in t.columns))
    for k, row in t.iterrows():
        print(f'  {k:<12}' + ''.join(f'{v*100:>8.1f}%' for v in row))
    ratio = t.loc['Q5 youngest'] / t.loc['Q1 oldest']
    print('  youngest / oldest ratio' + ''.join(f'{v:>8.2f} ' for v in ratio))
    return t, ratio

t_all, ratio_all = series(r, 'ALL PRECINCTS  - every year counts ALL primary ballots')
print()
h = r[r.pres24_dem2p > .70]
t_dem, ratio_dem = series(h, f'Democratic-leaning precincts only, for comparison with the '
                             f'earlier draft (n={len(h)})')

def wc(x, y, w):
    m = x.notna() & y.notna(); x, y, w = x[m], y[m], w[m]
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return np.average((x-mx)*(y-my), weights=w)/np.sqrt(
        np.average((x-mx)**2, weights=w)*np.average((y-my)**2, weights=w))
print('\nCorrelation of young-registrant share with each year\'s turnout, all precincts:')
for c, y in list(AUG.items()):
    print(f'  {y}: {wc(r[c]/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}')
print(f'  2024: {wc(r.voted_all/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}')
print(f'  2026: {wc(r.TOTAL_TURNOUT_MEASURE/r.reg_all, r.pct_reg_young, r.votes_total):+.3f}')
print('\nAnd with the 2026-vs-prior-year ratio:')
for c, y in list(AUG.items()) + [('voted_all', 2024)]:
    v = r.votes_total / r[c].replace(0, np.nan)
    v2 = r.TOTAL_TURNOUT_MEASURE / r[c].replace(0, np.nan)
    print(f'  2026 / {y}: {wc(v2, r.pct_reg_young, r.votes_total):+.3f}')

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
