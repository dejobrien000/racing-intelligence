"""Study 6 secondary: does the pace-corrected figure (PA1, recency-weighted) beat simple form on its own, overall and 1400m+?"""
import numpy as np, pandas as pd
from clogit_tools import eligible, prep, fit, score, fit_pct, boot_diff
X = pd.read_parquet('features.parquet').merge(pd.read_parquet('pace_figures.parquet')[['race_id', 'horse_id', 'rec_rating_pa1', 'rec_rating']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna(); X['missform'] = (~has).astype(float); X['misspa'] = (has & X.rec_rating_pa1.isna()).astype(float)
x = prep(eligible(X), ['f_avgfp3', 'rec_rating_pa1', 'missform', 'misspa'])
rf = score(x, ['f_avgfp3', 'missform'], fit(x, ['f_avgfp3', 'missform'])); rp = score(x, ['rec_rating_pa1', 'missform', 'misspa'], fit(x, ['rec_rating_pa1', 'missform', 'misspa']))
lng = x[x.period == 'evaluation'].groupby('race_id').distance_m.first() >= 1400
rows = []
for nm, idx in [('all', rf.index), ('1400m+', lng[lng].index), ('under 1400m', lng[~lng].index)]:
    a, b = rf.loc[idx], rp.loc[idx]; m, lo, hi, p = boot_diff(a, b); h = boot_diff(a, b, 'hit'); _, mlo, mhi, _ = boot_diff(a, b, by='month')
    rows.append({'races': nm, 'n': len(idx), 'form_fit_%': round(fit_pct(a), 2), 'PA1_fit_%': round(fit_pct(b), 2), 'form_top_%': round(100 * a.hit.mean(), 1), 'PA1_top_%': round(100 * b.hit.mean(), 1),
                 'PA1_minus_form_fit': round(m, 4), 'lo95': round(lo, 4), 'hi95': round(hi, 4), 'lo95_months': round(mlo, 4), 'hi95_months': round(mhi, 4), 'top_diff_pts': round(100 * h[0], 1), 'tp_lo95': round(100 * h[1], 1), 'tp_hi95': round(100 * h[2], 1)})
t = pd.DataFrame(rows); t.to_csv('out/out_s6_pa1_vs_form.csv', index=False); print(t.to_string(index=False))
