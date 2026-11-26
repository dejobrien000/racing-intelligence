"""Batch 14 follow-up s5: rider late-speed retention ('hold') by distance band, Queensland vs South Australia, same controls as
b14f_riders.py (position, deficit at 800, tempo, distance, course, opposition, prep stage, field; within-horse; trainer average removed).
Split-half persistence among riders with 40+ tracked rides in the band."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
P = pd.read_parquet('/home/claude/b14/profiles.parquet'); P['hold'] = P.v200r - P.v400r
P['jk'] = P.jkey.fillna(P.jockey.astype(str)); P['tk'] = P.tkey.fillna(P.trainer.astype(str)); P = P.dropna(subset=['hold']).sort_values('meeting_date').reset_index(drop=True)
out = {}
for st in ['QLD', 'SA']:
    d = P[P.state == st].copy()
    y, X = patsy.dmatrices('hold ~ early_pos + I(early_pos**2) + def800c + tz + tz_miss + C(dband) + C(track) + fmean_c + C(prep) + field', d, return_type='dataframe', NA_action='drop')
    d = d.loc[y.index]; d['r'] = sm.OLS(y, X).fit().resid.values; d['wh'] = d.r - d.groupby('horse').r.transform('mean'); d['wht'] = d.wh - d.groupby('tk').wh.transform('mean')
    for b, g in d.groupby('dband'):
        g = g.groupby('jk').filter(lambda z: len(z) >= 40).copy(); g['half'] = g.groupby('jk').cumcount() % 2
        p = g.groupby(['jk', 'half']).wht.mean().unstack().dropna()
        r = p[0].corr(p[1]) if len(p) > 5 else np.nan
        bs = [p.sample(len(p), replace=True, random_state=i) for i in range(500)]; rb = np.nanpercentile([q[0].corr(q[1]) for q in bs], [2.5, 97.5]) if len(p) > 5 else [np.nan, np.nan]
        out[f'{st} {b}'] = {'split-half r': round(r, 3), '95%': [round(rb[0], 2), round(rb[1], 2)], 'riders': len(p), 'rides': len(g)}
print(json.dumps(out)); json.dump(out, open('batch14/followup/out_riders_band.json', 'w'), indent=1)
