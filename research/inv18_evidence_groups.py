"""Batch 2, Study 2 (plan: batch02_plan.md). Evidence groups: what does each add, independently?
Within-race conditional logit, fitted before 2025, scored Jan 2025 - Nov 2026 (chronological out-of-sample, not independent).
Usage: python3 inv18_evidence_groups.py  (reads features.parquet) -> out/out_s2_*.csv"""
import numpy as np, pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit
from sklearn.ensemble import HistGradientBoostingClassifier
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
X = pd.read_parquet('features.parquet')
has = X.f_avgfp3.notna()
X['missform'] = (~has).astype(float)                                   # no earlier Queensland run
X['missfig'] = (has & X.a_avg3.isna()).astype(float)                   # earlier run(s) but no figure
X['misssec'] = (has & X.s_gap600_avg3.isna()).astype(float)
X['missstyle'] = (has & X.p_style.isna()).astype(float)
X['missgoing'] = (has & X.t_going.isna()).astype(float)
G = {'F simple form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'],
     'A ability and opposition': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'],   # a_cls_gap dropped: within a race it equals the average figure
     'S sectional': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'P race shape': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],   # number of other leaders only enters via leader x pressure (race-level otherwise)
     'T track and distance': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'R fitness and recency': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
cols = sorted({c for v in G.values() for c in v})
x = prep(eligible(X), cols)
ev_races = x[x.period == 'evaluation'].race_id.nunique()
print('eligible races: development', x[x.period == 'development'].race_id.nunique(), 'evaluation', ev_races, '| runners', len(x))
ALL = [c for v in G.values() for c in v]
cache = {}
def run(name, cs):
    if name not in cache:
        b = fit(x, cs) if cs else np.array([]); cache[name] = (score(x, cs, b), b, cs)
    return cache[name][0]
null = run('null', [])
rows, comps = [], []
def comp(label, a, b, test=''):
    m, lo, hi, p = boot_diff(cache[a][0], cache[b][0], 'lp'); hm, hlo, hhi, _ = boot_diff(cache[a][0], cache[b][0], 'hit')
    comps.append({'test': test, 'comparison': label, 'fit_gain_per_race': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'p_one_sided': round(p, 4),
                  'top_pick_diff_pts': round(100 * hm, 1), 'tp_lo95': round(100 * hlo, 1), 'tp_hi95': round(100 * hhi, 1)})
run('F', G['F simple form'])
for gname, gc in G.items():
    run(gname + ' alone', gc if gname[0] == 'F' else gc + ['missform']); rows.append({'model': gname + ' alone', 'fit_%': round(fit_pct(cache[gname + ' alone'][0]), 2), 'top_pick_%': round(100 * cache[gname + ' alone'][0].hit.mean(), 1)})
    if gname[0] != 'F':
        run('F + ' + gname, G['F simple form'] + gc); comp(f'{gname}: added to simple form', 'F', 'F + ' + gname)
run('Full', ALL); rows.append({'model': 'Full (all groups)', 'fit_%': round(fit_pct(cache['Full'][0]), 2), 'top_pick_%': round(100 * cache['Full'][0].hit.mean(), 1)})
for i, gname in enumerate([g for g in G if g[0] != 'F']):
    rest = [c for k, v in G.items() if k != gname for c in v]
    run('Full - ' + gname, rest); comp(f'{gname}: beyond form and all other groups', 'Full - ' + gname, 'Full', f'P{i + 2}')
# P8 race-shape interactions
noint = [c for c in ALL if c not in ('p_bar_x_style', 'p_lead_x_press', 'p_lone')]
run('Full - shape interactions', noint); comp('Race-shape interactions beyond main effects', 'Full - shape interactions', 'Full', 'P8')
# P7 stacked separate profiles: each group's own score, then weights fitted on development
for gname in G:
    b = cache[gname + ' alone'][1]; z = [c + '_z' for c in cache[gname + ' alone'][2]]
    sc = x[z].values @ b; x['sc_' + gname[0]] = sc
for k in 'FASPTR':
    x['sc_' + k + '_z'] = x['sc_' + k] - x.groupby('race_id')['sc_' + k].transform('mean')
stk = ['sc_' + k for k in 'FASPTR']
run('Stacked profiles', stk); rows.append({'model': 'Stacked separate profiles', 'fit_%': round(fit_pct(cache['Stacked profiles'][0]), 2), 'top_pick_%': round(100 * cache['Stacked profiles'][0].hit.mean(), 1)})
comp('One combined model vs stacked separate profiles (positive = combined better)', 'Stacked profiles', 'Full', 'P7')
# P9 trees on race-centred inputs, normalised within race
zc = [c + '_z' for c in ALL]; dv, ev = x[x.period == 'development'], x[x.period == 'evaluation']
tr, va = dv[dv.meeting_date < '2024-01-01'], dv[dv.meeting_date >= '2024-01-01']
def race_ll(df, p):
    t = df[['race_id', 'meeting_id', 'win', 'field']].copy(); t['p'] = p; t['p'] = t.p / t.groupby('race_id')['p'].transform('sum')
    w = t[t.win == 1].set_index('race_id'); top = t.loc[t.groupby('race_id')['p'].idxmax()].set_index('race_id')
    return pd.DataFrame({'meeting_id': w.meeting_id, 'field': w.field, 'lp': np.log(w.p), 'hit': top.win.reindex(w.index).values, 'null': -np.log(w.field)})
best = None
for depth in [2, 3]:
    for it in [150, 300]:
        m = HistGradientBoostingClassifier(max_depth=depth, learning_rate=0.05, max_iter=it, min_samples_leaf=200, l2_regularization=2.0, random_state=1).fit(tr[zc], tr.win)
        ll = race_ll(va, m.predict_proba(va[zc])[:, 1]).lp.sum()
        if best is None or ll > best[0]: best = (ll, depth, it)
m = HistGradientBoostingClassifier(max_depth=best[1], learning_rate=0.05, max_iter=best[2], min_samples_leaf=200, l2_regularization=2.0, random_state=1).fit(dv[zc], dv.win)
cache['Trees'] = (race_ll(ev, m.predict_proba(ev[zc])[:, 1]), None, zc)
rows.append({'model': f'Trees (depth {best[1]}, {best[2]} rounds)', 'fit_%': round(fit_pct(cache['Trees'][0]), 2), 'top_pick_%': round(100 * cache['Trees'][0].hit.mean(), 1)})
comp('Trees vs combined conditional logit (positive = trees better)', 'Full', 'Trees', 'P9')
t = pd.DataFrame(rows); t.to_csv('out/out_s2_models.csv', index=False); print(t.to_string(index=False))
c = pd.DataFrame(comps); c.to_csv('out/out_s2_comparisons.csv', index=False); print(c.to_string(index=False))
# agreement between groups' own top picks (evaluation)
e = x[x.period == 'evaluation'].copy()
for k in 'ASPTR':
    e['top_' + k] = e.groupby('race_id')['sc_' + k].transform(lambda s: (s.rank(method='first', ascending=False) == 1).astype(int))
e['votes'] = e[['top_' + k for k in 'ASPTR']].sum(axis=1)
e['top_F'] = e.groupby('race_id')['sc_F'].transform(lambda s: (s.rank(method='first', ascending=False) == 1).astype(int))
ag = []
for k, h in e.groupby('votes'):
    ag.append({'groups (of A,S,P,T,R) naming the runner as top pick': int(k), 'runners': len(h), 'win_%': round(100 * h.win.mean(), 1), 'A/E': round(h.win.sum() / (1 / h.field).sum(), 2),
               'also simple-form top pick %': round(100 * h.top_F.mean(), 1)})
for k, h in e[e.top_F == 1].groupby('votes'):
    ag.append({'groups (of A,S,P,T,R) naming the runner as top pick': f'{int(k)} (and simple-form top pick)', 'runners': len(h), 'win_%': round(100 * h.win.mean(), 1), 'A/E': round(h.win.sum() / (1 / h.field).sum(), 2), 'also simple-form top pick %': 100.0})
a = pd.DataFrame(ag); a.to_csv('out/out_s2_agreement.csv', index=False); print(a.to_string(index=False))
# secondary: coefficients of the full model (per development sd), incl. R23 last-200m term
fb = cache['Full'][1]
dvx = x[x.period == 'development']; mm = ConditionalLogit(dvx.win.values, dvx[[c + '_z' for c in ALL]].values, groups=dvx.race_id.values).fit(disp=0, maxiter=200)
co = pd.DataFrame({'input': ALL, 'coef_per_sd': np.round(mm.params, 3), 'se': np.round(mm.bse, 3), 'p': np.round(mm.pvalues, 4)})
co.to_csv('out/out_s2_full_coefficients.csv', index=False); print(co.to_string(index=False))
# secondary: metro races only (same fitted models)
met = []
for a_, b_ in [('Full - ' + g, 'Full') for g in G if g[0] != 'F'] + [('F', 'Full')]:
    ra, rb = cache[a_][0], cache[b_][0]; idx = ra.index[ra.index.isin(x[(x.venue_tier == 'metro')].race_id)]
    mm_, lo, hi, _ = boot_diff(ra.loc[idx], rb.loc[idx], 'lp')
    met.append({'metro races only': f'{b_} vs {a_}', 'races': len(idx), 'fit_gain_per_race': round(mm_, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4)})
mt = pd.DataFrame(met); mt.to_csv('out/out_s2_metro.csv', index=False); print(mt.to_string(index=False))
