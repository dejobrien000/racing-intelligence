"""Evidence for the data-foundation register (26 Nov 2026): how TAB form records (past starts) compare with the sources we
already hold, field by field and by state. Read-only; writes ops/foundation/tab_form_overlap.csv and prints a summary.
Usage (from research/): python3 ops/foundation/tab_form_overlap.py <YYYYMMDD> ../history/history.duckdb"""
import sys, re, duckdb, pandas as pd, numpy as np
D, DB = sys.argv[1], sys.argv[2]
P = pd.read_csv(f'collect/national/{D}/form_past_starts.csv', dtype=str)
P = P[P.start_type.isin(['LastStarts', 'WinRun'])].copy()
P = P.rename(columns={'class': 'tab_class'}); P['k'] = P.name.str.upper().str.replace(r'[^A-Z0-9]', '', regex=True); P['d'] = P.start_date
con = duckdb.connect(DB, read_only=True)
key = lambda col: f"regexp_replace(upper({col}), '[^A-Z0-9]', '', 'g')"
bn = con.execute(f"""select {key('u.name_key')} k, cast(u.meeting_date as varchar) d, m.state, u.finish_pos, u.margin_l, u.weight_kg, u.jockey, r.distance_m, r.class,
                     r.going, r.race_time_s, r.last600_s from bn_runner u join bn_meeting m using (meeting_date, slug) join bn_race r using (meeting_date, slug, race_no)
                     where not r.is_trial""").fetchdf().drop_duplicates(['k', 'd'])
qs = con.execute(f"""select {key('name_key')} k, cast(meeting_date as varchar) d, finish_pos q_finish, barrier q_barrier from starter where not coalesce(scratched,false)""").fetchdf().drop_duplicates(['k', 'd'])
nf = con.execute(f"""select {key('name_key')} k, cast(run_date as varchar) d, barrier n_barrier, pos800, pos400 from nsw_form_line where not coalesce(trial,false)""").fetchdf().drop_duplicates(['k', 'd'])
sa = con.execute(f"""select {key('name_key')} k, cast(meeting_date as varchar) d, barrier sa_barrier from sa_starter where not coalesce(scratched,false)""").fetchdf().drop_duplicates(['k', 'd'])
X = P.merge(bn, on=['k', 'd'], how='left').merge(qs, on=['k', 'd'], how='left').merge(nf, on=['k', 'd'], how='left').merge(sa, on=['k', 'd'], how='left')
X['state'] = X.state.fillna('not in Breednet')
num = lambda s: pd.to_numeric(s, errors='coerce')
X['t_fin'] = num(X.finish); X['t_mar'] = num(X.margin); X['t_dist'] = num(X.distance)
has = lambda s: s.notna() & ~s.astype(str).str.strip().isin(['', '-', '0', 'nan', 'None'])
rows = []
for st, g in list(X.groupby('state')) + [('ALL', X)]:
    b = g.finish_pos.notna()
    r = {'state': st, 'tab_race_starts': len(g), 'in_breednet': int(b.sum()),
         'date_from': g.d.min(), 'date_to': g.d.max(),
         'tab_position_in_run': int(has(g.position_in_run).sum()), 'tab_stewards_comment': int(has(g.stewards_comment).sum()),
         'tab_track_condition': int(has(g.track_condition).sum()), 'tab_time': int(has(g.time).sum()), 'tab_rider': int(has(g.rider).sum()),
         'tab_class': int(has(g.tab_class).sum()), 'tab_starters': int(has(g.starters).sum()), 'tab_barrier_given': int(has(g.barrier).sum()),
         'finish_agrees_breednet': int((g.t_fin == g.finish_pos)[b].sum()), 'finish_compared': int((b & g.t_fin.notna()).sum()),
         'margin_within_0_1L': int(((g.t_mar - g.margin_l).abs() <= 0.1)[b & g.t_mar.notna() & g.margin_l.notna() & (g.t_fin > 1)].sum()),
         'margin_compared': int((b & g.t_mar.notna() & g.margin_l.notna() & (g.t_fin > 1)).sum()),
         'distance_agrees': int((g.t_dist == g.distance_m)[b].sum()),
         'barrier_held_elsewhere': int((g.q_barrier.notna() | g.n_barrier.notna() | g.sa_barrier.notna()).sum()),
         'positions_held_elsewhere_nsw800_400': int(g.pos800.notna().sum()),
         'breednet_last600': int(g.last600_s.notna().sum())}
    rows.append(r)
out = pd.DataFrame(rows); out.to_csv('ops/foundation/tab_form_overlap.csv', index=False)
pd.set_option('display.width', 250); print(out.T.to_string())
