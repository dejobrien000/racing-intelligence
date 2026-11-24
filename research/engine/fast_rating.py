"""Batch 7, Study B: one controlled faster-learning rating candidate (engine/dyn_fast.py).
Step 1 - tune its single setting (lam, and whether it applies to declines too) on DEVELOPMENT races only, by the
rating's own predictive fit (Gaussian log-likelihood of each run's surprise, the same objective the rating was built on).
Step 2 - on identical 2025-26 races, compare inside the operational models:
  M0 operational (current rating)      M1 current rating swapped for the faster one (records rebuilt from it too)
  M2 M0 + surprise & trajectory terms  M3 M1 + surprise & trajectory terms (from the faster rating)
so we learn whether the Batch 6 signal is best captured by a revised rating, new features, or both.
Outputs engine/out/fast_*.csv and engine/frames/national_fast.parquet"""
import json, numpy as np, pandas as pd
from engine import lab, dyn_fast, evaltools as E
P = lab.PN_FROZEN; s = P['s_kg']
U0 = pd.read_parquet('engine/frames/national.parquet')
base = U0[[c for c in U0.columns if not c.startswith(('dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'surprise', 'dyn_traj', 'j_', 't_surp', 't_n', 'jt_', 'h2h'))]].copy()
dev_rows = (base.date < '2025-01-01').values
rows = []
for mode in ['both', 'up']:
    for lam in [0, 0.25, 0.5, 1, 2, 4]:
        if mode == 'up' and lam == 0: continue
        V = lab.add_rating(base.copy(), 'r', runner=dyn_fast.run, lam=lam, mode=mode)
        ok = dev_rows & V.r_inn.notna().values; pv = V.r_sd.values[ok] ** 2 + s * s; inn = V.r_inn.values[ok]
        ll = float(np.mean(-0.5 * (np.log(2 * np.pi * pv) + inn ** 2 / pv)))
        okv = (~dev_rows) & V.r_inn.notna().values; pvv = V.r_sd.values[okv] ** 2 + s * s; innv = V.r_inn.values[okv]
        llv = float(np.mean(-0.5 * (np.log(2 * np.pi * pvv) + innv ** 2 / pvv)))
        rows.append({'mode': mode, 'lam': lam, 'dev_loglik_per_run': round(ll, 5), 'eval_loglik_per_run (not used to choose)': round(llv, 5)}); print(rows[-1])
T = pd.DataFrame(rows); T.to_csv('engine/out/fast_tuning.csv', index=False)
best = T.sort_values('dev_loglik_per_run', ascending=False).iloc[0]; LAM, MODE = float(best.lam), best['mode']
print('chosen on development races:', MODE, LAM)
json.dump({'lam': LAM, 'mode': MODE, 'chosen_on': 'development races (before 2025-01-01), rating predictive log-likelihood'}, open('engine/out/fast_choice.json', 'w'))
# ---- build the frame with the faster rating and everything derived from it ----
F = lab.add_rating(base.copy(), 'dyn_nat', runner=dyn_fast.run, lam=LAM, mode=MODE); F = lab.add_derived(F); F = lab.add_people(F); F = lab.add_h2h(F)
F.to_parquet('engine/frames/national_fast.parquet')
def compare(frame_fn, ALL, extra, tag):
    xc = frame_fn(U0); xf = frame_fn(F); out = []
    feats = {'M0 operational': (xc, ALL), 'M1 faster rating': (xf, ALL), 'M2 operational + surprise/trajectory': (xc, ALL + extra), 'M3 faster rating + surprise/trajectory': (xf, ALL + extra)}
    R = {}
    for k, (x, cols) in feats.items():
        x = E.zcols(x, cols); dev = x.period == 'development'; ev = x.period == 'evaluation'
        R[k] = E.metrics(x, E.eta(x, cols, E.fit(x, cols, dev)), ev)
    for k in R:
        d = E.diff(R['M0 operational'], R[k]) if k != 'M0 operational' else {}
        out.append({'model': k, **E.summary(R[k]), **{('vs_M0_' + a): b for a, b in d.items() if a != 'races'}})
    T = pd.DataFrame(out); T.to_csv(f'engine/out/fast_compare_{tag}.csv', index=False); print(tag); print(T.to_string(index=False))
EXTRA = ['surprise_last', 'dyn_traj']
compare(E.qld_frame, list(E.QCOEF), EXTRA, 'qld')
compare(E.nat_frame, E.NV2, EXTRA, 'nat')
