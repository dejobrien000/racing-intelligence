"""R9 deep dive: beaten runners who ran the fastest last 600 m in their race, next start up 200 m or more.
Question: do they win more often next start than expected, beyond what the fast finish or the distance rise alone explain,
and does it depend on class change, the strength of the race they came from, early pace, distance, margin, or venue?
Data: Queensland TAB meetings with RQ tracking, Oct 2022 - Nov 2026 (all of it; the 2026 holdout is already spent, so
everything here is EXPLORATORY and needs a fresh period or another state to validate).
Standard errors are clustered by horse (the same horse appears many times). Sensitivity: clustered by next race.
Usage: python3 inv9_r9_deep.py   (reads runs_rated.parquet, writes out/out_inv9_*.csv)
"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import chi2

d = pd.read_parquet('runs_rated.parquet').drop_duplicates(['race_id', 'horse_id'])
for c in ['margin_l', 'distance_m', 'next_distance_m', 'next_field', 'next_win', 'l600_rank', 'settle_rel', 'gap_to_next', 'next_days_since']:
    d[c] = pd.to_numeric(d[c], errors='coerce').astype(float)
level = d.groupby('class_bucket')['rating'].median()               # class level in rating units (kg)
d['class_level'] = d['class_bucket'].map(level); d['next_class_level'] = d['next_class_bucket'].map(level)
d['class_delta'] = d['next_class_level'] - d['class_level']
metro = {'Eagle_Farm', 'Doomben'}; prov = {'Sunshine_Coast', 'Sunshine_Coast_Poly_Track', 'TAB_Park_Gold_Coast', 'Ipswich', 'Toowoomba'}
d['venue_tier'] = np.where(d.track.isin(metro), 'metro', np.where(d.track.isin(prov), 'provincial', 'country'))

b = d[(d.field >= 6) & (d.next_field >= 6) & d.finished & d.l600_rank.notna() & (d.win == 0) & d.gap_to_next.between(7, 60)
      & (d.next_days_since == d.gap_to_next) & d.next_race_id.notna()].copy()        # true next start, no interstate run in between
b['top_l600'] = (b.l600_rank == 1).astype(int)
step = b.next_distance_m - b.distance_m
b['step'] = pd.cut(step, [-1e9, -200, 199, 399, 1e9], right=False, labels=['down 200+', 'same (+/-199)', 'up 200-399', 'up 400+'])
b['step_up'] = (step >= 200).astype(int); b['step_down'] = (step <= -200).astype(int)
b['next_win'] = b['next_win'].astype(int)
b['class_move'] = pd.cut(b.class_delta, [-99, -1.5, 1.5, 99], labels=['drops in class', 'same class', 'rises in class'])
b['margin_band'] = pd.cut(b.margin_l, [0, 1, 2, 4, 8, 999], labels=['<=1L', '1-2L', '2-4L', '4-8L', '8L+'])
b['dist_band'] = pd.cut(b.distance_m, [0, 1150, 1450, 1750, 9999], labels=['<=1150', '1200-1450', '1500-1750', '1800+'])
b['fs_z'] = (b.field_strength - b.field_strength.mean()) / b.field_strength.std()
b['strength_band'] = pd.qcut(b.field_strength, 3, labels=['weaker races', 'middle', 'stronger races'])
b['fsp_rel'] = b.fsp - b.groupby('race_id')['fsp'].transform('median')
b['next_fig_vs_avg3'] = b.next_rating - b.groupby('horse_id')['rating'].transform(lambda s: s.rolling(3, min_periods=1).mean())
b['improved'] = (b.next_rating > b.rating).astype(float).where(b.next_rating.notna() & b.rating.notna())
b['exp'] = 1 / b.next_field
print('population: beaten finishers, fields 6+, next start 7-60 days, true next start:', len(b), 'runs,', b.horse_id.nunique(), 'horses')

def ae_ci(w, e):
    from scipy.stats import chi2 as c2
    lo = c2.ppf(0.025, 2 * w) / 2 / e if w > 0 else 0; hi = c2.ppf(0.975, 2 * w + 2) / 2 / e
    return round(w / e, 2), round(lo, 2), round(hi, 2)

def cells(g, by):
    rows = []
    for k, h in g.groupby(by, observed=True):
        if len(h) < 30: continue
        a = ae_ci(h.next_win.sum(), h.exp.sum())
        rows.append({**dict(zip(by if isinstance(by, list) else [by], k if isinstance(k, tuple) else [k])), 'runs': len(h), 'horses': h.horse_id.nunique(),
                     'next_win_%': round(100 * h.next_win.mean(), 1), 'A/E': a[0], 'A/E_lo95': a[1], 'A/E_hi95': a[2],
                     'improved_figure_%': round(100 * h.improved.mean(), 1), 'next_fig_vs_own_avg3': round(h.next_fig_vs_avg3.mean(), 2)})
    return pd.DataFrame(rows)

# 1. the basic 2x step table (absolute numbers)
t1 = cells(b, ['top_l600', 'step']); t1.to_csv('out/out_inv9_cells_step.csv', index=False); print(t1.to_string(index=False))

# 2. models: interaction before and after adjustment, horse-clustered
base = 'np.log(margin_l + 0.5) + np.log(next_field)'
adj = base + ' + class_delta + fs_z + C(venue_tier) + C(dist_band) + settle_rel + np.log(gap_to_next) + C(tempo_band)'
m_rows = []
def fit(formula, data, name, groups='horse_id'):
    m = smf.logit('next_win ~ ' + formula, data=data).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(data[groups])[0]})
    for term in ['top_l600', 'step_up', 'top_l600:step_up']:
        if term in m.params:
            m_rows.append({'model': name, 'term': term, 'odds_ratio': round(np.exp(m.params[term]), 2), 'lo95': round(np.exp(m.conf_int().loc[term, 0]), 2),
                           'hi95': round(np.exp(m.conf_int().loc[term, 1]), 2), 'p': round(m.pvalues[term], 4), 'runs': int(m.nobs)})
    return m
cc = b.dropna(subset=['class_delta', 'fs_z', 'settle_rel', 'tempo_band']).copy()
fit('top_l600 * step_up + top_l600 * step_down + ' + base, b, 'A: basic (as R9), all runs')
fit('top_l600 * step_up + top_l600 * step_down + ' + base, cc, 'B: basic, complete-data subset')
fit('top_l600 * step_up + top_l600 * step_down + ' + adj, cc, 'C: adjusted for class move, race strength, venue, distance, settling, days, tempo')
fit('top_l600 * step_up + top_l600 * step_down + ' + adj, cc, 'C2: as C, clustered by next race', groups='next_race_id')
mt = pd.DataFrame(m_rows); mt.to_csv('out/out_inv9_models.csv', index=False); print(mt.to_string(index=False))

# 3. does the interaction depend on X? fit the basic model inside each subgroup and test equality of the interaction
def by_group(col):
    rows = []; ests = []
    for k, h in cc.groupby(col, observed=True):
        h = h[h.step_down == 0]
        if h.top_l600.sum() < 40 or (h.top_l600 * h.step_up).sum() < 15: continue
        m = smf.logit('next_win ~ top_l600 * step_up + ' + base, data=h).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(h['horse_id'])[0]})
        e, se = m.params['top_l600:step_up'], m.bse['top_l600:step_up']; ests.append((e, se))
        tu = h[(h.top_l600 == 1) & (h.step_up == 1)]; ts = h[(h.top_l600 == 1) & (h.step_up == 0)]
        rows.append({'factor': col, 'group': k, 'runs': len(h), 'fast_L600_up_runs': len(tu), 'fast_L600_up_A/E': ae_ci(tu.next_win.sum(), tu.exp.sum())[0],
                     'fast_L600_same_A/E': ae_ci(ts.next_win.sum(), ts.exp.sum())[0],
                     'others_up_A/E': ae_ci(h[(h.top_l600 == 0) & (h.step_up == 1)].next_win.sum(), h[(h.top_l600 == 0) & (h.step_up == 1)].exp.sum())[0],
                     'interaction_OR': round(np.exp(e), 2), 'lo95': round(np.exp(e - 1.96 * se), 2), 'hi95': round(np.exp(e + 1.96 * se), 2)})
    if len(ests) > 1:   # Cochran Q test that the interaction is the same across groups
        w = np.array([1 / s ** 2 for _, s in ests]); e = np.array([x for x, _ in ests]); q = float((w * (e - (w * e).sum() / w.sum()) ** 2).sum())
        for r in rows: r['same_across_groups_p'] = round(1 - chi2.cdf(q, len(ests) - 1), 3)
    return rows
sub = []
for col in ['class_move', 'strength_band', 'tempo_band', 'venue_tier', 'dist_band', 'margin_band', 'step']:
    sub += by_group(col) if col != 'step' else []
st = pd.DataFrame(sub); st.to_csv('out/out_inv9_by_subgroup.csv', index=False); print(st.to_string(index=False))

# 4. who are the fast-L600 step-up horses? (composition vs other beaten runners stepping up)
comp = b[b.step_up == 1].groupby('top_l600').agg(runs=('race_id', 'size'), margin_L=('margin_l', 'median'), settle_rel=('settle_rel', 'mean'),
        slow_early_pct=('tempo_band', lambda s: round(100 * (s == 'slow early').mean(), 1)), class_rise_pct=('class_move', lambda s: round(100 * (s == 'rises in class').mean(), 1)),
        race_strength=('field_strength', 'mean'), figure=('rating', 'mean'), step_m=('next_distance_m', lambda s: 0)).round(2)
comp['step_m'] = b[b.step_up == 1].assign(s=lambda x: x.next_distance_m - x.distance_m).groupby('top_l600')['s'].mean().round(0)
comp.to_csv('out/out_inv9_composition.csv'); print(comp.to_string())

# 5. continuous version: closing speed relative to the race's best L600 (0 = fastest), stepping up vs not
b['l600_gap_band'] = pd.cut(b.l600_vs_best, [-0.01, 0.0001, 0.2, 0.5, 1.0, 99], labels=['fastest', '0-0.2s off', '0.2-0.5s', '0.5-1.0s', '1.0s+'])
t5 = cells(b[b.step_down == 0], ['step_up', 'l600_gap_band']); t5.to_csv('out/out_inv9_l600_gradient.csv', index=False); print(t5.to_string(index=False))

# 6. does the fast finish add anything beyond the overall figure of the run? (adds the run's rating v0 and pre-race best of last 3)
cd2 = cc.dropna(subset=['rating', 'best_last3']).copy()
cd2['fig_z'] = (cd2.rating - cd2.rating.mean()) / 5; cd2['pre_z'] = (cd2.best_last3 - cd2.best_last3.mean()) / 5
m_rows.clear()
fit('top_l600 * step_up + top_l600 * step_down + ' + adj, cd2, 'C on figure subset')
fit('top_l600 * step_up + top_l600 * step_down + fig_z + pre_z + ' + adj, cd2, 'D: C + the run figure + pre-race best of last 3')
md = pd.DataFrame(m_rows); md.to_csv('out/out_inv9_models_with_figure.csv', index=False); print(md.to_string(index=False))
