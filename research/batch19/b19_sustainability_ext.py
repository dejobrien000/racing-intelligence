"""Batch 19 B5: sustainability of exceptional runs, extended (research only; no prices). Same definitions as batch18/b18_sustainability.py
(exec'd unchanged), plus:
(1) firmly established horses: starts held 6-11, 12-15, 16-19, 20+ for the 6+ kinds;
(2) career-history completeness: horses whose first run in our data was a genuine debut (aged 2-3, from March 2023) vs horses whose
    careers began before our data does (first run held Oct 2022 - Feb 2023, or aged 4+ at their first run held);
(3) selection by returning: next-run kept share for horses that went on to 5 more starts vs those that did not;
(4) uncertainty: horse-cluster bootstrap 95% range for the median kept share (200 resamples).
Usage (from research/): python3 batch19/b19_sustainability_ext.py -> batch19/out_b19_sustainability_ext.json"""
import json, numpy as np, pandas as pd
src = open('batch18/b18_sustainability.py').read(); src = src[:src.index('OUT = {')]; exec(src)
first = U.groupby('horse').date.transform('min'); age1 = U.groupby('horse').age_n.transform('first')
U['complete'] = (first >= '2023-03-01') & age1.isin([2, 3]); U['incomplete'] = (first < '2023-03-01') | (age1 >= 4)
E = E.join(U[['complete', 'incomplete']])
rng = np.random.default_rng(19)
def boot(x, c):
    y = x[x[c].notna()]
    if len(y) < 100: return None
    r = ((y[c] - y.dyn_nat) / (y.perf - y.dyn_nat)).values; h = pd.factorize(y.horse)[0]; groups = pd.Series(np.arange(len(y))).groupby(h).apply(list).tolist()
    meds = []
    for _ in range(200):
        pick = rng.integers(0, len(groups), len(groups)); idx = np.concatenate([groups[i] for i in pick]); meds.append(np.median(r[idx]))
    return [round(float(np.median(r)), 3), round(float(np.percentile(meds, 2.5)), 3), round(float(np.percentile(meds, 97.5)), 3)]
def T(x):
    o = S(x)
    o['kept_median_ci'] = {lab: boot(x, c) for c, lab in [('p1', 'next'), ('m3', 'next3'), ('m5', 'next5')]}
    return o
OUT = {'definitions': {
    'eligible run': 'surprise (performance minus pre-race rating, relative to the field) of at least 2 kg, at least one earlier run held, Jan 2023 - Jun 2026',
    'kinds (checked in this order)': 'emerging = 1-5 starts held; progressive = 6+ held and the slope of the last 5 performances above 0.5 kg per run; return to level = performance no more than 2 kg above the previous career best; unprecedented isolated = more than 3 kg above the previous career best and not progressive; other = 2-3 kg above the previous best',
    'gain kept (share)': 'for EACH run: (later performance, or mean of the next 3 / next 5, minus the pre-race rating) divided by (exceptional performance minus the pre-race rating); the table reports the median of these individual shares, not a ratio of averages',
    'repeated': 'at least one of the next 5 performances within 1 kg of the exceptional run (or better)',
    'higher range established': 'median of the next 5 at least 2 kg above the previous repeatable upper level (second best of the last 6)',
    'back to previous range': 'median of the next 5 no more than 1 kg above the previous typical level (median of the last 5)',
    'mutually exclusive': 'yes: the repeatable upper level is never below the typical level, so a median cannot be both >= upper + 2 and <= typical + 1; a run can be neither',
    'horizons': 'next 3 / next 5 use the next 3 / 5 starts whenever they came (no time limit; window ends mid-2026 so they are possible); horses without them are excluded from that horizon only and counted in had_3_more_365d / had_5_more_365d'},
    'by_kind': {k: T(x) for k, x in E.groupby('kind')}}
est = E[E.k >= 6].copy(); est['held'] = pd.cut(est.k, [5, 11, 15, 19, 999], labels=['6-11', '12-15', '16-19', '20+']).astype(str)
OUT['established_by_starts_held'] = {f'{k} | {h}': T(x) for (k, h), x in est.groupby(['kind', 'held']) if len(x) >= 100}
OUT['history_completeness'] = {f'{k} | {"complete history" if c else "career began before our data"}': T(x) for (k, c), x in E[E.complete | E.incomplete].groupby(['kind', 'complete']) if len(x) >= 100}
sel = {}
for k, x in E.groupby('kind'):
    y = x[x.p1.notna()].copy(); y['five'] = y.m5.notna(); r = (y.p1 - y.dyn_nat) / (y.perf - y.dyn_nat)
    sel[k] = {'went_on_to_5_more': [int(y.five.sum()), round(float(r[y.five].median()), 3)], 'did_not': [int((~y.five).sum()), round(float(r[~y.five].median()), 3) if (~y.five).sum() >= 30 else None],
              'gain_kg_mean (5 more / not)': [round(float((y.perf - y.dyn_nat)[y.five].mean()), 2), round(float((y.perf - y.dyn_nat)[~y.five].mean()), 2) if (~y.five).sum() else None]}
OUT['selection_by_returning'] = sel
json.dump(OUT, open('batch19/out_b19_sustainability_ext.json', 'w'), indent=1)
for k, v in OUT['established_by_starts_held'].items(): print(k, v['runs'], v['kept_median_ci'])
for k, v in OUT['history_completeness'].items(): print(k, v['runs'], v['kept_median_ci'])
print(json.dumps(sel, indent=0))
