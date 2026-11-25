"""Batch 11 s5 (cont.): lightly raced horses by what their runs showed (last-start rating surprise), rating level and opposition step. 2025-26, v2 and v2.2 out of sample."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'b11'); from s11_common import ae
x = pd.read_parquet('b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1]
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'surprise_last', 'finish_pos']).sort_values(['horse', 'date'])
U['last_surprise'] = U.surprise_last; U['last_fpos'] = U.groupby('horse').finish_pos.shift()
x = x.merge(U[['race_id', 'horse', 'last_surprise', 'last_fpos']], on=['race_id', 'horse'], how='left')
x['q3'] = pd.cut(x.groupby('race_id').dyn_nat.rank(ascending=False, pct=True), [0, 1 / 3, 2 / 3, 1.01], labels=['top third', 'middle third', 'bottom third'])
o = x[(x.meeting_date.dt.year >= 2025) & x.n_prior.between(1, 3)].copy()
o['surp'] = pd.cut(o.last_surprise, [-99, -3, 0, 3, 6, 99], labels=['ran 3kg+ below expectation', '0-3kg below', '0-3kg above', '3-6kg above', '6kg+ above (big surprise)'])
o['opp'] = np.where(o.opp_step > 0, 'facing stronger field than last time', 'facing weaker/equal field')
def both(g, nm):
    a = ae(g.assign(p=g.p_v2), 'horse'); b = ae(g.assign(p=g.p_v22), 'horse')
    return {'group': nm, 'runners': a['runners'], 'wins': a['wins'], 'v2_ratio': a['ratio'], 'v2_ci': f"{a.get('lo95')}-{a.get('hi95')}", 'v22_expected': b['expected'], 'v22_ratio': b['ratio'], 'v22_ci': f"{b.get('lo95')}-{b.get('hi95')}"}
rows = []
for n in [1, 2, 3]:
    for v, g in o[o.n_prior == n].groupby('surp', observed=True): rows.append(both(g, f'{n} run(s) held | last start {v}'))
for v, g in o.groupby('opp'): rows.append(both(g, f'1-3 runs | {v}'))
for v, g in o.groupby('q3', observed=True): rows.append(both(g, f'1-3 runs | rating {v} of field'))
ex = o[(o.q3 == 'top third') & (o.last_surprise >= 3)]; rows.append(both(ex, '1-3 runs | top third AND last start 3kg+ above expectation ("exceptional")'))
ex = o[(o.q3 == 'top third') & (o.last_fpos == 1)]; rows.append(both(ex, '1-3 runs | top third AND won last start'))
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('b11/out_lightly_raced2.csv', index=False)
