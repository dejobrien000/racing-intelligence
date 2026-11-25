"""Share of the Queensland (Engine v2.1.1) race-relative score from each kind of evidence, 2025-26 tracked races. cov share, within race."""
import json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))['coefficients_per_dev_sd']; M = json.load(open('benchmarks/engine_v2_1/manifest.json'))['families']['QLD']
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']
x = E.qld_frame(pd.read_parquet('engine/frames/national_v3.parquet')); x = E.zcols(x, list(E.QCOEF)); x = build_terms(x, QT); x['meeting_date'] = pd.to_datetime(x.meeting_date)
x = x[x.meeting_date.dt.year >= 2025].copy(); C = pd.DataFrame(index=x.index)
lab = {'Ability & opposition rating': 'Margin-based rating (v3: margins, weight, opposition)', 'Ability figures & opposition faced': 'Time-based figures + opposition faced (RQ times)',
       'Closing sectionals': 'Individual closing sectionals (tracking)', 'Barrier & race shape': 'Barrier and running style (tracking positions)'}
for f, cols in E.QFAM.items(): C[lab.get(f, f)] = sum(C21.get(c, 0.0) * x[c + '_z'].fillna(0.0) for c in cols if c + '_z' in x)
C['v2: horse course/going/distance records'] = x[['t::' + t for t in QFAM2['Horse course/going/distance records']]].fillna(0).values @ np.array([M['coef_per_term_sd_all_races'][t] for t in QFAM2['Horse course/going/distance records']])
C['v2: jockey & trainer'] = x[['t::' + t for t in QFAM2['Jockey & trainer']]].fillna(0).values @ np.array([M['coef_per_term_sd_all_races'][t] for t in QFAM2['Jockey & trainer']])
C = C.sub(C.groupby(x.race_id.values).transform('mean')); tot = C.sum(axis=1)
out = pd.DataFrame({'share_%': (100 * C.apply(lambda c: np.cov(c, tot)[0, 1]) / tot.var()).round(1)}).sort_values('share_%', ascending=False)
print(out.to_string()); out.to_csv('/tmp/natq/b11/decomp_qld.csv'); print('races', x.race_id.nunique())
print({f: cols for f, cols in E.QFAM.items() if f in ('Ability figures & opposition faced', 'Closing sectionals')})
