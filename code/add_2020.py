"""Add 2020 and 2016 general-election results, then 2024-2020 deltas.

Source is the ALARM/VEST file at 2020 VTD geography (statewide totals match the
official Michigan canvass to within ~10 votes). Unlike the 2024 reallocation, the
block -> 2020 VTD step needs no spatial join at all: the P.L. 94-171 geoheader
records each block's VTD directly (field 78), so that half of the crosswalk is exact.
Blocks then carry votes into 2026 precincts weighted by block voting-age population.
"""
import warnings
import pandas as pd, numpy as np
warnings.filterwarnings('ignore')

SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'

# ---------- block -> VTD (exact, from the geoheader) + block VAP ----------
geo = pd.read_csv(f'{SCR}/pl/migeo2020.pl', sep='|', header=None, dtype=str,
                  usecols=[2, 7, 9, 14, 77],
                  names=['SUMLEV', 'LOGRECNO', 'GEOCODE', 'COUNTY', 'VTD'], encoding='latin-1')
geo = geo[geo.SUMLEV == '750']
geo['LOGRECNO'] = geo.LOGRECNO.str.zfill(7)
geo['GEOID20']  = '26' + geo.COUNTY.str.zfill(3) + geo.VTD.str.zfill(6)

s2 = pd.read_csv(f'{SCR}/pl/mi000022020.pl', sep='|', header=None, usecols=[4, 76],
                 names=['LOGRECNO', 'vap_blk'], dtype={4: str}, encoding='latin-1')
s2['LOGRECNO'] = s2.LOGRECNO.astype(str).str.zfill(7)
b = geo[['GEOCODE', 'GEOID20']].merge(s2, on='LOGRECNO' if False else 'LOGRECNO', how='left') \
    if False else geo[['LOGRECNO', 'GEOCODE', 'GEOID20']].merge(s2, on='LOGRECNO')

x26 = pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet').rename(
    columns={'PrecinctID': 'p2026'})
b = b.merge(x26, on='GEOCODE', how='left').dropna(subset=['p2026'])
print(f'blocks with VTD + 2026 precinct: {len(b):,} | VAP {b.vap_blk.sum():,}')

# ---------- ALARM results ----------
KEEP = {'pre_20_dem_bid': 'pres20_biden', 'pre_20_rep_tru': 'pres20_trump',
        'uss_20_dem_pet': 'uss20_peters', 'uss_20_rep_jam': 'uss20_james',
        'pre_16_dem_cli': 'pres16_clinton', 'pre_16_rep_tru': 'pres16_trump'}
a = pd.read_csv(f'{SCR}/mi_2020_vtd.csv', dtype={'GEOID20': str})[['GEOID20'] + list(KEEP)]
a = a.rename(columns=KEEP)
VAL = list(KEEP.values())

hit = b.GEOID20.isin(set(a.GEOID20))
print(f'blocks whose VTD is in ALARM: {hit.sum():,}/{len(b):,} ({hit.mean()*100:.2f}%) '
      f'| VAP covered {b.loc[hit,"vap_blk"].sum()/b.vap_blk.sum()*100:.2f}%')

m = b[hit].merge(a, on='GEOID20', how='left')
tot = m.groupby('GEOID20')['vap_blk'].transform('sum')
m['w'] = np.where(tot > 0, m.vap_blk / tot, np.nan)
zero = m.w.isna()
if zero.any():
    m.loc[zero, 'w'] = 1.0 / m[zero].groupby('GEOID20')['GEOCODE'].transform('size')
    print(f'zero-VAP VTDs using equal split: {m.loc[zero,"GEOID20"].nunique()}')
for c in VAL:
    m[c] = m[c] * m.w
out = m.groupby('p2026', as_index=False)[VAL].sum().rename(columns={'p2026': 'precinct_id'})

print(f'\ncarried onto {len(out)} 2026 precincts:')
for c in VAL:
    print(f'  {c:<16} {out[c].sum():>12,.0f}  ({out[c].sum()/a[c].sum()*100:.2f}% of source)')

# ---------- merge and derive ----------
d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
d = d.drop(columns=[c for c in d.columns if c in VAL or c.startswith(('pres20_', 'uss20_',
           'pres16_', 'swing_', 'turnout'))and c != 'primary_turnout'], errors='ignore')
d = d.merge(out, on='precinct_id', how='left')

d['pres20_total'] = d.pres20_biden + d.pres20_trump          # two-party, both years
d['pres24_2ptotal'] = d.pres24_harris + d.pres24_trump
d['pres20_dem2p']   = d.pres20_biden / d.pres20_total.replace(0, np.nan)
d['uss20_dem2p']    = d.uss20_peters / (d.uss20_peters + d.uss20_james).replace(0, np.nan)
d['pres16_dem2p']   = d.pres16_clinton / (d.pres16_clinton + d.pres16_trump).replace(0, np.nan)

# --- swing: 2024 minus 2020 (negative = moved toward Republicans) ---
d['swing_pres_2024_2020'] = d.pres24_dem2p - d.pres20_dem2p
d['swing_uss_2024_2020']  = d.uss24_dem2p - d.uss20_dem2p
d['swing_pres_2020_2016'] = d.pres20_dem2p - d.pres16_dem2p

# --- turnout, scaled by a common 2020 VAP denominator so precincts are comparable ---
d['turnout20_vap'] = d.pres20_total / d.vap.replace(0, np.nan)
d['turnout24_vap'] = d.pres24_2ptotal / d.vap.replace(0, np.nan)
d['turnout_delta_vap'] = d.turnout24_vap - d.turnout20_vap
d['turnout_ratio_24_20'] = d.pres24_2ptotal / d.pres20_total.replace(0, np.nan)
d['log_turnout_ratio'] = np.log(d.turnout_ratio_24_20.replace(0, np.nan))

# --- decompose the swing into where each side's raw votes moved ---
d['dem_votes_delta_vap'] = (d.pres24_harris - d.pres20_biden) / d.vap.replace(0, np.nan)
d['rep_votes_delta_vap'] = (d.pres24_trump - d.pres20_trump) / d.vap.replace(0, np.nan)

d.to_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv', index=False)
import geopandas as gpd
g = gpd.read_file(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.gpkg',
                  columns=['precinct_id'])
g = g.merge(d, on='precinct_id', how='left')
g.to_file(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.gpkg', driver='GPKG')
print(f'\nfile now {len(d)} rows x {len(d.columns)} cols')
