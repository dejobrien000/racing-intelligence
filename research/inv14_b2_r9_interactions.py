"""Batch 1, B2 (plan: batch01_plan.md). Does the R9 combination add predictive information beyond its parts?
Fit on Queensland beaten finishers before 2025, score on Jan 2025 - Nov 2026 (internal out-of-sample, not independent).
Inputs come from runs_rated_dev.parquet (pars and class levels fitted on pre-2025 races only).
M1 = main effects; M2 = M1 + pre-set interactions of the last-600m gap with step up, tempo, class change, race strength and
figure. Trees: depth 1 (no interactions possible) vs depth 3. Outputs out/out_b2_*.csv"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import log_loss
from frames import next_start_frame
rng = np.random.default_rng(20261124)
b = next_start_frame('runs_rated_dev.parquet', level_until='2024-12-31')
b['meeting_date'] = pd.to_datetime(b.meeting_date)
b['gap600'] = b.l600_vs_best.clip(upper=3.0)
b['dist_change'] = b.next_distance_m - b.distance_m
b['tempo_c'] = b.tempo.clip(-2, 2)
b['fig_z'] = (b.rating - 95) / 5; b['pre_z'] = (b.best_last3 - 95) / 5
b['fs_z'] = (b.field_strength - 100) / 5
b['lgap'] = np.log(b.gap_to_next); b['lmargin'] = np.log(b.margin_l + 0.5); b['lnf'] = np.log(b.next_field)
need = ['gap600', 'step', 'tempo_band', 'class_delta', 'fig_z', 'pre_z', 'fs_z', 'settle_rel', 'lgap', 'lmargin', 'lnf', 'venue_tier', 'dist_band']
x = b.dropna(subset=need).copy(); x['step'] = x.step.astype(str); x['tempo_band'] = x.tempo_band.astype(str); x['dist_band'] = x.dist_band.astype(str)
x['tempo_fast'] = (x.tempo_band == 'fast early').astype(float); x['tempo_slow'] = (x.tempo_band == 'slow early').astype(float)
x['meeting_id'] = x.meeting_date.dt.strftime('%Y-%m-%d') + '|' + x.track
dev, ev = x[x.meeting_date < '2025-01-01'], x[x.meeting_date >= '2025-01-01']
print('runs: development', len(dev), 'evaluation', len(ev), '| horses', x.horse_id.nunique())
main = 'bs(gap600, df=3) + C(step) + C(tempo_band) + class_delta + fig_z + pre_z + fs_z + settle_rel + lgap + lmargin + lnf + C(venue_tier) + C(dist_band)'
inter = ' + gap600:step_up + gap600:tempo_fast + gap600:tempo_slow + gap600:class_delta + gap600:fs_z + gap600:fig_z'
models = {}
for name, f in [('M0 field size and margin only', 'lmargin + lnf'), ('M1 main effects', main), ('M2 main effects + interactions', main + inter)]:
    models[name] = smf.logit('next_win ~ ' + f, data=dev).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(dev.horse_id)[0]})
m2 = models['M2 main effects + interactions']
iterms = [t for t in m2.params.index if t.startswith('gap600:')]
w = m2.wald_test(' , '.join(f'{t} = 0' for t in iterms), scalar=True)
print('development Wald test of the interaction block (horse-clustered): chi2', round(float(w.statistic), 2), 'df', len(iterms), 'p', round(float(w.pvalue), 4))
coef = pd.DataFrame({'term': iterms, 'odds_ratio_per_second': np.exp(m2.params[iterms]).round(3), 'lo95': np.exp(m2.conf_int().loc[iterms, 0]).round(3),
                     'hi95': np.exp(m2.conf_int().loc[iterms, 1]).round(3), 'p': m2.pvalues[iterms].round(4)})
coef.to_csv('out/out_b2_interaction_terms.csv', index=False); print(coef.to_string(index=False))

# trees (numeric inputs; NaN allowed), tuned on 2024 inside the development period
feat = ['gap600', 'dist_change', 'tempo_c', 'class_delta', 'rating', 'best_last3', 'field_strength', 'settle_rel', 'gap_to_next', 'margin_l', 'next_field', 'distance_m', 'vt']
x['vt'] = x.venue_tier.map({'metro': 2, 'provincial': 1, 'country': 0}); dev, ev = x[x.meeting_date < '2025-01-01'], x[x.meeting_date >= '2025-01-01']
tr, va = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
trees = {}
for depth in [1, 3]:
    best = None
    for lr in [0.03, 0.1]:
        for it in [100, 200, 400]:
            m = HistGradientBoostingClassifier(max_depth=depth, learning_rate=lr, max_iter=it, min_samples_leaf=80, l2_regularization=1.0, random_state=1)
            m.fit(tr[feat], tr.next_win); ll = log_loss(va.next_win, m.predict_proba(va[feat])[:, 1])
            if best is None or ll < best[0]: best = (ll, lr, it)
    m = HistGradientBoostingClassifier(max_depth=depth, learning_rate=best[1], max_iter=best[2], min_samples_leaf=80, l2_regularization=1.0, random_state=1).fit(dev[feat], dev.next_win)
    trees[f'Trees depth {depth} ({"no interactions" if depth == 1 else "interactions allowed"})'] = (m, best)
# score everything on the evaluation period
pred = {k: v.predict(ev) for k, v in models.items()}
pred.update({k: v[0].predict_proba(ev[feat])[:, 1] for k, v in trees.items()})
y = ev.next_win.values
def rowll(p): p = np.clip(p, 1e-6, 1 - 1e-6); return -(y * np.log(p) + (1 - y) * np.log(1 - p))
ll = {k: rowll(np.asarray(p)) for k, p in pred.items()}
meet = ev.meeting_id.values; um = np.unique(meet); idx = {m: np.where(meet == m)[0] for m in um}
def boot(a, b_):
    d_ = ll[b_] - ll[a]; s = []
    for _ in range(1000):
        pick = np.concatenate([idx[m] for m in rng.choice(um, len(um))]); s.append(d_[pick].mean())
    return d_.mean(), np.percentile(s, 2.5), np.percentile(s, 97.5), float(np.mean(np.array(s) <= 0))
rows = [{'model': k, 'evaluation_log_loss': round(v.mean(), 5)} for k, v in ll.items()]
t = pd.DataFrame(rows); t.to_csv('out/out_b2_models.csv', index=False); print(t.to_string(index=False))
cmp = []
for a, c, label in [('M1 main effects', 'M2 main effects + interactions', 'Primary 2: M2 vs M1'),
                    ('Trees depth 1 (no interactions)', 'Trees depth 3 (interactions allowed)', 'Primary 3: trees depth 3 vs depth 1'),
                    ('M0 field size and margin only', 'M1 main effects', 'context: M1 vs field size and margin only'),
                    ('M1 main effects', 'Trees depth 1 (no interactions)', 'context: depth-1 trees vs M1')]:
    m_, lo, hi, p = boot(c, a)      # positive = second model better (lower loss)
    cmp.append({'comparison': label, 'log_loss_improvement_per_run': round(m_, 5), 'lo95': round(lo, 5), 'hi95': round(hi, 5), 'p_one_sided': round(p, 4)})
c = pd.DataFrame(cmp); c.to_csv('out/out_b2_primary.csv', index=False); print(c.to_string(index=False))
print('tree tuning (validation 2024 log loss, learning rate, iterations):', {k: tuple(round(z, 4) if isinstance(z, float) else z for z in v[1]) for k, v in trees.items()})
# secondary (R25): the same blocks with next figure change as the outcome, development data
r = dev.dropna(subset=['next_rating']).copy(); r['fig_change'] = r.next_rating - r.rating
o1 = smf.ols('fig_change ~ ' + main + inter, data=r).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(r.horse_id)[0]})
w2 = o1.wald_test(' , '.join(f'{t} = 0' for t in iterms), scalar=True)
print('R25 secondary: next figure change, interaction block p', round(float(w2.pvalue), 4), '| gap600 per second (main):',
      {k: round(v, 2) for k, v in o1.params.items() if k.startswith('bs(gap600')}, 'n', int(o1.nobs))
r25 = pd.DataFrame({'term': iterms, 'kg_per_second': o1.params[iterms].round(3), 'lo95': o1.conf_int().loc[iterms, 0].round(3), 'hi95': o1.conf_int().loc[iterms, 1].round(3), 'p': o1.pvalues[iterms].round(4)})
r25.to_csv('out/out_b2_r25_figure_change_terms.csv', index=False); print(r25.to_string(index=False)); print('Wald chi2', round(float(w2.statistic), 1))
