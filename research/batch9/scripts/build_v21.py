"""Engine v2.1 (Queensland): v3 rating (engine/dyn_v3.py, settings chosen on pre-2025 runs) replaces the national rating
inside the Queensland v2 model. Refit v1 coefficients (development races), then v2 terms on top (penalty 100, as v2.0).
Gate: must beat Queensland v2.0 on identical 2025-26 races and in 2026 alone. Writes the manifests only if it passes."""
import json, copy, numpy as np, pandas as pd, hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(21)
F3 = pd.read_parquet('/tmp/exp/rt/national_v3.parquet')
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; COLS = list(E.QCOEF)
def model(frame, v1coef=None):
    x = E.qld_frame(frame); x = E.zcols(x, COLS); dev = (x.period == 'development'); ev = x.period == 'evaluation'
    b1 = E.fit(x, COLS, dev) if v1coef is None else np.array([v1coef[c] for c in COLS])
    off = E.eta(x, COLS, b1); x = build_terms(x, QT)
    b2 = fitd(x, QT, dev, off, 100); e = off + x[['t::' + t for t in QT]].values @ b2
    return x, b1, b2, off, e, dev, ev
# current v2.0 Queensland (frozen v1 coefficients, v2 terms dev-fit as released)
xc = E.qld_frame(U); xc = build_terms(xc, QT); offc = offset_v1(xc, 'qld'); bdc = np.array([MAN['families']['QLD']['coef_per_term_sd_dev_fit'][t] for t in QT])
ec = offc + xc[['t::' + t for t in QT]].values @ bdc; evc = xc.period == 'evaluation'
x3, b1, b2, off3, e3, dev3, ev3 = model(F3)
mc = E.metrics(xc, ec, evc); m3 = E.metrics(x3, e3, ev3)
d = E.diff(mc, m3); d26 = E.diff(mc[mc.date.dt.year == 2026], m3[m3.date.dt.year == 2026])
print('v2.1 vs v2.0, Qld 2025-26:', {k: v for k, v in d.items()}); print('2026 only:', {k: v for k, v in d26.items()})
print('v2.0', E.summary(mc)); print('v2.1', E.summary(m3))
ok = d['lp_lo'] > 0 and d26['lp'] > 0
json.dump({'gate_passed': bool(ok), 'vs_v2_0': d, 'vs_v2_0_2026': d26, 'v2_0': E.summary(mc), 'v2_1': E.summary(m3)}, open('/tmp/exp/rt/v21_gate.json', 'w'), indent=1, default=float)
if not ok: raise SystemExit('GATE FAILED: v2.1 does not beat v2.0 on 2025-26 and 2026; nothing written')
# production pieces, same conventions as v2.0: v1 coefficients from development races; v2 terms refit on all races
allm = pd.Series(True, index=x3.index); b2all = fitd(x3, QT, allm, off3, 100)
dvx = x3[dev3]
bsd = {c: float((dvx[c].astype(float) - dvx.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())).std()) for c in sorted(set(QT) | {'dyn_nat'}) if c in dvx}
tsd = {}
for n in QT:
    t = pd.Series(np.nan_to_num(np.asarray(x3[n + '_z'] if n + '_z' in x3 else x3[n], dtype=float)), index=x3.index); t = t - t.groupby(x3.race_id).transform('mean'); tsd[n] = float(t[dev3].std() or 1.0)
fdm = x3.groupby('race_id').dyn_nat.transform('mean')
v1c = {c: float(b) for c, b in zip(COLS, b1)}
cand = json.load(open('benchmarks/candidates_b4_national/manifest.json')); cand3 = copy.deepcopy(cand)
cand3.update({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'candidate': 'combined_v1 + national dynamic rating (v3 rating)', 'coefficients_per_dev_sd': v1c,
              'rating_runner': 'engine/dyn_v3.py', 'rating_settings': json.load(open('/tmp/exp/rt/tune_v3_choice.json')), 'dyn_nat_dev_sd_after_race_centring': bsd['dyn_nat'],
              'coefficients_fit_on': 'development races (before 2025-01-01), v3 rating frame'})
import os; os.makedirs('benchmarks/candidates_b4_national_v3', exist_ok=True); json.dump(cand3, open('benchmarks/candidates_b4_national_v3/manifest.json', 'w'), indent=1)
M = copy.deepcopy(MAN); Q = M['families']['QLD']
Q.update({'v1_offset': 'benchmarks/candidates_b4_national_v3 (combined_v1 + national rating, v3 rating)', 'coef_per_term_sd_all_races': {t: float(b) for t, b in zip(QT, b2all)},
          'coef_per_term_sd_dev_fit': {t: float(b) for t, b in zip(QT, b2)}, 'base_feature_dev_sd': {**Q['base_feature_dev_sd'], **bsd}, 'term_dev_sd': tsd,
          'context': {'field_dyn_mean': float(fdm[dev3].mean()), 'field_dyn_sd': float(fdm[dev3].std())}, 'score_per_kg_total': float(v1c['dyn_nat'] / bsd['dyn_nat'])})
M['released_utc'] = pd.Timestamp.now(tz='UTC').isoformat(); M['version'] = 'Engine v2.1 (Queensland: v3 rating); NSW/Vic/ACT as v2.0'
M['rule'] = 'Queensland uses the v3 rating from 25 Nov 2026 (approved by Damo); NSW/Vic/ACT unchanged. Evidence: research/batch9 (re-used 2025-26 data).'
os.makedirs('benchmarks/engine_v2_1', exist_ok=True); json.dump(M, open('benchmarks/engine_v2_1/manifest.json', 'w'), indent=1)
print('written; dyn_nat dev sd', bsd['dyn_nat'], 'score per kg', Q['score_per_kg_total'])
