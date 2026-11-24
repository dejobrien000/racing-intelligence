"""Batch 1, B1 (plan: batch01_plan.md). Rating v0 against simple baselines (R15, R17).
Ratings: runs_rated_dev.parquet = rating_v0.py with pars and class allowances fitted on races before 2025 only.
Each measure is fitted (within-race conditional logit) on development races and scored on evaluation races (2025-26).
Outputs out/out_b1_*.csv"""
import numpy as np, pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit
rng = np.random.default_rng(20261124)
d = pd.read_parquet('runs_rated_dev.parquet').drop_duplicates(['race_id', 'horse_id'])
d['meeting_date'] = pd.to_datetime(d.meeting_date)
d = d.sort_values(['horse_id', 'meeting_date', 'race_no'])
g = d.groupby('horse_id')
d['prev_fp'] = -g['finish_pct'].shift()                                     # higher = better
d['prev_logmargin'] = -np.log(pd.to_numeric(g['margin_l'].shift(), errors='coerce').astype(float) + 0.5)
d['avg_fp3'] = -g['finish_pct'].transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
starts = g.cumcount(); wins = g['win'].transform(lambda s: s.shift().fillna(0).cumsum())
d['career_win'] = np.where(starts > 0, wins / starts.replace(0, np.nan), np.nan)
dev_mask = d.meeting_date < '2025-01-01'
level = d[dev_mask].groupby('class_bucket')['rating'].median()              # class level from development races only
d['prev_class_level'] = g['class_bucket'].shift().map(level)
d['last_fig'] = d['prev_rating']; d['best3'] = d['best_last3']; d['avg3'] = d['avg_last3']
d['is_hcp'] = d.race_name.str.contains('HANDICAP|HCP', case=False, na=False)
d['weight_today'] = pd.to_numeric(d.weight_kg, errors='coerce')
meas = ['best3', 'last_fig', 'avg3', 'prev_fp', 'prev_logmargin', 'avg_fp3', 'career_win', 'prev_class_level']
labels = {'best3': 'Rating v0: best of last 3 figures (R15)', 'last_fig': 'Rating v0: last figure (R17)', 'avg3': 'Rating v0: average of last 3 (R17)',
          'prev_fp': 'Baseline: last-start finishing position', 'prev_logmargin': 'Baseline: last-start beaten margin', 'avg_fp3': 'Baseline: average finishing position, last 3',
          'career_win': 'Baseline: career win % before the race', 'prev_class_level': 'Baseline: class of last race', 'weight_today': 'Baseline: weight carried (handicaps only)'}
x = d[(d.field >= 6) & d.finished.notna()].copy()
x['n_win'] = x.groupby('race_id')['win'].transform('sum'); x = x[x.n_win == 1]
x['complete'] = x.groupby('race_id')[meas].transform(lambda s: s.notna().all()).all(axis=1)
x['n_in'] = x.groupby('race_id')['race_id'].transform('size'); x = x[x.complete & (x.n_in == x.field)]
x['period'] = np.where(x.meeting_date < '2025-01-01', 'development', 'evaluation')
x['meeting_id'] = x.meeting_date.dt.strftime('%Y-%m-%d') + '|' + x.track
for c in meas + ['weight_today']:
    x[c + '_z'] = (x[c] - x.groupby('race_id')[c].transform('mean')) / (x[c].std() or 1)
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']
print('complete-field races: development', dev.race_id.nunique(), 'evaluation', ev.race_id.nunique(),
      ' (share of all 6+ evaluation races kept:', round(ev.race_id.nunique() / d[(d.meeting_date >= '2025-01-01') & (d.field >= 6)].race_id.nunique(), 2), ')')

def fit(cols, data):
    m = ConditionalLogit(data['win'].values, data[[c + '_z' for c in cols]].values, groups=data['race_id'].values).fit(disp=0)
    return np.asarray(m.params)
def race_ll(cols, beta, data):
    eta = data[[c + '_z' for c in cols]].values @ beta
    t = data[['race_id', 'win', 'meeting_id']].copy(); t['eta'] = eta
    t['lse'] = t.groupby('race_id')['eta'].transform(lambda s: np.log(np.exp(s - s.max()).sum()) + s.max())
    t['lp'] = t.eta - t.lse
    r = t[t.win == 1][['race_id', 'meeting_id', 'lp']].set_index('race_id'); return r
null = ev.groupby('race_id').agg(meeting_id=('meeting_id', 'first'), lp=('field', lambda s: -np.log(s.iloc[0])))
rows = []
for c in meas:
    b = fit([c], dev); r = race_ll([c], b, ev)
    top = ev.loc[ev.groupby('race_id')[c].idxmax()]
    rows.append({'measure': labels[c], 'races': ev.race_id.nunique(), 'top_pick_win_%': round(100 * top.win.mean(), 1),
                 'top_pick_A/E': round(top.win.sum() / (1 / top.field).sum(), 2), 'out_of_sample_R2_%': round(100 * (1 - r.lp.sum() / null.lp.sum()), 2)})
# handicap weight, on handicap races only (with the figure alongside for comparison)
hw = lambda t: t[t.is_hcp & t.groupby('race_id')['weight_today'].transform(lambda s: s.notna().all())]
h_dev, h_ev = hw(dev), hw(ev)
hn = h_ev.groupby('race_id').agg(lp=('field', lambda s: -np.log(s.iloc[0])))
for c in ['weight_today', 'best3']:
    b = fit([c], h_dev); r = race_ll([c], b, h_ev); top = h_ev.loc[h_ev.groupby('race_id')[c].idxmax()]
    rows.append({'measure': labels[c] + (' (handicaps only)' if c == 'best3' else ''), 'races': h_ev.race_id.nunique(), 'top_pick_win_%': round(100 * top.win.mean(), 1),
                 'top_pick_A/E': round(top.win.sum() / (1 / top.field).sum(), 2), 'out_of_sample_R2_%': round(100 * (1 - r.lp.sum() / hn.lp.sum()), 2)})
t = pd.DataFrame(rows); t.to_csv('out/out_b1_measures.csv', index=False); print(t.to_string(index=False))

# primary test 1: all baselines vs all baselines + best-of-3 figure (and + all three figure measures)
base = ['prev_fp', 'prev_logmargin', 'avg_fp3', 'career_win', 'prev_class_level']
res = []
for name, cols in [('all baselines', base), ('baselines + best of 3', base + ['best3']), ('baselines + all three figure measures', base + ['best3', 'last_fig', 'avg3'])]:
    b = fit(cols, dev); r = race_ll(cols, b, ev); res.append((name, r, b))
r0 = res[0][1]
out = []
for name, r, b in res:
    diff = (r.lp - r0.lp)
    per_meet = diff.groupby(r.meeting_id).sum(); meets = per_meet.index.values
    boots = [per_meet.loc[rng.choice(meets, len(meets))].sum() / len(r) for _ in range(1000)]
    out.append({'model': name, 'out_of_sample_R2_%': round(100 * (1 - r.lp.sum() / null.lp.sum()), 2), 'gain_in_log_lik_per_race_vs_baselines': round(diff.mean(), 4),
                'lo95': round(np.percentile(boots, 2.5), 4), 'hi95': round(np.percentile(boots, 97.5), 4),
                'p_one_sided': round(float(np.mean(np.array(boots) <= 0)), 4) if name != 'all baselines' else None})
o = pd.DataFrame(out); o.to_csv('out/out_b1_primary.csv', index=False); print(o.to_string(index=False))
print('coefficients (per sd), baselines + best of 3:', dict(zip(base + ['best3'], np.round(res[1][2], 3))))

# sensitivity (not in the plan's primary test): all 6+ races, missing measures filled at the race average with a missing flag
y = d[(d.field >= 6)].copy(); y['n_win'] = y.groupby('race_id')['win'].transform('sum'); y = y[(y.n_win == 1)]
y['n_in'] = y.groupby('race_id')['race_id'].transform('size'); y = y[y.n_in == y.field]
y['period'] = np.where(y.meeting_date < '2025-01-01', 'development', 'evaluation'); y['meeting_id'] = y.meeting_date.dt.strftime('%Y-%m-%d') + '|' + y.track
for c in meas:
    z = (y[c] - y.groupby('race_id')[c].transform('mean')) / (y[c].std() or 1)
    y[c + '_z'] = z.fillna(0); y[c + 'miss_z'] = y[c].isna().astype(float) - y.groupby('race_id')[c].transform(lambda s: s.isna().mean())
dv2, ev2 = y[y.period == 'development'], y[y.period == 'evaluation']
null2 = ev2.groupby('race_id').agg(meeting_id=('meeting_id', 'first'), lp=('field', lambda s: -np.log(s.iloc[0])))
sens = []
cols_b = base + ['prev_fpmiss', 'prev_class_levelmiss']
for name, cols in [('all baselines', cols_b), ('baselines + best of 3', cols_b + ['best3', 'best3miss'])]:
    b = fit(cols, dv2); r = race_ll(cols, b, ev2); sens.append((name, r))
d0 = sens[0][1]; d1 = sens[1][1]; diff = d1.lp - d0.lp; pm = diff.groupby(d1.meeting_id).sum(); ms = pm.index.values
bs = [pm.loc[rng.choice(ms, len(ms))].sum() / len(d1) for _ in range(1000)]
print('SENSITIVITY all races (', ev2.race_id.nunique(), 'evaluation races): R2 baselines', round(100 * (1 - d0.lp.sum() / null2.lp.sum()), 2),
      '+ best of 3', round(100 * (1 - d1.lp.sum() / null2.lp.sum()), 2), 'gain per race', round(diff.mean(), 4), 'CI', round(np.percentile(bs, 2.5), 4), round(np.percentile(bs, 97.5), 4))
pd.DataFrame([{'population': 'all 6+ races, missing filled + flag', 'races': ev2.race_id.nunique(), 'R2_baselines_%': round(100 * (1 - d0.lp.sum() / null2.lp.sum()), 2),
               'R2_plus_best3_%': round(100 * (1 - d1.lp.sum() / null2.lp.sum()), 2), 'gain_per_race': round(diff.mean(), 4), 'lo95': round(np.percentile(bs, 2.5), 4), 'hi95': round(np.percentile(bs, 97.5), 4)}]).to_csv('out/out_b1_sensitivity_all_races.csv', index=False)
