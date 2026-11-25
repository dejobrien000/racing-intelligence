"""Six-state diagnostics of Engine v2 (NSW/Vic family coefficients, never refit) on 2025-26 races, and by tier and venue.
Is SA's lower top-pick rate the engine being worse there, or SA races simply being harder (bigger, more even fields)?"""
import numpy as np, pandas as pd, sys
sys.path.insert(0, 'b10/scripts'); import lib10 as L
b = L.base('nat'); b = b[b.meeting_date.dt.year >= 2025].copy()
mx = b.groupby('race_id').v2.transform('max'); b['p'] = np.exp(b.v2 - mx); b['p'] /= b.groupby('race_id').p.transform('sum')
b['rk'] = b.groupby('race_id').v2.rank(ascending=False, method='first')
top = b[b.rk == 1]
r = b.groupby('race_id').agg(state=('state', 'first'), venue=('venue', 'first'), tier=('tier', 'first'), field=('field', 'first'), meeting_id=('meeting_id', 'first'))
r['lp'] = np.log(b[b.win == 1].set_index('race_id').p); r['null'] = -np.log(r.field)
r['hit'] = top.set_index('race_id').win; r['p_top'] = top.set_index('race_id').p
def summ(g):
    return pd.Series({'races': len(g), 'avg_field': g.field.mean(), 'top_pick_%': 100 * g.hit.mean(), 'expected_top_pick_%': 100 * g.p_top.mean(),
                      'fit_%': 100 * (1 - g.lp.sum() / g.null.sum()), 'logloss_gain_vs_random': (g.lp - g.null).mean()})
out = []
for k in ['state', 'tier']:
    t = r.groupby(k).apply(summ).round(2); t.insert(0, 'by', k); out.append(t.reset_index().rename(columns={k: 'group'}))
t = r[r.state.isin(['SA', 'WA', 'TAS'])].groupby(['state', 'venue']).apply(summ).round(2).reset_index(); t = t[t.races >= 40]; t['group'] = t.state + ' ' + t.venue; t['by'] = 'west venue'
out.append(t.drop(columns=['state', 'venue']))
res = pd.concat(out, ignore_index=True); res.to_csv('b10/out/s1_six_state.csv', index=False); print(res.to_string(index=False))
# same-field-size comparison: top pick rate by field-size band and region
r['band'] = pd.cut(r.field, [0, 8, 10, 12, 30], labels=['<=8', '9-10', '11-12', '13+']); r['region'] = np.where(r.state.isin(['SA', 'WA', 'TAS']), r.state, 'NSW/VIC/ACT')
fb = r.groupby(['region', 'band'], observed=True).apply(summ).round(2)[['races', 'top_pick_%', 'expected_top_pick_%', 'fit_%']]; print(fb.to_string()); fb.to_csv('b10/out/s1_field_bands.csv')
