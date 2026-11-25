"""Release CANDIDATE (not live): Engine v2.1.2-candidate for Queensland = v2.1.1 without last-start finish and the 10 track/distance/going
history inputs. Same fitting rule as v2.1.1 (v1 inputs on development races before 2025; v2 terms penalty 100, dev-fit and all-races).
Removed inputs get coefficient 0 so the existing scorers can run it unchanged. Writes to benchmarks/candidate_qld_v2_1_2/ only."""
import json, copy, os, numpy as np, pandas as pd, hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; ALL = list(E.QCOEF); DROP = ['f_lastfp'] + E.QFAM['Track/distance/going history']
C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json')); M21 = json.load(open('benchmarks/engine_v2_1/manifest.json'))
x = E.qld_frame(pd.read_parquet('engine/frames/national_v3.parquet')); x = E.zcols(x, ALL); dev = (x.period == 'development')
cols = [c for c in ALL if c not in DROP]; b1 = E.fit(x, cols, dev); off = E.eta(x, cols, b1); x = build_terms(x, QT)
b2 = fitd(x, QT, dev, off, 100); b2all = fitd(x, QT, pd.Series(True, index=x.index), off, 100)
v1c = {c: 0.0 for c in ALL}; v1c.update({c: float(b) for c, b in zip(cols, b1)})
c3 = copy.deepcopy(C21); c3.update({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'engine_release': 'Engine v2.1.2-candidate (NOT LIVE)', 'coefficients_per_dev_sd': v1c,
     'removed_inputs': DROP, 'coefficients_fit_on': 'development races (before 2025-01-01), v3 rating frame, database master-2026-11-23-sa-wa-tas-qld'})
M = copy.deepcopy(M21); Q = M['families']['QLD']; Q.update({'coef_per_term_sd_dev_fit': {t: float(b) for t, b in zip(QT, b2)}, 'coef_per_term_sd_all_races': {t: float(b) for t, b in zip(QT, b2all)}})
M['version'] = 'Engine v2.1.2-candidate (Queensland, NOT LIVE): v2.1.1 without last-start finish and track/distance/going history'
os.makedirs('benchmarks/candidate_qld_v2_1_2', exist_ok=True)
json.dump(c3, open('benchmarks/candidate_qld_v2_1_2/candidates_manifest.json', 'w'), indent=1); json.dump(M, open('benchmarks/candidate_qld_v2_1_2/engine_manifest.json', 'w'), indent=1)
print('v1 coefs', {k: round(v, 3) for k, v in v1c.items() if v}); print('v2 dev', {k: round(v, 3) for k, v in Q['coef_per_term_sd_dev_fit'].items()})
