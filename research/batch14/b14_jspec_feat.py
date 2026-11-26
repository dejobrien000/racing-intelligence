"""Batch 14 s11 engine test input: the jockey's and the trainer's prior distance-band surprise (band minus overall; earlier dates only,
each shrunk with 60 rides' weight), computed on the Engine v2.3 (C2) frame's own rating surprise, added to the C2 harness feature file."""
import pandas as pd, numpy as np
U = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race_id', 'horse', 'date', 'race_no', 'distance_m', 'jkey', 'tkey', 'dyn_nat_inn'])
U['date'] = pd.to_datetime(U.date); U['band'] = pd.cut(U.distance_m.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
for key, pre in [('jkey', 'j'), ('tkey', 't')]:
    v = U[U[key].notna() & U.dyn_nat_inn.notna()]
    day = v.groupby([key, 'band', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    day['cs'] = day.groupby([key, 'band'])['sum'].cumsum() - day['sum']; day['cc'] = day.groupby([key, 'band'])['count'].cumsum() - day['count']
    al = v.groupby([key, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    al['as'] = al.groupby(key)['sum'].cumsum() - al['sum']; al['ac'] = al.groupby(key)['count'].cumsum() - al['count']
    X = U[[key, 'band', 'date']].merge(day[[key, 'band', 'date', 'cs', 'cc']], on=[key, 'band', 'date'], how='left').merge(al[[key, 'date', 'as', 'ac']], on=[key, 'date'], how='left')
    U[pre + '_spec'] = (X['cs'] / (X['cc'] + 60) - X['as'] / (X['ac'] + 60)).fillna(0).values
F = pd.read_parquet('/tmp/cand/f_C2/b10/out/feat.parquet'); n0 = len(F)
F = F.merge(U[['race_id', 'horse', 'j_spec', 't_spec']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
assert len(F) == n0; F[['j_spec', 't_spec']] = F[['j_spec', 't_spec']].fillna(0)
F.to_parquet('/tmp/cand/f_C2J/b10/out/feat.parquet'); print(F[['j_spec', 't_spec']].describe().round(3).to_string())
