"""Batch 18 E6/E4 preliminary (research only; point in time; no prices).
(1) Trainer debut behaviour: for each debut (first run held, horse aged 2-3 so the career starts inside our history), the trainer's share of
    EARLIER debutants that debuted at two (shrunk, k = 10), known before the race. Outcome: the debut run's surprise (performance against
    the generic first-starter expectation). Controls: trainer form (t_surp, point in time), age, sex, state, distance band, year.
    Question: is a two-year-old from a trainer who rarely debuts two-year-olds better than expected? Observed debut behaviour only - we do
    not hold any stable's full population of unraced horses, so this is NOT selectivity relative to an eligible population.
(2) Persistence: each trainer's average debut surprise beyond trainer form, 2023-24 vs 2025-26.
(3) Maturity with continuation (Per Incanto example): by sire, the share of three-year-old starters seen racing at four, and the
    three-to-four change among horses with 3+ runs at both ages. Disappearing from our data is not assumed to mean retirement.
Usage: python3 batch18/b18_debut_selectivity.py -> batch18/out_b18_debut_selectivity.json"""
import re, json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'state', 'tkey', 't_surp', 'age_n', 'female', 'distance_m', 'dyn_nat', 'dyn_nat_inn'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
D = U[(U.k == 0) & U.age_n.isin([2, 3]) & (U.date >= '2023-03-01') & U.dyn_nat_inn.notna() & U.tkey.notna()].copy().sort_values('date')
D['is2'] = (D.age_n == 2).astype(float); D['one'] = 1.0
g = D.groupby(['tkey', 'date'])[['is2', 'one']].sum().reset_index().sort_values(['tkey', 'date'])
g[['s2', 'n']] = g.groupby('tkey')[['is2', 'one']].cumsum().values - g[['is2', 'one']].values
D = D.merge(g[['tkey', 'date', 's2', 'n']], on=['tkey', 'date'], how='left'); pop = float(D.is2.mean())
D['tr_share2'] = (D.s2 + 10 * pop) / (D.n + 10); D['tr_n'] = D.n
D['db'] = pd.cut(D.distance_m, [0, 1050, 1250, 1450, 9999], labels=['to 1050', '1051-1250', '1251-1450', '1451+']).astype(str); D['yr'] = D.date.dt.year.astype(str)
OUT = {'debuts': int(len(D)), 'share_debuting_at_two': round(pop, 3), 'trainers': int(D.tkey.nunique())}
E = D[D.tr_n >= 5].copy(); E['low2'] = (E.tr_share2 < E.tr_share2.median()).astype(float)
m = smf.ols('dyn_nat_inn ~ is2 * low2 + t_surp + female + C(state) + C(db) + C(yr)', E.fillna({'t_surp': 0, 'female': 0})).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(E.tkey)[0]})
ci = lambda k: [round(float(m.params[k]), 3), round(float(m.conf_int().loc[k, 0]), 3), round(float(m.conf_int().loc[k, 1]), 3)]
OUT['debut_surprise_model'] = {'n': int(m.nobs), 'two_year_old': ci('is2'), 'trainer_rarely_debuts_twos': ci('low2'), 'two_yo_from_such_trainer_extra': ci('is2:low2'), 'trainer_form_per_kg': ci('t_surp')}
OUT['raw_means'] = {f"{'2yo' if a else '3yo'} | {'trainer rarely debuts twos' if b else 'trainer often debuts twos'}": [int(len(x)), round(float(x.dyn_nat_inn.mean()), 2)] for (a, b), x in E.groupby(['is2', 'low2'])}
# persistence of trainer debut performance beyond trainer form
E2 = D[D.tr_n >= 0].copy(); E2['res'] = E2.dyn_nat_inn - smf.ols('dyn_nat_inn ~ t_surp + is2 + female', E2.fillna({'t_surp': 0, 'female': 0})).fit().fittedvalues
P = E2.assign(per=np.where(E2.date < '2025-01-01', 'a', 'b')).groupby(['tkey', 'per']).res.agg(['mean', 'count']).unstack()
P = P[(P[('count', 'a')] >= 15) & (P[('count', 'b')] >= 15)]
OUT['trainer_debut_residual_persistence'] = {'trainers': int(len(P)), 'corr_2023_24_vs_2025_26': round(float(np.corrcoef(P[('mean', 'a')], P[('mean', 'b')])[0, 1]), 3) if len(P) > 5 else None}
# maturity with continuation, by sire
con = duckdb.connect('../history/history.duckdb', read_only=True); nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
Pd = con.execute("select name_key, sire from bn_runner where sire is not null").fetchdf(); Pd['horse'] = Pd.name_key.map(nk); Pd = Pd.groupby('horse').sire.agg(lambda s: s.mode().iloc[0])
A = U[U.age_n.isin([3, 4]) & (U.date < '2026-08-01')].copy(); A['sire'] = A.horse.map(Pd)
c3 = A[A.age_n == 3].groupby('horse').agg(n3=('race', 'count'), r3=('dyn_nat', 'last'), sire=('sire', 'first'), last3=('date', 'max'))
c4 = A[A.age_n == 4].groupby('horse').agg(n4=('race', 'count'), r4=('dyn_nat', 'last'))
W = c3.join(c4, how='left'); W = W[W.last3 < '2025-08-01']           # three-year-old seasons that ended at least a year before the data ends
W['raced_at_4'] = W.n4.notna().astype(float); W['d'] = W.r4 - W.r3
S = W.groupby('sire').agg(three_yo=('n3', 'size'), share_seen_at_4=('raced_at_4', 'mean'))
Wf = W[(W.n3 >= 3) & (W.n4 >= 3)]; S = S.join(Wf.groupby('sire').d.agg(change_3_to_4='mean', both_ages='count'))
avg = {'share_seen_at_4': round(float(W.raced_at_4.mean()), 3), 'change_3_to_4_with_3plus_runs_each': round(float(Wf.d.mean()), 2)}
pi = S[S.index.str.contains('Per Incanto', case=False)]
OUT['maturity_with_continuation'] = {'population': avg, 'per_incanto': pi.round(3).reset_index().to_dict('records'),
    'top_change_sires_40plus': S[S.both_ages >= 40].sort_values('change_3_to_4', ascending=False).head(6).round(3).reset_index().to_dict('records')}
json.dump(OUT, open('batch18/out_b18_debut_selectivity.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:4000])
