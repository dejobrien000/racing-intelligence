import time, json, numpy as np, pandas as pd, sys
from engine import lab, dyn_v3
import dyn_rating as DR
P = lab.PN_FROZEN
U = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m'])
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0), 'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
def ev(**kw):
    t0 = time.time(); dyn_v3.run(PN, P['s_kg'], P['q_kg2_per_day'], P['sig0_kg'], P['debut_offset_kg'], **kw)
    r = {**kw, 'll_dev': round(dyn_v3.run.ll_dev, 5), 'll_eval_not_used_to_choose': round(dyn_v3.run.ll_eval, 5), 'secs': round(time.time() - t0)}; print(r, flush=True); return r
rows = [ev()]; best = {}; bll = rows[0]['ll_dev']
for rnd in range(2):
    for name, grid in [('a_q', [1, 3, 6, 10]), ('v_spell', [2, 5, 10, 20]), ('s_first', [-0.15, 0.15, 0.3]), ('c_trend', [0.1, 0.25, 0.5])]:
        cur = best.get(name, 0.0); pick = cur
        for g in grid:
            if g == cur: continue
            r = ev(**{**best, name: g}); rows.append(r)
            if r['ll_dev'] > bll + 1e-5: bll, pick = r['ll_dev'], g
        if pick: best[name] = pick
print('chosen on development runs only:', best, bll)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/tune_v3.csv', index=False); json.dump({'params': best, 'll_dev': bll}, open('/tmp/exp/rt/tune_v3_choice.json', 'w'))
