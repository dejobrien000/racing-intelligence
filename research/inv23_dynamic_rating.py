"""Batch 4, Study 12 prototype. Tune the dynamic opposition rating on development races (one-step-ahead predictive
likelihood, Queensland), then compare its pre-race rating with the v0 and PA1 figures, alone and inside combined_v1.
Chronological out-of-sample (Qld 2025-26, not untouched). Outputs out/out_s12_*.csv"""
import numpy as np, pandas as pd
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
import dyn_rating as DR
q = pd.read_parquet('runs.parquet'); q = q[q.scratched != True]
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0
P = DR.prepare(d)
dev = P.date < '2025-01-01'
best = None; grid = []
for s in [2.5, 3.0, 3.5, 4.0]:
    for qq in [0.05, 0.1, 0.2, 0.4]:
        for sig0 in [3.0, 4.0, 5.0]:
            _, _, ll = DR.run(P[dev], s, qq, sig0, 2.0); grid.append((s, qq, sig0, ll))
            if best is None or ll > best[0]: best = (ll, s, qq, sig0)
pd.DataFrame(grid, columns=['s', 'q', 'sig0', 'dev_pred_loglik']).to_csv('out/out_s12_grid.csv', index=False)
print('chosen on development: s', best[1], 'q', best[2], 'sig0', best[3], '| mean predictive loglik', round(best[0], 4))
mu, sd, _ = DR.run(P, best[1], best[2], best[3], 2.0)
P['dyn_mu'] = mu; P['dyn_sd'] = sd
pd.DataFrame([{'s': best[1], 'q': best[2], 'sig0': best[3], 'dev_pred_loglik': best[0]}]).to_csv('out/out_s12_params.csv', index=False)
X = pd.read_parquet('features.parquet').merge(P[['race_id', 'horse_id', 'dyn_mu', 'dyn_sd']], on=['race_id', 'horse_id'], how='left')
X = X.merge(pd.read_parquet('pace_figures.parquet')[['race_id', 'horse_id', 'rec_rating', 'rec_rating_pa1']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna(),
             'misspa': has & X.rec_rating_pa1.isna()}.items(): X[k] = v.astype(float)
X['dyn_new'] = (X.dyn_sd >= 0.999 * best[3]).astype(float)   # no earlier rated run: field-based prior; flagged
G = {'F': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'A': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'],
     'S': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'P': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
     'T': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'R': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
BENCH = [c for v in G.values() for c in v]
x = prep(eligible(X), sorted(set(BENCH + ['dyn_mu', 'dyn_sd', 'dyn_new', 'rec_rating', 'rec_rating_pa1', 'misspa'])))
specs = {'simple form (avg finish last 3)': ['f_avgfp3', 'missform'], 'v0 figure, recency-weighted': ['rec_rating', 'missform', 'missfig'],
         'PA1 pace-corrected figure, recency-weighted': ['rec_rating_pa1', 'missform', 'misspa'], 'dynamic opposition rating': ['dyn_mu', 'dyn_new'],
         'dynamic rating + PA1 figure': ['dyn_mu', 'dyn_new', 'rec_rating_pa1', 'misspa'], 'combined_v1': BENCH, 'combined_v1 + dynamic rating': BENCH + ['dyn_mu']}
res = {k: score(x, v, fit(x, v)) for k, v in specs.items()}
rows = [{'model': k, 'races': len(r), 'fit_%': round(fit_pct(r), 2), 'top_pick_%': round(100 * r.hit.mean(), 1)} for k, r in res.items()]
t = pd.DataFrame(rows); t.to_csv('out/out_s12_models.csv', index=False); print(t.to_string(index=False))
cmp = []
for a, b in [('v0 figure, recency-weighted', 'dynamic opposition rating'), ('simple form (avg finish last 3)', 'dynamic opposition rating'),
             ('PA1 pace-corrected figure, recency-weighted', 'dynamic rating + PA1 figure'), ('combined_v1', 'combined_v1 + dynamic rating')]:
    m, lo, hi, p = boot_diff(res[a], res[b]); _, mlo, mhi, _ = boot_diff(res[a], res[b], by='month'); h = boot_diff(res[a], res[b], 'hit')
    cmp.append({'comparison': f'{b} vs {a}', 'fit_gain_per_race': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'lo95_months': round(mlo, 4), 'hi95_months': round(mhi, 4),
                'top_pick_diff_pts': round(100 * h[0], 1), 'tp_lo95': round(100 * h[1], 1), 'tp_hi95': round(100 * h[2], 1)})
c = pd.DataFrame(cmp); c.to_csv('out/out_s12_comparisons.csv', index=False); print(c.to_string(index=False))
