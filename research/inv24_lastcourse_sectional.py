"""Batch 4, Study 11 (secondary, descriptive, reported only). Does a last-start closing sectional mean the same at every
course? Course of the LAST start x last-start closing-sectional gap (s_gap600_last), partially pooled as in Study 10 D,
same combined_v1 offset. Outputs out/out_s11_*.csv"""
import numpy as np, pandas as pd
exec(open('inv22_course_barriers.py').read().split("models = {}")[0])
r = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'meeting_date', 'track']].sort_values(['horse_id', 'meeting_date'])
r['last_course'] = r.groupby('horse_id').track.shift(1)
x = x.merge(r[['race_id', 'horse_id', 'last_course']], on=['race_id', 'horse_id'], how='left')
x['sg'] = x.s_gap600_last_z
lc = x[(x.period == 'development') & x.s_gap600_last.notna()].groupby('last_course').race_id.nunique()
LC = sorted(lc[lc >= 150].index)
def C11(df): return pd.DataFrame({f'sg|{c}': df.sg.values * (df.last_course == c).values for c in LC}, index=df.index)
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']; d1, d2 = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
tl = []
for a in [0.005, 0.02, 0.05, 0.1, 0.2, 0.5, 1e3]:
    tl.append((races(d2, C11(d2)).loglik_per_race(H.fit(races(d1, C11(d1)), np.full(len(LC), 1 / a ** 2))).sum(), a))
print('inner split by tau:', [(a, round(v, 2)) for v, a in tl]); tau = max(tl)[1]
lam = np.full(len(LC), 1 / tau ** 2); b = H.fit(races(dev, C11(dev)), lam); sd = H.posterior_sd(races(dev, C11(dev)), b, lam)
bi = H.fit(races(dev, C11(dev)), np.full(len(LC), 1e-6))
b1 = H.fit(races(d1, C11(d1)), np.full(len(LC), 1e-6)); b2 = H.fit(races(d2, C11(d2)), np.full(len(LC), 1e-6))
pool = bb[BENCH.index('s_gap600_last')]
t = pd.DataFrame({'last_start_course': LC, 'dev_races': [int(lc[c]) for c in LC], 'pooled_coef': round(pool, 3), 'deviation_partial_pooling': b.round(3), 'sd': sd.round(3),
                  'deviation_no_pooling': bi.round(3), 'no_pool_oct22_dec23': b1.round(3), 'no_pool_2024': b2.round(3)})
t['clear_of_pool_95'] = (t.deviation_partial_pooling.abs() > 1.96 * t.sd)
Re0 = races(ev, C11(ev)); l0 = Re0.loglik_per_race(np.zeros(len(LC))); l1 = Re0.loglik_per_race(b)
print('chosen tau', tau, '| eval fit gain per race vs pooled', round((l1 - l0).mean(), 5), '| stability corr (no pooling halves)', round(np.corrcoef(b1, b2)[0, 1], 3))
print(t.to_string(index=False)); t.to_csv('out/out_s11_lastcourse_sectional.csv', index=False)
