"""Batch 19 D13/D14: barrier effects learned at several levels with pooling (research only; no prices; no production use).
Barrier history exists only where the database holds it: Queensland tracking (starter table, 2022-26) and South Australian tracking
(sa_starter, 2024-26); national Breednet history has no barriers. Outcome = surprise (performance minus pre-race rating, relative to the
field, Engine v2.3 frame). Barrier position = rank among the race's actual starters, scaled 0 (inside) to 1 (outside), centred within race.
Levels: national (Qld + SA) -> state -> course -> course x distance band -> course x distance band x rail band. Each group's within-race
slope is pulled towards its parent by its own precision (empirical Bayes; between-group variance by method of moments on the fit period).
Going and field size are checked as national modifiers. Point in time: fit on meetings before 2025, judged on 2025-26 (SA fit = 2024 only).
Compared: no barrier effect, national, state, independent course x distance (no pooling), hierarchical at each depth, and recency-weighted.
Stability (D14): course x distance slopes 2023-24 vs 2025-26 beyond chance (meeting-shuffled halves).
Usage (from research/): python3 batch19/b19_barrier_hierarchy.py -> batch19/out_b19_barrier_hierarchy.json"""
import re, json, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date', 'state', 'q_race_id', 'q_horse_id', 'dyn_nat_inn', 'gband', 'field'])
rail = lambda s: 0.0 if re.match(r'(?i)\s*true', str(s)) else (float(re.search(r'\+\s*(\d+(?:\.\d+)?)', str(s)).group(1)) if re.search(r'\+\s*(\d+(?:\.\d+)?)', str(s)) else np.nan)
# Queensland
Rq = con.execute("select race_id, track, distance_m, rail, meeting_date from race").fetchdf()
Sq = con.execute("select race_id, horse_code, barrier from starter where not coalesce(scratched, false) and barrier is not null").fetchdf()
Sq['horse_code'] = Sq.horse_code.astype(str); Fq = F.dropna(subset=['q_race_id']).copy(); Fq['q_horse_id'] = Fq.q_horse_id.astype(str)
Q = Fq.merge(Sq, left_on=['q_race_id', 'q_horse_id'], right_on=['race_id', 'horse_code']).merge(Rq, left_on='q_race_id', right_on='race_id', suffixes=('', '_r'))
Q = Q.assign(course=Q.track, state='QLD', meeting=Q.track + '|' + Q.meeting_date.astype(str), rid=Q.q_race_id)
# South Australia
Ra = con.execute("select r.race_id, r.track, r.meeting_date, r.race_no, r.distance_m, r.rail from sa_race r").fetchdf()
Sa = con.execute("select race_id, name_key, barrier from sa_starter where not coalesce(scratched, false) and barrier is not null").fetchdf().merge(Ra, on='race_id')
Sa['race'] = 'SA|' + Sa.track.str.lower().str.replace('_', '-') + '|' + pd.to_datetime(Sa.meeting_date).dt.strftime('%Y-%m-%d') + '|' + Sa.race_no.astype(str)
A = F[F.state == 'SA'].merge(Sa, left_on=['race', 'horse'], right_on=['race', 'name_key'])
A = A.assign(course=A.track, meeting=A.track + '|' + A.meeting_date.astype(str), rid=A.race_id)
cols = ['rid', 'meeting', 'meeting_date', 'state', 'course', 'distance_m', 'rail', 'gband', 'barrier', 'dyn_nat_inn']
X = pd.concat([Q[cols], A[cols]], ignore_index=True).dropna(subset=['dyn_nat_inn', 'barrier'])
X['n'] = X.groupby('rid').barrier.transform('count'); X = X[X.n >= 6].copy()
X['bpos'] = (X.groupby('rid').barrier.rank(method='average') - 1) / (X.n - 1)
X['x'] = X.bpos - X.groupby('rid').bpos.transform('mean'); X['y'] = X.dyn_nat_inn - X.groupby('rid').dyn_nat_inn.transform('mean')
X['dband'] = pd.cut(X.distance_m, [0, 1100, 1300, 1500, 1800, 9999], labels=['to1100', '1101-1300', '1301-1500', '1501-1800', '1801+']).astype(str)
X['rail_m'] = X.rail.map(rail); X['rband'] = pd.cut(X.rail_m, [-0.1, 0.5, 3.5, 6.5, 99], labels=['true', '+1-3', '+4-6', '+7+']).astype(str)
X['fband'] = pd.cut(X.n, [5, 9, 12, 99], labels=['6-9', '10-12', '13+']).astype(str)
X['md'] = pd.to_datetime(X.meeting_date); X['fit'] = X.md < '2025-01-01'
X['L0'] = 'all'; X['L1'] = X.state; X['L2'] = X.L1 + '|' + X.course; X['L3'] = X.L2 + '|' + X.dband; X['L4'] = X.L3 + '|' + X.rband
fitd = X[X.fit]; sig2 = float((fitd.y ** 2).mean())
def slopes(d, key, w=None):
    w = np.ones(len(d)) if w is None else w
    g = pd.DataFrame({'k': d[key].values, 'xy': w * d.x.values * d.y.values, 'xx': w * d.x.values ** 2}).groupby('k').sum()
    g['b'] = g.xy / g.xx; g['v'] = sig2 / g.xx; return g
def hier(d, levels, w=None):
    post = {}; prev = None
    for L in levels:
        g = slopes(d, L, w)
        if prev is None: g['post'] = g.b; tau2 = np.nan
        else:
            par = d.groupby(L)[prev].first(); g['par'] = par.reindex(g.index).map(post[prev]).values
            tau2 = max(0.0, float(np.average((g.b - g.par) ** 2, weights=1 / g.v) - np.average(g.v, weights=1 / g.v)))
            g['post'] = (tau2 * g.b + g.v * g.par) / (tau2 + g.v)
        post[L] = g.post.to_dict(); post[L + '_tau2'] = tau2; prev = L
    return post
LV = ['L0', 'L1', 'L2', 'L3', 'L4']
P = hier(fitd, LV)
age_days = (fitd.md.max() - fitd.md).dt.days.values; Pr = hier(fitd, LV, w=0.5 ** (age_days / 365.0))   # recency: one-year half-life
indep = slopes(fitd, 'L3').b.to_dict()
test = X[~X.fit].copy()
def pred_from(post, L):
    keys = test[L]; out = keys.map(post[L])
    for up in LV[:LV.index(L)][::-1]: out = out.fillna(test[up].map(post[up]))      # unseen group -> its parent's estimate
    return out.fillna(post['L0']['all']).values
preds = {'no barrier effect': np.zeros(len(test)), 'national': np.full(len(test), P['L0']['all'])}
for L, lab in [('L1', 'state'), ('L2', 'course (pooled)'), ('L3', 'course x distance (pooled)'), ('L4', 'course x distance x rail (pooled)')]: preds[lab] = pred_from(P, L)
preds['course x distance, recency-weighted (pooled)'] = pred_from(Pr, 'L3')
ind = test.L3.map(indep); preds['course x distance, independent (no pooling)'] = ind.fillna(test.L2.map(P['L2'])).fillna(P['L0']['all']).values
rng = np.random.default_rng(19); mt = pd.factorize(test.meeting)[0]; base = test.y.values ** 2
OUT = {'coverage': {'runs': int(len(X)), 'races': int(X.rid.nunique()), 'fit_runs': int(X.fit.sum()), 'test_runs': int((~X.fit).sum()), 'by_state_runs': X.groupby('state').size().to_dict(),
                    'courses': int(X.L2.nunique()), 'course_x_distance_groups': int(X.L3.nunique()), 'rail_known_share': round(float((X.rband != 'nan').mean()), 3)},
       'national_slope_kg_inside_to_outside': round(P['L0']['all'], 3), 'between_group_sd_kg': {L: (round(float(np.sqrt(P[L + '_tau2'])), 3) if P[L + '_tau2'] == P[L + '_tau2'] else None) for L in LV[1:]},
       'national_modifiers': {**{f'going {k}': round(float(v), 3) for k, v in slopes(fitd, 'gband').b.items()}, **{f'field {k}': round(float(v), 3) for k, v in slopes(fitd, 'fband').b.items()}}}
res = {}
for lab, p in preds.items():
    pw = p * test.x.values; sse = (test.y.values - pw) ** 2; d = base - sse
    s_m = pd.Series(d).groupby(mt).sum().values; n_m = pd.Series(np.ones(len(d))).groupby(mt).sum().values
    bs = [s_m[k].sum() / n_m[k].sum() for k in (rng.integers(0, len(s_m), len(s_m)) for _ in range(500))]
    cal = float(np.dot(pw, test.y.values) / np.dot(pw, pw)) if np.dot(pw, pw) > 0 else None
    res[lab] = {'error_reduction_kg2_per_run': round(float(d.mean()), 4), 'ci95': [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                'share_of_within_race_variance_explained_pct': round(100 * float(d.sum() / base.sum()), 3), 'calibration_slope': (round(cal, 2) if cal is not None else None)}
OUT['judged_2025_26'] = res
nat_sse = (test.y.values - preds['national'] * test.x.values) ** 2; pair = {}
for lab, p in preds.items():
    if lab in ('national', 'no barrier effect'): continue
    d = nat_sse - (test.y.values - p * test.x.values) ** 2; s_m = pd.Series(d).groupby(mt).sum().values; n_m = pd.Series(np.ones(len(d))).groupby(mt).sum().values
    bs = [s_m[k].sum() / n_m[k].sum() for k in (rng.integers(0, len(s_m), len(s_m)) for _ in range(500))]
    pair[lab] = [round(float(d.mean()), 4), round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]
OUT['vs_national_paired'] = pair
for st in ['QLD', 'SA']:
    m = (test.state == st).values; OUT[f'judged_2025_26_{st}'] = {lab: round(float((base[m] - (test.y.values[m] - p[m] * test.x.values[m]) ** 2).mean()), 4) for lab, p in preds.items()}
# stability: course x distance slopes in 2023-24 vs 2025-26 (Qld; enough meetings), against meeting-shuffled halves
q = X[(X.state == 'QLD') & (X.md >= '2023-01-01')].copy(); q['half'] = np.where(q.md < '2025-01-01', 'a', 'b')
def corr_halves(d, key):
    a = slopes(d[d.half == 'a'], key); b = slopes(d[d.half == 'b'], key); j = a.join(b, lsuffix='_a', rsuffix='_b', how='inner')
    j = j[(j.xx_a > 30) & (j.xx_b > 30)]; return (float(np.corrcoef(j.b_a, j.b_b)[0, 1]) if len(j) >= 8 else np.nan), int(len(j))
obs, ng = corr_halves(q, 'L3'); null = []
for _ in range(200):
    mm = q.meeting.unique(); hh = set(rng.choice(mm, len(mm) // 2, replace=False)); q['half'] = np.where(q.meeting.isin(hh), 'a', 'b'); null.append(corr_halves(q, 'L3')[0])
OUT['stability_qld_course_x_distance'] = {'groups': ng, 'corr_2023_24_vs_2025_26': round(obs, 3), 'random_halves_mean': round(float(np.nanmean(null)), 3), 'random_halves_p05_p95': [round(float(np.nanpercentile(null, 5)), 3), round(float(np.nanpercentile(null, 95)), 3)]}
big = slopes(fitd, 'L3'); big = big[big.xx > 60].join(pd.Series(P['L3'], name='pooled')).sort_values('xx', ascending=False).head(12)
OUT['largest_course_x_distance_groups_fit'] = [{'group': k, 'independent': round(float(r.b), 2), 'pooled': round(float(r.pooled), 2), 'se': round(float(np.sqrt(r.v)), 2)} for k, r in big.iterrows()]
json.dump(OUT, open('batch19/out_b19_barrier_hierarchy.json', 'w'), indent=1); print(json.dumps(OUT, indent=0)[:5000])
