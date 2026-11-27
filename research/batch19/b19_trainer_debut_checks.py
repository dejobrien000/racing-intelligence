"""Batch 19 A3: checks on the trainer debut record before it becomes a candidate (research only; no production use).
Uses the same point-in-time record as batch18/b18_trainer_debut_feature.py (shrunk mean of a trainer's EARLIER genuine debutants' surprise,
k = 15). Checks: (1) genuine debut identification against TAB's as-at career starts (26-27 Nov 2026 form records); (2) trainer-name parity
between history (Breednet / Racing Queensland) and today's TAB fields through the same person key; (3) partnerships; (4) independence from
general trainer form; (5) trainers with little debut history; (6) age and sex; (7) first runs that are not genuine debuts; (8) accuracy of
the initial expectation itself (debut performance), fitted on 2023 and judged on 2024 and 2025-26, separately from race forecasts.
Writes the genuine-debut-only harness input (tr_debut_g) beside tr_debut: /tmp/cand/f_C2T/b10/out/feat.parquet.
Usage (from research/): python3 batch19/b19_trainer_debut_checks.py -> batch19/out_b19_trainer_debut_checks.json"""
import os, json, numpy as np, pandas as pd, statsmodels.formula.api as smf, sys
sys.path.insert(0, 'engine'); from lab import person_key
U = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race_id', 'horse', 'date', 'race', 'state', 'tkey', 't_surp', 'age_n', 'female', 'dyn_nat_inn'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
U['genuine'] = (U.k == 0) & U.age_n.isin([2, 3]) & (U.date >= '2023-03-01')
D = U[U.genuine & U.dyn_nat_inn.notna() & U.tkey.notna()].copy()
pop = D.groupby('date').dyn_nat_inn.agg(['sum', 'count']).sort_index().cumsum().shift(1); D = D.join((pop['sum'] / pop['count']).rename('pop'), on='date')
D['r'] = D.dyn_nat_inn - D['pop'].fillna(0)
g = D.groupby(['tkey', 'date']).r.agg(['sum', 'count']).reset_index().sort_values(['tkey', 'date']); g[['cs', 'cn']] = g.groupby('tkey')[['sum', 'count']].cumsum().values
Q = U[(U.k == 0) & U.tkey.notna()][['race_id', 'horse', 'tkey', 'date', 'genuine', 'age_n', 'female', 't_surp', 'dyn_nat_inn', 'state']].sort_values('date')
Q = pd.merge_asof(Q, g[['date', 'tkey', 'cs', 'cn']].sort_values('date'), on='date', by='tkey', allow_exact_matches=False)
Q['cn'] = Q.cn.fillna(0); Q['tr_debut'] = (Q.cs.fillna(0) / (Q.cn + 15)); Q['tr_debut_g'] = np.where(Q.genuine, Q.tr_debut, 0.0)
OUT = {}
# (1) genuine debut identification vs TAB as-at career starts
R = []
for Dd in ['20261126', '20261127']:
    a = pd.read_csv(f'collect/national/{Dd}/form_runners.csv'); b = pd.read_csv(f'collect/national/{Dd}/form_runner_status.csv')
    R.append(a.merge(b[['ven', 'race', 'n', 'held_starts']], on=['ven', 'race', 'n'], how='left'))
T = pd.concat(R).dropna(subset=['career_starts', 'held_starts'])
z = T[T.held_starts == 0]
OUT['1_debut_identification_tab_26_27_nov'] = {'runners_with_no_runs_held': int(len(z)), 'tab_career_starts_zero': int((z.career_starts == 0).sum()),
    'by_age': {int(k): [int(len(v)), int((v.career_starts == 0).sum())] for k, v in z.groupby('age')}, 'tab_first_starters_with_runs_held': int(((T.career_starts == 0) & (T.held_starts > 0)).sum())}
# (2) trainer-name parity: today's TAB trainer strings -> person key -> a debut record in history?
hist_keys = set(g.tkey)
T['tk'] = T.trainer.map(person_key); fs = T[T.career_starts == 0]
OUT['2_trainer_key_parity'] = {'tab_first_starters': int(len(fs)), 'trainer_key_found_in_history': int(fs.tk.isin(set(U.tkey.dropna())).sum()), 'with_a_debut_record': int(fs.tk.isin(hist_keys).sum()),
                               'examples_not_found': fs[~fs.tk.isin(set(U.tkey.dropna()))].trainer.head(8).tolist()}
# (3) partnerships (the key keeps the first named trainer's initial + the LAST surname, so a new partnership starts a new record)
Gd = Q[Q.genuine & Q.dyn_nat_inn.notna()].copy()
fs = fs.assign(partnership=fs.trainer.fillna('').str.contains('&'))
OUT['3_partnerships_tab_first_starters'] = {'share_partnership': round(float(fs.partnership.mean()), 3),
    'partnership_with_debut_record': [int(fs[fs.partnership].tk.isin(hist_keys).sum()), int(fs.partnership.sum())], 'solo_with_debut_record': [int(fs[~fs.partnership].tk.isin(hist_keys).sum()), int((~fs.partnership).sum())]}
# (4) independence from general trainer form
OUT['4_independence'] = {'corr_tr_debut_with_t_surp_genuine': round(float(Gd[['tr_debut', 't_surp']].dropna().corr().iloc[0, 1]), 3)}
# (5) limited debut history
OUT['5_prior_debuts_at_time'] = {k: int(v) for k, v in pd.cut(Gd.cn, [-1, 0, 4, 14, 9999], labels=['none', '1-4', '5-14', '15+']).value_counts().sort_index().items()}
OUT['5_shrink_weight_note'] = 'weight on the trainer\'s own mean = n / (n + 15): 1 debut 6%, 5 debuts 25%, 15 debuts 50%, 45 debuts 75%'
# (6)-(8) initial expectation accuracy and interactions (fit 2023, judge 2024 and 2025-26), genuine debuts
Gd['yr'] = Gd.date.dt.year; Gd['t_surp'] = Gd.t_surp.fillna(0); Gd['two'] = (Gd.age_n == 2).astype(float); Gd['female'] = Gd.female.fillna(0)
fit = Gd[Gd.yr == 2023]; m0 = smf.ols('dyn_nat_inn ~ t_surp + two + female', fit).fit(); m1 = smf.ols('dyn_nat_inn ~ t_surp + two + female + tr_debut', fit).fit()
acc = {}
for lab, te in [('2024', Gd[Gd.yr == 2024]), ('2025-26', Gd[Gd.yr >= 2025])]:
    e0 = (te.dyn_nat_inn - m0.predict(te)) ** 2; e1 = (te.dyn_nat_inn - m1.predict(te)) ** 2; d = (e0 - e1).values
    rng = np.random.default_rng(3); bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(1000)]
    acc[lab] = {'debuts': int(len(te)), 'mse_without': round(float(e0.mean()), 3), 'mse_with': round(float(e1.mean()), 3), 'reduction': round(float(d.mean()), 3), 'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
OUT['8_initial_expectation_accuracy'] = {'fit_2023_coef_per_kg_of_record': round(float(m1.params['tr_debut']), 3), **acc}
late = Gd[Gd.yr >= 2024]; mi = smf.ols('dyn_nat_inn ~ t_surp + two + female + tr_debut + tr_debut:two + tr_debut:female', late).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(late.tkey)[0]})
ci = lambda k: [round(float(mi.params[k]), 3), round(float(mi.conf_int().loc[k, 0]), 3), round(float(mi.conf_int().loc[k, 1]), 3)]
OUT['6_age_sex_interactions_2024_26'] = {'tr_debut (3yo colt/gelding)': ci('tr_debut'), 'extra for two-year-olds': ci('tr_debut:two'), 'extra for fillies/mares': ci('tr_debut:female')}
nong = Q[~Q.genuine & Q.dyn_nat_inn.notna() & (Q.date >= '2024-01-01')]
mn = smf.ols('dyn_nat_inn ~ t_surp + tr_debut', nong.fillna({'t_surp': 0})).fit()
OUT['7_first_runs_held_that_are_not_genuine_debuts'] = {'runs_2024_26': int(len(nong)), 'share_of_all_first_runs_held_2024_26': round(float(len(nong) / len(Q[Q.dyn_nat_inn.notna() & (Q.date >= '2024-01-01')])), 3),
                                                       'tr_debut_coef_on_them': [round(float(mn.params['tr_debut']), 3), round(float(mn.conf_int().loc['tr_debut', 0]), 3), round(float(mn.conf_int().loc['tr_debut', 1]), 3)]}
feat = pd.read_parquet('/tmp/cand/f_C2T/b10/out/feat.parquet')
feat = feat.drop(columns=['tr_debut_g'], errors='ignore').merge(Q[['race_id', 'horse', 'tr_debut_g']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left'); feat['tr_debut_g'] = feat.tr_debut_g.fillna(0.0)
os.makedirs('/tmp/cand/f_C2T/b10/out', exist_ok=True); feat.to_parquet('/tmp/cand/f_C2T/b10/out/feat.parquet')
json.dump(OUT, open('batch19/out_b19_trainer_debut_checks.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
