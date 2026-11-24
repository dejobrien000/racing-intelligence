import pandas as pd, numpy as np, json
from statsmodels.discrete.conditional_models import ConditionalLogit
from lib import ae_table, dist_band
pd.set_option('display.width', 220); pd.set_option('display.max_rows', 200)
df = pd.read_parquet('runs.parquet')
df = df[(df['field'] >= 6) & df['barrier'].notna() & ~df['track'].isin(['TAB_Park_Gold_Coast'])].copy()
df['dband'] = dist_band(df['distance_m'])
df['bgrp'] = pd.cut(df['eff_barrier'], [0, 2, 4, 6, 8, 10, 30], labels=['1-2','3-4','5-6','7-8','9-10','11+'])
df['third'] = pd.cut(df['rel_barrier'], [-0.01, 1/3, 2/3, 1.01], labels=['inside third','middle third','outside third'])
ex, ho = df[df.split == 'explore_2022_2025'], df[df.split == 'holdout_2026']
out = {}
out['overall_by_barrier'] = ae_table(ex, 'bgrp')
out['overall_by_third'] = ae_table(ex, 'third')
# conditional logit: within-race effect of relative barrier (0 = inside, 1 = outside)
def clogit(d):
    d = d.dropna(subset=['rel_barrier'])
    m = ConditionalLogit(d['win'].values, d[['rel_barrier']].values, groups=d['race_id'].values).fit(disp=0)
    b, se = m.params[0], m.bse[0]
    return pd.Series({'runs': len(d), 'races': d.race_id.nunique(), 'coef': round(b, 3), 'se': round(se, 3),
                      'OR_out_vs_in': round(np.exp(b), 2), 'OR_lo95': round(np.exp(b-1.96*se), 2), 'OR_hi95': round(np.exp(b+1.96*se), 2), 'p': round(m.pvalues[0], 4)})
out['clogit_all_explore'] = clogit(ex).to_frame().T
out['clogit_all_holdout'] = clogit(ho).to_frame().T
rows = []
for (t, b), g in ex.groupby(['track', 'dband'], observed=True):
    if g.race_id.nunique() >= 60:
        r = clogit(g); r['track'] = t; r['dband'] = b; rows.append(r)
tb = pd.DataFrame(rows).sort_values('coef')
out['clogit_track_dist_explore'] = tb
# holdout check for the strongest and weakest cells
chk = []
for _, r in pd.concat([tb.head(4), tb.tail(4)]).iterrows():
    g = ho[(ho.track == r.track) & (ho.dband == r.dband)]
    if g.race_id.nunique() >= 20:
        h = clogit(g); h['track'] = r.track; h['dband'] = r.dband; h['explore_OR'] = r.OR_out_vs_in; chk.append(h)
out['holdout_check_extremes'] = pd.DataFrame(chk)
# Damo's example: Doomben 1200, controlling field size and track condition
d12 = df[(df.track == 'Doomben') & (df.distance_m == 1200)].copy()
d12['field_grp'] = pd.cut(d12['field'], [5, 9, 12, 30], labels=['6-9','10-12','13+'])
d12['going'] = np.where(d12['cond_group'].isin(['Soft', 'Heavy']), 'Soft/Heavy', 'Good/Firm')
out['doomben1200_third_by_field'] = ae_table(d12, ['field_grp', 'third'])
out['doomben1200_third_by_going'] = ae_table(d12, ['going', 'third'])
m = ConditionalLogit(d12['win'].values, np.column_stack([d12['rel_barrier'], d12['rel_barrier'] * (d12['going'] == 'Soft/Heavy'), d12['rel_barrier'] * (d12['field'] >= 13)]), groups=d12['race_id'].values).fit(disp=0)
out['doomben1200_clogit_interactions'] = pd.DataFrame({'term': ['rel_barrier (Good, field<13)', 'x Soft/Heavy', 'x field 13+'], 'coef': m.params.round(3), 'se': m.bse.round(3), 'p': m.pvalues.round(4)})
out['doomben1200_n'] = pd.DataFrame([{'runs': len(d12), 'races': d12.race_id.nunique(), 'from': str(d12.meeting_date.min())[:10], 'to': str(d12.meeting_date.max())[:10]}])
for k, v in out.items():
    print('\n==', k); print(v.to_string(index=False))
    v.to_csv(f'out_inv1_{k}.csv', index=False)
