"""Batch 12 s10: preparation-relative improvement. If a horse runs better than at the SAME run of its previous preparation, does the
difference persist (next start), beyond what Engine v2.2 already knows? Performance per run = pre-race rating + surprise (kg)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
U = pd.read_parquet('/home/claude/b10/research/engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'dyn_nat', 'dyn_nat_inn', 'distance_m', 'age_n'])
F = pd.read_parquet('/home/claude/b10/research/b10/out/feat.parquet', columns=['race_id', 'horse', 'prep_run'])
U = U.merge(F, on=['race_id', 'horse'], how='left').sort_values(['horse', 'date']).reset_index(drop=True)
U['perf'] = U.dyn_nat + U.dyn_nat_inn; U['prep_id'] = (U.prep_run == 1).astype(int).groupby(U.horse).cumsum()
P = U[U.prep_run.between(1, 4)][['horse', 'prep_id', 'prep_run', 'perf', 'distance_m']]
prev = P.assign(prep_id=P.prep_id + 1).rename(columns={'perf': 'perf_prevprep', 'distance_m': 'dist_prevprep'})
U = U.merge(prev, on=['horse', 'prep_id', 'prep_run'], how='left')
U['vs_prev_prep'] = U.perf - U.perf_prevprep                         # this run vs the same run of the previous preparation (kg)
U['same_dist'] = (np.log(U.distance_m / U.dist_prevprep)).abs() < 0.1
g = U.groupby('horse'); U['next_inn'] = g.dyn_nat_inn.shift(-1); U['next_vs_prev'] = g.vs_prev_prep.shift(-1); U['vs_prev_lag'] = g.vs_prev_prep.shift()
d = U[U.vs_prev_prep.notna() & U.next_vs_prev.notna()]
print('persistence: correlation of (this run vs previous prep) with (next run vs previous prep):', round(d[['vs_prev_prep', 'next_vs_prev']].corr().iloc[0, 1], 3), '| pairs', len(d),
      '| same distance both times:', round(d[d.same_dist][['vs_prev_prep', 'next_vs_prev']].corr().iloc[0, 1], 3))
d['band'] = pd.cut(d.vs_prev_prep, [-99, -6, -3, -1, 1, 3, 6, 99])
print(d.groupby('band', observed=True).agg(pairs=('next_vs_prev', 'size'), next_vs_prev_prep=('next_vs_prev', 'mean'), next_surprise=('next_inn', 'mean')).round(2).to_string())
U['prev_prep_level'] = U.perf_prevprep  # (the horse's level at this point last time)
x = pd.read_parquet('/home/claude/b10/research/b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1]
U['last_vs_prev'] = U.groupby('horse').vs_prev_prep.shift()            # PRE-RACE: the previous start's comparison with its previous preparation
x = x.merge(U[['race_id', 'horse', 'last_vs_prev']], on=['race_id', 'horse'], how='left'); x['v2'] = x.v22_dev
rows = [{k: r.get(k) for k in ['label', 'stage', 'coef_per_sd', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'gain_west', 'coverage_%']} for r in
        [L.test(x.copy(), ['last_vs_prev'], 'last start vs same run of previous prep', st) for st in ['discovery', 'validation']]]
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('/home/claude/b12/out_s10_prep_rel.csv', index=False)
