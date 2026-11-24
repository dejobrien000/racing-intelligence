"""Batch 4, Study 12 national step. The dynamic opposition rating run over EVERY state's results in date order (Qld
tracked + Breednet NSW/Vic/ACT), so interstate runs and opposition count. Then: (a) common-feature model F+A+R vs
F+A+R + dynamic rating by state group and tier (as Study 8); (b) Qld: combined_v1 + national dynamic rating vs
combined_v1 + Qld-only dynamic rating. Usage: python3 inv25_national_dynamic.py [split]  (needs national_runs.parquet)"""
import sys, numpy as np, pandas as pd
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
import dyn_rating as DR
SPLIT = sys.argv[1] if len(sys.argv) > 1 else '2025-01-01'
U = pd.read_parquet('national_runs.parquet')
d = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                  'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
P = DR.prepare(d).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
dev = P.date < SPLIT; best = None
for s in [4.0, 4.5, 5.0, 5.5]:
    for qq in [0.025, 0.05, 0.1]:
        _, _, ll = DR.run(P[dev], s, qq, 5.0, 2.0)
        if best is None or ll > best[0]: best = (ll, s, qq)
print('national params (development):', best)
mu, sd, _ = DR.run(P, best[1], best[2], 5.0, 2.0)
U['dyn_mu'] = pd.Series(mu, index=P.idx.values).reindex(np.arange(len(U))).values
U['dyn_sd'] = pd.Series(sd, index=P.idx.values).reindex(np.arange(len(U))).values
F = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform']; A = ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']; R = ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays']
def elig(x):
    x = x[x.field >= 6].copy(); x['n_win'] = x.groupby('race_id').win.transform('sum'); return x[x.n_win == 1]
out = []
for label, sel in [('NSW/ACT/Vic metro', (U.state != 'QLD') & (U.tier == 'metro')), ('NSW/ACT/Vic provincial', (U.state != 'QLD') & (U.tier == 'provincial')),
                   ('NSW/ACT/Vic country', (U.state != 'QLD') & (U.tier == 'country')), ('Qld all tracked (common features)', U.state == 'QLD')]:
    x = elig(U[sel])
    if min(x[x.period == p].race_id.nunique() for p in ['development', 'evaluation']) < 50: out.append({'sample': label, 'note': 'too few races'}); continue
    x = prep(x, F + A + R + ['dyn_mu'])
    res = {k: score(x, v, fit(x, v)) for k, v in {'F+A+R': F + A + R, 'F+A+R+dyn': F + A + R + ['dyn_mu']}.items()}
    m, lo, hi, p = boot_diff(res['F+A+R'], res['F+A+R+dyn']); _, mlo, mhi, _ = boot_diff(res['F+A+R'], res['F+A+R+dyn'], by='month'); h = boot_diff(res['F+A+R'], res['F+A+R+dyn'], 'hit')
    out.append({'sample': label, 'races_scored': len(res['F+A+R']), 'fit_FAR_%': round(fit_pct(res['F+A+R']), 2), 'fit_FAR+dyn_%': round(fit_pct(res['F+A+R+dyn']), 2),
                'top_FAR_%': round(100 * res['F+A+R'].hit.mean(), 1), 'top_FAR+dyn_%': round(100 * res['F+A+R+dyn'].hit.mean(), 1),
                'gain': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'lo95_months': round(mlo, 4), 'hi95_months': round(mhi, 4), 'top_pick_diff': round(100 * h[0], 1), 'tp_lo': round(100 * h[1], 1), 'tp_hi': round(100 * h[2], 1)})
t = pd.DataFrame(out); t.to_csv('out/out_s12n_replication.csv', index=False); print(t.T.to_string())
# (b) Qld: national vs Qld-only dynamic rating inside combined_v1
qn = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_mu']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id', 'dyn_mu': 'dyn_nat'}).dropna(subset=['race_id'])
src = open('inv23_dynamic_rating.py').read(); src = src.replace(src[src.index("best = None; grid = []"):src.index("print('chosen on development")], "best = (np.nan, 4.0, 0.1, 5.0)\n")
src = src.split("res = {k: score")[0].replace("x = prep(eligible(X)", "X = X.merge(qn, on=['race_id', 'horse_id'], how='left')\nx = prep(eligible(X)").replace("'rec_rating_pa1', 'misspa'])))", "'rec_rating_pa1', 'misspa', 'dyn_nat'])))")
exec(src)
r1 = score(x, BENCH + ['dyn_mu'], fit(x, BENCH + ['dyn_mu'])); r2 = score(x, BENCH + ['dyn_nat'], fit(x, BENCH + ['dyn_nat'])); r0 = score(x, BENCH, fit(x, BENCH))
m, lo, hi, p = boot_diff(r1, r2); m0, lo0, hi0, _ = boot_diff(r0, r2)
print('Qld national dyn coverage of eligible runners:', round(x.dyn_nat.notna().mean(), 3))
pd.DataFrame([{'comparison': 'combined_v1 + national dyn vs combined_v1 + Qld-only dyn', 'gain': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'top_diff': round(100 * (r2.hit.mean() - r1.hit.mean()), 1)},
              {'comparison': 'combined_v1 + national dyn vs combined_v1', 'gain': round(m0, 4), 'lo95': round(lo0, 4), 'hi95': round(hi0, 4), 'top_diff': round(100 * (r2.hit.mean() - r0.hit.mean()), 1),
               'fit_%': round(fit_pct(r2), 2), 'top_%': round(100 * r2.hit.mean(), 1)}]).to_csv('out/out_s12n_qld.csv', index=False)
print(pd.read_csv('out/out_s12n_qld.csv').to_string(index=False))
