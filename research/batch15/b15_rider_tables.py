"""Batch 15 (brief s4): readable rider momentum tables (descriptive, research only). Same measures as b14f_riders.py:
timing = gain on the field 800-400 m out minus the last 400 (+ = the horses he/she rides make their ground EARLY),
late hold = final 200 vs the 200 before (+ = keep their speed late). Each run's value has the circumstances removed (position, deficit at
800, tempo, distance, course, opposition, prep stage, field) and the horse's own average removed (same horse, different riders), then
the trainer's average removed. Riders shrunk towards 0 by 50 rides. Only riders with 200+ tracked rides (Qld Oct 2022-Nov 2026, SA
Jan 2024-Nov 2026) are profiled; nobody else gets a profile. Consistency: the tendency estimated separately on two halves of the
rider's trainers (alternate trainers), and in each state where the rider has 60+ rides.
Writes batch15/rider_tables.csv and out_rider_tables.json, and freezes the profile table for the prospective check
(prospective/research/rider_momentum_frozen_20261126.csv: data to 23 Nov 2026 database release)."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json, os
P = pd.read_parquet('/home/claude/b14/profiles.parquet')
for v in ['v1000', 'v800']: P[v + 'r'] = P[v] - P.groupby('race_id')[v].transform('median')
P['timing'] = (P.v800r + P.v600r) / 2 - (P.v400r + P.v200r) / 2; P['hold'] = P.v200r - P.v400r
P['jk'] = P.jkey.fillna(P.jockey.astype(str)); P['tk'] = P.tkey.fillna(P.trainer.astype(str))
P = P.dropna(subset=['timing', 'hold']).sort_values('meeting_date').reset_index(drop=True)
rows = []
for st in ['QLD', 'SA']:
    d = P[P.state == st].copy()
    for col in ['timing', 'hold']:
        y, X = patsy.dmatrices(f'{col} ~ early_pos + I(early_pos**2) + def800c + tz + tz_miss + C(dband) + C(track) + fmean_c + C(prep) + field', d, return_type='dataframe', NA_action='drop')
        r = pd.Series(np.nan, index=d.index); r.loc[y.index] = sm.OLS(y, X).fit().resid.values
        d[col + '_wh'] = r - r.groupby(d.horse).transform('mean'); d[col + '_wht'] = d[col + '_wh'] - d.groupby('tk')[col + '_wh'].transform('mean')
    rows.append(d)
D = pd.concat(rows); D = D.dropna(subset=['timing_wht', 'hold_wht'])
name = D.groupby('jk').jockey.agg(lambda x: x.dropna().mode().iloc[0] if len(x.dropna()) else '')
K = 50.0
def prof(g):
    n = len(g); out = {'rides': n, 'qld_rides': int((g.state == 'QLD').sum()), 'sa_rides': int((g.state == 'SA').sum()), 'trainers': g.tk.nunique()}
    for c in ['timing', 'hold']:
        v = g[c + '_wht']; m = v.sum() / (n + K); se = v.std() / np.sqrt(n + K)
        out[c] = m; out[c + '_lo'] = m - 1.96 * se; out[c + '_hi'] = m + 1.96 * se
        tg = pd.factorize(g.tk)[0] % 2; a, b = v[tg == 0], v[tg == 1]
        out[c + '_trainersA'] = a.sum() / (len(a) + K); out[c + '_trainersB'] = b.sum() / (len(b) + K)
        for st in ['QLD', 'SA']:
            s_ = v[g.state == st]; out[f'{c}_{st}'] = s_.sum() / (len(s_) + K) if len(s_) >= 60 else np.nan
    return pd.Series(out)
T = D.groupby('jk').apply(prof); T = T[T.rides >= 200].copy(); T['rider'] = name.reindex(T.index)
# m/s to lengths over 200 m: a length ~ 2.4 m; at ~16.5 m/s a 200 m section takes ~12 s; 0.01 m/s x 12 s = 0.12 m = 0.05 L
T['timing_L'] = T.timing * 12 / 2.4; T['hold_L'] = T.hold * 12 / 2.4
T['timing_consistent'] = np.sign(T.timing_trainersA) == np.sign(T.timing_trainersB)
T['hold_consistent'] = np.sign(T.hold_trainersA) == np.sign(T.hold_trainersB)
T['timing_clear'] = (T.timing_lo > 0) | (T.timing_hi < 0); T['hold_clear'] = (T.hold_lo > 0) | (T.hold_hi < 0)
T = T.round(4)
T.sort_values('rides', ascending=False).to_csv('batch15/rider_tables.csv')
OUT = {'riders profiled (200+ tracked rides)': int(len(T)), 'by state (main state)': T.apply(lambda r: 'QLD' if r.qld_rides >= r.sa_rides else 'SA', axis=1).value_counts().to_dict(),
       'riders with 60+ rides in both states': int(((T.qld_rides >= 60) & (T.sa_rides >= 60)).sum()),
       'correlation timing vs hold (riders)': round(float(T.timing.corr(T.hold)), 3),
       'trainer-half agreement: timing r, same sign %': [round(float(T.timing_trainersA.corr(T.timing_trainersB)), 3), round(100 * float(T.timing_consistent.mean()), 1)],
       'trainer-half agreement: hold r, same sign %': [round(float(T.hold_trainersA.corr(T.hold_trainersB)), 3), round(100 * float(T.hold_consistent.mean()), 1)],
       'riders whose 95% interval excludes 0: timing, hold': [int(T.timing_clear.sum()), int(T.hold_clear.sum())]}
both = T[(T.qld_rides >= 60) & (T.sa_rides >= 60)]
if len(both) >= 3: OUT['state agreement (riders with 60+ rides in both): timing r, hold r'] = [round(float(both.timing_QLD.corr(both.timing_SA)), 3), round(float(both.hold_QLD.corr(both.hold_SA)), 3), int(len(both))]
cols = ['rider', 'rides', 'qld_rides', 'sa_rides', 'trainers', 'timing', 'timing_lo', 'timing_hi', 'timing_L', 'timing_consistent', 'hold', 'hold_lo', 'hold_hi', 'hold_L', 'hold_consistent']
E = T[T.timing > 0].sort_values('rides', ascending=False).head(20).sort_values('timing', ascending=False)
L_ = T[T.timing < 0].sort_values('rides', ascending=False).head(20).sort_values('timing')
H = T.sort_values('hold', ascending=False).head(20)
OUT['top 20 early-momentum riders (most rides among riders whose horses gain early)'] = E[cols].to_dict('records')
OUT['top 20 late-momentum riders (most rides among riders whose horses gain late)'] = L_[cols].to_dict('records')
OUT['20 strongest late-speed retention'] = H[cols].to_dict('records')
OUT['overlap: of the 20 strongest retention riders, how many are late-momentum (timing < 0)'] = int((H.timing < 0).sum())
json.dump(OUT, open('batch15/out_rider_tables.json', 'w'), indent=1, default=str)
os.makedirs('prospective/research', exist_ok=True)
T[['rider', 'rides', 'timing', 'timing_lo', 'timing_hi', 'hold', 'hold_lo', 'hold_hi']].to_csv('prospective/research/rider_momentum_frozen_20261126.csv')
print(json.dumps({k: v for k, v in OUT.items() if not k.startswith(('top', '20'))}, default=str))
for k in ['top 20 early-momentum riders (most rides among riders whose horses gain early)', 'top 20 late-momentum riders (most rides among riders whose horses gain late)', '20 strongest late-speed retention']:
    print(k); print(pd.DataFrame(OUT[k])[['rider', 'rides', 'timing', 'timing_lo', 'timing_hi', 'timing_consistent', 'hold', 'hold_lo', 'hold_hi', 'hold_consistent']].to_string(index=False))
