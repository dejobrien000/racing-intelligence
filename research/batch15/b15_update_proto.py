"""Batch 15 (brief s2/s7): does the rating's UPDATE rule (how far one run moves a rating) need changing? Prototype only, research.
The production rule (dyn_rating_innov.run, Engine v2.3 settings: weight credit 0.25, s 4.5, q 0.05, sig0 5.0, d0 2.0) moves a horse's
rating towards each run by a fixed share K = var/(var + s^2) of the surprise, the same for good and bad runs of every size.
Variants change only the update (the same runs, the same order, every run still predicted before it is used):
  V1 margins capped at 12 lengths (instead of 25) when turning a defeat into a performance
  V2 surprise capped at +-1.5 predictive sd when updating (robust; one wild run moves the rating less)
  V3 asymmetric: good surprises move the rating 1.3x as far; bad surprises capped at -1.5 sd
  V4 asymmetric only: good surprises 1.3x
  V5 = V1 + V4: margins capped at 12 lengths and good surprises 1.3x
  V6 = V1 + good surprises 1.2x
Judged on runs in 2024 and 2025-26 (each run predicted from earlier runs only):
  accuracy  = Gaussian predictive log-likelihood of each run's performance relative to the field (higher is better), and its
              mean squared error; per run, differences with bootstrap 95% by horse
  calibration = next-run surprise after each size of surprise (0 everywhere = the update is right); spread across bands
  stability = average absolute rating change per run, and the share of runs moving the rating by more than 3 kg
Nothing here changes production. A variant would still need a full engine refit and test before it could be a candidate."""
import os, numpy as np, pandas as pd, json, sys
os.environ['WCREDIT'] = '0.25'
import dyn_rating as DR
P = {'s': 4.5, 'q': 0.05, 'sig0': 5.0, 'd0': 2.0}
def runner(d, mode):
    s, q, sig0, d0 = P['s'], P['q'], P['sig0'], P['d0']
    mu, var, last = {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); innov = np.full(len(d), np.nan); post = np.full(len(d), np.nan)
    horses = d.horse.values; dates = d.date.values.astype('datetime64[D]').astype(np.int64); perf = d.perf.values
    keys = d.race_key.values; starts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1]) + 1, len(d)]
    for a, b in zip(starts[:-1], starts[1:]):
        hs = horses[a:b]; t = dates[a]
        known = [mu[h] for h in hs if h in mu]; base = (np.mean(known) if known else 0.0) - d0
        m = np.array([mu.get(h, base) for h in hs])
        v = np.array([min(var[h] + q * (t - last[h]), sig0 ** 2) if h in var else sig0 ** 2 for h in hs])
        pre_mu[a:b] = m; pre_sd[a:b] = np.sqrt(v)
        ok = ~np.isnan(perf[a:b])
        if ok.sum() >= 2:
            pm, mm_, vv_ = perf[a:b][ok], m[ok], v[ok]
            inn = (pm - pm.mean()) - (mm_ - mm_.mean()); pv = vv_ + s * s
            idx = np.arange(a, b)[ok]; innov[idx] = inn
            K = vv_ / pv; u = inn.copy(); sd = np.sqrt(pv)
            if mode in ('V2',): u = np.clip(u, -1.5 * sd, 1.5 * sd)
            if mode in ('V3',): u = np.where(u > 0, 1.3 * u, np.maximum(u, -1.5 * sd))
            if mode in ('V4', 'V5'): u = np.where(u > 0, 1.3 * u, u)
            if mode in ('V6',): u = np.where(u > 0, 1.2 * u, u)
            m[ok] = mm_ + np.minimum(K * (1.3 if False else 1.0), 1.0) * u; v[ok] = (1 - K) * vv_
            post[idx] = m[ok]
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    return pre_mu, pre_sd, innov
U = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'state'])
U['date'] = pd.to_datetime(U.date)
def prep(cap):
    dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                       'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
    d = DR.prepare(dn)
    if cap != 25:
        ok = d.perf.notna(); d.loc[ok, 'perf'] = -d.loc[ok, 'margin_l'].clip(upper=cap) * d.loc[ok, 'kgpl'] + 0.25 * (d.loc[ok, 'weight_kg'] - 57)
    return d.sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
R = {}
MODES = sys.argv[1].split(',') if len(sys.argv) > 1 else ['V0', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6']
for mode in MODES:
    d = prep(12 if mode in ('V1', 'V5', 'V6') else 25)
    mu, sd, inn = runner(d, 'V0' if mode == 'V1' else mode)
    o = pd.DataFrame({'idx': d.idx.values, 'R': mu, 'sd': sd, 'inn': inn}).set_index('idx').sort_index()
    R[mode] = o; print(mode, 'done', flush=True)
base = U[['race', 'horse', 'date', 'state', 'finish_pos', 'margin_l']].copy()
OUT = {}
for mode, o in R.items():
    x = base.join(o); x = x.sort_values(['horse', 'date']).copy(); g = x.groupby('horse')
    x['inn1'] = g.inn.shift(-1); x['dR'] = g.R.shift(-1) - x.R
    pv = x.sd ** 2 + P['s'] ** 2; x['ll'] = -0.5 * (np.log(2 * np.pi * pv) + x.inn ** 2 / pv); x['se'] = x.inn ** 2
    if mode == 'V1':   # V1 changes the target itself (capped margins): judge it on the production target (25-length cap) for a fair comparison
        x['inn_prod'] = R['V0'].inn.reindex(x.index)    # placeholder; replaced below
    R[mode] = x
# fair accuracy comparison for V1: predict the production performance target from V1's pre-race ratings
v0 = R['V0'];
for mode, x in R.items():
    r = {}
    for per, msk in [('2024', (x.date >= '2024-01-01') & (x.date < '2025-01-01')), ('2025-26', x.date >= '2025-01-01')]:
        y = x[msk & x.inn.notna()]
        if mode in ('V1', 'V5', 'V6'):
            # production target: race-relative performance with the 25-length cap, against V1's race-relative pre-race ratings
            y0 = v0.loc[y.index]; perf_rel = y0.inn + (y0.R - y0.R.groupby(y0.race).transform('mean'))         # perf - field mean perf (production target)
            pred_rel = y.R - y.R.groupby(y.race).transform('mean'); e = perf_rel - pred_rel; pv = y.sd ** 2 + P['s'] ** 2
            ll = -0.5 * (np.log(2 * np.pi * pv) + e ** 2 / pv); se = e ** 2
        else: ll, se = y.ll, y.se
        dd = pd.DataFrame({'horse': y.horse, 'll': ll, 'se': se}); dd0 = v0.loc[y.index]; dd['ll0'] = dd0.ll; dd['se0'] = dd0.se
        dif = (dd.ll - dd.ll0); hs = dd.horse.values; uh, inv = np.unique(hs, return_inverse=True)
        sums = np.bincount(inv, dif.values); cnts = np.bincount(inv); rng = np.random.default_rng(3); bs = []
        for _ in range(300):
            s_ = rng.integers(0, len(uh), len(uh)); bs.append(sums[s_].sum() / cnts[s_].sum())
        cal = y.groupby(pd.cut(y.inn, [-99, -10, -6, -3, 3, 6, 10, 99]), observed=True).inn1.mean()
        r[per] = {'runs': int(len(y)), 'loglik per run': round(float(ll.mean()), 5), 'vs production': round(float(dif.mean()), 5), 'vs production 95%': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)],
                  'mean squared surprise': round(float(se.mean()), 3), 'next-run surprise by size of this surprise': {str(k): round(v_, 2) for k, v_ in cal.items()},
                  'calibration spread (max-min)': round(float(cal.max() - cal.min()), 2), 'mean |rating change| per run': round(float(y.dR.abs().mean()), 3),
                  'share of runs moving rating > 3 kg %': round(100 * float((y.dR.abs() > 3).mean()), 2)}
    OUT[mode] = r; print(mode, json.dumps(r), flush=True)
import os.path
old = json.load(open('batch15/out_update_proto.json')) if os.path.exists('batch15/out_update_proto.json') else {}
old.update(OUT); json.dump(old, open('batch15/out_update_proto.json', 'w'), indent=1)
