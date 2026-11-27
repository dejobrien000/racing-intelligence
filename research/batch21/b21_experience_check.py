"""Batch 21 B5: does the experience file (v3) match TAB's verified career starts? VALIDATION ONLY: TAB's present-day counts are compared
with what the file says at each horse's latest completed run; they are never written back into history or used as an input.
For every TAB runner on the collected mornings (26-27 Nov) with a career-starts figure and runs in our history:
  ours_observed = starts known at its latest run + 1 (that run)   ours_used = experience the rating used + 1
  TAB = career starts that morning (includes any starts after our data end, so ours may be a little lower legitimately)
Reported by label (complete / older beginner / probably incomplete, split into 'list starts too late' and 'aged 5+ outside a maiden').
Usage (from research/): python3 batch21/b21_experience_check.py"""
import re, glob, json, numpy as np, pandas as pd
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
E = pd.read_parquet('/tmp/cand/experience_b21.parquet')
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date']).rename(columns={'race': 'race_key'})
E = E.merge(F, on=['race_key', 'horse']).sort_values(['horse', 'date'])
L = E.groupby('horse').tail(1).set_index('horse')
T = pd.concat([pd.read_csv(f).assign(day=f.split('/')[2]) for f in sorted(glob.glob('collect/national/*/form_runners.csv'))], ignore_index=True)
T['horse'] = T.name.map(nk); T = T.dropna(subset=['career_starts']).drop_duplicates('horse', keep='last').join(L, on='horse', how='inner')
T['ours_observed'] = T.observed + 1; T['ours_used'] = T.n_eff + 1; T['tab'] = T.career_starts.astype(float)
T['grp'] = T.source.where(T.source != 'probable_incomplete', np.where(T.inferred_added > 0, 'probably incomplete (typical starts added)', 'probably incomplete'))
def summ(g, col):
    d = g[col] - g.tab
    return {'runners': int(len(g)), 'median_diff': float(d.median()), 'mean_diff': round(float(d.mean()), 2), 'share_over_by_5plus': round(float((d >= 5).mean()), 3), 'share_under_by_5plus': round(float((d <= -5).mean()), 3)}
OUT = {'note': 'ours minus TAB career starts; TAB includes starts after our data end (about 4 days of results), so small negatives are expected'}
for lab, g in [('all', T)] + list(T.groupby('grp')):
    OUT[lab] = {'observed_only': summ(g, 'ours_observed'), 'as_used_by_candidate': summ(g, 'ours_used')}
# where the added typical starts overstate: by age at the current run
P = T[T.inferred_added > 0].copy(); P['age_band'] = pd.cut(P.age, [0, 4, 5, 6, 7, 20], labels=['<=4', '5', '6', '7', '8+']).astype(str)
OUT['typical_starts_added_by_age'] = {a: summ(g, 'ours_used') for a, g in P.groupby('age_band') if len(g) >= 10}
json.dump(OUT, open('batch21/out_b21_experience_check.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
