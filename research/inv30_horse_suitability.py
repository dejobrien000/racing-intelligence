"""Batch 5 (plan batch05_plan.md), Studies 16-17: horse records relative to the national rating's expectation.
Each measured run's surprise = its innovation in the national dynamic rating (kg; positive = ran better than the
pre-race ratings expected). A horse's record for a key (course configuration, going band, distance band) = sum of its
EARLIER surprises with that key / (n + k): shrunk to 0 for few runs. k chosen on the inner split (fit Oct 2022-Dec
2023, score 2024) from 1, 3, 10, 30. Home track = configuration with most earlier runs (point-in-time).
P5/P7 Qld (offset = frozen combined_v1 + national rating); P6/P8 NSW/Vic/ACT (baseline F+A+R+national rating,
development fit). Outputs out/out_s16_17_*.csv"""
import re, json, duckdb, numpy as np, pandas as pd
import dyn_rating as DR, dyn_rating_innov as DI, hier_tools as H
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
rng = np.random.default_rng(20261125)
mn = json.load(open('benchmarks/candidates_b4_national/manifest.json')); COEF = mn['coefficients_per_dev_sd']; pn = mn['dynamic_rating_params']
U = pd.read_parquet('national_runs.parquet')
# course configuration: Qld from the tracking track name; NSW/Vic/ACT from the Breednet meeting slug (naming variants merged only)
NAMEVAR = {'royal-randwick': 'randwick', 'canterbury-park': 'canterbury', 'the-valley': 'moonee-valley', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill', 'beaumont-newcastle': 'beaumont', 'newcastle-beaumont': 'beaumont'}
con = duckdb.connect('../history/history.duckdb', read_only=True)
bm = con.execute("select meeting_date, bf_track_slug venue, slug from bn_meeting").fetchdf(); bm['date'] = pd.to_datetime(bm.meeting_date)
bm = bm.drop_duplicates(['date', 'venue']); bm['config'] = bm.slug.map(lambda s: NAMEVAR.get(s, s))
U = U.merge(bm[['date', 'venue', 'config']], on=['date', 'venue'], how='left')
qt = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'track', 'cond_group']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'})
U = U.merge(qt, on=['q_race_id', 'q_horse_id'], how='left')
U.loc[U.state == 'QLD', 'config'] = U.track; U['config'] = U.config.fillna(U.venue)
gw = U.going.fillna(U.cond_group).astype(str).str.lower()
U['gband'] = np.select([gw.str.contains('heavy'), gw.str.contains('soft'), gw.str.contains('synth|poly|awt')], ['heavy', 'soft', 'synthetic'], 'good')
U['dband'] = pd.cut(U.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                   'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu_f, _, _ = DR.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
mu, sd, inn = DI.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
assert np.nanmax(np.abs(mu - mu_f)) == 0, 'innovation module differs from the frozen rating'
ix = PN.idx.values
U['dyn_nat'] = pd.Series(mu, index=ix).reindex(np.arange(len(U))).values; U['innov'] = pd.Series(inn, index=ix).reindex(np.arange(len(U))).values
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
def record(key, k):
    v = U.innov.fillna(0.0); c = U.innov.notna().astype(int); grp = [U.horse, U[key]]
    s = v.groupby(grp).cumsum() - v; n = c.groupby(grp).cumsum() - c
    return s / (n + k), n
gh = U.groupby('horse')
# home track (point-in-time): configuration with most earlier runs
U['_one'] = 1; U['n_cfg_prev'] = U.groupby(['horse', 'config'])._one.cumsum() - 1
def home(df):
    best, cnt, out = None, {}, []
    for c in df.config.values:
        out.append(best); cnt[c] = cnt.get(c, 0) + 1
        if best is None or cnt[c] >= cnt.get(best, 0): best = c
    return pd.Series(out, index=df.index)
hv = []
for _, df in gh: hv.append(home(df))
U['home'] = pd.concat(hv).reindex(U.index)
U['at_home'] = ((U.home == U.config) & (U.n_cfg_prev >= 3)).astype(float)
RES = []
def add_records(k):
    for key, nm in [('config', 'c_rec'), ('gband', 'g_rec'), ('dband', 'd_rec')]: U[nm], U[nm + '_n'] = record(key, k)
# ---------- choose k on the inner split (Qld, baseline offset) ----------
X0 = pd.read_parquet('features.parquet')
has = X0.f_avgfp3.notna()
for kk, v in {'missform': ~has, 'missfig': has & X0.a_avg3.isna(), 'misssec': has & X0.s_gap600_avg3.isna(), 'missstyle': has & X0.p_style.isna(), 'missgoing': has & X0.t_going.isna()}.items(): X0[kk] = v.astype(float)
def qld_frame():
    q = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'at_home', 'c_rec_n']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id'])
    X = X0.merge(q, on=['race_id', 'horse_id'], how='left'); x = prep(eligible(X), sorted(set(COEF) | {'c_rec', 'g_rec', 'd_rec', 'at_home'}))
    x['offset'] = x[[c + '_z' for c in COEF]].values @ np.array(list(COEF.values())); return x
def gain_inner(x, terms):
    dv = x[x.period == 'development']; a, b = dv[dv.meeting_date < '2024-01-01'], dv[dv.meeting_date >= '2024-01-01']
    Ra = H.Races(a.race_id.values, a.win.values, a.offset.values, a[[t + '_z' for t in terms]].values); bb = H.fit(Ra, np.full(len(terms), 1e-6))
    Rb = H.Races(b.race_id.values, b.win.values, b.offset.values, b[[t + '_z' for t in terms]].values)
    return Rb.loglik_per_race(bb).sum() - Rb.loglik_per_race(np.zeros(len(terms))).sum()
best = None
for k in [1, 3, 10, 30]:
    add_records(k); x = qld_frame(); g5 = gain_inner(x, ['c_rec']); g7 = gain_inner(x, ['g_rec', 'd_rec'])
    RES.append({'k': k, 'inner_gain_course_record': round(g5, 2), 'inner_gain_going_distance_records': round(g7, 2)})
    if best is None or g5 + g7 > best[0]: best = (g5 + g7, k)
K = best[1]; add_records(K); x = qld_frame()
print(pd.DataFrame(RES).to_string(index=False), '\nchosen k', K)
# ---------- Qld tests ----------
def qtest(terms):
    dv, ev = x[x.period == 'development'], x[x.period == 'evaluation']
    b = H.fit(H.Races(dv.race_id.values, dv.win.values, dv.offset.values, dv[[t + '_z' for t in terms]].values), np.full(len(terms), 1e-6))
    Re = H.Races(ev.race_id.values, ev.win.values, ev.offset.values, ev[[t + '_z' for t in terms]].values); rid = ev.race_id.values[Re.o][Re.starts]
    A = pd.DataFrame({'race_id': rid, 'lp': Re.loglik_per_race(np.zeros(len(terms))), 'hit': Re.top_hit(np.zeros(len(terms)))}).set_index('race_id')
    B = pd.DataFrame({'race_id': rid, 'lp': Re.loglik_per_race(b), 'hit': Re.top_hit(b)}).set_index('race_id')
    mid = ev.drop_duplicates('race_id').set_index('race_id').meeting_id; A['meeting_id'] = mid; B['meeting_id'] = mid
    return A, B, dict(zip(terms, np.round(b, 3)))
rows = []
for test, terms in [('P5 16 horse-course record (Qld)', ['c_rec']), ('P7 17 going + distance records (Qld)', ['g_rec', 'd_rec']), ('sec home track (Qld)', ['at_home'])]:
    A, B, cf = qtest(terms); m, lo, hi, p = boot_diff(A, B); _, mlo, mhi, mp = boot_diff(A, B, by='month')
    rows.append({'test': test, 'races': len(A), 'coef_per_sd': cf, 'fit_gain_per_race': round(m, 5), 'lo95_meetings': round(lo, 5), 'hi95_meetings': round(hi, 5),
                 'lo95_months': round(mlo, 5), 'hi95_months': round(mhi, 5), 'p_meetings': round(p, 4), 'top_pick_diff_pts': round(100 * (B.hit.mean() - A.hit.mean()), 2)})
# ---------- NSW/Vic/ACT tests (common-feature baseline + national rating) ----------
F_ = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform']; A_ = ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']; R_ = ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays']
N = U[(U.state != 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1]
nx = prep(N, F_ + A_ + R_ + ['dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'at_home'])
base = F_ + A_ + R_ + ['dyn_nat']
r0 = score(nx, base, fit(nx, base))
for test, terms in [('P6 16 horse-course record (NSW/Vic)', ['c_rec']), ('P8 17 going + distance records (NSW/Vic)', ['g_rec', 'd_rec']), ('sec home track (NSW/Vic)', ['at_home'])]:
    b = fit(nx, base + terms); r1 = score(nx, base + terms, b); m, lo, hi, p = boot_diff(r0, r1); _, mlo, mhi, mp = boot_diff(r0, r1, by='month')
    rows.append({'test': test, 'races': len(r0), 'coef_per_sd': dict(zip(terms, np.round(b[-len(terms):], 3))), 'fit_gain_per_race': round(m, 5), 'lo95_meetings': round(lo, 5), 'hi95_meetings': round(hi, 5),
                 'lo95_months': round(mlo, 5), 'hi95_months': round(mhi, 5), 'p_meetings': round(p, 4), 'top_pick_diff_pts': round(100 * (r1.hit.mean() - r0.hit.mean()), 2)})
T = pd.DataFrame(rows); T.to_csv('out/out_s16_17_tests.csv', index=False); print(T.to_string(index=False))
pd.DataFrame(RES).to_csv('out/out_s16_17_k_grid.csv', index=False)
# descriptive: how much evidence a course record usually rests on
ev = U[(U.date >= '2025-01-01')]
print('runs with 3+ earlier runs at the course:', round((ev.c_rec_n >= 3).mean(), 3), '| median earlier runs at course', ev.c_rec_n.median())
