"""Independent check of R1 (inside draws win more) and R16 (a wide draw hurts horses that settle back more than leaders)
on NSW and other interstate races, using Racing NSW career form lines (not used in any earlier test).
Each line is one horse's run; only horses still racing in NSW from July 2026 are present (survivor bias), and a race
appears only through those horses, so this uses A/E against field size rather than a within-race model.
Relative draw = (barrier - 1) / (field - 1), clipped to 0-1 (raw barriers, so scratchings blur it slightly).
Running style = the horse's average position at 800m relative to field size over its previous 3 runs (pre-race).
Excludes trials and all Queensland tracks (so the test is independent of the Queensland findings).
Usage: python3 inv12_nsw_barriers.py <history.duckdb> -> out/out_inv12_nsw_barriers.csv"""
import sys, duckdb, numpy as np, pandas as pd
from scipy.stats import chi2
con = duckdb.connect(sys.argv[1], read_only=True)
d = con.execute("select * from nsw_form_line where not trial and field >= 6 and barrier between 1 and 24 and finish_pos is not null").fetchdf()
qld = {'DOOM', 'E FM', 'GCST', 'SCST', 'IPSW', 'TOOW', 'SCPT', 'CANP', 'TWNS', 'ROCK', 'MACK', 'KILC', 'WARW', 'DALB', 'BDST', 'DEAG', 'BEAU'}
d = d[~d.track_code.isin(qld - {'BEAU'})]          # BEAU = Beaumont Newcastle (NSW)
d = d[pd.to_datetime(d.run_date) >= pd.Timestamp('2022-10-01')]
d['rel'] = ((d.barrier - 1) / (d.field - 1)).clip(0, 1)
d['third'] = pd.cut(d.rel, [-0.01, 1 / 3, 2 / 3, 1.01], labels=['inside third', 'middle third', 'outside third'])
d['win'] = (d.finish_pos == 1).astype(int); d['exp'] = 1 / d.field
d = d.sort_values(['name_key', 'dob', 'run_date'])
d['set800'] = (d.pos800 - 1) / (d.field - 1)
d['style_prev'] = d.groupby(['name_key', 'dob'])['set800'].transform(lambda s: s.shift().rolling(3, min_periods=2).mean())
d['style'] = pd.cut(d.style_prev, [-0.01, 0.2, 0.5, 0.8, 1.01], labels=['usually leads/on pace', 'handy', 'midfield', 'back'])
def ae(h):
    w, e = h.win.sum(), h.exp.sum(); return round(w / e, 2), round(chi2.ppf(0.025, 2 * w) / 2 / e, 2), round(chi2.ppf(0.975, 2 * w + 2) / 2 / e, 2)
rows = []
for third, h in d.groupby('third', observed=True):
    rows.append({'split': 'all', 'group': '-', 'draw': third, 'runs': len(h), 'horses': h.name_key.nunique(), 'win_%': round(100 * h.win.mean(), 1), **dict(zip(['A/E', 'lo95', 'hi95'], ae(h)))})
for (st, third), h in d.groupby(['style', 'third'], observed=True):
    rows.append({'split': 'usual running style', 'group': st, 'draw': third, 'runs': len(h), 'horses': h.name_key.nunique(), 'win_%': round(100 * h.win.mean(), 1), **dict(zip(['A/E', 'lo95', 'hi95'], ae(h)))})
t = pd.DataFrame(rows)
# ratio outside/inside A/E per group, the analogue of the Queensland odds ratio
r = t.pivot_table(index=['split', 'group'], columns='draw', values='A/E', observed=True)
r['outside_vs_inside'] = (r['outside third'] / r['inside third']).round(2)
t.to_csv('out/out_inv12_nsw_barriers.csv', index=False); print(t.to_string(index=False)); print(r.to_string())
print('runs', len(d), 'horses', d.name_key.nunique(), 'date range', d.run_date.min(), d.run_date.max())
