"""Batch 14 (Damo's "Research Batch 13: physical performance, momentum, course geometry, rider specialisation", 26 Nov 2026 night).
Folder batch14 because research/batch13 already holds the 26 Nov consolidation tests.
Run-level physical table for Queensland (RQ tracking) and South Australia (Racing SA tracking), measured data only:
  - cumulative time at the 800/600/400/200 m marks and the line, from each runner's own 200 m splits
  - deficit to the race leader at each mark, in seconds (measured; a length is about 0.17 s)
  - 200 m segment speeds v1000 (1000-800 out) ... v200 (last 200), each also relative to the race median (removes tempo, going, rail of the day)
  - early tempo of the race: leader's average speed to the 600 m mark, standardised within track x distance (z; + = faster early)
  - path: distance from the rail per segment (Qld; SA where supplied), ground covered
Then joined to the national v3 frame (the rating Queensland production uses) for: pre-race rating, rating surprise this run and next
runs (dyn_nat_inn, kg: how much better or worse than the pre-race rating, relative to the field), jockey key, distance, class.
Nothing is estimated or filled: a mark without a measured split stays missing. No market data. Output: /home/claude/b14/runs_<STATE>.parquet"""
import duckdb, re, os, numpy as np, pandas as pd
os.makedirs('/home/claude/b14', exist_ok=True)
DB = '/home/claude/racing-intelligence/history/history.duckdb'
c = duckdb.connect(DB, read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', str(s).upper())
MARKS = [1000, 800, 600, 400, 200, 0]

def build(st):
    sec, stt, rac = ('sectional', 'starter', 'race') if st == 'QLD' else ('sa_sectional', 'sa_starter', 'sa_race')
    seglen = "200.0" if st == 'QLD' else "s.seg_len_m"
    S = c.execute(f"""select s.race_id, s.saddlecloth, s.segment_end_m seg, {seglen} seglen, s.split_s, s.avg_speed_ms v, s.position pos,
                             s.stride_freq_hz sf, s.stride_len_m sl, s.dist_to_rail_m rail, r.distance_m d, r.meeting_date, r.track, r.race_no, r.start_time
                      from {sec} s join {rac} r using (race_id)""").fetchdf()
    R = c.execute(f"""select race_id, saddlecloth, name_key, finish_pos fp, margin_l m, finish_time_s t, ground_m, weight_kg, barrier, jockey, trainer
                      from {stt} where result_state='Finished' and finish_pos is not null""").fetchdf().drop_duplicates(['race_id', 'saddlecloth'])
    S = S.merge(R[['race_id', 'saddlecloth']], on=['race_id', 'saddlecloth']).drop_duplicates(['race_id', 'saddlecloth', 'seg'])
    S = S.sort_values(['race_id', 'saddlecloth', 'seg']).reset_index(drop=True)
    # only races where every finisher has a complete, contiguous set of splits starting at the jump (else cumulative times are not comparable)
    S['cum'] = S.groupby(['race_id', 'saddlecloth']).split_s.cumsum()
    first = S.groupby(['race_id', 'saddlecloth']).seg.transform('min'); S = S[first.le(S.seglen + 1)]                      # first split starts at the jump
    S['to_go'] = S.d - S.seg
    end = S.groupby(['race_id', 'saddlecloth']).to_go.transform('min'); S = S[end.abs() < 1]                               # reaches the line
    rcount = S.groupby('race_id').saddlecloth.nunique(); fin = R.groupby('race_id').saddlecloth.nunique()
    good = rcount[rcount.eq(fin.reindex(rcount.index))].index; S = S[S.race_id.isin(good)]
    K = ['race_id', 'saddlecloth']; X = R[R.race_id.isin(good)].set_index(K).copy()
    for mk in MARKS:
        m = S[S.to_go.round() == mk].set_index(K)
        X[f'cum{mk}'] = m.cum; X[f'pos{mk}'] = m.pos; X[f'rail{mk}'] = m.rail
        if mk < 1000:                                                                     # speed of the 200 m segment ENDING at this mark
            seg200 = m[(m.seglen.round() == 200)]
            X[f'v{mk + 200}'] = seg200.v; X[f'sl{mk + 200}'] = seg200.sl; X[f'sf{mk + 200}'] = seg200.sf
    X = X.reset_index()
    meta = S.groupby('race_id')[['d', 'meeting_date', 'track', 'race_no', 'start_time']].first()
    X = X.join(meta, on='race_id')
    for mk in MARKS: X[f'def{mk}'] = X[f'cum{mk}'] - X.groupby('race_id')[f'cum{mk}'].transform('min')   # seconds behind the leader at the mark
    for v in ['v1000', 'v800', 'v600', 'v400', 'v200', 'sl200', 'sl400', 'sf200', 'sf400', 'ground_m']:
        if v in X: X[v + '_rel'] = X[v] - X.groupby('race_id')[v].transform('median')
    for v in ['v1000', 'v800', 'v600', 'v400', 'v200']: X.loc[~X[v].between(9, 22), v] = np.nan
    # early tempo: leader's time to the 600 m mark -> average speed; z within track x distance (>= 8 races), else missing
    lead600 = X.groupby('race_id').cum600.min(); rs = pd.DataFrame({'sp': (meta.d - 600) / lead600, 'track': meta.track, 'd': meta.d}).dropna()
    rs = rs[(rs.sp > 9) & (rs.sp < 20) & (rs.d >= 900)]
    g = rs.groupby(['track', 'd']).sp; n = g.transform('count'); rs['tempo_z'] = ((rs.sp - g.transform('median')) / g.transform('std')).where(n >= 8)
    X['tempo_z'] = X.race_id.map(rs.tempo_z); X['early_sp'] = X.race_id.map(rs.sp)
    X['field'] = X.groupby('race_id').saddlecloth.transform('count'); X['fp_pct'] = (X.fp - 1) / (X.field - 1).clip(lower=1)
    X['meeting_date'] = pd.to_datetime(X.meeting_date); X['horse'] = X.name_key.map(nk); X['state'] = st
    return X

V = pd.read_parquet('/home/claude/racing-intelligence/research/engine/frames/national_v3.parquet',
                    columns=['state', 'venue', 'date', 'race_no', 'race_id', 'q_race_id', 'horse', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'finish_pos', 'field',
                             'margin_l', 'distance_m', 'class_label', 'bm', 'jkey', 'tkey', 'j_surp', 'j_n', 'r_firstup', 'prev', 'gap', 'dist_change', 'age_n', 'fig_n', 'settle_rel', 'weight_kg', 'meeting_id', 'period'])
V = V.sort_values(['horse', 'date', 'race_no']).reset_index(drop=True); g = V.groupby('horse')
V['nat_fp_pct'] = (V.finish_pos - 1) / (V.field - 1).clip(lower=1)
for k in [1, 2, 3]: V[f'inn_n{k}'] = g.dyn_nat_inn.shift(-k); V[f'fp_n{k}'] = g.nat_fp_pct.shift(-k); V[f'gap_n{k}'] = g.gap.shift(-k)
V['dist_n1'] = g.distance_m.shift(-1); V['next3'] = V[['inn_n1', 'inn_n2', 'inn_n3']].mean(axis=1); V['n_runs'] = g.cumcount()
V['prep_run'] = (V.gap.isna() | (V.gap > 60)).astype(int).groupby(V.horse).cumsum(); V['prep_idx'] = V.groupby(['horse', 'prep_run']).cumcount() + 1   # run number within preparation
V['n_jk_meet'] = 0
V.to_parquet('/home/claude/b14/national_v3_next.parquet')
for st in ['QLD', 'SA']:
    X = build(st)
    if st == 'QLD':
        Y = X.merge(V[V.state == 'QLD'].rename(columns={'race_id': 'nat_race', 'q_race_id': 'race_id'}).drop(columns=['state']), on=['race_id', 'horse'], how='inner')
    else:
        W = V[V.state == 'SA'].copy(); W['venue_key'] = W.venue.str.lower().str.replace(r'[^a-z]', '', regex=True); W['dkey'] = pd.to_datetime(W.date).dt.date
        X['venue_key'] = X.track.str.lower().str.replace(r'[^a-z]', '', regex=True); X['dkey'] = X.meeting_date.dt.date
        Y = X.merge(W.rename(columns={'race_id': 'nat_race', 'race_no': 'nat_race_no'}).drop(columns=['state', 'q_race_id']), left_on=['dkey', 'venue_key', 'race_no', 'horse'],
                    right_on=['dkey', 'venue_key', 'nat_race_no', 'horse'], how='inner')
    print(st, 'tracked finishers', len(X), 'races', X.race_id.nunique(), '| joined to national frame', len(Y), f'({100 * len(Y) / len(X):.1f}%)',
          '| tempo_z present', round(Y.tempo_z.notna().mean(), 3), '| years', Y.meeting_date.dt.year.value_counts().sort_index().to_dict())
    Y.to_parquet(f'/home/claude/b14/runs_{st}.parquet')
