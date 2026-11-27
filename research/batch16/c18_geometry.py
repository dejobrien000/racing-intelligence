"""Batch 16 C18: actual course geometry x horse momentum (Qld tracked courses; research only, descriptive first).
Geometry from public sources (research/batch16/course_geometry.csv; conflicts noted there). Late-momentum tendency is the horse's own
point-in-time average of last-200 m speed relative to the race (earlier runs only, 3+ runs). Outcome: this run's performance relative
to its rating (national-rating innovation, kg). Question: do late-finishing horses beat their rating by more where the straight is long?"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
G = pd.read_csv('batch16/course_geometry.csv'); G = G[G.state == 'QLD']
R = pd.read_parquet('/home/claude/b14/runs_QLD.parquet', columns=['race_id', 'horse', 'meeting_date', 'track', 'distance_m', 'v200_rel', 'early_sp', 'dyn_nat_inn', 'field_x', 'fp'])
R = R.sort_values(['horse', 'meeting_date', 'race_id']); g = R.groupby('horse')
R['late_prior'] = g.v200_rel.transform(lambda s: s.shift().expanding().mean()); R['n_prior'] = g.cumcount()
R['early_prior'] = g.early_sp.transform(lambda s: s.shift().expanding().mean())
R['track'] = R.track.str.replace('_', ' '); R = R.merge(G[['course', 'home_straight_m']], left_on='track', right_on='course', how='inner')
R = R[(R.n_prior >= 3) & R.dyn_nat_inn.notna() & R.late_prior.notna()].copy()
R['late_z'] = (R.late_prior - R.late_prior.mean()) / R.late_prior.std(); R['early_z'] = (R.early_prior - R.early_prior.mean()) / R.early_prior.std()
R['straight_100m'] = (R.home_straight_m - R.home_straight_m.mean()) / 100; R['dband'] = pd.cut(R.distance_m, [0, 1150, 1450, 1750, 9999]).astype(str)
R['yr'] = pd.to_datetime(R.meeting_date).dt.year
OUT = {'runs': int(len(R)), 'courses': R.groupby('track').size().to_dict(), 'geometry': G[['course', 'home_straight_m', 'circumference_m']].to_dict('records')}
for lab, d in [('all', R), ('2022-24', R[R.yr <= 2024]), ('2025-26', R[R.yr >= 2025])]:
    d = d.dropna(subset=['dyn_nat_inn', 'late_z', 'early_z', 'straight_100m', 'dband'])
    m = smf.ols('dyn_nat_inn ~ late_z * straight_100m + early_z * straight_100m + C(dband)', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    OUT[lab] = {k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)] for k in ['late_z', 'late_z:straight_100m', 'early_z', 'early_z:straight_100m']}
    OUT[lab]['n'] = int(m.nobs)
# by course: late finishers' residual
R['late_q'] = pd.qcut(R.late_z, 4, labels=['early-fading', 'q2', 'q3', 'late-finishing'])
OUT['by_course_late_quartile_mean_inn'] = {t: {str(k): round(float(v), 2) for k, v in d.groupby('late_q', observed=True).dyn_nat_inn.mean().items()} for t, d in R.groupby('track')}
json.dump(OUT, open('batch16/out_c18_geometry.json', 'w'), indent=1); print(json.dumps({k: OUT[k] for k in ['runs', 'all', '2022-24', '2025-26']}))
print(json.dumps(OUT['by_course_late_quartile_mean_inn']))
