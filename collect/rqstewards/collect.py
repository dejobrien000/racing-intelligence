"""Racing Queensland / QRIC race-day stewards' reports, thoroughbred meetings (Damo, 26 Nov 2026: "Continue the proposed
Queensland stewards' report collector"; history from Oct 2022, forward weekly). Staging input only: nothing here is a rating input.

Public pages on www.racingqueensland.com.au (robots.txt has no Disallow; checked 26 Nov 2026), honest User-Agent, 2.5-3.5 s
between requests, stops on a CAPTCHA page or after 20 consecutive refusals. Resumable: files.csv is the manifest; a meeting is
fetched once unless its last attempt failed (re-run with REFRESH_DAYS=n to re-read the last n days, e.g. for late amendments).

  1. Meetings: monthly calendar pages /racing/full-calendar/YYYY/MM list every meeting; thoroughbred links are
     /racing/full-calendar/thoroughbred/meeting/<code>/<YYYYMMDD>.
  2. Report: /racing/full-calendar/thoroughbred/meeting/<code>/<YYYYMMDD>/stewards-report. The report is the page's
     'cke_editable' text block that mentions stewards; it is kept verbatim (HTML and plain text) with the page's sha256.
     No report block = status no_report (a missing report is NOT evidence that nothing happened).

Usage: collect.py <first YYYY-MM> <last YYYY-MM> <outdir> [unix deadline]
Output: outdir/meetings.csv, outdir/files.csv (manifest), outdir/reports.jsonl (one JSON object per fetched report), collect.log"""
import sys, os, re, csv, json, time, random, hashlib, datetime as dt
import requests
from bs4 import BeautifulSoup
UA = 'RacingIntelligence-private/0.3 (personal research; github.com/dejobrien000)'
B = 'https://www.racingqueensland.com.au'
CAPTCHA = re.compile(r'captcha|are you (a )?human|verify you are human', re.I)
first, last, out = sys.argv[1], sys.argv[2], sys.argv[3]; deadline = float(sys.argv[4]) if len(sys.argv) > 4 else 9e18
REFRESH = int(os.environ.get('REFRESH_DAYS', '0'))
os.makedirs(out, exist_ok=True)
S = requests.Session(); S.headers['User-Agent'] = UA
now = lambda: dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
LOG = open(os.path.join(out, 'collect.log'), 'a')
def log(*a): m = ' '.join(str(x) for x in a); print(m, flush=True); LOG.write(f'{now()} {m}\n'); LOG.flush()
refusals = 0
def get(url):
    global refusals
    for a in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200 and CAPTCHA.search(r.text[:30000]): log('STOP: CAPTCHA/human check at', url); sys.exit(2)
            if r.status_code in (403, 429): refusals += 1
            else: refusals = 0
            if refusals >= 20: log('STOP: 20 consecutive refusals'); sys.exit(3)
            return r
        except requests.RequestException as e:
            log('retry', url, e); time.sleep(15 * (a + 1))
    return None
def pause(): time.sleep(2.5 + random.random())
# 1. meetings
mfile = os.path.join(out, 'meetings.csv'); meetings = {}
if os.path.exists(mfile):
    for r in csv.DictReader(open(mfile)): meetings[(r['code'], r['date'])] = r
y, m = map(int, first.split('-')); ly, lm = map(int, last.split('-'))
months = []
while (y, m) <= (ly, lm): months.append((y, m)); y, m = (y + (m == 12), m % 12 + 1)
this_month = dt.date.today().strftime('%Y-%m')
for y, m in months:
    ym = f'{y}-{m:02d}'
    if any(v.get('month') == ym for v in meetings.values()) and ym < this_month and not REFRESH: continue
    if time.time() > deadline: break
    r = get(f'{B}/racing/full-calendar/{y}/{m:02d}'); pause()
    if r is None or r.status_code != 200: log('calendar fail', ym, r.status_code if r is not None else 'none'); continue
    n = 0
    for code, d in set(re.findall(r'/racing/full-calendar/thoroughbred/meeting/([^/"?#]+)/(\d{8})', r.text)):
        if d[:6] != f'{y}{m:02d}': continue
        meetings.setdefault((code, d), {'code': code, 'date': d, 'month': ym, 'listed_utc': now()}); n += 1
    log('calendar', ym, 'thoroughbred meetings', n)
with open(mfile, 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=['code', 'date', 'month', 'listed_utc']); w.writeheader()
    for k in sorted(meetings, key=lambda k: (k[1], k[0])): w.writerow({f: meetings[k].get(f, '') for f in ['code', 'date', 'month', 'listed_utc']})
# 2. reports
ffile = os.path.join(out, 'files.csv'); FIELDS = ['code', 'date', 'url', 'status', 'http', 'bytes', 'page_sha256', 'report_chars', 'retrieved_utc']
done = {}
if os.path.exists(ffile):
    for r in csv.DictReader(open(ffile)): done[(r['code'], r['date'])] = r
today = dt.date.today(); cut = (today - dt.timedelta(days=REFRESH)).strftime('%Y%m%d') if REFRESH else None
todo = [k for k in sorted(meetings, key=lambda k: (k[1], k[0])) if k[1] <= today.strftime('%Y%m%d')
        and (k not in done or done[k]['status'] in ('error', 'http_error') or (cut and k[1] >= cut))]
log('reports to fetch', len(todo), 'of', len(meetings))
RJ = open(os.path.join(out, 'reports.jsonl'), 'a')
def save_manifest():
    with open(ffile, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS); w.writeheader()
        for k in sorted(done, key=lambda k: (k[1], k[0])): w.writerow({f: done[k].get(f, '') for f in FIELDS})
for i, (code, d) in enumerate(todo):
    if time.time() > deadline: log('deadline reached; stopping cleanly'); break
    url = f'{B}/racing/full-calendar/thoroughbred/meeting/{code}/{d}/stewards-report'
    r = get(url); pause(); cap = now()
    if r is None: done[(code, d)] = {'code': code, 'date': d, 'url': url, 'status': 'error', 'retrieved_utc': cap}; continue
    rec = {'code': code, 'date': d, 'url': url, 'http': r.status_code, 'bytes': len(r.content), 'page_sha256': hashlib.sha256(r.content).hexdigest(), 'retrieved_utc': cap}
    if r.status_code != 200: rec['status'] = 'http_error'
    else:
        soup = BeautifulSoup(r.text, 'html.parser'); blk = None
        for div in soup.find_all('div', class_='cke_editable'):
            if re.search(r'steward', div.get_text(' '), re.I): blk = div; break
        pdfs = sorted({a['href'] for a in soup.find_all('a', href=True) if re.search(r'steward', a['href'] + a.get_text(' '), re.I) and a['href'].lower().endswith('.pdf')})
        if blk is None and not pdfs: rec['status'] = 'no_report'
        else:
            text = blk.get_text('\n') if blk else ''
            text = re.sub(r'[ \t ]+', ' ', text); text = re.sub(r'\n\s*\n+', '\n', text).strip()
            rec['status'] = 'ok' if blk else 'pdf_link_only'; rec['report_chars'] = len(text)
            RJ.write(json.dumps({**rec, 'report_html': str(blk) if blk else '', 'report_text': text, 'pdf_links': pdfs}, ensure_ascii=False) + '\n'); RJ.flush()
    done[(code, d)] = rec
    if i % 25 == 0: save_manifest(); log('progress', i + 1, '/', len(todo), code, d, rec['status'])
save_manifest()
c = {}
for v in done.values(): c[v['status']] = c.get(v['status'], 0) + 1
log('done; manifest status counts', c)
