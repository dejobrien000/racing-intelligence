"""Same algorithm as the frozen dyn_rating.run (unchanged file), additionally returning each measured run's
innovation: (performance relative to the field) - (pre-race rating relative to the field), in kg. Positive = ran better
than the ratings expected. Equality with the frozen module is checked by inv30 before use."""
import numpy as np
def run(d, s, q, sig0, d0):
    mu, var, last = {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); innov = np.full(len(d), np.nan)
    horses = d.horse.values; dates = d.date.values.astype('datetime64[D]').astype(np.int64); perf = d.perf.values
    import os; GOOD = float(os.environ.get('RATING_GOOD_X', '1')); perf_u = d['perf_upd'].values if 'perf_upd' in d else perf
    HOOK = ('perf_upd' in d) or GOOD != 1.0          # off in production: the original update line runs unchanged
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
            K = vv_ / pv
            if HOOK:                      # CANDIDATE ONLY (Batch 16 B9): update from the capped performance, good surprises x GOOD
                pu = perf_u[a:b][ok]; iu = (pu - pu.mean()) - (mm_ - mm_.mean()); iu = np.where(iu > 0, GOOD * iu, iu); m[ok] = mm_ + K * iu
            else: m[ok] = mm_ + K * inn
            v[ok] = (1 - K) * vv_
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    return pre_mu, pre_sd, innov
