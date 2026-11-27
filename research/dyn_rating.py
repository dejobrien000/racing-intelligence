"""Study 12 prototype: point-in-time dynamic opposition rating (margin-based, Gaussian, updated race by race).
Each horse: current ability mu (kg) and uncertainty var. In each race, observed performance = -(margin x kg per length)
+ (weight - 57). Only performance RELATIVE to the field is used, judged against the current ratings of the horses
actually met (so beating strong opposition counts for more than beating weak). After the race each runner moves towards
what it showed, by a Kalman gain var/(var + s^2); uncertainty then shrinks, and grows again with time off (q per day).
Strictly point-in-time: a race only ever sees ratings built from earlier races.
Usage (module): run(df, s, q, sig0, d0) -> pre-race mu/var per run, and the Gaussian predictive log-likelihood."""
import numpy as np, pandas as pd

def prepare(df):
    """Keeps EVERY runner (so non-finishers still get a pre-race rating); perf is NaN where the run can't be measured
    (did not finish, no margin or no weight) and such runs are simply not used to update anyone."""
    d = df.copy()
    d['kgpl'] = 1.5 * (1200 / d.distance_m) ** 0.8
    ok = d.finish_pos.notna() & d.margin_l.notna() & d.weight_kg.notna()
    import os; WC = float(os.environ.get('WCREDIT', '1'))   # history weight credit per kg (production 1.0; candidate C2 0.25: benchmarks/candidate_national_weight)
    d['perf'] = np.where(ok, -d.margin_l.clip(upper=25) * d.kgpl + WC * (d.weight_kg - 57), np.nan)
    CAP = os.environ.get('RATING_CAP_L')   # CANDIDATE ONLY (Batch 16 B9; off unless set). The margin in the data is never changed.
    if CAP and os.environ.get('RATING_CAP_SCOPE', 'update') == 'all':
        # 'all': the performance FIGURE used by the rating and by the form features built from it counts a defeat at most CAP lengths
        d['perf'] = np.where(ok, -d.margin_l.clip(upper=float(CAP)) * d.kgpl + WC * (d.weight_kg - 57), np.nan)
    elif CAP and os.environ.get('RATING_CAP_SCOPE') == 'reference':   # Batch 17 B10: the cap limits ONLY the race-level reference the other runners are measured against
        d['perf_ref'] = np.where(ok, -d.margin_l.clip(upper=float(CAP)) * d.kgpl + WC * (d.weight_kg - 57), np.nan)
    elif CAP:                              # 'update': only the rating move is limited; the performance figure and its innovation stay as recorded
        d['perf_upd'] = np.where(ok, -d.margin_l.clip(upper=float(CAP)) * d.kgpl + WC * (d.weight_kg - 57), np.nan)
    d = d.sort_values(['date', 'race_key', 'finish_pos'])
    return d

def run(d, s=5.0, q=0.02, sig0=6.0, d0=2.0, collect=True):
    mu, var, last = {}, {}, {}
    pre_mu = np.full(len(d), np.nan); pre_sd = np.full(len(d), np.nan); ll = 0.0; n = 0
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
            ll += -0.5 * (np.log(2 * np.pi * pv) + inn * inn / pv).sum(); n += ok.sum()
            K = vv_ / pv; m[ok] = mm_ + K * inn; v[ok] = (1 - K) * vv_
        for h, mm, vv, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm; var[h] = vv; last[h] = t
    return pre_mu, pre_sd, ll / max(n, 1)
