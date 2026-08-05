"""Prepare the plotting dataset: points, vote-weighted binscatter, weighted fits."""
import json
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
OUT  = f'{BASE}/precinct_demographics/figures'
import os; os.makedirs(OUT, exist_ok=True)

PANELS = [
    ('pct_vap_black',        'Black share of voting-age population', 'share'),
    ('pct_age_18_34',        'Age 18–34 share of population',        'share'),
    ('pct_ba_plus',          "Bachelor's degree or higher",          'share'),
    ('pct_arab_ancestry',    'Arab ancestry share (ACS)',            'share'),
    ('swing_pres_2020_2016', 'Presidential swing 2016 → 2020',       'swing'),
    ('swing_pres_2024_2020', 'Presidential swing 2020 → 2024',       'swing'),
]

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
r = d[d.has_results & (d.votes_total >= 25)].copy()
cols = ['precinct_id', 'jurisdiction', 'votes_total', 'margin_elsayed'] + [p[0] for p in PANELS]
r = r[cols].dropna(subset=['margin_elsayed'])
print(f'precincts: {len(r)} | votes {r.votes_total.sum():,.0f}')


def wstat(x, y, w):
    m = x.notna() & y.notna()
    x, y, w = x[m].values, y[m].values, w[m].values
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx, vy = np.average((x - mx) ** 2, weights=w), np.average((y - my) ** 2, weights=w)
    slope = cov / vx
    return dict(r=cov / np.sqrt(vx * vy), slope=slope, intercept=my - slope * mx,
                xmin=float(np.nanmin(x)), xmax=float(np.nanmax(x)))


def binscatter(x, y, w, nbins=20):
    """Vote-weighted means within equal-weight quantile bins of x."""
    m = x.notna() & y.notna()
    x, y, w = x[m].values, y[m].values, w[m].values
    o = np.argsort(x); x, y, w = x[o], y[o], w[o]
    cw = np.cumsum(w) / w.sum()
    idx = np.searchsorted(cw, np.linspace(0, 1, nbins + 1)[1:-1])
    out = []
    for grp in np.split(np.arange(len(x)), idx):
        if len(grp) == 0:
            continue
        ww = w[grp]
        out.append(dict(x=round(float(np.average(x[grp], weights=ww)), 5),
                        y=round(float(np.average(y[grp], weights=ww)), 5),
                        n=int(len(grp)), votes=int(ww.sum())))
    return out


panels, stats_rows = [], []
for col, label, kind in PANELS:
    s = wstat(r[col], r.margin_elsayed, r.votes_total)
    # axis limits trimmed to 1st–99th pct: a handful of extreme precincts otherwise
    # compress every panel. Statistics are computed on the FULL data, not the trim.
    lo, hi = np.nanpercentile(r[col].dropna(), [1, 99])
    pad = (hi - lo) * 0.04
    lo, hi = lo - pad, hi + pad
    panels.append(dict(key=col, label=label, kind=kind, r=round(s['r'], 3),
                       slope=round(s['slope'], 4), intercept=round(s['intercept'], 4),
                       xlo=round(float(lo), 4), xhi=round(float(hi), 4),
                       bins=binscatter(r[col], r.margin_elsayed, r.votes_total)))
    stats_rows.append(dict(variable=col, label=label, r=round(s['r'], 3),
                           slope=round(s['slope'], 4)))
    print(f'  {col:<24} r={s["r"]:+.3f} slope={s["slope"]:+.3f}  x range shown {lo:.3f}..{hi:.3f}')

pts = []
for i, row in r.reset_index(drop=True).iterrows():
    o = {'j': row.jurisdiction, 'v': int(row.votes_total), 'm': round(float(row.margin_elsayed), 4)}
    for col, _, _ in PANELS:
        o[col] = None if pd.isna(row[col]) else round(float(row[col]), 4)
    pts.append(o)

payload = dict(n=len(pts), votes=int(r.votes_total.sum()), panels=panels, points=pts)
with open(f'{OUT}/chart_data.json', 'w') as f:
    json.dump(payload, f, separators=(',', ':'))
r.to_csv(f'{OUT}/figure_data.csv', index=False)
pd.DataFrame(stats_rows).to_csv(f'{OUT}/figure_stats.csv', index=False)
print(f"\nwrote chart_data.json ({os.path.getsize(f'{OUT}/chart_data.json')/1024:.0f} KB) "
      f"and figure_data.csv")
