"""Reallocate RDH 2024 general-election precinct results onto 2026 precincts.

RDH ships its own geometry but keys on MI SOS internal county/jurisdiction codes,
not the WP-{FIPS} ids used by the state shapefiles. Rather than build a code
crosswalk, this goes through 2020 Census blocks, which are already assigned to
2026 precincts by internal point: each RDH precinct's votes are split across
blocks in proportion to block voting-age population, then summed into 2026
precincts. VAP weighting beats land area anywhere settlement is uneven.
"""
import warnings
import geopandas as gpd, pandas as pd, numpy as np
warnings.filterwarnings('ignore')

SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
RDH  = f'{BASE}/mi_2024_gen_prec/mi_2024_gen_all_prec/mi_2024_gen_all_prec.shp'

KEEP = {
    'G24PREDHAR': 'pres24_harris',   'G24PRERTRU': 'pres24_trump',
    'G24PREGSTE': 'pres24_stein',    'G24PREUWES': 'pres24_west',
    'G24PREUCRU': 'pres24_delacruz', 'G24PRELOLI': 'pres24_oliver',
    'G24PRENKEN': 'pres24_kennedy',
    'G24USSDSLO': 'uss24_slotkin',   'G24USSRROG': 'uss24_rogers',
    'G24USSGMAR': 'uss24_marsh',
    'TOT_VOTES':  'tot24_ballots',
}

r = gpd.read_file(RDH, columns=['UNIQUE_ID'] + list(KEEP))
r = r.rename(columns=KEEP)
r['geometry'] = r.geometry.buffer(0)
VAL = list(KEEP.values())
for c in VAL:
    r[c] = pd.to_numeric(r[c], errors='coerce').fillna(0)
r['rdh_id'] = np.arange(len(r))
print(f'RDH 2024 precincts: {len(r)} | crs {r.crs.to_epsg()}')
print(f'statewide: Harris {r.pres24_harris.sum():,.0f} | Trump {r.pres24_trump.sum():,.0f} '
      f'| Stein {r.pres24_stein.sum():,.0f}')
print(f'           Slotkin {r.uss24_slotkin.sum():,.0f} | Rogers {r.uss24_rogers.sum():,.0f}')

# ---------- blocks: internal points + VAP + 2026 assignment ----------
geo = pd.read_csv(f'{SCR}/pl/migeo2020.pl', sep='|', header=None, dtype=str,
                  usecols=[2, 7, 9], names=['SUMLEV', 'LOGRECNO', 'GEOCODE'], encoding='latin-1')
geo = geo[geo.SUMLEV == '750'][['LOGRECNO', 'GEOCODE']]
geo['LOGRECNO'] = geo.LOGRECNO.str.zfill(7)
s2 = pd.read_csv(f'{SCR}/pl/mi000022020.pl', sep='|', header=None, usecols=[4, 76],
                 names=['LOGRECNO', 'vap_blk'], dtype={4: str}, encoding='latin-1')
s2['LOGRECNO'] = s2.LOGRECNO.astype(str).str.zfill(7)
vap = geo.merge(s2, on='LOGRECNO')[['GEOCODE', 'vap_blk']]

tb = gpd.read_file(f'{SCR}/tiger/tl_2020_26_tabblock20.shp',
                   columns=['GEOID20', 'INTPTLAT20', 'INTPTLON20'])
tb = pd.DataFrame(tb.drop(columns='geometry')).merge(
    vap, left_on='GEOID20', right_on='GEOCODE', how='inner')
pts = gpd.GeoDataFrame(tb, geometry=gpd.points_from_xy(
    tb.INTPTLON20.astype(float), tb.INTPTLAT20.astype(float)), crs=4326).to_crs(r.crs)

x26 = pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet').rename(
    columns={'PrecinctID': 'p2026'})
pts = pts.merge(x26, on='GEOCODE', how='left')

j = gpd.sjoin(pts, r[['rdh_id', 'geometry']], how='left',
              predicate='within').drop_duplicates('GEOCODE')
un = j.rdh_id.isna()
print(f'\nblocks not inside any RDH precinct: {un.sum():,} (VAP {j.loc[un,"vap_blk"].sum():,})')
if un.sum():
    miss = gpd.GeoDataFrame(j[un].drop(columns=['index_right', 'rdh_id']),
                            geometry=j[un].geometry, crs=r.crs)
    nn = gpd.sjoin_nearest(miss, r[['rdh_id', 'geometry']], how='left',
                           max_distance=5000).drop_duplicates('GEOCODE')
    j.loc[un, 'rdh_id'] = nn.rdh_id.values
    print(f'  after nearest fallback: {j.rdh_id.isna().sum():,}')

b = j.dropna(subset=['rdh_id', 'p2026'])[['GEOCODE', 'rdh_id', 'p2026', 'vap_blk']]

# ---------- allocate ----------
tot = b.groupby('rdh_id')['vap_blk'].transform('sum')
b['w'] = np.where(tot > 0, b.vap_blk / tot, np.nan)
zero = b.w.isna()
if zero.any():
    b.loc[zero, 'w'] = 1.0 / b[zero].groupby('rdh_id')['GEOCODE'].transform('size')
    print(f'zero-VAP RDH precincts using equal split: {b.loc[zero,"rdh_id"].nunique()}')

m = b.merge(r[['rdh_id'] + VAL], on='rdh_id', how='left')
for c in VAL:
    m[c] = m[c] * m.w
out = m.groupby('p2026', as_index=False)[VAL].sum()

print(f'\ncarried onto {len(out)} 2026 precincts')
for c in ['pres24_harris', 'pres24_trump', 'pres24_stein', 'uss24_slotkin', 'uss24_rogers']:
    print(f'  {c:<16} {out[c].sum():>12,.0f}  ({out[c].sum()/r[c].sum()*100:.3f}% of source)')

# ---------- derived ----------
o = out.rename(columns={'p2026': 'precinct_id'})
pres_all = ['pres24_harris', 'pres24_trump', 'pres24_stein', 'pres24_west',
            'pres24_delacruz', 'pres24_oliver', 'pres24_kennedy']
o['pres24_total']    = o[pres_all].sum(axis=1)
o['uss24_total']     = o[['uss24_slotkin', 'uss24_rogers', 'uss24_marsh']].sum(axis=1)
den = o.pres24_total.replace(0, np.nan)
o['pres24_dem2p']    = o.pres24_harris / (o.pres24_harris + o.pres24_trump).replace(0, np.nan)
o['pres24_harris_pct'] = o.pres24_harris / den
o['pres24_stein_pct']  = o.pres24_stein / den
o['pres24_left_protest_pct'] = o[['pres24_stein', 'pres24_west', 'pres24_delacruz']].sum(axis=1) / den
o['uss24_dem2p']     = o.uss24_slotkin / (o.uss24_slotkin + o.uss24_rogers).replace(0, np.nan)
o['slotkin_over_harris'] = o.uss24_dem2p - o.pres24_dem2p        # ticket splitting
o.to_parquet(f'{SCR}/results_2024_on_2026.parquet', index=False)
print(f'\nwrote results_2024_on_2026.parquet ({len(o)} rows)')
