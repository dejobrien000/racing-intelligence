"""Batch 14: does the 'uneven last 600' finding add anything to the Queensland PRODUCTION engine (Engine v2.1.3, from 27 Nov)?
Offset = production v2.1.3 exactly as it runs (frozen v1 + v2.1.3 dev-fit terms). Added inputs, all pre-race:
  dip_last  = unevenness (mean of the last three 200 m sections minus the weakest, vs the field) at the horse's most recent tracked run
  dip_prior = the horse's shrunk mean unevenness over all earlier tracked runs (3 runs' weight towards the field average)
  (+ a missing flag when the horse has no earlier tracked run)
Windows: A = add-on fitted before 2024, judged on 2024 (clean); B = fitted before 2025, judged on 2025-26 (re-used period).
Identical races; per-race log-likelihood gain with a meeting bootstrap. Research only: nothing here changes production."""
import json, numpy as np, pandas as pd, os, sys
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", "pd.read_parquet('engine/frames/national_v3.parquet')"); exec(src)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))
Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); COLS = list(E.QCOEF)
x = E.qld_frame(U); x = E.zcols(x, COLS); PV = C21['coefficients_per_dev_sd']
off = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS]); x = build_terms(x, NEW)
e0 = off + x[['t::' + t for t in NEW]].fillna(0.0).values @ np.array([Q3['coef_per_term_sd_dev_fit'][t] for t in NEW])
# features from the tracked-run table
T = pd.read_parquet('/home/claude/b14/runs_QLD.parquet').rename(columns={'field_x': 'field'})
T = T[(T.def400 < 10) & T[['v600', 'v400', 'v200']].notna().all(axis=1)].copy()
for v in ['v600', 'v400', 'v200']: T[v + 'r'] = T[v] - T.groupby('race_id')[v].transform('median')
T['dip'] = T[['v600r', 'v400r', 'v200r']].mean(axis=1) - T[['v600r', 'v400r', 'v200r']].min(axis=1)
T = T.sort_values(['horse', 'meeting_date']); cnt = T.groupby('horse').cumcount() + 1; T['dip_prior_after'] = T.groupby('horse').dip.cumsum() / (cnt + 3.0)
T = T[['horse', 'meeting_date', 'dip', 'dip_prior_after']].rename(columns={'meeting_date': 'tdate', 'dip': 'dip_last', 'dip_prior_after': 'dip_prior'})
x['_d'] = pd.to_datetime(x.meeting_date); x['_i'] = np.arange(len(x))
xs = x[['_i', 'horse', '_d']].sort_values('_d'); Ts = T.sort_values('tdate')
mm = pd.merge_asof(xs, Ts, left_on='_d', right_on='tdate', by='horse', allow_exact_matches=False).sort_values('_i')
x['dip_last'] = mm.dip_last.values; x['dip_prior'] = mm.dip_prior.values; x['dip_miss'] = x.dip_last.isna().astype(float)
x[['dip_last', 'dip_prior']] = x[['dip_last', 'dip_prior']].fillna(0.0)
ADD = ['dip_last', 'dip_prior', 'dip_miss']; x = E.zcols(x, ADD)
out = {'coverage: Qld rows with an earlier tracked run %': round(100 * (1 - x.dip_miss.mean()), 1)}
for W, (fe, lo, hi) in {'A (judge 2024, clean)': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B (judge 2025-26, re-used)': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = (x._d < fe) & x.period.notna(); em = (x._d >= lo) & (x._d < hi)
    b = E.fit(x, ADD, fm, 1e-6, offset=e0); e1 = e0 + x[[c + '_z' for c in ADD]].values @ b
    m0, m1 = E.metrics(x, e0, em), E.metrics(x, e1, em); dd = E.diff(m0, m1)
    out[W] = {'coef_per_sd': dict(zip(ADD, [round(float(v), 4) for v in b])), **{k: dd[k] for k in ['races', 'lp', 'lp_lo', 'lp_hi', 'hit', 'hit_lo', 'hit_hi', 'top3']}}
    print(W, out[W], flush=True)
json.dump(out, open('batch14/out_qld_engine_dip.json', 'w'), indent=1)
