"""Batch 16 C15: individual distance suitability from measured performance (not wins). Research only.
Performance = this run's surprise against the opposition-aware rating (kg). The rating already knows how good the horse is overall;
a surprise at a distance is what distance adds or takes away for THIS horse. Every horse-level quantity uses earlier runs only.
1. Transitions: surprise by previous distance -> today's distance (common steps), direction and size; asymmetry of up vs down.
2. First time at a distance band (untested) vs tried before; up vs down.
3. Continuous individual suitability: the horse's own earlier surprises weighted by closeness of distance (Gaussian kernel, 150 m),
   shrunk towards 0 (k = 3 runs of weight). Does it predict today's surprise, and does it add to the production distance-band record (d_rec)?
4. Evidence strength: same test split by how much nearby evidence the horse has (kernel weight), and whether consecutive similar-distance
   runs agree (consistency of nearby evidence).
5. Physical (Qld tracking): do horses with a strong late finish improve more when stepping up? (late = own earlier last-200 m speed vs race).
Usage (from research/): python3 batch16/c15_distance.py -> batch16/out_c15_distance.json"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'distance_m', 'dyn_nat_inn', 'd_rec', 'd_rec_n', 'age_n', 'state', 'class_label'])
U = U[U.dyn_nat_inn.notna()].sort_values(['horse', 'date', 'race']).reset_index(drop=True)
g = U.groupby('horse'); U['prev_d'] = g.distance_m.shift(); U['n_prior'] = g.cumcount()
U['band'] = pd.cut(U.distance_m, [0, 1150, 1450, 1750, 2150, 9999], labels=['<=1150', '1151-1450', '1451-1750', '1751-2150', '2151+']).astype(str)
U['tried_band'] = U.groupby(['horse', 'band']).cumcount() > 0
OUT = {}
E = U[(U.date >= '2023-07-01') & (U.n_prior >= 1)].copy()
se = lambda x: float(x.std() / np.sqrt(len(x))) if len(x) > 1 else float('nan')
# 1 transitions
r100 = lambda x: (np.round(x / 200) * 200).astype(int)
E['from'] = r100(E.prev_d); E['to'] = r100(E.distance_m); E['step'] = E.to - E['from']
T = E.groupby(['from', 'to']).dyn_nat_inn.agg(['size', 'mean', se]).reset_index(); T = T[T['size'] >= 400]
OUT['transitions_mean_surprise_kg'] = {f"{int(r['from'])}->{int(r.to)}": [int(r['size']), round(float(r['mean']), 2), round(float(r['<lambda_0>']), 2)] for _, r in T.iterrows()}
E['stepb'] = pd.cut(E.distance_m - E.prev_d, [-9999, -601, -301, -101, 100, 300, 600, 9999], labels=['down 600+', 'down 300-600', 'down 100-300', 'same (+-100)', 'up 100-300', 'up 300-600', 'up 600+']).astype(str)
OUT['by_step_size'] = {k: [int(len(v)), round(float(v.dyn_nat_inn.mean()), 2), round(se(v.dyn_nat_inn), 2)] for k, v in E.groupby('stepb')}
OUT['by_step_size_young_vs_old'] = {f'{k[0]} | {k[1]}': [int(len(v)), round(float(v.dyn_nat_inn.mean()), 2)] for k, v in E.assign(ag=np.where(E.age_n <= 3, 'age 2-3', 'age 4+')).groupby(['stepb', 'ag']) if len(v) >= 300}
# 2 untested
E['dir'] = np.sign(E.distance_m - E.prev_d)
OUT['first_time_at_band_vs_tried'] = {f"{'first time' if not t else 'tried before'} | {'up' if d > 0 else 'down' if d < 0 else 'same'}": [int(len(v)), round(float(v.dyn_nat_inn.mean()), 2), round(se(v.dyn_nat_inn), 2)] for (t, d), v in E.groupby(['tried_band', 'dir'])}
# 3 continuous kernel suitability (point in time), computed per horse
H = 150.0; K = 3.0
suit = np.full(len(U), np.nan); wsum = np.zeros(len(U)); agree = np.full(len(U), np.nan)
for h, idx in U.groupby('horse').indices.items():
    d = U.distance_m.values[idx].astype(float); s = U.dyn_nat_inn.values[idx]
    for j in range(1, len(idx)):
        w = np.exp(-0.5 * ((d[:j] - d[j]) / H) ** 2); ws = w.sum(); wsum[idx[j]] = ws
        suit[idx[j]] = (w * s[:j]).sum() / (ws + K)
        near = s[:j][np.abs(d[:j] - d[j]) <= 100]
        if len(near) >= 2: agree[idx[j]] = np.std(near)
U['suit'] = suit; U['suit_w'] = wsum; U['near_sd'] = agree
# horse overall mean surprise (point in time), to separate distance-specific from 'beats its rating anywhere'
U['mean_prior'] = U.groupby('horse').dyn_nat_inn.transform(lambda s: s.shift().expanding().mean() * s.shift().expanding().count() / (s.shift().expanding().count() + K))
E = U[(U.date >= '2023-07-01') & (U.n_prior >= 3)].copy(); E['suit_specific'] = E.suit - E.mean_prior * (E.suit_w / (E.suit_w + 0))
def ols(f, d):
    d = d.dropna(subset=[c for c in ['dyn_nat_inn', 'suit', 'd_rec', 'mean_prior', 'suit_specific'] if c in f]); m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    return m
for per, d in [('2023H2-24', E[E.date < '2025-01-01']), ('2025-26', E[E.date >= '2025-01-01'])]:
    m1 = ols('dyn_nat_inn ~ suit', d); m2 = ols('dyn_nat_inn ~ suit + d_rec + mean_prior', d)
    OUT[f'kernel_suitability_{per}'] = {'alone_per_kg': [round(m1.params['suit'], 3), round(m1.conf_int().loc['suit', 0], 3), round(m1.conf_int().loc['suit', 1], 3)],
                                        'given_d_rec_and_general_overperformance': [round(m2.params['suit'], 3), round(m2.conf_int().loc['suit', 0], 3), round(m2.conf_int().loc['suit', 1], 3)],
                                        'd_rec_given_suit': [round(m2.params['d_rec'], 3), round(m2.conf_int().loc['d_rec', 0], 3), round(m2.conf_int().loc['d_rec', 1], 3)],
                                        'general_overperformance': [round(m2.params['mean_prior'], 3)], 'n': int(m2.nobs)}
# 4 evidence strength
E['wb'] = pd.cut(E.suit_w, [0, 1, 3, 6, 999], labels=['<1 run nearby', '1-3', '3-6', '6+']).astype(str)
OUT['kernel_slope_by_nearby_evidence'] = {}
for k, d in E.groupby('wb'):
    if len(d) < 3000: continue
    m = ols('dyn_nat_inn ~ suit + mean_prior', d); OUT['kernel_slope_by_nearby_evidence'][k] = [round(m.params['suit'], 3), round(m.conf_int().loc['suit', 0], 3), round(m.conf_int().loc['suit', 1], 3), int(m.nobs)]
E['agree'] = pd.qcut(E.near_sd, 3, labels=['consistent nearby runs', 'middle', 'scattered nearby runs']).astype(str)
OUT['kernel_slope_by_consistency_of_nearby_runs'] = {}
for k, d in E[E.near_sd.notna()].groupby('agree'):
    m = ols('dyn_nat_inn ~ suit + mean_prior', d); OUT['kernel_slope_by_consistency_of_nearby_runs'][k] = [round(m.params['suit'], 3), round(m.conf_int().loc['suit', 0], 3), round(m.conf_int().loc['suit', 1], 3), int(m.nobs)]
# how often is an 'optimal distance' even estimable? share of runs whose horse has 3+ runs of weight at the distance and at +-400 m
OUT['share_runs_with_evidence_here_and_400m_away'] = round(float(((E.suit_w >= 3)).mean()), 3)
# 5 physical: Qld late finishers stepping up
try:
    R = pd.read_parquet('/home/claude/b14/runs_QLD.parquet', columns=['horse', 'meeting_date', 'race_id', 'distance_m', 'v200_rel', 'dyn_nat_inn'])
    R = R.sort_values(['horse', 'meeting_date', 'race_id']); gq = R.groupby('horse')
    R['late_prior'] = gq.v200_rel.transform(lambda s: s.shift().expanding(3).mean()); R['prev_d'] = gq.distance_m.shift()
    R = R.dropna(subset=['late_prior', 'prev_d', 'dyn_nat_inn']); R['late_z'] = (R.late_prior - R.late_prior.mean()) / R.late_prior.std()
    R['up'] = ((R.distance_m - R.prev_d) >= 200).astype(int); R['down'] = ((R.distance_m - R.prev_d) <= -200).astype(int)
    m = smf.ols('dyn_nat_inn ~ late_z * up + late_z * down', R).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(R.horse)[0]})
    OUT['qld_late_finish_x_step'] = {k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)] for k in ['late_z', 'late_z:up', 'late_z:down', 'up', 'down']}; OUT['qld_late_finish_x_step']['n'] = int(m.nobs)
except Exception as e: OUT['qld_late_finish_x_step'] = str(e)[:200]
json.dump(OUT, open('batch16/out_c15_distance.json', 'w'), indent=1); print(json.dumps(OUT, indent=0)[:4000])
