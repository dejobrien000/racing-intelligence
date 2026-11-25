"""SA/WA/Tas release check (run from /tmp/nat3/research after the rebuild with NAT_STATES incl. SA,WA,TAS).
1) NSW/Vic/ACT ratings before vs after (they should barely move). 2) Engine v2 (NSW/Vic family, frozen) on 2025-26 races
by state: how well does it rank SA, WA and Tas races it never saw? 3) NSW/Vic accuracy before vs after."""
import json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)   # U = new frame
MAN = json.load(open('benchmarks/engine_v2/manifest.json'))
OLD = pd.read_parquet('/home/claude/pilot/research/engine/frames/national.parquet', columns=['race', 'horse', 'dyn_nat'])
j = U[['race', 'horse', 'state', 'dyn_nat']].merge(OLD, on=['race', 'horse'], suffixes=('', '_old'))
d = (j.dyn_nat - j.dyn_nat_old).abs()
print('1) rows matched', len(j), '| NSW/Vic/ACT rating change: mean abs', round(d.mean(), 3), 'kg; 95th pct', round(d.quantile(.95), 3), 'kg; max', round(d.max(), 2))
print(U.groupby('state').size().to_dict())
def score(frame):
    x = E.nat_frame(frame); allt = sum(NFAM2.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat')
    bd = np.array([MAN['families']['NSW_VIC_ACT']['coef_per_term_sd_dev_fit'][t] for t in allt]); return x, off + x[['t::' + a for a in allt]].values @ bd
x, e = score(U); ev = (x.period == 'evaluation')
rows = []
for st in ['NSW', 'VIC', 'ACT', 'SA', 'WA', 'TAS']:
    m = ev & (x.state == st)
    if m.sum() == 0: continue
    r = E.metrics(x, e, m); rows.append({'state': st, **E.summary(r)})
xo, eo = score(pd.read_parquet('/home/claude/pilot/research/engine/frames/national.parquet'))
for st in ['NSW', 'VIC']:
    r = E.metrics(xo, eo, (xo.period == 'evaluation') & (xo.state == st)); rows.append({'state': st + ' (before)', **E.summary(r)})
T = pd.DataFrame(rows); print(T.to_string(index=False)); T.to_csv('/tmp/nat3/eval_by_state.csv', index=False)
# how many SA/WA/Tas runners have at least one measured run before the race (the rest stay unrated)
h = U[U.state.isin(['SA', 'WA', 'TAS']) & (U.date >= '2025-01-01')]
print('SA/WA/Tas 2025-26 runners with a prior measured run:', round(100 * h.dyn_nat_sd.lt(h.dyn_nat_sd.max() - 1e-9).mean(), 1), '%')
