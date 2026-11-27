"""Batch 18 D2: where do the experience-based rule (U5E) and the uniform 1.3x rule (U5) disagree? Per-race log-likelihood differences
(harness results, same races) broken down by year, state, race type, field experience and the share of runners whose careers began before
our history does (first run held in Oct-Dec 2022 at age 4+, or any runner aged 5+ with under 5 runs held). Research only.
Usage: python3 batch18/b18_experience_split.py -> batch18/out_b18_experience_split.json"""
import json, numpy as np, pandas as pd
import sys; VA, VB = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ('U5E', 'U5')   # e.g. U5EA U5 (age-floor variant)
a = pd.read_parquet(f'/tmp/cand/res_{VA}_R.parquet'); b = pd.read_parquet(f'/tmp/cand/res_{VB}_R.parquet')
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'horse', 'date', 'state', 'class_label', 'age_n', 'field']).sort_values(['horse', 'date'])
U['k'] = U.groupby('horse').cumcount(); first = U.groupby('horse').date.transform('min'); age_first = U.groupby('horse').age_n.transform('first')
U['incomplete'] = ((first < '2023-01-01') & (age_first >= 4)) | ((U.age_n >= 5) & (U.k < 5))
R = U.groupby('race_id').agg(date=('date', 'first'), state=('state', 'first'), cls=('class_label', 'first'), mean_k=('k', 'mean'), inc=('incomplete', 'mean'),
                              light=('k', lambda s: float((s <= 5).mean())))
rng = np.random.default_rng(18); OUT = {}
def ci(d, meet):
    if len(d) < 50: return None
    g = pd.DataFrame({'d': d, 'm': meet}).groupby('m').d; s, n = g.sum().values, g.count().values
    bs = [s[k].sum() / n[k].sum() for k in (rng.integers(0, len(s), len(s)) for _ in range(500))]
    return [int(len(d)), round(float(np.mean(d)), 5), round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]
for w in ['A', 'B']:
    x = a[a.window == w].set_index('race_id'); y = b[b.window == w].set_index('race_id'); j = x[['lp', 'meeting_id']].join(y[['lp']], rsuffix='_u', how='inner').join(R)
    j['d'] = j.lp - j.lp_u; j['yr'] = j.date.dt.year.astype(str)
    o = {'all': ci(j.d, j.meeting_id)}
    for col, lab in [('yr', 'year'), ('state', 'state'), ('cls', 'race type')]:
        for k_, g in j.groupby(col): o[f'{lab} {k_}'] = ci(g.d, g.meeting_id)
    j['incq'] = pd.qcut(j.inc.rank(method='first'), 4, labels=['least incomplete', 'q2', 'q3', 'most incomplete']).astype(str)
    j['lq'] = pd.qcut(j.light.rank(method='first'), 4, labels=['fewest lightly raced', 'q2', 'q3', 'most lightly raced']).astype(str)
    for col, lab in [('incq', 'incomplete-history share'), ('lq', 'lightly raced share')]:
        for k_, g in j.groupby(col): o[f'{lab}: {k_}'] = ci(g.d, g.meeting_id)
    o['races_with_no_incomplete_runner'] = ci(j[j.inc == 0].d, j[j.inc == 0].meeting_id)
    o['mean_incomplete_share'] = round(float(j.inc.mean()), 3); o['mean_lightly_raced_share'] = round(float(j.light.mean()), 3)
    OUT['A (judge 2024)' if w == 'A' else 'B (judge 2025-26)'] = o
json.dump(OUT, open('batch18/out_b18_experience_split.json' if (VA, VB) == ('U5E', 'U5') else f'batch18/out_b18_experience_split_{VA}_vs_{VB}.json', 'w'), indent=1); print(json.dumps(OUT, indent=0))
