"""Batch 27 P3 (preregistered rule, runs BEFORE 2024 only): how fast does the within-horse correlation of surprises fall with the
log-distance gap, for sprints (<=1200 m), middle (1201-1800) and staying (1801+)? Pairs of runs of the same horse at most 8 runs apart.
half-gap = gap where (corr(gap) - corr(far)) falls to half of (corr(near) - corr(far)); far = gaps 0.45-0.70. Output out_b27_dist_neighbourhood.json"""
import json, numpy as np, pandas as pd
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'distance_m', 'dyn_nat_inn'])
F = F[pd.to_datetime(F.date) < '2024-01-01'].dropna(subset=['dyn_nat_inn']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
F['ld'] = np.log(F.distance_m.astype(float)); F['inn'] = F.dyn_nat_inn.astype(float)
F['inn'] = F.inn - F.groupby('horse').inn.transform('mean')          # remove each horse's general level (distance-specific part only)
h = F.horse.values; P = []
for lag in range(1, 9):
    same = h[lag:] == h[:-lag]; a = np.flatnonzero(same)
    P.append(pd.DataFrame({'i1': F.inn.values[a], 'i2': F.inn.values[a + lag], 'gap': np.abs(F.ld.values[a] - F.ld.values[a + lag]), 'dm': np.exp((F.ld.values[a] + F.ld.values[a + lag]) / 2)}))
P = pd.concat(P); P['rng'] = pd.cut(P.dm, [0, 1200, 1800, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
bins = [-0.001, 0.03, 0.08, 0.13, 0.18, 0.25, 0.35, 0.45, 0.70]
out = {}
for r, Z in [('pooled', P)] + list(P.groupby('rng')):
    Z = Z.assign(b=pd.cut(Z.gap, bins)); c = Z.groupby('b', observed=True).apply(lambda g: pd.Series({'pairs': len(g), 'corr': g.i1.corr(g.i2)}))
    near, far = c['corr'].iloc[0], c['corr'].iloc[-1]; mid = far + (near - far) / 2
    x = [(iv.left + iv.right) / 2 for iv in c.index]; y = c['corr'].values
    hg = next((x[i - 1] + (x[i] - x[i - 1]) * (y[i - 1] - mid) / (y[i - 1] - y[i]) for i in range(1, len(y)) if y[i] <= mid), None)
    out[r] = {'pairs': int(len(Z)), 'corr_by_gap': {str(k): [int(v.pairs), round(float(v['corr']), 4)] for k, v in c.iterrows()}, 'half_gap_log': None if hg is None else round(float(hg), 3)}
hp = out['pooled']['half_gap_log']; rs = {r: out[r]['half_gap_log'] for r in ['sprint', 'middle', 'staying']}
differs = any(v is not None and hp and abs(v / hp - 1) > 0.5 for v in rs.values())
out['decision'] = {'pooled_half_gap': hp, 'by_range': rs, 'range_specific': bool(differs),
                   'bandwidths': {r: round(0.12 * (v / hp), 3) for r, v in rs.items()} if differs else {'all': 0.12}}
json.dump(out, open('batch27/out_b27_dist_neighbourhood.json', 'w'), indent=1); print(json.dumps(out['decision']))
for r in ['pooled', 'sprint', 'middle', 'staying']: print(r, out[r]['pairs'], out[r]['corr_by_gap'])
