"""Batch 10: (a) residual-scan items as model terms; (b) one candidate bundle (v2.2 research candidate) fitted jointly with a ridge,
judged on 2024 (fit to 2023) and on 2025-26 (fit to 2024), by region and year; ranking measures included. Research only."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
b = L.base('nat'); F = pd.read_parquet('b10/out/feat.parquet').drop(columns=['date', 'state'])
x = b.merge(F, on=['race_id', 'horse'], how='left')
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'age_n', 'f_avgfp3', 'weight_kg', 'female', 'dyn_nat_sd', 'a_wt_rel'])
vs = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
U = U.sort_values(['horse', 'date']); U['venue_level'] = U.venue.map(vs); U['venue_step'] = U.venue_level - U.groupby('horse').venue_level.shift()
x = x.merge(U.drop(columns=['date', 'venue', 'venue_level']), on=['race_id', 'horse'], how='left')
x['rel_rating'] = x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean'); x['hsd_x_rel'] = x.h_sd * x.rel_rating
x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['male'] = 1 - x.female
x['age3'] = (x.age_n == 3).astype(float).where(x.age_n.notna()); x['rating_uncertainty'] = x.dyn_nat_sd
rows = []
for c in ['light_weight', 'weight_kg', 'log_runs_held', 'rating_uncertainty', 'male', 'age3', 'quick_today']:
    r = L.test(x, [c], c, 'validation'); r['section'] = 'residual scan item'; rows.append(r); print({k: r.get(k) for k in ['label', 'coef_per_sd', 'gain', 'lo95', 'hi95', 'gain_west', 'top_pick_pts']}, flush=True)
BUNDLE = ['below_top3', 'gap_long_z', 'short_vs_long', 'slope15', 'neg_run', 'recent_var_ratio', 'hsd_x_rel', 'early_prep_vs_usual', 'quick_today', 'venue_step', 'recentform_x_established',
          'light_weight', 'log_runs_held', 'rating_uncertainty']
for stage in ['discovery', 'validation']:
    for ridge in [1.0, 30.0]:
        r = L.test(x, BUNDLE, f'bundle ridge {ridge}', stage, ridge=ridge); r['section'] = 'candidate bundle'; rows.append(r); print({k: r.get(k) for k in ['label', 'stage', 'gain', 'lo95', 'hi95', 'gain_east', 'gain_west', 'west_lo', 'top_pick_pts']}, flush=True)
pd.DataFrame(rows).to_csv('b10/out/t10b.csv', index=False)
# per-year and per-state view of the validation bundle (ridge 30), plus winner-in-top-3
yr = x.meeting_date.dt.year; fitm = pd.Series((yr <= 2024).values, index=x.index); evm = pd.Series((yr >= 2025).values, index=x.index)
z = L.prep_z(x.copy(), BUNDLE, fitm); off = z.v2.values; bb = L.clogit_fit(z, BUNDLE, fitm, off, 30.0); e = off + z[[c + '_z' for c in BUNDLE]].values @ bb
a0, a1 = L.race_lp(z, off, evm), L.race_lp(z, e, evm); d = a1.lp - a0.lp
print('coefficients per SD:', dict(zip(BUNDLE, np.round(bb, 4))))
t = pd.DataFrame({'state': a1.state, 'year': a1.date.dt.year, 'gain': d, 'hit0': a0.hit, 'hit1': a1.hit})
print(t.groupby('state')[['gain', 'hit0', 'hit1']].mean().round(4).to_string()); print(t.groupby('year')[['gain', 'hit0', 'hit1']].mean().round(4).to_string())
pd.Series(dict(zip(BUNDLE, bb))).to_csv('b10/out/t10b_bundle_coefs.csv')
