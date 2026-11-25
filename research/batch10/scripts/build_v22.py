"""Build the Engine v2.2 release files (approved by Damo 25 Nov 2026: 'Replace from tomorrow').
v2.2 = Engine v2 NSW/VIC/ACT family score (unchanged) + 14 Batch 10 terms (career shape & consistency, weight, spacing, measured venue class).
Applies to NSW, VIC, ACT, SA, WA, TAS meetings. Queensland stays on Engine v2.1. Coefficients: fitted on all races to 23 Nov 2026 on top of the
production v2 score (all-races coefficients), the same rule v2 used; the dev-fit (<2025) coefficients and their 2025-26 validation are recorded.
Calibration (display): bent line refitted on the dev-fit v2.2 chances for 2025-26 (out of sample for the 14 terms).
Writes benchmarks/engine_v2_2/manifest.json and benchmarks/engine_v2_2/runner_calibration_v22.json (+ /tmp/v22_oos.parquet)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
U0, E, NFAM2, build_terms, offset_v1 = g['U'], g['E'], g['NFAM2'], g['build_terms'], g['offset_v1']
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); F2 = MAN['families']['NSW_VIC_ACT']
x = E.nat_frame(U0); allt = sum(NFAM2.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat'); Tm = x[['t::' + a for a in allt]].values
x['v2_dev'] = off + Tm @ np.array([F2['coef_per_term_sd_dev_fit'][t] for t in allt]); x['v2_all'] = off + Tm @ np.array([F2['coef_per_term_sd_all_races'][t] for t in allt])
x = x[['race_id', 'horse', 'meeting_date', 'state', 'venue', 'meeting_id', 'period', 'win', 'fpos', 'field', 'dyn_nat', 'v2_dev', 'v2_all']].copy(); x['meeting_date'] = pd.to_datetime(x.meeting_date)
F = pd.read_parquet('b10/out/feat.parquet').drop(columns=['date', 'state']); x = x.merge(F, on=['race_id', 'horse'], how='left')
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'f_avgfp3', 'weight_kg', 'dyn_nat_sd'])
VL = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
U = U.sort_values(['horse', 'date']); U['venue_level'] = U.venue.map(VL); U['venue_step'] = U.venue_level - U.groupby('horse').venue_level.shift()
x = x.merge(U.drop(columns=['date', 'venue', 'venue_level']), on=['race_id', 'horse'], how='left')
x['hsd_x_rel'] = x.h_sd * (x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')); x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['rating_uncertainty'] = x.dyn_nat_sd
TERMS = ['below_top3', 'gap_long_z', 'short_vs_long', 'slope15', 'neg_run', 'recent_var_ratio', 'hsd_x_rel', 'early_prep_vs_usual', 'quick_today', 'venue_step', 'recentform_x_established', 'light_weight', 'log_runs_held', 'rating_uncertainty']
yr = x.meeting_date.dt.year
def fit(mask, offcol):
    m = pd.Series(mask.values, index=x.index); z = L.prep_z(x.copy(), TERMS, m)
    sds = {c: float(((pd.to_numeric(x[c], errors='coerce') - pd.to_numeric(x[c], errors='coerce').groupby(x.race_id).transform('mean')).fillna(0.0))[m].std()) for c in TERMS}
    b = L.clogit_fit(z, TERMS, m, z[offcol].values, 30.0); return b, sds, z
b_dev, sd_dev, z_dev = fit(yr <= 2024, 'v2_dev')
b_all, sd_all, _ = fit(yr <= 2026, 'v2_all')
# out-of-sample chances for 2025-26 from the dev fit (for calibration and the record)
e = z_dev.v2_dev.values + z_dev[[c + '_z' for c in TERMS]].values @ b_dev; ev = (yr >= 2025).values
o = x.loc[ev, ['race_id', 'meeting_id', 'win', 'field', 'state']].copy(); o['e'] = e[ev]; mx = o.groupby('race_id').e.transform('max'); o['p'] = np.exp(o.e - mx); o['p'] /= o.groupby('race_id').p.transform('sum')
o['kind'] = 'NSW_VIC_ACT'; o.to_parquet('/tmp/v22_oos.parquet')
ALIAS = {'caulfield-heath': 'caulfield', 'sandown-hillside': 'sandown', 'sandown-lakeside': 'sandown', 'randwick-kensington': 'randwick', 'kensington': 'randwick', 'royal-randwick': 'randwick',
         'the-valley': 'moonee-valley', 'beaumont-newcastle': 'newcastle', 'newcastle-beaumont': 'newcastle', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill', 'canterbury-park': 'canterbury',
         'pakenham-synthetic': 'pakenham', 'ballarat-synthetic': 'ballarat', 'geelong-synthetic': 'geelong', 'sunshine-coast-poly-track': 'sunshine-coast',
         'mt-barker': 'mount-barker', 'mt-gambier': 'mount-gambier', 'devonport-synthetic': 'devonport', 'devonport-tapeta': 'devonport'}
v = pd.read_csv('b10/out/t10b.csv'); val = v[(v.label == 'bundle ridge 30.0')].set_index('stage')
MANI = {'engine_release': 'Engine v2.2', 'released': '2026-11-25 (live from the 26 Nov 2026 7:30am run)', 'approved_by': 'Damo, 25 Nov 2026 (chat): replace from tomorrow',
        'applies_to': ['NSW', 'VIC', 'ACT', 'SA', 'WA', 'TAS'], 'not_applied_to': 'QLD (stays Engine v2.1)', 'base': 'Engine v2 NSW_VIC_ACT family score (benchmarks/engine_v2_1/manifest.json, unchanged)',
        'terms': TERMS, 'coef_per_sd_all_races': dict(zip(TERMS, map(float, b_all))), 'term_sd_all_races': sd_all, 'coef_per_sd_dev_fit': dict(zip(TERMS, map(float, b_dev))), 'term_sd_dev_fit': sd_dev,
        'ridge': 30.0, 'constants': {'pop_var_surprise_kg2': float(x.attrs.get('pop_var', 0)) or 5.51 ** 2, 'h_sd_shrink_runs': 5, 'prep_gap_days': 60, 'quick_days': 10, 'light_weight_kg': 54, 'established_runs': 15},
        'term_families': {'Career shape and consistency': ['below_top3', 'gap_long_z', 'short_vs_long', 'slope15', 'neg_run', 'recent_var_ratio', 'hsd_x_rel', 'log_runs_held', 'rating_uncertainty', 'recentform_x_established', 'early_prep_vs_usual'],
                          'Weight, spacing and venue class': ['light_weight', 'quick_today', 'venue_step']},
        'venue_level_kg': {k: float(vv) for k, vv in VL.items()}, 'venue_alias': ALIAS,
        'evidence': {'discovery_fit2023_judge2024': {k: float(val.loc['discovery', k]) for k in ['gain', 'lo95', 'hi95', 'gain_east', 'gain_west', 'top_pick_pts']},
                     'validation_fit2024_judge2025_26': {k: float(val.loc['validation', k]) for k in ['gain', 'lo95', 'hi95', 'gain_east', 'gain_west', 'top_pick_pts']},
                     'status': 'research-period only: 2025-26 examined repeatedly; first untouched evidence = races from 26 Nov 2026'}}
import dyn_rating  # noqa (presence check)
pv = pd.read_parquet('engine/frames/national.parquet', columns=['date', 'dyn_nat_inn']); MANI['constants']['pop_var_surprise_kg2'] = float(pv[pv.date < '2025-01-01'].dyn_nat_inn.var())
json.dump(MANI, open('benchmarks/engine_v2_2/manifest.json', 'w'), indent=1)
print('all-races coefs', {k: round(v_, 4) for k, v_ in MANI['coef_per_sd_all_races'].items()}); print('dev coefs', {k: round(v_, 4) for k, v_ in MANI['coef_per_sd_dev_fit'].items()})
