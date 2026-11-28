"""Batch 26 Part 3: pre-race physical inputs from the three replicated Batch 25 measures, for the national engine harness.
Measured tracking only (Racing Queensland 200 m splits, Racing SA tracking); never a rating. For every row of the Engine v2.3 frame
(race_id, horse), using only tracked runs on EARLIER dates:
  ph_m3p / ph_m1p / ph_m6p = the horse's shrunk mean of M3 (600-200 m vs the day), M1 (last 400 vs the day), M6t (tempo against
  position) over its earlier tracked runs: sum / (n + 3) -> 0 (average) when the horse has no tracked run
  ph_m3l / ph_m1l = value at its most recent earlier tracked run, 0 when none
No missing flag: a horse without tracking is treated as average, never penalised for missing measurement (Damo, Batch 26 Part 3).
Coverage columns (not model inputs): ph_n = earlier tracked runs, ph_src = state of the tracking.
Output: /tmp/cand/feat_phys.parquet (race_id, horse, ph_*). Usage (from research/): python3 batch26/b26_phys_feat.py"""
import numpy as np, pandas as pd
F = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race_id', 'horse', 'date', 'state'])
F['date'] = pd.to_datetime(F.date)
T = []
for st in ['QLD', 'SA']:
    P = pd.read_parquet(f'/home/claude/b14/b25_phys_{st}.parquet', columns=['horse', 'meeting_date', 'race_id', 'M1', 'M3', 'M6_tempo_part'])
    P['src'] = st; T.append(P)
T = pd.concat(T).rename(columns={'M6_tempo_part': 'M6t', 'meeting_date': 'tdate'}).sort_values(['horse', 'tdate', 'race_id'])
for m in ['M3', 'M1', 'M6t']:
    v = T[m].fillna(0.0); c = T[m].notna().astype(float)
    T[m + '_s'] = v.groupby(T.horse).cumsum(); T[m + '_c'] = c.groupby(T.horse).cumsum()
T['n'] = T.groupby('horse').cumcount() + 1
T = T.groupby(['horse', 'tdate']).last().reset_index().drop(columns=['race_id'])   # state after the horse's last tracked run that day
Fs = F.sort_values('date'); Ts = T.sort_values('tdate')
M = pd.merge_asof(Fs, Ts, left_on='date', right_on='tdate', by='horse', allow_exact_matches=False, direction='backward')
out = M[['race_id', 'horse']].copy()
for m, k in [('M3', 'm3'), ('M1', 'm1'), ('M6t', 'm6')]:
    out[f'ph_{k}p'] = (M[m + '_s'] / (M[m + '_c'] + 3.0)).fillna(0.0).astype('float32')
out['ph_m3l'] = M.M3.fillna(0.0).astype('float32'); out['ph_m1l'] = M.M1.fillna(0.0).astype('float32')
out['ph_n'] = M.n.fillna(0).astype('int16'); out['ph_src'] = M.src.fillna('none')
out = out.drop_duplicates(['race_id', 'horse'])
out.to_parquet('/tmp/cand/feat_phys.parquet')
cov = out.merge(F[['race_id', 'horse', 'state']], on=['race_id', 'horse'])
print('rows', len(out), '| with an earlier tracked run:', int((out.ph_n > 0).sum()))
print(cov.assign(has=cov.ph_n > 0).groupby('state').has.mean().round(3).to_dict())
print(cov[cov.ph_n > 0].groupby(['state', 'ph_src']).size().to_dict())
