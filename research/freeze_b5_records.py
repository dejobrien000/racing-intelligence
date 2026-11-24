"""Freeze the Batch 5 horse-record candidate before any race from 25 Nov 2026: offset = frozen combined_v1 + national
rating; added terms c_rec (course configuration), g_rec (going band), d_rec (distance band), shrinkage k = 1, fitted
jointly on Qld development races. Writes benchmarks/candidates_b5/manifest.json."""
import json, os, hashlib, numpy as np, pandas as pd
src = open('inv30_horse_suitability.py').read()
src = src.split("best = None")[0]
exec(src)
K = 1; add_records(K); x = qld_frame(); dv = x[x.period == 'development']; T = ['c_rec', 'g_rec', 'd_rec']
b = H.fit(H.Races(dv.race_id.values, dv.win.values, dv.offset.values, dv[[t + '_z' for t in T]].values), np.full(3, 1e-6))
sdv = {t: float(prep(eligible(X0.merge(U[U.state == 'QLD'][['q_race_id', 'q_horse_id', t]].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id']), on=['race_id', 'horse_id'], how='left')), [t]).pipe(lambda z: z[z.period == 'development'][t].std())) for t in T}
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
os.makedirs('benchmarks/candidates_b5', exist_ok=True)
json.dump({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'plan': 'batch05_plan.md', 'plan_sha256_16': h('batch05_plan.md'), 'base': 'benchmarks/candidates_b4_national/manifest.json (offset)',
           'records': {'definition': 'sum of earlier innovations of the national rating with the same key / (n + k)', 'k': K, 'keys': {'c_rec': 'course configuration', 'g_rec': 'going band', 'd_rec': 'distance band'}},
           'added_coefficients_per_dev_sd': dict(zip(T, map(float, b))), 'raw_dev_sd_after_race_centring': sdv,
           'code_sha256_16': {p: h(p) for p in ['inv30_horse_suitability.py', 'dyn_rating.py', 'dyn_rating_innov.py', 'hier_tools.py', 'freeze_b5_records.py']},
           'prospective_rule': 'only races dated 2026-11-25 or later count; no refit'}, open('benchmarks/candidates_b5/manifest.json', 'w'), indent=1)
print(dict(zip(T, np.round(b, 3))), sdv)
