"""Batch 13 (26 Nov 2026, consolidation brief s5): Queensland v2.2 alignment.
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
F3 = pd.read_parquet('engine/frames/national_v3.parquet')
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
rows = []; coefs = {}
for win, (fit_end, lo, hi) in {'A: fit <2024, judge 2024': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B: fit <2025, judge 2025-26': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = x0.meeting_date < fit_end; em = (x0.meeting_date >= lo) & (x0.meeting_date < hi); res = {}
    def base(drop):
        cols = [c for c in ALL if c not in drop]; b1 = E.fit(x0, cols, fm); return E.eta(x0, cols, b1)
    for nm, drop, extra, add22 in [('1 v2.1.1', [], [], False), ('2 v2.1.2', ['f_lastfp'] + TRK, [], False), ('3 v2.1.1 + age & sex', [], AS, False),
                                   ('4 v2.1.1 + v2.2 terms', [], [], True), ('5 v2.1.1 + age & sex + v2.2', [], AS, True), ('6 v2.1.2 + age & sex + v2.2', ['f_lastfp'] + TRK, AS, True)]:
        off = base(drop); tt = QT + extra; b2 = fitd(x0, tt, fm, off, 100); e = off + x0[['t::' + t for t in tt]].fillna(0.0).values @ b2
        if add22: e, c22 = v22(x0, e, fm); coefs[(win, nm)] = c22
        res[nm] = E.metrics(x0, e, em); print(win, nm, E.summary(res[nm]), flush=True)
    # 7: common national framework on the same Qld tracked races (nat_v2 inputs from the v3 frame's common columns)
    xc = x0.copy(); NV = [c for c in E.NV2 if c in xc]; xc = E.zcols(xc, NV); allt = sum(NFAM2.values(), []); xc = build_terms(xc, allt)
    b1 = E.fit(xc, NV, fm); off = E.eta(xc, NV, b1); b2 = fitd(xc, allt, fm, off, 100); e = off + xc[['t::' + t for t in allt]].fillna(0.0).values @ b2; e, _ = v22(xc, e, fm)
    res['7 common national framework (Qld coefficients)'] = E.metrics(xc, e, em); print(win, '7 common', E.summary(res['7 common national framework (Qld coefficients)']), flush=True)
    for nm, r in res.items():
        if nm.startswith('1 '): continue
        d = E.diff(res['1 v2.1.1'], r); y26 = r.date.dt.year == 2026; d26 = E.diff(res['1 v2.1.1'][res['1 v2.1.1'].date.dt.year == 2026], r[y26]) if y26.any() else {}
        rows.append({'window': win, 'variant': nm, **E.summary(r), **{'vs_v211_' + k: v for k, v in d.items()}, 'lp_2026': d26.get('lp'), 'lp_2026_lo': d26.get('lp_lo'), 'lp_2026_hi': d26.get('lp_hi')})
    rows.append({'window': win, 'variant': '1 v2.1.1', **E.summary(res['1 v2.1.1'])})
O = pd.DataFrame(rows); print(O.to_string(index=False)); O.to_csv('batch13/out/qld_align.csv', index=False)
json.dump({f'{a} | {b}': v for (a, b), v in coefs.items()}, open('batch13/out/qld_align_v22_coefs.json', 'w'), indent=1)
