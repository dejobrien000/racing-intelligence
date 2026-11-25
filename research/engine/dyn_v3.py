"""Engine v3 candidate rating (Batch 9, study A): same Gaussian opposition-aware rating as dyn_rating_innov, with the
learning speed split into its two racing meanings and allowed to depend on the horse's situation:
  * persistence (how fast true ability changes) = process noise. Young / lightly raced horses get more (a_q, decaying with
    measured runs over n0); a return from a spell (> 60 days) adds a one-off v_spell kg^2 of extra uncertainty.
  * measurement reliability (how well one run shows ability) = run noise s. First-up runs get s x (1 + s_first).
  * improvement: after each measured run a lightly raced horse's rating rises by g_imp x exp(-runs/n0) kg (expected
    development), so the rating need not wait for the next surprise.
  * trend: when this surprise has the same sign as the last one, uncertainty is inflated by (1 + c_trend) before updating.
All zero = the frozen rating exactly. Point-in-time: a race only sees earlier races. Predictive fit is judged BEFORE any
inflation, as in the frozen rating."""
import numpy as np
def run(d, s, q, sig0, d0, a_q=0.0, n0=6.0, v_spell=0.0, s_first=0.0, c_trend=0.0, g_imp=0.0):
    mu, var, last, prev, cnt = {}, {}, {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); innov = np.full(len(d), np.nan)
    horses = d.horse.values; dates = d.date.values.astype('datetime64[D]').astype(np.int64); perf = d.perf.values
    keys = d.race_key.values; starts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1]) + 1, len(d)]
    ll, n, lld, nd = 0.0, 0, 0.0, 0
    dev_end = np.datetime64('2025-01-01').astype('datetime64[D]').astype(np.int64)
    for a, b in zip(starts[:-1], starts[1:]):
        hs = horses[a:b]; t = dates[a]
        known = [mu[h] for h in hs if h in mu]; base = (np.mean(known) if known else 0.0) - d0
        m = np.array([mu.get(h, base) for h in hs])
        gap = np.array([t - last[h] if h in last else -1 for h in hs], dtype=float)
        qh = np.array([q * (1 + a_q * np.exp(-cnt.get(h, 0) / n0)) for h in hs])
        v = np.array([var[h] if h in var else sig0 ** 2 for h in hs])
        v = np.where(gap >= 0, np.minimum(v + qh * np.maximum(gap, 0) + np.where(gap > 60, v_spell, 0.0), sig0 ** 2), sig0 ** 2)
        pre_mu[a:b] = m; pre_sd[a:b] = np.sqrt(v)
        ok = ~np.isnan(perf[a:b])
        if ok.sum() >= 2:
            pm, mm_, vv_ = perf[a:b][ok], m[ok], v[ok]
            sr = s * np.where(gap[ok] > 60, 1 + s_first, 1.0)
            inn = (pm - pm.mean()) - (mm_ - mm_.mean()); pv = vv_ + sr * sr
            l_ = -0.5 * (np.log(2 * np.pi * pv) + inn * inn / pv)
            if t < dev_end: lld += l_.sum(); nd += ok.sum()
            else: ll += l_.sum(); n += ok.sum()
            idx = np.arange(a, b)[ok]; innov[idx] = inn
            if c_trend:
                pr = np.array([prev.get(h, 0.0) for h in hs[ok]]); same = (np.sign(pr) == np.sign(inn)) & (pr != 0)
                vv_ = np.where(same, vv_ * (1 + c_trend), vv_)
            K = vv_ / (vv_ + sr * sr); m[ok] = mm_ + K * inn; v[ok] = (1 - K) * vv_
            for j_, (h, i_) in enumerate(zip(hs[ok], inn)): prev[h] = i_; cnt[h] = cnt.get(h, 0) + 1
            if g_imp: m[ok] = m[ok] + g_imp * np.exp(-np.array([cnt[h] for h in hs[ok]]) / n0)   # expected improvement after a run, larger for lightly raced horses
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    run.ll_dev = lld / max(nd, 1); run.ll_eval = ll / max(n, 1)
    return pre_mu, pre_sd, innov
