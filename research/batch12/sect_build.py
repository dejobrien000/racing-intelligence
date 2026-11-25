"""Batch 12 s5/s6: per-run Queensland tracking composition (measured, individual), field-relative. Output /home/claude/b12/sect_runs.parquet."""
import duckdb, numpy as np, pandas as pd
c = duckdb.connect('/tmp/nat3/history/history.duckdb', read_only=True)
S = c.execute("""select s.race_id, s.saddlecloth, s.segment_end_m seg, s.split_s, s.avg_speed_ms v, s.position pos, s.stride_freq_hz sf, s.stride_len_m sl, s.dist_to_rail_m rail,
                        r.distance_m d, r.meeting_date, r.track, r.track_rating_tracking going
                 from sectional s join race r using (race_id)""").fetchdf()
R0 = c.execute("""select s.race_id, s.saddlecloth, s.name_key, s.finish_pos fp, s.margin_l m, s.finish_time_s t, s.ground_m, s.weight_kg, s.barrier from starter s
                 where s.result_state='Finished' and s.finish_pos is not null""").fetchdf()
R = R0.drop_duplicates(['race_id', 'saddlecloth'])
S = S.merge(R[['race_id', 'saddlecloth']], on=['race_id', 'saddlecloth']).drop_duplicates(['race_id', 'saddlecloth', 'seg']).sort_values(['race_id', 'saddlecloth', 'seg']).reset_index(drop=True)
S['to_go'] = S.d - S.seg                                     # metres still to run at the end of this segment
seg = lambda k: S[S.to_go == k].set_index(['race_id', 'saddlecloth'])
L200, L400, L600 = seg(0), seg(200), seg(400)                 # segments ending at the line, 200 m out, 400 m out
X = R.set_index(['race_id', 'saddlecloth']).copy()
X['v200'] = L200.v; X['v400'] = L400.v; X['v600'] = L600.v; X['sf200'] = L200.sf; X['sl200'] = L200.sl; X['sf400'] = L400.sf; X['sl400'] = L400.sl
X['pos400'] = L400.pos; X['pos600'] = L600.pos; X['pos800'] = seg(600).pos
S['cum'] = S.groupby(['race_id', 'saddlecloth']).split_s.cumsum()
t600 = S[S.to_go == 600].set_index(['race_id', 'saddlecloth']).cum            # time to the 600 m mark
X['t600'] = t600; X['early_speed'] = (pd.Series(X.index.get_level_values(0), index=X.index).map(S.groupby('race_id').d.first()) - 600) / X.t600
X = X.reset_index(); X['d'] = X.race_id.map(S.groupby('race_id').d.first()); X['meeting_date'] = X.race_id.map(S.groupby('race_id').meeting_date.first()); X['track'] = X.race_id.map(S.groupby('race_id').track.first())
X['going'] = X.race_id.map(S.groupby('race_id').going.first())
X = X[X.v200.between(10, 22) & X.v400.between(10, 22)].copy()
X['accel'] = X.v200 - X.v400; X['retention'] = X.v200 / X.v400                    # final 200 vs the 200 before it
X['l600_s'] = 200 / X.v200 + 200 / X.v400 + 200 / X.v600
for col in ['v200', 'v400', 'v600', 'accel', 'retention', 'early_speed', 'l600_s', 'sf200', 'sl200', 'ground_m']:
    X[col + '_rel'] = X[col] - X.groupby('race_id')[col].transform('median')      # field-relative: removes tempo, going, track, distance, rail of the day
X['field'] = X.groupby('race_id').saddlecloth.transform('count'); X['fp_pct'] = (X.fp - 1) / (X.field - 1).clip(lower=1)
X['meeting_date'] = pd.to_datetime(X.meeting_date)
print(X.shape, X[['v200', 'v400', 'accel', 'retention', 'early_speed', 'sf200', 'sl200']].describe().round(3).to_string())
X.to_parquet('/home/claude/b12/sect_runs.parquet')
