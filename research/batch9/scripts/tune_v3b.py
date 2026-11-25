import time, json, itertools, numpy as np, pandas as pd
from engine import lab, dyn_v3
import dyn_rating as DR
P = lab.PN_FROZEN
U = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m'])
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0), 'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
rows = []
for g, n0, a in itertools.product([0, 0.5, 1.0, 1.5], [4, 8], [0, 0.5, 1.0, 1.5]):
    if g == 0 and n0 == 8 and a == 0: continue
    dyn_v3.run(PN, P['s_kg'], P['q_kg2_per_day'], P['sig0_kg'], P['debut_offset_kg'], a_q=a, n0=n0, g_imp=g)
    rows.append({'g_imp': g, 'n0': n0, 'a_q': a, 'll_dev': round(dyn_v3.run.ll_dev, 5), 'll_eval_not_used': round(dyn_v3.run.ll_eval, 5)}); print(rows[-1], flush=True)
T = pd.DataFrame(rows); T.to_csv('/tmp/exp/rt/tune_v3b.csv', index=False)
b = T.sort_values('ll_dev', ascending=False).iloc[0]; print('BEST on development:', b.to_dict())
json.dump({k: float(b[k]) for k in ['g_imp', 'n0', 'a_q']}, open('/tmp/exp/rt/tune_v3_choice.json', 'w'))
