"""CANDIDATE ONLY (Batch 28 item 3 + amendment, 28 Nov 2026): third layer of the COMBINED NATIONAL CANDIDATE, built through the release chain.
Combined = consolidated rating (Engine v2.5) + distance-specific suitability REPLACING the distance record (layers 1-2, DREC_SOURCE=dspec)
         + handicap weight slope (wt_x_hcp) + trainer debut record (tr_debut_g) + sire debut record (sire_debut_x) in the third layer.
Run inside the combined sandbox (/tmp/cmb/research) AFTER the dspec frame, freeze (DREC_SOURCE=dspec + Engine v2.5 rating settings) and
engine/release_v2.py. Same rule as the releases: production coefficients fitted on all races, dev fit (<2025) for the evidence.
Built check (2025-26, dev-fit chances, races not used to fit any layer): ladder on identical races
  L0 Engine v2.5 as built (/tmp/cc/out/v22_oos.parquet)   L1 + distance replacement (14 terms)   L2 + handicap slope   L3 + both debut terms
Writes <sandbox>/out_combined/{engine_v2_2.json, built_check.json, oos.parquet}. Debut terms from batch28/b28_debut_terms.py (serving parity)."""
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
DEB, V25OOS = sys.argv[1], sys.argv[2]
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
x = x.merge(U.drop(columns=['date', 'venue', 'venue_level']).drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
x['hsd_x_rel'] = x.h_sd * (x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean')); x['recentform_x_established'] = x.f_avgfp3 * (x.n_prior >= 15)
x['light_weight'] = (x.weight_kg <= 54).astype(float).where(x.weight_kg.notna()); x['log_runs_held'] = np.log1p(x.n_prior); x['rating_uncertainty'] = x.dyn_nat_sd
TERMS0 = ['below_top3', 'gap_long_z', 'short_vs_long', 'slope15', 'neg_run', 'recent_var_ratio', 'hsd_x_rel', 'early_prep_vs_usual', 'quick_today', 'venue_step', 'recentform_x_established', 'light_weight', 'log_runs_held', 'rating_uncertainty']
HCP_CLASSES = ['Benchmark', 'BM', 'Open/Hcp']
x['wt_x_hcp'] = x.a_wt_rel * x.class_label.isin(HCP_CLASSES).astype(float)
x = x.merge(pd.read_parquet(DEB), on=['race_id', 'horse'], how='left'); x[['tr_debut_g', 'sire_debut_x']] = x[['tr_debut_g', 'sire_debut_x']].fillna(0.0)
LAD = [('L1 distance replacement (14 terms)', TERMS0), ('L2 + handicap weight slope', TERMS0 + ['wt_x_hcp']), ('L3 + trainer and sire debut', TERMS0 + ['wt_x_hcp', 'tr_debut_g', 'sire_debut_x'])]
TERMS = LAD[-1][1]; yr = x.meeting_date.dt.year
def fit(mask, offcol, T_):
    m = pd.Series(mask.values, index=x.index); z = L.prep_z(x.copy(), T_, m)
    sds = {c: float(((pd.to_numeric(x[c], errors='coerce') - pd.to_numeric(x[c], errors='coerce').groupby(x.race_id).transform('mean')).fillna(0.0))[m].std()) for c in T_}
    b = L.clogit_fit(z, T_, m, z[offcol].values, 30.0); return b, sds, z
def lp(e, ev):
    o = x.loc[ev, ['race_id', 'horse', 'win']].copy(); o['e'] = e[ev]; mx = o.groupby('race_id').e.transform('max'); p = np.exp(o.e - mx); p = p / p.groupby(o.race_id).transform('sum')
    o['p'] = p; return o
def gain(d):
    rng = np.random.default_rng(7); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    return {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'lo95': round(float(np.percentile(bs, 2.5)), 5), 'hi95': round(float(np.percentile(bs, 97.5)), 5)}
ev = (yr >= 2025).values; OUT = {'ladder_2025_26': {}}; P = {}
for lab, T_ in LAD:
    b, s_, z = fit(yr <= 2024, 'v2_dev', T_); e = z.v2_dev.values + z[[c + '_z' for c in T_]].values @ b
    o = lp(e, ev); P[lab] = o; OUT['ladder_2025_26'][lab] = {'coef_per_sd_dev_fit': dict(zip(T_, map(lambda v_: round(float(v_), 4), b)))}
    print(lab, 'fitted', flush=True)
# L0 = Engine v2.5 as built; compare on identical races (winner rows)
V = pd.read_parquet(V25OOS); pc = 'p' if 'p' in V else [c for c in V.columns if c.startswith('p')][0]
W = {lab: o[o.win == 1][['race_id', 'p']].rename(columns={'p': lab}) for lab, o in P.items()}
base = V[V.win == 1][['race_id', pc]].rename(columns={pc: 'L0 Engine v2.5 built'}) if 'win' in V else None
M_ = base
for lab in W: M_ = M_.merge(W[lab], on='race_id')
cols = ['L0 Engine v2.5 built'] + [l for l, _ in LAD]
for a_, b_ in zip(cols[:-1], cols[1:]): OUT['ladder_2025_26'].setdefault(b_, {})['vs_previous_step'] = gain(np.log(M_[b_].values) - np.log(M_[a_].values))
OUT['combined_vs_v25_built'] = gain(np.log(M_[cols[-1]].values) - np.log(M_[cols[0]].values))
for s_ in ['QLD', 'NSW', 'VIC', 'SA', 'WA', 'TAS']:
    ids = set(x.loc[ev & (x.state == s_).values, 'race_id'])
    mm = M_[M_.race_id.isin(ids)]
    if len(mm) > 200: OUT.setdefault('combined_vs_v25_by_state', {})[s_] = gain(np.log(mm[cols[-1]].values) - np.log(mm[cols[0]].values))
os.makedirs('out_combined', exist_ok=True); P[LAD[-1][0]].to_parquet('out_combined/oos.parquet')
b_all, sd_all, _ = fit(yr <= 2026, 'v2_all', TERMS); b_dev, sd_dev, _ = fit(yr <= 2024, 'v2_dev', TERMS)
V25 = json.load(open('/home/claude/racing-intelligence/research/benchmarks/engine_v2_5/engine_v2_2.json'))
MANI = {k: v for k, v in V25.items() if k != 'candidate_record'}
MANI.update({'engine_release': 'Combined national candidate (NOT LIVE): Engine v2.5 + distance suitability (replacing the distance record) + handicap weight slope + trainer and sire debut records',
    'released': None, 'approved_by': None, 'base': 'Engine v2.5 (benchmarks/engine_v2_5); v1 and v2 layers rebuilt with the distance record slot carrying distance-specific suitability',
    'terms': TERMS, 'coef_per_sd_all_races': dict(zip(TERMS, map(float, b_all))), 'term_sd_all_races': sd_all, 'coef_per_sd_dev_fit': dict(zip(TERMS, map(float, b_dev))), 'term_sd_dev_fit': sd_dev,
    'hcp_classes': HCP_CLASSES, 'hcp_definition': 'wt_x_hcp = (weight carried - race mean weight carried) x 1[race class is Benchmark]; class from TAB raceClassConditions at scoring time (BMnn -> Benchmark)',
    'evidence': OUT})
MANI['term_families'] = {k: list(v) for k, v in V25['term_families'].items()}
MANI['term_families']['Weight, spacing and venue class'] = MANI['term_families']['Weight, spacing and venue class'] + ['wt_x_hcp']
MANI['term_families']['Debut: trainer and sire records (candidate)'] = ['tr_debut_g', 'sire_debut_x']
os.makedirs('out_combined', exist_ok=True); json.dump(MANI, open('out_combined/engine_v2_2.json', 'w'), indent=1); json.dump(OUT, open('out_combined/built_check.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in OUT.items() if k != 'ladder_2025_26'}, indent=1)); print({k: v.get('vs_previous_step') for k, v in OUT['ladder_2025_26'].items()})
print('all-races coefs (new terms)', {k: round(float(v_), 4) for k, v_ in zip(TERMS, b_all) if k in ('wt_x_hcp', 'tr_debut_g', 'sire_debut_x')})
