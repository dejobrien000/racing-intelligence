"""Out-of-sample Engine v2.2 chances for history (dev-fit coefficients, fitted on races before 2025): b11/v22hist.parquet. Research only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
U0, E, NFAM2, build_terms, offset_v1 = g['U'], g['E'], g['NFAM2'], g['build_terms'], g['offset_v1']
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); F2 = MAN['families']['NSW_VIC_ACT']; M22 = json.load(open('benchmarks/engine_v2_2/manifest.json'))
x = E.nat_frame(U0); allt = sum(NFAM2.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat'); Tm = x[['t::' + a for a in allt]].values
x['v2_dev'] = off + Tm @ np.array([F2['coef_per_term_sd_dev_fit'][t] for t in allt])
keep = [c for c in ['race_id', 'horse', 'meeting_date', 'state', 'venue', 'meeting_id', 'win', 'fpos', 'field', 'dyn_nat', 'v2_dev', 'tkey', 'jkey', 'distance_m'] if c in x]
x = x[keep].copy(); x['meeting_date'] = pd.to_datetime(x.meeting_date)
F = pd.read_parquet('b10/out/feat.parquet').drop(columns=['date', 'state']); x = x.merge(F, on=['race_id', 'horse'], how='left')
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'f_avgfp3', 'weight_kg', 'dyn_nat_sd', 'prev_state', 'class_label', 'r_ldays'])
VL = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
U = U.sort_values(['horse', 'date']); U['venue_level'] = U.venue.map(VL); U['venue_step'] = U.venue_level - U.groupby('horse').venue_level.shift()
x = x.merge(U.drop(columns=['date', 'venue', 'venue_level']), on=['race_id', 'horse'], how='left')
x['hsd_x_rel'] = x.h_sd * (x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')); x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['rating_uncertainty'] = x.dyn_nat_sd
T = M22['terms']; z = np.column_stack([((pd.to_numeric(x[c], errors='coerce') - pd.to_numeric(x[c], errors='coerce').groupby(x.race_id).transform('mean')).fillna(0.0) / M22['term_sd_dev_fit'][c]).values for c in T])
x['v22_dev'] = x.v2_dev + z @ np.array([M22['coef_per_sd_dev_fit'][c] for c in T])
for k in ['v2_dev', 'v22_dev']:
    mx = x.groupby('race_id')[k].transform('max'); p = np.exp(x[k] - mx); x['p_' + k[:-4]] = p / p.groupby(x.race_id).transform('sum')
x.to_parquet('b11/v22hist.parquet'); print(x.shape, x[['p_v2', 'p_v22']].describe().round(3).to_dict())
