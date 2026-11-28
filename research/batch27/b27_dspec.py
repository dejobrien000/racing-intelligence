"""Batch 27 P3: distance-specific suitability (preregistered spec, h = 0.12 kept by the pre-2024 neighbourhood rule) from ANY rating frame's
own surprises, and a copy of that frame with the distance record replaced by it (the replacement test; nothing else changes).
dsuit = sum_j w_j inn_j / (sum_j w_j + 3), w = exp(-(ld - ld_j)^2 / (2 h^2)) over the horse's EARLIER runs; gen = sum inn / (n + 3);
dspec = dsuit - gen * ev / (ev + 3), ev = sum w. Usage: python3 batch27/b27_dspec.py <frame in> <frame out> <feature parquet out>"""
import sys, numpy as np, pandas as pd
fin, fout, ffeat = sys.argv[1:4]; H, K = 0.12, 3.0
F = pd.read_parquet(fin); F['_o'] = np.arange(len(F))
S = F[['_o', 'horse', 'date', 'race', 'distance_m', 'dyn_nat_inn']].copy(); S['date'] = pd.to_datetime(S.date)
S = S.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
ld = np.log(S.distance_m.astype(float).values); inn = S.dyn_nat_inn.astype(float).values; hs = S.horse.values; n = len(S)
dsuit = np.zeros(n); ev = np.zeros(n); gen = np.zeros(n)
starts = np.r_[0, np.flatnonzero(hs[1:] != hs[:-1]) + 1, n]
for a, b in zip(starts[:-1], starts[1:]):
    for i in range(a + 1, b):
        j = np.arange(a, i); j = j[~np.isnan(inn[j])]
        if len(j) == 0: continue
        w = np.exp(-(ld[i] - ld[j]) ** 2 / (2 * H * H)); s = w.sum()
        dsuit[i] = (w * inn[j]).sum() / (s + K); ev[i] = s; gen[i] = inn[j].sum() / (len(j) + K)
S['dspec'] = dsuit - gen * ev / (ev + K); S['dsuit_ev'] = ev
S = S.set_index('_o').reindex(F._o)
F['d_rec'] = S.dspec.values; F['d_rec_n'] = S.dsuit_ev.values           # replacement: the record's slot now carries the distance-specific measure
F.drop(columns=['_o']).to_parquet(fout)
F[['race_id', 'horse']].assign(dspec=S.dspec.values, dsuit_ev=S.dsuit_ev.values).drop_duplicates(['race_id', 'horse']).to_parquet(ffeat)
print('dspec written', fout, len(F), 'mean', round(float(np.nanmean(S.dspec.values)), 3), 'sd', round(float(np.nanstd(S.dspec.values)), 3))
