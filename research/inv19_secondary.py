"""Batch 2 secondary (descriptive, not primary tests). Same models and periods as inv18 (chronological out-of-sample).
(a) does agreement between groups add anything to the combined model?  (b) R18 and R49 inside ability: drop the opposition
strength or the weight input alone. (c) recency-weighted figure in place of the 3-run average. (d) R40: field-strength
change vs class-label change for next-start results. Outputs out/out_s2b_*.csv"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
exec(open('inv18_evidence_groups.py').read().split("ev_races =")[0])          # same features, groups and preparation
from clogit_tools import fit, score, boot_diff, fit_pct
ALL = [c for v in G.values() for c in v]
# recency-weighted figure (V4 weights) from runs_rated_dev, keyed by race and horse
d = pd.read_parquet('runs_rated_dev.parquet').drop_duplicates(['race_id', 'horse_id']).sort_values(['horse_id', 'meeting_date', 'race_no'])
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
def rec(s):
    a = s.shift().values; out = np.full(len(a), np.nan)
    for i in range(len(a)):
        h = a[max(0, i - 5):i + 1][::-1]; h = h[~np.isnan(h)]
        if len(h): out[i] = np.dot(h, wts[:len(h)]) / wts[:len(h)].sum()
    return pd.Series(out, index=s.index)
d['a_rec'] = d.groupby('horse_id')['rating'].transform(rec)
x = x.merge(d[['race_id', 'horse_id', 'a_rec']], on=['race_id', 'horse_id'], how='left')
x = prep(x, ['a_rec'])
res = {}
def run(name, cs): b = fit(x, cs); res[name] = (score(x, cs, b), b); return res[name][0]
run('Full', ALL)
# group scores for agreement votes (each group alone, as in inv18)
for gname, gc in G.items():
    cs = gc if gname[0] == 'F' else gc + ['missform']; b = fit(x, cs); x['sc_' + gname[0]] = x[[c + '_z' for c in cs]].values @ b
for k in 'ASPTR':
    x['top_' + k] = x.groupby('race_id')['sc_' + k].transform(lambda s: (s.rank(method='first', ascending=False) == 1).astype(float))
x['votes'] = x[['top_' + k for k in 'ASPTR']].sum(axis=1); x = prep(x, ['votes'])
run('Full + agreement votes', ALL + ['votes'])
run('Full - opposition strength faced (R18)', [c for c in ALL if c != 'a_fs3'])
run('Full - weight relative to field (R49)', [c for c in ALL if c != 'a_wt_rel'])
run('Full with recency-weighted figure', [c if c != 'a_avg3' else 'a_rec' for c in ALL])
rows = []
for a_, b_, label in [('Full', 'Full + agreement votes', '(a) agreement votes added to the combined model'),
                      ('Full - opposition strength faced (R18)', 'Full', '(b) opposition strength faced (R18) beyond everything else'),
                      ('Full - weight relative to field (R49)', 'Full', '(b) weight relative to the field (R49) beyond everything else'),
                      ('Full', 'Full with recency-weighted figure', '(c) recency-weighted figure instead of the 3-run average')]:
    m, lo, hi, p = boot_diff(res[a_][0], res[b_][0], 'lp'); hm, hlo, hhi, _ = boot_diff(res[a_][0], res[b_][0], 'hit')
    rows.append({'check': label, 'fit_gain_per_race': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'p_one_sided': round(p, 4), 'top_pick_diff_pts': round(100 * hm, 1), 'tp_lo95': round(100 * hlo, 1), 'tp_hi95': round(100 * hhi, 1)})
o = pd.DataFrame(rows); o.to_csv('out/out_s2b_secondary.csv', index=False); print(o.to_string(index=False))
# (d) R40: which explains next-start results better, the class-label move or the field-strength move? (beaten + winners)
from frames import next_start_frame
b = next_start_frame('runs_rated_dev.parquet', level_until='2024-12-31')
b['fs_delta'] = b.next_field_strength - b.field_strength
b['md'] = pd.to_datetime(b.meeting_date)
b = b.dropna(subset=['class_delta', 'fs_delta']).copy(); b['lm'] = np.log(b.margin_l + 0.5); b['lnf'] = np.log(b.next_field)
dv, ev = b[b.md < '2025-01-01'], b[b.md >= '2025-01-01']
out = []
for name, f in [('margin + field only', 'lm + lnf'), ('+ class-label move', 'lm + lnf + class_delta'), ('+ field-strength move', 'lm + lnf + fs_delta'), ('+ both', 'lm + lnf + class_delta + fs_delta')]:
    m = smf.logit('next_win ~ ' + f, data=dv).fit(disp=0); p = np.clip(m.predict(ev), 1e-6, 1 - 1e-6)
    ll = -(ev.next_win * np.log(p) + (1 - ev.next_win) * np.log(1 - p)).mean()
    out.append({'R40 next-start model (beaten runners)': name, 'evaluation_log_loss': round(ll, 5), 'coef_class_delta': round(m.params.get('class_delta', np.nan), 3), 'coef_fs_delta': round(m.params.get('fs_delta', np.nan), 3), 'runs_dev': len(dv), 'runs_eval': len(ev)})
r40 = pd.DataFrame(out); r40.to_csv('out/out_s2b_r40.csv', index=False); print(r40.to_string(index=False))
