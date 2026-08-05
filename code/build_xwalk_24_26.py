"""2024 -> 2026 precinct crosswalk, mediated by 2020 Census blocks.

Both precinct vintages already have every block assigned to them by internal point,
so the block is a common atom: a 2024 precinct's votes are split across the 2026
precincts its blocks fall into, weighted by block voting-age population.

VAP beats total population as the weight because we are reallocating VOTES, and
beats land area by a wide margin in any precinct that is not uniformly settled.
"""
import warnings
import pandas as pd, numpy as np
warnings.filterwarnings('ignore')

SCR = '/private/tmp/claude-503/-Users-jskuk-Dropbox-Claude/6e257534-2c98-4c64-96b1-2153cb838d7a/scratchpad'

# block -> 2024 precinct, block -> 2026 precinct
x24 = pd.read_parquet(f'{SCR}/block_precinct_xwalk.parquet').rename(
    columns={'PRECINCTID': 'p2024'})
x26 = pd.read_parquet(f'{SCR}/block_precinct26_xwalk.parquet').rename(
    columns={'PrecinctID': 'p2026'})

# block VAP from the P.L. file (field 77 of segment 2 = P4_001N)
geo = pd.read_csv(f'{SCR}/pl/migeo2020.pl', sep='|', header=None, dtype=str,
                  usecols=[2, 7, 9], names=['SUMLEV', 'LOGRECNO', 'GEOCODE'], encoding='latin-1')
geo = geo[geo.SUMLEV == '750'][['LOGRECNO', 'GEOCODE']]
geo['LOGRECNO'] = geo.LOGRECNO.str.zfill(7)
s2 = pd.read_csv(f'{SCR}/pl/mi000022020.pl', sep='|', header=None, usecols=[4, 76],
                 names=['LOGRECNO', 'vap_blk'], dtype={4: str}, encoding='latin-1')
s2['LOGRECNO'] = s2.LOGRECNO.astype(str).str.zfill(7)
vap = geo.merge(s2, on='LOGRECNO')[['GEOCODE', 'vap_blk']]

b = x24.merge(x26, on='GEOCODE', how='inner').merge(vap, on='GEOCODE', how='left')
b = b.dropna(subset=['p2024', 'p2026'])
print(f'blocks with both assignments: {len(b):,} | VAP {b.vap_blk.sum():,}')

# weight = share of the 2024 precinct's VAP that lands in each 2026 precinct
pair = b.groupby(['p2024', 'p2026'], as_index=False)['vap_blk'].sum()
tot = pair.groupby('p2024')['vap_blk'].transform('sum')
pair['w'] = np.where(tot > 0, pair.vap_blk / tot, np.nan)

# 2024 precincts with zero VAP: fall back to equal split across their 2026 pieces
zero = pair.w.isna()
if zero.any():
    n = pair[zero].groupby('p2024')['p2026'].transform('size')
    pair.loc[zero, 'w'] = 1.0 / n
    print(f'zero-VAP 2024 precincts using equal split: {pair.loc[zero,"p2024"].nunique()}')

chk = pair.groupby('p2024').w.sum()
assert np.allclose(chk, 1.0), f'weights do not sum to 1: {chk.min():.4f}-{chk.max():.4f}'

n24, n26 = pair.p2024.nunique(), pair.p2026.nunique()
splits = pair.groupby('p2024').size()
print(f'2024 precincts: {n24} | 2026 precincts touched: {n26} | pairs: {len(pair)}')
print(f'2024 precincts mapping 1:1        : {(splits==1).sum()} ({(splits==1).mean()*100:.1f}%)')
print(f'2024 precincts split across 2+    : {(splits>1).sum()}')
print(f'max pieces a 2024 precinct splits : {splits.max()}')
w_dom = pair.groupby('p2024').w.max()
print(f'median dominant-piece weight      : {w_dom.median():.3f}')
print(f'2024 precincts where dominant <0.9: {(w_dom<0.9).sum()} ({(w_dom<0.9).mean()*100:.1f}%)')

pair[['p2024', 'p2026', 'w', 'vap_blk']].to_parquet(f'{SCR}/xwalk_2024_2026.parquet', index=False)
print(f'\nwrote xwalk_2024_2026.parquet')
