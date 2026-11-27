"""Batch 21 D12: pre-specified follow-ups to the pooled course x distance x rail barrier expectation (research only; Qld + SA tracking
starters, same construction as batch20/b20_barrier_feature.py, exec'd unchanged up to the yearly fit). Chronological: every rule is fitted
on meetings before 1 Jan 2025 and judged on 2025-26 by the reduction in squared field-relative surprise (kg^2 per run, bootstrap 95% by
meeting). Baseline = the pooled linear slope (course x distance x rail, empirical Bayes). Four pre-stated questions only (no further
subdividing): (1) why 1301-1500 m went the wrong way (slope by course; start-to-first-turn not held, so described, not modelled);
(2) shape: is the effect straight-line in relative barrier, or bent (separate inside / middle / outside slopes, pooled nationally);
(3) absolute barrier number vs relative position among starters; (4) going and field size: does the pooled slope change with
going band (Good / Soft / Heavy) or field size (6-8 / 9-11 / 12+)? Usage (from research/): python3 batch21/b21_barrier_followups.py"""
import json, re, numpy as np, pandas as pd
src = open('batch20/b20_barrier_feature.py').read(); src = src[src.index('import re'):src.index("X['slope'] = np.nan")]
NORAIL, SUF = False, ''   # with rail (the Batch 20 construction)
exec(src, globals())
con2 = con
G = pd.concat([con2.execute("select race_id rid, track_rating_tracking g from race").fetchdf(), con2.execute("select race_id rid, track_rating_tracking g from sa_race").fetchdf()])
X = X.merge(G.drop_duplicates('rid'), on='rid', how='left')
X['going'] = X.g.fillna('').str.extract(r'(?i)(good|soft|heavy|firm|synthetic)')[0].str.lower().fillna('unknown')
X['fsz'] = pd.cut(X.n, [0, 8, 11, 40], labels=['6-8', '9-11', '12+']).astype(str)
X = X[(X.n >= 6) & X.y.notna()].copy(); fit = X[X.md < pd.Timestamp('2025-01-01')]; te = X[X.md >= pd.Timestamp('2025-01-01')].copy()
P = hier(fit); s = te.L4.map(P['L4'])
for up in ['L3', 'L2', 'L1', 'L0']: s = s.fillna(te[up].map(P[up]))
te['base'] = s.values * te.x
rng = np.random.default_rng(21)
def judge(pred, lab):
    e = (te.y - te.base) ** 2 - (te.y - pred) ** 2; m = te.meeting.values; um, inv = np.unique(m, return_inverse=True)
    sm = np.bincount(inv, e.values); nn = np.bincount(inv); bs = [sm[k].sum() / nn[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(500))]
    return {'runs': int(len(e)), 'gain_kg2_per_run': round(float(e.mean()), 4), 'ci95': [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)], 'label': lab}
OUT = {'fit_runs_before_2025': int(len(fit)), 'judged_runs_2025_26': int(len(te)), 'no_barrier_vs_base': judge(np.zeros(len(te)), 'no barrier term at all (how much the baseline itself is worth)')}
# (1) 1301-1500 m: slope by course (fit period and judged period separately: stable or not?)
def slopes(d, by):
    g = pd.DataFrame({'k': d[by].values, 'xy': d.x.values * d.y.values, 'xx': d.x.values ** 2}).groupby('k').agg(xy=('xy', 'sum'), xx=('xx', 'sum'), n=('xy', 'size'))
    return (g.xy / g.xx).round(2), g.n
b = X[X.dband == '1301-1500']
s_fit, n_fit = slopes(b[b.md < pd.Timestamp('2025-01-01')], 'L2'); s_te, n_te = slopes(b[b.md >= pd.Timestamp('2025-01-01')], 'L2')
c13 = pd.DataFrame({'slope_fit': s_fit, 'runs_fit': n_fit, 'slope_2025_26': s_te, 'runs_2025_26': n_te}).dropna().sort_values('runs_2025_26', ascending=False)
OUT['(1) 1301-1500 m slope by course (kg inside to outside; negative = outside worse)'] = c13.head(12).to_dict('index')
nb_fit, _ = slopes(X[X.md < pd.Timestamp('2025-01-01')], 'dband'); nb_te, _ = slopes(X[X.md >= pd.Timestamp('2025-01-01')], 'dband')
OUT['(1) pooled slope by distance band, fit vs 2025-26'] = {k: [float(nb_fit.get(k, np.nan)), float(nb_te.get(k, np.nan))] for k in sorted(set(nb_fit.index) | set(nb_te.index))}
# (2) shape: three-piece national shape on top of the pooled slope (inside third / middle / outside third)
def piece(d): return np.c_[np.minimum(d.bpos, 1 / 3), np.clip(d.bpos - 1 / 3, 0, 1 / 3), np.clip(d.bpos - 2 / 3, 0, 1 / 3)]
def centred(A, d): A = pd.DataFrame(A, index=d.index); return (A - A.groupby(d.rid.values).transform('mean')).values
Af = centred(piece(fit), fit); s_f = fit.L4.map(P['L4'])
for up in ['L3', 'L2', 'L1', 'L0']: s_f = s_f.fillna(fit[up].map(P[up]))
rf = fit.y - s_f.values * fit.x; coef = np.linalg.lstsq(Af, rf.values, rcond=None)[0]
OUT['(2) bent shape: extra slope inside / middle / outside third (kg per third)'] = [round(float(c), 3) for c in coef]
OUT['(2) judged'] = judge(te.base + centred(piece(te), te) @ coef, 'pooled slope + three-piece national shape')
# (3) absolute barrier number (centred in the race), with the same pooling, vs relative position
def with_x(d, xcol):
    d = d.copy(); d['x'] = d[xcol] - d.groupby('rid')[xcol].transform('mean'); return d
X['bar_abs'] = X.barrier.astype(float); fitA = with_x(X[X.md < pd.Timestamp('2025-01-01')], 'bar_abs'); teA = with_x(X[X.md >= pd.Timestamp('2025-01-01')], 'bar_abs')
PA = hier(fitA); sA = teA.L4.map(PA['L4'])
for up in ['L3', 'L2', 'L1', 'L0']: sA = sA.fillna(teA[up].map(PA[up]))
OUT['(3) absolute barrier number instead of relative position'] = judge((sA.values * teA.x).values, 'pooled slope per barrier number (centred)')
OUT['(3) national slope per barrier number, kg'] = round(float(PA['L0']['all']), 3)
# (4) going and field size: multiply the pooled slope by a band factor fitted before 2025
for col in ['going', 'fsz']:
    fac = {}
    for k, g in fit.groupby(col):
        sb = s_f.loc[g.index].values * g.x.values; fac[k] = float((sb * g.y.values).sum() / (sb ** 2).sum()) if (sb ** 2).sum() > 0 else 1.0
    OUT[f'(4) {col}: factor on the pooled slope (1 = no change)'] = {k: round(v, 2) for k, v in fac.items()}
    OUT[f'(4) {col} judged'] = judge(te.base * te[col].map(fac).fillna(1.0).values, f'pooled slope x {col} factor')
json.dump(OUT, open('batch21/out_b21_barrier_followups.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=1, default=str)[:6000])
