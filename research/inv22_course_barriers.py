"""Batch 4, Study 10 (plan: batch04_plan.md). Course-specific barrier x expected running style, Queensland.
Pooled (A = frozen combined_v1) vs independent course models (C) vs hierarchical partial pooling (D), plus course x
distance (E) and rail (Rail) extensions. Fitted on races before 2025, scored 2025-26 (chronological out-of-sample).
Outputs out/out_s10_*.csv and benchmarks/course_v1/."""
import json, os, numpy as np, pandas as pd
from clogit_tools import eligible, prep, fit as cfit
import hier_tools as H
rng = np.random.default_rng(20261124)
X = pd.read_parquet('features.parquet')
has = X.f_avgfp3.notna()
X['missform'] = (~has).astype(float); X['missfig'] = (has & X.a_avg3.isna()).astype(float); X['misssec'] = (has & X.s_gap600_avg3.isna()).astype(float)
X['missstyle'] = (has & X.p_style.isna()).astype(float); X['missgoing'] = (has & X.t_going.isna()).astype(float)
G = {'F': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'A': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'],
     'S': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'P': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
     'T': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'R': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
BENCH = [c for v in G.values() for c in v]
x = prep(eligible(X), sorted(set(BENCH)))
bb = cfit(x, BENCH); x['offset'] = x[[c + '_z' for c in BENCH]].values @ bb
pooled_relbar = bb[BENCH.index('p_relbar')]; pooled_bs = bb[BENCH.index('p_bar_x_style')]
rail = pd.read_parquet('runs_rated_dev.parquet')[['race_id', 'rail']].drop_duplicates('race_id')
def rail_m(s):
    import re
    s = s if isinstance(s, str) else ''
    if s.lower().startswith('true'): return 0.0
    m = re.match(r'\+?\s*(\d+(?:\.\d+)?)m', s); return float(m.group(1)) if m else np.nan
rail['rail_m'] = rail.rail.map(rail_m); x = x.merge(rail[['race_id', 'rail_m']], on='race_id', how='left')
x['railz'] = (x.rail_m.fillna(x.rail_m.median()) / 5.0)
x['db'] = pd.cut(x.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
x['course'] = x.track
x['rb'] = x.p_relbar_z; x['bs'] = x.p_bar_x_style_z
dev_races = x[x.period == 'development'].groupby('course').race_id.nunique()
courses_D = sorted(dev_races[dev_races >= 30].index)
_cd = x[x.period == 'development'].groupby(['course', 'db']).race_id.nunique()
CDB = [k for k, v in _cd.items() if v >= 60 and k[0] in set(dev_races[dev_races >= 30].index)]; courses_C = sorted(dev_races[dev_races >= 150].index)
print('courses (dev races):', dev_races.sort_values(ascending=False).to_dict())
def cols(df, spec):
    out = {}
    for kind, arg in spec:
        if kind == 'course':
            for c in arg: m = (df.course == c).values; out[f'rb|{c}'] = df.rb.values * m; out[f'bs|{c}'] = df.bs.values * m
        if kind == 'course_db':
            for c, d in CDB:
                m = ((df.course == c) & (df.db == d)).values; out[f'rb|{c}|{d}'] = df.rb.values * m
        if kind == 'rail_pooled': out['rb*rail'] = df.rb.values * df.railz.values
        if kind == 'rail_course':
            for c in arg: m = (df.course == c).values; out[f'rb*rail|{c}'] = df.rb.values * df.railz.values * m
    return pd.DataFrame(out, index=df.index)
def races(df, C): return H.Races(df.race_id.values, df.win.values, df.offset.values, C.values if C.shape[1] else np.zeros((len(df), 0)))
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']
d1, d2 = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
def lam_for(names, taus):
    return np.array([1.0 / taus[[k for k in taus if n.startswith(k)][0]] ** 2 for n in names])
def tune(spec, grid):
    """choose prior spreads on the inner split (fit Oct 2022-Dec 2023, score 2024), then refit on all development races"""
    best = None
    for taus in grid:
        C1 = cols(d1, spec); C2 = cols(d2, spec)
        b = H.fit(races(d1, C1), lam_for(C1.columns, taus)); ll = races(d2, C2).loglik_per_race(b).sum()
        if best is None or ll > best[0]: best = (ll, taus)
    return best[1]
models = {}
models['A pooled (combined_v1)'] = ([], None)
models['C independent courses'] = ([('course', courses_C)], {'rb|': 1e3, 'bs|': 1e3})          # tau huge = no pooling
grid_D = [{'rb|': a, 'bs|': b} for a in [0.02, 0.05, 0.1, 0.2, 0.4] for b in [0.02, 0.05, 0.1, 0.2]]
tD = tune([('course', courses_D)], grid_D); models['D hierarchical (partial pooling)'] = ([('course', courses_D)], tD)
best = None
for te in [0.02, 0.05, 0.1, 0.2]:
    spec = [('course', courses_D), ('course_db', courses_D)]
    C1, C2 = cols(d1, spec), cols(d2, spec)
    lam = np.array([1 / te ** 2 if n.count('|') == 2 else 1 / tD['rb|' if n.startswith('rb|') else 'bs|'] ** 2 for n in C1.columns])
    ll = races(d2, C2).loglik_per_race(H.fit(races(d1, C1), lam)).sum()
    if best is None or ll > best[0]: best = (ll, te)
tE = best[1]
best = None
for tr in [0.02, 0.05, 0.1, 0.2]:
    spec = [('course', courses_D), ('rail_pooled', None), ('rail_course', courses_D)]
    C1, C2 = cols(d1, spec), cols(d2, spec)
    lam = np.array([1e-6 if n == 'rb*rail' else (1 / tr ** 2 if n.startswith('rb*rail|') else 1 / tD['rb|' if n.startswith('rb|') else 'bs|'] ** 2) for n in C1.columns])
    ll = races(d2, C2).loglik_per_race(H.fit(races(d1, C1), lam)).sum()
    if best is None or ll > best[0]: best = (ll, tr)
tR = best[1]
print('chosen prior spreads: D', tD, '| E course x distance', tE, '| rail', tR)
def lam_of(name, C):
    if name.startswith('A'): return np.zeros(0)
    if name.startswith('C'): return np.full(C.shape[1], 1e-6)
    out = []
    for n in C.columns:
        if n == 'rb*rail': out.append(1e-6)
        elif n.startswith('rb*rail|'): out.append(1 / tR ** 2)
        elif n.count('|') == 2: out.append(1 / tE ** 2)
        else: out.append(1 / tD['rb|' if n.startswith('rb|') else 'bs|'] ** 2)
    return np.array(out)
specs = {'A pooled (combined_v1)': [], 'C independent courses': [('course', courses_C)], 'D hierarchical (partial pooling)': [('course', courses_D)],
         'E hierarchical + course x distance': [('course', courses_D), ('course_db', courses_D)],
         'Rail hierarchical + rail x barrier': [('course', courses_D), ('rail_pooled', None), ('rail_course', courses_D)]}
fitted, scored = {}, {}
for name, spec in specs.items():
    Cd, Ce = cols(dev, spec), cols(ev, spec); lam = lam_of(name, Cd)
    b = H.fit(races(dev, Cd), lam) if Cd.shape[1] else np.zeros(0)
    Re = races(ev, Ce); fitted[name] = (b, list(Cd.columns), lam)
    rid = ev.race_id.values[Re.o][Re.starts]
    scored[name] = pd.DataFrame({'race_id': rid, 'lp': Re.loglik_per_race(b), 'hit': Re.top_hit(b)}).set_index('race_id')
info = ev.groupby('race_id').agg(course=('course', 'first'), meeting_id=('meeting_id', 'first'), tier=('venue_tier', 'first'), db=('db', 'first'), field=('field', 'first'))
for k in scored: scored[k] = scored[k].join(info)
def boot(a, b, by='meeting', reps=1000):
    d = (b.lp - a.lp); key = a.meeting_id if by == 'meeting' else a.meeting_id.str[:7]
    m = d.groupby(key).agg(['sum', 'count']); s, n = m['sum'].values, m['count'].values
    bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(s), len(s)) for _ in range(reps))]
    return d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), float(np.mean(np.array(bs) <= 0))
rows = []
for tid, a, b, sub in [('P1', 'A pooled (combined_v1)', 'D hierarchical (partial pooling)', None), ('P2', 'C independent courses', 'D hierarchical (partial pooling)', None),
                       ('P3', 'A pooled (combined_v1)', 'D hierarchical (partial pooling)', 'metro'), ('P4', 'D hierarchical (partial pooling)', 'E hierarchical + course x distance', None),
                       ('P5', 'D hierarchical (partial pooling)', 'Rail hierarchical + rail x barrier', None), ('sec', 'A pooled (combined_v1)', 'C independent courses', None),
                       ('sec', 'A pooled (combined_v1)', 'E hierarchical + course x distance', None), ('sec', 'A pooled (combined_v1)', 'Rail hierarchical + rail x barrier', None)]:
    sa, sb = scored[a], scored[b]
    if sub: sa, sb = sa[sa.tier == sub], sb[sb.tier == sub]
    m, lo, hi, p = boot(sa, sb); _, mlo, mhi, mp = boot(sa, sb, 'month')
    rows.append({'test': tid, 'comparison': f'{b} vs {a}', 'races': len(sa), 'fit_gain_per_race': round(m, 5), 'lo95_meetings': round(lo, 5), 'hi95_meetings': round(hi, 5),
                 'lo95_months': round(mlo, 5), 'hi95_months': round(mhi, 5), 'p_meetings': round(p, 4), 'p_months': round(mp, 4), 'top_pick_diff_pts': round(100 * (sb.hit.mean() - sa.hit.mean()), 2)})
t = pd.DataFrame(rows); t.to_csv('out/out_s10_primary.csv', index=False); print(t.to_string(index=False))
# by course: D vs A, and the estimated barrier effect per course (pooled + deviation), with posterior sd and shrinkage
bD, cD, lD = fitted['D hierarchical (partial pooling)']; sdD = H.posterior_sd(races(dev, cols(dev, specs['D hierarchical (partial pooling)'])), bD, lD)
bC, cC, _ = fitted['C independent courses']
sd_rb = x[x.period == 'development'].groupby('race_id').p_relbar.transform(lambda s: s - s.mean()).std()   # raw relbar sd (race-centred)
crow = []
for c in courses_D:
    j = cD.index(f'rb|{c}'); k = cD.index(f'bs|{c}')
    sa, sb = scored['A pooled (combined_v1)'], scored['D hierarchical (partial pooling)']; ia = sa.course == c
    m, lo, hi, _ = boot(sa[ia], sb[ia]) if ia.sum() > 20 else (np.nan,) * 4
    c_rb = bC[cC.index(f'rb|{c}')] if f'rb|{c}' in cC else np.nan
    crow.append({'course': c, 'dev_races': int(dev_races[c]), 'eval_races': int(ia.sum()),
                 'barrier_dev_D': round(bD[j], 3), 'barrier_dev_sd': round(sdD[j], 3), 'barrier_dev_independent_C': round(c_rb, 3) if c_rb == c_rb else None,
                 'shrinkage_kept_%': round(100 * bD[j] / c_rb, 0) if c_rb == c_rb and abs(c_rb) > 1e-6 else None,
                 'style_x_barrier_dev_D': round(bD[k], 3), 'style_dev_sd': round(sdD[k], 3),
                 'inside_vs_outside_win_odds_midfield': round(float(np.exp((pooled_relbar + bD[j]) / sd_rb * 1.0)), 2),
                 'departs_from_pool_95': bool(abs(bD[j]) > 1.96 * sdD[j] or abs(bD[k]) > 1.96 * sdD[k]),
                 'D_vs_A_gain_per_race': round(m, 4) if m == m else None, 'lo95': round(lo, 4) if lo == lo else None, 'hi95': round(hi, 4) if hi == hi else None})
ct = pd.DataFrame(crow).sort_values('dev_races', ascending=False); ct.to_csv('out/out_s10_by_course.csv', index=False); print(ct.to_string(index=False))
print('pooled barrier coef (per sd):', round(pooled_relbar, 3), 'pooled barrier x style:', round(pooled_bs, 3), 'relbar sd:', round(sd_rb, 3))
# stability: D fitted separately on Oct 2022-Dec 2023 and on 2024 (development halves)
spec = specs['D hierarchical (partial pooling)']; C1, C2 = cols(d1, spec), cols(d2, spec)
b1 = H.fit(races(d1, C1), lam_of('D', C1)); b2 = H.fit(races(d2, C2), lam_of('D', C2))
st = pd.DataFrame({'term': list(C1.columns), 'oct22_dec23': b1, 'y2024': b2})
st.to_csv('out/out_s10_stability.csv', index=False)
print('stability corr (course deviations, two development halves): barrier', round(st[st.term.str.startswith('rb|')][['oct22_dec23', 'y2024']].corr().iloc[0, 1], 3),
      '| barrier x style', round(st[st.term.str.startswith('bs|')][['oct22_dec23', 'y2024']].corr().iloc[0, 1], 3))
# freeze candidates for prospective scoring
os.makedirs('benchmarks/course_v1', exist_ok=True)
json.dump({'frozen_utc': pd.Timestamp.utcnow().isoformat(), 'plan': 'batch04_plan.md', 'baseline': 'combined_v1 offset (development fit)', 'benchmark_coefs': dict(zip(BENCH, map(float, bb))),
           'models': {k: {'columns': v[1], 'beta': list(map(float, v[0])), 'lambda': list(map(float, v[2])) if len(v[2]) else []} for k, v in fitted.items()},
           'prior_spreads': {'D': tD, 'E': tE, 'rail': tR}, 'courses_D': courses_D, 'courses_C': courses_C}, open('benchmarks/course_v1/manifest.json', 'w'), indent=1)
print('frozen to benchmarks/course_v1')
