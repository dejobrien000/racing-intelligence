"""Batch 18 A5: retrospective Queensland lane-bias candidate (research only; no production release). For each Queensland tracked run,
the day's lane effect is estimated from the OTHER races of the same meeting (leave-one-race-out, known once the meeting is over and before
the horse's next assessment), times the horse's own straight lane relative to its race = estimated help (kg). The share of that help that
actually showed in the run is calibrated ONLY on meetings before 2024 (this-run slope); the candidate subtracts calibrated help from the
performance figure the rating learns from (the recorded margin and the run itself are untouched). Barrier and early position are held
constant in the calibration so lane is not standing in for them. Output: /tmp/cand/lane_adj.parquet (race_key, horse, adj_kg) for the harness.
Fields used (measured by the tracking provider, per 200 m segment): distance from the running rail (average over the segment, metres),
position, ground covered. Lane in the straight = mean distance from the rail over the segments in the last 400 m."""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
src = open('batch17/b17_track_bias.py').read(); src = src[:src.index("OUT = {'coverage'")]; exec(src)
F2 = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'q_race_id', 'q_horse_id']).dropna(subset=['q_race_id']); F2['q_horse_id'] = F2.q_horse_id.astype(str)
X = X.merge(F2, on=['q_race_id', 'q_horse_id'], how='left')
X['lxy'] = (X.lane_w * X.y_w).fillna(0); X['lxx'] = (X.lane_w ** 2).fillna(0)
m = X.groupby('meeting')[['lxy', 'lxx']].transform('sum'); r = X.groupby('race_id')[['lxy', 'lxx']].transform('sum')
X['day_slope'] = (m.lxy - r.lxy) / (m.lxx - r.lxx).replace(0, np.nan); X['help'] = (X.day_slope * X.lane_w).clip(-6, 6)
import os; CAL = os.environ.get('LANE_CAL', 'pre2024')   # 'pre2024' (primary) or '2024' (follow-up: judge 2025-26 only)
md = pd.to_datetime(X.meeting_date)
pre = X[((md < '2024-01-01') if CAL == 'pre2024' else ((md >= '2024-01-01') & (md < '2025-01-01'))) & X.help.notna()]
cal = smf.ols('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w', pre.fillna({'early_rel_w': 0})).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(pre.meeting)[0]})
c = float(cal.params['help'])
X['adj_kg'] = (c * X.help).fillna(0.0)
out = X[X.race.notna() & (X.adj_kg != 0)][['race', 'horse', 'adj_kg']].rename(columns={'race': 'race_key'}).drop_duplicates(['race_key', 'horse'])   # 2 rows duplicated by the tracking join
out.to_parquet('/tmp/cand/lane_adj.parquet' if CAL == 'pre2024' else f'/tmp/cand/lane_adj_{CAL}.parquet')
info = {'runs_adjusted': int(len(out)), f'calibration_share_{CAL}': [round(c, 3), round(float(cal.conf_int().loc['help', 0]), 3), round(float(cal.conf_int().loc['help', 1]), 3)], 'calibration_runs': int(cal.nobs),
        'adj_sd_kg': round(float(out.adj_kg.std()), 3), 'adj_abs_mean_kg': round(float(out.adj_kg.abs().mean()), 3),
        'why_one_third': 'Per kg of estimated lane help the run itself was 0.36 kg better (realised help) and the next run 0.13 kg worse. 0.13 / 0.36 = 0.36: about a third of the realised help was carried into the rating as ability, which is what a rating that moves about a third of the way towards each surprise (Kalman gain ~0.3-0.4 for an exposed horse) does with any surprise. It is a reading of the two slopes, not a separate estimate.'}
json.dump(info, open('batch18/out_b18_lane_candidate.json' if CAL == 'pre2024' else f'batch18/out_b18_lane_candidate_{CAL}.json', 'w'), indent=1); print(json.dumps(info, indent=0))
