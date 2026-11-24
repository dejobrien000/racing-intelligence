"""Faster-learning candidate of the national dynamic rating (ONE controlled change; everything else identical to the
frozen dyn_rating / dyn_rating_innov).
Change: when a horse's surprise in this race has the SAME SIGN as its previous measured surprise (two runs in a row above,
or two below, what its rating expected) the rating's uncertainty is inflated by a factor (1 + lam) before the update, so
the rating moves further towards what the horse just showed. A single surprise is still treated as mostly noise; a
repeated one is treated as evidence of real change. lam = 0 reproduces the frozen rating exactly.
mode 'both' (improvement and decline) or 'up' (improvement only). Point-in-time: uses only this and earlier races."""
import numpy as np
def run(d, s, q, sig0, d0, lam=0.0, mode='both'):
    mu, var, last, prev = {}, {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); innov = np.full(len(d), np.nan)
    horses = d.horse.values; dates = d.date.values.astype('datetime64[D]').astype(np.int64); perf = d.perf.values
    keys = d.race_key.values; starts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1]) + 1, len(d)]
    ll, n = 0.0, 0
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
            ll += -0.5 * (np.log(2 * np.pi * pv) + inn * inn / pv).sum(); n += ok.sum()      # predictive fit judged BEFORE any boost
            idx = np.arange(a, b)[ok]; innov[idx] = inn
            if lam:
                pr = np.array([prev.get(h, 0.0) for h in hs[ok]])
                same = (np.sign(pr) == np.sign(inn)) & (pr != 0)
                if mode == 'up': same &= inn > 0
                vv_ = np.where(same, vv_ * (1 + lam), vv_)
            K = vv_ / (vv_ + s * s); m[ok] = mm_ + K * inn; v[ok] = (1 - K) * vv_
            for h, i_ in zip(hs[ok], inn): prev[h] = i_
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    run.ll = ll / max(n, 1)
    return pre_mu, pre_sd, innov
