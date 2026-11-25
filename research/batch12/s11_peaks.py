"""Batch 12 s11-12: peak vs typical ability, peak recency and frequency, decline vs recovery. Does knowing how often and how recently a horse
reproduced its best add anything beyond Engine v2.2 (which already has own variability, distance below best-3, long-run gap, slope)?
Performance per run = pre-race rating + surprise (kg), earlier runs only. Judged on 2025-26 (out of sample) and 2024 (discovery)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
U = pd.read_parquet('/home/claude/b10/research/engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'dyn_nat', 'dyn_nat_inn'])
U = U.sort_values(['horse', 'date']).reset_index(drop=True); U['perf'] = U.dyn_nat + U.dyn_nat_inn; g = U.groupby('horse')
best = g.perf.transform(lambda s: s.shift().cummax()); U['best_prior'] = best
# runs since the best, share of earlier runs within 3 kg of the best (peak frequency), recent typical (median of last 5) vs best
def per_horse(s, d):
    p = s.values; out_since = np.full(len(p), np.nan); out_freq = np.full(len(p), np.nan); out_typ = np.full(len(p), np.nan); out_days = np.full(len(p), np.nan)
    for i in range(1, len(p)):
        h = p[:i]; ok = ~np.isnan(h)
        if ok.sum() == 0: continue
        hv = h[ok]; b = hv.max(); j = np.where(ok)[0][np.argmax(hv)]
        out_since[i] = i - 1 - j; out_freq[i] = (hv >= b - 3).mean(); out_typ[i] = np.median(hv[-5:]); out_days[i] = (d[i] - d[j]) / np.timedelta64(1, 'D')
    return pd.DataFrame({'runs_since_best': out_since, 'peak_freq': out_freq, 'typical5': out_typ, 'days_since_best': out_days}, index=s.index)
parts = [per_horse(grp.perf, grp.date.values) for _, grp in U.groupby('horse', sort=False)]
U = U.join(pd.concat(parts)); U['best_minus_typical'] = U.best_prior - U.typical5
x = pd.read_parquet('/home/claude/b10/research/b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1]
x = x.merge(U[['race_id', 'horse', 'runs_since_best', 'peak_freq', 'typical5', 'days_since_best', 'best_minus_typical', 'best_prior']], on=['race_id', 'horse'], how='left')
x['v2'] = x.v22_dev; x['log_days_since_best'] = np.log1p(x.days_since_best); x['typ_rel'] = x.typical5 - x.groupby('race_id').typical5.transform('mean'); x['best_rel'] = x.best_prior - x.groupby('race_id').best_prior.transform('mean')
rows = []
for cols, lab in [(['peak_freq'], 'peak frequency (share of runs within 3 kg of best)'), (['log_days_since_best'], 'time since best'), (['runs_since_best'], 'runs since best'),
                  (['best_minus_typical'], 'best minus recent typical'), (['typ_rel'], 'recent typical vs field'), (['best_rel'], 'career best vs field'),
                  (['peak_freq', 'log_days_since_best', 'best_minus_typical'], 'peak bundle')]:
    for st in ['discovery', 'validation']:
        r = L.test(x[x.n_prior >= 5].copy(), cols, lab, st); rows.append({k: r.get(k) for k in ['label', 'stage', 'coef_per_sd', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'gain_west', 'coverage_%']})
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('/home/claude/b12/out_s11_peaks.csv', index=False)
# the two-horse example: consistent vs occasionally brilliant, same typical level (2025-26, 10+ runs)
o = x[(x.meeting_date.dt.year >= 2025) & (x.n_prior >= 10)].copy(); o['h'] = pd.qcut(o.h_sd, 3, labels=['most consistent third', 'middle', 'least consistent third'])
o['top'] = o.groupby('race_id').v22_dev.rank(ascending=False) == 1
t = o.groupby('h', observed=True).apply(lambda d: pd.Series({'runs': len(d), 'actual_over_expected': d.win.sum() / d.p_v22.sum(), 'top_pick_runs': int(d.top.sum()), 'top_pick_ae': d[d.top].win.sum() / d[d.top].p_v22.sum()}), include_groups=False)
print(t.round(3).to_string()); t.to_csv('/home/claude/b12/out_s12_consistency.csv')
