import pandas as pd, numpy as np
import statsmodels.formula.api as smf
from statsmodels.discrete.conditional_models import ConditionalLogit
df = pd.read_parquet('runs.parquet')
for c in ['margin_l','distance_m','next_distance_m','next_field','next_win','l600_rank','rel_barrier']:
    df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
d = df[(df.field >= 6) & (df.next_field >= 6) & df.finished & df.l600_rank.notna() & (df.win == 0) & df.gap_to_next.between(7, 60)].copy()
d['top_l600'] = (d.l600_rank <= 1).astype(int)
d['step_up'] = (d.next_distance_m >= d.distance_m + 200).astype(int)
d['step_down'] = (d.next_distance_m <= d.distance_m - 200).astype(int)
d['next_win'] = d['next_win'].astype(int)
res = []
for split, g in d.groupby('split'):
    m = smf.logit('next_win ~ top_l600 * step_up + top_l600 * step_down + np.log(margin_l + 0.5) + np.log(next_field)', data=g).fit(disp=0)
    t = m.summary2().tables[1][['Coef.','Std.Err.','P>|z|']].round(4); t['split'] = split; t['n'] = len(g); res.append(t)
r = pd.concat(res).reset_index().rename(columns={'index':'term'}); print(r.to_string(index=False)); r.to_csv('out/out_inv3b_l600_x_distance.csv', index=False)
# Doomben and Eagle Farm by exact distance (barrier effect, all years, labelled)
b = df[(df.field >= 6) & df.rel_barrier.notna() & df.track.isin(['Doomben','Eagle_Farm','Sunshine_Coast'])]
rows = []
for (t, dist), g in b.groupby(['track','distance_m']):
    if g.race_id.nunique() < 60: continue
    for split, h in [('explore', g[g.split == 'explore_2022_2025']), ('holdout', g[g.split == 'holdout_2026'])]:
        if h.race_id.nunique() < 15: continue
        m = ConditionalLogit(h['win'].values, h[['rel_barrier']].values, groups=h['race_id'].values).fit(disp=0)
        rows.append({'track': t, 'distance': int(dist), 'split': split, 'races': h.race_id.nunique(), 'OR_outside_vs_inside': round(np.exp(m.params[0]), 2), 'lo95': round(np.exp(m.params[0]-1.96*m.bse[0]), 2), 'hi95': round(np.exp(m.params[0]+1.96*m.bse[0]), 2), 'p': round(m.pvalues[0], 4)})
x = pd.DataFrame(rows); print(x.to_string(index=False)); x.to_csv('out/out_inv1b_metro_exact_distance.csv', index=False)
