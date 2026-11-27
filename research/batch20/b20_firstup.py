"""Batch 20 G16: the evidence behind the 0.14 first-up relationship (Batch 19), and whether a horse's own first-up record adds anything
beyond the fitness and preparation terms the engine already has. Research only; no prices.
Preparation = runs separated by gaps of 60 days or less (as Batch 19). Each horse's first preparation held is skipped (its start may lie
before our data). fresh preference of a preparation = its first-up surprise minus the mean surprise of runs 2-5 (3+ runs).
  fu_own = a horse's own fresh record from EARLIER preparations only, shrunk (sum / (n + 3)); at a first-up run, 0 at any other run.
  (1) Batch 19 replication: fresh preference ~ fu_own (descriptive; the target uses runs after the first-up run).
  (2) Pre-race question: the first-up run's own surprise ~ fu_own, then + the existing fitness/preparation terms (days since the last run,
      spell length relative to the horse's usual, first-up vs usual, runs to usual peak, preparation shape). Cluster-robust by horse.
Outputs: batch20/out_b20_firstup.json; /tmp/cand/fu_own.parquet (race_id, horse, fu_own) for the harness test.
Usage (from research/): python3 batch20/b20_firstup.py"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'race_id', 'dyn_nat_inn', 'age_n', 'r_ldays']).dropna(subset=['dyn_nat_inn'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U['gap'] = U.groupby('horse').date.diff().dt.days; U['newprep'] = U.gap.isna() | (U.gap > 60)
U['prep'] = U.groupby('horse').newprep.cumsum(); U['prun'] = U.groupby(['horse', 'prep']).cumcount() + 1
P = U.groupby(['horse', 'prep']).agg(first=('dyn_nat_inn', lambda s: s.iloc[0]), later=('dyn_nat_inn', lambda s: s.iloc[1:5].mean() if len(s) >= 3 else np.nan),
                                     race_id=('race_id', 'first'), date=('date', 'first'), spell=('gap', 'first')).reset_index()
P = P[P.prep >= 2].copy(); P['fresh_pref'] = P['first'] - P.later
P = P.sort_values(['horse', 'prep'])
P['prior_sum'] = P.groupby('horse').fresh_pref.transform(lambda s: s.shift().fillna(0).cumsum()); P['prior_n'] = P.groupby('horse').fresh_pref.transform(lambda s: s.shift().notna().cumsum())
P['fu_own'] = P.prior_sum / (P.prior_n + 3)
FE = pd.read_parquet('/tmp/cand/f_C2/b10/out/feat.parquet', columns=['race_id', 'horse', 'gap_long_z', 'early_prep_vs_usual', 'runs_to_usual_peak', 'prep_shape', 'prep_days'])
Q = P[P.prior_n >= 1].merge(FE.drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
Q = Q.merge(U[['race_id', 'horse', 'r_ldays']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
Q['gap_long_miss'] = Q.gap_long_z.isna().astype(float); Q['gap_long_z0'] = Q.gap_long_z.fillna(0.0)   # spell length vs the horse's usual; missing when no usual yet
Q['win'] = np.where(Q.date < '2025-01-01', 'to 2024', '2025-26')
def fit(f, d, cols):
    d = d.dropna(subset=cols); m = smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    return {'n': int(m.nobs), 'fu_own': [round(float(m.params['fu_own']), 3)] + [round(float(x), 3) for x in m.conf_int().loc['fu_own']], 'r2': round(float(m.rsquared), 4),
            'others': {v: round(float(m.params[v]), 3) for v in m.params.index if v not in ('Intercept', 'fu_own')}}
FIT = ['r_ldays', 'gap_long_z0', 'gap_long_miss', 'runs_to_usual_peak', 'prep_shape']   # early_prep_vs_usual is not defined at first-up runs (0.1% coverage)
OUT = {'definition': 'fresh preference = first-up surprise minus mean surprise of runs 2-5 of the same preparation; own record shrunk with 3 pseudo-preparations',
       'preparations_with_an_earlier_record': int(len(Q)), 'horses': int(Q.horse.nunique()), 'fu_own_sd_kg': round(float(Q.fu_own.std()), 3)}
OUT['(1) Batch 19 replication: fresh preference ~ own record'] = fit('fresh_pref ~ fu_own', Q, ['fresh_pref', 'fu_own'])
OUT['(2a) first-up surprise ~ own record'] = fit('first ~ fu_own', Q, ['first', 'fu_own'])
OUT['(2b) first-up surprise ~ own record + fitness terms'] = fit('first ~ fu_own + ' + ' + '.join(FIT), Q, ['first', 'fu_own'] + FIT)
for w, g in Q.groupby('win'): OUT[f'(2b) by window: {w}'] = fit('first ~ fu_own + ' + ' + '.join(FIT), g, ['first', 'fu_own'] + FIT)
for lab, g in [('1 earlier preparation', Q[Q.prior_n == 1]), ('2-3 earlier', Q[Q.prior_n.between(2, 3)]), ('4+ earlier', Q[Q.prior_n >= 4])]:
    OUT[f'(2b) by record depth: {lab}'] = fit('first ~ fu_own + ' + ' + '.join(FIT), g, ['first', 'fu_own'] + FIT)
OUT['fitness_term_coverage'] = {c: round(float(Q[c].notna().mean()), 3) for c in FIT}
A = U[['race_id', 'horse']].drop_duplicates(['race_id', 'horse']).merge(P[['race_id', 'horse', 'fu_own']], on=['race_id', 'horse'], how='left'); A['fu_own'] = A.fu_own.fillna(0.0)
A.to_parquet('/tmp/cand/fu_own.parquet'); json.dump(OUT, open('batch20/out_b20_firstup.json', 'w'), indent=1)
for k, v in OUT.items(): print(k, v)
