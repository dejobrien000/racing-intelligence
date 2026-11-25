"""Batch 12 s13: perennial placegetters. Does a horse's past under/over-conversion (actual wins vs the engine's market-free expected wins over
its earlier runs) predict its next result beyond the engine? Expected wins = Engine v2.2 (dev-fit) chances; judged on 2025-26 (out of sample).
Strong shrinkage: conversion = (wins + 3) / (expected + 3). Compared with raw career strike rate."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
x = pd.read_parquet('/home/claude/b10/research/b11/v22hist.parquet', columns=['race_id', 'horse', 'meeting_date', 'meeting_id', 'state', 'win', 'fpos', 'field', 'p_v22', 'v22_dev', 'n_prior', 'dyn_nat'])
x = x[x.groupby('race_id').win.transform('sum') == 1].sort_values(['horse', 'meeting_date']).copy(); g = x.groupby('horse')
x['W'] = g.win.cumsum() - x.win; x['Ex'] = g.p_v22.cumsum() - x.p_v22; x['N'] = g.cumcount()
x['place'] = (x.fpos <= 3).astype(float); x['P'] = g.place.cumsum() - x.place
x['conv'] = (x.W + 3) / (x.Ex + 3); x['log_conv'] = np.log(x.conv); x['career_sr'] = x.W / x.N.replace(0, np.nan)
x['placegetter'] = ((x.P - x.W) / x.N.replace(0, np.nan))                     # share of runs placed 2nd/3rd
o = x[(x.meeting_date.dt.year >= 2025) & (x.N >= 10)].copy()
o['cband'] = pd.qcut(o.conv, 5, labels=['most under-converting fifth', 'q2', 'q3', 'q4', 'most over-converting fifth'])
t = o.groupby('cband', observed=True).agg(runs=('win', 'size'), horses=('horse', 'nunique'), wins=('win', 'sum'), expected=('p_v22', 'sum'), mean_past_wins=('W', 'mean'), mean_past_expected=('Ex', 'mean'))
t['actual_over_expected'] = (t.wins / t.expected).round(3); print(t.round(2).to_string())
# 'perennial placegetters': many seconds/thirds, few wins vs expected
pp = o[(o.placegetter >= 0.30) & (o.conv < 0.8)]; print('perennial-placegetter profile (30%+ of runs 2nd/3rd, conversion < 0.8):', len(pp), 'runs,', pp.horse.nunique(), 'horses, actual/expected next', round(pp.win.sum() / pp.p_v22.sum(), 3))
x['v2'] = x.v22_dev; rows = []
for cols, lab in [(['log_conv'], 'past conversion (shrunk)'), (['career_sr'], 'raw career strike rate'), (['log_conv', 'career_sr'], 'both')]:
    for st in ['discovery', 'validation']:
        r = L.test(x[x.N >= 1].copy(), cols, lab, st); rows.append({k: r.get(k) for k in ['label', 'stage', 'coef_per_sd', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'gain_west']})
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('/home/claude/b12/out_s13_conversion.csv', index=False); t.to_csv('/home/claude/b12/out_s13_bands.csv')
