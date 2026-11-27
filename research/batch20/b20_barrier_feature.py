"""Batch 20 D9: point-in-time pooled barrier expectation (research only; candidate input for testing, never production without approval).
For each run with a barrier (Queensland tracking 2022-26, SA tracking 2024-26), bar_h = the pooled course x distance x rail barrier slope
(empirical Bayes, as batch19/b19_barrier_hierarchy.py) estimated ONLY from meetings before 1 January of the run's year, times the horse's
relative barrier position among the race's starters (0 inside .. 1 outside, centred within the race). Runs with no earlier data get the
broader level's estimate, or 0. Barrier number is used only through its rank among starters (relative position), as before.
Outputs: /tmp/cand/bar_h_qld.parquet (q_race_id, q_horse_id, bar_h) and /tmp/cand/bar_h_sa.parquet (race_id [frame key], horse, bar_h)
NORAIL=1: the rail level is dropped (course x distance is the finest level) because the morning TAB capture carries no rail position;
outputs then end _norail.
Usage (from research/): [NORAIL=1] python3 batch20/b20_barrier_feature.py"""
import os; NORAIL = os.environ.get('NORAIL') == '1'; SUF = '_norail' if NORAIL else ''
import re, json, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
rail = lambda s: 0.0 if re.match(r'(?i)\s*true', str(s)) else (float(re.search(r'\+\s*(\d+(?:\.\d+)?)', str(s)).group(1)) if re.search(r'\+\s*(\d+(?:\.\d+)?)', str(s)) else np.nan)
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'state', 'q_race_id', 'q_horse_id', 'dyn_nat_inn'])
Rq = con.execute("select race_id, track, distance_m, rail, meeting_date from race").fetchdf()
Sq = con.execute("select race_id, cast(horse_code as varchar) horse_code, barrier from starter where not coalesce(scratched, false) and barrier is not null").fetchdf()
Fq = F.dropna(subset=['q_race_id']).copy(); Fq['q_horse_id'] = Fq.q_horse_id.astype(str).str.replace(r'\.0$', '', regex=True)
Q = Fq.merge(Sq, left_on=['q_race_id', 'q_horse_id'], right_on=['race_id', 'horse_code'], suffixes=('', '_s')).merge(Rq, left_on='q_race_id', right_on='race_id', suffixes=('', '_r'))
Q = Q.assign(rid=Q.q_race_id, course=Q.track, st='QLD', meeting=Q.track + '|' + Q.meeting_date.astype(str))
Ra = con.execute("select race_id, track, meeting_date, race_no, distance_m, rail from sa_race").fetchdf()
Sa = con.execute("select race_id, name_key, barrier from sa_starter where not coalesce(scratched, false) and barrier is not null").fetchdf().merge(Ra, on='race_id')
Sa['race'] = 'SA|' + Sa.track.str.lower().str.replace('_', '-') + '|' + pd.to_datetime(Sa.meeting_date).dt.strftime('%Y-%m-%d') + '|' + Sa.race_no.astype(str)
A = F[F.state == 'SA'].merge(Sa, left_on=['race', 'horse'], right_on=['race', 'name_key'], suffixes=('', '_sa'))
A = A.assign(rid=A.race_id_sa, course=A.track, st='SA', meeting=A.track + '|' + A.meeting_date.astype(str))
cols = ['rid', 'meeting', 'meeting_date', 'st', 'course', 'distance_m', 'rail', 'barrier', 'dyn_nat_inn']
X = pd.concat([Q[cols + ['q_race_id', 'q_horse_id']].assign(race_id=np.nan, horse=np.nan), A[cols + ['race_id', 'horse']].assign(q_race_id=np.nan, q_horse_id=np.nan)], ignore_index=True)
X = X.dropna(subset=['barrier']); X['n'] = X.groupby('rid').barrier.transform('count'); X = X[X.n >= 2].copy()
X['bpos'] = (X.groupby('rid').barrier.rank(method='average') - 1) / (X.n - 1); X['x'] = X.bpos - X.groupby('rid').bpos.transform('mean')
X['y'] = X.dyn_nat_inn - X.groupby('rid').dyn_nat_inn.transform('mean')
X['dband'] = pd.cut(X.distance_m, [0, 1100, 1300, 1500, 1800, 9999], labels=['to1100', '1101-1300', '1301-1500', '1501-1800', '1801+']).astype(str)
X['rband'] = pd.cut(X.rail.map(rail), [-0.1, 0.5, 3.5, 6.5, 99], labels=['true', '+1-3', '+4-6', '+7+']).astype(str)
X['md'] = pd.to_datetime(X.meeting_date); X['yr'] = X.md.dt.year
X['L0'] = 'all'; X['L1'] = X.st; X['L2'] = X.L1 + '|' + X.course; X['L3'] = X.L2 + '|' + X.dband; X['L4'] = X.L3 + ('' if NORAIL else '|' + X.rband); LV = ['L0', 'L1', 'L2', 'L3'] + ([] if NORAIL else ['L4'])
def hier(d):
    d = d[(d.n >= 6) & d.y.notna()]; sig2 = float((d.y ** 2).mean()); post = {}; prev = None
    for L in LV:
        g = pd.DataFrame({'k': d[L].values, 'xy': d.x.values * d.y.values, 'xx': d.x.values ** 2}).groupby('k').sum(); g['b'] = g.xy / g.xx; g['v'] = sig2 / g.xx
        if prev is None: g['post'] = g.b
        else:
            g['par'] = d.groupby(L)[prev].first().reindex(g.index).map(post[prev]).values
            tau2 = max(0.0, float(np.average((g.b - g.par) ** 2, weights=1 / g.v) - np.average(g.v, weights=1 / g.v))); g['post'] = (tau2 * g.b + g.v * g.par) / (tau2 + g.v)
        post[L] = g.post.to_dict(); prev = L
    return post
X['slope'] = np.nan; info = {}
for Y in sorted(X.yr.unique()):
    past = X[X.md < pd.Timestamp(f'{Y}-01-01')]; cur = X.yr == Y
    if len(past) < 2000: info[int(Y)] = 'no earlier data: 0'; continue
    P = hier(past); s = X.loc[cur, LV[-1]].map(P[LV[-1]])
    for up in LV[-2::-1]: s = s.fillna(X.loc[cur, up].map(P[up]))
    X.loc[cur, 'slope'] = s; info[int(Y)] = {'national_slope': round(P['L0']['all'], 3), 'fit_runs': int(len(past))}
X['bar_h'] = (X.slope * X.x).fillna(0.0)
X[X.st == 'QLD'][['q_race_id', 'q_horse_id', 'bar_h']].to_parquet(f'/tmp/cand/bar_h_qld{SUF}.parquet'); X[X.st == 'SA'][['race_id', 'horse', 'bar_h']].to_parquet(f'/tmp/cand/bar_h_sa{SUF}.parquet')
json.dump({'by_year': info, 'runs': {s: int((X.st == s).sum()) for s in ['QLD', 'SA']}, 'nonzero_share': {s: round(float((X[X.st == s].bar_h != 0).mean()), 3) for s in ['QLD', 'SA']}}, open(f'batch20/out_b20_barrier_feature{SUF}.json', 'w'), indent=1)
print(json.load(open(f'batch20/out_b20_barrier_feature{SUF}.json')))
