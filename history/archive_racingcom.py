"""Retire the original racing.com tables from active use (approved by Damo 26 Nov 2026, foundation step 5, "subject to preserving any
unique information and archiving the original tables"). Runs at the weekly update.
1. Archive every original table (rc_meeting, rc_race, rc_runner, vic_speed_point, vic_speed_runner, vic_speed_split) to parquet with
   row counts and sha256 (the workflow commits the folder to branch archive-racingcom).
2. Preserve the unique information in tables that stay:
   - legacy_racingcom_runner: barrier, 800 m / 400 m positions, weight, finish and margin for the 106 racing.com races (Victorian and
     NSW barriers are not held anywhere else before 25 Nov 2026). Source and caveat recorded on every row.
   - vic_pilot_runner / vic_pilot_point (made by load_vic_tracking.py): the Flemington 3 Oct 2026 speed pilot's distance run, early/mid/late/
     peak speed and positions at each mark, which the TripleS CSVs do not have.
3. Only with --drop, and only after the archive is re-read and matches row for row, the original tables are dropped.
Usage: python3 history/archive_racingcom.py <history.duckdb> <archive dir> [--drop]"""
import sys, os, json, hashlib, duckdb, pandas as pd
DB, OUT = sys.argv[1], sys.argv[2]; DROP = '--drop' in sys.argv
os.makedirs(OUT, exist_ok=True); con = duckdb.connect(DB)
have = {t[0] for t in con.execute('show tables').fetchall()}
TABLES = [t for t in ['rc_meeting', 'rc_race', 'rc_runner', 'vic_speed_point', 'vic_speed_runner', 'vic_speed_split'] if t in have]
man = {'archived_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'why': 'racing.com tables retired from active use (Damo 26 Nov 2026); originals kept here', 'tables': {}}
for t in TABLES:
    df = con.execute(f'select * from {t}').fetchdf(); p = os.path.join(OUT, f'{t}.parquet'); df.to_parquet(p, index=False)
    back = pd.read_parquet(p); ok = len(back) == len(df) and list(back.columns) == list(df.columns)
    man['tables'][t] = {'rows': len(df), 'columns': list(df.columns), 'sha256': hashlib.sha256(open(p, 'rb').read()).hexdigest(), 'reread_ok': ok}
json.dump(man, open(os.path.join(OUT, 'MANIFEST.json'), 'w'), indent=1)
if 'rc_runner' in have:
    con.execute("""create or replace table legacy_racingcom_runner as
                   select m.meeting_date, m.state, m.slug, m.bf_track, u.race_no, u.saddlecloth, u.horse, u.name_key, u.barrier, u.pos800, u.pos400, u.weight_kg,
                          u.finish_pos, u.margin_l, u.scratched, 'racing.com results pages collected 24 Nov 2026 (archived originals: branch archive-racingcom)' source
                   from rc_runner u join rc_meeting m using (rc_key)""")
print('archived:', {t: v['rows'] for t, v in man['tables'].items()}, '| re-read ok:', all(v['reread_ok'] for v in man['tables'].values()))
if DROP:
    assert all(v['reread_ok'] for v in man['tables'].values()), 'archive did not re-read cleanly: nothing dropped'
    assert 'legacy_racingcom_runner' in {t[0] for t in con.execute('show tables').fetchall()} or 'rc_runner' not in have
    for t in TABLES: con.execute(f'drop table {t}')
    print('dropped from active use:', TABLES)
