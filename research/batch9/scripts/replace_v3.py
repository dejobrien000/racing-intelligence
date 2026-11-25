"""Batch 9 study A: v3 rating as a REPLACEMENT for the current rating inside the operational models (same harness as
Batch 7's faster-rating test, engine/fast_rating.py). Settings chosen on pre-2025 runs only."""
import json, numpy as np, pandas as pd
from engine import lab, dyn_v3, evaltools as E
PRM = json.load(open('/tmp/exp/rt/tune_v3_choice.json')); PRM['n0'] = float(PRM['n0'])
U0 = pd.read_parquet('engine/frames/national.parquet')
base = U0[[c for c in U0.columns if not c.startswith(('dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'surprise', 'dyn_traj', 'j_', 't_surp', 't_n', 'jt_', 'h2h'))]].copy()
F = lab.add_rating(base.copy(), 'dyn_nat', runner=dyn_v3.run, **PRM); F = lab.add_derived(F); F = lab.add_people(F); F = lab.add_h2h(F)
F.to_parquet('/tmp/exp/rt/national_v3.parquet')
def compare(frame_fn, ALL, tag):
    xc = frame_fn(U0); xf = frame_fn(F); R = {}; out = []
    for k, x in {'current rating': xc, 'v3 rating (replacement)': xf}.items():
        x = E.zcols(x, ALL); dev = x.period == 'development'; ev = x.period == 'evaluation'
        R[k] = E.metrics(x, E.eta(x, ALL, E.fit(x, ALL, dev)), ev)
        y26 = R[k].date.dt.year == 2026
        R[k + ' 2026'] = R[k][y26]
    for k in ['current rating', 'v3 rating (replacement)']:
        d = E.diff(R['current rating'], R[k]) if k != 'current rating' else {}
        out.append({'model': k, **E.summary(R[k]), **{('vs_current_' + a): b for a, b in d.items() if a != 'races'}})
    d26 = E.diff(R['current rating 2026'], R['v3 rating (replacement) 2026']); out.append({'model': 'v3 vs current, 2026 only', **{('vs_current_' + a): b for a, b in d26.items()}})
    T = pd.DataFrame(out); T.to_csv(f'/tmp/exp/rt/v3_replace_{tag}.csv', index=False); print(tag); print(T.to_string(index=False), flush=True)
compare(E.qld_frame, list(E.QCOEF), 'qld')
compare(E.nat_frame, E.NV2, 'nat')
