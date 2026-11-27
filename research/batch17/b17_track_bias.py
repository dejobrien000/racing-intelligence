"""Batch 17 C13/C14 preliminary test: track bias on Queensland tracking (research only; no prices; point in time where it matters).
Outcome = surprise (performance relative to the field minus rating relative to the field, kg, Engine v2.3 frame): it already allows for
each horse's ability and the field's strength. Inputs: barrier (assigned before the race), early position (first 200 m), racing lane in
the last 400 m (average distance from the rail; an average, not a lane-by-lane trace), rail position from the race record.
(1) Historical configuration tendencies: within-race slopes of surprise on barrier, early position and straight lane for each
    course x distance band x rail band group; are they persistent (even vs odd years) beyond what chance gives (shuffled years)?
(2) Race-day bias: within a meeting, does the lane slope in the first half of the card predict the slope in the second half?
Usage (from research/): python3 batch17/b17_track_bias.py -> batch17/out_b17_track_bias.json"""
import re, json, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
R = con.execute("select race_id, track, distance_m, rail, meeting_date, race_no from race").fetchdf()
S = con.execute("select race_id, horse_code, saddlecloth, barrier, result_state, result_substate from starter where not coalesce(scratched, false)").fetchdf()
SEC = con.execute("select race_id, saddlecloth, segment_end_m, position, dist_to_rail_m from sectional").fetchdf()
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['q_race_id', 'q_horse_id', 'dyn_nat_inn', 'field', 'date']).dropna(subset=['q_race_id'])
F['q_horse_id'] = F.q_horse_id.astype(str); S['horse_code'] = S.horse_code.astype(str)
X = F.merge(S, left_on=['q_race_id', 'q_horse_id'], right_on=['race_id', 'horse_code']).merge(R, on='race_id')
first = SEC[SEC.segment_end_m == 200].set_index(['race_id', 'saddlecloth']).position
SEC = SEC.merge(R[['race_id', 'distance_m']], on='race_id'); last4 = SEC[SEC.segment_end_m > SEC.distance_m - 400].groupby(['race_id', 'saddlecloth']).dist_to_rail_m.mean()
X['early_pos'] = [first.get(k, np.nan) for k in zip(X.race_id, X.saddlecloth)]; X['lane'] = [last4.get(k, np.nan) for k in zip(X.race_id, X.saddlecloth)]
X = X[X.dyn_nat_inn.notna() & X.barrier.notna() & (X.field >= 6)].copy()
X['barrier_rel'] = (X.barrier.astype(float) - 1) / (X.field - 1); X['early_rel'] = (X.early_pos - 1) / (X.field - 1)
rb = lambda s: 0.0 if re.match(r'(?i)\s*true', str(s)) else (float(re.search(r'\+(\d+(?:\.\d+)?)', str(s)).group(1)) if re.search(r'\+(\d+(?:\.\d+)?)', str(s)) else np.nan)
X['rail_m'] = X.rail.map(rb); X['rail_band'] = pd.cut(X.rail_m, [-0.1, 0.5, 3.5, 6.5, 99], labels=['true', '+1-3', '+4-6', '+7+']).astype(str)
X['dband'] = pd.cut(X.distance_m, [0, 1200, 1600, 9999], labels=['to 1200', '1201-1600', '1601+']).astype(str)
X['yr'] = pd.to_datetime(X.meeting_date).dt.year; X['meeting'] = X.track + '|' + X.meeting_date.astype(str)
for c in ['barrier_rel', 'early_rel', 'lane']: X[c + '_w'] = X[c] - X.groupby('race_id')[c].transform('mean')   # within race
X['y_w'] = X.dyn_nat_inn - X.groupby('race_id').dyn_nat_inn.transform('mean')
OUT = {'coverage': {'runs': int(len(X)), 'races': int(X.race_id.nunique()), 'meetings': int(X.meeting.nunique()), 'with_rail_band': round(float((X.rail_band != 'nan').mean()), 3),
                    'with_early_position': round(float(X.early_pos.notna().mean()), 3), 'with_lane': round(float(X.lane.notna().mean()), 3), 'years': sorted(map(int, X.yr.unique()))},
       'result_states': S.result_state.value_counts().head(8).to_dict(), 'result_substates': S.result_substate.value_counts().head(10).to_dict()}
def slope(d, c):
    d = d[d[c + '_w'].notna()]; v = (d[c + '_w'] ** 2).sum()
    return float((d[c + '_w'] * d.y_w).sum() / v) if v > 0 and len(d) >= 200 else np.nan
OUT['overall_slopes_kg'] = {c: round(slope(X, c), 3) for c in ['barrier_rel', 'early_rel', 'lane']}   # barrier/early: inside->outside (0->1); lane: per metre off the rail
G = X[X.rail_band != 'nan'].copy(); G['grp'] = G.track + ' | ' + G.dband + ' | rail ' + G.rail_band
rng = np.random.default_rng(17)
for c in ['barrier_rel', 'early_rel', 'lane']:
    rows = []
    for gname, d in G.groupby('grp'):
        a, b = slope(d[d.yr % 2 == 0], c), slope(d[d.yr % 2 == 1], c)
        if not (np.isnan(a) or np.isnan(b)): rows.append((gname, a, b, slope(d, c), int(len(d))))
    T = pd.DataFrame(rows, columns=['grp', 'even', 'odd', 'all', 'runs'])
    obs = float(np.corrcoef(T.even, T.odd)[0, 1]) if len(T) >= 5 else np.nan
    null = []                                      # chance level: shuffle meetings between the halves within each group
    for _ in range(100):
        rr = []
        for gname, d in G[G.grp.isin(T.grp)].groupby('grp'):
            m = d.meeting.unique(); half = set(rng.choice(m, len(m) // 2, replace=False)); a, b = slope(d[d.meeting.isin(half)], c), slope(d[~d.meeting.isin(half)], c)
            if not (np.isnan(a) or np.isnan(b)): rr.append((a, b))
        rr = np.array(rr); null.append(np.corrcoef(rr[:, 0], rr[:, 1])[0, 1])
    OUT[f'configuration_{c}'] = {'groups': int(len(T)), 'even_vs_odd_year_corr': round(obs, 3), 'random_half_corr_mean': round(float(np.mean(null)), 3), 'random_half_corr_p95': round(float(np.percentile(null, 95)), 3),
                                 'largest_groups': T.sort_values('runs', ascending=False).head(8).round(3).to_dict('records'), 'spread_of_group_slopes_sd': round(float(T['all'].std()), 3)}
# race-day: first half of the card vs second half, lane and early position
def s_(d, c):
    d = d[d[c + '_w'].notna()]; v = (d[c + '_w'] ** 2).sum(); return float((d[c + '_w'] * d.y_w).sum() / v) if v > 0 and len(d) >= 30 else np.nan
for c in ['lane', 'early_rel']:
    rr = []
    for mtg, d in X[X[c].notna()].groupby('meeting'):
        n = d.race_no.max()
        if n < 6: continue
        a, b = s_(d[d.race_no <= n // 2], c), s_(d[d.race_no > n // 2], c)
        if not (np.isnan(a) or np.isnan(b)): rr.append((a, b))
    rr = np.array(rr); OUT[f'race_day_{c}'] = {'meetings': int(len(rr)), 'first_half_vs_second_half_corr': round(float(np.corrcoef(rr[:, 0], rr[:, 1])[0, 1]), 3),
                                                'second_half_slope_when_first_half_top_quarter': round(float(rr[rr[:, 0] >= np.percentile(rr[:, 0], 75), 1].mean()), 3),
                                                'second_half_slope_when_first_half_bottom_quarter': round(float(rr[rr[:, 0] <= np.percentile(rr[:, 0], 25), 1].mean()), 3), 'mean_slope': round(float(rr.mean()), 3)}
json.dump(OUT, open('batch17/out_b17_track_bias.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:5000])
