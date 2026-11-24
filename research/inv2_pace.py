import pandas as pd, numpy as np
from statsmodels.discrete.conditional_models import ConditionalLogit
from lib import ae_table, dist_band
pd.set_option('display.width', 220)
df = pd.read_parquet('runs.parquet')
df = df[(df['field'] >= 6) & df['pos_settle'].notna() & ~df['track'].isin(['TAB_Park_Gold_Coast'])].copy()
df['dband'] = dist_band(df['distance_m'])
df['settle_grp'] = pd.cut(df['pos_settle'], [0, 1, 3, 6, 9, 30], labels=['led','2nd-3rd','4th-6th','7th-9th','10th+'])
ex, ho = df[df.split == 'explore_2022_2025'], df[df.split == 'holdout_2026']
out = {}
out['settle_all_explore'] = ae_table(ex, 'settle_grp')
out['settle_all_holdout'] = ae_table(ho, 'settle_grp')
# leader A/E by track x distance band: where is on-pace strongest?
lead = ae_table(ex[ex.pos_settle == 1], ['track', 'dband'])
out['leader_by_track_dist_explore'] = lead[lead.runs >= 80].sort_values('A/E', ascending=False)
# by going
df['going'] = np.select([df.is_poly, df.cond_group.isin(['Good','Firm']), df.cond_group.eq('Soft'), df.cond_group.eq('Heavy')], ['Synthetic','Good/Firm','Soft','Heavy'], 'Unknown')
ex = df[df.split == 'explore_2022_2025']
out['leader_by_going_explore'] = ae_table(ex[ex.pos_settle == 1], 'going')
# Pre-race version: does last start's settling position predict today's?
d = pd.read_parquet('runs.parquet').sort_values(['horse_id','meeting_date','race_no'])
d['prev_settle_rel'] = d.groupby('horse_id')['settle_rel'].shift()
d['prev_led'] = d.groupby('horse_id')['leader_settle'].shift()
d['prev_gap'] = (pd.to_datetime(d['meeting_date']) - pd.to_datetime(d.groupby('horse_id')['meeting_date'].shift())).dt.days
d = d[(d.field >= 6) & d.prev_settle_rel.notna() & d.settle_rel.notna() & (d.prev_gap <= 60)]
dx = d[d.split == 'explore_2022_2025']
out['run_style_persistence'] = pd.DataFrame([{
    'pairs': len(dx), 'corr_prev_vs_today_settle_rel': round(dx[['prev_settle_rel','settle_rel']].corr().iloc[0,1], 3),
    'P(lead today | led last)': round(dx[dx.prev_led == 1].leader_settle.mean(), 3),
    'P(lead today | did not lead last)': round(dx[dx.prev_led == 0].leader_settle.mean(), 3)}])
dx = dx.copy(); dx['prev_style'] = pd.cut(dx['prev_settle_rel'], [-0.01, 0.0001, 0.25, 0.6, 1.01], labels=['led last start','handy (top quarter)','midfield','back'])
out['win_by_prev_style_explore'] = ae_table(dx, 'prev_style')
dh = d[d.split == 'holdout_2026'].copy(); dh['prev_style'] = pd.cut(dh['prev_settle_rel'], [-0.01, 0.0001, 0.25, 0.6, 1.01], labels=['led last start','handy (top quarter)','midfield','back'])
out['win_by_prev_style_holdout'] = ae_table(dh, 'prev_style')
for k, v in out.items():
    print('\n==', k); print(v.to_string(index=False)); v.to_csv(f'out/out_inv2_{k}.csv', index=False)
