"""Batch 20 B4: experience used by the history-completeness responsiveness candidate, one row per completed run (point in time).
Sources, in order of preference, each labelled:
  verified   TAB's as-at career starts for that horse on that race day (morning form record, collected since 25 Nov 2026): n_eff = TAB starts
             before the race. Never projected backwards to earlier runs (that would use information not available at the time).
  complete   inferred: the horse's first run held is from March 2023 and it was aged 4 or less then, so runs held = career starts.
  probable_incomplete  inferred: first run held before March 2023, or aged 5+ at its first run held (earlier career, import, or a genuine
             late starter: age is part of this proxy and is NOT verification); n_eff = max(runs held, 24).
  (unknown experience arises only for a future runner with no runs held and no TAB record; completed runs are always one of the above)
Usage (from research/): python3 batch20/b20_experience_file.py <frame.parquet> <out.parquet>"""
import sys, glob, re, numpy as np, pandas as pd
FR, OUTF = sys.argv[1], sys.argv[2]
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
U = pd.read_parquet(FR, columns=['race', 'horse', 'date', 'age_n']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U['n_held'] = U.groupby('horse').cumcount()
first = U.groupby('horse').date.transform('min'); age1 = U.groupby('horse').age_n.transform('first')
complete = (first >= pd.Timestamp('2023-03-01')) & (age1 <= 4)
U['source'] = np.where(complete, 'complete', 'probable_incomplete')   # a first run held by an incomplete-history horse is not a debut
U['n_eff'] = np.where(U.source == 'probable_incomplete', np.maximum(U.n_held, 24), U.n_held).astype(float)
V = []
for f in sorted(glob.glob('collect/national/*/form_runners.csv')):
    d = pd.read_csv(f, usecols=['name', 'career_starts']); d['date'] = pd.Timestamp(f.split('/')[2]); d['horse'] = d.name.map(nk); V.append(d.dropna(subset=['career_starts']))
if V:
    V = pd.concat(V).drop_duplicates(['horse', 'date'])
    U = U.merge(V[['horse', 'date', 'career_starts']], on=['horse', 'date'], how='left')
    v = U.career_starts.notna(); U.loc[v, 'n_eff'] = U.loc[v, 'career_starts'].astype(float); U.loc[v, 'source'] = 'verified'
U[['race', 'horse', 'n_eff', 'source']].rename(columns={'race': 'race_key'}).to_parquet(OUTF)
print(OUTF, U.source.value_counts().to_dict())
