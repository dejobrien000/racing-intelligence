"""Research E: does the inside-barrier edge depend on the rail, field size, distance, the horse's usual running style,
and how much early speed is in the race? Pre-race only: running style and pace pressure come from each horse's
PREVIOUS runs (average settling position over its last 3 Queensland starts), never from the race itself.
Method: conditional logit within race (win ~ relative barrier), one fit per group; odds ratio = outside vs inside draw.
Many groups are tested, so p-values are adjusted (Benjamini-Hochberg q-values). Queensland, Oct 2022 - Nov 2026, exploratory.
Usage: python3 inv10_barriers_context.py  -> out/out_inv10_barrier_context.csv"""
import re, numpy as np, pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit
from statsmodels.stats.multitest import multipletests

d = pd.read_parquet('runs_rated.parquet').drop_duplicates(['race_id', 'horse_id'])
d = d[(d.field >= 6) & d.rel_barrier.notna() & ~d.is_poly.fillna(False)].copy()
def rail_m(s):
    s = s if isinstance(s, str) else ''
    if s.lower().startswith('true'): return 0.0
    m = re.match(r'\+?\s*(\d+(?:\.\d+)?)m', s); return float(m.group(1)) if m else np.nan
d['rail_m'] = d['rail'].map(rail_m)
d['rail_band'] = pd.cut(d.rail_m, [-0.1, 0.1, 3, 6, 99], labels=['true', '+0.5-3m', '+3.5-6m', '+6.5m or more'])
d['field_band'] = pd.cut(d.field, [5, 9, 12, 30], labels=['6-9 runners', '10-12', '13+'])
d['dist_band'] = pd.cut(d.distance_m, [0, 1150, 1450, 1750, 9999], labels=['<=1150', '1200-1450', '1500-1750', '1800+'])
d = d.sort_values(['horse_id', 'meeting_date', 'race_no'])
d['style_prev'] = d.groupby('horse_id')['settle_rel'].transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
d['style'] = pd.cut(d.style_prev, [-0.01, 0.2, 0.5, 0.8, 1.01], labels=['usually leads/on pace', 'handy', 'midfield', 'back'])
d['leader_type'] = (d.style_prev <= 0.15).astype(int)
d['pace_pressure'] = pd.cut(d.groupby('race_id')['leader_type'].transform('sum'), [-1, 0, 1, 2, 99], labels=['no habitual leader', '1 leader', '2 leaders', '3+ leaders'])

rows = []
def fit(h, factor, level):
    h = h.dropna(subset=['rel_barrier'])
    if h.race_id.nunique() < 80: return
    m = ConditionalLogit(h['win'].values, h[['rel_barrier']].values, groups=h['race_id'].values).fit(disp=0)
    b, se = m.params[0], m.bse[0]
    rows.append({'factor': factor, 'group': level, 'races': h.race_id.nunique(), 'runs': len(h), 'OR_outside_vs_inside': round(np.exp(b), 2),
                 'lo95': round(np.exp(b - 1.96 * se), 2), 'hi95': round(np.exp(b + 1.96 * se), 2), 'p': m.pvalues[0]})
fit(d, 'all', 'all Queensland turf')
for f in ['rail_band', 'field_band', 'dist_band', 'pace_pressure']:          # race-level factors: fit within each group of races
    for lev, h in d.groupby(f, observed=True): fit(h, f, str(lev))
# runner-level factor (usual running style): full fields, barrier x style interaction, so every horse is compared with its whole race
def fit_inter(h, col, factor):
    h = h.dropna(subset=[col]).copy(); h = h[h.groupby('race_id')['race_id'].transform('size') >= 4]
    levs = [str(x) for x in h[col].cat.categories if (h[col] == x).any()]
    X = pd.DataFrame({'rel_barrier': h.rel_barrier.values})
    for lv in levs[1:]: X['x_' + lv] = (h[col].astype(str).values == lv) * h.rel_barrier.values; X['m_' + lv] = (h[col].astype(str).values == lv) * 1.0
    m = ConditionalLogit(h['win'].values, X.values, groups=h['race_id'].values).fit(disp=0)
    P = pd.Series(m.params, index=X.columns); V = pd.DataFrame(m.cov_params(), index=X.columns, columns=X.columns)
    for lv in levs:
        names = ['rel_barrier'] + ([] if lv == levs[0] else ['x_' + lv]); b = P[names].sum(); se = float(np.sqrt(V.loc[names, names].values.sum()))
        from scipy.stats import norm
        rows.append({'factor': factor, 'group': lv, 'races': h[h[col].astype(str) == lv].race_id.nunique(), 'runs': int((h[col].astype(str) == lv).sum()),
                     'OR_outside_vs_inside': round(np.exp(b), 2), 'lo95': round(np.exp(b - 1.96 * se), 2), 'hi95': round(np.exp(b + 1.96 * se), 2), 'p': 2 * (1 - norm.cdf(abs(b / se)))})
fit_inter(d, 'style', 'usual running style (last 3 starts)')
for p, h in d.groupby('pace_pressure', observed=True): fit_inter(h.copy(), 'style', f'running style, races with {p}')
t = pd.DataFrame(rows)
t['q_BH'] = multipletests(t.p, method='fdr_bh')[1]
t['p'] = t.p.round(4); t['q_BH'] = t.q_BH.round(4)
t.to_csv('out/out_inv10_barrier_context.csv', index=False); print(t.to_string(index=False))
print('rail missing:', round(d.rail_m.isna().mean() * 100, 1), '%; style known for', round(d.style_prev.notna().mean() * 100, 1), '% of runs')
