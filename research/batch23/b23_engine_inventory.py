"""Batch 23 B5: inventory of the inputs the production engines actually use, with fitted coefficients, and how much each feature family
actually moves a horse's score in served forecasts (research documentation; changes nothing).
Engines: national Engine v2.3 (benchmarks/engine_v2_3: layer 1 candidates_national_common nat_v2, layer 2 engine_v2 NSW_VIC_ACT
family, layer 3 engine_v2_2 terms) and Queensland Engine v2.1.3 (benchmarks/engine_v2_1_3 QLD family on the v2.1 operational score).
Coefficients are per development standard deviation of the race-centred input (the units the model uses); dividing by the input's sd
gives the effect per unit of the input. Raw coefficients are NOT comparable as importance (inputs are correlated and differently
scaled), so influence is measured from served forecasts instead: for every race on the served days, the within-race spread (standard
deviation) of each family's contribution, in model units and in kg (model units / score_per_kg_total). Inputs that are trained but not
served show zero spread. Outputs: batch23/engine_inventory.csv, batch23/out_b23_family_influence.json.
Usage (from research/): python3 batch23/b23_engine_inventory.py <YYYYMMDD> [...]"""
import sys, json, glob, numpy as np, pandas as pd
rows = []
m1 = json.load(open('benchmarks/engine_v2_3/candidates_national_common.json'))
c1 = m1['candidates']['nat_v2 (+ horse records)']; sd1 = m1.get('dev_sd_after_race_centring', {})
coef1 = c1.get('coefficients_per_dev_sd', c1)
for k, v in (coef1.items() if isinstance(coef1, dict) else []):
    if isinstance(v, (int, float)): rows.append({'engine': 'national v2.3', 'layer': '1 common + rating (nat_v2)', 'family': '', 'input': k, 'coef_per_sd': v, 'input_sd': sd1.get(k)})
for eng, path, fam in [('national v2.3', 'benchmarks/engine_v2_3/engine_v2.json', 'NSW_VIC_ACT'), ('Queensland v2.1.3', 'benchmarks/engine_v2_1_3/manifest.json', 'QLD')]:
    F = json.load(open(path))['families'][fam]
    for fname, terms in F['term_families'].items():
        for t in terms:
            rows.append({'engine': eng, 'layer': '2 engine v2 family terms', 'family': fname, 'input': t, 'coef_per_sd': F['coef_per_term_sd_all_races'].get(t), 'input_sd': F['term_dev_sd'].get(t)})
    rows.append({'engine': eng, 'layer': 'scale', 'family': '', 'input': 'score_per_kg_total', 'coef_per_sd': F.get('score_per_kg_total'), 'input_sd': None})
M3 = json.load(open('benchmarks/engine_v2_3/engine_v2_2.json'))
fam3 = {t: f for f, ts in M3.get('term_families', {}).items() for t in ts}
for t in M3['terms']: rows.append({'engine': 'national v2.3', 'layer': '3 engine v2.2 terms', 'family': fam3.get(t, ''), 'input': t, 'coef_per_sd': M3['coef_per_sd_all_races'].get(t), 'input_sd': M3['term_sd_all_races'].get(t)})
I = pd.DataFrame(rows); I['coef_per_unit'] = I.coef_per_sd / I.input_sd.replace(0, np.nan)
I.to_csv('batch23/engine_inventory.csv', index=False); print('inventory rows', len(I), I.groupby(['engine', 'layer']).size().to_dict())
# influence from served v2 prediction files
OUT = {}
for D in sys.argv[1:]:
    for f in sorted(glob.glob(f'prospective/prerace/{D}/*/v2_pred_*_runners.csv')):
        x = pd.read_csv(f); ven = f.split('/')[-2]
        g = [c for c in x.columns if c.startswith('grp_') or c.startswith('v2+ ')]
        if not g or 'race_no' not in x: continue
        fam = 'QLD' if str(x['family'].iloc[0]).upper().startswith('QLD') else 'NAT'   # the file's own model family
        for c in g:
            s = x.groupby('race_no')[c].std().dropna()
            OUT.setdefault(fam, {}).setdefault(c, []).extend(s.tolist())
kg = {'NAT': float(I[(I.engine == 'national v2.3') & (I.input == 'score_per_kg_total')].coef_per_sd.iloc[0]), 'QLD': float(I[(I.engine == 'Queensland v2.1.3') & (I.input == 'score_per_kg_total')].coef_per_sd.iloc[0])}
R = {}
for fam, d in OUT.items():
    R[fam] = {c: {'races': len(v), 'within_race_sd_units': round(float(np.mean(v)), 4), 'within_race_sd_kg': round(float(np.mean(v)) / kg[fam], 2), 'races_with_zero_spread': int(sum(1 for z in v if z < 1e-9))}
              for c, v in sorted(d.items(), key=lambda kv: -np.mean(kv[1]))}
json.dump({'kg_per_unit_scale': kg, 'families': R}, open('batch23/out_b23_family_influence.json', 'w'), indent=1); print(json.dumps(R, indent=1)[:3500])
