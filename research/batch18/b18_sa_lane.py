"""Batch 18 A5 replication on South Australian tracking (research only; no prices; no release). Same construction as the Queensland
test (batch17/b17_bias_next_run.py, batch18/b18_lane_candidate.py): the meeting's lane effect from the OTHER races of the same meeting
(leave-one-race-out) times the horse's own straight lane relative to its race = estimated help (kg). Questions: (1) does the run itself show
the help (this-run slope, with barrier and early position held constant)? (2) does the next run move the other way (the rating took the help
as ability)? SA tracking begins January 2024, so there is no pre-2024 calibration period: this is a replication of the two relations, not a
candidate. Lane in the straight = mean distance from the rail over the segments ending in the last 400 m; early position = position at the
first recorded segment (SA's first split is not always 200 m). Ground covered is not available for SA.
Usage: python3 batch18/b18_sa_lane.py -> batch18/out_b18_sa_lane.json"""
import json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
con = duckdb.connect('../history/history.duckdb', read_only=True)
R = con.execute("select r.race_id, r.track, r.meeting_date, r.race_no, r.distance_m from sa_race r join sa_race_checks c using(race_id) where c.pass").fetchdf()
S = con.execute("select race_id, saddlecloth, name_key, barrier from sa_starter where not coalesce(scratched, false)").fetchdf()
SEC = con.execute("select race_id, saddlecloth, segment_end_m, position, dist_to_rail_m from sa_sectional").fetchdf().merge(R[['race_id', 'distance_m']], on='race_id')
first = SEC.loc[SEC.groupby('race_id').segment_end_m.transform('min') == SEC.segment_end_m].set_index(['race_id', 'saddlecloth']).position
last4 = SEC[SEC.segment_end_m > SEC.distance_m - 400].groupby(['race_id', 'saddlecloth']).dist_to_rail_m.mean()
X = S.merge(R, on='race_id')
X['race'] = 'SA|' + X.track.str.lower().str.replace('_', '-') + '|' + pd.to_datetime(X.meeting_date).dt.strftime('%Y-%m-%d') + '|' + X.race_no.astype(str)
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date', 'dyn_nat_inn', 'field', 'state'])
F = F.sort_values(['horse', 'date', 'race']); F['nxt'] = F.groupby('horse').dyn_nat_inn.shift(-1); Fs = F[F.state == 'SA']
n_sa = len(X); X = X.merge(Fs, left_on=['race', 'name_key'], right_on=['race', 'horse'], how='inner')
cov = {'sa_tracked_runners': int(n_sa), 'matched_to_rating_frame': int(len(X)), 'match_share': round(len(X) / n_sa, 3)}
X['early_pos'] = [first.get(k, np.nan) for k in zip(X.race_id, X.saddlecloth)]; X['lane'] = [last4.get(k, np.nan) for k in zip(X.race_id, X.saddlecloth)]
X = X[X.dyn_nat_inn.notna() & X.barrier.notna() & (X.field >= 6)].copy()
X['barrier_rel'] = (X.barrier.astype(float) - 1) / (X.field - 1); X['early_rel'] = (X.early_pos - 1) / (X.field - 1)
for c in ['barrier_rel', 'early_rel', 'lane']: X[c + '_w'] = X[c] - X.groupby('race_id')[c].transform('mean')
X['y_w'] = X.dyn_nat_inn - X.groupby('race_id').dyn_nat_inn.transform('mean'); X['meeting'] = X.track + '|' + X.meeting_date.astype(str)
cov.update({'runs_used': int(len(X)), 'with_lane': round(float(X.lane.notna().mean()), 3), 'meetings': int(X.meeting.nunique()), 'first': str(X.meeting_date.min())[:10], 'last': str(X.meeting_date.max())[:10]})
X['lxy'] = (X.lane_w * X.y_w).fillna(0); X['lxx'] = (X.lane_w ** 2).fillna(0)
m = X.groupby('meeting')[['lxy', 'lxx']].transform('sum'); r = X.groupby('race_id')[['lxy', 'lxx']].transform('sum')
X['day_slope'] = (m.lxy - r.lxy) / (m.lxx - r.lxx).replace(0, np.nan); X['help'] = (X.day_slope * X.lane_w)
d = X[np.isfinite(X.help)].copy(); d['b'] = d.help.clip(d.help.quantile(0.01), d.help.quantile(0.99))
ci = lambda mm, k: [round(float(mm.params[k]), 3), round(float(mm.conf_int().loc[k, 0]), 3), round(float(mm.conf_int().loc[k, 1]), 3)]
t1 = smf.ols('dyn_nat_inn ~ b + barrier_rel_w + early_rel_w', d.fillna({'early_rel_w': 0})).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.meeting)[0]})
dn = d.dropna(subset=['nxt']); t2 = smf.ols('nxt ~ b + dyn_nat_inn', dn).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(dn.horse)[0]})
q = pd.qcut(dn.b, 5, labels=['most harmed', 'q2', 'q3', 'q4', 'most helped']).astype(str)
OUT = {'coverage': cov, 'lane_help_sd_kg': round(float(d.b.std()), 2), 'overall_lane_slope_kg_per_m': round(float((d.lane_w * d.y_w).sum() / (d.lane_w ** 2).sum()), 3),
       'this_run_per_kg_of_help_with_barrier_early_controls': ci(t1, 'b'), 'this_run_runs': int(t1.nobs),
       'next_run_per_kg_of_help': ci(t2, 'b'), 'next_run_runs': int(t2.nobs), 'next_surprise_by_quintile': {k: round(float(v), 2) for k, v in dn.groupby(q).nxt.mean().items()},
       'qld_reference': {'this_run': 0.36, 'next_run': [-0.132, -0.177, -0.086], 'lane_help_sd': 0.84}}
OUT['carried_share'] = round(-OUT['next_run_per_kg_of_help'][0] / OUT['this_run_per_kg_of_help_with_barrier_early_controls'][0], 2) if OUT['this_run_per_kg_of_help_with_barrier_early_controls'][0] > 0 else None
json.dump(OUT, open('batch18/out_b18_sa_lane.json', 'w'), indent=1); print(json.dumps(OUT, indent=0))
# Candidate file (env SA_LANE_OUT): share calibrated on 2024 SA meetings only (this-run slope with barrier/early controls), applied to
# every SA tracked run; the harness can judge 2025-26 cleanly (2024 is the calibration year).
import os
if os.environ.get('SA_LANE_OUT'):
    c24 = d[pd.to_datetime(d.meeting_date) < '2025-01-01'].fillna({'early_rel_w': 0})
    cal = smf.ols('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w', c24).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(c24.meeting)[0]})
    sh = float(cal.params['help']); X['adj_kg'] = (sh * X.help.clip(-6, 6)).fillna(0.0)
    o = X[X.adj_kg != 0][['race', 'horse', 'adj_kg']].rename(columns={'race': 'race_key'}).drop_duplicates(['race_key', 'horse'])
    o.to_parquet(os.environ['SA_LANE_OUT']); info = {'share_2024': ci(cal, 'help'), 'calibration_runs': int(cal.nobs), 'runs_adjusted': int(len(o)), 'adj_sd_kg': round(float(o.adj_kg.std()), 3)}
    json.dump(info, open('batch18/out_b18_sa_lane_candidate.json', 'w'), indent=1); print(info)
