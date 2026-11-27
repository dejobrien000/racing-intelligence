"""Batch 18 E6 harness input (research only; not authorised for production): trainer debut record.
For a horse's first run in our data, the trainer's earlier debutants' surprise on debut (performance against the rating's first-start
expectation, Engine v2.3 frame), strictly before the race date, minus the population's running average, shrunk towards zero
(k = 15 debuts, fixed in advance, not tuned). Only genuine debuts count towards a trainer's record (first run in our data, aged 2 or 3,
from March 2023, so careers that began before our history are not mistaken for debuts). Zero for every other run.
Writes a copy of the C2 harness features with the extra column tr_debut: /tmp/cand/f_C2T/b10/out/feat.parquet (frame = C2, symlinked).
Usage: python3 batch18/b18_trainer_debut_feature.py"""
import os, numpy as np, pandas as pd
U = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race_id', 'horse', 'date', 'race', 'tkey', 'age_n', 'dyn_nat_inn'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
real = (U.k == 0) & U.age_n.isin([2, 3]) & (U.date >= '2023-03-01') & U.dyn_nat_inn.notna() & U.tkey.notna()
D = U[real].copy()
pd_ = D.groupby('date').dyn_nat_inn.agg(['sum', 'count']).sort_index().cumsum().shift(1)            # population running mean, earlier dates only
pop = (pd_['sum'] / pd_['count']).rename('pop'); D = D.join(pop, on='date'); D['r'] = D.dyn_nat_inn - D['pop'].fillna(0)
g = D.groupby(['tkey', 'date']).r.agg(['sum', 'count']).reset_index().sort_values(['tkey', 'date'])
g[['cs', 'cn']] = g.groupby('tkey')[['sum', 'count']].cumsum().values                                 # record up to and including that date
Q = U[(U.k == 0) & U.tkey.notna()][['race_id', 'horse', 'tkey', 'date']].sort_values('date')
F = pd.merge_asof(Q, g[['date', 'tkey', 'cs', 'cn']].sort_values('date'), on='date', by='tkey', allow_exact_matches=False)   # strictly earlier dates
F['tr_debut'] = (F.cs / (F.cn + 15)).fillna(0.0)
feat = pd.read_parquet('/tmp/cand/f_C2/b10/out/feat.parquet')
feat = feat.drop(columns=['tr_debut'], errors='ignore').merge(F[['race_id', 'horse', 'tr_debut']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
feat['tr_debut'] = feat.tr_debut.fillna(0.0)
os.makedirs('/tmp/cand/f_C2T/b10/out', exist_ok=True); feat.to_parquet('/tmp/cand/f_C2T/b10/out/feat.parquet')
if not os.path.exists('/tmp/cand/frames/C2T_national.parquet'): os.symlink('/tmp/cand/frames/C2_national.parquet', '/tmp/cand/frames/C2T_national.parquet')
nz = feat.tr_debut != 0
print('rows', len(feat), 'non-zero', int(nz.sum()), 'sd (non-zero)', round(float(feat.tr_debut[nz].std()), 3), 'range', round(float(feat.tr_debut.min()), 2), round(float(feat.tr_debut.max()), 2))
