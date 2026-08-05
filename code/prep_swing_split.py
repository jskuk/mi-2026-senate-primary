"""The 2020->2024 swing panel, split by Arab ancestry share.

Splitting at 10% shows that the negative swing/El-Sayed relationship in the pooled
data is carried entirely by 115 precincts. Below the threshold the sign reverses.
"""
import json, os
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
FIG  = f'{BASE}/precinct_demographics/figures'
os.makedirs(FIG, exist_ok=True)

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
r = d[d.has_results & (d.votes_total >= 25)].dropna(
    subset=['swing_pres_2024_2020', 'pct_arab_ancestry', 'margin_elsayed']).copy()

SUBSETS = [
    ('all',  'All precincts',            lambda x: x.index == x.index),
    ('low',  'Arab ancestry 10% or less', lambda x: x.pct_arab_ancestry <= 0.10),
    ('high', 'Arab ancestry above 10%',   lambda x: x.pct_arab_ancestry > 0.10),
]

def wstat(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx, vy = np.average((x - mx) ** 2, weights=w), np.average((y - my) ** 2, weights=w)
    sl = cov / vx
    return cov / np.sqrt(vx * vy), sl, my - sl * mx

def binscatter(x, y, w, nbins):
    o = np.argsort(x); x, y, w = x[o], y[o], w[o]
    cw = np.cumsum(w) / w.sum()
    idx = np.searchsorted(cw, np.linspace(0, 1, nbins + 1)[1:-1])
    out = []
    for g in np.split(np.arange(len(x)), idx):
        if len(g) == 0: continue
        ww = w[g]
        out.append(dict(x=round(float(np.average(x[g], weights=ww)), 5),
                        y=round(float(np.average(y[g], weights=ww)), 5)))
    return out

panels, rows = [], []
for key, label, f in SUBSETS:
    s = r[f(r)]
    x, y, w = s.swing_pres_2024_2020.values, s.margin_elsayed.values, s.votes_total.values
    rr, sl, ic = wstat(x, y, w)
    lo, hi = np.percentile(x, [1, 99]); pad = (hi - lo) * .05
    nb = 20 if key != 'high' else 10
    panels.append(dict(key=key, label=label, r=round(rr, 3), slope=round(sl, 4),
                       intercept=round(ic, 4), n=int(len(s)), votes=int(w.sum()),
                       xlo=round(float(lo - pad), 4), xhi=round(float(hi + pad), 4),
                       bins=binscatter(x, y, w, nb)))
    rows.append(dict(subset=label, n=len(s), votes=int(w.sum()), r=round(rr, 3),
                     slope=round(sl, 3)))
    print(f'{label:<28} n={len(s):>5} votes={w.sum():>10,.0f} r={rr:+.3f} slope={sl:+.2f}'
          f'  x[{lo:+.3f},{hi:+.3f}]')

pts = []
for _, row in r.iterrows():
    pts.append(dict(j=row.jurisdiction, v=int(row.votes_total),
                    m=round(float(row.margin_elsayed), 4),
                    s=round(float(row.swing_pres_2024_2020), 4),
                    a=round(float(row.pct_arab_ancestry), 4)))

json.dump(dict(n=len(pts), votes=int(r.votes_total.sum()), panels=panels, points=pts),
          open(f'{FIG}/swing_split_data.json', 'w'), separators=(',', ':'))
r.to_csv(f'{FIG}/swing_split_data.csv', index=False)
pd.DataFrame(rows).to_csv(f'{FIG}/swing_split_stats.csv', index=False)
print(f"\nwrote swing_split_data.json ({os.path.getsize(f'{FIG}/swing_split_data.json')/1024:.0f} KB)")
