"""Freeze the Batch 4 candidates (fitted on development races only) with code/data hashes, before any race from
25 Nov 2026 exists, so later scoring on those races is genuinely prospective. Never refit on prospective races."""
import json, hashlib, os, numpy as np, pandas as pd
src = open('inv23_dynamic_rating.py').read()
src = src.replace(src[src.index("best = None; grid = []"):src.index("print('chosen on development")], "best = (np.nan, 4.0, 0.1, 5.0)\n")
src = src.split("res = {k: score")[0]
exec(src)
out = {}
for name in ['combined_v1', 'combined_v1 + dynamic rating', 'dynamic rating + PA1 figure']:
    b = fit(x, specs[name]); out[name] = dict(zip(specs[name], map(float, b)))
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
os.makedirs('benchmarks/candidates_b4', exist_ok=True); os.makedirs('prospective', exist_ok=True)
man = {'frozen_utc': pd.Timestamp.utcnow().isoformat(), 'plan': 'batch04_plan.md', 'plan_sha256_16': h('batch04_plan.md'),
       'fit_window': 'development races only (before 2025-01-01), Queensland tracked',
       'dynamic_rating_params': {'s_kg': 4.0, 'q_kg2_per_day': 0.1, 'sig0_kg': 5.0, 'debut_offset_kg': 2.0},
       'coefficients_per_dev_sd': out, 'course_models': 'benchmarks/course_v1/manifest.json (partial pooling chose ~no course deviation)',
       'code_sha256_16': {p: h(p) for p in ['dyn_rating.py', 'inv23_dynamic_rating.py', 'features.py', 'clogit_tools.py', 'hier_tools.py', 'inv22_course_barriers.py', 'rating_v0.py']},
       'data_sha256_16': {p: h(p) for p in ['runs.parquet', 'features.parquet', 'pace_figures.parquet']},
       'prospective_rule': 'score only races dated 2026-11-25 or later; features built from runs before each race; no refit; report against combined_v1'}
json.dump(man, open('benchmarks/candidates_b4/manifest.json', 'w'), indent=1)
open('prospective/README.md', 'w').write("""# Prospective evaluation (protected)
Frozen candidates: benchmarks/candidates_b4/manifest.json (frozen %s UTC) and benchmarks/course_v1/manifest.json.
Rule: only races dated 25 Nov 2026 or later count. Models are never refitted on these races. Each scoring run writes
prospective/scores_YYYYMMDD.csv with a UTC timestamp and the manifest hash it used.
Limitation today: we collect results, not acceptances, so scores are computed after the race from features built only
from earlier runs (point-in-time by construction). Saving true pre-race predictions needs a Qld acceptances collector
(next-sequence item), which also guards against late data revisions.
""" % man['frozen_utc'])
print(json.dumps({k: (v if k != 'coefficients_per_dev_sd' else {m: len(c) for m, c in v.items()}) for k, v in man.items()}, indent=1)[:1500])
