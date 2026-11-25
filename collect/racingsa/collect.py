"""Racing SA tracking collection (Damo, 26 Nov 2026: 'do SA overnight ... same shape as Qld'). Staging only, never production.
For every SA meeting in collect/racingsa/sa_meetings.csv (Breednet calendar, Dec 2023 on), asks Racing SA's public file host for
<date>_race<NN>_sectional.pdf, the per-race tripleSdata report linked from racingsa.com.au. Race 1 first: if a meeting has no
report under the known naming, the meeting is recorded as 'not found' and skipped (no other names guessed).
Honest User-Agent, robots.txt check, ~1.5 s between requests, stops after 20 refusals (403/429) in a row. Resumable: files already in
the manifest are not fetched again. Raw PDFs are not kept (sha256 + URL recorded); every page's text is kept so parsing can be
re-run without re-downloading.
Usage: python3 collect.py <meetings.csv> <outdir> [<deadline_unix>]"""
import csv, gzip, hashlib, io, json, os, random, re, sys, time, urllib.robotparser
from datetime import datetime, timezone
import requests, pdfplumber
sys.path.insert(0, os.path.dirname(__file__)); import parse_sectional as PS
BASE = 'https://d26j0amf97rmny.cloudfront.net/30072'
UA = 'RacingIntelligence-private/0.2 (personal non-commercial research; github.com/dejobrien000)'
MEET, OUT = sys.argv[1], sys.argv[2]; DEADLINE = float(sys.argv[3]) if len(sys.argv) > 3 else time.time() + 5 * 3600
os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = UA
LOG = open(os.path.join(OUT, 'collect.log'), 'a')
def log(*a): m = datetime.now(timezone.utc).strftime('%H:%M:%SZ') + ' ' + ' '.join(map(str, a)); print(m, flush=True); print(m, file=LOG, flush=True)
rp = urllib.robotparser.RobotFileParser()
r = S.get('https://d26j0amf97rmny.cloudfront.net/robots.txt', timeout=30); rp.parse(r.text.splitlines() if r.status_code == 200 else [])
log('robots.txt', r.status_code, '(no file = no restriction)' if r.status_code != 200 else '')
MAN = os.path.join(OUT, 'files.csv'); FIELDS = ['url', 'meeting_date', 'slug', 'race_no', 'status', 'bytes', 'sha256', 'fetched_utc', 'pdf_venue', 'pdf_date', 'pdf_race_no', 'n_runners', 'n_segments', 'problems']
done = {}
if os.path.exists(MAN):
    for row in csv.DictReader(open(MAN)): done[row['url']] = row
mf = open(MAN, 'a', newline=''); mw = csv.DictWriter(mf, fieldnames=FIELDS)
if not done: mw.writeheader()
TXT = gzip.open(os.path.join(OUT, 'texts.jsonl.gz'), 'at')
refusals = 0; last = 0.0
def fetch(url):
    global refusals, last
    if not rp.can_fetch(UA, url): log('ROBOTS DISALLOW', url); return None, None
    wait = 1.2 + random.random() * 0.6 - (time.time() - last)
    if wait > 0: time.sleep(wait)
    for attempt in range(3):
        try: r = S.get(url, timeout=60); last = time.time(); break
        except requests.RequestException as ex: log('error', url, ex); time.sleep(10 * (attempt + 1)); r = None
    if r is None: return 'error', None
    if r.status_code in (429, 503): refusals += 1; log('refused', r.status_code, url); time.sleep(60); return str(r.status_code), None
    refusals = refusals + 1 if r.status_code == 403 and r.headers.get('content-type', '').startswith('text/html') else 0
    return str(r.status_code), r.content if r.status_code == 200 else None
mon = {m: i for i, m in enumerate(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 1)}
def one(md, slug, rn, pad=True):
    url = f'{BASE}/{md}_race{rn:02d}_sectional.pdf' if pad else f'{BASE}/{md}_race{rn}_sectional.pdf'
    if url in done: return done[url]['status']
    st, body = fetch(url); row = {'url': url, 'meeting_date': md, 'slug': slug, 'race_no': rn, 'status': st, 'fetched_utc': datetime.now(timezone.utc).strftime('%FT%TZ')}
    if body:
        row.update(bytes=len(body), sha256=hashlib.sha256(body).hexdigest())
        try:
            with pdfplumber.open(io.BytesIO(body)) as pdf: pages = [(pg.extract_text() or '') for pg in pdf.pages]
            TXT.write(json.dumps({'url': url, 'sha256': row['sha256'], 'pages': pages}) + '\n'); TXT.flush()
            race, runners, segs, probs = PS.parse(pages)
            dt = race.get('date_text', '').split()
            row.update(pdf_venue=race.get('venue'), pdf_date=f'{dt[2]}-{mon.get(dt[1], 0):02d}-{int(dt[0]):02d}' if len(dt) == 3 else None, pdf_race_no=race.get('race_no'),
                       n_runners=len(runners), n_segments=len(segs), problems=' | '.join(probs)[:500])
        except Exception as ex: row['problems'] = f'parse error: {ex}'[:500]
    mw.writerow(row); mf.flush(); done[url] = row; return st
meetings = list(csv.DictReader(open(MEET))); log('meetings', len(meetings), 'already in manifest', len(done))
stats = {'found_meetings': 0, 'not_found_meetings': 0, 'files': 0}
for m in meetings:
    if time.time() > DEADLINE: log('deadline reached: stopping cleanly'); break
    if refusals >= 20: log('STOP: 20 refusals in a row'); break
    md, slug, nr = m['meeting_date'], m['slug'], int(float(m['maxr'] or m['races'] or 0))
    pad = True; st = one(md, slug, 1)
    if st != '200': pad = False; st = one(md, slug, 1, pad=False)          # the older reports used race1 (no leading zero)
    if st != '200': stats['not_found_meetings'] += 1; continue
    stats['found_meetings'] += 1
    for rn in range(2, max(nr, 1) + 1):
        if time.time() > DEADLINE or refusals >= 20: break
        one(md, slug, rn, pad); stats['files'] += 1
    log(md, slug, 'races', nr, '| totals', stats)
TXT.close(); mf.close(); log('DONE', stats)
