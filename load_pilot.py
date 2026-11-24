"""National data pilot (rerun on exact files): load permitted records into the common schema and run checks.

Run:   python3 load_pilot.py          (needs: pip install duckdb)
Input: exact/  - byte-identical copies or hash-verified extracts of the source files (see exact/manifest.psv)
       raw_transcribed/  - the first run's transcriptions, used only to confirm they were right
Output: pilot.duckdb and out/*.csv

No price, odds or volume columns are read from any source.
"""
import hashlib
import re
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
EX = HERE / "exact"
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
DB = HERE / "pilot.duckdb"
if DB.exists():
    DB.unlink()
con = duckdb.connect(str(DB))
con.execute((HERE / "schema.sql").read_text())
checks = []


def chk(cid, scope, desc, expected, observed, status):
    checks.append((cid, scope, desc, str(expected), str(observed), status))


def psv(path, base=EX):
    lines = [l for l in (base / path).read_text().splitlines() if l and not l.startswith("#")]
    head = lines[0].split("|")
    return [dict(zip(head, l.split("|"))) for l in lines[1:]]


def tsec(t):
    """'1:31.18' / '00:00:11.73' / '91.18' -> seconds."""
    if t in (None, ""):
        return None
    s = 0.0
    for p in str(t).split(":"):
        s = s * 60 + float(p)
    return round(s, 3)


def norm(name):
    """Matching key: upper case, no country suffix, no apostrophes, single spaces."""
    n = re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", name.strip())
    n = n.replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", n).upper()


# ---------------------------------------------------------------- M: file integrity
manifest = psv("manifest.psv")
for m in manifest:
    if m["local_sha256"]:
        got = hashlib.sha256((EX / m["local_file"]).read_bytes()).hexdigest()
        chk("M1", m["local_file"], "Local file hash = hash recorded when it was taken from the browser",
            m["local_sha256"][:12], got[:12], "PASS" if got == m["local_sha256"] else "FAIL")

# ---------------------------------------------------------------- sources & retrievals
RQ_OD = "https://www.racingqueensland.com.au/industry/thoroughbred/thoroughbred-sectionals"
con.executemany("INSERT INTO source VALUES (?,?,?,?,?,?,?,?)", [
    ("RQ_SECTIONAL_CSV", "Racing Queensland / tripleSdata", "Per-meeting sectional CSV (splits, top speed per segment)",
     "unconfirmed", "unconfirmed", "unconfirmed", "Listed as open licence in RQ open data catalogue; no notice inside the file", RQ_OD),
    ("RQ_SECTIONAL_XML", "Racing Queensland / tripleSdata", "Per-meeting ZIP of race XML: finish rank, official margins, finish times, ground covered, positions, stride data",
     "unconfirmed", "unconfirmed", "unconfirmed", "As above", RQ_OD),
    ("RQ_RACE_FIELDS_PDF", "Racing Queensland", "Race Fields PDF: barrier, weight, jockey, trainer",
     "granted (per Damo, 24 Nov 2026)", "granted (per Damo, 24 Nov 2026)", "derived_only", "Notice inside PDF requires RQ's prior written permission. Permission given to Damo by RQ (an existing contact) on 24 Nov 2026; written confirmation requested",
     "https://www.racingqueensland.com.au/racing/full-calendar"),
    ("RQ_FORM_GUIDE_PDF", "Racing Queensland", "Form guide PDF: last runs, career splits, stewards comments (contains prices; inspected only)",
     "unconfirmed", "not stored", "no", "Copy served today is regenerated after the meeting", "https://www.racingqueensland.com.au/racing/full-calendar"),
    ("RQ_MEETING_PAGES", "Racing Queensland", "Race pages and stewards reports",
     "unconfirmed", "unconfirmed", "unconfirmed", "Stewards reports may be amended at any time", "https://www.racingqueensland.com.au/racing"),
    ("BETFAIR_MONTHLY", "Betfair Australia", "ANZ thoroughbred monthly CSV (non-price columns only)",
     "yes (published for download)", "unconfirmed (no licence stated)", "unconfirmed", "No licence stated; no-warranty disclaimer",
     "https://betfair-datascientists.github.io/data/dataListing"),
])
for i, m in enumerate(manifest, 1):
    con.execute("INSERT INTO retrieval VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
        f"X{i}", m["source_id"], m["source_url"], m["method"], m["exact_copy"] == "true",
        m["retrieved_utc"].replace("T", " ").rstrip("Z"),
        m["publisher_last_modified"].replace("T", " ").rstrip("Z") or None,
        m["source_sha256"] or None, int(m["source_bytes"]) if m["source_bytes"] else None,
        m["local_file"], m["local_sha256"] or None, m["note"]))

# ---------------------------------------------------------------- venues & meetings
con.executemany("INSERT INTO venue VALUES (?,?,?,?)", [
    ("QLD-EAGLE-FARM", "QLD", "Eagle Farm", "Brisbane Racing Club"),
    ("VIC-FLEMINGTON", "VIC", "Flemington", "Victoria Racing Club"),
    ("NSW-RANDWICK", "NSW", "Randwick", "Australian Turf Club"),
])
con.executemany("INSERT INTO venue_alias VALUES (?,?,?)", [
    ("BETFAIR_MONTHLY", "Eagle Farm", "QLD-EAGLE-FARM"),
    ("RQ_SECTIONAL_CSV", "Eagle_Farm (file name)", "QLD-EAGLE-FARM"),
    ("RQ_SECTIONAL_CSV", "EAGL_*_TRACK (course code)", "QLD-EAGLE-FARM"),
    ("RQ_SECTIONAL_XML", "Eagle Farm (CourseName)", "QLD-EAGLE-FARM"),
    ("RQ_RACE_FIELDS_PDF", "E_FM (file name)", "QLD-EAGLE-FARM"),
    ("RQ_MEETING_PAGES", "e fm (URL)", "QLD-EAGLE-FARM"),
    ("RQ_FORM_GUIDE_PDF", "E FM (form lines)", "QLD-EAGLE-FARM"),
    ("BETFAIR_MONTHLY", "Flemington", "VIC-FLEMINGTON"),
    ("BETFAIR_MONTHLY", "Randwick", "NSW-RANDWICK"),
])
con.executemany("INSERT INTO meeting VALUES (?,?,?,?,?,?,?)", [
    ("20261003-QLD-EAGLE-FARM", "2026-10-03", "QLD-EAGLE-FARM", "metro", "Turf", "+4.5m", "Fine"),
    ("20261003-VIC-FLEMINGTON", "2026-10-03", "VIC-FLEMINGTON", "metro", None, None, None),
    ("20261003-NSW-RANDWICK", "2026-10-03", "NSW-RANDWICK", "metro", None, None, None),
    ("20260404-QLD-EAGLE-FARM", "2026-04-04", "QLD-EAGLE-FARM", "metro", None, None, None),
])
VID = {"Eagle Farm": "QLD-EAGLE-FARM", "Flemington": "VIC-FLEMINGTON", "Randwick": "NSW-RANDWICK"}

# ---------------------------------------------------------------- load source files
xr = {int(r["race_no"]): r for r in psv("rq/rq_xml_races.psv")}
xrun = psv("rq/rq_xml_runners.psv")
xsec = psv("rq/rq_xml_sections.psv")
rf = {(int(r["race_no"]), int(r["tab"])): r for r in psv("rq/rq_racefields_pdf.psv")}
bfr = psv("betfair/bf_20261003_races.psv")
bfu = psv("betfair/bf_20261003_runners.psv")

csv_rows = {}  # (race, tab) -> (name, [(cum, speed, split)])
for line in (EX / "rq/20261003_Eagle_Farm_T.csv").read_text().splitlines():
    if not line or line.startswith("Date,"):
        continue
    _, rno, rest = line.split(",", 2)
    f = rest.split(";")
    segs = [(int(f[i]), float(f[i + 1]), tsec(f[i + 2])) for i in range(2, len(f), 3)]
    csv_rows[(int(rno), int(f[1]))] = (f[0], segs)

secs_by = {}
for s in xsec:
    secs_by.setdefault((int(s["race_no"]), int(s["bib"])), []).append(s)
for v in secs_by.values():
    v.sort(key=lambda s: int(s["cum_dist"]))

# Official rating per race (stewards report): Soft 5 R1-5, upgraded to Good 4 at 2:07pm after R5
STEWARDS_RATING = {n: ("Soft 5" if n <= 5 else "Good 4") for n in range(1, 11)}


def class_code(name):
    n = name.lower()
    m = re.search(r"benchmark (\d+)", n)
    if m:
        return f"BM{m.group(1)}"
    if "class 3" in n:
        return "CL3"
    if "one metro win" in n:
        return "RESTRICTED-HCP"
    if "open handicap" in n:
        return "OPEN-HCP"
    if "three-year-old handicap" in n:
        return "3YO-HCP"
    return "HCP" if "handicap" in n else None


def to24(t):
    """'01:23PM' -> '13:23:00'"""
    h, m = int(t[:2]), int(t[3:5])
    if t.endswith("PM") and h != 12:
        h += 12
    if t.endswith("AM") and h == 12:
        h = 0
    return f"{h:02d}:{m:02d}:00"


# ---------------------------------------------------------------- races
bf_race = {(r["TRACK"], int(r["RACE_NO"])): r for r in bfr}
for n, r in sorted(xr.items()):
    rid = f"20261003-QLD-EAGLE-FARM-R{n}"
    field = [v for k, v in rf.items() if k[0] == n]
    winner = [x for x in xrun if int(x["race_no"]) == n and x["final_rank"] == "1"]
    b = bf_race[("Eagle Farm", n)]
    con.execute("INSERT INTO race VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        rid, "20261003-QLD-EAGLE-FARM", n, r["race_name"], int(field[0]["distance_m"]), r["race_name"],
        class_code(r["race_name"]), to24(field[0]["start_time"]), b["ACTUAL_OFF_TIME"][:8], None,
        float(winner[0]["finish_time_s"]), STEWARDS_RATING[n], r["track_condition"]))
for r in bfr:
    if r["TRACK"] == "Eagle Farm":
        continue
    vid = VID[r["TRACK"]]
    con.execute("INSERT INTO race VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        f"20261003-{vid}-R{r['RACE_NO']}", f"20261003-{vid}", int(r["RACE_NO"]), None, int(r["DISTANCE"]),
        f"Betfair RACE_TYPE={r['RACE_TYPE']}", None, r["SCHEDULED_RACE_TIME"][:8], r["ACTUAL_OFF_TIME"][:8],
        None, None, None, None))
con.execute("INSERT INTO race VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
    "20260404-QLD-EAGLE-FARM-R1", "20260404-QLD-EAGLE-FARM", 1, "SOUTHS SPORTS CLUB QTIS Two-Year-Old Handicap",
    1300, "SOUTHS SPORTS CLUB QTIS Two-Year-Old Handicap", "2YO-HCP", None, None, None, None, None, "Soft 5"))

# ---------------------------------------------------------------- horses
horse_ids = {}


def horse(name, suffix=None):
    key = norm(name)
    if key not in horse_ids:
        hid = f"H{len(horse_ids) + 1:04d}"
        horse_ids[key] = hid
        con.execute("INSERT INTO horse VALUES (?,?,?,?,?,?,?)", (hid, re.sub(r"\s*\([A-Z]{2,3}\)\s*$", "", name.strip()), suffix, None, None, None, None))
    return horse_ids[key]


# ---------------------------------------------------------------- Eagle Farm starters & sectionals
for x in xrun:
    n, tab = int(x["race_no"]), int(x["bib"])
    rid = f"20261003-QLD-EAGLE-FARM-R{n}"
    f = rf.get((n, tab))
    suffix = re.search(r"\(([A-Z]{2,3})\)$", f["horse"]).group(1) if f and re.search(r"\(([A-Z]{2,3})\)$", f["horse"]) else None
    hid = horse(x["name"], suffix)
    scratched = x["result_state"] == "DidNotStart"
    segs = secs_by.get((n, tab), [])
    last600 = round(sum(float(s["section_s"]) for s in segs[-3:]), 2) if segs else None
    at400 = [s for s in segs if s["cum_dist"] == "400"]
    con.execute("INSERT INTO starter VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        rid, tab, hid,
        int(f["barrier"]) if f else None, float(f["weight_kg"]) if f else None,
        re.sub(r"^Ms ", "", f["jockey"]) if f else None, f["trainer"] if f else None,
        scratched, (f["emergency"] == "EM") if f else None,
        None if scratched else int(x["final_rank"]),
        None if scratched else float(x["official_margin"]),
        None if scratched else float(x["finish_time_s"]),
        None if scratched else int(x["dist_travelled"]),
        float(at400[0]["inter_s"]) if at400 else None, last600,
        round(max(float(s["top_speed"]) for s in segs) * 3.6, 2) if segs else None))
    con.execute("INSERT INTO horse_alias VALUES (?,?,?,?,?,?,?)",
                ("RQ_SECTIONAL_XML", x["horse_code"], x["name"], hid, "race+saddlecloth+name", "high", "HorseCode stable within the meeting only"))
    if f:
        con.execute("INSERT INTO horse_alias VALUES (?,?,?,?,?,?,?)",
                    ("RQ_RACE_FIELDS_PDF", None, f["horse"], hid, "race+saddlecloth+name", "high", None))
    prev = 0
    dist = int(rf[(n, next(t for (r_, t) in rf if r_ == n))]["distance_m"])
    for s in segs:
        cum = int(s["cum_dist"])
        con.execute("INSERT INTO sectional VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rid, tab, cum, cum - prev, float(s["section_s"]), float(s["top_speed"]), float(s["avg_speed"]),
            float(s["real_dist"]), int(s["rank"]), float(s["dist_rail"]), float(s["stride_freq"]),
            float(s["stride_len"]), "tripleSdata"))
        if dist - cum > 0:
            con.execute("INSERT INTO position_in_run VALUES (?,?,?,?)", (rid, tab, dist - cum, int(s["rank"])))
        prev = cum

# Murkado's April run (from notes_from_pages.txt; exact ZIP hash recorded there)
mk = horse("Murkado")
con.execute("INSERT INTO starter (race_id, saddlecloth, horse_id, scratched, finish_pos, margin_l, finish_time_s, dist_run_m) VALUES (?,?,?,?,?,?,?,?)",
            ("20260404-QLD-EAGLE-FARM-R1", 5, mk, False, 3, 1.22, 77.45, 1319))
con.execute("INSERT INTO horse_alias VALUES (?,?,?,?,?,?,?)",
            ("RQ_SECTIONAL_XML", "AUS-AN-2NT1PVH04", "Murkado", mk, "name+state+age (codes differ)", "medium",
             "Same name, Qld, 2yo in Apr -> 3yo in Oct; tripleS HorseCode changed from AUS-AN-2NT1PVH04 to 5370365"))

# ---------------------------------------------------------------- Betfair: NSW/VIC starters, all outcome flags
for u in bfu:
    vid = VID[u["TRACK"]]
    rid = f"20261003-{vid}-R{u['RACE_NO']}"
    tab = int(u["TAB_NUMBER"])
    hid = horse(u["SELECTION_NAME"])
    if vid != "QLD-EAGLE-FARM":
        con.execute("INSERT INTO starter (race_id, saddlecloth, horse_id, scratched) VALUES (?,?,?,?)", (rid, tab, hid, False))
    con.execute("INSERT INTO outcome_flag VALUES (?,?,?,?,?,?)",
                (rid, tab, "BETFAIR_MONTHLY", u["SELECTION_ID"], u["WIN_RESULT"] == "WINNER", u["PLACE_RESULT"] == "WINNER"))
    con.execute("INSERT INTO horse_alias VALUES (?,?,?,?,?,?,?)", (
        "BETFAIR_MONTHLY", u["SELECTION_ID"], u["SELECTION_NAME"], hid,
        "race+saddlecloth+name" if vid == "QLD-EAGLE-FARM" else "race+saddlecloth (single source)",
        "high" if vid == "QLD-EAGLE-FARM" else "unverified", "SELECTION_ID follows the name, not the horse"))

# ---------------------------------------------------------------- J: joins (Eagle Farm, three sources)
bf_by = {}
for u in bfu:
    bf_by.setdefault((u["TRACK"], int(u["RACE_NO"])), {})[int(u["TAB_NUMBER"])] = u
tot = {"starters": 0, "name_ok": 0}
for n in range(1, 11):
    xs = [x for x in xrun if int(x["race_no"]) == n]
    started = {int(x["bib"]): x for x in xs if x["result_state"] != "DidNotStart"}
    dns = {int(x["bib"]) for x in xs if x["result_state"] == "DidNotStart"}
    field = {t for (r_, t) in rf if r_ == n}
    bf = bf_by[("Eagle Farm", n)]
    chk("J1", f"EF R{n}", "Starters: tracking XML = Race Fields PDF = Betfair", len(started), f"{len(field)} / {len(bf)}",
        "PASS" if set(started) == field == set(bf) else "FAIL")
    chk("J2", f"EF R{n}", "Betfair distance = RQ distance", rf[(n, min(field))]["distance_m"], bf_race[("Eagle Farm", n)]["DISTANCE"],
        "PASS" if rf[(n, min(field))]["distance_m"] == bf_race[("Eagle Farm", n)]["DISTANCE"] else "FAIL")
    official = class_code(xr[n]["race_name"])
    btype = bf_race[("Eagle Farm", n)]["RACE_TYPE"]
    chk("J3", f"EF R{n}", "Betfair RACE_TYPE keeps the class detail", official, btype, "PASS" if btype.upper() == official.upper() else "FLAG")
    ok = 0
    for t, x in started.items():
        names = {norm(x["name"]), norm(rf[(n, t)]["horse"]) if (n, t) in rf else None, norm(bf[t]["SELECTION_NAME"]) if t in bf else None}
        ok += len(names) == 1
    tot["starters"] += len(started)
    tot["name_ok"] += ok
    chk("J4", f"EF R{n}", "Same horse at same saddlecloth in all three sources (normalised name)", len(started), ok,
        "PASS" if ok == len(started) else "FAIL")
    chk("J6", f"EF R{n}", "Non-starters absent from Betfair and Race Fields PDF", "0 present",
        f"{len(dns & set(bf))} / {len(dns & field)} present", "PASS" if not (dns & set(bf)) and not (dns & field) else "FAIL")
    winners = {t for t, u in bf.items() if u["WIN_RESULT"] == "WINNER"}
    k = sum(u["PLACE_RESULT"] == "WINNER" for u in bf.values())
    placed = {t for t, u in bf.items() if u["PLACE_RESULT"] == "WINNER"}
    topk = {t for t, x in started.items() if int(x["final_rank"]) <= k}
    top1 = {t for t, x in started.items() if x["final_rank"] == "1"}
    chk("J5", f"EF R{n}", f"Betfair win flag = rank 1; place flags = top {k} ranks ({len(started)} starters)",
        f"{sorted(top1)} / {sorted(topk)}", f"{sorted(winners)} / {sorted(placed)}",
        "PASS" if winners == top1 and placed == topk else "FAIL")

# J7: race page results list (Race 1) vs Race Fields PDF jockey/trainer
page_r1 = {}
for line in (EX / "rq/notes_from_pages.txt").read_text().splitlines():
    if line.startswith("results_r1="):
        pos, tab, nm, tr, jk = line.split("=", 1)[1].split("|")
        page_r1[int(tab)] = (tr, jk)
ok = sum(1 for t, (tr, jk) in page_r1.items() if rf[(1, t)]["trainer"] == tr and re.sub(r"^Ms ", "", rf[(1, t)]["jockey"]) == jk)
chk("J7", "EF R1", "Race page trainer and jockey = Race Fields PDF", len(page_r1), ok, "PASS" if ok == len(page_r1) else "FAIL")

# ---------------------------------------------------------------- I: internal integrity
for n in range(1, 11):
    bad_sum = bad_csv = bad_top = n_seg = 0
    starters = [x for x in xrun if int(x["race_no"]) == n and x["result_state"] != "DidNotStart"]
    for x in starters:
        tab = int(x["bib"])
        segs = secs_by[(n, tab)]
        if abs(sum(float(s["section_s"]) for s in segs) - float(x["finish_time_s"])) > 0.02:
            bad_sum += 1
        name, csegs = csv_rows[(n, tab)]
        for s, c in zip(segs, csegs):
            n_seg += 1
            if int(s["cum_dist"]) != c[0] or abs(float(s["section_s"]) - c[2]) > 0.005:
                bad_csv += 1
            if abs(float(s["top_speed"]) - c[1]) > 0.005:
                bad_top += 1
    chk("I1", f"EF R{n}", "Sum of segment times = official finish time (±0.02s), per starter", len(starters), len(starters) - bad_sum,
        "PASS" if bad_sum == 0 else "FAIL")
    chk("I2", f"EF R{n}", "CSV and XML agree on every split and top speed", n_seg, f"{n_seg - bad_csv} splits, {n_seg - bad_top} speeds",
        "PASS" if bad_csv == bad_top == 0 else "FAIL")
    zero_csv = {t for (r_, t), (_, cs) in csv_rows.items() if r_ == n and all(c[2] == 0 for c in cs)}
    dns = {int(x["bib"]) for x in xrun if int(x["race_no"]) == n and x["result_state"] == "DidNotStart"}
    chk("I3", f"EF R{n}", "CSV zero rows = XML DidNotStart", sorted(dns), sorted(zero_csv), "PASS" if dns == zero_csv else "FAIL")
    chk("I6", f"EF R{n}", "Tracking file track rating = stewards rating for that race", STEWARDS_RATING[n], xr[n]["track_condition"],
        "PASS" if STEWARDS_RATING[n] == xr[n]["track_condition"] else "FLAG")

draw_eq_bib = sum(1 for x in xrun if x["draw"] == x["bib"])
barrier_diff = sum(1 for (n, t), f in rf.items() if int(f["barrier"]) != t)
chk("I8", "EF all", "Tracking XML DrawNumber is the real barrier", f"barrier differs from saddlecloth for {barrier_diff}/87 (Race Fields PDF)",
    f"DrawNumber = saddlecloth for {draw_eq_bib}/{len(xrun)}", "FLAG")
r1w = next(x for x in xrun if x["race_no"] == "1" and x["final_rank"] == "1")
chk("I4", "EF R1", "XML race-level FinishTime = winner's time", r1w["finish_time_s"], xr[1]["finish_time_s"], "FLAG")
chk("I10", "EF R1", "Winner's XML time = race page time 1-31.18", "91.18", r1w["finish_time_s"],
    "PASS" if abs(float(r1w["finish_time_s"]) - 91.18) < 0.005 else "FAIL")
chk("I5", "EF R1", "Course code matches race distance", "1500m", xr[1]["track_name"], "FLAG")
mk_l600 = round(sum(float(s["section_s"]) for s in secs_by[(1, 2)][-3:]), 2)
chk("I7", "EF R1", "Race page 'Last 600m' = winner's last 600 from segments", "34.51 (race page)", mk_l600, "FLAG")
chk("I9", "EF R1", "XML cumulative margins agree with form-guide margins (rounded)", "Apostle 0.10L; Win Star 0.10+1.7=1.8L",
    "Apostle 0.07; Win Star 1.8", "PASS")
chk("I11", "EF meeting", "Race page 'last rating update' consistent with stewards upgrade", "upgrade 2:07pm", "Finalised 7.45am", "FLAG")

# ---------------------------------------------------------------- H: history and identity
chk("H1", "Murkado", "Prior run found in an earlier RQ file (Eagle Farm 4 Apr 2026 R1)", "found", "rank 3, bib 5, 77.45s, 1.22L, Soft 5", "PASS")
chk("H2", "RQ HorseCode", "tripleS HorseCode stable across meetings", "same code", "AUS-AN-2NT1PVH04 (Apr) vs 5370365 (Oct)", "FLAG")
multi = {}
for x in xrun:
    multi.setdefault(x["name"], set()).add(x["horse_code"])
repeat = [nm for nm in multi if sum(1 for x in xrun if x["name"] == nm) > 1]
chk("H3", "RQ HorseCode", "Same code for a horse entered in two races on the day", f"{len(repeat)} horses", f"{sum(len(multi[nm]) == 1 for nm in repeat)} consistent",
    "PASS" if all(len(multi[nm]) == 1 for nm in repeat) else "FAIL")
low = [u for u in bfu if u["TRACK"] == "Eagle Farm" and int(u["SELECTION_ID"]) < 10_000_000]
chk("H4", "Betfair IDs", "SELECTION_ID identifies the horse (not reused from older horses with the same name)", "new IDs for young horses",
    f"{len(low)}/87 EF runners have IDs < 10M, e.g. Apostle (3yo) 4517631, Just In Time 324042", "FLAG")

# ---------------------------------------------------------------- P: point in time
chk("P1", "Race Fields PDF", "Copy served today is the pre-race version", "pre-race field incl. scratched", "final field only; emergency marked (EM)", "FLAG")
chk("P2", "Form guide PDF", "Copy served today excludes the meeting's own results", "no 3 Oct form lines", "3 Oct result present in every runner's form", "FLAG")
chk("P3", "Betfair Oct file", "Publisher date equals race date", "2026-10-03", "Last-Modified 2026-11-23 03:36 UTC", "FLAG")

# ---------------------------------------------------------------- C / D / T
chk("C1", "Randwick", "Second lawful source to confirm runners and results", "official result", "none available without permission", "FLAG")
chk("C2", "Flemington", "Second lawful source to confirm runners and results", "official result", "none available without permission", "FLAG")
day = {"Eagle Farm": 87, "Flemington": 111, "Randwick": 115}
chk("D1", "Betfair 3 Oct", "Same-day file also covers provincial/country meetings", "yes",
    "13 meetings: Eagle Farm, Gold Coast, Toowoomba, Randwick, Newcastle, Wagga, Flemington, Murray Bridge, Kalgoorlie, Moora, Darwin, Matamata, Hawera", "PASS")

T = HERE / "raw_transcribed"
if T.exists():
    summ = [l.split("|") for l in (T / "betfair_2026_10_race_summary.psv").read_text().splitlines() if l and not l.startswith("#")]
    mism = 0
    for date, track, state, rno, rtype, dist, cnt in summ:
        if not rno.isdigit():
            continue
        if len(bf_by[(track, int(rno))]) != int(cnt) or bf_race[(track, int(rno))]["DISTANCE"] != dist:
            mism += 1
    chk("T1", "first run", "Transcribed Betfair counts and distances reproduced by exact file", "30 races", f"{30 - mism} match",
        "PASS" if mism == 0 else "FAIL")
    rq_rows = {1: 8, 2: 8, 3: 13, 4: 11, 5: 13, 6: 13, 7: 10, 8: 12, 9: 13, 10: 15}
    got = {n: sum(1 for (r_, _) in csv_rows if r_ == n) for n in range(1, 11)}
    chk("T2", "first run", "Transcribed RQ CSV row counts reproduced by exact file", sum(rq_rows.values()), sum(got.values()),
        "PASS" if got == rq_rows else "FAIL")

con.executemany("INSERT INTO integrity_check VALUES (?,?,?,?,?,?)", checks)

# ---------------------------------------------------------------- provenance classes & gaps
con.executemany("INSERT INTO field_provenance VALUES (?,?,?,?,?)", [
    ("RQ_RACE_FIELDS_PDF", "barrier / weight", "PRE_RACE_PUBLISHED", "acceptances release (Wed 9am for this meeting)", "Copy served later is regenerated; value usable, file date is not"),
    ("RQ_RACE_FIELDS_PDF", "jockey", "PRE_RACE_PUBLISHED", "riders release (Wed 12pm); late changes overwrite", "Original rider not recoverable from today's copy"),
    ("RQ_RACE_FIELDS_PDF", "field list / emergencies", "RACE_MORNING", "scratchings deadline (Sat 7:30am)", "Scratched runners removed from the copy"),
    ("RQ_MEETING_PAGES", "track rating (stewards, per race)", "RACE_MORNING", "morning rating; upgrades knowable at stated time (2:07pm)", "Race page shows end-of-day value only"),
    ("RQ_SECTIONAL_XML", "track condition", "UNVERIFIABLE_TIME", "n/a", "Lagged the stewards upgrade by two races; do not use"),
    ("RQ_SECTIONAL_XML", "DrawNumber", "UNVERIFIABLE_TIME", "n/a", "Equals saddlecloth; not the barrier; do not use"),
    ("RQ_SECTIONAL_XML", "rank / margin / time / ground / positions / stride", "POST_RACE_OUTCOME", "after the meeting", "No issue timestamp exposed"),
    ("RQ_SECTIONAL_XML", "HorseCode", "UNVERIFIABLE_TIME", "n/a", "Stable within a meeting; scheme changed between Apr and Oct 2026"),
    ("RQ_SECTIONAL_CSV", "splits / top speed", "POST_RACE_OUTCOME", "after the meeting", "Identical to XML"),
    ("RQ_FORM_GUIDE_PDF", "form lines", "RETRO_REVISED", "regenerated after each meeting", "Never treat a later download as the pre-race guide"),
    ("RQ_MEETING_PAGES", "stewards comments", "RETRO_REVISED", "after the meeting; may be amended", ""),
    ("BETFAIR_MONTHLY", "runner list / win / place", "POST_RACE_OUTCOME", "file Last-Modified (2026-11-23 for October)", "Final field only"),
    ("BETFAIR_MONTHLY", "selection_id", "UNVERIFIABLE_TIME", "n/a", "Follows the name; reused across horses"),
])
con.executemany("INSERT INTO data_gap VALUES (?,?,?,?,?)", [
    ("QLD", "starter", "original (pre-scratching) field and original rider", "NOT_PUBLISHED", "Only regenerated copies are served"),
    ("QLD", "horse", "stable horse key across meetings", "NOT_PUBLISHED", "tripleS HorseCode scheme changed; link by name + age + state for now"),
    ("QLD", "race", "prize money", "NOT_TESTED", "On race page and form guide; not extracted"),
    ("NSW", "starter", "finish order beyond 1st / margins / times", "PERMISSION_REQUIRED", "Racing NSW approval or written agreement with RA / authorised wholesaler"),
    ("NSW", "starter", "barrier / weight / jockey / trainer", "PERMISSION_REQUIRED", "Same; Betfair API metadata untested (needs account)"),
    ("NSW", "race", "class and conditions", "PERMISSION_REQUIRED", "Betfair RACE_TYPE is lossy (Hcap/Grp/Listed)"),
    ("NSW", "sectional", "splits / positions", "ACCESS_BLOCKED", "Punter's Intel app only; no export"),
    ("VIC", "starter", "finish order beyond 1st / margins / times", "PERMISSION_REQUIRED", "racing.com blocked to fetch tool; Racing Australia automation disallowed"),
    ("VIC", "starter", "barrier / weight / jockey / trainer", "PERMISSION_REQUIRED", "Betfair API metadata untested (needs account)"),
    ("VIC", "race", "class and conditions", "PERMISSION_REQUIRED", "Betfair RACE_TYPE is lossy"),
    ("VIC", "sectional", "splits / positions", "PERMISSION_REQUIRED", "racing.com CSV: personal download only; storage needs permission"),
    ("ALL", "horse", "stable national horse key", "PERMISSION_REQUIRED", "Betfair IDs follow names; RA / licensed providers hold horse IDs"),
])

# ---------------------------------------------------------------- exports
cov = con.execute("""
  SELECT v.state,
         count(*) FILTER (WHERE NOT coalesce(s.scratched,false)) AS starters,
         count(s.barrier) AS barrier, count(s.weight_kg) AS weight, count(s.jockey) AS jockey, count(s.trainer) AS trainer,
         count(s.finish_pos) AS finish_pos, count(s.margin_l) AS margin, count(s.finish_time_s) AS finish_time,
         count(s.last600_s) AS last600, count(s.dist_run_m) AS ground_covered
  FROM starter s JOIN race r USING (race_id) JOIN meeting m USING (meeting_id) JOIN venue v USING (venue_id)
  WHERE m.meeting_date = '2026-10-03' GROUP BY 1 ORDER BY 1""")
cov_rows = cov.fetchall()
con.execute("CREATE TABLE coverage_by_state AS SELECT * FROM (VALUES " + ",".join(
    "(" + ",".join(repr(v) for v in r) + ")" for r in cov_rows) + ") t(state, starters, barrier, weight, jockey, trainer, finish_pos, margin, finish_time, last600, ground_covered)")
for table in ["integrity_check", "data_gap", "field_provenance", "starter", "sectional", "position_in_run", "race",
              "horse_alias", "outcome_flag", "venue_alias", "source", "retrieval", "coverage_by_state"]:
    con.execute(f"COPY {table} TO '{OUT / (table + '.csv')}' (HEADER)")

print("check summary:", con.execute("SELECT status, count(*) FROM integrity_check GROUP BY 1 ORDER BY 1").fetchall())
print("by family:", con.execute("SELECT regexp_extract(check_id,'^[A-Z]+') k, status, count(*) FROM integrity_check GROUP BY 1,2 ORDER BY 1,2").fetchall())
print("tables:", {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in
                 ["race", "starter", "sectional", "position_in_run", "horse", "horse_alias", "outcome_flag", "integrity_check", "data_gap"]})
print("coverage:", cov_rows)
con.close()
