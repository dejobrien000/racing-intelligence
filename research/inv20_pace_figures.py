"""Batch 3, Study 6 (plan: batch03_plan.md). Pace-adjusted figures from individual sectionals (Queensland).
Builds PA1 (tempo-corrected figure), the late-section figure and PA2 (blend), and run-profile components; then compares
pre-race (recency-weighted) versions with the v0 figure, alone and inside the frozen combined_v1 benchmark.
Chronological out-of-sample: all slopes and pars fitted on races before 2025; scored 2025-26.
Usage: python3 inv20_pace_figures.py ../history/history.duckdb  -> out/out_s6_*.csv, pace_figures.parquet"""
import sys, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
con = duckdb.connect(sys.argv[1], read_only=True)
d = pd.read_parquet('runs_rated_dev.parquet').drop_duplicates(['race_id', 'horse_id'])
d['meeting_date'] = pd.to_datetime(d.meeting_date); dev = d.meeting_date < '2025-01-01'
# elapsed time at 600m to go: each runner, and the leader (fastest elapsed) of the race
t6 = con.execute("""select s.race_id, s.saddlecloth, s.inter_s t600 from sectional s join race r using (race_id)
                    where r.distance_m - s.segment_end_m = 600""").fetchdf()
d = d.merge(t6, on=['race_id', 'saddlecloth'], how='left')
d.loc[~d.finished | ~(d.t600 > 0), 't600'] = np.nan
d['lead600'] = d.groupby('race_id')['t600'].transform('min')
d['early_km'] = (d.distance_m - 600) / 1000
d['td'] = d.track + '|' + d.distance_m.fillna(0).astype(int).astype(str)
ok = d.distance_m >= 1000
d['lead600_adj'] = d.lead600 - d.variant * d.early_km                     # leader's early time, day's track speed removed
par_lead = d[dev & ok & (d.win == 1)].groupby('td')['lead600_adj'].median()
d['early_excess'] = (d.lead600_adj - d.td.map(par_lead)).where(ok)          # + = slower early than usual (seconds)
d['early_excess'] = d.early_excess.clip(-8, 8)
# slope c: how much of the early excess shows up in the final time (winners, development, class held steady)
w = d[dev & (d.win == 1) & d.early_excess.notna() & d.par.notna() & d.race_time_s.notna()].copy()
w['tres'] = w.race_time_s - (w.par + w.km * w.variant)
mc = smf.ols('tres ~ early_excess + C(class_bucket)', data=w).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(w.meeting_date.dt.strftime('%Y-%m-%d') + w.track)[0]})
c_hat = mc.params['early_excess']
# late section: last 600 vs par for track/distance, early tempo held steady (slope e on development winners)
w['l6res'] = w.l600 - w.td.map(w.groupby('td')['l600'].median()) - 0.6 * w.variant
w2 = w.dropna(subset=['l6res'])
me = smf.ols('l6res ~ early_excess', data=w2).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(w2.meeting_date.dt.strftime('%Y-%m-%d') + w2.track)[0]})
e_hat = me.params['early_excess']
par_l6 = w.groupby('td')['l600'].median()
print(f'c (share of early excess left in final time) = {c_hat:.3f} (se {mc.bse["early_excess"]:.3f}); e (late 600 change per second slower early) = {e_hat:.3f} (se {me.bse["early_excess"]:.3f}); races {len(w)}')
sec_per_l = 2.4 / d.speed
d['rating_pa1'] = d.rating + d.kg_per_l * (c_hat * d.early_excess.fillna(0)) / sec_per_l    # credit for time lost to a slow early pace
d.loc[d.rating.isna(), 'rating_pa1'] = np.nan
d['late_resid'] = d.l600 - d.td.map(par_l6) - 0.6 * d.variant - e_hat * d.early_excess      # + = slower late than the tempo implies
secl_late = 2.4 / (600 / d.td.map(par_l6))
d['late_fig'] = 100 - d.kg_per_l * d.late_resid / secl_late + (pd.to_numeric(d.weight_kg, errors='coerce') - 57)
d.loc[d.rating.isna() | d.late_resid.isna(), 'late_fig'] = np.nan
d['rating_pa2'] = 0.5 * d.rating + 0.5 * d.late_fig
d['early_own'] = (d.t600 - d.variant * d.early_km - d.td.map(par_lead)).where(ok).clip(-10, 15)   # own early time vs par (+ slower)
# pre-race recency-weighted versions over the last 6 runs
d = d.sort_values(['horse_id', 'meeting_date', 'race_no']).reset_index(drop=True)
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
def rec(s):
    a = s.shift().values; out = np.full(len(a), np.nan)
    for i in range(len(a)):
        h = a[max(0, i - 5):i + 1][::-1]; h = h[~np.isnan(h)]
        if len(h): out[i] = np.dot(h, wts[:len(h)]) / wts[:len(h)].sum()
    return pd.Series(out, index=s.index)
g = d.groupby('horse_id')
for c in ['rating', 'rating_pa1', 'rating_pa2', 'late_fig']: d['rec_' + c] = g[c].transform(rec)
for c in ['rating_pa1']:
    d['avg3_' + c] = g[c].transform(lambda s: s.shift().rolling(3, min_periods=1).mean()); d['best3_' + c] = g[c].transform(lambda s: s.shift().rolling(3, min_periods=1).max())
d['last_early_own'] = g['early_own'].shift(); d['last_late_resid'] = -g['late_resid'].shift(); d['last_tempo'] = g['early_excess'].shift()
d['last_fig'] = g['rating'].shift()
keep = ['race_id', 'horse_id', 'rating', 'rating_pa1', 'late_fig', 'rating_pa2', 'early_excess', 'late_resid', 'early_own', 'rec_rating', 'rec_rating_pa1', 'rec_rating_pa2', 'rec_late_fig',
        'avg3_rating_pa1', 'best3_rating_pa1', 'last_early_own', 'last_late_resid', 'last_tempo', 'last_fig']
d[keep].to_parquet('pace_figures.parquet')
print('runs with PA1:', int(d.rating_pa1.notna().sum()), ' with late-section figure:', int(d.late_fig.notna().sum()), ' of', len(d))
# descriptive: how different are the figures?  correlation with the horse's next figure (repeatability)
d['next_rating'] = g['rating'].shift(-1)
rep = {c: round(d[[c, 'next_rating']].dropna().corr().iloc[0, 1], 3) for c in ['rating', 'rating_pa1', 'rating_pa2', 'late_fig']}
rep_long = {c: round(d[d.distance_m >= 1400][[c, 'next_rating']].dropna().corr().iloc[0, 1], 3) for c in ['rating', 'rating_pa1', 'rating_pa2', 'late_fig']}
print('repeatability with the next v0 figure: all', rep, '| 1400m+', rep_long)

# predictive comparison inside the within-race framework (features.parquet = frozen benchmark inputs)
X = pd.read_parquet('features.parquet').merge(d[['race_id', 'horse_id', 'rec_rating', 'rec_rating_pa1', 'rec_rating_pa2', 'rec_late_fig', 'avg3_rating_pa1', 'best3_rating_pa1',
                                                    'last_early_own', 'last_late_resid', 'last_tempo', 'last_fig']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
X['missform'] = (~has).astype(float); X['missfig'] = (has & X.a_avg3.isna()).astype(float); X['misssec'] = (has & X.s_gap600_avg3.isna()).astype(float)
X['missstyle'] = (has & X.p_style.isna()).astype(float); X['missgoing'] = (has & X.t_going.isna()).astype(float)
X['misspa'] = (has & X.rec_rating_pa1.isna()).astype(float); X['misslate'] = (has & X.rec_late_fig.isna()).astype(float)
G = {'F': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'A': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'],
     'S': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'P': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
     'T': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'R': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
BENCH = [c for v in G.values() for c in v]
newc = ['rec_rating', 'rec_rating_pa1', 'rec_rating_pa2', 'rec_late_fig', 'avg3_rating_pa1', 'best3_rating_pa1', 'last_early_own', 'last_late_resid', 'last_tempo', 'last_fig', 'misspa', 'misslate']
x = prep(eligible(X), sorted(set(BENCH + newc)))
x['long'] = x.distance_m >= 1400
specs = {'v0 recency-weighted alone': ['rec_rating', 'missform', 'missfig'], 'PA1 recency-weighted alone': ['rec_rating_pa1', 'missform', 'misspa'],
         'PA2 blend recency-weighted alone': ['rec_rating_pa2', 'missform', 'misslate'], 'late-section figure alone': ['rec_late_fig', 'missform', 'misslate'],
         'benchmark (frozen combined_v1)': BENCH,
         'benchmark, PA1 in place of v0': [c.replace('a_avg3', 'avg3_rating_pa1').replace('a_best3', 'best3_rating_pa1') for c in BENCH] + ['misspa'],
         'benchmark + late-section figure': BENCH + ['rec_late_fig', 'misslate'],
         'benchmark + last-start run profile (early, late, tempo)': BENCH + ['last_early_own', 'last_late_resid', 'last_tempo', 'misslate']}
res = {k: score(x, v, fit(x, v)) for k, v in specs.items()}
info = x[x.period == 'evaluation'].groupby('race_id').agg(long=('long', 'first'), tier=('venue_tier', 'first'))
def sub(r, which):
    if which == 'all': return r
    if which == '1400m+': return r[info.loc[r.index, 'long'].values]
    if which == 'metro': return r[(info.loc[r.index, 'tier'] == 'metro').values]
    if which == 'metro 1400m+': return r[(info.loc[r.index, 'long'] & (info.loc[r.index, 'tier'] == 'metro')).values]
    if which == 'under 1400m': return r[~info.loc[r.index, 'long'].values]
rows = []
for k, r in res.items():
    for wh in ['all', '1400m+', 'under 1400m', 'metro', 'metro 1400m+']:
        s = sub(r, wh); rows.append({'model': k, 'races': wh, 'n_races': len(s), 'fit_%': round(fit_pct(s), 2), 'top_pick_%': round(100 * s.hit.mean(), 1)})
t = pd.DataFrame(rows); t.to_csv('out/out_s6_models.csv', index=False); print(t.pivot(index='model', columns='races', values='fit_%').to_string())
comps = [('P1', 'v0 recency-weighted alone', 'PA1 recency-weighted alone', '1400m+'), ('P2', 'v0 recency-weighted alone', 'PA1 recency-weighted alone', 'all'),
         ('P3', 'benchmark (frozen combined_v1)', 'benchmark, PA1 in place of v0', '1400m+'), ('P4', 'benchmark (frozen combined_v1)', 'benchmark, PA1 in place of v0', 'metro'),
         ('P5', 'benchmark (frozen combined_v1)', 'benchmark + late-section figure', '1400m+'),
         ('sec', 'v0 recency-weighted alone', 'PA2 blend recency-weighted alone', '1400m+'), ('sec', 'v0 recency-weighted alone', 'late-section figure alone', '1400m+'),
         ('sec', 'benchmark (frozen combined_v1)', 'benchmark, PA1 in place of v0', 'all'), ('sec', 'benchmark (frozen combined_v1)', 'benchmark, PA1 in place of v0', 'metro 1400m+'),
         ('sec', 'benchmark (frozen combined_v1)', 'benchmark + late-section figure', 'all'), ('sec', 'benchmark (frozen combined_v1)', 'benchmark + last-start run profile (early, late, tempo)', 'all'),
         ('sec', 'benchmark (frozen combined_v1)', 'benchmark + last-start run profile (early, late, tempo)', '1400m+')]
out = []
for tid, a, b, wh in comps:
    ra, rb = sub(res[a], wh), sub(res[b], wh)
    m1, lo1, hi1, p1 = boot_diff(ra, rb, 'lp'); m2, lo2, hi2, p2 = boot_diff(ra, rb, 'lp', by='month'); h1 = boot_diff(ra, rb, 'hit')
    out.append({'test': tid, 'comparison': f'{b} vs {a}', 'races': wh, 'n_races': len(ra), 'fit_gain_per_race': round(m1, 4), 'lo95_meetings': round(lo1, 4), 'hi95_meetings': round(hi1, 4),
                'lo95_months': round(lo2, 4), 'hi95_months': round(hi2, 4), 'p_one_sided_meetings': round(p1, 4), 'p_one_sided_months': round(p2, 4),
                'top_pick_diff_pts': round(100 * h1[0], 1), 'tp_lo95': round(100 * h1[1], 1), 'tp_hi95': round(100 * h1[2], 1)})
o = pd.DataFrame(out); o.to_csv('out/out_s6_comparisons.csv', index=False); print(o.to_string(index=False))
# composition of the scored races
comp = x[x.period == 'evaluation'].groupby('race_id').agg(tier=('venue_tier', 'first'), long=('long', 'first'))
print('scored races by tier:', comp.tier.value_counts().to_dict(), '| 1400m+:', int(comp.long.sum()), '| runners:', int((x.period == 'evaluation').sum()), '| horses:', x[x.period == 'evaluation'].horse_id.nunique())
pd.DataFrame([{'c_hat': c_hat, 'c_se': mc.bse['early_excess'], 'e_hat': e_hat, 'e_se': me.bse['early_excess'], 'dev_winner_races': len(w), **{f'repeat_{k}': v for k, v in rep.items()}, **{f'repeat1400_{k}': v for k, v in rep_long.items()}}]).to_csv('out/out_s6_slopes.csv', index=False)
