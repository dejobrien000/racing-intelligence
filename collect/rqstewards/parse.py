"""Queensland (QRIC) stewards' reports -> staging tables. Research data only: nothing here feeds the ratings.

Usage: python3 collect/rqstewards/parse.py <reports.jsonl> <out dir> [history.duckdb]
Reads every record the collector saved (a report fetched twice is kept twice: QRIC says reports "may be amended at any
time", so each version is kept with its page_sha256; the newest version per meeting is flagged latest=1).

TIMING RULE. A stewards' report is written after the meeting. Everything in it is RETROSPECTIVE information, including
items about pre-race events (late gear changes, vet checks, scratchings). available_from_utc = the later of 00:00 Brisbane
the day after the meeting and nothing earlier; for the backfill the actual retrieval time is also kept. A model may use a
row only for races that start after available_from_utc. A meeting with no report row is UNKNOWN, never "no incidents".

Outputs (one row per item, the original text always kept):
  meetings.csv   code, date, venue/club line, weather, track rating, rail, penetrometer, sections found, chars, sha, times
  comments.csv   one row per horse comment in a race section: race_no, race heading, horse as printed, horse_key, text,
                 simple tags (descriptive only, for measurement), matched_race_id/saddlecloth when the DB is given
  general.csv    GENERAL section lines
  summary.csv    SUMMARY section items: category (Reprimands, Fines, Horses swabbed pre-race, Warnings/bars, rider changes...)
  unparsed.csv   any line inside a race section that could not be tied to a horse (kept, never dropped)
  parse_report.txt counts
"""
import sys, os, re, json, csv, datetime as dt
from collections import Counter
src, out = sys.argv[1], sys.argv[2]
db = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(out, exist_ok=True)
BNE = dt.timezone(dt.timedelta(hours=10))
DASH = r'\s*[–—-]\s*'                         # en dash, em dash or hyphen between horse and comment
HORSE = re.compile(r"^((?:\d{1,2}\.\s*)?[A-Z0-9][A-Z0-9 '’.&\-]*?(?:\s*\([A-Z]{2,3}\))?)" + DASH + r'(.+)$')
RACE = re.compile(r'^RACE\s*(\d{1,2})\s*[:.\-–]?\s*(.*)$')   # race heading: capitals, e.g. 'RACE 1:GREAT NORTHERN ... 1350 M'
def is_heading(ln):
    g = RACE.match(ln)
    if not g or int(g.group(1)) > 12: return None
    rest = g.group(2)
    if re.search(r'[a-z]', rest): return None                      # 'Race 6: M. Rodd +0.5kg' style lines are not headings
    return g if re.search(r'\d{3,4}\s*(?:M|METRES)\b', rest) or not rest else None
KEYS = {'WEATHER': 'weather', 'TRACK RATING': 'track_rating', 'RAIL': 'rail', 'PENETROMETER': 'penetrometer'}
TAGS = [('slow_or_awkward_start', r'slow to begin|began (?:awkwardly|slowly|moderately)|missed the start|jumped (?:awkwardly|away slowly)'),
        ('interference', r'bumped|hampered|checked|crowded|tightened|inconvenienced|steadied|squeezed'),
        ('held_up', r'held up|unable to obtain clear running|difficulty obtaining clear running|lacked room|no clear running'),
        ('wide', r'raced wide|wide without cover|three wide|four wide|five wide'),
        ('keen', r'over-?raced|raced keenly|pulled hard|raced fiercely|ungenerously'),
        ('laid_or_shifted', r'laid in|laid out|hung in|hung out|shifted (?:in|out)'),
        ('vet_or_injury', r'veterinary|lame|bled|blood|cardiac|heart|injur|poor recovery|abrasion|lost (?:a|its|the) .*plate|respiratory'),
        ('gear', r'\bgear\b|blinkers|winkers|visors|tongue tie|ear ?muffs|nose ?roll|lugging bit|bit\b|cross-?over|bandages'),
        ('tactics_or_rider_explanation', r'when (?:asked|questioned)|connections advised|change of tactics|reported that'),
        ('swab', r'swabbed'), ('penalty', r'fined|reprimand|suspended|warned')]
def nk(s): return re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', s.upper()))
def tags(t): return ';'.join(n for n, p in TAGS if re.search(p, t, re.I))
def avail(d):  # 00:00 Brisbane the day after the meeting, in UTC
    x = dt.datetime.strptime(d, '%Y%m%d').replace(tzinfo=BNE) + dt.timedelta(days=1)
    return x.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

recs = [json.loads(l) for l in open(src, encoding='utf-8') if l.strip()]
latest = {}
for i, r in enumerate(recs):
    k = (r['code'], r['date'])
    if k not in latest or r['retrieved_utc'] >= recs[latest[k]]['retrieved_utc']: latest[k] = i
M, C, G, S, U = [], [], [], [], []
for i, r in enumerate(recs):
    lines = [l.strip() for l in (r.get('report_text') or '').split('\n') if l.strip()]
    base = {'code': r['code'], 'date': r['date'], 'page_sha256': r.get('page_sha256', ''), 'latest': int(latest[(r['code'], r['date'])] == i)}
    m = dict(base, url=r.get('url', ''), retrieved_utc=r.get('retrieved_utc', ''), available_from_utc=avail(r['date']),
             status=r.get('status', ''), chars=len(r.get('report_text') or ''), pdf_links=' '.join(r.get('pdf_links') or []),
             club_line='', date_line='', weather='', track_rating='', rail='', penetrometer='', races_found=0, sections='')
    sec, race_no, race_head, last = 'HEADER', None, '', None
    secs = []
    for ln in lines:
        up = ln.upper()
        if sec == 'HEADER':
            if not m['club_line'] and ('CLUB' in up or ('RACING' in up and 'COMMISSION' not in up)): m['club_line'] = ln
            if re.search(r'(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)', up) and not m['date_line']: m['date_line'] = ln
            for g in re.finditer(r'(WEATHER|TRACK RATING|RAIL|PENETROMETER)' + DASH + r'(.*?)(?=\s+(?:WEATHER|TRACK RATING|RAIL|PENETROMETER)' + DASH + r'|$)', ln):
                if not m[KEYS[g.group(1)]]: m[KEYS[g.group(1)]] = g.group(2).strip()
        g = is_heading(ln) if sec in ('HEADER', 'GENERAL', 'OFFICIALS', 'RACE') else None
        if g:
            sec, race_no, race_head, last = 'RACE', int(g.group(1)), ln, None; m['races_found'] += 1; secs.append(f'R{race_no}'); continue
        if ln == up and len(ln) < 40 and re.fullmatch(r"(?:STEWARDS'? )?(?:RACE ?DAY )?SUMMARY", up): up = 'SUMMARY'   # 'STEWARDS RACE DAY SUMMARY'
        if up in ('GENERAL', 'OFFICIALS', 'SUMMARY', 'TRIALS', 'JUMP OUTS', 'JUMPOUTS'):
            sec, last = up, None; secs.append(up); cat = ''; continue
        if sec == 'GENERAL': G.append(dict(base, line=ln, tags=tags(ln)))
        elif sec == 'SUMMARY':
            if not re.match(r'^(race\s*\d+|all |[A-Z]\.\s)', ln, re.I) and len(ln) < 70 and not ln.endswith('.'): cat = ln; continue
            g = re.match(r'^race\s*(\d{1,2})\s*:\s*(.*)$', ln, re.I)
            S.append(dict(base, category=cat, race_no=g.group(1) if g else '', text=g.group(2) if g else ln))
        elif sec == 'RACE':
            h = HORSE.match(ln)
            if h and h.group(1).strip().upper() == h.group(1).strip() and len(h.group(1)) <= 40:
                name = re.sub(r'^\d{1,2}\.\s*', '', h.group(1)).strip()
                last = dict(base, race_no=race_no, race_heading=race_head, horse_as_printed=name, horse_key=nk(name), text=h.group(2).strip())
                C.append(last)
            elif last is not None and not is_heading(ln):   # wrapped continuation of the previous horse's comment
                last['text'] += ' ' + ln
            else:
                U.append(dict(base, race_no=race_no, line=ln))
    m['sections'] = ' '.join(secs); M.append(m)
for c in C: c['tags'] = tags(c['text'])

# optional: tie each comment to the horse's start in our database (same day; a horse runs once a day)
if db and C:
    import duckdb
    con = duckdb.connect(db, read_only=True)
    q = con.execute("""select strftime(s.meeting_date, '%Y%m%d') d, regexp_replace(upper(s.name_key), '[^A-Z0-9]', '', 'g') k,
                       s.race_id, s.track, s.race_no, s.saddlecloth from starter s""").fetchall()
    idx = {}
    for d, k, rid, trk, rn, sc in q: idx.setdefault((d, k), []).append((rid, trk, rn, sc))
    for c in C:
        hit = idx.get((c['date'], c['horse_key']), [])
        if len(hit) > 1: hit = [h for h in hit if h[2] == c['race_no']] or hit   # dual acceptor: the race the report names
        c['match'] = 'matched' if len(hit) == 1 else 'ambiguous' if hit else 'not in database'
        if len(hit) == 1: c['race_id'], c['db_track'], c['db_race_no'], c['saddlecloth'] = hit[0]
        c['race_no_agrees'] = '' if len(hit) != 1 else int(hit[0][2] == c['race_no'])
def dump(name, rows):
    if not rows: open(os.path.join(out, name), 'w').write(''); return
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(out, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
for n, rows in [('meetings.csv', M), ('comments.csv', C), ('general.csv', G), ('summary.csv', S), ('unparsed.csv', U)]: dump(n, rows)
rep = [f'records {len(recs)} (meetings {len(latest)}; older versions kept {len(recs) - len(latest)})',
       f'comments {len(C)} | general lines {len(G)} | summary items {len(S)} | unparsed race lines {len(U)}',
       'tags ' + str(dict(Counter(t for c in C for t in c['tags'].split(';') if t)))]
if db and C: rep.append('database match ' + str(dict(Counter(c['match'] for c in C))) + ' | race number agrees ' + str(dict(Counter(c['race_no_agrees'] for c in C if c['match'] == 'matched'))))
open(os.path.join(out, 'parse_report.txt'), 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep))
