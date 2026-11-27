"""Batch 20 B5: supported vs unsupported big runs, and why exposed progressive horses keep little (research only; no prices).
Uses the Batch 18 sustainability construction (exec'd unchanged) on Engine v2.3. For big runs (surprise >= 2 kg) by horses with 6+ runs held:
 - how far the rating itself moved (update share = revised rating minus pre-race rating, over the surprise);
 - what the next run kept (kept share) and the next run relative to the REVISED rating (positive = rating still too low);
 split by experience, trajectory, variability, distance from the previous best and the repeatable upper level, preparation stage,
 trainer change, and familiar vs unfamiliar distance. If 'next vs revised' is about 0, the low kept share is ordinary regression to the mean
 that the rating already allows for; if clearly positive or negative, the rating under- or over-reacts for that group.
Point in time: every split uses information from before the big run. Follow-up counts reported per horizon.
Usage (from research/): python3 batch20/b20_supported.py -> batch20/out_b20_supported.json"""
import json, numpy as np, pandas as pd
src = open('batch18/b18_sustainability.py').read(); src = src[:src.index('OUT = {')]; exec(src)
X = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'tkey', 'distance_m']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U = U.join(X[['tkey', 'distance_m']]); g = U.groupby('horse')
U['var6'] = g.dyn_nat_inn.transform(lambda s: s.shift().rolling(6, min_periods=4).std())
U['tr_change'] = (U.tkey != g.tkey.shift()) & g.tkey.shift().notna()
U['gap'] = g.date.diff().dt.days; U['newprep'] = U.gap.isna() | (U.gap > 60); U['prep'] = U.newprep.groupby(U.horse).cumsum(); U['prun'] = U.groupby(['horse', 'prep']).cumcount() + 1
U['dband'] = pd.cut(U.distance_m, [0, 1150, 1450, 1750, 9999]).astype(str)
U['dist_runs_before'] = U.groupby(['horse', 'dband']).cumcount()
E = E.join(U[['var6', 'tr_change', 'prun', 'dist_runs_before']])
E = E[E.k >= 6].copy()
E['upd'] = (E.r1 - E.dyn_nat) / (E.perf - E.dyn_nat); E['kept1'] = (E.p1 - E.dyn_nat) / (E.perf - E.dyn_nat); E['nvr'] = E.p1 - E.r1
def S(x):
    y = x[x.p1.notna()]
    if len(y) < 80: return None
    o = {'runs': int(len(x)), 'with_next_run': int(len(y)), 'surprise_kg_mean': round(float((y.perf - y.dyn_nat).mean()), 2), 'rating_update_share_median': round(float(y.upd.median()), 3),
         'kept_next_median': round(float(y.kept1.median()), 3), 'next_vs_revised_kg': round(float(y.nvr.mean()), 2), 'next_vs_revised_se': round(float(y.nvr.std() / np.sqrt(len(y))), 2)}
    z = x[x.m5.notna()]; o['with_5_more'] = int(len(z))
    if len(z) >= 80: o['kept_next5_median'] = round(float(((z.m5 - z.dyn_nat) / (z.perf - z.dyn_nat)).median()), 3)
    return o
E['exp'] = pd.cut(E.k, [5, 11, 19, 999], labels=['6-11', '12-19', '20+']).astype(str)
E['var_band'] = pd.qcut(E.var6.rank(method='first'), 3, labels=['steady', 'middling', 'erratic']).astype(str)
E['vs_best'] = pd.cut(E.perf - E.best, [-99, 0, 2, 4, 99], labels=['at or below best', '0-2 above', '2-4 above', '4+ above']).astype(str)
E['vs_upper'] = pd.cut(E.perf - E.rep6, [-99, 0, 3, 99], labels=['within upper level', '0-3 above upper', '3+ above upper']).astype(str)
E['stage'] = pd.cut(E.prun, [0, 1, 3, 99], labels=['first-up', '2nd-3rd up', '4th+ up']).astype(str)
E['familiar'] = np.where(E.dist_runs_before >= 3, 'familiar distance (3+ runs)', 'unfamiliar distance')
E['magn'] = pd.cut(E.perf - E.dyn_nat, [2, 4, 6, 10, 99], right=False, labels=['2-4', '4-6', '6-10', '10+']).astype(str)
OUT = {'note': 'kept = (later performance - pre-race rating) / surprise, median of individual shares; update share = (revised rating - pre-race rating) / surprise; next vs revised = next performance minus the revised rating (kg).'}
for col in ['exp', 'kind', 'var_band', 'vs_best', 'vs_upper', 'stage', 'tr_change', 'familiar', 'magn']:
    OUT[col] = {str(k): S(x) for k, x in E.groupby(col)}
OUT['progressive_by_experience'] = {k: S(x) for k, x in E[E.kind.str.startswith('progressive')].groupby('exp')}
OUT['unprecedented_by_experience'] = {k: S(x) for k, x in E[E.kind.str.startswith('unprecedented')].groupby('exp')}
E['sup'] = np.where((E.slope5 > 0.5) | (E.perf <= E.rep6 + 1), 'supported (improving or near its upper level)', 'unsupported (one-off above its range)')
OUT['supported_vs_unsupported_same_size'] = {f'{m} | {s}': S(x) for (m, s), x in E[E.k >= 12].groupby(['magn', 'sup'])}
json.dump(OUT, open('batch20/out_b20_supported.json', 'w'), indent=1, default=str)
for k in ['exp', 'progressive_by_experience', 'unprecedented_by_experience', 'var_band', 'vs_upper', 'stage', 'tr_change', 'familiar', 'supported_vs_unsupported_same_size']:
    print('==', k); [print(' ', kk, v) for kk, v in OUT[k].items()]
