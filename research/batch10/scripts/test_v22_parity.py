"""Parity: production engine/v22.raw on (history before D + D's runners) must equal the research features for the same runs."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '.'); sys.path.insert(0, 'b10/scripts'); from engine import v22; import lib10 as L
U = pd.read_parquet('engine/frames/national.parquet'); b = L.base('nat')
F = pd.read_parquet('b10/out/feat.parquet').drop(columns=['date', 'state'])
VL = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
R = U[['race_id', 'horse', 'date', 'venue', 'f_avgfp3', 'weight_kg', 'dyn_nat_sd']].sort_values(['horse', 'date']).copy(); R['vl'] = R.venue.map(VL); R['venue_step'] = R.vl - R.groupby('horse').vl.shift()
x = b.merge(F, on=['race_id', 'horse'], how='left').merge(R.drop(columns=['date', 'venue', 'vl']), on=['race_id', 'horse'], how='left')
x['hsd_x_rel'] = x.h_sd * (x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')); x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['rating_uncertainty'] = x.dyn_nat_sd
bad = 0
for D in ['2026-10-18', '2026-11-11', '2025-06-07']:
    t = x[x.meeting_date == D].copy(); H_ = U[U.date < pd.Timestamp(D)]
    T = t[['race_id', 'horse', 'dyn_nat', 'weight_kg', 'venue', 'f_avgfp3']].assign(date=pd.Timestamp(D), rating_sd_kg_national=t.dyn_nat_sd.values)
    P = v22.raw(T, H_)
    for c in v22.M['terms']:
        a = pd.to_numeric(P['b22_' + c], errors='coerce').values; r = pd.to_numeric(t[c], errors='coerce').values
        same = np.isclose(a, r, rtol=1e-7, atol=1e-7, equal_nan=True)
        if not same.all(): bad += 1; print(D, c, 'MISMATCH', (~same).sum(), 'of', len(a), list(zip(a[~same][:3], r[~same][:3])))
    print(D, len(T), 'runners checked')
print('PARITY', 'PASS' if bad == 0 else 'FAIL')
