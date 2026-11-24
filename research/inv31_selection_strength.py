"""Selection strength, first check (design in Batch 5 tab; no thresholds are set here).
Frozen candidate "combined_v1 + national dynamic rating", Qld tracked races scored 2025-01-01 to 2026-11-23.
Per race: the model's top chance; separation from the second; uncertainty (top runner's rating sd; share of field new
to our data); evidence completeness (share of field with figure, sectionals and running style); agreement (how many of
three independent groups - ability/opposition, recent form, race shape - also rank the top pick first); reliability
in similar races (top-pick win rate in the same tier x distance band x class group during development, shrunk).
Question: does any of these predict whether the top pick wins BEYOND the model's own top chance?
Meta-model fitted on 2025 races, tested on 2026 races (chronological). Outputs out/out_sel_*.csv"""
import json, numpy as np, pandas as pd, statsmodels.api as sm
from clogit_tools import eligible, prep
mn = json.load(open('benchmarks/candidates_b4_national/manifest.json')); COEF = mn['coefficients_per_dev_sd']
X = pd.read_parquet('features.parquet').merge(pd.read_parquet('dyn_nat_qld.parquet'), on=['race_id', 'horse_id'], how='left')
import dyn_rating as DR
q = pd.read_parquet('runs.parquet'); p = json.load(open('benchmarks/candidates_b4/manifest.json'))['dynamic_rating_params']
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0; P = DR.prepare(d); P['dyn_sd'] = DR.run(P, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])[1]
X = X.merge(P[['race_id', 'horse_id', 'dyn_sd']], on=['race_id', 'horse_id'], how='left').merge(q[['race_id', 'horse_id', 'class_group']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
x = prep(eligible(X), sorted(COEF))
z = lambda cs: sum(COEF[c] * x[c + '_z'] for c in cs if c in COEF)
x['lp'] = z(COEF); x['g_ability'] = z(['dyn_nat', 'a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']); x['g_form'] = z(['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'])
x['g_shape'] = z(['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'])
e = np.exp(x.lp - x.groupby('race_id').lp.transform('max')); x['p'] = e / e.groupby(x.race_id).transform('sum')
x['full_inputs'] = ((x.missform == 0) & (x.missfig == 0) & (x.misssec == 0) & (x.missstyle == 0)).astype(float)
x['dband'] = pd.cut(x.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
rows = []
for rid, g in x.groupby('race_id'):
    g = g.sort_values('lp', ascending=False); t = g.iloc[0]
    agree = sum(int(g[c].idxmax() == t.name) for c in ['g_ability', 'g_form', 'g_shape'])
    rows.append({'race_id': rid, 'date': t.meeting_date, 'period': t.period, 'tier': t.venue_tier, 'dband': t.dband, 'cls': t.class_group, 'field': len(g),
                 'p_top': t.p, 'gap': t.p - g.p.iloc[1], 'top_sd': t.dyn_sd, 'share_new': g.missform.mean(), 'share_full': g.full_inputs.mean(), 'agree': agree, 'top_won': int(t.win == 1)})
R = pd.DataFrame(rows)
dv = R[R.period == 'development']; grp = ['tier', 'dband', 'cls']
rel = dv.groupby(grp).agg(n=('top_won', 'size'), w=('top_won', 'sum'), pexp=('p_top', 'sum')).reset_index()
rel['reliability'] = (rel.w + 20) / (rel.pexp + 20)                       # actual / expected top-pick wins in similar development races, shrunk to 1
R = R.merge(rel[grp + ['reliability']], on=grp, how='left'); R['reliability'] = R.reliability.fillna(1.0)
ev = R[R.period == 'evaluation'].copy(); ev['y2026'] = pd.to_datetime(ev.date).dt.year == 2026
# calibration of the model's own top chance
ev['bin'] = pd.cut(ev.p_top, [0, .15, .2, .25, .3, .4, 1]); cal = ev.groupby('bin', observed=True).agg(races=('top_won', 'size'), predicted=('p_top', 'mean'), actual=('top_won', 'mean')).round(3)
cal.to_csv('out/out_sel_calibration.csv'); print(cal.to_string())
lg = lambda p_: np.log(p_ / (1 - p_))
ev['lp_top'] = lg(ev.p_top.clip(1e-4, 1 - 1e-4))
tr, te = ev[~ev.y2026], ev[ev.y2026]
def ll(m, df, cols):
    pr = m.predict(sm.add_constant(df[cols], has_constant='add')); y = df.top_won.values
    return float(np.mean(y * np.log(pr) + (1 - y) * np.log(1 - pr)))
base = ['lp_top']; m0 = sm.Logit(tr.top_won, sm.add_constant(tr[base])).fit(disp=0); b0 = ll(m0, te, base)
out = [{'measure': '(model top chance only)', 'coef': None, 'p_value_2025': None, 'test_loglik_2026': round(b0, 4), 'gain_vs_top_chance_only': 0.0}]
for meas in ['gap', 'top_sd', 'share_new', 'share_full', 'agree', 'reliability']:
    cols = base + [meas]; m1 = sm.Logit(tr.top_won, sm.add_constant(tr[cols])).fit(disp=0)
    out.append({'measure': meas, 'coef': round(m1.params[meas], 3), 'p_value_2025': round(m1.pvalues[meas], 3), 'test_loglik_2026': round(ll(m1, te, cols), 4), 'gain_vs_top_chance_only': round(ll(m1, te, cols) - b0, 4)})
O = pd.DataFrame(out); O.to_csv('out/out_sel_measures.csv', index=False); print(O.to_string(index=False))
ag = ev.groupby('agree').agg(races=('top_won', 'size'), mean_top_chance=('p_top', 'mean'), top_pick_win_rate=('top_won', 'mean')).round(3); ag.to_csv('out/out_sel_agreement.csv'); print(ag.to_string())
print('races 2025 (fit):', len(tr), '| 2026 (test):', len(te), '| mean top chance', round(ev.p_top.mean(), 3), '| top-pick win rate', round(ev.top_won.mean(), 3))
