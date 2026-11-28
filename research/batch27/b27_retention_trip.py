"""Batch 27 P3 secondary (preregistered): speed retention x trip direction inside the distance candidate. ret_up = retention prior x 1(step up
15%+), ret_down = retention prior x 1(step down 15%+); retention prior = shrunk mean (3 runs to 0) of the horse's earlier measured M5 (Qld RQ
and SA tracking); 0 when untracked (no missing flag, no penalty). Writes the two terms into /tmp/cand/feat_CONS_L.parquet."""
import numpy as np, pandas as pd
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'horse', 'date', 'dist_change'])
F['date'] = pd.to_datetime(F.date)
T = pd.concat([pd.read_parquet(f'/home/claude/b14/b25_phys_{s}.parquet', columns=['horse', 'meeting_date', 'M5']) for s in ['QLD', 'SA']]).rename(columns={'meeting_date': 'tdate'})
T['tdate'] = pd.to_datetime(T.tdate); T = T.sort_values(['horse', 'tdate'])
T['s'] = T.M5.fillna(0).groupby(T.horse).cumsum(); T['c'] = T.M5.notna().astype(float).groupby(T.horse).cumsum(); T = T.groupby(['horse', 'tdate']).last().reset_index()
M = pd.merge_asof(F[['race_id', 'horse', 'date']].sort_values('date'), T[['horse', 'tdate', 's', 'c']].sort_values('tdate'), left_on='date', right_on='tdate', by='horse', allow_exact_matches=False)
M['m5p'] = (M.s / (M.c + 3.0)).fillna(0.0)
F = F.merge(M[['race_id', 'horse', 'm5p']], on=['race_id', 'horse'], how='left'); dc = F.dist_change.astype(float).fillna(0)
F['ret_up'] = F.m5p.fillna(0) * (dc > 0.14); F['ret_down'] = F.m5p.fillna(0) * (dc < -0.14)
G = pd.read_parquet('/tmp/cand/feat_CONS_L.parquet'); n = len(G)
G = G.drop(columns=[c for c in ['ret_up', 'ret_down'] if c in G]).merge(F[['race_id', 'horse', 'ret_up', 'ret_down']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
assert len(G) == n; G[['ret_up', 'ret_down']] = G[['ret_up', 'ret_down']].fillna(0.0); G.to_parquet('/tmp/cand/feat_CONS_L.parquet')
print('nonzero up/down', int((G.ret_up != 0).sum()), int((G.ret_down != 0).sum()))
