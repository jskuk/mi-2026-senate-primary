"""One payload for the combined report.

All three views describe the same 2,864 precincts, so the point array is shared:
the swing view is the predictor view's swing panel with a filter on Arab ancestry,
not a second copy of the data.
"""
import json, os
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026'
FIG  = f'{BASE}/precinct_demographics/figures'
rng = np.random.default_rng(20260805)

PANELS = [
    ('pct_vap_black',        'Black share of voting-age population'),
    ('pct_age_18_34',        'Age 18-34 share of population'),
    ('pct_ba_plus',          "Bachelor's degree or higher"),
    ('pct_arab_ancestry',    'Arab ancestry share (ACS)'),
    ('swing_pres_2020_2016', 'Presidential swing 2016 to 2020'),
    ('swing_pres_2024_2020', 'Presidential swing 2020 to 2024'),
]
KEYS = [k for k, _ in PANELS]

d = pd.read_csv(f'{BASE}/precinct_demographics/mi_precinct_demographics_2026.csv')
r = d[d.has_results & (d.votes_total >= 25)].dropna(subset=['margin_elsayed']).copy()
print(f'precincts {len(r)} | votes {r.votes_total.sum():,.0f}')

def wstat(x, y, w):
    m = x.notna() & y.notna()
    x, y, w = x[m].values, y[m].values, w[m].values
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    cov = np.average((x - mx) * (y - my), weights=w)
    vx, vy = np.average((x - mx) ** 2, weights=w), np.average((y - my) ** 2, weights=w)
    sl = cov / vx
    return dict(r=round(cov / np.sqrt(vx * vy), 3), slope=round(sl, 4),
                intercept=round(my - sl * mx, 4), n=int(m.sum()))

def bins_of(x, y, w, nb=20):
    m = x.notna() & y.notna()
    x, y, w = x[m].values, y[m].values, w[m].values
    o = np.argsort(x); x, y, w = x[o], y[o], w[o]
    cw = np.cumsum(w) / w.sum()
    idx = np.searchsorted(cw, np.linspace(0, 1, nb + 1)[1:-1])
    out = []
    for g in np.split(np.arange(len(x)), idx):
        if len(g) == 0: continue
        ww = w[g]
        out.append(dict(x=round(float(np.average(x[g], weights=ww)), 5),
                        y=round(float(np.average(y[g], weights=ww)), 5)))
    return out

def limits(x, pad=.04):
    lo, hi = np.nanpercentile(x.dropna(), [1, 99])
    p = (hi - lo) * pad
    return round(float(lo - p), 4), round(float(hi + p), 4)

# ---- view 1: predictors ----
predictors = []
for key, label in PANELS:
    s = wstat(r[key], r.margin_elsayed, r.votes_total)
    lo, hi = limits(r[key])
    predictors.append(dict(key=key, label=label, xlo=lo, xhi=hi, filt='none',
                           bins=bins_of(r[key], r.margin_elsayed, r.votes_total), **s))
    print(f'  {key:<24} r={s["r"]:+.3f}')

# ---- view 2: the same swing panel, split on Arab ancestry ----
SPLIT = [('none', 'All precincts', lambda t: t),
         ('low',  'Arab ancestry 10% or less', lambda t: t[t.pct_arab_ancestry <= .10]),
         ('high', 'Arab ancestry above 10%',   lambda t: t[t.pct_arab_ancestry > .10])]
swing = []
rs = r.dropna(subset=['swing_pres_2024_2020', 'pct_arab_ancestry'])
for filt, label, f in SPLIT:
    s = f(rs)
    st = wstat(s.swing_pres_2024_2020, s.margin_elsayed, s.votes_total)
    lo, hi = limits(s.swing_pres_2024_2020, .05)
    swing.append(dict(key='swing_pres_2024_2020', label=label, filt=filt, xlo=lo, xhi=hi,
                      votes=int(s.votes_total.sum()),
                      bins=bins_of(s.swing_pres_2024_2020, s.margin_elsayed, s.votes_total,
                                   10 if filt == 'high' else 20), **st))
    print(f'  swing/{filt:<5} n={st["n"]:>5} r={st["r"]:+.3f}')

# ---- view 3: winner sequences ----
need = ['pres16_clinton','pres16_trump','pres20_biden','pres20_trump','pres24_harris','pres24_trump']
c = r.dropna(subset=need).copy()
c['combo'] = (np.where(c.pres16_clinton > c.pres16_trump, 'D', 'R') +
              np.where(c.pres20_biden   > c.pres20_trump, 'D', 'R') +
              np.where(c.pres24_harris  > c.pres24_trump, 'D', 'R'))
CAND = {'C_TOT_Abdul_El-Sayed': 'elsayed', 'C_TOT_Haley_Stevens': 'stevens'}
LBL = {'D': 'Dem', 'R': 'Rep'}
def boot(sub, col, B=2000):
    v, t = sub[col].values, sub.votes_total.values
    i = rng.integers(0, len(sub), size=(B, len(sub)))
    s = v[i].sum(axis=1) / np.where(t[i].sum(axis=1) == 0, np.nan, t[i].sum(axis=1))
    return [round(float(q), 5) for q in np.nanpercentile(s, [2.5, 97.5])]
combos = []
for cb in ['DDD','DDR','DRD','DRR','RDD','RDR','RRD','RRR']:
    s = c[c.combo == cb]
    if not len(s): continue
    tot = s.votes_total.sum()
    cands = []
    for col, name in CAND.items():
        lo, hi = boot(s, col)
        cands.append(dict(k=name, v=round(float(s[col].sum() / tot), 5), lo=lo, hi=hi))
    combos.append(dict(combo=cb, parts=[LBL[ch] for ch in cb], n=int(len(s)), votes=int(tot),
                       share_of_votes=round(float(tot / c.votes_total.sum()), 5), cands=cands,
                       mcmorrow=round(float(s['C_TOT_Mallory_McMorrow'].sum() / tot), 5)))
print(f'  {len(combos)} of 8 sequences present')

pts = []
for _, row in r.iterrows():
    o = dict(j=row.jurisdiction, v=int(row.votes_total), m=round(float(row.margin_elsayed), 4))
    for k in KEYS:
        o[k] = None if pd.isna(row[k]) else round(float(row[k]), 4)
    pts.append(o)

payload = dict(n=len(pts), votes=int(r.votes_total.sum()),
               combo_votes=int(c.votes_total.sum()), combo_n=int(len(c)),
               predictors=predictors, swing=swing, combos=combos, points=pts)
json.dump(payload, open(f'{FIG}/report_data.json', 'w'), separators=(',', ':'))
print(f"\nwrote report_data.json ({os.path.getsize(f'{FIG}/report_data.json')/1024:.0f} KB)")
