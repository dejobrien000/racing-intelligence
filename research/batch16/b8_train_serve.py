"""Batch 16 B8: training vs serving integrity check for the national engine (Engine v2.3 inputs). Ordinary check, not a monitor.
For every raw input the v1, v2 and third layers use, compare how it looks in the data the engine was fitted on (2025-26 rows of the
Engine v2.3 frame) with how it looks when served on race morning (27 Nov 2026, the six-state meetings, rebuilt exactly as the scorer
builds them). Flags: missing far more (or less) often when served; values outside the fitted range; served constant; race-centred value
always zero (contributes nothing - distinguishing 'no information' from 'everyone the same').
Usage (from research/): ENGINE_C2=1 PYTHONPATH=. python3 batch16/b8_train_serve.py 20261127 -> batch16/out_b8_train_serve.json"""
import sys, json, numpy as np, pandas as pd
from engine import score_v2 as S, v22
D = sys.argv[1]
IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[(IX.date.astype(str) == D) & IX.file.str.endswith('_runners.csv') & ~IX.file.str.contains('/v2_')]
IX = IX.sort_values('scored_utc').groupby('track').tail(1)
TT = []
for _, ix in IX.iterrows():
    T, fam, _, _ = S.meeting_table(ix)
    if fam == 'QLD': continue
    H_ = S.history(D, fam); T = S.new_raw(T, H_, fam); T = v22.raw(T, H_); TT.append(T)
T = pd.concat(TT, ignore_index=True)
F = pd.read_parquet('engine/frames/national_c2.parquet'); F = F[(F.date >= '2025-01-01')]
import os
FT = '/tmp/cand/f_C2/b10/out/feat.parquet'   # the third layer's research features on the v2.3 frame (fitted inputs)
G = pd.read_parquet(FT) if os.path.exists(FT) else None
if G is not None: G = G[pd.to_datetime(G.date) >= '2025-01-01']
B22 = ['n_prior', 'h_sd', 'recent_var_ratio', 'gap_long_z', 'short_vs_long', 'below_top3', 'slope15', 'neg_run', 'quick_today', 'early_prep_vs_usual', 'venue_step']
V1 = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'r_ldays', 'dyn_nat', 'c_rec', 'g_rec', 'd_rec']
V2 = ['j_surp', 'j_n', 't_surp', 't_n', 'jt_surp', 'j_change', 'age_n', 'female', 'h2h', 'surprise_last', 'dyn_traj', 'dist_change', 'wt_change', 'bm_change']
rows = []
def stats(v, race):
    v = pd.to_numeric(v, errors='coerce'); c = v - v.groupby(race).transform('mean')
    return {'n': int(len(v)), 'missing_pct': round(100 * float(v.isna().mean()), 1), 'mean': None if v.notna().sum() == 0 else round(float(v.mean()), 3),
            'sd': None if v.notna().sum() < 2 else round(float(v.std()), 3), 'p1': None if v.notna().sum() == 0 else round(float(v.quantile(.01)), 3),
            'p99': None if v.notna().sum() == 0 else round(float(v.quantile(.99)), 3), 'race_centred_zero_pct': round(100 * float((c.fillna(0).abs() < 1e-9).mean()), 1)}
for layer, cols in [('v1', V1), ('v2', V2), ('third', B22)]:
    for c in cols:
        tc = c if c in F else None; sc = ('b22_' + c) if layer == 'third' else c
        tr = stats(F[tc], F.race_id) if tc else None
        if layer == 'third' and G is not None and c in G: tr = stats(G[c], G.race_id)
        if layer == 'third' and tr is None and 'b22_' + c not in F: tr = None
        sv = stats(T[sc], T.race_id) if sc in T else None
        flag = []
        if sv is None: flag.append('not built when served')
        elif tr is None: flag.append('not in the fitted frame under this name (built by the third-layer research code; checked by the Batch 10 parity test)')
        else:
            if sv['missing_pct'] - tr['missing_pct'] > 20: flag.append(f"missing far more often when served ({sv['missing_pct']}% vs {tr['missing_pct']}%)")
            if tr['missing_pct'] - sv['missing_pct'] > 20: flag.append(f"missing far less often when served ({sv['missing_pct']}% vs {tr['missing_pct']}%)")
            if sv['missing_pct'] == 100: flag.append('never served (always missing)')
            elif sv['sd'] == 0: flag.append('constant when served')
            if sv['mean'] is not None and tr['sd'] and abs(sv['mean'] - tr['mean']) > 0.5 * tr['sd']: flag.append(f"served mean differs by {round((sv['mean'] - tr['mean']) / tr['sd'], 2)} sd")
        rows.append({'layer': layer, 'input': c, 'fitted_2025_26': tr, 'served_' + D: sv, 'flags': flag})
out = {'date': D, 'served_runners': int(len(T)), 'fitted_rows': int(len(F)), 'inputs': rows,
       'flagged': [f"{r['layer']}:{r['input']}: {'; '.join(r['flags'])}" for r in rows if r['flags']]}
json.dump(out, open('batch16/out_b8_train_serve.json', 'w'), indent=1); print('\n'.join(out['flagged']) or 'no flags')
