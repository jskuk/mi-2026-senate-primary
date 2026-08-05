"""Step 1: assign all 2020 Census blocks to 2026 voting precincts by internal point."""
import warnings
import pandas as pd, geopandas as gpd
warnings.filterwarnings('ignore')

SCR  = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'
BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'

# ---------- P.L. 94-171 at block level (offsets verified vs published state totals) ----------
geo = pd.read_csv(f'{SCR}/pl/migeo2020.pl', sep='|', header=None, dtype=str,
                  usecols=[2, 7, 9], names=['SUMLEV', 'LOGRECNO', 'GEOCODE'], encoding='latin-1')
geo = geo[geo.SUMLEV == '750'][['LOGRECNO', 'GEOCODE']]
geo['LOGRECNO'] = geo.LOGRECNO.str.zfill(7)

S1 = {77: 'pop', 78: 'pop_hisp', 81: 'pop_white', 82: 'pop_black', 83: 'pop_aian',
      84: 'pop_asian', 85: 'pop_nhpi', 86: 'pop_other', 87: 'pop_two'}
S2 = {77: 'vap', 78: 'vap_hisp', 81: 'vap_white', 82: 'vap_black', 83: 'vap_aian',
      84: 'vap_asian', 85: 'vap_nhpi', 86: 'vap_other', 87: 'vap_two',
      150: 'housing', 151: 'housing_occ'}

def seg(path, spec):
    d = pd.read_csv(path, sep='|', header=None, usecols=[4] + [k - 1 for k in spec],
                    names=['LOGRECNO'] + list(spec.values()), dtype={4: str}, encoding='latin-1')
    d['LOGRECNO'] = d.LOGRECNO.astype(str).str.zfill(7)
    return d

blk = (geo.merge(seg(f'{SCR}/pl/mi000012020.pl', S1), on='LOGRECNO')
          .merge(seg(f'{SCR}/pl/mi000022020.pl', S2), on='LOGRECNO'))
assert blk['pop'].sum() == 10077331, 'state population mismatch'
print(f'blocks: {len(blk):,} | pop {blk["pop"].sum():,} | vap {blk.vap.sum():,}')

# ---------- internal points ----------
tb = gpd.read_file(f'{SCR}/tiger/tl_2020_26_tabblock20.shp',
                   columns=['GEOID20', 'INTPTLAT20', 'INTPTLON20'])
tb = pd.DataFrame(tb.drop(columns='geometry'))
b = blk.merge(tb, left_on='GEOCODE', right_on='GEOID20', how='inner')
pts = gpd.GeoDataFrame(b, geometry=gpd.points_from_xy(
    b.INTPTLON20.astype(float), b.INTPTLAT20.astype(float)), crs=4326)

# ---------- 2026 precincts ----------
g = gpd.read_file(f'{BASE}/shapefile26/2026_Voting_Precincts.shp')
g['geometry'] = g.geometry.buffer(0)
print(f'2026 precincts: {len(g)} | unique {g.PrecinctID.nunique()}')

pts = pts.to_crs(g.crs)
j = gpd.sjoin(pts, g[['PrecinctID', 'geometry']], how='left',
              predicate='within').drop_duplicates('GEOCODE')
un = j.PrecinctID.isna()
print(f'unassigned by point-in-polygon: {un.sum():,} (pop {j.loc[un,"pop"].sum():,})')
if un.sum():
    miss = gpd.GeoDataFrame(j[un].drop(columns=['index_right', 'PrecinctID']),
                            geometry=j[un].geometry, crs=g.crs)
    nn = gpd.sjoin_nearest(miss, g[['PrecinctID', 'geometry']], how='left',
                           max_distance=5000).drop_duplicates('GEOCODE')
    j.loc[un, 'PrecinctID'] = nn.PrecinctID.values
    still = j.PrecinctID.isna()
    print(f'  after nearest fallback: {still.sum():,} (pop {j.loc[still,"pop"].sum():,})')

DEM = list(S1.values()) + list(S2.values())
ok = j.dropna(subset=['PrecinctID'])
agg = ok.groupby('PrecinctID')[DEM].sum()
agg['n_blocks'] = ok.groupby('PrecinctID').size()
agg = agg.reset_index()
print(f'\nprecincts receiving blocks: {len(agg)}/{len(g)}')
print(f'population assigned: {agg["pop"].sum():,} / 10,077,331 '
      f'({agg["pop"].sum()/10077331*100:.2f}%)')

agg.to_parquet(f'{SCR}/precinct2026_demographics.parquet', index=False)
j[['GEOCODE', 'PrecinctID']].to_parquet(f'{SCR}/block_precinct26_xwalk.parquet', index=False)
