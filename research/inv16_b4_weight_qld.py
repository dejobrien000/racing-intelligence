"""Batch 1, B4 (Queensland part, primary test 5). Weight change from last start and the next run (R41).
All finishers with a true next start 7-60 days later (no interstate run between), fields 6+.
Controls: class change (rating units), the run's figure, last-start win, beaten margin, next field size.
Secondary: weight band x class move; handicaps only. Usage: python3 inv16_b4_weight_qld.py -> out/out_b4_qld_*.csv"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import chi2
d = pd.read_parquet('runs_rated.parquet').drop_duplicates(['race_id', 'horse_id'])
for c in ['margin_l', 'next_field', 'next_win', 'gap_to_next', 'next_days_since', 'weight_kg']:
    d[c] = pd.to_numeric(d[c], errors='coerce').astype(float)
level = d.groupby('class_bucket')['rating'].median()
d['class_delta'] = d.next_class_bucket.map(level) - d.class_bucket.map(level)
nx = d[['race_id', 'horse_id', 'weight_kg', 'race_name']].rename(columns={'race_id': 'next_race_id', 'weight_kg': 'next_weight', 'race_name': 'next_race_name'})
d = d.merge(nx, on=['next_race_id', 'horse_id'], how='left')
x = d[d.finished & (d.field >= 6) & (d.next_field >= 6) & d.gap_to_next.between(7, 60) & (d.next_days_since == d.gap_to_next) & d.next_weight.notna() & d.weight_kg.notna()].copy()
wc = x.next_weight - x.weight_kg
x['wt_band'] = pd.cut(wc, [-99, -2, 1.5, 99], right=False, labels=['drop 2kg+', 'within 1.5kg', 'rise 2kg+']); x = x[x.wt_band.notna()]
x['drop2'] = (x.wt_band == 'drop 2kg+').astype(int); x['rise2'] = (x.wt_band == 'rise 2kg+').astype(int)
x['next_win'] = x.next_win.astype(int); x['exp'] = 1 / x.next_field
x['lm'] = np.log(x.margin_l + 0.5); x['lnf'] = np.log(x.next_field); x['fig_z'] = (x.rating - 95) / 5
x['class_move'] = pd.cut(x.class_delta, [-99, -1.5, 1.5, 99], labels=['drops in class', 'same class', 'rises in class'])
x['next_hcp'] = x.next_race_name.str.contains('HANDICAP|HCP', case=False, na=False)
def ae(h):
    w, e = h.next_win.sum(), h.exp.sum(); return round(w / e, 2), round(chi2.ppf(0.025, 2 * w) / 2 / e, 2), round(chi2.ppf(0.975, 2 * w + 2) / 2 / e, 2)
rows = []
for keys, h in x.groupby(['class_move', 'wt_band'], observed=True):
    a = ae(h); rows.append({'class_move': keys[0], 'weight': keys[1], 'runs': len(h), 'next_win_%': round(100 * h.next_win.mean(), 1), 'A/E': a[0], 'lo95': a[1], 'hi95': a[2]})
for k, h in x.groupby('wt_band', observed=True):
    a = ae(h); rows.append({'class_move': 'all', 'weight': k, 'runs': len(h), 'next_win_%': round(100 * h.next_win.mean(), 1), 'A/E': a[0], 'lo95': a[1], 'hi95': a[2]})
t = pd.DataFrame(rows); t.to_csv('out/out_b4_qld_cells.csv', index=False); print(t.to_string(index=False))
res = []
cc = x.dropna(subset=['class_delta', 'fig_z'])
for name, f, data in [('Primary 5: adjusted (class change, figure, won, margin, next field)', 'next_win ~ drop2 + rise2 + class_delta + fig_z + win + lm + lnf', cc),
                      ('unadjusted except margin and next field', 'next_win ~ drop2 + rise2 + lm + lnf', cc),
                      ('handicaps only (next race), adjusted', 'next_win ~ drop2 + rise2 + class_delta + fig_z + win + lm + lnf', cc[cc.next_hcp]),
                      ('weight x class move interaction, adjusted', 'next_win ~ drop2 * C(class_move) + rise2 + class_delta + fig_z + win + lm + lnf', cc)]:
    m = smf.logit(f, data=data).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(data.horse_id)[0]})
    for term in [t_ for t_ in m.params.index if t_.startswith('drop2') or t_ == 'rise2']:
        res.append({'model': name, 'term': term, 'odds_ratio': round(np.exp(m.params[term]), 3), 'lo95': round(np.exp(m.conf_int().loc[term, 0]), 3),
                    'hi95': round(np.exp(m.conf_int().loc[term, 1]), 3), 'p': round(m.pvalues[term], 4), 'runs': int(m.nobs)})
r = pd.DataFrame(res); r.to_csv('out/out_b4_qld_models.csv', index=False); print(r.to_string(index=False))
