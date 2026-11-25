"""Batch 12 s14: opposition composition beyond field strength. Earlier work rejected running style x opposition (Qld, Batch 10) and the
leader-pressure terms live only in the Qld model; this tests only NEW composition measures on top of Engine v2.2 (dev-fit), national."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
x = pd.read_parquet('/home/claude/b10/research/b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1].copy(); x['v2'] = x.v22_dev
r = x.groupby('race_id').dyn_nat
x['n_above2'] = x.groupby('race_id').dyn_nat.transform(lambda s: [(s > v + 2).sum() for v in s]) if False else 0
x = x.sort_values(['race_id', 'dyn_nat'], ascending=[True, False]); x['rank_rating'] = x.groupby('race_id').cumcount()
x['n_above2'] = x.groupby('race_id').dyn_nat.transform(lambda s: np.searchsorted(-np.sort(-s.values)[::-1], s.values + 2, side='right')) * 0
v = x.dyn_nat.values; rid = pd.factorize(x.race_id)[0]
# number of rivals rated 2 kg+ above (vectorised per race)
out = np.zeros(len(x))
for k, idx in pd.Series(np.arange(len(x))).groupby(rid):
    vv = v[idx.values]; out[idx.values] = (vv[None, :] > vv[:, None] + 2).sum(axis=1)
x['n_above2'] = out; x['field_sd'] = r.transform('std'); x['top2_gap'] = x.groupby('race_id').dyn_nat.transform(lambda s: np.sort(s.values)[-1] - np.sort(s.values)[-2] if len(s) > 1 else np.nan)
x['above2_x_rel'] = x.n_above2 * (x.dyn_nat - r.transform('mean'))
rows = []
for cols, lab in [(['n_above2'], 'rivals rated 2 kg+ above'), (['field_sd'], 'spread of field ratings'), (['top2_gap'], 'gap between the two best-rated'), (['above2_x_rel'], 'rivals above x own standing')]:
    for st in ['discovery', 'validation']:
        q = L.test(x.copy(), cols, lab, st); rows.append({k: q.get(k) for k in ['label', 'stage', 'coef_per_sd', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'gain_west']})
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('/home/claude/b12/out_s14_opposition.csv', index=False)
