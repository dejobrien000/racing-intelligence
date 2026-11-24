"""Shared fitting and evaluation for engine experiments. Within-race conditional logit (hier_tools, tiny ridge), metrics per
race on identical races: winner log-probability (fit), top pick won, winner in top 3, Spearman between score and finishing
order (finishers), plus meeting-bootstrap intervals for differences. Frames: Qld (tracked; full feature set) and NSW/Vic/ACT."""
import json, numpy as np, pandas as pd, hier_tools as H
from clogit_tools import eligible, prep
QCOEF = json.load(open('benchmarks/candidates_b4_national/manifest.json'))['coefficients_per_dev_sd']
NCAND = json.load(open('benchmarks/candidates_national_common/manifest.json'))['candidates']
QFAM = {'Ability & opposition rating': ['dyn_nat'], 'Ability figures & opposition faced': ['a_avg3', 'a_best3', 'a_fs3', 'missfig'], 'Weight vs field': ['a_wt_rel'],
        'Recent form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'Closing sectionals': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
        'Barrier & race shape': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
        'Track/distance/going history': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
        'Fitness & spacing': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
assert sorted(sum(QFAM.values(), [])) == sorted(QCOEF), 'family map must cover the Qld operational model exactly'
NV2 = list(NCAND['nat_v2 (+ horse records)'])
NFAM = {'Ability & opposition rating': ['dyn_nat'], 'Ability figures & opposition faced': ['a_rec', 'a_best3', 'a_fs3', 'missfig'], 'Weight vs field': ['a_wt_rel'],
        'Recent form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'Fitness & spacing': ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays'],
        'Horse course/going/distance records': ['c_rec', 'g_rec', 'd_rec']}
assert sorted(sum(NFAM.values(), [])) == sorted(NV2)

def qld_frame(U, extra=()):
    X = pd.read_parquet('features.parquet')
    has = X.f_avgfp3.notna()
    for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
    q = U[U.state == 'QLD'].dropna(subset=['q_race_id']).drop(columns=['race_id', 'horse_id'], errors='ignore').rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
    keep = ['race_id', 'horse_id'] + [c for c in q.columns if c not in X.columns and c not in ('race_id', 'horse_id')]
    X = X.drop(columns=['dyn_nat'], errors='ignore').merge(q[keep], on=['race_id', 'horse_id'], how='left')
    X = X.merge(pd.read_parquet('pace_figures.parquet')[['race_id', 'horse_id', 'rec_rating_pa1']], on=['race_id', 'horse_id'], how='left')
    fp = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'finish_pos']).rename(columns={'finish_pos': 'fpos'}); X = X.merge(fp, on=['race_id', 'horse_id'], how='left')
    X['meeting_date'] = pd.to_datetime(X.meeting_date)
    return eligible(X)

def nat_frame(U):
    N = U[(U.state != 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1].copy()
    N['fpos'] = N.finish_pos; N['meeting_date'] = N.date; return N

def zcols(x, cols):
    new = [c for c in cols if c + '_z' not in x]
    if new:
        p = prep(x[['race_id', 'period'] + new], new); x[[c + '_z' for c in new]] = p[[c + '_z' for c in new]].values
    return x

def fit(x, cols, mask, tau=1e-6, offset=None):
    d = x[mask]; off = np.zeros(len(d)) if offset is None else offset[mask]
    R = H.Races(d.race_id.values, d.win.values, off, d[[c + '_z' for c in cols]].values); return H.fit(R, np.full(len(cols), tau))

def eta(x, cols, b, offset=None):
    e = x[[c + '_z' for c in cols]].values @ b if len(cols) else np.zeros(len(x))
    return e + (0 if offset is None else offset)

def metrics(x, e, mask):
    t = x.loc[mask, ['race_id', 'meeting_id', 'meeting_date', 'win', 'fpos', 'field']].copy(); t['e'] = e[mask.values] if hasattr(mask, 'values') else e[mask]
    mx = t.groupby('race_id').e.transform('max'); t['lp'] = t.e - (np.log(np.exp(t.e - mx).groupby(t.race_id).transform('sum')) + mx)
    t['rk'] = t.groupby('race_id').e.rank(ascending=False, method='first')
    g = t.groupby('race_id')
    r = pd.DataFrame({'meeting_id': g.meeting_id.first(), 'date': g.meeting_date.first(), 'field': g.field.first(),
                      'lp': t[t.win == 1].set_index('race_id').lp, 'hit': t[t.win == 1].set_index('race_id').rk.eq(1).astype(float),
                      'top3': t[t.win == 1].set_index('race_id').rk.le(3).astype(float)})
    f = t[t.fpos.notna()]; f = f.assign(re=f.groupby('race_id').e.rank(ascending=False), rf=f.groupby('race_id').fpos.rank())
    r['rho'] = f.groupby('race_id')[['re', 'rf']].apply(lambda d: d.re.corr(d.rf, method='pearson') if len(d) > 2 else np.nan)
    r['null'] = -np.log(r.field); return r

def summary(r):
    return {'races': len(r), 'fit_%': round(100 * (1 - r.lp.sum() / r.null.sum()), 2), 'top_pick_%': round(100 * r.hit.mean(), 2), 'winner_in_top3_%': round(100 * r.top3.mean(), 2), 'order_rho': round(r.rho.mean(), 4)}

def diff(a, b, reps=600, seed=11):
    """b - a on identical races: per-race log-lik gain, top pick, top 3, ordering; meeting bootstrap 95% CI."""
    rng = np.random.default_rng(seed); j = a.index.intersection(b.index); a, b = a.loc[j], b.loc[j]; out = {'races': len(j)}
    key = a.meeting_id.values; um, inv = np.unique(key, return_inverse=True)
    for col, sc in [('lp', 1), ('hit', 100), ('top3', 100), ('rho', 1)]:
        d = (b[col] - a[col]).fillna(0).values * sc; s = np.bincount(inv, d); n = np.bincount(inv)
        bs = [s[k].sum() / n[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(reps))]
        out[col] = round(float(d.mean()), 5 if col in ('lp', 'rho') else 2); out[col + '_lo'] = round(float(np.percentile(bs, 2.5)), 5 if col in ('lp', 'rho') else 2); out[col + '_hi'] = round(float(np.percentile(bs, 97.5)), 5 if col in ('lp', 'rho') else 2)
    return out
