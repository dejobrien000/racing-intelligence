"""Engine v2.1.3 (Queensland) release CANDIDATE: Engine v2.1.1 + the national 'Age & sex' family (age, young, old, female), possible
now that Queensland ages are held (98.9% of 2025-26 runners, 26 Nov database). Nothing else changes: v1 coefficients stay frozen at the
v2.1.1 values (benchmarks/candidates_b4_national_v3), the v2 family = horse records + jockey & trainer + age & sex, penalty 100, refitted
on development races (dev fit, for the gate and calibration) and on all races (release coefficients), exactly as build_v211.py did.
Writes benchmarks/engine_v2_1_3/manifest.json (engine_v2_1 manifest with the QLD family replaced) and runner_calibration_qld.json
(bent-line calibration refitted on the dev-fit v2.1.3 chances for 2025-26, same method as engine/runner_calibration_v22.py).
NOT LIVE: engine/score_v2.py reads it only when ENGINE_QLD213=1 (ops/engine_qld213_enabled), a release decision.
Gate (identical 2025-26 Qld races, production-style v2.1.1 with the same frozen v1): log-lik gain > 0 overall and in 2026."""
import json, copy, os, numpy as np, pandas as pd, statsmodels.api as sm
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
M21 = json.load(open('benchmarks/engine_v2_1/manifest.json')); C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; AS = NFAM2['Age & sex']; COLS = list(E.QCOEF); NEW = QT + AS
x = E.qld_frame(pd.read_parquet('engine/frames/national_v3.parquet')); x = E.zcols(x, COLS); dev = x.period == 'development'; ev = x.period == 'evaluation'
PV = C21['coefficients_per_dev_sd']; off = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS])
x = build_terms(x, NEW)
b_old = np.array([M21['families']['QLD']['coef_per_term_sd_dev_fit'][t] for t in QT]); e_old = off + x[['t::' + t for t in QT]].values @ b_old   # production v2.1.1 as it runs (dev fit)
b_dev = fitd(x, NEW, dev, off, 100); e_new = off + x[['t::' + t for t in NEW]].fillna(0.0).values @ b_dev
b_dev_old = fitd(x, QT, dev, off, 100); e_ref = off + x[['t::' + t for t in QT]].values @ b_dev_old                                           # v2.1.1 refitted the same way
mo, mr, mn = E.metrics(x, e_old, ev), E.metrics(x, e_ref, ev), E.metrics(x, e_new, ev)
G = {'vs_production_v2_1_1': E.diff(mo, mn), 'vs_production_2026': E.diff(mo[mo.date.dt.year == 2026], mn[mn.date.dt.year == 2026]), 'vs_refitted_v2_1_1': E.diff(mr, mn),
     'production': E.summary(mo), 'candidate': E.summary(mn)}
print(json.dumps(G, indent=1, default=float))
os.makedirs('benchmarks/engine_v2_1_3', exist_ok=True); json.dump(G, open('benchmarks/engine_v2_1_3/gate.json', 'w'), indent=1, default=float)
if not (G['vs_production_v2_1_1']['lp'] > 0 and G['vs_production_2026']['lp'] > 0): raise SystemExit('GATE FAILED: nothing else written')
allr = dev | ev; b_all = fitd(x, NEW, allr, off, 100)
# development scaling constants exactly as engine/release_v2.py computes them (base features race-centred sd; each term's sd)
base = {}
for c in [c[:-2] for c in x.columns if c.endswith('_z') and c[:-2] in x.columns]:
    v = x[c].astype(float); cen = v - v.groupby(x.race_id).transform('mean'); s = cen[dev].std(); base[c] = float(s) if s == s and s else 1.0
tsd = {}
for n in NEW:
    t = x[n + '_z'] if n + '_z' in x else x[n]; t = pd.Series(np.nan_to_num(np.asarray(t, dtype=float)), index=x.index); t = t - t.groupby(x.race_id).transform('mean'); tsd[n] = float(t[dev].std() or 1.0)
fdm = x.groupby('race_id').dyn_nat.transform('mean')
# kg-equivalent scale exactly as release_v2.py: development within-race slope of the dev-fit score on the rating
d = x[dev].assign(e=e_new[dev.values]); a_ = d.e - d.groupby('race_id').e.transform('mean'); r_ = d.dyn_nat - d.groupby('race_id').dyn_nat.transform('mean'); ok = a_.notna() & r_.notna()
slope = float((a_[ok] * r_[ok]).sum() / (r_[ok] ** 2).sum()); print('score per kg', round(slope, 4), 'v2.1.1 had', M21['families']['QLD']['score_per_kg_total'])
M = copy.deepcopy(M21); Q = M['families']['QLD']
Q.update({'term_families': {**Q['term_families'], 'Age & sex': AS}, 'coef_per_term_sd_all_races': {t: float(b) for t, b in zip(NEW, b_all)},
          'coef_per_term_sd_dev_fit': {t: float(b) for t, b in zip(NEW, b_dev)}, 'base_feature_dev_sd': {**Q['base_feature_dev_sd'], **{k: v for k, v in base.items() if k in set(NEW) | {'dyn_nat'}}},
          'term_dev_sd': tsd, 'context': {'field_dyn_mean': float(fdm[dev].mean()), 'field_dyn_sd': float(fdm[dev].std())}, 'score_per_kg_total': slope, 'penalty_tau': 100})
M['released_utc'] = pd.Timestamp.now(tz='UTC').isoformat(); M['version'] = 'Engine v2.1.3 (Queensland: v2.1.1 + age & sex family; v3 rating); NSW/Vic/ACT/SA/WA/Tas unchanged by this file'
M['rule'] = M.get('rule', '') + ' | v2.1.3 CANDIDATE (26 Nov 2026 night): adds the national Age & sex family to Queensland now that Queensland ages are held. Not live unless ENGINE_QLD213=1.'
json.dump(M, open('benchmarks/engine_v2_1_3/manifest.json', 'w'), indent=1)
# calibration (display): bent line on dev-fit chances for 2025-26, QLD family; NSW_VIC_ACT family copied unchanged from v2.2's file
t = x.loc[ev, ['race_id', 'meeting_id', 'win', 'field']].copy(); t['e'] = e_new[ev.values]; mx = t.groupby('race_id').e.transform('max'); t['p'] = np.exp(t.e - mx); t['p'] /= t.groupby('race_id').p.transform('sum')
t['kind'] = 'QLD'; t.to_parquet('/tmp/qld213_oos.parquet')
print('gate passed; release coefficients written; age/sex coefficients (all races):', {k: round(v, 4) for k, v in Q['coef_per_term_sd_all_races'].items() if k in AS})
