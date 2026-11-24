import pandas as pd, numpy as np
import statsmodels.formula.api as smf
from lib import ae_table
pd.set_option('display.width', 220)
df = pd.read_parquet('runs.parquet')
# last-start rows with a next Qld start within 7-60 days, both fields >= 6, finished, L600 known, did not win last start
d = df[(df.field >= 6) & (df.next_field >= 6) & df.finished & df.l600_rank.notna() & (df.win == 0)
       & df.gap_to_next.between(7, 60)].copy()
d['margin_band'] = pd.cut(d['margin_l'], [0, 2, 4, 7, 100], labels=['beaten <2L','2-4L','4-7L','7L+'])
d['l600_grp'] = pd.cut(d['l600_rank'], [0, 1, 3, 100], labels=['fastest L600 in race','2nd-3rd fastest','rest'])
d['next_distance_m'] = d['next_distance_m'].astype(float); d['distance_m'] = d['distance_m'].astype(float); d['dist_change'] = np.select([(d.next_distance_m >= d.distance_m + 200).fillna(False).to_numpy(bool), (d.next_distance_m <= d.distance_m - 200).fillna(False).to_numpy(bool)], ['up 200m+','down 200m+'], 'similar')
d['next_win'] = d['next_win'].astype(float).astype(int); d['margin_l'] = d['margin_l'].astype(float)
d['next_field'] = d['next_field'].astype(float)
ex, ho = d[d.split == 'explore_2022_2025'], d[d.split == 'holdout_2026']
out = {}
out['next_start_by_margin_x_l600_explore'] = ae_table(ex, ['margin_band','l600_grp'], win='next_win', field='next_field')
out['next_start_by_margin_x_l600_holdout'] = ae_table(ho, ['margin_band','l600_grp'], win='next_win', field='next_field')
# logistic model: next-start win, controlling for last-start margin (quality/form proxy), field size next start
def fit(x):
    m = smf.logit('next_win ~ C(l600_grp, Treatment("rest")) + np.log(margin_l + 0.5) + np.log(next_field)', data=x).fit(disp=0)
    t = m.summary2().tables[1][['Coef.','Std.Err.','P>|z|']].round(4); t['odds_ratio'] = np.exp(t['Coef.']).round(2); return t.reset_index().rename(columns={'index':'term'})
out['logit_explore'] = fit(ex); out['logit_holdout'] = fit(ho)
# does the edge hold when the horse steps up in distance?
out['fastest_l600_by_dist_change_explore'] = ae_table(ex[ex.margin_l <= 4], ['dist_change','l600_grp'], win='next_win', field='next_field')
out['n'] = pd.DataFrame([{'explore_pairs': len(ex), 'holdout_pairs': len(ho), 'explore_from': str(ex.meeting_date.min())[:10], 'explore_to': str(ex.meeting_date.max())[:10], 'holdout_to': str(ho.meeting_date.max())[:10]}])
for k, v in out.items():
    print('\n==', k); print(v.to_string(index=False)); v.to_csv(f'out/out_inv3_{k}.csv', index=False)
