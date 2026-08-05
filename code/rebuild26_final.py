"""Step 2: final 2026-precinct file — exact P.L. demographics + ACS + primary results.

Unit of analysis is the 2026 voting precinct itself: the shapefile vintage matches
the election, so every VoteHub precinct joins 1:1 and no geography is collapsed.
"""
import os, warnings
import pandas as pd, geopandas as gpd, numpy as np
warnings.filterwarnings('ignore')

SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
OUT  = f'{BASE}/precinct_demographics'

g = gpd.read_file(f'{BASE}/shapefile26/2026_Voting_Precincts.shp')
g['geometry'] = g.geometry.buffer(0)
g = g.rename(columns={'PrecinctID': 'precinct_id', 'CountyFIPS': 'county_fips',
                      'PrecinctLo': 'precinct_label', 'Jurisdicti': 'jurisdiction',
                      'ActiveVote': 'active_voters', 'Registered': 'registered',
                      'VTD': 'vtd'})
for c in ['registered', 'active_voters']:
    g[c] = pd.to_numeric(g[c], errors='coerce')
g = g.merge(pd.read_parquet(f'{SCR}/precinct2026_demographics.parquet')
              .rename(columns={'PrecinctID': 'precinct_id'}), on='precinct_id', how='left')

# ---------- ACS pushed down to precincts, weighted by 2020 block population ----------
xw = (pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet')
        .rename(columns={'PrecinctID': 'precinct_id'})
        .merge(pd.read_parquet(f'{SCR}/blocks_pop.parquet'), on='GEOCODE', how='left'))
xw['bg']    = xw.GEOCODE.str[:12]
xw['tract'] = xw.GEOCODE.str[:11]

def acs(table, keep):
    d = pd.read_csv(f'{SCR}/acs/{table}_mi.psv', sep='|', dtype={'GEO_ID': str})
    d = d[[c for c in d.columns if c == 'GEO_ID' or c in keep]]
    d['geo'] = d.GEO_ID.str.split('US').str[1]
    return d.drop(columns='GEO_ID')

def push_down(d, level, cols):
    key = 'bg' if level == 'bg' else 'tract'
    x = xw.merge(d.rename(columns={'geo': key}), on=key, how='left')
    tot = x.groupby(key)['pop_blk'].transform('sum')
    w = np.where(tot > 0, x.pop_blk / tot.replace(0, np.nan), 0)
    for c in cols:
        x[c] = pd.to_numeric(x[c], errors='coerce').clip(lower=0) * w
    return x.groupby('precinct_id')[cols].sum()

e = acs('b15003', [f'B15003_E{i:03d}' for i in range(1, 26)])
e['edu_total']      = e['B15003_E001']
e['edu_ba_plus']    = e[[f'B15003_E{i:03d}' for i in (22, 23, 24, 25)]].sum(axis=1)
e['edu_hs_or_less'] = e[[f'B15003_E{i:03d}' for i in range(2, 19)]].sum(axis=1)
edu = push_down(e, 'bg', ['edu_total', 'edu_ba_plus', 'edu_hs_or_less'])

a = acs('b01001', [f'B01001_E{i:03d}' for i in range(1, 50)])
a['age_total'] = a['B01001_E001']
a['age_18_34'] = a[[f'B01001_E{i:03d}' for i in (7,8,9,10,11,12,31,32,33,34,35,36)]].sum(axis=1)
a['age_65p']   = a[[f'B01001_E{i:03d}' for i in list(range(20,26)) + list(range(44,50))]].sum(axis=1)
age = push_down(a, 'bg', ['age_total', 'age_18_34', 'age_65p'])

inc = acs('b19025', ['B19025_E001']).rename(columns={'B19025_E001': 'agg_hh_income'})
hh  = acs('b11001', ['B11001_E001']).rename(columns={'B11001_E001': 'households'})
income = push_down(inc.merge(hh, on='geo'), 'bg', ['agg_hh_income', 'households'])

n = acs('b05002', ['B05002_E001', 'B05002_E013']).rename(
    columns={'B05002_E001': 'nativity_total', 'B05002_E013': 'foreign_born'})
nat = push_down(n, 'tract', ['nativity_total', 'foreign_born'])          # tract-level source

t = acs('b25003', ['B25003_E001', 'B25003_E002']).rename(
    columns={'B25003_E001': 'tenure_total', 'B25003_E002': 'owner_occ'})
ten = push_down(t, 'bg', ['tenure_total', 'owner_occ'])

# Arab is the key variable: the 2020 Census codes MENA respondents as White, so
# race alone cannot identify El-Sayed's base. B04006_005 is "American" — Arab is _006.
# Chaldean (_017) is kept separate: large in metro Detroit, politically distinct.
anc = acs('b04006', ['B04006_E001', 'B04006_E006', 'B04006_E017', 'B04006_E073']).rename(
    columns={'B04006_E001': 'anc_total', 'B04006_E006': 'anc_arab',
             'B04006_E017': 'anc_chaldean', 'B04006_E073': 'anc_subsaharan'})
ancestry = push_down(anc, 'tract', ['anc_total', 'anc_arab', 'anc_chaldean', 'anc_subsaharan'])

g = g.set_index('precinct_id').join([edu, age, income, nat, ten, ancestry]).reset_index()
g['area_km2'] = g.to_crs(5070).area / 1e6

# ---------- results: 1:1, no collapsing ----------
vh  = pd.read_csv(f'{BASE}/mi_sen_dem_primary_2026_precincts.csv')
vhp = vh[vh.geography_type == 'precinct'].copy()
vcols = [c for c in vhp.columns if c.startswith('C_')]
assert vhp.GEO_KEY.isin(set(g.precinct_id)).all(), 'unmatched VoteHub precinct'
g = g.merge(vhp[['GEO_KEY'] + vcols].rename(columns={'GEO_KEY': 'precinct_id'}),
            on='precinct_id', how='left')

CAND = {'Abdul_El-Sayed': 'elsayed', 'Haley_Stevens': 'stevens', 'Mallory_McMorrow': 'mcmorrow'}
g['votes_total'] = g[[f'C_TOT_{c}' for c in CAND]].sum(axis=1)
g['has_results'] = g[f'C_TOT_Abdul_El-Sayed'].notna() & (g.votes_total > 0)
for c, t_ in CAND.items():
    g[f'share_{t_}'] = g[f'C_TOT_{c}'] / g.votes_total.replace(0, np.nan)
g['margin_elsayed'] = g.share_elsayed - g.share_stevens
for mode, t_ in [('ELD', 'eday'), ('VBM', 'mail'), ('ADV', 'early')]:
    g[f'pct_{t_}'] = g[[f'C_{mode}_{c}' for c in CAND]].sum(axis=1) / g.votes_total.replace(0, np.nan)

for r in ['hisp', 'white', 'black', 'aian', 'asian', 'nhpi', 'other', 'two']:
    g[f'pct_vap_{r}'] = g[f'vap_{r}'] / g.vap.replace(0, np.nan)
g['pct_vap_nonwhite']      = 1 - g.pct_vap_white
g['pct_ba_plus']           = g.edu_ba_plus / g.edu_total.replace(0, np.nan)
g['pct_hs_or_less']        = g.edu_hs_or_less / g.edu_total.replace(0, np.nan)
g['pct_age_18_34']         = g.age_18_34 / g.age_total.replace(0, np.nan)
g['pct_age_65p']           = g.age_65p / g.age_total.replace(0, np.nan)
g['mean_hh_income']        = g.agg_hh_income / g.households.replace(0, np.nan)
g['pct_foreign_born']      = g.foreign_born / g.nativity_total.replace(0, np.nan)
g['pct_owner_occ']         = g.owner_occ / g.tenure_total.replace(0, np.nan)
g['pct_arab_ancestry']     = g.anc_arab / g.anc_total.replace(0, np.nan)
g['pct_chaldean_ancestry'] = g.anc_chaldean / g.anc_total.replace(0, np.nan)
g['pop_density']           = g['pop'] / g.area_km2.replace(0, np.nan)
g['log_density']           = np.log1p(g.pop_density)
g['log_income']            = np.log(g.mean_hh_income.replace(0, np.nan))
g['reg_rate']              = g.registered / g.vap.replace(0, np.nan)
g['active_rate']           = g.active_voters / g.vap.replace(0, np.nan)
g['primary_turnout']       = g.votes_total / g.registered.replace(0, np.nan)

drop = ['OBJECTID', 'Shape__Are', 'Shape__Len', 'PrecinctCo', 'PrecinctSh', 'TabulatorV']
g = g.drop(columns=[c for c in drop if c in g.columns])

os.makedirs(OUT, exist_ok=True)
g.to_file(f'{OUT}/mi_precinct_demographics_2026.gpkg', driver='GPKG')
g.drop(columns='geometry').to_csv(f'{OUT}/mi_precinct_demographics_2026.csv', index=False)

r = g[g.has_results]
print(f'precincts: {len(g)} | with results: {len(r)}')
print(f'votes {r.votes_total.sum():,.0f} of {vhp[[f"C_TOT_{c}" for c in CAND]].sum().sum():,.0f}')
print(f'pop {g["pop"].sum():,.0f} / 10,077,331')
print(f'reg_rate median {r.reg_rate.median():.3f} | >1.15 {(r.reg_rate>1.15).sum()} '
      f'| >1.5 {(r.reg_rate>1.5).sum()}')
print(f'active_rate median {r.active_rate.median():.3f}')
print('\npredictor coverage on units with results:')
for c in ['pct_vap_black','pct_ba_plus','mean_hh_income','pct_age_18_34',
          'pct_foreign_born','pct_arab_ancestry','pct_chaldean_ancestry','pct_owner_occ']:
    print(f'  {c:<24} {r[c].notna().sum()}/{len(r)}')
