"""Primary turnout measured against the DEMOCRATIC general-election vote.

Why this replaces the all-party version as the headline measure
--------------------------------------------------------------
The earlier measure divided 2026 Democratic primary votes by TOTAL August-2024 primary
voters. That denominator is contaminated: Michigan runs an open primary, and in older,
more Republican precincts a large share of August-2024 primary voters took a Republican
ballot. Those precincts show an Aug-2024 primary electorate 94% the size of their Harris
electorate, against 45% in the youngest precincts - a gap only Republican ballots can
explain. Dividing by it penalises old precincts and flatters young ones.

Using Harris 2024 as the denominator puts a Democratic number on both sides and is
immune to that. It is a proxy, not an identity: Michigan has no party registration, so
some Harris voters are independents who would never take a Democratic primary ballot,
and anyone may take one.

The two measures answer different questions and both are true:
  * vs 2024 primary voters  -> GROWTH in primary participation. Young precincts grew most.
  * vs 2024 Harris voters   -> CONVERSION of Democratic general voters into primary
                               voters. Young precincts convert worst.
Young precincts grew fastest from the smallest base and still show up least.
"""
import json
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026/precinct_demographics'
OUT  = f'{BASE}/analysis'

t = pd.read_csv(f'{OUT}/turnout_by_age_precincts.csv')[
    ['precinct_id','pct_reg_young','reg_all','voted_all','votes_total']]
d = pd.read_csv(f'{BASE}/mi_precinct_demographics_2026.csv')[
    ['precinct_id','pres24_harris','pres24_trump','pres24_dem2p']]
r = t.merge(d, on='precinct_id')
r = r[(r.pres24_harris > 0) & r.pct_reg_young.notna()].copy()
r['q'] = pd.qcut(r.pct_reg_young, 5, labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest'])
print(f'{len(r)} precincts, {r.votes_total.sum():,.0f} primary votes\n')

rows = []
for k, s in r.groupby('q', observed=True):
    rows.append(dict(
        group=k,
        young=np.average(s.pct_reg_young, weights=s.votes_total),
        dem2p=np.average(s.pres24_dem2p, weights=s.votes_total),
        harris=int(s.pres24_harris.sum()), primary=int(s.votes_total.sum()),
        aug24=int(s.voted_all.sum()),
        dem_based=s.votes_total.sum()/s.pres24_harris.sum(),
        all_party=s.votes_total.sum()/s.voted_all.sum(),
        aug24_over_harris=s.voted_all.sum()/s.pres24_harris.sum()))
t5 = pd.DataFrame(rows)
tot = dict(group='STATEWIDE', young=np.average(r.pct_reg_young, weights=r.votes_total),
           dem2p=np.average(r.pres24_dem2p, weights=r.votes_total),
           harris=int(r.pres24_harris.sum()), primary=int(r.votes_total.sum()),
           aug24=int(r.voted_all.sum()),
           dem_based=r.votes_total.sum()/r.pres24_harris.sum(),
           all_party=r.votes_total.sum()/r.voted_all.sum(),
           aug24_over_harris=r.voted_all.sum()/r.pres24_harris.sum())

print('2026 Democratic primary votes as a share of the 2024 DEMOCRATIC (Harris) vote')
print(f"{'':<13}{'young reg':>10}{'Dem 2-pty':>11}{'Harris 24':>12}{'2026 Dem':>11}"
      f"{'CONVERSION':>12}{'growth':>9}{'Aug24/Har':>11}")
for x in rows + [tot]:
    print(f"  {x['group']:<11}{x['young']:>10.3f}{x['dem2p']:>11.3f}{x['harris']:>12,}"
          f"{x['primary']:>11,}{x['dem_based']:>12.3f}{x['all_party']:>9.3f}"
          f"{x['aug24_over_harris']:>11.2f}")
print('\n  CONVERSION falls with youth (0.61 -> 0.51); growth rises (0.65 -> 1.13).')
print('  Aug24/Harris shows why growth is misleading: in the oldest precincts the')
print('  Aug-2024 primary was 94% the size of the Harris vote, against 45% in the')
print('  youngest - Republican ballots inflating the growth denominator.')

# does it survive restricting to Democratic precincts? (i.e. is it only partisanship?)
h = r[r.pres24_dem2p > .70].copy()
h['q'] = pd.qcut(h.pct_reg_young, 5, labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest'])
print(f'\nWithin >70% Democratic precincts (n={len(h)}), where Republican ballots cannot')
print('be the explanation, conversion still falls with youth:')
demrows = []
for k, s in h.groupby('q', observed=True):
    demrows.append(dict(group=k, young=np.average(s.pct_reg_young, weights=s.votes_total),
                        dem_based=s.votes_total.sum()/s.pres24_harris.sum(),
                        all_party=s.votes_total.sum()/s.voted_all.sum()))
    print(f"  {k:<11} young {demrows[-1]['young']:.3f} | conversion "
          f"{demrows[-1]['dem_based']:.3f} | growth {demrows[-1]['all_party']:.3f}")
print('\n  So partisanship explains part of the gap but not all of it: even among')
print('  Democratic precincts, older ones convert general voters into primary')
print('  voters at 0.59 against 0.47 for the youngest.')

t5.to_csv(f'{OUT}/dem_turnout_quintiles.csv', index=False)
js = json.load(open(f'{OUT}/turnout_series.json'))
js['dem_based'] = dict(
    rows=[dict(k=x['group'], young=round(x['young'],4), dem2p=round(x['dem2p'],4),
               harris=x['harris'], primary=x['primary'],
               conv=round(x['dem_based'],4), growth=round(x['all_party'],4),
               aug_over_har=round(x['aug24_over_harris'],4)) for x in rows],
    total=dict(conv=round(tot['dem_based'],4), growth=round(tot['all_party'],4),
               harris=tot['harris'], primary=tot['primary']),
    dem70=[dict(k=x['group'], young=round(x['young'],4), conv=round(x['dem_based'],4),
                growth=round(x['all_party'],4)) for x in demrows])
json.dump(js, open(f'{OUT}/turnout_series.json','w'), separators=(',',':'))
print(f'\nwrote dem_turnout_quintiles.csv and updated turnout_series.json')
