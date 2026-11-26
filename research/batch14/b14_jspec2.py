"""Batch 14 s11 follow-up: does the jockey's prior distance-band surprise still add once the TRAINER's prior distance-band surprise is in?
And a rating-free check: finishing position vs rating rank (share of field) as the outcome."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
src = open('/home/claude/racing-intelligence/research/batch14/b14_jockey.py').read()
exec(src.split("# a) persistence")[0])
def cfit(form, f, key='jkey'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
V = V.sort_values(['date', 'race_no']).reset_index(drop=True)
def prior(key, pre):
    day = V.groupby([key, 'band', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    day['cs'] = day.groupby([key, 'band'])['sum'].cumsum() - day['sum']; day['cc'] = day.groupby([key, 'band'])['count'].cumsum() - day['count']
    al = V.groupby([key, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    al['as'] = al.groupby(key)['sum'].cumsum() - al['sum']; al['ac'] = al.groupby(key)['count'].cumsum() - al['count']
    X = V[[key, 'band', 'date']].merge(day[[key, 'band', 'date', 'cs', 'cc']], on=[key, 'band', 'date'], how='left').merge(al[[key, 'date', 'as', 'ac']], on=[key, 'date'], how='left')
    V[pre + '_all'] = (X['as'] / (X['ac'] + 60)).values; V[pre + '_spec'] = (X['cs'] / (X['cc'] + 60) - X['as'] / (X['ac'] + 60)).values; V[pre + '_n'] = X['ac'].values
prior('jkey', 'j'); prior('tkey', 't')
V['exp_rank_pct'] = V.groupby('race_id').dyn_nat.rank(ascending=False, pct=True); V['beat'] = V.exp_rank_pct - V.nat_fp_pct
e = V[(V.j_n >= 100) & (V.date >= '2023-07-01') & V.j_surp.notna()].copy()
O = {}
for y in ['dyn_nat_inn', 'beat']:
    for lab, f in [('2023-26', e), ('2025-26', e[e.date >= '2025-01-01'])]:
        m = cfit(f'{y} ~ j_surp + j_all + j_spec + t_all + t_spec + C(band) + C(rband) + C(state)', f)
        O[f'{y} {lab}'] = {k: (round(m.params[k], 4), round(m.conf_int().loc[k, 0], 4), round(m.conf_int().loc[k, 1], 4)) for k in ['j_spec', 't_spec', 'j_surp']}
print(json.dumps(O)); json.dump(O, open('/home/claude/racing-intelligence/research/batch14/out_jspec2.json', 'w'), indent=1)
