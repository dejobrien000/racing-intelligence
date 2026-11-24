"""Verification of the dynamic opposition rating (Batch 4 candidate), and its record on identical races.
1. Strict chronology: ratings computed on history cut at date T must equal the full-history pre-race ratings for every
   race up to and including T (later races cannot leak backwards). Checked at three cut dates, Qld and national.
2. Own-result blindness: blanking the result of a race must leave every runner's pre-race rating for that race unchanged.
3. Edge cases counted: dead heats, non-finishers, horses with no history, long spells.
4. Identical-race comparison (Qld tracked, scored 2025-01-01 to 2026-11-23, frozen development fits): fit, top pick,
   winner's mean rank, winner in model top 3, Spearman between model order and finishing order.
Outputs out/out_s12v_*.csv"""
import json, numpy as np, pandas as pd
from scipy.stats import spearmanr
import dyn_rating as DR
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
man = json.load(open('benchmarks/candidates_b4/manifest.json')); mn = json.load(open('benchmarks/candidates_b4_national/manifest.json'))
p, pn = man['dynamic_rating_params'], mn['dynamic_rating_params']
q = pd.read_parquet('runs.parquet')
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0
P = DR.prepare(d); P['mu'], P['sd'], _ = DR.run(P, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
rows = []
for T in ['2023-06-30', '2024-12-31', '2026-06-30']:
    cut = P[P.date <= T].copy(); keep = cut.date == pd.Timestamp(T).normalize()
    cut.loc[cut.date == cut.date.max(), 'perf'] = np.nan                       # the last day's results are not known yet
    mu, sd, _ = DR.run(cut.drop(columns=['mu', 'sd']), p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
    diff = np.abs(mu - cut.mu.values)
    rows.append({'test': 'chronology (Qld)', 'cut_date': T, 'runs_compared': len(cut), 'max_abs_diff_kg': float(np.nanmax(diff)), 'last_day_runs': int((cut.date == cut.date.max()).sum())})
rng = np.random.default_rng(7)
for D in rng.choice(P.date.unique(), 5, replace=False):                    # blank one whole race day at a time
    bl = P.copy(); m = (bl.date == D).values; bl.loc[m, 'perf'] = np.nan
    mu_b, _, _ = DR.run(bl.drop(columns=['mu', 'sd']), p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
    rows.append({'test': 'own-result blindness (Qld: all races of one day blanked)', 'cut_date': str(pd.Timestamp(D).date()), 'runs_compared': int(m.sum()), 'max_abs_diff_kg': float(np.nanmax(np.abs(mu_b[m] - P.mu.values[m])))})
U = pd.read_parquet('national_runs.parquet')
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                   'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U)), 'state': U.state})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last').reset_index(drop=True)
PN['mu'], PN['sd'], _ = DR.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
for T in ['2024-06-29', '2025-11-01']:
    cut = PN[PN.date <= T].copy(); cut.loc[cut.date == cut.date.max(), 'perf'] = np.nan
    mu, _, _ = DR.run(cut.drop(columns=['mu', 'sd']), pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
    rows.append({'test': 'chronology (national)', 'cut_date': T, 'runs_compared': len(cut), 'max_abs_diff_kg': float(np.nanmax(np.abs(mu - cut.mu.values))), 'last_day_runs': int((cut.date == cut.date.max()).sum())})
V = pd.DataFrame(rows); V.to_csv('out/out_s12v_leak_tests.csv', index=False); print(V.to_string(index=False))
# edge cases
fp = q.finish_pos.where(q.finish_pos <= q.field)
dh = q[fp == 1].groupby('race_id').size(); nat_dh = U[U.finish_pos == 1].groupby('race').size()
E = pd.DataFrame([{'case': 'dead heats for first (Qld races)', 'count': int((dh > 1).sum()), 'handling': 'both winners margin 0; same performance; race left out of winner-only scoring (needs exactly one winner)'},
                  {'case': 'dead heats for first (national races)', 'count': int((nat_dh > 1).sum()), 'handling': 'as above'},
                  {'case': 'non-finishers / no margin or weight (Qld runs)', 'count': int(P.perf.isna().sum()), 'handling': 'get a pre-race rating; never update anyone; their uncertainty keeps growing from their last measured run'},
                  {'case': 'first run in the data (Qld)', 'count': int((P.sd >= 0.999 * p['sig0_kg']).sum()), 'handling': f"start at field average of known horses minus {p['debut_offset_kg']} kg, sd {p['sig0_kg']} kg; flagged"},
                  {'case': 'runs after 180+ days off (Qld)', 'count': int((q.days_since >= 180).sum()), 'handling': 'uncertainty grows by q per day off (capped at the debut sd), so the next run moves the rating more'}])
E.to_csv('out/out_s12v_edge_cases.csv', index=False); print(E.to_string(index=False))
# identical-race comparison
X = pd.read_parquet('features.parquet').merge(P[['race_id', 'horse_id', 'mu', 'sd']].rename(columns={'mu': 'dyn_mu', 'sd': 'dyn_sd'}), on=['race_id', 'horse_id'], how='left')
UQ = U.assign(mu=pd.Series(PN.mu.values, index=PN.idx.values).reindex(np.arange(len(U))).values)
X = X.merge(UQ[UQ.state == 'QLD'][['q_race_id', 'q_horse_id', 'mu']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id', 'mu': 'dyn_nat'}).dropna(subset=['race_id']), on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
X['dyn_new'] = (X.dyn_sd >= 0.999 * p['sig0_kg']).astype(float)
BENCH = list(man['coefficients_per_dev_sd']['combined_v1'])
x = prep(eligible(X), sorted(set(BENCH + ['dyn_mu', 'dyn_nat', 'dyn_new'])))
fp_all = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'finish_pos', 'field']]
x = x.merge(fp_all.rename(columns={'field': 'field_r'}), on=['race_id', 'horse_id'], how='left')
specs = {'combined_v1 (frozen benchmark)': BENCH, 'Qld dynamic rating alone': ['dyn_mu', 'dyn_new'], 'national dynamic rating alone': ['dyn_nat', 'missform'],
         'combined_v1 + Qld dynamic rating': BENCH + ['dyn_mu'], 'combined_v1 + national dynamic rating': BENCH + ['dyn_nat']}
res, out = {}, []
for k, cols in specs.items():
    b = fit(x, cols); res[k] = score(x, cols, b)
    e = x[x.period == 'evaluation'].copy(); e['lp'] = e[[c + '_z' for c in cols]].values @ b
    e['mrank'] = e.groupby('race_id').lp.rank(ascending=False, method='first')
    w = e[e.win == 1]; fin = e[e.finish_pos.notna() & (e.finish_pos <= e.field_r)]
    sp = fin.groupby('race_id').apply(lambda g: spearmanr(-g.lp, g.finish_pos).correlation if len(g) > 2 else np.nan, include_groups=False)
    out.append({'model': k, 'races': len(res[k]), 'fit_%': round(fit_pct(res[k]), 2), 'top_pick_%': round(100 * res[k].hit.mean(), 1), 'winner_mean_rank': round(w.mrank.mean(), 2),
                'winner_in_top3_%': round(100 * (w.mrank <= 3).mean(), 1), 'spearman_model_vs_finish': round(sp.mean(), 3)})
C = pd.DataFrame(out); C.to_csv('out/out_s12v_identical_races.csv', index=False); print(C.to_string(index=False))
a, b_ = res['combined_v1 (frozen benchmark)'], res['combined_v1 + national dynamic rating']
for by in ['meeting', 'month']:
    m_, lo, hi, _ = boot_diff(a, b_, by=by); h = boot_diff(a, b_, 'hit', by=by)
    print(by, 'fit gain', round(m_, 4), (round(lo, 4), round(hi, 4)), '| top pick', round(100 * h[0], 1), (round(100 * h[1], 1), round(100 * h[2], 1)))
