"""Illustration only (retrospective): ranked runners with reasons for one race, from the frozen candidate
'combined_v1 + dynamic rating'. Each information group's contribution = sum of (learned weight x runner's race-relative
value) over that group's features, so the reasons are the model's own learned weights, never hand-added percentages.
Usage: python3 demo_ranked_reasons.py <scratch folder from score_frozen.py> <race_id or 'auto'>"""
import sys, json, numpy as np, pandas as pd
W, RID = sys.argv[1], sys.argv[2]; sys.path.insert(0, W)
from clogit_tools import eligible, prep
import dyn_rating as DR
man = json.load(open('benchmarks/candidates_b4/manifest.json')); coef = man['coefficients_per_dev_sd']['combined_v1 + dynamic rating']; p = man['dynamic_rating_params']
q = pd.read_parquet(f'{W}/runs.parquet')
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0
P = DR.prepare(d); P['dyn_mu'], P['dyn_sd'], _ = DR.run(P, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
X = pd.read_parquet(f'{W}/features.parquet').merge(P[['race_id', 'horse_id', 'dyn_mu', 'dyn_sd']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
x = prep(eligible(X), list(coef))
if RID == 'auto':
    c = x[(x.meeting_date >= '2026-11-01') & x.track.isin(['Eagle_Farm', 'Doomben'])].groupby('race_id').agg(n=('win', 'size'), d=('meeting_date', 'first'))
    RID = c[c.n >= 10].sort_values('d').index[-1]
r = x[x.race_id == RID].copy()
G = {'Opposition-aware rating': ['dyn_mu'], 'Recent ability figures': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'],
     'Recent form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'Closing sectionals': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'Barrier and race shape': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
     'Track, distance, going': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'Fitness and spacing': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
for g, cs in G.items(): r[g] = sum(coef[c] * r[c + '_z'] for c in cs if c in coef)
r['lp'] = r[list(G)].sum(axis=1); e = np.exp(r.lp - r.lp.max()); r['chance_%'] = (100 * e / e.sum()).round(1)
r = r.sort_values('lp', ascending=False); r['rank'] = np.arange(1, len(r) + 1)
def why(row):
    s = row[list(G)].sort_values(); pos = [f'{k} +' for k, v in s[::-1].items() if v > 0.15][:2]; neg = [f'{k} -' for k, v in s.items() if v < -0.15][:1]
    return '; '.join(pos + neg) or 'no group stands out'
r['reasons'] = r.apply(why, axis=1)
nm = q.drop_duplicates(['race_id', 'horse_id']).set_index(['race_id', 'horse_id'])
r['horse'] = [nm.loc[(RID, h), 'name'] for h in r.horse_id]; r['finished'] = [int(nm.loc[(RID, h), 'finish_pos']) for h in r.horse_id]
meta = nm.loc[RID].iloc[0]
print(RID, meta.track, meta.meeting_date, meta.race_no, meta.distance_m, 'm', meta.race_name)
out = r[['rank', 'horse', 'chance_%', 'reasons', 'finished']]; print(out.to_string(index=False)); out.to_csv('out/out_demo_ranked_reasons.csv', index=False)
gap = r['chance_%'].iloc[0] - r['chance_%'].iloc[1]; print('top-two gap pts', round(gap, 1), '| top rating sd kg', round(float(r.dyn_sd.iloc[0]), 2))
