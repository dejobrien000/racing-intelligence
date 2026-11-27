"""Batch 17 B11: exceptional positive performances - how much of a big run is kept? Research only; point in time; no prices.
perf = pre-race rating + surprise (kg). Every reference point (previous 5/10/20 runs, career best, second best, repeatable upper = second
best of the last six, own variability, trajectory) uses only runs BEFORE the exceptional run. Outcomes use later runs.
For each band of positive surprise (vs the pre-race rating r0): next-start and next-3 / next-5 average performance relative to r0, to the
revised rating r1 and to the exceptional figure pE; share of the improvement kept; how often the new level is repeated (within 1 kg of pE);
how often the horse races again within 365 days. Split by experience, age, trajectory and whether the run was unprecedented (more than
3 kg above the previous career best). Then the next-run residual (vs the revised rating) by band under v2.3, cap only and the update rule.
Usage (from research/): python3 batch17/b17_positive_outliers.py C2=<frame> CAP=<frame> UR=<frame>  -> batch17/out_b17_positive_outliers.json"""
import sys, json, numpy as np, pandas as pd
OUT = {}
BANDS = [2, 4, 6, 8, 10, 99]; LAB = ['2-4', '4-6', '6-8', '8-10', '10+']
def build(path):
    U = pd.read_parquet(path, columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
    U['perf'] = U.dyn_nat + U.dyn_nat_inn; g = U.groupby('horse'); U['k'] = g.cumcount()
    n = len(U); ref = {c: np.full(n, np.nan) for c in ['m5', 'm10', 'm20', 'best', 'second', 'rep6', 'psd', 'slope5']}
    fut = {c: np.full(n, np.nan) for c in ['p1', 'p3', 'p5', 'r1', 'rep5', 'gap1']}
    dates = U.date.values.astype('datetime64[D]').astype(np.int64)
    for h, idx in g.indices.items():
        p = U.perf.values[idx]; r = U.dyn_nat.values[idx]; dd = dates[idx]
        for j in range(len(idx)):
            q = p[:j]; q = q[~np.isnan(q)]
            if len(q):
                ref['m5'][idx[j]] = q[-5:].mean(); ref['m10'][idx[j]] = q[-10:].mean() if len(q) >= 6 else np.nan; ref['m20'][idx[j]] = q[-20:].mean() if len(q) >= 11 else np.nan
                s_ = np.sort(q); ref['best'][idx[j]] = s_[-1]; ref['second'][idx[j]] = s_[-2] if len(s_) >= 2 else np.nan
                l6 = np.sort(q[-6:]); ref['rep6'][idx[j]] = l6[-2] if len(l6) >= 3 else np.nan
                if len(q) >= 5: ref['psd'][idx[j]] = q.std(ddof=1); ref['slope5'][idx[j]] = np.polyfit(np.arange(5), q[-5:], 1)[0]
            nx = p[j + 1:j + 6]
            if j + 1 < len(idx):
                fut['p1'][idx[j]] = nx[0]; fut['r1'][idx[j]] = r[j + 1]; fut['gap1'][idx[j]] = dd[j + 1] - dd[j]
                if len(nx) >= 3: fut['p3'][idx[j]] = np.nanmean(nx[:3])
                if len(nx) >= 5: fut['p5'][idx[j]] = np.nanmean(nx[:5])
                if not np.isnan(p[j]): fut['rep5'][idx[j]] = float(np.nansum(nx >= p[j] - 1.0))
    for c, v in {**ref, **fut}.items(): U[c] = v
    U['last_date'] = g.date.transform('max'); return U
def summarise(E):
    r0, pE = E.dyn_nat, E.perf
    o = {'runs': int(len(E)), 'raced_again_365d': round(float(((E.gap1 <= 365) & E.p1.notna()).mean()), 3)}
    for c, lab in [('p1', 'next'), ('p3', 'next3_avg'), ('p5', 'next5_avg')]:
        x = E[E[c].notna()]
        o[lab] = {'n': int(len(x)), 'vs_pre_rating': round(float((x[c] - x.dyn_nat).mean()), 2), 'vs_exceptional_run': round(float((x[c] - x.perf).mean()), 2),
                  'share_of_improvement_kept': round(float(((x[c] - x.dyn_nat) / (x.perf - x.dyn_nat)).median()), 2)}
    x = E[E.p1.notna() & E.r1.notna()]; o['next_vs_revised_rating'] = round(float((x.p1 - x.r1).mean()), 2); o['revised_rating_moved_kg'] = round(float((x.r1 - x.dyn_nat).mean()), 2)
    x = E[E.p5.notna()]; o['repeat_within_1kg_in_next5_share'] = round(float((x.rep5 >= 1).mean()), 3)
    return o
frames = dict(a.split('=', 1) for a in sys.argv[1:])
for lab, path in frames.items():
    U = build(path); OUT[lab] = {}
    E = U[(U.date >= '2023-01-01') & U.dyn_nat_inn.notna() & (U.k >= 1)].copy()
    E['band'] = pd.cut(E.dyn_nat_inn, BANDS, labels=LAB, right=False).astype(str)
    E['exp'] = pd.cut(E.k, [0, 5, 15, 9999], labels=['1-5 starts', '6-15', '16+'], right=True).astype(str)
    E['traj'] = np.where(E.slope5 > 0.5, 'improving', np.where(E.slope5 < -0.5, 'declining', np.where(E.slope5.notna(), 'flat', 'short history')))
    E['kind'] = np.where(E.best.isna(), 'no best yet', np.where(E.perf > E.best + 3, 'unprecedented (>3 kg above career best)', np.where(E.perf >= E.best - 2, 'near career best', 'below career best (return)')))
    E['z_own'] = E.dyn_nat_inn / E.psd
    P = E[E.band != 'nan']
    OUT[lab]['distribution'] = {b: int((P.band == b).sum()) for b in LAB}
    OUT[lab]['next_residual_by_band'] = {b: round(float((x.p1 - x.r1).mean()), 2) for b, x in P[P.p1.notna() & P.r1.notna()].groupby('band')}
    if lab == 'C2':
        OUT[lab]['by_band'] = {b: summarise(x) for b, x in P.groupby('band')}
        OUT[lab]['by_band_x_experience'] = {f'{b} | {e}': summarise(x) for (b, e), x in P[P.band.isin(['6-8', '8-10', '10+'])].groupby(['band', 'exp']) if len(x) >= 150}
        OUT[lab]['by_band_x_kind'] = {f'{b} | {e}': summarise(x) for (b, e), x in P[P.band.isin(['4-6', '6-8', '8-10', '10+'])].groupby(['band', 'kind']) if len(x) >= 150}
        OUT[lab]['by_band_x_trajectory'] = {f'{b} | {e}': summarise(x) for (b, e), x in P[P.band.isin(['6-8', '8-10', '10+'])].groupby(['band', 'traj']) if len(x) >= 150}
        OUT[lab]['deviation_measures_mean_by_band'] = {b: {c: round(float((x.perf - x[c]).mean()), 2) for c in ['m5', 'm10', 'm20', 'best', 'second', 'rep6']} | {'own_sd_units': round(float(x.z_own.mean()), 2)} for b, x in P.groupby('band')}
    # experienced horses with an unprecedented run and no improving trajectory: the isolated-peak case, next residual by band
    Q = P[(P.k >= 16) & (P.kind.str.startswith('unprecedented')) & (P.traj != 'improving') & P.p1.notna() & P.r1.notna()]
    OUT[lab]['isolated_peak_experienced_next_residual'] = {b: [int(len(x)), round(float((x.p1 - x.r1).mean()), 2), round(float((x.p1 - x.r1).std() / np.sqrt(max(len(x), 1))), 2)] for b, x in Q.groupby('band')}
    Q2 = P[(P.k <= 5) & P.p1.notna() & P.r1.notna()]
    OUT[lab]['lightly_raced_next_residual'] = {b: [int(len(x)), round(float((x.p1 - x.r1).mean()), 2), round(float((x.p1 - x.r1).std() / np.sqrt(max(len(x), 1))), 2)] for b, x in Q2.groupby('band')}
    Q3 = P[(P.k >= 16) & P.kind.isin(['near career best', 'below career best (return)']) & P.p1.notna() & P.r1.notna()]
    OUT[lab]['experienced_return_to_level_next_residual'] = {b: [int(len(x)), round(float((x.p1 - x.r1).mean()), 2), round(float((x.p1 - x.r1).std() / np.sqrt(max(len(x), 1))), 2)] for b, x in Q3.groupby('band')}
    print(lab, 'done', flush=True)
json.dump(OUT, open('batch17/out_b17_positive_outliers.json', 'w'), indent=1); print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ('distribution', 'next_residual_by_band', 'isolated_peak_experienced_next_residual', 'lightly_raced_next_residual', 'experienced_return_to_level_next_residual')} for k, v in OUT.items()}, indent=0))
