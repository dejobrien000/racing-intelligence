"""Batch 19 E17: individual preparation and spacing preferences (research only; no prices). Not a generic quick-backup study: the question
is whether a horse's OWN preference repeats. Surprise = performance minus pre-race rating relative to the field (Engine v2.3 frame).
Preparation = runs separated by gaps of 60 days or less. For each horse and preparation:
 - fresh preference: first-up surprise minus the mean surprise of runs 2-5 of the same preparation;
 - progression: mean surprise of runs 3-5 minus runs 1-2;
 - spacing preference: mean surprise after 7-14 day gaps minus after 21-42 day gaps (within the preparation, runs 2+).
Repeatability: correlation of a horse's preference in its odd-numbered vs even-numbered preparations (horses with 2+ usable preparations
of each kind), against the same correlation with preparations shuffled between horses of the same age (chance level). Also: does the
population fresh effect change with age, and does an individual's spell length relate to its fresh preference?
Usage (from research/): python3 batch19/b19_spacing_preferences.py -> batch19/out_b19_spacing_preferences.json"""
import json, numpy as np, pandas as pd
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'dyn_nat_inn', 'age_n']).dropna(subset=['dyn_nat_inn'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U['gap'] = U.groupby('horse').date.diff().dt.days; U['newprep'] = U.gap.isna() | (U.gap > 60)
U['prep'] = U.groupby('horse').newprep.cumsum(); U['prun'] = U.groupby(['horse', 'prep']).cumcount() + 1
U['spell'] = np.where(U.newprep & U.gap.notna(), U.gap, np.nan)
P = U.groupby(['horse', 'prep']).agg(first=('dyn_nat_inn', lambda s: s.iloc[0]), runs=('dyn_nat_inn', 'size'), age=('age_n', 'first'), spell=('spell', 'first'),
                                     later=('dyn_nat_inn', lambda s: s.iloc[1:5].mean() if len(s) >= 3 else np.nan),
                                     early2=('dyn_nat_inn', lambda s: s.iloc[:2].mean() if len(s) >= 5 else np.nan), late3=('dyn_nat_inn', lambda s: s.iloc[2:5].mean() if len(s) >= 5 else np.nan)).reset_index()
P = P[P.prep >= 2]                     # skip each horse's first preparation held (its start may lie before our data)
P['fresh_pref'] = P['first'] - P.later; P['progression'] = P.late3 - P.early2
sp = U[(U.prun >= 2)].copy(); sp['short'] = sp.gap.between(7, 14); sp['long'] = sp.gap.between(21, 42)
S = sp.groupby(['horse', 'prep']).apply(lambda g: (g[g.short].dyn_nat_inn.mean() - g[g.long].dyn_nat_inn.mean()) if g.short.any() and g.long.any() else np.nan).rename('spacing_pref').reset_index()
P = P.merge(S, on=['horse', 'prep'], how='left')
rng = np.random.default_rng(17)
def repeat(col):
    d = P.dropna(subset=[col]).copy(); d['k'] = d.groupby('horse').cumcount()
    a = d[d.k % 2 == 0].groupby('horse')[col].mean(); b = d[d.k % 2 == 1].groupby('horse')[col].mean(); j = pd.concat([a, b], axis=1, keys=['a', 'b']).dropna()
    obs = float(j.corr().iloc[0, 1]); age = d.groupby('horse').age.first().reindex(j.index); null = []
    for _ in range(200):
        bb = j.b.groupby(age.fillna(0).values).transform(lambda s: s.sample(frac=1, random_state=int(rng.integers(1e9))).values); null.append(float(np.corrcoef(j.a, bb)[0, 1]))
    sd_a = float(d[col].std()); return {'horses': int(len(j)), 'preparations': int(len(d)), 'odd_vs_even_prep_corr': round(obs, 3), 'chance_mean': round(float(np.mean(null)), 3),
                                        'chance_p95': round(float(np.percentile(null, 95)), 3), 'sd_of_preference_kg': round(sd_a, 2)}
OUT = {'fresh_preference': repeat('fresh_pref'), 'progression_through_prep': repeat('progression'), 'short_vs_longer_spacing': repeat('spacing_pref')}
OUT['population_fresh_effect_by_age_kg'] = {str(int(a)): round(float(g.fresh_pref.mean()), 2) for a, g in P.dropna(subset=['fresh_pref']).groupby(P.age.clip(2, 8)) if len(g) >= 200}
d = P.dropna(subset=['fresh_pref', 'spell']); d['spell_band'] = pd.cut(d.spell, [60, 90, 150, 9999], labels=['61-90 d', '91-150 d', '151+ d']).astype(str)
OUT['fresh_effect_by_spell_length_kg'] = {k: [int(len(g)), round(float(g.fresh_pref.mean()), 2)] for k, g in d.groupby('spell_band')}
# does an individual's fresh record predict its NEXT first-up run beyond the population? (point in time: earlier preparations only)
P = P.sort_values(['horse', 'prep']); P['prior_fresh'] = P.groupby('horse').fresh_pref.transform(lambda s: s.shift().expanding().sum()); P['prior_n'] = P.groupby('horse').fresh_pref.transform(lambda s: s.shift().notna().cumsum())
q = P.dropna(subset=['fresh_pref', 'prior_fresh']); q = q[q.prior_n >= 1]; q['shrunk'] = q.prior_fresh / (q.prior_n + 3)
import statsmodels.formula.api as smf
m = smf.ols('fresh_pref ~ shrunk', q).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(q.horse)[0]})
OUT['own_fresh_record_predicts_next'] = {'preparations': int(m.nobs), 'coef_per_kg_of_shrunk_record': [round(float(m.params['shrunk']), 3), round(float(m.conf_int().loc['shrunk', 0]), 3), round(float(m.conf_int().loc['shrunk', 1]), 3)]}
json.dump(OUT, open('batch19/out_b19_spacing_preferences.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
