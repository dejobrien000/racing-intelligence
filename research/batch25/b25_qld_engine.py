"""Batch 25 Part B, engine check: do the meeting-specific physical benchmarks add anything to the Queensland PRODUCTION engine
(Engine v2.1.3) - i.e. information the opposition-aware rating and the existing Qld physical inputs do not already carry?
Offset = production v2.1.3 exactly as it runs (same construction as batch14/b14_qld_engine.py). Added pre-race inputs per measure
(from batch25/b25_physical.py, measured tracking only; never a rating): <m>_last = value at the horse's most recent tracked run;
<m>_prior = shrunk mean over all its earlier tracked runs (3 runs' weight to 0); one shared missing flag.
Measures: M3 (600-200 m speed vs the day's other races, tempo/position adjusted), M1 (last-400 m benchmark), M6t (the part of the
race shape due to the race's tempo), and all three together. Windows: A = fitted before 2024, judged on 2024 (clean); B = fitted
before 2025, judged on 2025-26 (re-used). Per-race log-likelihood gain with a meeting bootstrap. Research only."""
import json, numpy as np, pandas as pd, os, sys
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", "pd.read_parquet('engine/frames/national_v3.parquet')"); exec(src)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))
Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); COLS = list(E.QCOEF)
x = E.qld_frame(U); x = E.zcols(x, COLS); PV = C21['coefficients_per_dev_sd']
off = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS]); x = build_terms(x, NEW)
e0 = off + x[['t::' + t for t in NEW]].fillna(0.0).values @ np.array([Q3['coef_per_term_sd_dev_fit'][t] for t in NEW])
T = pd.read_parquet('/home/claude/b14/b25_phys_QLD.parquet', columns=['horse', 'meeting_date', 'race_id', 'M1', 'M3', 'M6_tempo_part'])
T = T.rename(columns={'M6_tempo_part': 'M6t'}).sort_values(['horse', 'meeting_date', 'race_id'])
MS = ['M3', 'M1', 'M6t']
for m in MS:
    v = T[m].fillna(0.0); c = T[m].notna().astype(float)
    T[m + '_prior'] = v.groupby(T.horse).cumsum() / (c.groupby(T.horse).cumsum() + 3.0)
    T[m + '_last'] = T[m]
T = T.groupby(['horse', 'meeting_date']).last().reset_index()        # one row per horse-day (no Qld horse runs twice a day)
x['_d'] = pd.to_datetime(x.meeting_date); x['_i'] = np.arange(len(x))
xs = x[['_i', 'horse', '_d']].sort_values('_d'); Ts = T.rename(columns={'meeting_date': 'tdate'}).sort_values('tdate')
mm = pd.merge_asof(xs, Ts[['horse', 'tdate'] + [m + s for m in MS for s in ('_last', '_prior')]], left_on='_d', right_on='tdate', by='horse',
                   allow_exact_matches=False).sort_values('_i')
for m in MS:
    for s_ in ('_last', '_prior'): x[m + s_] = mm[m + s_].values
x['phys_miss'] = mm.tdate.isna().astype(float).values
for m in MS: x[[m + '_last', m + '_prior']] = x[[m + '_last', m + '_prior']].fillna(0.0)
SETS = {'M3 middle benchmark': ['M3_last', 'M3_prior', 'phys_miss'], 'M1 late-400 benchmark': ['M1_last', 'M1_prior', 'phys_miss'],
        'M6t tempo cost': ['M6t_last', 'M6t_prior', 'phys_miss'], 'all three': ['M3_last', 'M3_prior', 'M1_last', 'M1_prior', 'M6t_last', 'M6t_prior', 'phys_miss']}
allc = sorted({c for v in SETS.values() for c in v}); x = E.zcols(x, allc)
out = {'coverage_qld_rows_with_earlier_tracked_run_pct': round(100 * (1 - x.phys_miss.mean()), 1)}
for name, ADD in SETS.items():
    out[name] = {}
    for W, (fe, lo, hi) in {'A (judge 2024, clean)': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B (judge 2025-26, re-used)': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
        fm = (x._d < fe) & x.period.notna(); em = (x._d >= lo) & (x._d < hi)
        b = E.fit(x, ADD, fm, 1e-6, offset=e0); e1 = e0 + x[[c + '_z' for c in ADD]].values @ b
        m0, m1 = E.metrics(x, e0, em), E.metrics(x, e1, em); dd = E.diff(m0, m1)
        out[name][W] = {'coef_per_sd': dict(zip(ADD, [round(float(v), 4) for v in b])), **{k: dd[k] for k in ['races', 'lp', 'lp_lo', 'lp_hi', 'hit', 'hit_lo', 'hit_hi', 'top3']}}
        print(name, W, out[name][W], flush=True)
json.dump(out, open('batch25/out_b25_qld_engine.json', 'w'), indent=1)
