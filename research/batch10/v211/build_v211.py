"""Engine v2.1.1 (Queensland): same model as v2.1 (v3 rating, v1 coefficients refit on development races, v2 terms penalty 100), refitted
on the database that adds Breednet Queensland country meetings (915 meetings not covered by RQ tracking) and Qld ages.
Gate: must beat CURRENT v2.1 on identical 2025-26 Queensland races (log-lik CI above 0... or at least >0 overall and in 2026).
Run from the sandbox research/ with NEW frames in engine/frames and the CURRENT v2.1 frame at /tmp/nat3/research/engine/frames/national_v3.parquet."""
import json, copy, os, numpy as np, pandas as pd, hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN0 = json.load(open('benchmarks/engine_v2/manifest.json')); M21 = json.load(open('benchmarks/engine_v2_1/manifest.json')); C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; COLS = list(E.QCOEF)
def model(frame, v1coef=None, v2coef=None):
    x = E.qld_frame(frame); x = E.zcols(x, COLS); dev = (x.period == 'development'); ev = x.period == 'evaluation'
    b1 = E.fit(x, COLS, dev) if v1coef is None else np.array([v1coef[c] for c in COLS])
    off = E.eta(x, COLS, b1); x = build_terms(x, QT)
    b2 = fitd(x, QT, dev, off, 100) if v2coef is None else np.array([v2coef[t] for t in QT]); e = off + x[['t::' + t for t in QT]].values @ b2
    return x, b1, b2, off, e, dev, ev
Fcur = pd.read_parquet('/tmp/nat3/research/engine/frames/national_v3.parquet'); Fnew = pd.read_parquet('engine/frames/national_v3.parquet')
xc, _, _, _, ec, _, evc = model(Fcur, C21['coefficients_per_dev_sd'], M21['families']['QLD']['coef_per_term_sd_dev_fit'])
xn, b1, b2, offn, en, devn, evn = model(Fnew)
mc = E.metrics(xc, ec, evc); mn = E.metrics(xn, en, evn)
d = E.diff(mc, mn); d26 = E.diff(mc[mc.date.dt.year == 2026], mn[mn.date.dt.year == 2026])
print('v2.1.1 vs current v2.1, Qld 2025-26:', d); print('2026 only:', d26); print('v2.1', E.summary(mc)); print('v2.1.1', E.summary(mn))
ok = d['lp'] > 0 and d26['lp'] > 0
json.dump({'gate_passed': bool(ok), 'vs_v2_1': d, 'vs_v2_1_2026': d26, 'v2_1': E.summary(mc), 'v2_1_1': E.summary(mn)}, open('/tmp/natq/v211/gate.json', 'w'), indent=1, default=float)
if not ok: raise SystemExit('GATE FAILED: nothing written')
allm = pd.Series(True, index=xn.index); b2all = fitd(xn, QT, allm, offn, 100); dvx = xn[devn]
bsd = {c: float((dvx[c].astype(float) - dvx.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())).std()) for c in sorted(set(QT) | {'dyn_nat'}) if c in dvx}
tsd = {}
for n in QT:
    t = pd.Series(np.nan_to_num(np.asarray(xn[n + '_z'] if n + '_z' in xn else xn[n], dtype=float)), index=xn.index); t = t - t.groupby(xn.race_id).transform('mean'); tsd[n] = float(t[devn].std() or 1.0)
fdm = xn.groupby('race_id').dyn_nat.transform('mean'); v1c = {c: float(b) for c, b in zip(COLS, b1)}
c3 = copy.deepcopy(C21); c3.update({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'engine_release': 'Engine v2.1.1', 'coefficients_per_dev_sd': v1c, 'dyn_nat_dev_sd_after_race_centring': bsd['dyn_nat'],
                                     'coefficients_fit_on': 'development races (before 2025-01-01), v3 rating frame incl. Breednet Queensland country meetings (database master-2026-11-24-qld)'})
M = copy.deepcopy(M21); Q = M['families']['QLD']
Q.update({'coef_per_term_sd_all_races': {t: float(b) for t, b in zip(QT, b2all)}, 'coef_per_term_sd_dev_fit': {t: float(b) for t, b in zip(QT, b2)}, 'base_feature_dev_sd': {**Q['base_feature_dev_sd'], **bsd},
          'term_dev_sd': tsd, 'context': {'field_dyn_mean': float(fdm[devn].mean()), 'field_dyn_sd': float(fdm[devn].std())}})   # score_per_kg_total kept (same rule as v2.1)
M['released_utc'] = pd.Timestamp.now(tz='UTC').isoformat(); M['version'] = 'Engine v2.1.1 (Queensland: v3 rating, refitted with Queensland country history); NSW/Vic/ACT as v2.0 (+ v2.2 terms)'
M['rule'] = M.get('rule', '') + ' | v2.1.1 (approved by Damo 25 Nov 2026: refit tonight, live 26 Nov): same model refitted on the database with Breednet Queensland country meetings.'
json.dump(c3, open('benchmarks/candidates_b4_national_v3/manifest.json', 'w'), indent=1); json.dump(M, open('benchmarks/engine_v2_1/manifest.json', 'w'), indent=1)
print('written; dyn_nat dev sd', bsd['dyn_nat'], 'v1 coefs', {k: round(v, 3) for k, v in v1c.items()})
