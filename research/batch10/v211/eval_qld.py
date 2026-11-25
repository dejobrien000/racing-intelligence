"""Qld Breednet backfill release check (run from the sandbox research/ after the rebuild). Compares with the current release
(/tmp/nat3 = master-2026-11-23-sa-wa-tas): rating movement, Engine v2 national family by state, Qld family (v1+v2 terms, frozen),
Qld scale guard, and Qld coverage (ages, non-tracked meetings)."""
import json, numpy as np, pandas as pd, sys
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json'))
OLD = pd.read_parquet('/tmp/nat3/research/engine/frames/national.parquet', columns=['race', 'horse', 'dyn_nat', 'state'])
j = U[['race', 'horse', 'state', 'dyn_nat']].merge(OLD, on=['race', 'horse'], suffixes=('', '_old')); d = (j.dyn_nat - j.dyn_nat_old).abs()
print('1) runs matched', len(j), '| rating change mean', round(d.mean(), 3), 'kg; 95th', round(d.quantile(.95), 3), '; max', round(d.max(), 2)); print(j.assign(d=d).groupby('state').d.mean().round(3).to_dict())
print('frame rows by state', U.groupby('state').size().to_dict(), '| Qld rows from Breednet (no RQ id):', int((U.state.eq('QLD') & U.q_race_id.isna()).sum()))
def nat(frame):
    x = E.nat_frame(frame); allt = sum(NFAM2.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat')
    bd = np.array([MAN['families']['NSW_VIC_ACT']['coef_per_term_sd_dev_fit'][t] for t in allt]); return x, off + x[['t::' + a for a in allt]].values @ bd
def qld(frame):
    QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
    x = E.qld_frame(frame); allt = sum(QREL.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'qld')
    bd = np.array([MAN['families']['QLD']['coef_per_term_sd_dev_fit'][t] for t in allt]); return x, off + x[['t::' + a for a in allt]].values @ bd
rows = []
for lab_, fr in [('after', U), ('before', pd.read_parquet('/tmp/nat3/research/engine/frames/national.parquet'))]:
    x, e = nat(fr); ev = x.period == 'evaluation'
    for st in ['NSW', 'VIC', 'SA', 'WA', 'TAS']:
        rows.append({'model': 'national family', 'state': st, 'version': lab_, **E.summary(E.metrics(x, e, ev & (x.state == st)))})
    x, e = qld(fr); rows.append({'model': 'Qld family', 'state': 'QLD', 'version': lab_, **E.summary(E.metrics(x, e, x.period == 'evaluation'))})
T = pd.DataFrame(rows); print(T.to_string(index=False)); T.to_csv('/tmp/natq/eval_qld.csv', index=False)
q = U[(U.state == 'QLD') & U.q_race_id.notna()]; dev = q[q.period == 'development']
c = dev.dyn_nat - dev.groupby('race').dyn_nat.transform('mean'); print('Qld scale (dev SD after race centring, national rating):', round(float(c.std()), 4), 'frozen v2:', MAN['families']['QLD']['base_feature_dev_sd']['dyn_nat'])
print('Qld runners 2025-26 with age known:', round(100 * U[(U.state == 'QLD') & (U.date >= '2025-01-01')].age.notna().mean(), 1), '%')
