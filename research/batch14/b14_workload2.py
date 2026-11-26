"""Batch 14 s12 follow-up: is the 'later rides go better' pattern booking selection or order? Compare rides WITHIN the same jockey at the
same meeting (jockey x meeting means removed), so who books the jockey and how busy the day is are held fixed; race order controlled
for all runners. Also: add the trainer's prior distance-band surprise to the s11 prospective test (stables target distances)."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
exec(open('/home/claude/racing-intelligence/research/batch14/b14_jockey.py').read().split("# a) persistence")[0])
def cfit(form, f, key='jkey'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
OUT = {}
W = V.sort_values(['jkey', 'meeting_id', 'race_no']).copy(); g = W.groupby(['jkey', 'meeting_id'])
W['ride_idx'] = g.cumcount(); W['rides_meeting'] = g.race_no.transform('size'); W['dist_before'] = g.distance_m.cumsum().astype(float) - W.distance_m.astype(float)
W = W[W.rides_meeting >= 2].copy()
# race-order effect for everyone (all runners) is removed first, then compare within jockey x meeting
W['race_no_c'] = W.race_no.clip(upper=10).astype(str)
ro = W.groupby('race_no_c').dyn_nat_inn.mean(); W['inn_ro'] = W.dyn_nat_inn - W.race_no_c.map(ro)
for v in ['inn_ro', 'dyn_nat']: W[v + '_wjm'] = W[v] - W.groupby(['jkey', 'meeting_id'])[v].transform('mean')
W['ride_c'] = W.ride_idx.clip(upper=6).astype(str)
m = cfit('inn_ro_wjm ~ C(ride_c) + dyn_nat_wjm', W)
OUT['within jockey x meeting: surprise by earlier rides (vs first ride), kg'] = {k.replace('C(ride_c)[T.', '').replace(']', ''): (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in m.params.index if 'ride_c' in k}
m2 = cfit('inn_ro_wjm ~ I(dist_before/1000) + dyn_nat_wjm', W)
OUT['within jockey x meeting: per 1,000 m ridden earlier'] = tuple(round(x, 3) for x in [m2.params['I(dist_before / 1000)'], *m2.conf_int().loc['I(dist_before / 1000)']])
# between meetings: busier days vs quieter days for the same jockey (selection)
W['inn_wj'] = W.dyn_nat_inn - W.groupby('jkey').dyn_nat_inn.transform('mean'); W['rm_c'] = W.rides_meeting.clip(upper=7).astype(str)
m3 = cfit('inn_wj ~ C(rm_c) + C(race_no_c) + C(rband)', W)
OUT['same jockey, busier meeting (rides at the meeting, vs 2), kg'] = {k.replace('C(rm_c)[T.', '').replace(']', ''): (round(m3.params[k], 3), round(m3.conf_int().loc[k, 0], 3), round(m3.conf_int().loc[k, 1], 3)) for k in m3.params.index if 'rm_c' in k}
OUT['rides in the within-meeting comparison'] = len(W)
print(json.dumps(OUT), flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_workload2.json', 'w'), indent=1)
# placebo: the same within-meeting comparison for TRAINERS (a trainer's later runners at the same meeting); and a horse-free check using
# the finishing percentile beaten vs expected by rating rank in the race (no rating-surprise arithmetic)
T = V[V.tkey.notna()].sort_values(['tkey', 'meeting_id', 'race_no']).copy(); gt = T.groupby(['tkey', 'meeting_id'])
T['idx'] = gt.cumcount(); T['n'] = gt.race_no.transform('size'); T = T[T.n >= 2].copy(); T['race_no_c'] = T.race_no.clip(upper=10).astype(str)
T['inn_ro'] = T.dyn_nat_inn - T.race_no_c.map(T.groupby('race_no_c').dyn_nat_inn.mean())
for v in ['inn_ro', 'dyn_nat']: T[v + '_wtm'] = T[v] - T.groupby(['tkey', 'meeting_id'])[v].transform('mean')
T['idx_c'] = T.idx.clip(upper=4).astype(str)
mt = cfit('inn_ro_wtm ~ C(idx_c) + dyn_nat_wtm', T, key='tkey')
P = {'trainer placebo: later runners at the same meeting (vs first), kg': {k.replace('C(idx_c)[T.', '').replace(']', ''): (round(mt.params[k], 3), round(mt.conf_int().loc[k, 0], 3), round(mt.conf_int().loc[k, 1], 3)) for k in mt.params.index if 'idx_c' in k}}
W['exp_rank_pct'] = W.groupby('race_id').dyn_nat.rank(ascending=False, pct=True); W['beat'] = W.exp_rank_pct - W.nat_fp_pct      # + = finished better than rating rank
W['beat_wjm'] = W.beat - W.groupby(['jkey', 'meeting_id']).beat.transform('mean'); W['beat_ro'] = W.beat_wjm
mb = cfit('beat_wjm ~ C(ride_c) + C(race_no_c)', W)
P['finish vs rating rank (share of field), within jockey x meeting'] = {k.replace('C(ride_c)[T.', '').replace(']', ''): (round(mb.params[k], 4), round(mb.conf_int().loc[k, 0], 4), round(mb.conf_int().loc[k, 1], 4)) for k in mb.params.index if 'ride_c' in k}
print(json.dumps(P), flush=True); OUT.update(P); json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_workload2.json', 'w'), indent=1)
