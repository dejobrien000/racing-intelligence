import pandas as pd, numpy as np
import statsmodels.formula.api as smf
from lib import ae_table
pd.set_option('display.width', 220)
df = pd.read_parquet('runs.parquet')
for c in ['margin_l','ground_extra','distance_m','next_field','next_win','field','days_since','finish_pct','next_finish_pct']:
    df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)
out = {}
# --- 4a. same race: extra ground vs margin, within-race (race-demeaned) regression
d = df[(df.field >= 6) & df.finished & df.ground_extra.notna() & df.margin_l.notna()].copy()
for c in ['ground_extra','margin_l']:
    d[c + '_dm'] = d[c] - d.groupby('race_id')[c].transform('mean')
rows = []
for split, g in d.groupby('split'):
    m = smf.ols('margin_l_dm ~ ground_extra_dm - 1', data=g).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(g['race_id'])[0]})
    rows.append({'split': split, 'runs': len(g), 'lengths_per_extra_metre': round(m.params.iloc[0], 3), 'se': round(m.bse.iloc[0], 3), 'r2_within': round(m.rsquared, 3)})
out['ground_vs_margin_within_race'] = pd.DataFrame(rows)
# --- 4b. next start: wide trip last start (extra ground in the race's widest quarter, >= 8m), within last-start margin bands
n = df[(df.field >= 6) & (df.next_field >= 6) & df.finished & (df.win == 0) & df.gap_to_next.between(7, 60) & df.ground_extra.notna()].copy()
n['wide'] = np.where(n.ground_extra >= 8, 'covered 8m+ extra', 'under 8m extra')
n['margin_band'] = pd.cut(n['margin_l'], [0, 2, 4, 7, 100], labels=['beaten <2L','2-4L','4-7L','7L+'])
n['next_win'] = n['next_win'].astype(int)
out['wide_trip_next_start_explore'] = ae_table(n[n.split == 'explore_2022_2025'], ['margin_band','wide'], win='next_win', field='next_field')
out['wide_trip_next_start_holdout'] = ae_table(n[n.split == 'holdout_2026'], ['margin_band','wide'], win='next_win', field='next_field')
def fit(x):
    m = smf.logit('next_win ~ I(ground_extra >= 8) + np.log(margin_l + 0.5) + np.log(next_field)', data=x).fit(disp=0)
    t = m.summary2().tables[1][['Coef.','Std.Err.','P>|z|']].round(4); t['odds_ratio'] = np.exp(t['Coef.']).round(2); return t.reset_index().rename(columns={'index':'term'})
out['wide_trip_logit_explore'] = fit(n[n.split == 'explore_2022_2025']); out['wide_trip_logit_holdout'] = fit(n[n.split == 'holdout_2026'])
# --- 5. fitness: days since previous TAB start (any state, via Betfair) and preparation run number
f = df[(df.field >= 6) & df.days_since.notna()].copy()
f['gap_grp'] = pd.cut(f['days_since'], [0, 13, 20, 27, 41, 59, 120, 240, 5000], labels=['<=13d','14-20d','21-27d','28-41d','42-59d','60-120d (first-up)','121-240d (first-up)','241d+ (long spell)'])
out['win_by_days_since_explore'] = ae_table(f[f.split == 'explore_2022_2025'], 'gap_grp')
out['win_by_days_since_holdout'] = ae_table(f[f.split == 'holdout_2026'], 'gap_grp')
# within-horse preparation pattern: first-up vs second-up vs third-up (compares each horse with itself)
p = df.sort_values(['horse_id','meeting_date','race_no']).copy()
p['new_prep'] = (p['days_since'] >= 60)
p['prep_id'] = p.groupby('horse_id')['new_prep'].cumsum()
p.loc[p.days_since.isna(), 'prep_id'] = np.nan
p['run_in_prep'] = p.groupby(['horse_id','prep_id']).cumcount() + 1
p = p[p.prep_id.notna() & (p.prep_id > 0) & p.finished & (p.field >= 6)]
w = p[p.run_in_prep <= 4].pivot_table(index=['horse_id','prep_id'], columns='run_in_prep', values='finish_pct', aggfunc='first')
rows = []
for a, b in [(1, 2), (2, 3), (3, 4)]:
    x = w[[a, b]].dropna(); diff = (x[b] - x[a])
    rows.append({'comparison': f'run {b} vs run {a} of prep', 'horses_preps': len(x), 'mean_finish_pct_change': round(diff.mean(), 4),
                 'se': round(diff.std() / np.sqrt(len(x)), 4), 'share_improved': round((diff < 0).mean(), 3)})
out['prep_pattern_within_horse'] = pd.DataFrame(rows)
for k, v in out.items():
    print('\n==', k); print(v.to_string(index=False)); v.to_csv(f'out/out_inv45_{k}.csv', index=False)
