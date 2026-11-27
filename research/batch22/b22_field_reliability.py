"""Batch 22 C: does field experience say anything about how reliable a single performance is, beyond the horse's own experience and
the certainty of the race reference? (research only; no prices)
For each run better than expected (surprise > 0 kg) by a horse with at least one earlier run, in fields of 6+, outside Queensland,
2024 onward: 'next vs revised' = the horse's next performance minus its rating after this run (positive = the rule under-moved,
negative = over-moved). Regressed on the field's inexperience (share of runners with 5 or fewer runs held, measured before the race),
with the horse's own runs held (bands), the field's mean rating uncertainty (the race-reference certainty), the size of the surprise
and the spell before the next run as controls; cluster-robust by horse. Run for three rules: Engine v2.3, history-completeness +
certainty-weighting (gentle), stronger + history-completeness + certainty-weighting. If field inexperience has no coefficient beyond
the controls, it carries no extra reliability information and no field term belongs in the update.
Usage (from research/): python3 batch22/b22_field_reliability.py"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
RULES = {'Engine v2.3': '/tmp/cand/frames/C2_national.parquet', 'gentle + certainty-weighting': '/tmp/cand/frames/PWH3B_national.parquet',
         'stronger + certainty-weighting': '/tmp/cand/frames/PWH8B_national.parquet'}
OUT = {}
for lab, f in RULES.items():
    U = pd.read_parquet(f, columns=['race', 'horse', 'date', 'state', 'field', 'dyn_nat', 'dyn_nat_inn', 'dyn_nat_sd']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
    U['k'] = U.groupby('horse').cumcount(); g = U.groupby('horse')
    U['r1'] = g.dyn_nat.shift(-1); U['p1'] = (U.dyn_nat + U.dyn_nat_inn).groupby(U.horse).shift(-1); U['gap1'] = (g.date.shift(-1) - U.date).dt.days
    rg = U.groupby('race'); U['light'] = rg.k.transform(lambda s: float((s <= 5).mean())); U['fsd'] = rg.dyn_nat_sd.transform('mean')
    X = U[(U.dyn_nat_inn > 0) & (U.k >= 1) & (U.field >= 6) & (U.state != 'QLD') & (U.date >= '2024-01-01') & U.p1.notna()].copy()
    X['nvr'] = X.p1 - X.r1; X['kb'] = pd.cut(X.k, [0, 2, 5, 11, 999], labels=['1-2', '3-5', '6-11', '12+']).astype(str); X['spell'] = (X.gap1 >= 60).astype(float)
    m = smf.ols('nvr ~ light + C(kb) + fsd + dyn_nat_inn + spell', X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(X.horse)[0]})
    o = {'runs': int(m.nobs), 'field_inexperience_coef_kg': [round(float(m.params['light']), 3)] + [round(float(v), 3) for v in m.conf_int().loc['light']],
         'field_uncertainty_coef_kg_per_kg': round(float(m.params['fsd']), 3)}
    for kb in ['1-2', '3-5']:   # lightly raced horses only: the case the stronger rule acts on most
        y = X[X.kb == kb]; mm = smf.ols('nvr ~ light + fsd + dyn_nat_inn + spell', y).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(y.horse)[0]})
        o[f'own {kb} runs held: field inexperience coef'] = [round(float(mm.params['light']), 3)] + [round(float(v), 3) for v in mm.conf_int().loc['light']] + [int(mm.nobs)]
    X['ft'] = pd.cut(X.light, [-0.01, 0.083, 0.417, 1.01], labels=['established', 'mixed', 'inexperienced']).astype(str)
    o['mean next-vs-revised by field type and own experience (kg)'] = {f'{a} | {b}': round(float(v), 2) for (a, b), v in X.groupby(['ft', 'kb']).nvr.mean().items()}
    OUT[lab] = o; print(lab, json.dumps(o)[:900], flush=True)
json.dump(OUT, open('batch22/out_b22_field_reliability.json', 'w'), indent=1)
