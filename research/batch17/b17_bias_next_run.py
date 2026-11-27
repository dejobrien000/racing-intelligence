"""Batch 17 C14 follow-up: should a run be read differently when the day's track favoured another part of the track? For each Qld tracked
run, the meeting's lane effect from the OTHER races at that meeting (leave-one-race-out; known once the meeting is over, before the horse's
next assessment) times the horse's own straight lane relative to its race = the help or harm it got from the day's bias (kg). Same for
early position (on-pace vs off-pace; partly pace, not surface). Test: does the next run's surprise move opposite to it (the rating took the
bias as ability)? Research only; no prices. Usage: python3 batch17/b17_bias_next_run.py -> batch17/out_b17_bias_next_run.json"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
src = open('batch17/b17_track_bias.py').read(); src = src[:src.index("OUT = {'coverage'")]; exec(src)
X = X.sort_values(['meeting', 'race_no'])
for c in ['lane_w', 'early_rel_w']:
    X[c[:-2] + '_xy'] = (X[c] * X.y_w).fillna(0); X[c[:-2] + '_xx'] = (X[c] ** 2).fillna(0)
    m = X.groupby('meeting')[[c[:-2] + '_xy', c[:-2] + '_xx']].transform('sum'); r = X.groupby('race_id')[[c[:-2] + '_xy', c[:-2] + '_xx']].transform('sum')
    X[c[:-2] + '_day_slope'] = (m.iloc[:, 0] - r.iloc[:, 0]) / (m.iloc[:, 1] - r.iloc[:, 1]).replace(0, np.nan)
    X[c[:-2] + '_bias_kg'] = X[c[:-2] + '_day_slope'] * X[c]
F2 = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'q_race_id', 'q_horse_id', 'dyn_nat_inn']).sort_values(['horse', 'date', 'race'])
F2['nxt'] = F2.groupby('horse').dyn_nat_inn.shift(-1); F2 = F2.dropna(subset=['q_race_id']); F2['q_horse_id'] = F2.q_horse_id.astype(str)
X = X.merge(F2[['q_race_id', 'q_horse_id', 'nxt', 'horse']], on=['q_race_id', 'q_horse_id'], how='left')
OUT = {}
for c in ['lane', 'early_rel']:
    d = X.dropna(subset=['nxt', c + '_bias_kg']); d = d[np.isfinite(d[c + '_bias_kg'])]
    d['b'] = d[c + '_bias_kg'].clip(d[c + '_bias_kg'].quantile(0.01), d[c + '_bias_kg'].quantile(0.99))
    mm = smf.ols('nxt ~ b + dyn_nat_inn', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    q = pd.qcut(d.b, 5, labels=['most harmed', 'q2', 'q3', 'q4', 'most helped']).astype(str)
    OUT[c] = {'runs': int(mm.nobs), 'next_surprise_per_kg_of_day_bias': [round(float(mm.params['b']), 3), round(float(mm.conf_int().loc['b', 0]), 3), round(float(mm.conf_int().loc['b', 1]), 3)],
              'this_run_surprise_per_kg_of_day_bias': round(float(smf.ols('dyn_nat_inn ~ b', d).fit().params['b']), 3),
              'next_surprise_by_quintile': {k: round(float(v), 2) for k, v in d.groupby(q).nxt.mean().items()}, 'bias_kg_sd': round(float(d.b.std()), 2)}
json.dump(OUT, open('batch17/out_b17_bias_next_run.json', 'w'), indent=1); print(json.dumps(OUT, indent=0))
