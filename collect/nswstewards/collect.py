"""Racing NSW 'Stewards Notifications' (pre-race: late gear changes, surgery, in foal, barrier/rider notes...), Oct 2022 on.
Research data only; never feeds production ratings until a separate release decision.

Source: the public WordPress REST API of www.racingnsw.com.au (/wp-json/wp/v2/posts). robots.txt on www only disallows
/wp-admin/. Honest User-Agent, ~3 s between requests, stops on repeated refusals. (The FreeFields diary on
racing.racingnsw.com.au is robots-disallowed and is NOT used.)

TIMING. Each post carries date_gmt (first published) and modified_gmt (last edited). The API shows only the current text,
so every version this collector sees is kept with its own capture time. For history, a post's text is treated as known
only from modified_gmt (conservative: an item added in the last edit could have been added late). A model may use an item
only for races starting after that time. Posts not found are UNKNOWN, never "no notifications".

Output: posts.jsonl (one line per post version: id, date_gmt, modified_gmt, link, title, content_html, content_sha256,
captured_utc), manifest.csv (per post id: versions seen), collect.log
Usage: python3 collect.py <outdir> [--since YYYY-MM-DD]   (default: from the newest modified_gmt already held, minus 3 days)"""
import csv, hashlib, json, os, random, sys, time, datetime as dt
import requests
API = 'https://www.racingnsw.com.au/wp-json/wp/v2/posts'
UA = 'RacingIntelligence-private/0.3 (personal non-commercial research; github.com/dejobrien000)'
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
S = requests.Session(); S.headers.update({'User-Agent': UA, 'Accept': 'application/json'})
LOG = open(os.path.join(OUT, 'collect.log'), 'a')
def now(): return dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def log(*a): m = now() + ' ' + ' '.join(map(str, a)); print(m, flush=True); print(m, file=LOG, flush=True)
PJ = os.path.join(OUT, 'posts.jsonl'); seen = {}   # (id, content_sha256) -> True
newest = '2022-10-01T00:00:00'
if os.path.exists(PJ):
    for ln in open(PJ, encoding='utf-8'):
        try: p = json.loads(ln)
        except json.JSONDecodeError: continue
        seen[(p['id'], p['content_sha256'])] = True; newest = max(newest, p.get('modified_gmt') or newest)
since = sys.argv[sys.argv.index('--since') + 1] + 'T00:00:00' if '--since' in sys.argv else \
    (dt.datetime.fromisoformat(newest) - dt.timedelta(days=3)).strftime('%Y-%m-%dT%H:%M:%S') if seen else newest
log('fetching posts modified after', since, '| versions held', len(seen))
out = open(PJ, 'a', encoding='utf-8'); new = pages = refusals = 0; page = 1
while True:
    params = {'search': 'stewards notifications', 'per_page': 100, 'page': page, 'orderby': 'modified', 'order': 'asc',
              'modified_after': since, '_fields': 'id,date_gmt,modified_gmt,link,title,content'}
    for attempt in range(3):
        try: r = S.get(API, params=params, timeout=60); break
        except requests.RequestException as e: log('error', e); time.sleep(20 * (attempt + 1)); r = None
    if r is None: log('STOP: no response'); break
    if r.status_code == 400 and 'rest_post_invalid_page_number' in r.text: break
    if r.status_code in (403, 429, 503):
        refusals += 1; log('refused', r.status_code)
        if refusals >= 5: log('STOP: refused repeatedly'); break
        time.sleep(90); continue
    if r.status_code != 200 or not r.headers.get('content-type', '').startswith('application/json'):
        log('STOP: unexpected answer', r.status_code, r.headers.get('content-type'), r.text[:120]); break
    items = r.json(); pages += 1
    for p in items:
        title = (p.get('title') or {}).get('rendered', ''); html = (p.get('content') or {}).get('rendered', '')
        if 'steward' not in title.lower() and 'gear' not in title.lower(): continue      # search also matches unrelated posts
        sha = hashlib.sha256(html.encode('utf-8')).hexdigest()
        if (p['id'], sha) in seen: continue
        seen[(p['id'], sha)] = True; new += 1
        out.write(json.dumps({'id': p['id'], 'date_gmt': p.get('date_gmt'), 'modified_gmt': p.get('modified_gmt'), 'link': p.get('link'),
                              'title': title, 'content_html': html, 'content_sha256': sha, 'captured_utc': now()}, ensure_ascii=False) + '\n')
    out.flush()
    total = int(r.headers.get('X-WP-TotalPages', '1') or 1)
    log(f'page {page}/{total}: {len(items)} posts, new versions so far {new}')
    if page >= total or not items: break
    page += 1; time.sleep(2.5 + random.random())
out.close()
ver = {}
for ln in open(PJ, encoding='utf-8'):
    p = json.loads(ln); v = ver.setdefault(p['id'], {'id': p['id'], 'title': p['title'], 'date_gmt': p['date_gmt'], 'versions': 0, 'last_modified_gmt': '', 'link': p['link']})
    v['versions'] += 1; v['last_modified_gmt'] = max(v['last_modified_gmt'], p['modified_gmt'] or '')
with open(os.path.join(OUT, 'manifest.csv'), 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=['id', 'date_gmt', 'last_modified_gmt', 'versions', 'title', 'link']); w.writeheader()
    for v in sorted(ver.values(), key=lambda v: v['date_gmt'] or ''): w.writerow(v)
log(f'done | pages {pages} | new versions {new} | posts held {len(ver)}')
