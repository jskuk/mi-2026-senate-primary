"""Is the negative income coefficient real, or an artefact of controlling for education?

The regression says: holding education fixed, richer precincts favoured Stevens. Since
education and income correlate at +0.77, that could be a collinearity artefact of the
linear specification. This checks it WITHOUT any functional-form assumption, by matching
precincts into cells and comparing income terciles inside each cell.
"""
import pandas as pd, numpy as np

BASE = '/Users/jskuk/Dropbox/Claude/votehub_mi_2026/precinct_demographics'
COLLEGE = ['Ann Arbor','East Lansing','Ypsilanti','Mount Pleasant','Kalamazoo','Big Rapids',
           'Houghton','Marquette','Allendale Township','Ypsilanti Township','Scio Township',
           'Pittsfield Township']

d = pd.read_csv(f'{BASE}/mi_precinct_demographics_2026.csv')
r = d[d.has_results & (d.votes_total >= 25)].dropna(
    subset=['margin_elsayed','pct_ba_plus','mean_hh_income','pct_age_18_34','pct_vap_black']).copy()

def wc(x, y, w):
    mx, my = np.average(x, weights=w), np.average(y, weights=w)
    return (np.average((x-mx)*(y-my), weights=w) /
            np.sqrt(np.average((x-mx)**2, weights=w) * np.average((y-my)**2, weights=w)))

w = r.votes_total
print(f'corr(BA+, log income) = {wc(r.pct_ba_plus, r.log_income, w):+.3f}  '
      f'| raw corr(income, margin) = {wc(r.log_income, r.margin_elsayed, w):+.3f}\n')

# ---- 1. within education strata (this one is CONFOUNDED by race; see below) ----
print('Within education quintile, corr(log income, margin):')
r['edq'] = pd.qcut(r.pct_ba_plus, 5, labels=False)
for q, s in r.groupby('edq', observed=True):
    print(f'  Q{q+1}  n={len(s):>4}  r = {wc(s.log_income, s.margin_elsayed, s.votes_total):+.3f}')
q1 = r[r.edq == 0]
print(f'\n  Q1 looks POSITIVE (+{wc(q1.log_income, q1.margin_elsayed, q1.votes_total):.3f}) but that is race:')
print(f'    within Q1, corr(income, Black VAP) = {wc(q1.log_income, q1.pct_vap_black, q1.votes_total):+.3f}')
q1b = q1[q1.pct_vap_black <= .25]
print(f'    Q1 restricted to Black VAP <= 25%: r = {wc(q1b.log_income, q1b.margin_elsayed, q1b.votes_total):+.3f}')
print('    -> low income in low-education precincts mostly means heavily Black, i.e. Stevens country.\n')

# ---- 2. non-parametric matching ----
def matched(df, keys, label):
    rows = []
    for _, s in df.groupby(keys, observed=True):
        if len(s) < 25: continue
        lo, hi = s.mean_hh_income.quantile([1/3, 2/3])
        a, c = s[s.mean_hh_income <= lo], s[s.mean_hh_income >= hi]
        if len(a) < 6 or len(c) < 6: continue
        rows.append(dict(diff=(np.average(a.margin_elsayed, weights=a.votes_total) -
                               np.average(c.margin_elsayed, weights=c.votes_total)) * 100,
                         votes=s.votes_total.sum()))
    t = pd.DataFrame(rows)
    print(f'{label}: {len(t):>3} cells | poorer-third advantage '
          f'{np.average(t["diff"], weights=t.votes):+6.1f} pts | {(t["diff"]>0).sum()}/{len(t)} positive')

for df, tag in [(r, 'ALL'), (r[~r.jurisdiction.isin(COLLEGE)], 'NO COLLEGE TOWNS')]:
    x = df.copy()
    x['ed10'] = pd.qcut(x.pct_ba_plus, 10, labels=False)
    x['ed5']  = pd.qcut(x.pct_ba_plus, 5, labels=False)
    x['blk']  = pd.cut(x.pct_vap_black, [-1,.05,.2,.5,2], labels=False)
    x['age']  = pd.qcut(x.pct_age_18_34, 3, labels=False)
    print(f'--- {tag} ---')
    matched(x, ['ed10','blk'],      '  education x race      ')
    matched(x, ['ed5','blk','age'], '  education x race x age')

# ---- 3. matched jurisdiction pairs, for illustration ----
rc = r[~r.jurisdiction.isin(COLLEGE)]
j = (rc.groupby('jurisdiction').apply(lambda x: pd.Series({
        'votes': x.votes_total.sum(),
        'inc': np.average(x.mean_hh_income, weights=x.votes_total)/1000,
        'ba': np.average(x.pct_ba_plus, weights=x.votes_total)*100,
        'blk': np.average(x.pct_vap_black, weights=x.votes_total)*100,
        'young': np.average(x.pct_age_18_34, weights=x.votes_total)*100,
        'arab': np.average(x.pct_arab_ancestry, weights=x.votes_total)*100,
        'aes': x['C_TOT_Abdul_El-Sayed'].sum()/x.votes_total.sum()*100}),
        include_groups=False).reset_index())
j = j[(j.votes >= 2500) & (j.arab < 10)]
print('\nJurisdiction pairs matched on education, Black share and age; income gap >= $35k:')
seen, out = set(), []
for _, a in j.sort_values('inc', ascending=False).iterrows():
    for _, b in j.iterrows():
        if abs(a.ba-b.ba) > 4 or abs(a.blk-b.blk) > 6 or abs(a.young-b.young) > 5: continue
        if a.inc - b.inc < 35: continue
        k = tuple(sorted([a.jurisdiction, b.jurisdiction]))
        if k in seen: continue
        seen.add(k); out.append((a, b))
for a, b in out:
    print(f'  {a.jurisdiction:<24}${a.inc:>4.0f}k {a.ba:>3.0f}% BA+  {a.aes:>5.1f}%   vs   '
          f'{b.jurisdiction:<24}${b.inc:>4.0f}k {b.ba:>3.0f}% BA+  {b.aes:>5.1f}%  '
          f'({b.aes-a.aes:+.1f})')
print(f'\n{len(out)} pairs; poorer place favoured El-Sayed in '
      f'{sum(1 for a,b in out if b.aes > a.aes)}')
pd.DataFrame([dict(richer=a.jurisdiction, richer_inc=a.inc, richer_ba=a.ba, richer_aes=a.aes,
                   poorer=b.jurisdiction, poorer_inc=b.inc, poorer_ba=b.ba, poorer_aes=b.aes,
                   gap=b.aes-a.aes) for a, b in out]).to_csv(
    f'{BASE}/analysis/income_matched_pairs.csv', index=False)
