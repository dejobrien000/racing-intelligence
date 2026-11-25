"""Batch 10 test runner (national, Engine v2 NSW/Vic family score held fixed; six states).
Stage 1 discovery (fit Oct22-Dec23, judge 2024) for every candidate -> Benjamini-Hochberg q<0.10 on discovery p-values.
Stage 2 validation (fit <2025, judge 2025-26) for discovery passers AND for the pre-specified re-runs of earlier findings.
Region split in every result: east (NSW/VIC/ACT) vs west (SA/WA/TAS, never used to build or screen anything)."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
b = L.base('nat'); F = pd.read_parquet('b10/out/feat.parquet').drop(columns=['date', 'state'])
x = b.merge(F, on=['race_id', 'horse'], how='left')
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'age_n', 'f_avgfp3', 'state', 'prev_state'])
U['vic_out'] = ((U.prev_state == 'VIC') & (U.state != 'VIC')).astype(float).where(U.prev_state.notna()); U['into_vic'] = ((U.prev_state != 'VIC') & (U.state == 'VIC')).astype(float).where(U.prev_state.notna())
U['interstate'] = (U.prev_state != U.state).astype(float).where(U.prev_state.notna())
vs = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
U = U.sort_values(['horse', 'date']); U['venue_level'] = U.venue.map(vs); U['venue_step'] = U.venue_level - U.groupby('horse').venue_level.shift()
x = x.merge(U[['race_id', 'horse', 'venue_step', 'age_n', 'f_avgfp3', 'vic_out', 'into_vic', 'interstate']], on=['race_id', 'horse'], how='left')
x['rel_rating'] = x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')
x['hsd_x_rel'] = x.h_sd * x.rel_rating                     # does a horse's own variability matter more for favourites or outsiders?
x['established'] = (x.n_prior >= 15).astype(float); x['recentform_x_established'] = x.f_avgfp3 * x.established
x['below_best_x_old'] = x.below_best * (x.age_n >= 7)
SECTIONS = {
 '5 career & variability': ['h_sd', 'hsd_x_rel', 'recent_var_ratio', 'strong_rate', 'weak_rate', 'gap_long', 'gap_long_z', 'short_vs_long', 'below_top3', 'isolated_peak', 'slope15', 'slope5', 'neg_run', 'steady_decline'],
 '6 preparations': ['prep_shape', 'runs_to_usual_peak', 'early_prep_vs_usual', 'dip_from_prep_best'],
 '7 workload': ['quick_today', 'isolated_quick', 'consec_quick', 'sched_A', 'sched_B', 'sched_C', 'starts_28d', 'starts_60d', 'metres_42d', 'prep_days', 'last_race_strength'],
 '8 trainer decisions': ['tdec_dist_up', 'tdec_dist_down', 'tdec_quick', 'tdec_long_break', 'tdec_class_up', 'tdec_class_down', 'tdec_jockey_change', 'dist_up_improving', 'dist_up_declining'],
 '9 dynamic jockey & trainer': ['jkey_recent', 'jkey_bad', 'jkey_good', 'j_recent_vs_career', 'tkey_recent', 'tkey_bad', 'tkey_good', 't_recent_vs_career']}
PRESPEC = {'re-run (Batch 9 B)': ['below_best', 'recentform_x_established', 'below_best_x_old'], 're-run (Batch 9 F)': ['opp_step', 'venue_step'],
           're-run (s11 shippers, found in 2023-24 residuals)': ['vic_out', 'into_vic', 'interstate']}
rows = []
for sec, cols in {**SECTIONS, **PRESPEC}.items():
    for c in cols:
        r = L.test(x, [c], c, 'discovery'); r['section'] = sec; rows.append(r); print(sec, {k: r[k] for k in ['label', 'gain', 'lo95', 'hi95', 'p', 'gain_west']}, flush=True)
D = pd.DataFrame(rows); new = ~D.section.str.startswith('re-run'); D['bh_pass'] = False; D.loc[new, 'bh_pass'] = L.bh(D.loc[new, 'p'].values, 0.10)
D.to_csv('b10/out/t10_discovery.csv', index=False)
val = D[D.bh_pass | ~new].label.tolist(); vrows = []
for c in val:
    r = L.test(x, [c], c, 'validation'); r['section'] = D.set_index('label').section[c]; vrows.append(r); print('VALIDATION', {k: r.get(k) for k in ['label', 'gain', 'lo95', 'hi95', 'gain_east', 'gain_west', 'west_lo', 'west_hi', 'top_pick_pts']}, flush=True)
V = pd.DataFrame(vrows); V.to_csv('b10/out/t10_validation.csv', index=False)
# joint: all validated new terms together (no double counting): does the bundle add more than the best single term?
ok = V[(V.lo95 > 0) & ~V.section.str.startswith('re-run')].label.tolist()
if len(ok) > 1:
    r = L.test(x, ok, 'joint: ' + '+'.join(ok), 'validation', ridge=1.0); r['section'] = 'joint'; pd.DataFrame([r]).to_csv('b10/out/t10_joint.csv', index=False); print('JOINT', r, flush=True)
