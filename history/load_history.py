"""Queensland history load: read the year bundles saved by browser_bundle.js and build history.duckdb.

Run:   python3 load_history.py <folder with racing_rq_*.zip and racing_betfair_*.zip>
Out:   history.duckdb, out/*.csv (checks, coverage, gaps)

Betfair price columns were removed before the files were saved; none are read here.
"""
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
# Incremental mode (weekly job):  python3 load_history.py --incremental BUNDLE.zip [history.duckdb]
#   merges one new RQ bundle into an existing database: rows for each (date, track) in the bundle replace that meeting's
#   old rows in x_race / x_runner / x_sec / x_field / x_log; every other meeting and all Breednet / Betfair tables are left
#   untouched; then the canonical tables, checks and coverage are rebuilt from the x_ tables exactly as in a full load.
INCR = len(sys.argv) > 1 and sys.argv[1] == "--incremental"
if INCR:
    SRC = Path(sys.argv[2])
    DB = Path(sys.argv[3]) if len(sys.argv) > 3 else HERE / "history.duckdb"
    OUT = DB.parent / "out"
else:
    SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/mnt/user-data/uploads/Downloads")
    OUT = HERE / "out"
    DB = HERE / "history.duckdb"
    if DB.exists():
        DB.unlink()
OUT.mkdir(exist_ok=True)
con = duckdb.connect(str(DB))
TMP = Path(tempfile.mkdtemp(prefix="hist_"))

rq_bundles = [SRC] if INCR else sorted(SRC.glob("racing_rq_*.zip"))
bf_bundles = [] if INCR else sorted(SRC.glob("racing_betfair_*.zip"))
print("bundles:", [b.name for b in rq_bundles + bf_bundles])

# ---------------------------------------------------------------- unpack parsed files
parts = {k: [] for k in ["races", "runners", "secs", "fields", "log"]}
for b in rq_bundles:
    with zipfile.ZipFile(b) as z:
        for k in parts:
            name = f"parsed/{k}.psv"
            if name in z.namelist():
                dest = TMP / f"{b.stem}_{k}.psv"
                dest.write_bytes(z.read(name))
                parts[k].append(str(dest))
bf_files = []
bf_manifest = []
for b in bf_bundles:
    with zipfile.ZipFile(b) as z:
        for n in z.namelist():
            dest = TMP / f"{b.stem}__{Path(n).name}"
            dest.write_bytes(z.read(n))
            (bf_manifest if n == "MANIFEST.csv" else bf_files).append(str(dest))


def load_psv(table, files):
    if not files:
        con.execute(f"CREATE TABLE {table} (empty INTEGER)")
        return
    # Several bundles can hold the same meeting (yearly history + daily top-ups, or a re-fetch after
    # interim results). Keep each (date, track) only from the latest bundle: names sort yearly < daily, older < newer.
    con.execute(f"CREATE TABLE {table}_all AS SELECT * FROM read_csv({files!r}, delim='|', header=true, all_varchar=true, quote='', escape='', union_by_name=true, filename=true)")
    con.execute(f"""CREATE TABLE {table} AS SELECT * EXCLUDE (filename) FROM {table}_all t
                    WHERE filename = (SELECT max(u.filename) FROM {table}_all u WHERE u.date = t.date AND u.track = t.track)""")
    con.execute(f"DROP TABLE {table}_all")


def merge_psv(table, files):
    if not files:
        return
    con.execute(f"CREATE TEMP TABLE n_{table} AS SELECT * FROM read_csv({files!r}, delim='|', header=true, all_varchar=true, quote='', escape='', union_by_name=true)")
    if con.execute(f"SELECT count(*) FROM n_{table}").fetchone()[0]:
        con.execute(f"DELETE FROM {table} t WHERE EXISTS (SELECT 1 FROM n_{table} n WHERE n.date = t.date AND n.track = t.track)")
        con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM n_{table}")
    con.execute(f"DROP TABLE n_{table}")


if INCR:
    before = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ["x_race", "x_runner", "x_sec", "x_field"]}
    for t, k in [("x_race", "races"), ("x_runner", "runners"), ("x_sec", "secs"), ("x_field", "fields"), ("x_log", "log")]:
        merge_psv(t, parts[k])
    print("incremental:", {t: (before[t], con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in before})
    for t in ["race", "starter", "sectional", "venue_map", "checks", "coverage_qld", "coverage_betfair"]:
        con.execute(f"DROP TABLE IF EXISTS {t}")
else:
    load_psv("x_race", parts["races"])
    load_psv("x_runner", parts["runners"])
    load_psv("x_sec", parts["secs"])
    load_psv("x_field", parts["fields"])
    load_psv("x_log", parts["log"])
if INCR:
    pass
elif bf_files:
    con.execute(f"CREATE TABLE bf AS SELECT * FROM read_csv({bf_files!r}, header=true, all_varchar=true, union_by_name=true)")
    con.execute(f"CREATE TABLE bf_manifest AS SELECT * FROM read_csv({bf_manifest!r}, header=true, all_varchar=true, union_by_name=true)")
else:
    con.execute("CREATE TABLE bf (LOCAL_MEETING_DATE VARCHAR, TRACK VARCHAR, STATE_CODE VARCHAR, RACE_NO VARCHAR, DISTANCE VARCHAR, RACE_TYPE VARCHAR, SELECTION_ID VARCHAR, TAB_NUMBER VARCHAR, SELECTION_NAME VARCHAR, WIN_RESULT VARCHAR, PLACE_RESULT VARCHAR, SCHEDULED_RACE_TIME VARCHAR, ACTUAL_OFF_TIME VARCHAR)")

# ---------------------------------------------------------------- normalisation helpers (SQL)
con.execute(r"""
CREATE OR REPLACE MACRO norm_name(n) AS upper(regexp_replace(regexp_replace(regexp_replace(trim(n), '\s*\([A-Z]{2,3}\)\s*$', ''), '[''’]', '', 'g'), '\s+', ' ', 'g'));
CREATE OR REPLACE MACRO iso(d) AS strptime(d, '%Y%m%d')::DATE;
CREATE OR REPLACE MACRO bf_date(d) AS coalesce(try_strptime(d, '%Y-%m-%d'), try_strptime(d, '%d/%m/%Y'))::DATE;
CREATE OR REPLACE MACRO bf_time(t) AS coalesce(try_strptime(t, '%H:%M:%S.%f'), try_strptime(t, '%H:%M:%S'), try_strptime(t, '%I:%M:%S %p'))::TIME;
""")

con.execute("""
CREATE OR REPLACE TABLE bf_runner AS
SELECT bf_date(LOCAL_MEETING_DATE) meeting_date, TRACK bf_track, STATE_CODE state, RACE_NO::INT race_no, try_cast(DISTANCE AS INT) distance_m,
       RACE_TYPE race_type, SELECTION_ID selection_id, try_cast(TAB_NUMBER AS INT) saddlecloth, SELECTION_NAME name, norm_name(SELECTION_NAME) name_key,
       WIN_RESULT='WINNER' win_flag, PLACE_RESULT='WINNER' place_flag, bf_time(SCHEDULED_RACE_TIME) scheduled, bf_time(ACTUAL_OFF_TIME) actual_off,
       LOCAL_MEETING_DATE AS date_raw
FROM bf WHERE coalesce(RACING_TYPE, 'Thoroughbred') = 'Thoroughbred'
""")

# ---------------------------------------------------------------- venue mapping: RQ track -> Betfair TRACK (by shared dates)
con.execute("""
CREATE TABLE venue_map AS
WITH rq AS (SELECT DISTINCT track, iso(date) AS d FROM x_race),
     b AS (SELECT DISTINCT bf_track, meeting_date AS d FROM bf_runner WHERE state = 'QLD'),
     m AS (SELECT rq.track, b.bf_track, count(*) n FROM rq JOIN b USING (d) GROUP BY 1,2),
     tot AS (SELECT track, count(*) n_dates FROM rq GROUP BY 1)
SELECT m.track, m.bf_track, m.n AS shared_dates, tot.n_dates,
       row_number() OVER (PARTITION BY m.track ORDER BY m.n DESC) AS rk
FROM m JOIN tot USING (track)
QUALIFY rk = 1
""")

# ---------------------------------------------------------------- canonical tables
con.execute("""
CREATE TABLE race AS
WITH f AS (SELECT date, track, race_no::INT race_no, any_value(race_name) race_name_f, any_value(distance_m)::INT distance_m, any_value(start_time) start_time
           FROM x_field GROUP BY 1,2,3)
SELECT iso(r.date) AS meeting_date, r.track, r.race_no::INT AS race_no,
       r.date || '-' || r.track || '-R' || r.race_no AS race_id,
       coalesce(f.race_name_f, r.race_name) AS race_name, f.distance_m, f.start_time,
       r.track_condition AS track_rating_tracking, r.rail, r.meeting_code, r.race_code,
       (SELECT min(finish_time_s::DOUBLE) FROM x_runner u WHERE u.date=r.date AND u.track=r.track AND u.race_no=r.race_no AND u.final_rank='1') AS race_time_s
FROM x_race r LEFT JOIN f ON f.date=r.date AND f.track=r.track AND f.race_no=r.race_no::INT
""")
con.execute("""
CREATE TABLE starter AS
SELECT iso(u.date) AS meeting_date, u.track, u.race_no::INT race_no, u.date || '-' || u.track || '-R' || u.race_no AS race_id,
       u.bib::INT AS saddlecloth, u.name, norm_name(u.name) AS name_key, u.horse_code,
       u.result_state = 'DidNotStart' AS scratched,
       CASE WHEN u.result_state='DidNotStart' THEN NULL ELSE try_cast(u.final_rank AS INT) END AS finish_pos,
       CASE WHEN u.result_state='DidNotStart' THEN NULL ELSE try_cast(u.official_margin AS DOUBLE) END AS margin_l,
       CASE WHEN u.result_state='DidNotStart' THEN NULL ELSE try_cast(u.finish_time_s AS DOUBLE) END AS finish_time_s,
       try_cast(u.dist_travelled AS INT) AS ground_m, u.result_state, u.result_substate,
       try_cast(f.barrier AS INT) barrier, try_cast(f.weight_kg AS DOUBLE) weight_kg,
       regexp_replace(f.jockey, '^Ms ', '') jockey, f.trainer, f.emergency = 'EM' AS emergency, f.horse AS name_fields
FROM x_runner u
LEFT JOIN x_field f ON f.date=u.date AND f.track=u.track AND f.race_no::INT=u.race_no::INT AND try_cast(f.tab AS INT)=u.bib::INT
""")
con.execute("""
CREATE TABLE sectional AS
SELECT s.date || '-' || s.track || '-R' || s.race_no AS race_id, s.bib::INT saddlecloth, s.cum_dist::INT segment_end_m,
       try_cast(s.real_dist AS DOUBLE) ground_m, try_cast(s.rank AS INT) position, try_cast(s.inter_s AS DOUBLE) inter_s,
       try_cast(s.section_s AS DOUBLE) split_s, try_cast(s.avg_speed AS DOUBLE) avg_speed_ms, try_cast(s.top_speed AS DOUBLE) top_speed_ms,
       try_cast(s.stride_freq AS DOUBLE) stride_freq_hz, try_cast(s.stride_len AS DOUBLE) stride_len_m, try_cast(s.dist_rail AS DOUBLE) dist_to_rail_m
FROM x_sec s
""")

# ---------------------------------------------------------------- checks at scale
checks = []


def q1(sql):
    return con.execute(sql).fetchone()


def add(cid, desc, expected, observed, status):
    checks.append((cid, desc, str(expected), str(observed), status))


bad_d, bad_t, n_bf = q1("SELECT count(*) FILTER (WHERE meeting_date IS NULL), count(*) FILTER (WHERE actual_off IS NULL AND scheduled IS NULL), count(*) FROM bf_runner")
odd, = q1("SELECT count(*) FROM bf_runner WHERE date_raw NOT LIKE '____-__-__'")
add("B1", "Betfair rows with a readable date and time", n_bf, f"{n_bf-bad_d} dates, {n_bf-bad_t} times; {odd} rows in day-first format (Apr 2025 file)", "PASS" if bad_d == 0 else "FLAG")
n_meet, = q1("SELECT count(DISTINCT date||track) FROM x_log")
zip_ok, = q1("SELECT count(*) FROM x_log WHERE kind='sectional_zip' AND http_status='200'")
rf_ok, = q1("SELECT count(*) FROM x_log WHERE kind='race_fields_pdf' AND http_status='200'")
perr, = q1("SELECT count(*) FROM x_log WHERE kind LIKE 'parse_error%'")
add("K1", "Meetings with a tracking ZIP fetched", n_meet, zip_ok, "PASS" if zip_ok == n_meet else "FLAG")
add("K2", "Meetings with a Race Fields PDF fetched", n_meet, rf_ok, "PASS" if rf_ok == n_meet else "FLAG")
add("K3", "Files that failed to parse", 0, perr, "PASS" if perr == 0 else "FLAG")

r = q1("""
WITH a AS (SELECT race_id, list_sort(list(saddlecloth) FILTER (WHERE NOT scratched)) s FROM starter GROUP BY 1),
     b AS (SELECT date||'-'||track||'-R'||race_no race_id, list_sort(list(try_cast(tab AS INT))) s FROM x_field GROUP BY 1)
SELECT count(*), count(*) FILTER (WHERE a.s = b.s) FROM a JOIN b USING (race_id)""")
add("K4", "Races where tracking starters = Race Fields runners (same saddlecloths)", r[0], r[1], "PASS" if r[0] == r[1] else "FLAG")
r = q1("""
WITH t AS (SELECT race_id, saddlecloth, sum(split_s) tot FROM sectional GROUP BY 1,2)
SELECT count(*), count(*) FILTER (WHERE abs(t.tot - s.finish_time_s) <= 0.05) FROM t JOIN starter s USING (race_id, saddlecloth)""")
add("K5", "Starters whose segment times add to the official time (±0.05s)", r[0], r[1], "PASS" if r[0] == r[1] else "FLAG")
r = q1("""
WITH rq AS (SELECT r.race_id, r.meeting_date, v.bf_track, r.race_no, r.distance_m,
                   (SELECT count(*) FROM starter s WHERE s.race_id=r.race_id AND NOT s.scratched) n_start,
                   (SELECT any_value(saddlecloth) FROM starter s WHERE s.race_id=r.race_id AND s.finish_pos=1) winner
            FROM race r JOIN venue_map v USING (track)),
     b AS (SELECT meeting_date, bf_track, race_no, count(*) n, any_value(saddlecloth) FILTER (WHERE win_flag) bwin, any_value(distance_m) bdist
           FROM bf_runner WHERE state='QLD' GROUP BY 1,2,3)
SELECT count(*), count(b.n), count(*) FILTER (WHERE b.n = rq.n_start), count(*) FILTER (WHERE b.bwin = rq.winner), count(*) FILTER (WHERE b.bdist = rq.distance_m)
FROM rq LEFT JOIN b USING (meeting_date, bf_track, race_no)""")
add("K6", "Tracked Qld races found in Betfair", r[0], r[1], "PASS" if r[0] == r[1] else "FLAG")
add("K7", "Matched races: Betfair runners = tracking starters", r[1], r[2], "PASS" if r[1] == r[2] else "FLAG")
add("K8", "Matched races: Betfair winner = tracking rank 1", r[1], r[3], "PASS" if r[1] == r[3] else "FLAG")
add("K9", "Matched races: Betfair distance = Race Fields distance", r[1], r[4], "PASS" if r[1] == r[4] else "FLAG")
r = q1("SELECT count(*), count(*) FILTER (WHERE s.barrier = s.saddlecloth) FROM starter s WHERE NOT scratched AND barrier IS NOT NULL")
add("K10", "Barrier differs from saddlecloth (tracking draw field not used)", r[0], f"{r[0]-r[1]} differ, {r[1]} equal", "PASS")
r = q1("""SELECT count(*) FROM (SELECT name_key FROM starter WHERE horse_code NOT LIKE 'AUS-%' GROUP BY 1 HAVING count(DISTINCT horse_code) > 1)""")
add("H1", "Names carrying more than one numeric RQ horse code (different horses sharing a name)", 0, r[0], "PASS" if r[0] == 0 else "FLAG")
r = q1("SELECT min(meeting_date), max(meeting_date), count(DISTINCT meeting_date::VARCHAR||track) FROM starter WHERE horse_code LIKE 'AUS-%'")
add("H2", "Meetings using the AUS- horse code instead of the numeric code", 0, f"{r[2]} meetings, {r[0]} to {r[1]}", "FLAG" if r[2] else "PASS")
r = q1("""
WITH pre AS (SELECT name_key, any_value(horse_code) c FROM starter WHERE horse_code NOT LIKE 'AUS-%' AND meeting_date < (SELECT coalesce(min(meeting_date), DATE '2100-01-01') FROM starter WHERE horse_code LIKE 'AUS-%') GROUP BY 1 HAVING count(DISTINCT horse_code)=1),
     post AS (SELECT name_key, any_value(horse_code) c FROM starter WHERE horse_code NOT LIKE 'AUS-%' AND meeting_date > (SELECT coalesce(max(meeting_date), DATE '1900-01-01') FROM starter WHERE horse_code LIKE 'AUS-%') GROUP BY 1 HAVING count(DISTINCT horse_code)=1)
SELECT count(*), count(*) FILTER (WHERE pre.c = post.c) FROM pre JOIN post USING (name_key)""")
add("H3", "Horses keeping the same numeric code either side of the AUS- period", r[0], r[1], "PASS" if r[0] - r[1] <= max(1, r[0] // 500) else "FLAG")
r = q1("""
WITH rq AS (SELECT r.race_id, r.meeting_date, v.bf_track, r.race_no, list(s.saddlecloth) FILTER (WHERE s.finish_pos=1) w FROM race r JOIN venue_map v USING (track) JOIN starter s USING (race_id) GROUP BY ALL),
     b AS (SELECT meeting_date, bf_track, race_no, list(saddlecloth) FILTER (WHERE win_flag) bw FROM bf_runner WHERE state='QLD' GROUP BY ALL)
SELECT count(*) FILTER (WHERE list_sort(w) <> list_sort(bw)), count(*) FILTER (WHERE list_sort(w) <> list_sort(bw) AND (len(w)>1 OR len(bw)>1)) FROM rq JOIN b USING (meeting_date, bf_track, race_no)""")
add("K8b", "Winner mismatches explained by dead heats", r[0], r[1], "PASS" if r[0] - r[1] <= 5 else "FLAG")
r = q1("""
SELECT year(meeting_date), count(DISTINCT meeting_date::VARCHAR||bf_track), count(DISTINCT meeting_date::VARCHAR||bf_track) FILTER (WHERE bf_track NOT IN (SELECT bf_track FROM venue_map))
FROM bf_runner WHERE state='QLD' AND year(meeting_date)=2025 GROUP BY 1""")
if r:
    add("D1", "Qld meetings in Betfair 2025 at venues with no RQ tracking (country/picnic history comes from Betfair only)", "-", f"{r[2]} of {r[1]}", "FLAG")
else:
    add("D1", "Qld meetings in Betfair 2025 at venues with no RQ tracking", "-", "no 2025 Betfair data in this load", "SKIP")
con.execute("CREATE TABLE checks (id VARCHAR, description VARCHAR, expected VARCHAR, observed VARCHAR, status VARCHAR)")
con.executemany("INSERT INTO checks VALUES (?,?,?,?,?)", checks)

# ---------------------------------------------------------------- coverage
con.execute("""
CREATE TABLE coverage_qld AS
SELECT year(meeting_date) AS yr, track, count(DISTINCT meeting_date) meetings, count(DISTINCT race_id) races,
       count(*) FILTER (WHERE NOT scratched) starters,
       round(100.0 * count(barrier) FILTER (WHERE NOT scratched) / nullif(count(*) FILTER (WHERE NOT scratched),0), 1) pct_barrier_weight,
       round(100.0 * count(finish_pos) / nullif(count(*) FILTER (WHERE NOT scratched),0), 1) pct_result
FROM starter GROUP BY 1,2 ORDER BY 1,2""")
con.execute("""
CREATE TABLE coverage_betfair AS
SELECT year(meeting_date) AS yr, state, count(DISTINCT meeting_date::VARCHAR||bf_track) meetings, count(DISTINCT meeting_date::VARCHAR||bf_track||race_no::VARCHAR) races, count(*) runners
FROM bf_runner GROUP BY 1,2 ORDER BY 1,2""")

for t in ["checks", "coverage_qld", "coverage_betfair", "venue_map"]:
    con.execute(f"COPY {t} TO '{OUT / (t + '.csv')}' (HEADER)")
print("checks:")
for row in con.execute("SELECT * FROM checks").fetchall():
    print("  ", " | ".join(row))
print("tables:", {t: q1(f"SELECT count(*) FROM {t}")[0] for t in ["race", "starter", "sectional", "bf_runner"]})
con.close()
