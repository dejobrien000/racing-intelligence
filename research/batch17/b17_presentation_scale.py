"""Batch 17 A6: stable national presentation scale - demonstration only (no engine calculation, ranking or chance changes).
Ability ratings from different rating versions differ in both their zero point and their spread. Proposal: map each version onto one
display scale with a linear transform fitted on a FIXED reference population (all runners in 2025 Benchmark 64-72 races, all states):
    display = 0 + (rating - mean_ref_version) / sd_ref_version * SD_REF          (SD_REF = Engine v2.3's spread on that population)
so a reference-population runner of average ability reads 0 kg in every version and one standard deviation reads the same number of kg.
Checks: (1) offset and spread per version before and after; (2) for the same horse on the same date, how far apart versions are before
and after mapping (what remains is genuine reassessment); (3) Queensland (v3) vs national (v2.3) on horses rated by both;
(4) examples: established high-rated, established ordinary, lightly raced, Queensland. Usage: python3 batch17/b17_presentation_scale.py"""
import json, numpy as np, pandas as pd
V = {'Engine v2.2 rating': 'engine/frames/national.parquet', 'Engine v2.3 rating': 'engine/frames/national_c2.parquet', 'Queensland v3 rating': 'engine/frames/national_v3.parquet',
     'Update-rule candidate rating': 'engine/frames/national_update_rule.parquet'}
cols = ['race_id', 'horse', 'date', 'state', 'bm', 'class_label', 'dyn_nat', 'n_prior']
F = {}
for k, p in V.items():
    x = pd.read_parquet(p, columns=[c for c in cols if c != 'n_prior'] + ['dyn_nat_inn']); x['k'] = x.sort_values(['date']).groupby('horse').cumcount(); F[k] = x
ref = lambda x: x[(x.date.dt.year == 2025) & (x.class_label == 'Benchmark') & pd.to_numeric(x.bm, errors='coerce').between(64, 72) & x.dyn_nat.notna()]
OUT = {'reference_population': '2025 Benchmark 64-72 races, all states', 'versions': {}}
SD_REF = float(ref(F['Engine v2.3 rating']).dyn_nat.std())
for k, x in F.items():
    r = ref(x); m, s = float(r.dyn_nat.mean()), float(r.dyn_nat.std())
    x['display'] = (x.dyn_nat - m) / s * SD_REF
    OUT['versions'][k] = {'reference_runs': int(len(r)), 'raw_mean_kg': round(m, 2), 'raw_sd_kg': round(s, 2), 'scale_factor_to_display': round(SD_REF / s, 3)}
OUT['display_sd_kg'] = round(SD_REF, 2)
base = F['Engine v2.3 rating'][['race_id', 'horse', 'date', 'state', 'k', 'dyn_nat', 'display']]
for k in [v for v in F if v != 'Engine v2.3 rating']:
    j = base.merge(F[k][['race_id', 'horse', 'dyn_nat', 'display']], on=['race_id', 'horse'], suffixes=('', '_o')); j = j[j.date >= '2025-01-01']
    raw = (j.dyn_nat_o - j.dyn_nat); disp = (j.display_o - j.display)
    OUT['versions'][k]['vs_v2_3_same_runner_same_day'] = {'runs': int(len(j)), 'raw_gap_mean_kg': round(float(raw.mean()), 2), 'raw_gap_abs_mean_kg': round(float(raw.abs().mean()), 2),
        'display_gap_mean_kg': round(float(disp.mean()), 2), 'display_gap_abs_mean_kg': round(float(disp.abs().mean()), 2),
        'display_gap_p90_abs_kg': round(float(disp.abs().quantile(0.9)), 2), 'rank_corr_within_race': round(float(j.groupby('race_id').apply(lambda g: g.dyn_nat.corr(g.dyn_nat_o, method='spearman') if len(g) > 3 else np.nan).mean()), 3)}
# Queensland horses: national v2.3 vs Queensland v3 rating
q = base.merge(F['Queensland v3 rating'][['race_id', 'horse', 'dyn_nat', 'display']], on=['race_id', 'horse'], suffixes=('', '_q'))
q = q[(q.date >= '2025-01-01') & (q.state == 'QLD')]
OUT['queensland_horses_v3_vs_v2_3'] = {'runs': int(len(q)), 'raw_gap_mean_kg': round(float((q.dyn_nat_q - q.dyn_nat).mean()), 2), 'display_gap_mean_kg': round(float((q.display_q - q.display).mean()), 2),
                                       'display_gap_abs_mean_kg': round(float((q.display_q - q.display).abs().mean()), 2)}
# examples on the latest date in the frames
last = base.date.max(); L = base[base.date >= last - pd.Timedelta(days=21)].sort_values('date').groupby('horse').tail(1)
ex = {}
pick = {'established, high-rated': L[(L.k >= 15)].sort_values('dyn_nat').tail(1), 'established, ordinary': L[(L.k >= 15) & L.dyn_nat.between(L.dyn_nat.quantile(0.45), L.dyn_nat.quantile(0.55))].head(1),
        'lightly raced': L[L.k.between(1, 3)].head(1), 'Queensland': L[(L.state == 'QLD') & (L.k >= 8)].head(1)}
for lab, r in pick.items():
    if not len(r): continue
    r = r.iloc[0]; e = {'horse': r.horse, 'date': str(r.date.date()), 'runs_before': int(r.k)}
    for k, x in F.items():
        y = x[(x.race_id == r.race_id) & (x.horse == r.horse)]
        if len(y): e[k] = {'raw_kg': round(float(y.dyn_nat.iloc[0]), 1), 'display_kg': round(float(y.display.iloc[0]), 1)}
    ex[lab] = e
OUT['examples'] = ex
json.dump(OUT, open('batch17/out_b17_presentation_scale.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:3500])
