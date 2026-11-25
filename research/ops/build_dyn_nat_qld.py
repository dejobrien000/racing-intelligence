"""Rebuild dyn_nat_qld.parquet (national dynamic rating on Qld tracked runs, frozen Batch 4 parameters) without running the
rest of the Batch 5 study. Same code as the first lines of inv29_course_conditions.py. Run from research/."""
import json, numpy as np, pandas as pd
import dyn_rating as DR
mn = json.load(open('benchmarks/candidates_b4_national/manifest.json')); pn = mn['dynamic_rating_params']
U = pd.read_parquet('national_runs.parquet')
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                   'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, _, _ = DR.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
U['dyn_nat'] = pd.Series(mu, index=PN.idx.values).reindex(np.arange(len(U))).values
qn = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_nat']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id'])
qn.to_parquet('dyn_nat_qld.parquet'); print('dyn_nat_qld rows', len(qn))
