"""End-to-end tests of collector.py against a local mock of TAB's racing API and GitHub's contents API.
Run: python3 pc_collector/tests/test_collector.py   (prints PASS/FAIL per check; exit 1 on any failure)"""
import os, sys, json, base64, hashlib, threading, subprocess, tempfile, gzip, re, shutil
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
HERE = os.path.dirname(os.path.abspath(__file__)); COLLECTOR = os.path.join(os.path.dirname(HERE), 'collector.py')
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
TOKEN = 'test-token-not-a-secret'
D = '20261126'

# ---- fixtures: built from today's real racecard file so the output can be compared line by line ----
REAL = os.path.join(REPO_ROOT, 'research', 'collect', 'national', D, 'tab_20261125T220344Z.raw.txt')
def load_real():
    meets, races, cur = {}, {}, None
    for line in open(REAL, encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if p[0] == 'MEET': meets[p[1]] = (p[2], p[3])
        elif p[0] == 'RACE': cur = (p[1], int(p[2])); races[cur] = {'line': line.rstrip('\n'), 'p': p, 'runners': []}
        elif cur and len(p) >= 11 and p[0].isdigit(): races[cur]['runners'].append(p)
    return meets, races
MEETS, RACES = load_real()
def num(x):
    if x in ('null', None): return None
    try: return int(x)
    except ValueError: return float(x)
def racecard_json(ven, n, status='Open', results=None):
    r = RACES[(ven, n)]; p = r['p']
    runners = []
    for q in r['runners']:
        runners.append({'runnerNumber': int(q[0]), 'runnerName': q[1], 'barrierNumber': num(q[2]), 'handicapWeight': num(q[3]), 'claimAmount': num(q[4]),
                        'riderDriverName': q[5], 'trainerName': q[6], 'emergency': q[7] == 'true', 'blinkers': False, 'earlySpeedRating': 80,
                        'fixedOdds': {'returnWin': num(q[8]), 'returnPlace': num(q[9]), 'bettingStatus': q[10], 'flucs': [{'returnWin': 9.0}]},
                        'parimutuel': {'returnWin': 4.4}})
    return {'raceNumber': n, 'raceName': p[3], 'raceStartTime': p[4], 'raceDistance': int(p[5]), 'meeting': {'trackCondition': p[6], 'venueMnemonic': ven},
            'hasFixedOdds': p[8] == 'true', 'fixedOddsUpdateTime': p[9], 'raceStatus': status, 'results': results or [], 'runners': runners}
def meetings_json():
    ms = []
    for ven, (name, state) in MEETS.items():
        ms.append({'meetingName': name, 'location': state, 'raceType': 'R', 'venueMnemonic': ven,
                   'races': [{'raceNumber': n, 'raceStartTime': RACES[(v, n)]['p'][4]} for (v, n) in sorted(RACES) if v == ven]})
    ms.append({'meetingName': 'CHELMSFORD CITY', 'location': 'GBR', 'raceType': 'R', 'venueMnemonic': 'CHE', 'races': [{'raceNumber': 1}]})
    ms.append({'meetingName': 'ALBION PARK', 'location': 'QLD', 'raceType': 'H', 'venueMnemonic': 'APH', 'races': [{'raceNumber': 1}]})
    return {'meetings': ms}
def form_json(ven, n, r):
    return {'runnerNumber': r, 'runnerName': f'HORSE {ven}{n}{r}', 'age': 5, 'sex': 'Gelding', 'blinkers': r % 3 == 0, 'classLevel': 'dn',
            'runsSinceSpell': 0, 'daysSinceLastRun': 14, 'sire': 'SIRE (USA)', 'dam': 'DAM|WITH|PIPES', 'trainerName': 'T TRAINER',
            'formComment': 'tipster text', 'runnerStarts': {'startSummaries': {'overall': {'numberOfStarts': 9, 'numberOfWins': 2, 'numberOfPlacings': 3}},
            'previousStarts': [{'startType': 'LastStarts', 'startDate': '2026-11-03', 'venueAbbreviation': 'GERL', 'distance': 1200, 'class': '3YO+ BM58+',
                                'finishingPosition': 6, 'numberOfStarters': 12, 'draw': 0, 'margin': 3.3, 'positionInRun': '3-3-2', 'trackCondition': 'Good',
                                'time': '1:12.32', 'rider': 'Madi Derrick', 'stewardsComment': None, 'odds': 7.5, 'startingPosition': 0},
                               {'startType': 'Trial', 'startDate': '2026-09-30', 'venueAbbreviation': 'GERL', 'distance': 1100, 'class': 'OPEN',
                                'finishingPosition': 2, 'numberOfStarters': 8, 'draw': 0, 'margin': 1.25, 'positionInRun': None, 'trackCondition': 'Good',
                                'time': '1:07.32', 'rider': 'X Y', 'stewardsComment': 'Raced keenly.\nLine two', 'odds': 3.2}]}}

STATE = {'status': {}, 'tab_html': False, 'fail_once': set(), 'gh_corrupt_once': set(), 'files': {}, 'gets': 0}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def send(self, code, obj=None, raw=None, ctype='application/json'):
        b = raw if raw is not None else json.dumps(obj).encode(); self.send_response(code); self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        u = urlparse(self.path); pth = u.path; q = parse_qs(u.query)
        if pth.startswith('/v1/tab-info-service/'):
            assert 'cb' in q
            if STATE['tab_html']: return self.send(200, raw=b'<!DOCTYPE html><html><title>TAB.com.au</title></html>', ctype='text/html')
            if pth.endswith('/meetings'): return self.send(200, meetings_json())
            m = re.search(r'/meetings/R/(\w+)/races/(\d+)(?:/form/(\d+))?$', pth)
            ven, n, r = m[1], int(m[2]), m[3]
            key = (ven, n, r)
            if key in STATE['fail_once']: STATE['fail_once'].discard(key); return self.send(500, {'error': 'boom'})
            if r: return self.send(200, form_json(ven, n, int(r)))
            st = STATE['status'].get((ven, n), 'Open')
            res = [[int(x[0])] for x in RACES[(ven, n)]['runners'][:4]] if st in ('Paying', 'Final') else []
            return self.send(200, racecard_json(ven, n, st, res))
        if pth.startswith('/repos/'):
            if self.headers.get('Authorization') != f'Bearer {TOKEN}': return self.send(401, {'message': 'Bad credentials'})
            fp = unquote(pth.split('/contents/', 1)[1]); STATE['gets'] += 1
            if fp not in STATE['files']: return self.send(404, {'message': 'Not Found'})
            b = STATE['files'][fp]
            if 'raw' in (self.headers.get('Accept') or ''):
                if fp in STATE['gh_corrupt_once']: STATE['gh_corrupt_once'].discard(fp); return self.send(200, raw=b + b'X', ctype='application/octet-stream')
                return self.send(200, raw=b, ctype='application/octet-stream')
            sha = hashlib.sha1(b'blob %d\0' % len(b) + b).hexdigest()
            return self.send(200, {'sha': sha, 'path': fp, 'size': len(b)})
    def do_PUT(self):
        if self.headers.get('Authorization') != f'Bearer {TOKEN}': return self.send(401, {'message': 'Bad credentials'})
        fp = unquote(urlparse(self.path).path.split('/contents/', 1)[1]); body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        assert body['branch'] == 'pc-collect'
        if fp in STATE['files'] and 'sha' not in body: return self.send(422, {'message': 'sha missing'})
        STATE['files'][fp] = base64.b64decode(body['content']); return self.send(201, {'content': {'path': fp}})

srv = ThreadingHTTPServer(('127.0.0.1', 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{srv.server_address[1]}'
HOMED = tempfile.mkdtemp(prefix='rc_home_')
json.dump({'tab_base': BASE, 'gh_base': BASE}, open(os.path.join(HOMED, 'config.json'), 'w'))
def run(*args, now='2026-11-25T21:30:30Z'):
    env = dict(os.environ, RC_HOME=HOMED, RC_FAST='1', RC_GITHUB_TOKEN=TOKEN, RC_NOW=now)
    p = subprocess.run([sys.executable, '-I', COLLECTOR, *args], env=env, capture_output=True, text=True, timeout=300)
    return p.returncode, p.stdout + p.stderr
fails = 0
def check(name, cond, info=''):
    global fails
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else f'  -> {info}')); fails += (not cond)

# 1. morning, one race failing once (retried inside the job)
STATE['fail_once'].add(('HAW', 3, None))
rc, out = run('morning')
check('morning exits 0', rc == 0, out[-800:])
man = json.loads(STATE['files'].get(f'pc/{D}/morning_manifest.json', b'{}'))
check('morning manifest verified + complete', man.get('delivered_verified') and man.get('complete'), man)
f = [x for x in man.get('files', []) if x['path'].endswith('.raw.txt')]
body = STATE['files'][f[0]['path']].decode() if f else ''
check('file sha256 in manifest matches upload', f and hashlib.sha256(body.encode()).hexdigest() == f[0]['sha256'])
races = [l for l in body.splitlines() if l.startswith('RACE|')]
vens = {l.split('|')[1] for l in body.splitlines() if l.startswith(('MEET|', 'RACE|'))}
check('all 29 races, none international or harness', len(races) == len(RACES) and 'CHE' not in vens and 'APH' not in vens, (len(races), vens))
mismatch = []
for l in races:
    p = l.split('|'); k = (p[1], int(p[2])); orig = RACES[k]['line'].split('|')
    if p[:10] != orig[:10] or len(p) != 11: mismatch.append((k, p[:10], orig[:10]))
check('RACE lines identical to the WebFetch file (except observation time)', not mismatch, mismatch[:2])
rl = [l.split('|') for l in body.splitlines() if l and l[0].isdigit()]
orig_runners = [r for k in sorted(RACES) for r in RACES[k]['runners']]
check('runner lines: same count and 12 fields', len(rl) == len(orig_runners) and all(len(x) == 12 for x in rl), (len(rl), len(orig_runners)))
by = {}
for k in sorted(RACES):
    for r in RACES[k]['runners']: by[(k, r[0])] = r
cur = None; diffs = []
for l in body.splitlines():
    p = l.split('|')
    if p[0] == 'RACE': cur = (p[1], int(p[2]))
    elif cur and p[0].isdigit():
        o = by[(cur, p[0])]
        if p[:11] != o[:11]: diffs.append((cur, p, o))
check('runner fields identical to the WebFetch file', not diffs, diffs[:2])
check('MEET lines present', sum(l.startswith('MEET|') for l in body.splitlines()) == len(MEETS))
check('observation time per race recorded', all(re.match(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$', l.split('|')[10]) for l in races))
n_put = len(STATE['files']); rc, out = run('morning')
check('second morning run does nothing (idempotent)', rc == 0 and 'already delivered' in out, out[-300:])

# 2. form records, one runner failing once
STATE['fail_once'].add(('GER', 2, '3'))
rc, out = run('form')
check('form exits 0', rc == 0, out[-800:])
fm = json.loads(STATE['files'].get(f'pc/{D}/form_manifest.json', b'{}'))
check('form manifest complete, nothing missing', fm.get('complete') and not fm.get('missing') and fm.get('expected') == len(orig_runners), {k: fm.get(k) for k in ('expected', 'retrieved', 'missing')})
ff = [x['path'] for x in fm.get('files', [])]
text = gzip.decompress(STATE['files'][ff[0]]).decode() if ff else ''
check('no odds in form file', '7.5' not in text and '3.2|' not in text and 'tipster' not in text)
check('every PS line has 15 fields', all(len(l.split('|')) == 15 for l in text.splitlines() if l.startswith('PS|')))
check('pipes and line breaks inside text removed', 'DAM WITH PIPES' in text and 'Raced keenly. Line two' in text)
tmp = tempfile.mkdtemp(); open(os.path.join(tmp, 'f.raw.txt'), 'w').write(text)
p = subprocess.run([sys.executable, os.path.join(REPO_ROOT, 'research', 'ops', 'parse_form.py'), os.path.join(tmp, 'out'), os.path.join(tmp, 'f.raw.txt')], capture_output=True, text=True)
check('research/ops/parse_form.py reads it with 0 rejected lines', 'rejected PS lines (too few fields, see form_rejected_lines.csv) 0' in p.stdout and f'form records {len(orig_runners)}' in p.stdout, p.stdout + p.stderr)
rc, out = run('form'); check('second form run does nothing', 'already delivered' in out)

# 3. evening: first pass with some races still running, later pass completes, final run after 03:00
for k in RACES:
    STATE['status'][k] = 'Paying' if k[0] != 'GER' else ('Closed' if k[1] >= 7 else 'Paying')
rc, out = run('evening', now='2026-11-26T09:30:00Z')            # 19:30 Brisbane
em = json.loads(STATE['files'].get(f'pc/{D}/evening_manifest.json', b'{}'))
check('evening: unfinished WA races listed, not dropped', em.get('unresolved') == ['GER|7', 'GER|8'] and not em.get('complete'), em.get('unresolved'))
res = STATE['files'][f'pc/{D}/results.raw.txt'].decode()
rr = [l for l in res.splitlines() if l.startswith('RACE|')]
check('evening: unfinished races kept with their status', any(l.startswith('RACE|GER|7|') and l.endswith('|Closed') for l in rr) and len(rr) == len(RACES), len(rr))
won = [l for l in res.splitlines() if l and l[0].isdigit() and l.split('|')[11] == '1']
check('evening: winners recorded from results array', len(won) == len(RACES) - 2, len(won))
check('evening: RACE line has 12 fields (status last)', all(len(l.split('|')) == 12 for l in res.splitlines() if l.startswith('RACE|')))
STATE['status'][('GER', 7)] = 'Paying'
rc, out = run('evening', now='2026-11-26T14:40:00Z')            # 00:40 Brisbane next calendar day: still race day 26th
em = json.loads(STATE['files'].get(f'pc/{D}/evening_manifest.json', b'{}'))
check('evening after midnight belongs to the race day', em.get('date') == D and em.get('unresolved') == ['GER|8'], em)
rc, out = run('evening', now='2026-11-26T17:05:00Z')            # 03:05 Brisbane: final run
em = json.loads(STATE['files'].get(f'pc/{D}/evening_manifest.json', b'{}'))
check('final run marks still-unresolved race explicitly', em.get('final_run') and em.get('unresolved') == ['GER|8'], em)
settle = subprocess.run([sys.executable, '-c', f'''
import sys; lines=open(sys.argv[1]).read().splitlines(); r=[l for l in lines if l.startswith("RACE|")]; print(len(r))'''], capture_output=True, text=True)

# 4. delivery read-back corruption is caught and retried
STATE['gh_corrupt_once'].add('pc/selftest/' + __import__('socket').gethostname() + '.json')
rc, out = run('selftest')
check('selftest passes (incl. one corrupted read-back retried)', rc == 0 and 'SELFTEST PASSED' in out and 'read-back mismatch' in out, out[-500:])

# 5. TAB answering with its website page instead of data: job fails loudly, nothing delivered as complete
STATE['tab_html'] = True; shutil.rmtree(os.path.join(HOMED, 'state'), ignore_errors=True)
before = STATE['files'].get(f'pc/{D}/morning_manifest.json')
rc, out = run('morning', now='2026-11-26T21:30:30Z')
check('TAB website page instead of JSON -> error exit, heartbeat ok=false', rc == 1 and json.loads(STATE['files'].get('pc/heartbeat/morning.json', b'{}')).get('ok') is False, out[-400:])
STATE['tab_html'] = False
# 6. no token -> clear message
env = dict(os.environ, RC_HOME=tempfile.mkdtemp(), RC_FAST='1')
p = subprocess.run([sys.executable, '-I', COLLECTOR, 'selftest'], env=env, capture_output=True, text=True)
check('missing token -> clear instruction, no crash dump of secrets', 'run install.ps1 again' in (p.stdout + p.stderr))

# 7. crash part-way, then resume: no duplicates, nothing lost (fresh install folder, next day's date reuses fixtures)
HOMED2 = tempfile.mkdtemp(prefix='rc_home2_'); json.dump({'tab_base': BASE, 'gh_base': BASE}, open(os.path.join(HOMED2, 'config.json'), 'w'))
def run2(*args, now='2026-11-25T21:30:30Z', extra=None):
    env = dict(os.environ, RC_HOME=HOMED2, RC_FAST='1', RC_GITHUB_TOKEN=TOKEN, RC_NOW=now, **(extra or {}))
    p = subprocess.run([sys.executable, '-I', COLLECTOR, *args], env=env, capture_output=True, text=True, timeout=300); return p.returncode, p.stdout + p.stderr
for k in list(STATE['files']):
    if k.startswith(f'pc/{D}/'): del STATE['files'][k]
rc, out = run2('morning', extra={'RC_TEST_CRASH_AFTER': '11'})
check('crash simulated after 11 races', rc == 99 and f'pc/{D}/morning_manifest.json' not in STATE['files'], rc)
os.remove(os.path.join(HOMED2, 'state', 'locks', 'morning.lock')) if os.path.exists(os.path.join(HOMED2, 'state', 'locks', 'morning.lock')) else None
rc, out = run2('morning')
man = json.loads(STATE['files'].get(f'pc/{D}/morning_manifest.json', b'{}'))
body = STATE['files'][[x['path'] for x in man['files']][0]].decode()
keys = [tuple(l.split('|')[1:3]) for l in body.splitlines() if l.startswith('RACE|')]
check('resume completes all races exactly once', rc == 0 and len(keys) == len(set(keys)) == len(RACES) and man.get('complete'), (rc, len(keys), len(set(keys))))
rc, out = run2('form', extra={'RC_TEST_CRASH_AFTER': '50'})
lk = os.path.join(HOMED2, 'state', 'locks', 'form.lock'); os.path.exists(lk) and os.remove(lk)
rc, out = run2('form')
fm = json.loads(STATE['files'].get(f'pc/{D}/form_manifest.json', b'{}'))
text = gzip.decompress(STATE['files'][fm['files'][0]['path']]).decode()
heads = [l for l in text.splitlines() if l.startswith('FORM|')]
check('form resume: every runner exactly once', fm.get('complete') and len(heads) == len(orig_runners), (len(heads), len(orig_runners)))
# 8. catch-up after the PC was off at 07:30: collects late (flagged) before the first race; refuses after racing starts
HOMED3 = tempfile.mkdtemp(prefix='rc_home3_'); json.dump({'tab_base': BASE, 'gh_base': BASE}, open(os.path.join(HOMED3, 'config.json'), 'w'))
env3 = lambda now: dict(os.environ, RC_HOME=HOMED3, RC_FAST='1', RC_GITHUB_TOKEN=TOKEN, RC_NOW=now)
for k in list(STATE['files']):
    if k.startswith(f'pc/{D}/'): del STATE['files'][k]
p = subprocess.run([sys.executable, '-I', COLLECTOR, 'catchup'], env=env3('2026-11-25T23:00:00Z'), capture_output=True, text=True, timeout=300)
man = json.loads(STATE['files'].get(f'pc/{D}/morning_manifest.json', b'{}'))
check('catch-up at 09:00 collects the missed morning, flagged LATE', man.get('late') is True and man.get('complete'), {k: man.get(k) for k in ('late', 'complete')})
fm = json.loads(STATE['files'].get(f'pc/{D}/form_manifest.json', b'{}'))
check('catch-up also runs the form job', fm.get('complete') is True, fm.get('retrieved'))
HOMED4 = tempfile.mkdtemp(prefix='rc_home4_'); json.dump({'tab_base': BASE, 'gh_base': BASE}, open(os.path.join(HOMED4, 'config.json'), 'w'))
for k in list(STATE['files']):
    if k.startswith(f'pc/{D}/'): del STATE['files'][k]
p = subprocess.run([sys.executable, '-I', COLLECTOR, 'catchup'], env=dict(os.environ, RC_HOME=HOMED4, RC_FAST='1', RC_GITHUB_TOKEN=TOKEN, RC_NOW='2026-11-26T04:00:00Z'),
                   capture_output=True, text=True, timeout=300)
check('catch-up after racing began: no late pre-race snapshot', f'pc/{D}/morning_manifest.json' not in STATE['files'] and 'not collected late' in (p.stdout + p.stderr), (p.stdout + p.stderr)[-400:])

print('ALL PASSED' if not fails else f'{fails} FAILED'); sys.exit(1 if fails else 0)
