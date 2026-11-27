"""Batch 19 C9: does a sire's maturity pattern add anything beyond the horse's own record? (research only; no breeding input approved).
Seasons run 1 Aug - 31 Jul. Cohort A = three-year-old season 2023-24 and its four-year-old season 2024-25; cohort B = 2024-25 -> 2025-26.
Sire maturity = shrunk (k = 15) mean change from the last rating at three to the last rating at four, estimated on cohort A only, then
used to predict cohort B horses' change, with the horse's own controls: rating level at three, runs at three, age at debut, whether its
history is complete, trainer. Only horses seen racing at both ages with 3+ runs each (continuation reported separately, by sire).
Usage (from research/): python3 batch19/b19_sire_maturity.py -> batch19/out_b19_sire_maturity.json"""
import re, json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
P = con.execute("select name_key, sire from bn_runner where sire is not null").fetchdf(); P['horse'] = P.name_key.map(nk); P = P.groupby('horse').sire.agg(lambda s: s.mode().iloc[0])
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'dyn_nat', 'age_n', 'tkey'])
U = U.sort_values(['horse', 'date', 'race']); U['k'] = U.groupby('horse').cumcount()
f = U.groupby('horse').agg(first=('date', 'min'), age1=('age_n', 'first')); U = U.join(f, on='horse')
U['season'] = np.where(U.date.dt.month >= 8, U.date.dt.year, U.date.dt.year - 1)
def cohort(s3):
    a = U[(U.season == s3) & (U.age_n == 3)].groupby('horse').agg(r3=('dyn_nat', 'last'), n3=('race', 'count'), t=('tkey', 'last'), first=('first', 'first'), age1=('age1', 'first'))
    b = U[(U.season == s3 + 1) & (U.age_n == 4)].groupby('horse').agg(r4=('dyn_nat', 'last'), n4=('race', 'count'))
    c = a.join(b, how='left'); c['seen4'] = c.r4.notna(); c['sire'] = c.index.map(P); c['d'] = c.r4 - c.r3
    c['complete'] = (c['first'] >= pd.Timestamp('2023-03-01')) & c.age1.isin([2, 3]); c['deb2'] = (c.age1 == 2).astype(float); return c
A, B = cohort(2023), cohort(2024)
Af = A[(A.n3 >= 3) & (A.n4 >= 3)]; mu = Af.d.mean(); g = Af.groupby('sire').d.agg(['sum', 'count']); sm = ((g['sum'] - g['count'] * mu) / (g['count'] + 15)).rename('sire_mat')
Bf = B[(B.n3 >= 3) & (B.n4 >= 3)].join(sm, on='sire'); Bf['sire_mat'] = Bf.sire_mat.fillna(0); Bf['complete'] = Bf.complete.astype(float)
m0 = smf.ols('d ~ r3 + np.log(n3) + deb2 + complete', Bf).fit(); m1 = smf.ols('d ~ r3 + np.log(n3) + deb2 + complete + sire_mat', Bf).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Bf.sire.fillna('?'))[0]})
gB = Bf.groupby('sire').d.agg(['sum', 'count']); smB = ((gB['sum'] - gB['count'] * Bf.d.mean()) / (gB['count'] + 15)); both = sm.index.intersection(smB.index)
both = [s for s in both if g.loc[s, 'count'] >= 15 and gB.loc[s, 'count'] >= 15]
cont = {s: [round(float(A[A.sire == s].seen4.mean()), 3), round(float(B[B.sire == s].seen4.mean()), 3)] for s in ['Per Incanto (USA)', 'Justify (USA)', 'Brutal (NZ)', 'Fiorente (IRE)']}
OUT = {'cohort_A_horses_3plus_runs_each_age': int(len(Af)), 'cohort_B_horses': int(len(Bf)), 'mean_change_A': round(float(mu), 2), 'mean_change_B': round(float(Bf.d.mean()), 2),
       'sire_maturity_coef_in_B_beyond_controls': [round(float(m1.params['sire_mat']), 3), round(float(m1.conf_int().loc['sire_mat', 0]), 3), round(float(m1.conf_int().loc['sire_mat', 1]), 3)],
       'r2_without_with': [round(float(m0.rsquared), 4), round(float(m1.rsquared), 4)],
       'sire_means_A_vs_B_corr_15plus_each': [round(float(np.corrcoef(sm[both], smB[both])[0, 1]), 3) if len(both) > 8 else None, len(both)],
       'per_incanto': {'A': [int(g.loc['Per Incanto (USA)', 'count']) if 'Per Incanto (USA)' in g.index else 0, round(float(sm.get('Per Incanto (USA)', np.nan)), 2)],
                       'B': [int(gB.loc['Per Incanto (USA)', 'count']) if 'Per Incanto (USA)' in gB.index else 0, round(float(smB.get('Per Incanto (USA)', np.nan)), 2)]},
       'continuation_seen_at_four_A_B': {**cont, 'all horses': [round(float(A.seen4.mean()), 3), round(float(B.seen4.mean()), 3)]},
       'note': 'B four-year-old seasons end 31 Jul 2026; horses still racing after our data ends are counted as seen if they raced at four by then.'}
json.dump(OUT, open('batch19/out_b19_sire_maturity.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
