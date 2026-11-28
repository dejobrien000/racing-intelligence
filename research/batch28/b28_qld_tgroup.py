"""Batch 28 item 2: which parts of Queensland's track/distance/going group hurt? Leave-one-component-out (and pairs that belong together)
inside the Queensland production structure (v3 frame), everything refitted inside each window (A: fit <2024, judge 2024; B: fit <2025,
judge 2025-26). Paired per-race log-likelihood vs the full structure, race bootstrap. Output batch28/out_b28_qld_tgroup.json"""
import json, numpy as np, pandas as pd, os, sys
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", "pd.read_parquet('engine/frames/national_v3.parquet')"); exec(src)
rng = np.random.default_rng(281)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); TAU = Q3.get('penalty_tau', 100)
COLS = list(E.QCOEF); x = E.qld_frame(U); x = E.zcols(x, COLS); x = build_terms(x, NEW)
WIN = {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}
def lp(cols):
    o = {}
    for w, (fe, lo, hi) in WIN.items():
        fm = (x.meeting_date < fe) & x.period.notna(); em = (x.meeting_date >= lo) & (x.meeting_date < hi)
        b1 = E.fit(x, cols, fm, 1e-6); off = E.eta(x, cols, b1); e = off + x[['t::' + t for t in NEW]].values @ fitd(x, NEW, fm, off, TAU)
        o[w] = E.metrics(x, e, em).lp
    return o
base = lp(COLS)
GROUPS = {'track starts + wins': ['t_trk_starts', 't_trk_win'], 'track-distance starts + wins': ['t_td_starts', 't_td_win'], 'distance-band starts + wins': ['t_db_starts', 't_db_win'],
          'going': ['t_going', 'missgoing'], 'distance change': ['t_dchange', 't_dchange_abs']}
for c in sum(GROUPS.values(), []): GROUPS[c] = [c]
out = {}
for lab, drop in GROUPS.items():
    r = lp([c for c in COLS if c not in drop]); o = {}
    for w in WIN:
        d = (r[w] - base[w]).dropna().values; bs = d[rng.integers(0, len(d), (800, len(d)))].mean(1)
        o[w] = {'races': int(len(d)), 'gain_when_removed': round(float(d.mean()), 5), 'ci95': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]}
    out[lab] = o; print(f"{lab:32s} A {o['A']['gain_when_removed']:+.5f} {o['A']['ci95']}  B {o['B']['gain_when_removed']:+.5f} {o['B']['ci95']}", flush=True)
json.dump(out, open('batch28/out_b28_qld_tgroup.json', 'w'), indent=1)
