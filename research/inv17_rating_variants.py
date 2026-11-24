"""Batch 2, Study 1 (plan: batch02_plan.md). Rating variants against the simple form baseline, on matched races.
Chronological out-of-sample: fitted before 2025, scored Jan 2025 - Nov 2026 (not independent validation).
Outputs out/out_s1_*.csv"""
import re, numpy as np, pandas as pd
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
d = pd.read_parquet('runs_rated_dev.parquet').drop_duplicates(['race_id', 'horse_id'])
d['meeting_date'] = pd.to_datetime(d.meeting_date)
d = d.sort_values(['horse_id', 'meeting_date', 'race_no']).reset_index(drop=True)
dev = d.meeting_date < '2025-01-01'
level = d[dev].groupby('class_bucket')['rating'].median(); d['class_level'] = d.class_bucket.map(level)
# weight-for-age for age-restricted races (age otherwise unknown for Queensland runners)
nm = d.race_name.fillna('').str.upper()
d['age_r'] = np.where(nm.str.contains(r'2YO|TWO-YEAR|TWO YEAR|2-Y-O'), '2', np.where(nm.str.contains(r'3YO|THREE-YEAR|THREE YEAR|3-Y-O'), '3', 'open'))
d['mon'] = d.meeting_date.dt.month
w = d[dev & (d.win == 1) & d.rating.notna()]
base_cls = w[w.age_r == 'open'].groupby('class_bucket')['rating'].median()
w = w.assign(resid=w.rating - w.class_bucket.map(base_cls))
allow = w[w.age_r != 'open'].groupby(['age_r', 'mon'])['resid'].median() - w[w.age_r == 'open']['resid'].median()
d['wfa'] = [-(allow.get((a, m), 0.0)) if a != 'open' else 0.0 for a, m in zip(d.age_r, d.mon)]
d['fig'] = d.rating
d['fig_shrunk'] = d.class_level + 0.5 * (d.rating - d.class_level)
d['fig_opp'] = d.rating + 0.5 * (d.field_strength - d.class_level)
d['fig_wfa'] = d.rating + d.wfa
g = d.groupby('horse_id')
def prev(col, n=3, how='mean'): return g[col].transform(lambda s: getattr(s.shift().rolling(n, min_periods=1), how)())
V = d[['race_id', 'horse_id', 'meeting_date', 'track', 'field', 'win', 'race_name', 'distance_m', 'cond_group', 'class_bucket', 'days_since']].copy()
V['V1_best3'] = prev('fig', 3, 'max'); V['V2_last'] = g['fig'].shift(); V['V3_avg3'] = prev('fig')
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
def rec(s):
    a = s.shift().values; out = np.full(len(a), np.nan)
    for i in range(len(a)):
        h = a[max(0, i - 5):i + 1][::-1]; h = h[~np.isnan(h)] if len(h) else h
        if len(h): out[i] = np.dot(h, wts[:len(h)]) / wts[:len(h)].sum()
    return pd.Series(out, index=s.index)
V['V4_recency'] = g['fig'].transform(rec)
V['V5_shrunk'] = prev('fig_shrunk'); V['V6_opposition'] = prev('fig_opp'); V['V7_wfa'] = prev('fig_wfa')
V['B_avgfp3'] = -prev('finish_pct')
V['wt_rel_hcp'] = (pd.to_numeric(d.weight_kg, errors='coerce') - d.groupby('race_id')['weight_kg'].transform('mean')) * d.race_name.str.contains('HANDICAP|HCP', case=False, na=False)
V['period'] = np.where(V.meeting_date < '2025-01-01', 'development', 'evaluation')
V['meeting_id'] = V.meeting_date.dt.strftime('%Y-%m-%d') + '|' + V.track
x = eligible(V)
variants = ['V1_best3', 'V2_last', 'V3_avg3', 'V4_recency', 'V5_shrunk', 'V6_opposition', 'V7_wfa']
x = prep(x, variants + ['B_avgfp3', 'wt_rel_hcp'], {'missfig': 'V3_avg3', 'missform': 'B_avgfp3'})
print('eligible races: development', x[x.period == 'development'].race_id.nunique(), 'evaluation', x[x.period == 'evaluation'].race_id.nunique())

# matched sample 1: races where every runner has every measure; matched sample 2: all races, missing flagged
x['all_have'] = x.groupby('race_id')[variants + ['B_avgfp3']].transform(lambda s: s.notna().all()).all(axis=1)
samples = {'complete-figure races': x[x.all_have], 'all eligible races (missing flagged)': x}
rows, picks = [], []
for sname, s in samples.items():
    devll = {}
    for v in variants + ['B_avgfp3']:
        cols = [v] if sname.startswith('complete') else [v, 'missfig' if v != 'B_avgfp3' else 'missform']
        b = fit(s, cols); r = score(s, cols, b)
        r_dev = score(s, cols, b, period='development'); devll[v] = r_dev.lp.sum()
        rows.append({'sample': sname, 'measure': v, 'races': len(r), 'top_pick_win_%': round(100 * r.hit.mean(), 1), 'fit_%': round(fit_pct(r), 2), '_r': r})
    best = max(variants, key=lambda v: devll[v]); picks.append((sname, best))
t = pd.DataFrame(rows)
out = []
for sname, best in picks:
    rb = t[(t['sample'] == sname) & (t.measure == 'B_avgfp3')]._r.iloc[0]
    for v in variants + ['V8_avg3_plus_weight']:
        if v == 'V8_avg3_plus_weight':
            s = samples[sname]; cols = ['V3_avg3', 'wt_rel_hcp'] + ([] if sname.startswith('complete') else ['missfig'])
            r = score(s, cols, fit(s, cols)); t.loc[len(t)] = {'sample': sname, 'measure': v, 'races': len(r), 'top_pick_win_%': round(100 * r.hit.mean(), 1), 'fit_%': round(fit_pct(r), 2), '_r': r}
        r = t[(t['sample'] == sname) & (t.measure == v)]._r.iloc[0]
        fd = boot_diff(rb, r, 'lp'); hd = boot_diff(rb, r, 'hit')
        out.append({'sample': sname, 'variant': v, 'chosen_on_development': v == best, 'races': len(r), 'top_pick_%': round(100 * r.hit.mean(), 1), 'baseline_top_pick_%': round(100 * rb.hit.mean(), 1),
                    'top_pick_diff_pts': round(100 * hd[0], 1), 'tp_lo95': round(100 * hd[1], 1), 'tp_hi95': round(100 * hd[2], 1),
                    'fit_%': round(fit_pct(r), 2), 'baseline_fit_%': round(fit_pct(rb), 2), 'fit_gain_per_race': round(fd[0], 4), 'fit_lo95': round(fd[1], 4), 'fit_hi95': round(fd[2], 4), 'p_one_sided': round(fd[3], 4)})
o = pd.DataFrame(out); o.to_csv('out/out_s1_variants_vs_baseline.csv', index=False); print(o.to_string(index=False)); print('chosen on development:', picks)

# why so few complete-figure races: share of runners with a figure, and how those races differ
e = x[x.period == 'evaluation']
rr = e.groupby('race_id').agg(field=('field', 'first'), frac_fig=('V3_avg3', lambda s: s.notna().mean()), complete=('all_have', 'first'),
                              maiden=('class_bucket', lambda s: (s.iloc[0] == 'Maiden')), track=('track', 'first'), dist=('distance_m', 'first'))
rr['tier'] = np.where(rr.track.isin(['Eagle_Farm', 'Doomben']), 'metro', np.where(rr.track.isin(['Sunshine_Coast', 'Sunshine_Coast_Poly_Track', 'TAB_Park_Gold_Coast', 'Ipswich', 'Toowoomba']), 'provincial', 'country'))
first_q = e.groupby('race_id').apply(lambda h: (h.V3_avg3.isna() & h.B_avgfp3.isna()).sum(), include_groups=False)
unrated = e.groupby('race_id').apply(lambda h: (h.V3_avg3.isna() & h.B_avgfp3.notna()).sum(), include_groups=False)
rr['n_no_qld_run'] = first_q; rr['n_unrated_prior'] = unrated
sel = rr.groupby('complete').agg(races=('field', 'size'), mean_field=('field', 'mean'), maiden_pct=('maiden', lambda s: round(100 * s.mean(), 1)),
      metro_pct=('tier', lambda s: round(100 * (s == 'metro').mean(), 1)), country_pct=('tier', lambda s: round(100 * (s == 'country').mean(), 1)),
      runners_with_figure_pct=('frac_fig', lambda s: round(100 * s.mean(), 1)), avg_no_qld_run=('n_no_qld_run', 'mean'), avg_unrated=('n_unrated_prior', 'mean')).round(2)
sel.to_csv('out/out_s1_complete_selection.csv'); print(sel.to_string())
print('share of runners with a prior figure:', round(e.V3_avg3.notna().mean(), 3), '| expected share of complete 10-runner races if independent:', round(e.V3_avg3.notna().mean() ** 10, 3))
# where does the figure lose ground to the baseline? per-race fit difference by race type (all races, flagged)
s = samples['all eligible races (missing flagged)']
ra = score(s, ['V3_avg3', 'missfig'], fit(s, ['V3_avg3', 'missfig'])); rb = score(s, ['B_avgfp3', 'missform'], fit(s, ['B_avgfp3', 'missform']))
info = e.groupby('race_id').agg(tier=('track', lambda s: 'metro' if s.iloc[0] in ('Eagle_Farm', 'Doomben') else ('provincial' if s.iloc[0] in ('Sunshine_Coast', 'Sunshine_Coast_Poly_Track', 'TAB_Park_Gold_Coast', 'Ipswich', 'Toowoomba') else 'country')),
      dist=('distance_m', lambda s: pd.cut([s.iloc[0]], [0, 1150, 1450, 1750, 9999], labels=['<=1150', '1200-1450', '1500-1750', '1800+'])[0]),
      going=('cond_group', 'first'), maiden=('class_bucket', lambda s: s.iloc[0] == 'Maiden'), firstup_share=('days_since', lambda s: (s >= 60).mean()))
diff = (ra.lp - rb.lp).rename('fig_minus_form').to_frame().join(info)
diag = []
for col in ['tier', 'dist', 'going', 'maiden']:
    for k, h in diff.groupby(col, observed=True):
        diag.append({'split': col, 'group': k, 'races': len(h), 'figure_minus_form_fit_per_race': round(h.fig_minus_form.mean(), 4)})
diff['fu'] = pd.cut(diff.firstup_share, [-0.01, 0.1, 0.3, 1.01], labels=['few first-up', 'some', 'many first-up'])
for k, h in diff.groupby('fu', observed=True): diag.append({'split': 'first-up share', 'group': k, 'races': len(h), 'figure_minus_form_fit_per_race': round(h.fig_minus_form.mean(), 4)})
dg = pd.DataFrame(diag); dg.to_csv('out/out_s1_where_figure_loses.csv', index=False); print(dg.to_string(index=False))
