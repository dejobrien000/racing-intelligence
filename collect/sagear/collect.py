"""Racing SA gear-change and stewards' documents, from the public Country Racing SA site (www.countryracingsa.com.au).
Research data only; never feeds production ratings. Staging rule: nothing here is integrated until validated.

WHY THIS HOST. www.racingsa.com.au answers automated requests with an empty 202 (bot check), so it is not used. The same
Racing SA meeting pages are served openly by www.countryracingsa.com.au, whose robots.txt allows everything except
/modules/ and /email_share/. Honest User-Agent, robots.txt obeyed, one request every 2.5-3.5 s, stops after 20 refusals.

WHAT IT KEEPS (per meeting id, from Oct 2022):
  meetings.csv     id, title, meeting date, deadlines (acceptances, riders), race ids, document links, page sha256, retrieved
  files.csv        every document fetched: url, kind (gear / stewards / scratchings), sha256, bytes, retrieved, saved path
  pdf/<YYYYMM>/    the original PDFs ('Gear Change Race Order' carries 'Date Printed'; stewards' reports are post-meeting)
  gearchanges.jsonl  per-race 'gear changes' pages (changes only) for meetings within REFRESH_DAYS of today, with retrieval time
  collect.log
It does NOT keep the meeting pages themselves (they carry starting prices, which must stay out of everything model-side);
only the non-market fields listed above are extracted.

FINDING MEETINGS. There is no allowed index of meeting ids (the calendar is built from /modules/, which robots.txt disallows).
Ids are found by (1) following each meeting page's links to other meetings (form replays), and (2) checking neighbouring ids,
because Racing SA numbers a season's meetings in runs (5185273 = Gawler 7 Oct 24, 5185274 = Mount Gambier 9 Oct 24); an id that
is not an SA meeting answers 404 (4 KB). Upcoming meetings are found the same way from the newest ids.

Usage: python3 collect.py <outdir> [deadline_unix]    (env REFRESH_DAYS=14: re-read recent and upcoming meetings)"""
import csv, hashlib, json, os, random, re, sys, time, urllib.robotparser, datetime as dt
import requests
from bs4 import BeautifulSoup
B = 'https://www.countryracingsa.com.au'
UA = 'RacingIntelligence-private/0.3 (personal non-commercial research; github.com/dejobrien000)'
OUT = sys.argv[1]; DEADLINE = float(sys.argv[2]) if len(sys.argv) > 2 else time.time() + 5 * 3600
REFRESH = int(os.environ.get('REFRESH_DAYS', '0')); START = dt.date(2022, 10, 1); NEIGH = int(os.environ.get('NEIGHBOURS', '4'))
SEEDS = [5185273, 5185274] + [int(x) for x in os.environ.get('SEED_IDS', '').split(',') if x.strip()]
os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept-Encoding': 'gzip, deflate'})
LOG = open(os.path.join(OUT, 'collect.log'), 'a')
def now(): return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def log(*a): m = now() + ' ' + ' '.join(map(str, a)); print(m, flush=True); print(m, file=LOG, flush=True)
rp = urllib.robotparser.RobotFileParser(); r0 = S.get(B + '/robots.txt', timeout=30); rp.parse(r0.text.splitlines() if r0.status_code == 200 else [])
log('robots.txt', r0.status_code, '| /meeting allowed:', rp.can_fetch(UA, B + '/meeting/5185273'), '| /files allowed:', rp.can_fetch(UA, B + '/files/x.pdf'))
refusals, last = 0, 0.0
def get(url):
    global refusals, last
    if not rp.can_fetch(UA, url): log('ROBOTS DISALLOW', url); return None
    if refusals >= 20: return None
    wait = 2.5 + random.random() - (time.time() - last)
    if wait > 0: time.sleep(wait)
    for attempt in range(3):
        try: r = S.get(url, timeout=60); last = time.time(); break
        except requests.RequestException as e: log('error', url, e); time.sleep(15 * (attempt + 1)); r = None
    if r is None: return None
    if r.status_code in (403, 429, 503): refusals += 1; log('refused', r.status_code, url); time.sleep(60)
    elif r.status_code == 200 and r.headers.get('content-type', '').startswith('text/html') and len(r.content) < 200 and '/files/' not in url:
        refusals += 1; log('empty page (possible bot check)', url)
    else: refusals = 0
    return r

MFIELDS = ['id', 'status', 'title', 'meeting_date', 'acceptances_by', 'riders_by', 'race_ids', 'gear_pdf', 'stewards_pdf', 'scratchings_pdf',
           'gear_change_pages', 'linked_ids', 'page_sha256', 'retrieved_utc']
FFIELDS = ['url', 'kind', 'meeting_id', 'meeting_date', 'http', 'bytes', 'sha256', 'saved', 'retrieved_utc']
M = {}; F = {}
if os.path.exists(os.path.join(OUT, 'meetings.csv')): M = {r['id']: r for r in csv.DictReader(open(os.path.join(OUT, 'meetings.csv')))}
if os.path.exists(os.path.join(OUT, 'files.csv')): F = {r['url']: r for r in csv.DictReader(open(os.path.join(OUT, 'files.csv')))}
def save():
    for name, rows, cols, key in (('meetings.csv', M, MFIELDS, lambda r: int(r['id'])), ('files.csv', F, FFIELDS, lambda r: r['url'])):
        tmp = os.path.join(OUT, name + '.tmp')
        with open(tmp, 'w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader()
            for r in sorted(rows.values(), key=key): w.writerow({c: r.get(c, '') for c in cols})
        os.replace(tmp, os.path.join(OUT, name))
MONTHS = {m: i + 1 for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'])}
def parse_meeting(mid, html):
    soup = BeautifulSoup(html, 'html.parser'); text = soup.get_text(' ', strip=True)
    title = (soup.title.get_text(strip=True) if soup.title else '').replace(' | Country Racing SA', '')
    g = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)\s+(' + '|'.join(MONTHS) + r')\s+(\d{4})\b', text, re.I)
    mdate = dt.date(int(g.group(3)), MONTHS[g.group(2).lower()], int(g.group(1))).isoformat() if g else ''
    dl = {}
    for tr in soup.select('table.table__basic tr'):
        th, td = tr.find('th'), tr.find('td')
        if th and td: dl[th.get_text(' ', strip=True).lower()] = td.get_text(' ', strip=True)
    races = []
    for a in soup.select('a[href^="race/"]'):
        h = a['href']; t = a.get('title', '')
        if re.fullmatch(r'race/\d+', h): races.append(h.split('/')[1] + ':' + (re.search(r'race (\d+)$', t).group(1) if re.search(r'race (\d+)$', t) else ''))
    files = {}
    for a in soup.select('a[href*="files/"]'):
        lab = a.get_text(' ', strip=True).lower(); u = re.sub(r'\?.*$', '', a['href'])
        if not u.lower().endswith('.pdf'): continue
        kind = 'gear' if lab == 'gear' else 'stewards' if 'steward' in lab else 'scratchings' if 'scratching' in lab else None
        if kind: files.setdefault(kind, set()).add(u if u.startswith('http') else B + '/' + u.lstrip('/'))
    gc = sorted({a['href'].split('/')[-1] for a in soup.select('a[href^="race/gear-changes/"]')})
    linked = sorted({int(x) for x in re.findall(r'meeting/(\d{7})/', html)} - {mid})
    return {'id': str(mid), 'status': 'ok', 'title': title, 'meeting_date': mdate, 'acceptances_by': dl.get('acceptances must be declared before', ''),
            'riders_by': dl.get('riders must be declared before', ''), 'race_ids': ' '.join(dict.fromkeys(races)),
            'gear_pdf': ' '.join(sorted(files.get('gear', []))), 'stewards_pdf': ' '.join(sorted(files.get('stewards', []))),
            'scratchings_pdf': ' '.join(sorted(files.get('scratchings', []))), 'gear_change_pages': ' '.join(gc),
            'linked_ids': ' '.join(map(str, linked)), 'page_sha256': hashlib.sha256(html.encode('utf-8', 'replace')).hexdigest(), 'retrieved_utc': now()}
def fetch_pdf(url, kind, m):
    if url in F and F[url].get('http') == '200': return
    r = get(url); rec = {'url': url, 'kind': kind, 'meeting_id': m['id'], 'meeting_date': m['meeting_date'], 'retrieved_utc': now(), 'http': r.status_code if r is not None else 'error'}
    if r is not None and r.status_code == 200 and r.content[:4] == b'%PDF':
        sub = os.path.join('pdf', (m['meeting_date'] or 'undated').replace('-', '')[:6]); os.makedirs(os.path.join(OUT, sub), exist_ok=True)
        path = os.path.join(sub, url.rsplit('/', 1)[-1]); open(os.path.join(OUT, path), 'wb').write(r.content)
        rec.update(bytes=len(r.content), sha256=hashlib.sha256(r.content).hexdigest(), saved=path)
    elif r is not None and r.status_code == 200: rec['http'] = 'not a pdf'
    F[url] = rec

today = dt.date.today(); recent = (today - dt.timedelta(days=REFRESH)).isoformat() if REFRESH else None
GJ = open(os.path.join(OUT, 'gearchanges.jsonl'), 'a')
# work list: seeds, every linked id not yet read, neighbours of SA meetings in the window, recent/upcoming meetings to re-read
def in_window(m): return m.get('status') == 'ok' and m.get('meeting_date', '') >= START.isoformat()
def todo():
    want = set(SEEDS)
    for m in M.values():
        if m.get('status') == 'ok' and (m.get('meeting_date') or '9') >= START.isoformat():
            want.update(int(x) for x in m.get('linked_ids', '').split() if x)
            i = int(m['id']); want.update(range(i - NEIGH, i + NEIGH + 1))
    if M:   # newest ids: upcoming meetings get numbers above the latest known SA meeting
        top = max(int(k) for k, m in M.items() if m.get('status') == 'ok') if any(m.get('status') == 'ok' for m in M.values()) else max(SEEDS)
        want.update(range(top + 1, top + 1 + 3 * NEIGH))
    fresh = {int(k) for k, m in M.items() if recent and m.get('status') == 'ok' and (m.get('meeting_date') or '') >= recent}
    return sorted(i for i in want if i not in TRIED and (str(i) not in M or M[str(i)].get('status') == 'error')), sorted(fresh - TRIED)
n = 0; TRIED = set()   # each id at most once per run (a persistent error is retried next run, never in a loop)
while time.time() < DEADLINE and refusals < 20:
    new, fresh = todo()
    batch = new or fresh
    if not batch: break
    for mid in batch:
        if time.time() > DEADLINE or refusals >= 20: break
        TRIED.add(mid); r = get(f'{B}/meeting/{mid}')
        if r is None: M[str(mid)] = {'id': str(mid), 'status': 'error', 'retrieved_utc': now()}; continue
        if r.status_code == 404: M[str(mid)] = {'id': str(mid), 'status': 'not an SA meeting (404)', 'retrieved_utc': now()}; continue
        if r.status_code != 200: M[str(mid)] = {'id': str(mid), 'status': f'http {r.status_code}', 'retrieved_utc': now()}; continue
        m = parse_meeting(mid, r.text); M[str(mid)] = m; n += 1
        if in_window(m):
            for kind in ('gear', 'stewards', 'scratchings'):
                for u in m[{'gear': 'gear_pdf', 'stewards': 'stewards_pdf', 'scratchings': 'scratchings_pdf'}[kind]].split():
                    if time.time() < DEADLINE: fetch_pdf(u, kind, m)
            if recent and m['meeting_date'] >= recent:
                for rid in m['gear_change_pages'].split():
                    g = get(f'{B}/race/gear-changes/{rid}')
                    if g is not None and g.status_code == 200:
                        t = BeautifulSoup(g.text, 'html.parser').select_one('main') or BeautifulSoup(g.text, 'html.parser')
                        GJ.write(json.dumps({'meeting_id': m['id'], 'meeting_date': m['meeting_date'], 'race_id': rid, 'retrieved_utc': now(),
                                             'text': t.get_text('\n', strip=True)[:20000], 'page_sha256': hashlib.sha256(g.content).hexdigest()}) + '\n'); GJ.flush()
        if n % 20 == 0: save(); log('progress: meetings read', n, '| last', mid, m['meeting_date'], m['title'][:40], '| known', len(M), '| files', len(F))
save()
ok = [m for m in M.values() if in_window(m)]
log('done | SA meetings in window', len(ok), '| with gear PDF', sum(1 for m in ok if m.get('gear_pdf')), '| with stewards PDF',
    sum(1 for m in ok if m.get('stewards_pdf')), '| files', len(F), '| refusals', refusals)
