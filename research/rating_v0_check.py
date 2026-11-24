"""Checks for run rating v0: repeatability, does a better pre-race figure win more often, class ordering."""
import pandas as pd, numpy as np
from statsmodels.discrete.conditional_models import ConditionalLogit
d = pd.read_parquet('runs_rated.parquet').drop_duplicates(['race_id', 'horse_id'])
out = []
r = d[d.rating.notna() & d.next_rating.notna() & d.gap_to_next.between(7, 90)]
out.append(('repeatability: correlation of a run with the horse\'s next run (7-90 days)', round(r[['rating', 'next_rating']].corr().iloc[0, 1], 3), len(r)))
r2 = r[r.class_bucket == r.next_class_bucket]
out.append(('same, next run in the same class bucket', round(r2[['rating', 'next_rating']].corr().iloc[0, 1], 3), len(r2)))
# pre-race figure vs result, within race
x = d[d.best_last3.notna() & d.finished & (d.field >= 6)].copy()
x['n_rated'] = x.groupby('race_id')['best_last3'].transform('count'); x = x[x.n_rated == x.field]
x['pre_rank'] = x.groupby('race_id')['best_last3'].rank(ascending=False, method='first')
top = x[x.pre_rank == 1]
exp = (1 / top.field).sum()
out.append(('top-rated pre-race (best of last 3) win strike %', round(100 * top.win.mean(), 1), len(top)))
out.append(('  A/E (actual wins / wins expected by field size)', round(top.win.sum() / exp, 2), len(top)))
x['z'] = (x.best_last3 - x.groupby('race_id')['best_last3'].transform('mean')) / 5
for split, g in x.groupby('split'):
    m = ConditionalLogit(g['win'].values, g[['z']].values, groups=g['race_id'].values).fit(disp=0)
    out.append((f'win odds ratio per 5 kg of pre-race figure ({split})', round(float(np.exp(m.params[0])), 2), g.race_id.nunique()))
# compare with last-start finishing position as the only information
x['prev_fp'] = x.groupby('horse_id')['finish_pct'].shift()
cls = d[d.rating.notna()].groupby('class_bucket')['rating'].agg(['median', 'count']).sort_values('median')
res = pd.DataFrame(out, columns=['check', 'value', 'n']); print(res.to_string(index=False)); print(cls.round(1).to_string())
res.to_csv('out/out_rating_v0_checks.csv', index=False); cls.to_csv('out/out_rating_v0_by_class.csv')
