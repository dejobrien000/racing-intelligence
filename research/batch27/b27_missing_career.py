"""Batch 27 P4: experienced horses with missing histories (research only). At a horse's FIRST held run the rating treats it as a debutant
(field mean - 2 kg, sd 5 kg). How does that first held run go when the evidence says it had raced before (experience-file source
'probable_incomplete' = inferred earlier starts; 'late_maiden'; verified TAB counts) vs genuine debutants (complete, age 2-3)?
Surprise = performance vs the rating's expectation (kg). Output batch27/out_b27_missing_career.json"""
import json, numpy as np, pandas as pd
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date', 'age_n', 'state', 'dyn_nat_inn', 'class_label'])
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']); F['k'] = F.groupby('horse').cumcount()
E = pd.read_parquet('engine/frames/experience_at_run.parquet').rename(columns={'race_key': 'race'})
X = F[(F.k == 0) & (F.date >= '2023-01-01')].merge(E, on=['race', 'horse'], how='left')
X['prior'] = X.inferred_added.fillna(0) + X.verified.fillna(0)
X['grp'] = np.select([(X.source == 'complete') & X.age_n.isin([2, 3]), (X.source == 'complete'), X.prior >= 5, X.prior > 0], ['genuine debutant (2-3yo, complete)', 'first held run, older, history complete', 'evidence of 5+ earlier starts', 'evidence of 1-4 earlier starts'], 'other / unknown')
out = {}
for g, Z in X.groupby('grp'):
    Z = Z[Z.dyn_nat_inn.notna()]
    out[g] = {'first_runs': int(len(Z)), 'mean_surprise_kg': round(float(Z.dyn_nat_inn.mean()), 2), 'sd_kg': round(float(Z.dyn_nat_inn.std()), 2), 'mean_age': round(float(Z.age_n.mean()), 1)}
# second held run: does the rating catch up after one run? (surprise at k=1 by the same groups)
Y = F[F.k == 1].merge(X[['horse', 'grp']], on='horse')
out['second_held_run_mean_surprise_kg'] = {g: [int(len(Z)), round(float(Z.dyn_nat_inn.mean()), 2)] for g, Z in Y.groupby('grp')}
json.dump(out, open('batch27/out_b27_missing_career.json', 'w'), indent=1); print(json.dumps(out, indent=1))
