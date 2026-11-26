"""Batch 14 follow-up: joint test of the small physical/rider candidates on the Queensland PRODUCTION engine (v2.1.3); orig. docstring: does the 'uneven last 600' finding add anything to the Queensland PRODUCTION engine (Engine v2.1.3, from 27 Nov)?
Offset = production v2.1.3 exactly as it runs (frozen v1 + v2.1.3 dev-fit terms). Added inputs, all pre-race:
  dip_last  = unevenness (mean of the last three 200 m sections minus the weakest, vs the field) at the horse's most recent tracked run
  dip_prior = the horse's shrunk mean unevenness over all earlier tracked runs (3 runs' weight towards the field average)
  (+ a missing flag when the horse has no earlier tracked run)
Windows: A = add-on fitted before 2024, judged on 2024 (clean); B = fitted before 2025, judged on 2025-26 (re-used period).
Identical races; per-race log-likelihood gain with a meeting bootstrap. Research only: nothing here changes production."""
import json, numpy as np, pandas as pd, os, sys
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", "pd.read_parquet('engine/frames/national_v3.parquet')"); exec(src)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); C21 = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))
Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); COLS = list(E.QCOEF)
x = E.qld_frame(U); x = E.zcols(x, COLS); PV = C21['coefficients_per_dev_sd']
off = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS]); x = build_terms(x, NEW)
e0 = off + x[['t::' + t for t in NEW]].fillna(0.0).values @ np.array([Q3['coef_per_term_sd_dev_fit'][t] for t in NEW])
# last-start physical information (strictly earlier dates): dip (Batch 14), last-start profile flags, abnormal decline vs the horse's own
# usual finishing slope (z < -1.5, prior runs only, within-horse sd from b14f_norms); rider tendencies (b14f_riders)
P = pd.read_parquet('/home/claude/b14/profiles.parquet', columns=['state', 'horse', 'meeting_date', 'dip', 'profile', 'slope'])
P = P[P.state == 'QLD'].dropna(subset=['slope']).sort_values(['horse', 'meeting_date']).copy()
P['pf'] = (P.profile == 'Progressive fade').astype(float); P['lf'] = (P.profile == 'Late fade').astype(float)
g = P.groupby('horse'); cnt = g.cumcount(); P['usual'] = (g.slope.cumsum() - P.slope) / (cnt + 3.0)          # shrunk mean of EARLIER runs
P['dz'] = np.where(cnt >= 3, (P.slope - P.usual) / 0.466, np.nan); P['decl'] = (P.dz < -1.5).astype(float)
P['dip_prior'] = g.dip.cumsum() / (cnt + 4.0)
T = P[['horse', 'meeting_date', 'dip', 'dip_prior', 'pf', 'lf', 'decl']].rename(columns={'meeting_date': 'tdate', 'dip': 'dip_last'})
T['tdate'] = pd.to_datetime(T.tdate)
x['_d'] = pd.to_datetime(x.meeting_date); x['_i'] = np.arange(len(x))
xs = x[['_i', 'horse', '_d']].sort_values('_d'); Ts = T.sort_values('tdate')
mm = pd.merge_asof(xs, Ts, left_on='_d', right_on='tdate', by='horse', allow_exact_matches=False).sort_values('_i')
for c in ['dip_last', 'dip_prior', 'pf', 'lf', 'decl']: x[c] = mm[c].values
x['phys_miss'] = x.dip_last.isna().astype(float); x[['dip_last', 'dip_prior', 'pf', 'lf', 'decl']] = x[['dip_last', 'dip_prior', 'pf', 'lf', 'decl']].fillna(0.0)
R = pd.read_parquet('/home/claude/b14/rider_priors.parquet'); R = R[R.state == 'QLD'][['race_id', 'horse', 'r_hold', 'r_timing', 'r_hold_n', 'h_timing']].drop_duplicates(['race_id', 'horse'])
x = x.merge(R, on=['race_id', 'horse'], how='left')
x['r_miss'] = (x.r_hold.isna() | (x.r_hold_n.fillna(0) < 50)).astype(float)
for c in ['r_hold', 'r_timing', 'h_timing']: x[c] = x[c].where(x.r_miss == 0).fillna(0.0)
sdh, sdr = x.h_timing[x.h_timing != 0].std(), x.r_hold[x.r_hold != 0].std(); x['hxr'] = (x.h_timing / sdh) * (x.r_hold / sdr)
SETS = {'profile flags only (pf, lf, decl)': ['pf', 'lf', 'decl', 'phys_miss'], 'dip only (Batch 14)': ['dip_last', 'dip_prior', 'phys_miss'],
        'rider tendencies only': ['r_hold', 'r_timing', 'hxr', 'r_miss'],
        'all together': ['dip_last', 'dip_prior', 'pf', 'lf', 'decl', 'phys_miss', 'r_hold', 'r_timing', 'hxr', 'r_miss']}
x = E.zcols(x, sorted(set(sum(SETS.values(), []))))
out = {'coverage: Qld rows with an earlier tracked run %': round(100 * (1 - x.phys_miss.mean()), 1), 'last start progressive fade %, late fade %, abnormal decline %': [round(100 * x[c][x.phys_miss == 0].mean(), 1) for c in ['pf', 'lf', 'decl']]}
for nm, ADD in SETS.items():
    out[nm] = {}
    for W, (fe, lo, hi) in {'A (judge 2024, clean)': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B (judge 2025-26, re-used)': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
        fm = (x._d < fe) & x.period.notna(); em = (x._d >= lo) & (x._d < hi)
        b = E.fit(x, ADD, fm, 1e-6, offset=e0); e1 = e0 + x[[c + '_z' for c in ADD]].values @ b
        m0, m1 = E.metrics(x, e0, em), E.metrics(x, e1, em); dd = E.diff(m0, m1)
        out[nm][W] = {'coef_per_sd': dict(zip(ADD, [round(float(v), 4) for v in b])), **{k: dd[k] for k in ['races', 'lp', 'lp_lo', 'lp_hi', 'hit', 'hit_lo', 'hit_hi', 'top3']}}
        print(nm, W, {k: out[nm][W][k] for k in ['lp', 'lp_lo', 'lp_hi', 'hit']}, flush=True)
json.dump(out, open('batch14/followup/out_qld_engine_joint.json', 'w'), indent=1)
