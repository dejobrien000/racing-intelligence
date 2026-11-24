"""Freeze 'combined_v1 + national dynamic rating' before any race from 25 Nov 2026 exists: national rating with the
parameters tuned on pre-2025 races (all states held), coefficients fitted on Qld development races only.
Writes benchmarks/candidates_b4_national/manifest.json. Needs national_runs.parquet (national.py, full backfill)."""
import json, os, hashlib, numpy as np, pandas as pd
import dyn_rating as DR
from clogit_tools import eligible, prep, fit
P_ = {'s_kg': 4.5, 'q_kg2_per_day': 0.05, 'sig0_kg': 5.0, 'debut_offset_kg': 2.0}
U = pd.read_parquet('national_runs.parquet')
d = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                  'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
P = DR.prepare(d).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, sd, _ = DR.run(P, P_['s_kg'], P_['q_kg2_per_day'], P_['sig0_kg'], P_['debut_offset_kg'])
U['dyn_nat'] = pd.Series(mu, index=P.idx.values).reindex(np.arange(len(U))).values
qn = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_nat']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id'])
X = pd.read_parquet('features.parquet').merge(qn, on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
man_b4 = json.load(open('benchmarks/candidates_b4/manifest.json')); BENCH = list(man_b4['coefficients_per_dev_sd']['combined_v1'])
x = prep(eligible(X), sorted(set(BENCH + ['dyn_nat'])))
b = fit(x, BENCH + ['dyn_nat'])
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
os.makedirs('benchmarks/candidates_b4_national', exist_ok=True)
json.dump({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'candidate': 'combined_v1 + national dynamic rating', 'dynamic_rating_params': P_,
           'params_tuned_on': 'all states held, races before 2025-01-01 (inv25_national_dynamic.py)', 'coefficients_fit_on': 'Qld tracked development races (before 2025-01-01)',
           'coefficients_per_dev_sd': dict(zip(BENCH + ['dyn_nat'], map(float, b))),
           'code_sha256_16': {p: h(p) for p in ['dyn_rating.py', 'national.py', 'inv25_national_dynamic.py', 'freeze_b4_national.py', 'features.py', 'clogit_tools.py']},
           'data_sha256_16': {p: h(p) for p in ['national_runs.parquet', 'features.parquet']},
           'prospective_rule': 'only races dated 2026-11-25 or later count; no refit'}, open('benchmarks/candidates_b4_national/manifest.json', 'w'), indent=1)
print('frozen', dict(zip(BENCH + ['dyn_nat'], np.round(b, 3)))['dyn_nat'])
