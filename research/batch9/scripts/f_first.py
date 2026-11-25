"""Batch 9 study F (first look): (1) hard early pressure x recovery days (Qld sectionals), (2) real opposition change."""
import numpy as np, pandas as pd, duckdb
pd.set_option('display.width', 220)
con = duckdb.connect('../history/history.duckdb', read_only=True)
S = con.execute("""select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.avg_speed_ms v, s.position pos, r.track, r.distance_m
                   from sectional s join race r using (race_id) where r.distance_m - s.segment_end_m in (0, 200, 400, 600, 800)""").fetchdf()
W = S.pivot_table(index=['race_id', 'saddlecloth', 'track', 'distance_m'], columns='to_go', values=['v', 'pos']).reset_index()
W.columns = ['race_id', 'saddlecloth', 'track', 'distance_m'] + [f'{a}{int(b)}' for a, b in W.columns[4:]]
W = W.dropna(subset=['v600', 'v800', 'pos800', 'pos0'])
rv = W.groupby('race_id')[['v800', 'v600']].median().mean(axis=1).rename('race_mid')
W = W.merge(rv, left_on='race_id', right_index=True)
norm = W.groupby(['track', 'distance_m']).race_mid.transform('median'); W['tempo'] = W.race_mid - norm   # mid-race pace vs course/distance norm (m/s)
q = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'saddlecloth', 'margin_l', 'finish_pos'])
W = W.merge(q, on=['race_id', 'saddlecloth'])
W['pressure'] = np.select([(W.pos800 <= 2) & (W.tempo >= 0.15), (W.pos800 <= 2)], ['on speed, hot tempo', 'on speed, ordinary tempo'], 'not on speed')
W['fought'] = np.where(W.margin_l.fillna(99) <= 2, 'fought on (within 2L)', 'beaten further')
E = pd.read_parquet('/tmp/exp/rt/E.parquet'); E = E[E.state == 'QLD'].merge(W[['race_id', 'horse_id', 'pressure', 'fought', 'tempo']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'}), on=['q_race_id', 'q_horse_id'])
E['recovery'] = pd.cut(E.gap_next, [6, 13, 27, 60, 120], labels=['7-13 days', '14-27', '28-60', '61-120'])
t = E.groupby(['pressure', 'fought', 'recovery'], observed=True).agg(runs=('Y', 'size'), next_Y=('Y', 'mean'), sd=('Y', 'std')).reset_index()
t['se'] = t.sd / np.sqrt(t.runs); t = t.drop(columns='sd').round(3); print(t.to_string(index=False)); t.to_csv('/tmp/exp/rt/f_pressure_recovery.csv', index=False)
# (2) opposition change, all states: next race's field strength minus this race's
A = pd.read_parquet('/tmp/exp/rt/E.parquet')
fq = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'dyn_nat']).groupby('race_id').dyn_nat.mean()
A['fq'] = A.race_id.map(fq); A['nx_fq'] = A.nx_race_id.map(fq); A['opp_change'] = A.nx_fq - A.fq
A['opp_band'] = pd.cut(A.opp_change, [-99, -3, -1, 1, 3, 99], labels=['much weaker (3kg+)', 'weaker (1-3)', 'similar', 'stronger (1-3)', 'much stronger (3kg+)'])
o = A.groupby(['opp_band', 'half'], observed=True).agg(runs=('Y', 'size'), next_Y=('Y', 'mean'), sd=('Y', 'std')).reset_index(); o['se'] = o.sd / np.sqrt(o.runs)
print(o.drop(columns='sd').round(3).to_string(index=False)); o.drop(columns='sd').round(3).to_csv('/tmp/exp/rt/f_opposition_change.csv', index=False)
