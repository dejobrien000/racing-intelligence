"""CANDIDATE ONLY (27 Nov 2026, Batch 15 brief s1): Engine v2.3 third layer + handicap weight slope (wt_x_hcp = weight vs field x benchmark race).
Run in the v2.3 build sandbox (/tmp/c2/research: Engine v2.3 frames). Fits the 14 v2.3 terms with and without wt_x_hcp, same rule as the release
(all races for production coefficients; dev fit for evidence). Writes benchmarks/engine_v2_4_candidate/ only. Original docstring: Build the Engine v2.2 release files (approved by Damo 25 Nov 2026: 'Replace from tomorrow').
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
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'f_avgfp3', 'weight_kg', 'dyn_nat_sd', 'a_wt_rel', 'class_label'])
VL = pd.read_csv('b10/out/venue_strength.csv').groupby('venue').field_mean.mean()
U = U.sort_values(['horse', 'date']); U['venue_level'] = U.venue.map(VL); U['venue_step'] = U.venue_level - U.groupby('horse').venue_level.shift()
x = x.merge(U.drop(columns=['date', 'venue', 'venue_level']), on=['race_id', 'horse'], how='left')
x['hsd_x_rel'] = x.h_sd * (x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')); x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['rating_uncertainty'] = x.dyn_nat_sd
TERMS0 = ['below_top3', 'gap_long_z', 'short_vs_long', 'slope15', 'neg_run', 'recent_var_ratio', 'hsd_x_rel', 'early_prep_vs_usual', 'quick_today', 'venue_step', 'recentform_x_established', 'light_weight', 'log_runs_held', 'rating_uncertainty']
HCP_CLASSES = ['Benchmark', 'BM', 'Open/Hcp']   # as preregistered in the harness (only 'Benchmark' occurs in the data)
x['wt_x_hcp'] = x.a_wt_rel * x.class_label.isin(HCP_CLASSES).astype(float)
TERMS = TERMS0 + ['wt_x_hcp']
yr = x.meeting_date.dt.year
def fit(mask, offcol, TERMS=TERMS):
    m = pd.Series(mask.values, index=x.index); z = L.prep_z(x.copy(), TERMS, m)
    sds = {c: float(((pd.to_numeric(x[c], errors='coerce') - pd.to_numeric(x[c], errors='coerce').groupby(x.race_id).transform('mean')).fillna(0.0))[m].std()) for c in TERMS}
    b = L.clogit_fit(z, TERMS, m, z[offcol].values, 30.0); return b, sds, z
import os
def gain(e0, e1, ev):
    o = x.loc[ev, ['race_id', 'win']].copy(); r = []
    for e in (e0, e1):
        o['e'] = e[ev]; mx = o.groupby('race_id').e.transform('max'); p = np.exp(o.e - mx); p = p / p.groupby(o.race_id).transform('sum'); r.append(np.log(p[o.win == 1].values))
    d = r[1] - r[0]; rng = np.random.default_rng(7); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    return {'races': int(len(d)), 'gain': float(d.mean()), 'lo95': float(np.percentile(bs, 2.5)), 'hi95': float(np.percentile(bs, 97.5))}
EV = {}
for lab, fitmask, evmask in [('fit_to_2023_judge_2024', yr <= 2023, (yr == 2024).values), ('fit_to_2024_judge_2025_26', yr <= 2024, (yr >= 2025).values)]:
    b0, s0, z0 = fit(fitmask, 'v2_dev', TERMS0); b1, s1, z1 = fit(fitmask, 'v2_dev', TERMS)
    e0 = z0.v2_dev.values + z0[[c + '_z' for c in TERMS0]].values @ b0; e1 = z1.v2_dev.values + z1[[c + '_z' for c in TERMS]].values @ b1
    EV[lab] = gain(e0, e1, evmask); EV[lab]['wt_x_hcp_coef_per_sd'] = float(b1[-1]); print(lab, EV[lab], flush=True)
    if lab == 'fit_to_2024_judge_2025_26':
        o = x.loc[evmask, ['race_id', 'horse', 'meeting_date', 'state', 'win', 'class_label', 'a_wt_rel']].copy(); o['e0'] = e0[evmask]; o['e1'] = e1[evmask]; o.to_parquet('/tmp/v24c_oos.parquet')
b_dev, sd_dev, z_dev = fit(yr <= 2024, 'v2_dev')
b_all, sd_all, _ = fit(yr <= 2026, 'v2_all')

V23 = json.load(open('benchmarks/engine_v2_2/manifest.json'))     # sandbox = the Engine v2.3 third layer (copied to the repo as benchmarks/engine_v2_3/engine_v2_2.json)
MANI = dict(V23); MANI.update({'engine_release': 'Engine v2.4 CANDIDATE (not live): Engine v2.3 + handicap weight slope', 'released': None, 'approved_by': None,
    'base': 'Engine v2.3 (benchmarks/engine_v2_3): its v1 and v2 layers unchanged; this third layer replaces engine_v2_3/engine_v2_2.json',
    'terms': TERMS, 'coef_per_sd_all_races': dict(zip(TERMS, map(float, b_all))), 'term_sd_all_races': sd_all, 'coef_per_sd_dev_fit': dict(zip(TERMS, map(float, b_dev))), 'term_sd_dev_fit': sd_dev,
    'hcp_classes': HCP_CLASSES, 'hcp_definition': 'wt_x_hcp = (weight carried - race mean weight carried) x 1[race class is Benchmark]; class from TAB raceClassConditions at scoring time (BMnn -> Benchmark)',
    'evidence': {**EV, 'note': 'every term refitted with and without wt_x_hcp on identical races; 2024 contributed to the harness discovery of this term (Batch 12 preregistered it on 2024), 2025-26 examined repeatedly'}})
MANI['term_families'] = {k: list(v) for k, v in V23['term_families'].items()}; MANI['term_families']['Weight, spacing and venue class'] = MANI['term_families']['Weight, spacing and venue class'] + ['wt_x_hcp']
os.makedirs('benchmarks/engine_v2_4_candidate', exist_ok=True); json.dump(MANI, open('benchmarks/engine_v2_4_candidate/engine_v2_2.json', 'w'), indent=1)
print('all-races coefs', {k: round(v_, 4) for k, v_ in MANI['coef_per_sd_all_races'].items()})
print('v2.3 all-races coefs', {k: round(v_, 4) for k, v_ in V23['coef_per_sd_all_races'].items()})
