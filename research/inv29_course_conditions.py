"""Batch 5 (plan batch05_plan.md), Studies 13-15, Queensland tracked races. Baseline offset = frozen
"combined_v1 + national dynamic rating" (development coefficients). For each local term, candidates:
A pooled (offset only; the pooled term is already in the offset), C independent course deviations,
D partial pooling (prior spread chosen on the inner split Oct 2022-Dec 2023 -> 2024).
Primary: D vs A (P1 13a, P2 14a, P3 14b, P4 15a). Secondary: 13b, C vs A, Eagle Farm + Doomben, stability.
Outputs out/out_s13_15_*.csv"""
import json, numpy as np, pandas as pd
import hier_tools as H, dyn_rating as DR
from clogit_tools import eligible, prep
rng = np.random.default_rng(20261125)
mn = json.load(open('benchmarks/candidates_b4_national/manifest.json')); COEF = mn['coefficients_per_dev_sd']; pn = mn['dynamic_rating_params']
U = pd.read_parquet('national_runs.parquet')
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                   'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, _, _ = DR.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
U['dyn_nat'] = pd.Series(mu, index=PN.idx.values).reindex(np.arange(len(U))).values
qn = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_nat']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id'])
qn.to_parquet('dyn_nat_qld.parquet')
X = pd.read_parquet('features.parquet').merge(qn, on=['race_id', 'horse_id'], how='left')
r = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'cond_group']]
X = X.merge(r, on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
x = prep(eligible(X), sorted(set(COEF) | {'t_going', 'p_style', 'p_lead_x_press', 's_gap600_avg3'}))
x['offset'] = x[[c + '_z' for c in COEF]].values @ np.array(list(COEF.values()))
x['course'] = x.track; x['gb'] = x.cond_group.map({'Good': 'good', 'Firm': 'good', 'Soft': 'soft', 'Heavy': 'heavy', 'Synthetic': 'good'}).fillna('good')
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']; d1, d2 = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
cnt = dev.groupby('course').race_id.nunique(); COURSES = sorted(cnt[cnt >= 30].index)
def cols(df, term, by_going=False):
    out = {}
    for c in COURSES:
        if by_going:
            for g in ['good', 'soft', 'heavy']: out[f'{c}|{g}'] = df[term + '_z'].values * ((df.course == c) & (df.gb == g)).values
        else: out[c] = df[term + '_z'].values * (df.course == c).values
    return pd.DataFrame(out, index=df.index)
R_ = lambda df, C: H.Races(df.race_id.values, df.win.values, df.offset.values, C.values)
def per_race(df, C, b):
    R = R_(df, C); rid = df.race_id.values[R.o][R.starts]
    return pd.DataFrame({'race_id': rid, 'lp': R.loglik_per_race(b), 'hit': R.top_hit(b)}).set_index('race_id')
info = ev.groupby('race_id').agg(meeting_id=('meeting_id', 'first'), course=('course', 'first'))
def boot(a, b, key):
    dd = (b.lp - a.lp).to_frame('d').join(info); k_ = dd.meeting_id if key == 'meeting' else dd.meeting_id.str[:7]
    m = dd.d.groupby(k_).agg(['sum', 'count']); s, n = m['sum'].values, m['count'].values
    bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(s), len(s)) for _ in range(1000))]
    return dd.d.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5), float(np.mean(np.array(bs) <= 0))
rows, tabs = [], []
for test, term, byg in [('P1 13a course x going suitability', 't_going', False), ('P2 14a course x running position', 'p_style', False),
                        ('P3 14b course x pace pressure', 'p_lead_x_press', False), ('P4 15a course x late speed', 's_gap600_avg3', False),
                        ('sec 13b course x going band x running position', 'p_style', True)]:
    C1, C2 = cols(d1, term, byg), cols(d2, term, byg)
    grid = [(R_(d2, C2).loglik_per_race(H.fit(R_(d1, C1), np.full(C1.shape[1], 1 / t ** 2))).sum(), t) for t in [0.01, 0.03, 0.1, 0.3, 1.0]]
    base_inner = R_(d2, C2).loglik_per_race(np.zeros(C2.shape[1])).sum()
    tau = max(grid)[1]
    Cd, Ce = cols(dev, term, byg), cols(ev, term, byg)
    bD = H.fit(R_(dev, Cd), np.full(Cd.shape[1], 1 / tau ** 2)); bC = H.fit(R_(dev, Cd), np.full(Cd.shape[1], 1e-6))
    sA, sD, sC = per_race(ev, Ce, np.zeros(Ce.shape[1])), per_race(ev, Ce, bD), per_race(ev, Ce, bC)
    sdD = H.posterior_sd(R_(dev, Cd), bD, np.full(Cd.shape[1], 1 / tau ** 2))
    b1 = H.fit(R_(d1, C1), np.full(C1.shape[1], 1e-6)); b2 = H.fit(R_(d2, C2), np.full(C2.shape[1], 1e-6))
    for lab, sb in [('partial pooling vs pooled', sD), ('independent vs pooled', sC)]:
        m, lo, hi, p = boot(sA, sb, 'meeting'); _, mlo, mhi, mp = boot(sA, sb, 'month')
        rows.append({'test': test if lab.startswith('partial') else 'sec ' + test.split(' ', 1)[1], 'comparison': lab, 'races': len(sA), 'chosen_tau': tau,
                     'inner_gain_best_vs_pooled': round(max(grid)[0] - base_inner, 2), 'fit_gain_per_race': round(m, 5), 'lo95_meetings': round(lo, 5), 'hi95_meetings': round(hi, 5),
                     'lo95_months': round(mlo, 5), 'hi95_months': round(mhi, 5), 'p_meetings': round(p, 4), 'p_months': round(mp, 4), 'top_pick_diff_pts': round(100 * (sb.hit.mean() - sA.hit.mean()), 2)})
    ef = info.course.isin(['Eagle_Farm', 'Doomben'])
    m, lo, hi, _ = boot(sA[ef.values], sD[ef.values], 'meeting')
    rows.append({'test': 'sec ' + test.split(' ', 1)[1] + ' (Eagle Farm + Doomben)', 'comparison': 'partial pooling vs pooled', 'races': int(ef.sum()), 'chosen_tau': tau,
                 'fit_gain_per_race': round(m, 5), 'lo95_meetings': round(lo, 5), 'hi95_meetings': round(hi, 5)})
    pooled = COEF.get(term, 0.0)
    for j, name in enumerate(Cd.columns):
        tabs.append({'study': test, 'course': name, 'dev_races': int(dev[dev.course == name.split('|')[0]].race_id.nunique()), 'pooled_coef': round(pooled, 3),
                     'dev_partial': round(bD[j], 3), 'sd': round(sdD[j], 3), 'dev_independent': round(bC[j], 3),
                     'kept_%': round(100 * bD[j] / bC[j]) if abs(bC[j]) > 1e-4 else None, 'clear_of_pool_95': bool(abs(bD[j]) > 1.96 * sdD[j]),
                     'indep_2022_23': round(b1[j], 3), 'indep_2024': round(b2[j], 3)})
    st = np.corrcoef(b1, b2)[0, 1]
    rows.append({'test': 'sec ' + test.split(' ', 1)[1] + ' stability', 'comparison': 'independent deviations, Oct22-Dec23 vs 2024', 'fit_gain_per_race': round(st, 3)})
T = pd.DataFrame(rows); T.to_csv('out/out_s13_15_tests.csv', index=False); print(T.to_string(index=False))
C = pd.DataFrame(tabs); C.to_csv('out/out_s13_15_by_course.csv', index=False)
print(C[C.clear_of_pool_95].to_string(index=False) if C.clear_of_pool_95.any() else 'no course departs clearly from the pool in any study')
