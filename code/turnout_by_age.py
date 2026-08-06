"""Primary turnout by age, from L2 voter-file counts aggregated to 2026 precincts.

Two sources, both already at 2020 Census blocks, so they aggregate to 2026 precincts
exactly - no interpolation:
  * MI_l2_2024_pri_stats_2020block  - Aug 6 2024 primary, voted/registered by AGE BRACKET
  * mi_turnout_2010to2022...        - voter counts for every election 2010-2022

The age brackets matter: they give the actual turnout rate of registered young voters,
rather than inferring it from a precinct's census population age mix.

CAVEAT from L2's own README: vote history is tied to individuals and aggregated to
where they live AT THE SNAPSHOT DATE, not where they lived at the time of the election.
Movers are credited to their current block. The 2024 file's snapshot is two months
after its election, so attribution is tight; the 2022 file's snapshot (Apr 2023) is
eight months after Aug 2022 but five years after Aug 2018, so older columns degrade.
"""
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
OUT  = f'{BASE}/precinct_demographics/analysis'

xw = pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet').rename(
    columns={'PrecinctID': 'precinct_id'}).dropna(subset=['precinct_id'])
xw['GEOCODE'] = xw.GEOCODE.astype(str)

AGES = ['18_19','20_24','25_29','30_34','35_44','45_54','55_64','65_74','75_84','85over']
cols = ['geoid20','voted_all','reg_all'] + [f'{p}_age_{a}' for a in AGES for p in ('voted','reg')]
l2 = pd.read_csv(f'{BASE}/MI_l2_2024_pri_stats_2020block/MI_l2_2024_pri_stats_2020block.csv',
                 usecols=cols, dtype={'geoid20': str})
print(f'2024 L2 blocks: {len(l2):,} | registered {l2.reg_all.sum():,} | voted {l2.voted_all.sum():,} '
      f'({l2.voted_all.sum()/l2.reg_all.sum()*100:.1f}%)')

hist = pd.read_csv(f'{BASE}/mi_turnout_2010to2022_elc_2020_block_request/'
                   'mi_turnout_2010to2022_elc_2020_block.csv',
                   usecols=['geoid20','total_reg','p20220802','p20200804','p20180807'],
                   dtype={'geoid20': str})
print(f'2010-2022 blocks: {len(hist):,} | Aug-2022 primary voters {hist.p20220802.sum():,}')

b = (xw.merge(l2, left_on='GEOCODE', right_on='geoid20', how='left')
       .merge(hist, on='geoid20', how='left', suffixes=('','_h')))
num = [c for c in b.columns if c not in ('GEOCODE','precinct_id','geoid20')]
p = b.groupby('precinct_id', as_index=False)[num].sum()
print(f'aggregated to {len(p)} precincts')

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
m = d.merge(p, on='precinct_id', how='left')
r = m[m.has_results & (m.votes_total >= 25) & (m.reg_all > 0)].copy()
print(f'analysis set: {len(r)} precincts, {r.votes_total.sum():,.0f} votes\n')

# ---- 1. actual turnout by age, Aug 2024 primary (no ecological inference) ----
print('AUG 2024 PRIMARY turnout by age of REGISTERED VOTER (L2 counts, analysis precincts)')
rows = []
for a in AGES:
    v, g = r[f'voted_age_{a}'].sum(), r[f'reg_age_{a}'].sum()
    rows.append(dict(age=a.replace('_','-').replace('85over','85+'), registered=g, voted=v,
                     turnout=v/g if g else np.nan))
t = pd.DataFrame(rows)
for _, x in t.iterrows():
    print(f'  {x.age:<8} registered {x.registered:>9,.0f}   voted {x.voted:>9,.0f}   '
          f'turnout {x.turnout*100:>5.1f}%')
t.to_csv(f'{OUT}/turnout_by_age_2024.csv', index=False)

# ---- 2. young share: voter file vs census ----
r['young_reg'] = r[[f'reg_age_{a}' for a in ['18_19','20_24','25_29','30_34']]].sum(axis=1)
r['pct_reg_young'] = r.young_reg / r.reg_all
def wc(x, y, w):
    m_ = x.notna() & y.notna(); x, y, w = x[m_], y[m_], w[m_]
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return np.average((x-mx)*(y-my), weights=w)/np.sqrt(
        np.average((x-mx)**2, weights=w)*np.average((y-my)**2, weights=w))
w = r.votes_total
print(f'\nyoung share of REGISTERED voters (18-34): {np.average(r.pct_reg_young, weights=w):.3f}')
print(f'young share of CENSUS population (18-34):  {np.average(r.pct_age_18_34, weights=w):.3f}')
print(f'correlation between the two measures: {wc(r.pct_reg_young, r.pct_age_18_34, w):+.3f}')

# ---- 3. turnout deltas ----
r['t24'] = r.voted_all / r.reg_all
r['t22'] = r.p20220802 / r.total_reg.replace(0, np.nan)
r['prim26_over_24'] = r.votes_total / r.voted_all.replace(0, np.nan)
r['prim26_over_22'] = r.votes_total / r.p20220802.replace(0, np.nan)
print('\nTURNOUT DELTA vs young share  (r, vote-weighted)')
print(f"{'measure':<46}{'vs registered-young':>21}{'vs census-young':>17}")
for c, lab in [('prim26_over_24','2026 Dem primary votes / Aug-2024 primary voters'),
               ('prim26_over_22','2026 Dem primary votes / Aug-2022 primary voters'),
               ('t24','Aug-2024 primary turnout rate'),
               ('t22','Aug-2022 primary turnout rate'),
               ('primary_turnout_of_pres24','2026 primary votes / 2024 presidential votes')]:
    print(f'  {lab:<44}{wc(r[c], r.pct_reg_young, w):>+21.3f}{wc(r[c], r.pct_age_18_34, w):>+17.3f}')

q = r.assign(g=pd.qcut(r.pct_reg_young, 5, labels=['Q1 oldest','Q2','Q3','Q4','Q5 youngest']))
print('\nby quintile of YOUNG REGISTERED share:')
print(f"{'':<13}{'young reg':>10}{'2024 turnout':>14}{'2022 turnout':>14}{'26/24':>9}{'26/22':>9}")
for k, s in q.groupby('g', observed=True):
    print(f'  {k:<11}{np.average(s.pct_reg_young,weights=s.votes_total):>10.3f}'
          f'{s.voted_all.sum()/s.reg_all.sum():>14.3f}'
          f'{s.p20220802.sum()/s.total_reg.sum():>14.3f}'
          f'{s.votes_total.sum()/s.voted_all.sum():>9.3f}'
          f'{s.votes_total.sum()/s.p20220802.sum():>9.3f}')

keep = ['precinct_id','jurisdiction','votes_total','margin_elsayed','pct_age_18_34','pct_reg_young',
        'reg_all','voted_all','t24','t22','prim26_over_24','prim26_over_22','p20220802','total_reg'] \
       + [f'{p_}_age_{a}' for a in AGES for p_ in ('voted','reg')]
r[keep].to_csv(f'{OUT}/turnout_by_age_precincts.csv', index=False)
print(f'\nwrote turnout_by_age_2024.csv and turnout_by_age_precincts.csv')
