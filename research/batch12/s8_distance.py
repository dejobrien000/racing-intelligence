"""Batch 12 s8-9: continuous, evolving distance suitability vs the engine's band record, and the preparation-stage confound.
Surprise = how much better/worse than its rating a horse ran (kg, field-relative). Earlier runs only. On top of Engine v2.2 (dev-fit)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
U = pd.read_parquet('/home/claude/b10/research/engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'distance_m', 'dyn_nat_inn', 'd_rec', 'tier'])
F = pd.read_parquet('/home/claude/b10/research/b10/out/feat.parquet', columns=['race_id', 'horse', 'prep_run'])
U = U.merge(F, on=['race_id', 'horse'], how='left').sort_values(['horse', 'date']).reset_index(drop=True)
# 1. preparation-stage bias in surprises (population): first-up runs vs later
U['prep_b'] = U.prep_run.clip(upper=6)
ps = U.groupby('prep_b').dyn_nat_inn.agg(['mean', 'size']).round(3); print('mean surprise by run of preparation (1 = first-up):'); print(ps.to_string())
dist_by_prep = U.groupby('prep_b').distance_m.median(); print('median distance by run of preparation:', dist_by_prep.to_dict())
adj = U.prep_b.map(ps['mean']); U['inn_adj'] = U.dyn_nat_inn - adj                # surprise with the average preparation-stage effect removed
# 2. continuous distance profile: kernel-weighted mean of earlier surprises by log-distance closeness (bandwidth 0.12 ~ +-12%), shrunk with 3 runs
def prof(gr, col):
    ld = np.log(gr.distance_m.values); s = gr[col].values; out = np.full(len(s), np.nan); n_eff = np.full(len(s), 0.0)
    for i in range(1, len(s)):
        ok = ~np.isnan(s[:i]); 
        if not ok.any(): continue
        w = np.exp(-((ld[:i][ok] - ld[i]) ** 2) / (2 * 0.12 ** 2)); out[i] = (w * s[:i][ok]).sum() / (w.sum() + 3.0); n_eff[i] = w.sum()
    return pd.DataFrame({col + '_prof': out, col + '_neff': n_eff}, index=gr.index)
for col in ['dyn_nat_inn', 'inn_adj']:
    U = U.join(pd.concat([prof(gr, col) for _, gr in U.groupby('horse', sort=False)]))
x = pd.read_parquet('/home/claude/b10/research/b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1]
x = x.merge(U[['race_id', 'horse', 'dyn_nat_inn_prof', 'inn_adj_prof', 'dyn_nat_inn_neff', 'd_rec']], on=['race_id', 'horse'], how='left'); x['v2'] = x.v22_dev
rows = []
for cols, lab in [(['dyn_nat_inn_prof'], 'continuous distance profile'), (['inn_adj_prof'], 'continuous profile, preparation stage removed'), (['d_rec'], 'band record again (already in engine)')]:
    for st in ['discovery', 'validation']:
        r = L.test(x[x.n_prior >= 3].copy(), cols, lab, st); rows.append({k: r.get(k) for k in ['label', 'stage', 'coef_per_sd', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'gain_west']})
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('/home/claude/b12/out_s8_distance.csv', index=False); ps.to_csv('/home/claude/b12/out_s9_prep_surprise.csv')
# 3. by class of racing: preparation-stage effect in metro / provincial / country
t = U.groupby(['tier', 'prep_b']).dyn_nat_inn.mean().unstack().round(2); print('mean surprise by preparation run and tier:'); print(t.to_string())
