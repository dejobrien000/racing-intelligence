"""Freeze the NSW/Vic/ACT candidates (development fit, before any race from 25 Nov 2026):
  nat_v1 = common features F + A + R + national dynamic rating
  nat_v2 = nat_v1 + horse records (course configuration, going band, distance band; k = 1)
Writes benchmarks/candidates_national_common/manifest.json with coefficients and the development scaling (sd) of each
feature after race-centring, so pre-race scoring reproduces the fit exactly."""
import json, os, hashlib, numpy as np, pandas as pd
src = open('inv30_horse_suitability.py').read().split("best = None")[0]
exec(src)
add_records(1)
F_ = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform']; A_ = ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']; R_ = ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays']
N = U[(U.state != 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1]
V1 = F_ + A_ + R_ + ['dyn_nat']; V2 = V1 + ['c_rec', 'g_rec', 'd_rec']
nx = prep(N, V2)
dev = nx[nx.period == 'development']
sd = {}
for c in V2:
    v = N[c].astype(float); cen = v - v.groupby(N.race_id).transform('mean'); sd[c] = float(cen[N.period == 'development'].std())
b1 = fit(nx, V1); b2 = fit(nx, V2)
r1 = score(nx, V1, b1); r2 = score(nx, V2, b2)
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
os.makedirs('benchmarks/candidates_national_common', exist_ok=True)
json.dump({'frozen_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'scope': 'NSW, Vic, ACT races (Breednet full fields; jump-outs excluded); fields of 6+',
           'dynamic_rating_params': pn, 'records_k': 1, 'dev_sd_after_race_centring': sd,
           'candidates': {'nat_v1 (common + national rating)': dict(zip(V1, map(float, b1))), 'nat_v2 (+ horse records)': dict(zip(V2, map(float, b2)))},
           'eval_2025_26': {'nat_v1': {'races': len(r1), 'fit_%': round(fit_pct(r1), 2), 'top_pick_%': round(100 * r1.hit.mean(), 1)},
                            'nat_v2': {'races': len(r2), 'fit_%': round(fit_pct(r2), 2), 'top_pick_%': round(100 * r2.hit.mean(), 1)}},
           'code_sha256_16': {p: h(p) for p in ['inv30_horse_suitability.py', 'dyn_rating.py', 'dyn_rating_innov.py', 'national.py', 'freeze_b5_national_common.py']},
           'data_sha256_16': {'national_runs.parquet': h('national_runs.parquet')}, 'prospective_rule': 'only races dated 2026-11-25 or later count; no refit'},
          open('benchmarks/candidates_national_common/manifest.json', 'w'), indent=1)
print('v1', round(fit_pct(r1), 2), round(100 * r1.hit.mean(), 1), '| v2', round(fit_pct(r2), 2), round(100 * r2.hit.mean(), 1))
m, lo, hi, p = boot_diff(r1, r2); print('v2 vs v1 gain', round(m, 4), round(lo, 4), round(hi, 4))
