"""Batch 16 B11 (27 Nov 2026): Queensland configurations on one harness (copied from batch13/qld_align.py; variants 1, 3, 7 only).
Env F3 = rating frame (v3 structure), FEAT = its feat10 output, TAG = config name. Per-race results -> /tmp/qcfg/res_<TAG>_<variant>_<A|B>.parquet
for paired comparison across rating frames on identical races (batch16/b11_qld_compare.py). Research only.
Original header:
Same harness as batch11/qld_simplify_v211.py (Engine v2.1.1 structure on the v3 rating frame: v1 inputs refitted, v2 terms penalty 100),
then families added jointly on top. Windows: A = fit before 2024, judge 2024; B = fit before 2025, judge 2025-26 (re-used period).
Variants:
  1 v2.1.1 (as production)                          2 v2.1.2 (drop last-start finish + track/distance/going history)
  3 v2.1.1 + age & sex (Qld ages now held)          4 v2.1.1 + the 14 v2.2 terms (ridge 30 on top, as nationally)
  5 v2.1.1 + age & sex + v2.2                       6 v2.1.2 + age & sex + v2.2 (combined candidate)
  7 common national framework refitted on Qld tracked races (nat_v2 inputs + national v2 families incl. form changes/h2h + v2.2 terms),
    i.e. one structure with Queensland coefficients and NO Queensland-only physical inputs
v2.2 inputs for Qld rows come from batch10/scripts/feat10.py run on the v3 frame (FEAT env). No coefficient is copied from the national engine.
Writes batch13/out/qld_align.csv. Research only."""
import os, json, numpy as np, pandas as pd, hier_tools as H
import sys; sys.path.insert(0, 'batch10/scripts'); import lib10 as L
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; AS = NFAM2['Age & sex']; ALL = list(E.QCOEF)
TRK = E.QFAM['Track/distance/going history']
M22 = json.load(open('benchmarks/engine_v2_2/manifest.json')); T22 = M22['terms']
F3 = pd.read_parquet(os.environ.get('F3', 'engine/frames/national_v3.parquet')); TAG = os.environ.get('TAG', 'v3')
FE = pd.read_parquet(os.environ.get('FEAT', '/tmp/q3/b10/out/feat.parquet'))
x0 = E.qld_frame(F3); x0 = E.zcols(x0, ALL); x0 = build_terms(x0, QT + AS); x0['meeting_date'] = pd.to_datetime(x0.meeting_date)
# v2.2 raw terms for Qld rows (keyed by Qld race/horse ids), same definitions as build_v22.py; venue class: Qld venues are not in the national table -> no step (0)
fq = FE.dropna(subset=['q_race_id']).drop(columns=['race_id', 'horse'], errors='ignore').rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
x0 = x0.merge(fq[['race_id', 'horse_id'] + [c for c in fq.columns if c in T22 or c in ('h_sd', 'n_prior')]], on=['race_id', 'horse_id'], how='left', suffixes=('', '_f'))
U3 = F3[F3.state == 'QLD'].dropna(subset=['q_race_id'])[['q_race_id', 'q_horse_id', 'dyn_nat_sd', 'weight_kg', 'venue', 'date', 'horse']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
VL = pd.Series(M22['venue_level_kg']); U3 = U3.sort_values(['horse', 'date']); U3['vl'] = U3.venue.map(lambda v: M22['venue_alias'].get(v, v)).map(VL); U3['venue_step'] = U3.vl - U3.groupby('horse').vl.shift()
x0 = x0.merge(U3[['race_id', 'horse_id', 'dyn_nat_sd', 'venue_step']].rename(columns={'dyn_nat_sd': 'dyn_nat_sd_q'}), on=['race_id', 'horse_id'], how='left')
x0['hsd_x_rel'] = x0.h_sd * (x0.dyn_nat - x0.groupby('race_id').dyn_nat.transform('mean')); x0['recentform_x_established'] = x0.f_avgfp3 * (x0.n_prior >= 15)
x0['light_weight'] = (x0.weight_kg <= 54).astype(float).where(x0.weight_kg.notna()); x0['log_runs_held'] = np.log1p(x0.n_prior); x0['rating_uncertainty'] = x0.dyn_nat_sd_q
print('v2.2 inputs available on Qld rows:', {t: round(float(x0[t].notna().mean()), 3) for t in T22}, flush=True)
def v22(x, e, fm):
    z = L.prep_z(x.copy(), T22, pd.Series(fm.values, index=x.index)); b = L.clogit_fit(z, T22, pd.Series(fm.values, index=x.index), e, ridge=30.0)
    return e + z[[t + '_z' for t in T22]].values @ b, dict(zip(T22, map(float, b)))
os.makedirs('/tmp/qcfg', exist_ok=True)
for win, (fit_end, lo, hi) in {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = x0.meeting_date < fit_end; em = (x0.meeting_date >= lo) & (x0.meeting_date < hi)
    def base(drop):
        cols = [c for c in ALL if c not in drop]; b1 = E.fit(x0, cols, fm); return E.eta(x0, cols, b1)
    for nm, extra in [('1', []), ('3', AS)]:
        off = base([]); tt = QT + extra; b2 = fitd(x0, tt, fm, off, 100); e = off + x0[['t::' + t for t in tt]].fillna(0.0).values @ b2
        r = E.metrics(x0, e, em); r.to_parquet(f'/tmp/qcfg/res_{TAG}_{nm}_{win}.parquet'); print(TAG, win, nm, E.summary(r), flush=True)
    xc = x0.copy(); NV = [c for c in E.NV2 if c in xc]; xc = E.zcols(xc, NV); allt = sum(NFAM2.values(), []); xc = build_terms(xc, allt)
    b1 = E.fit(xc, NV, fm); off = E.eta(xc, NV, b1); b2 = fitd(xc, allt, fm, off, 100); e = off + xc[['t::' + t for t in allt]].fillna(0.0).values @ b2; e, _ = v22(xc, e, fm)
    r = E.metrics(xc, e, em); r.to_parquet(f'/tmp/qcfg/res_{TAG}_7_{win}.parquet'); print(TAG, win, '7 common', E.summary(r), flush=True)
    if os.environ.get('PHYS') == '1':   # Batch 17: the common framework PLUS Queensland's physical inputs (closing sectionals, barrier and race shape)
        PH = E.QFAM['Closing sectionals'] + E.QFAM['Barrier & race shape']; NVP = NV + [c for c in PH if c not in NV]; xc = E.zcols(xc, NVP)
        b1 = E.fit(xc, NVP, fm); off = E.eta(xc, NVP, b1); b2 = fitd(xc, allt, fm, off, 100); e = off + xc[['t::' + t for t in allt]].fillna(0.0).values @ b2; e, _ = v22(xc, e, fm)
        r = E.metrics(xc, e, em); r.to_parquet(f'/tmp/qcfg/res_{TAG}_8_{win}.parquet'); print(TAG, win, '8 common + physical', E.summary(r), flush=True)
