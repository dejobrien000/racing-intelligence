"""Frame for the rating-update prototype V5 (Batch 15): Engine v2.3 national runs, rating with margins capped at 12 lengths and
good surprises moving the rating 1.3x as far. Everything else identical to the C2 frame build (engine/lab.py)."""
import os, numpy as np
import dyn_rating as DR
_orig = DR.prepare
def prep12(df):
    d = _orig(df); ok = d.perf.notna()
    d.loc[ok, 'perf'] = -d.loc[ok, 'margin_l'].clip(upper=float(os.environ.get('CAP', '12'))) * d.loc[ok, 'kgpl'] + float(os.environ['WCREDIT']) * (d.loc[ok, 'weight_kg'] - 57)
    return d
DR.prepare = prep12
def run_v5(d, s, q, sig0, d0):
    mu, var, last = {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); innov = np.full(len(d), np.nan)
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
            K = vv_ / pv; u = np.where(inn > 0, float(os.environ.get('GOOD', '1.3')) * inn, inn); m[ok] = mm_ + K * u; v[ok] = (1 - K) * vv_
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    return pre_mu, pre_sd, innov
import engine.lab as L
L.DI.run = run_v5
U = L.build(os.environ['LAB_OUT']); print(len(U), 'rows; U5 frame written')
