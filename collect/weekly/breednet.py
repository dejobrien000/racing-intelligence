"""Breednet results collector for GitHub Actions (Python port of collectors/breednet_results.js + breednet_dates.js).
Reads Breednet's public, server-rendered results pages with an honest User-Agent, polite pacing (2.5-3.5 s) and a
robots.txt check. Stops at any CAPTCHA / "are you human" page and never tries to get past it. No prices are kept: the
weight cell also shows the starting price, and only the leading number (the weight) is stored.

Output: one gzip JSON-lines bundle in the same record format the browser crawler wrote, so history/load_breednet.py
reads it unchanged:  {"key": "bnidx:DATE", "value": {...}}  and  {"key": "bnm:DATE:slug", "value": {...}}.

Usage:
  python3 breednet.py dates FROM TO OUT.jsonl.gz [--states NSW,VIC,ACT,SA,WA,TAS] [--map venue_states.json]
  python3 breednet.py queue QUEUE.json OUT.jsonl.gz          (QUEUE = [[date, slug], ...]; indexes not re-fetched)
Resumable: records already in OUT (or OUT.part) are skipped."""
import sys, os, re, json, gzip, time, random, datetime as dt, urllib.robotparser
import requests
from bs4 import BeautifulSoup

BASE = 'https://www.breednet.com.au'
UA = 'RacingIntelligence-private/0.2 (personal non-commercial research; github.com/dejobrien000)'
CAPTCHA = re.compile(r'captcha|are you human|verify you are human|unusual traffic', re.I)
S = requests.Session(); S.headers['User-Agent'] = UA
clean = lambda s: re.sub(r'\s+', ' ', s or '').strip()
now = lambda: dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

class Captcha(Exception): pass

def cls(e): return e.get('class') or ''          # raw class attribute (multi_valued_attributes=None), like JS className
def has(e, c): return c in cls(e).split()
def find(e, c):
    for x in e.find_all(True):
        if has(x, c): return x
def text(e): return clean(e.get_text()) if e is not None else ''

def get(path, marker):
    for attempt in range(3):
        try:
            r = S.get(BASE + path, timeout=40)
        except requests.RequestException as ex:
            if attempt == 2: raise
            time.sleep(20 * (attempt + 1)); continue
        h = r.text
        if CAPTCHA.search(h[:20000]) and not re.search(marker, h): raise Captcha(path)
        if r.status_code in (429, 500, 502, 503, 504) and attempt < 2: time.sleep(60 * (attempt + 1)); continue
        if r.status_code >= 400: raise RuntimeError(f'HTTP {r.status_code} {path}')
        return h

def parse_index(html, date):
    d = BeautifulSoup(html, 'lxml', multi_valued_attributes=None); race, trial, other = [], [], 0
    for p in d.find_all(True):
        if not has(p, 'meetingPanel'): continue
        a = next((x for x in p.find_all('a') if '-results/' in (x.get('href') or '')), None)
        if a is None: continue
        parts = (a.get('href') or '').split('?')[0].split('/')
        if len(parts) < 5 or parts[2] != 'australia' or parts[4] != date: other += 1; continue
        (trial if parts[1] == 'trial-results' else race).append(parts[3])
    dedup = lambda xs: list(dict.fromkeys(xs))
    return {'race': dedup(race), 'trial': dedup(trial), 'other': other}

HDR = re.compile(r'^Race (\d+) - (.*?)\s*Class:(.*?)Track:(.*?)Time:(.*?)(?:Prizemoney:(.*))?$')
BRD = re.compile(r'^(\d+)([a-z]+)\s+(.*?)\s+x\s+(.*?(?:\s\([A-Z]{2,3}\))?)\s+\((.*)\)$', re.I)
def parse_meeting(html):
    d = BeautifulSoup(html, 'lxml', multi_valued_attributes=None)
    h2 = d.find('h2'); out = {'meeting': text(h2), 'races': [], 'v': 2}
    first = next((x for x in d.find_all(True) if has(x, 'runnerWrapper')), None)
    if first is None: return out
    cur = None
    for e in first.parent.find_all(True, recursive=False):
        cl = cls(e)
        if cl.startswith('raceheader'):
            t = text(e); m = HDR.match(t)
            cur = {'race_no': int(m[1]) if m else None, 'title': clean(m[2]) if m else t, 'class': clean(m[3]) if m else None,
                   'track_cond': clean(m[4]) if m else None, 'time': clean(m[5]) if m else None,
                   'prize': clean(m[6]) if m and m[6] else None, 'stakes_header': cl == 'raceheaderSR', 'header_raw': t, 'runners': []}
            dm = re.search(r'\((\d{3,4})m\)', cur['title']); cur['distance_m'] = int(dm[1]) if dm else None
            out['races'].append(cur)
        elif cl == 'runnerWrapper' and cur is not None:
            q = lambda c: find(e, c)
            horse = q('horse'); ht = text(horse); sc = re.match(r'^(\d+)\.', ht)
            a = horse.find('a') if horse is not None else None
            am = BRD.match(text(q('breeding')))
            w = re.match(r'^\d+(?:\.\d+)?', text(q('res-weight')))      # weight only; the starting price in the same cell is dropped
            cur['runners'].append({'pos': text(q('finishpos')), 'margin': text(q('margin')), 'saddlecloth': int(sc[1]) if sc else None,
                'horse': text(a) if a is not None else '', 'weight': w[0] if w else '',
                'jockey': re.sub(r'^R:\s*', '', text(q('jockey'))), 'trainer': re.sub(r'^T:\s*', '', text(q('trainer'))),
                'age': int(am[1]) if am else None, 'sex': am[2] if am else None, 'sire': am[3] if am else None,
                'dam': am[4] if am else None, 'damsire': am[5] if am else None})
    return out

def robots_ok():
    rp = urllib.robotparser.RobotFileParser()
    try:
        r = S.get(BASE + '/robots.txt', timeout=30); rp.parse(r.text.splitlines() if r.status_code == 200 else [])
    except requests.RequestException: rp.parse([])
    bad = [p for p in ('/results/daily-results', '/race-results/australia/x/2026-01-01') if not rp.can_fetch(UA, BASE + p)]
    if bad: sys.exit(f'robots.txt disallows {bad}; stopping')

class Out:
    def __init__(self, path):
        self.path, self.part = path, path + '.part'; self.have = set()
        for f in (path, self.part):
            if os.path.exists(f):
                op = gzip.open if f.endswith('.gz') else open
                try:
                    with op(f, 'rt', encoding='utf-8') as fh:
                        for line in fh:
                            if line.strip(): self.have.add(json.loads(line)['key'])
                except (EOFError, OSError, json.JSONDecodeError): pass
        if os.path.exists(path) and not os.path.exists(self.part):   # resume from a finished bundle
            with gzip.open(path, 'rt', encoding='utf-8') as fi, open(self.part, 'w', encoding='utf-8') as fo: fo.write(fi.read())
        self.fh = open(self.part, 'a', encoding='utf-8')
    def put(self, k, v): self.fh.write(json.dumps({'key': k, 'value': v}, ensure_ascii=False) + '\n'); self.fh.flush(); self.have.add(k)
    def close(self):
        self.fh.close()
        with open(self.part, encoding='utf-8') as fi, gzip.open(self.path, 'wt', encoding='utf-8') as fo: fo.write(fi.read())
        os.remove(self.part)

def pause(): time.sleep(2.5 + random.random())
LOG = []
def log(*a): s = ' '.join(str(x) for x in a); LOG.append(s); print(s, flush=True)

def meeting(out, date, slug, stats):
    key = f'bnm:{date}:{slug}'
    if key in out.have or f'bnmiss:{date}:{slug}' in out.have: stats['skipped'] += 1; return
    path = f'/race-results/australia/{slug}/{date}'
    p = parse_meeting(get(path, 'runnerWrapper'))
    if p['races']: out.put(key, {'key': key, 'date': date, 'slug': slug, 'path': path, 'retrieved_utc': now(), **p}); stats['meetings'] += 1
    else: out.put(f'bnmiss:{date}:{slug}', {'date': date, 'slug': slug, 'retrieved_utc': now()}); stats['miss'] += 1
    pause()

def run(items, out, stats):
    consec = 0
    for date, slug in items:
        try:
            meeting(out, date, slug, stats); consec = 0
        except Captcha as ex:
            log('STOP: CAPTCHA / are-you-human page at', ex); stats['captcha'] = True; return
        except Exception as ex:
            stats['err'] += 1; consec += 1; log('error', date, slug, str(ex)[:160])
            if consec >= 5: log('5 errors in a row: pausing 5 min'); time.sleep(300); consec = 0
            pause()

def main():
    mode = sys.argv[1]; stats = {'meetings': 0, 'miss': 0, 'skipped': 0, 'err': 0, 'idx': 0, 'captcha': False, 'started_utc': now()}
    robots_ok()
    if mode == 'dates':
        d0, d1, outp = dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3]), sys.argv[4]
        a = sys.argv[5:]; states = set((a[a.index('--states') + 1] if '--states' in a else 'NSW,VIC,ACT,SA,WA,TAS').split(','))
        vmap = json.load(open(a[a.index('--map') + 1] if '--map' in a else os.path.join(os.path.dirname(__file__), 'venue_states.json')))
        out = Out(outp); unknown = {}
        d = d0
        while d <= d1 and not stats['captcha']:
            date = d.isoformat()
            try:
                idx = {'date': date, **parse_index(get('/results/daily-results?t_date=' + date, 'meetingPanel'), date), 'retrieved_utc': now()}
                out.put('bnidx:' + date, idx); stats['idx'] += 1; pause()
            except Captcha as ex:
                log('STOP: CAPTCHA / are-you-human page at', ex); stats['captcha'] = True; break
            except Exception as ex:
                stats['err'] += 1; log('index error', date, str(ex)[:160]); pause(); d += dt.timedelta(days=1); continue
            want = []
            for s in idx['race']:
                st = vmap.get(s)
                if st is None: unknown.setdefault(s, []).append(date)
                elif st[0] in states: want.append((date, s))
            run(want, out, stats)
            d += dt.timedelta(days=1)
        stats['unknown_venues'] = unknown
    elif mode == 'queue':
        q, outp = json.load(open(sys.argv[2])), sys.argv[3]; out = Out(outp)
        run([(d, s) for d, s in q], out, stats)
    else: sys.exit(__doc__)
    out.close(); stats['finished_utc'] = now()
    json.dump({**stats, 'log': LOG}, open(outp.replace('.jsonl.gz', '') + '.stats.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in stats.items() if k != 'unknown_venues'}))
    if stats.get('unknown_venues'): print('venues with no state (not collected):', ', '.join(sorted(stats['unknown_venues'])))
    sys.exit(2 if stats['captcha'] else 0)

if __name__ == '__main__': main()
