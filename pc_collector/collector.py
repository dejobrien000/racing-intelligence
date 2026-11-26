"""Racing Intelligence PC collector (runs on Damo's Windows PC from Task Scheduler; standard library only).

Jobs (each idempotent, resumable, safe to re-run; see INSTALL.md):
  morning   07:30 Brisbane. TAB calendar + every Australian thoroughbred racecard (fields and OPEN fixed prices), written in
            the exact raw format of research/ops/DAILY_RUN.md step 2 with each race's real observation time (UTC).
  form      07:40. TAB runner form records for every runner in this morning's racecards (DAILY_RUN step 5b format).
            Never stores odds. Runs on its own so a long form collection can never delay the ratings.
  evening   18:30 to 03:00, every 30 minutes. Completed racecards (results + final TAB fixed prices) for every race of the
            day, captured once each race is Paying/Final/Abandoned; later runs fill the races that were not yet final
            (WA night racing). The last run of the night lists races still unresolved instead of dropping them.
  catchup   at start-up, at log-on and every 2 hours: runs any job that was missed (PC asleep or off) while it is still
            useful, and re-delivers anything whose delivery to GitHub was not verified.
  selftest  reads the TAB calendar, uploads and reads back a test file on branch pc-collect.
  status    prints today's job states.

Delivery: GitHub contents API, branch pc-collect, folder pc/<YYYYMMDD>/. Every file is read back and compared (sha256)
before the job's manifest is written; the manifest goes last, so downstream never sees a file that did not arrive whole.
Market separation: racecard/results prices are the evaluation layer the cloud pipeline already keeps away from ratings;
form files never contain odds (only the listed non-market fields are written)."""
import sys, os, json, time, random, hashlib, base64, gzip, socket, re, traceback, urllib.request, urllib.error, urllib.parse
import datetime as dt

VERSION = '1.0.0'
APP = os.path.dirname(os.path.abspath(__file__))
HOME = os.environ.get('RC_HOME') or os.path.dirname(APP)            # install folder (app\ lives inside it)
CFG = {
    'repo': 'dejobrien000/racing-intelligence', 'branch': 'pc-collect',
    'tab_base': 'https://api.beta.tab.com.au', 'gh_base': 'https://api.github.com',
    'states': ['NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'NT', 'ACT'],
    'pause_s': [2.0, 3.0], 'evening_last_local': '03:00', 'morning_late_after_local': '07:45',
    'user_agent': f'RacingIntelligence-PC/{VERSION} (private non-commercial research; github.com/dejobrien000)',
}
try: CFG.update(json.load(open(os.path.join(HOME, 'config.json'))))
except FileNotFoundError: pass
BNE = dt.timezone(dt.timedelta(hours=10))                               # Brisbane: UTC+10, no daylight saving
FINAL = {'paying', 'final', 'abandoned'}

def now_utc():
    t = os.environ.get('RC_NOW')                                        # tests only
    return dt.datetime.fromisoformat(t.replace('Z', '+00:00')) if t else dt.datetime.now(dt.timezone.utc)
def iso(t=None): return (t or now_utc()).strftime('%Y-%m-%dT%H:%M:%SZ')
def stamp(t=None): return (t or now_utc()).strftime('%Y%m%dT%H%M%SZ')
def bne_today(): return now_utc().astimezone(BNE).date()
def bne_local(): return now_utc().astimezone(BNE)
def pause():
    if os.environ.get('RC_FAST'): return
    time.sleep(random.uniform(*CFG['pause_s']))

# ---------- logging, state, locks ----------
def path(*p):
    q = os.path.join(HOME, *p); os.makedirs(os.path.dirname(q), exist_ok=True); return q
LOGF = None
def log(*a):
    global LOGF
    msg = f'{iso()} ' + ' '.join(str(x) for x in a)
    print(msg, flush=True)
    if LOGF is None: LOGF = open(path('logs', f'{bne_today():%Y%m%d}.log'), 'a', encoding='utf-8')
    LOGF.write(msg + '\n'); LOGF.flush()
def write_atomic(p, data, mode='w'):
    os.makedirs(os.path.dirname(p), exist_ok=True); tmp = p + '.tmp'
    with open(tmp, mode, **({} if 'b' in mode else {'encoding': 'utf-8'})) as fh: fh.write(data)
    os.replace(tmp, p)
def state_path(D, job): return path('state', D, f'{job}.json')
def load_state(D, job):
    try: return json.load(open(state_path(D, job), encoding='utf-8'))
    except FileNotFoundError: return {}
def save_state(D, job, st): st['updated_utc'] = iso(); write_atomic(state_path(D, job), json.dumps(st, indent=1))
class Lock:
    def __init__(self, name): self.p = path('state', 'locks', name + '.lock')
    def __enter__(self):
        if os.path.exists(self.p) and time.time() - os.path.getmtime(self.p) < 4 * 3600:
            log('another run of this job is active; exiting'); sys.exit(0)
        write_atomic(self.p, str(os.getpid())); return self
    def __exit__(self, *a):
        try: os.remove(self.p)
        except OSError: pass
def keep_awake(on=True):
    if os.name == 'nt':
        import ctypes
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))   # ES_CONTINUOUS|ES_SYSTEM_REQUIRED

# ---------- HTTP ----------
class HTTPFail(Exception): pass
def http(method, url, body=None, headers=None, tries=4, ok=(200,), raw=False):
    h = {'User-Agent': CFG['user_agent']}; h.update(headers or {})
    data = None if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    last = None
    for a in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=h, method=method)
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
                if r.status in ok: return (b if raw else (json.loads(b.decode('utf-8')) if b else {})), r.status
                last = f'HTTP {r.status}'
        except urllib.error.HTTPError as e:
            b = e.read()
            if e.code in ok: return (b if raw else (json.loads(b.decode('utf-8')) if b else {})), e.code
            last = f'HTTP {e.code} {b[:200]!r}'
            if e.code in (400, 401, 403, 404, 422) and a >= 1: break
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
            last = f'{type(e).__name__}: {e}'
        if a < tries - 1: time.sleep(0 if os.environ.get('RC_FAST') else min(60, 5 * 2 ** a) + random.random())
    raise HTTPFail(f'{method} {url.split("?")[0]}: {last}')

# ---------- TAB ----------
def tab_json(url):
    j, _ = http('GET', url + ('&' if '?' in url else '?') + f'cb={int(time.time() * 1000)}{random.randint(0, 999)}',
                headers={'Accept': 'application/json'})
    if not isinstance(j, dict): raise HTTPFail('TAB answered with something that is not JSON data')
    return j
def jur(state): return 'QLD' if state == 'QLD' else 'NSW'
def u_meetings(D): return f"{CFG['tab_base']}/v1/tab-info-service/racing/dates/{D[:4]}-{D[4:6]}-{D[6:]}/meetings?jurisdiction=NSW"
def u_race(D, ven, n, j): return f"{CFG['tab_base']}/v1/tab-info-service/racing/dates/{D[:4]}-{D[4:6]}-{D[6:]}/meetings/R/{ven}/races/{n}?jurisdiction={j}"
def u_form(D, ven, n, r, j): return f"{CFG['tab_base']}/v1/tab-info-service/racing/dates/{D[:4]}-{D[4:6]}-{D[6:]}/meetings/R/{ven}/races/{n}/form/{r}?jurisdiction={j}"
def f(v, absent='null'):
    """One field for a |-separated line: booleans lower case, None -> absent, no separators or line breaks inside."""
    if v is None: return absent
    if isinstance(v, bool): return 'true' if v else 'false'
    if isinstance(v, float) and v.is_integer(): v = int(v)
    return re.sub(r'[|\r\n]+', ' ', str(v)).strip()
def g(d, *keys):
    for k in keys:
        if not isinstance(d, dict): return None
        d = d.get(k)
    return d
def meetings_today(D):
    j = tab_json(u_meetings(D)); out = []
    for m in j.get('meetings') or []:
        if m.get('raceType') != 'R' or str(m.get('location', '')).upper() not in CFG['states']: continue
        races = sorted(int(r['raceNumber']) for r in m.get('races') or [] if r.get('raceNumber') is not None)
        starts = [r.get('raceStartTime') for r in m.get('races') or [] if r.get('raceStartTime')]
        out.append({'ven': m['venueMnemonic'], 'name': m.get('meetingName', ''), 'state': str(m['location']).upper(), 'races': races,
                    'first_start': min(starts) if starts else None})
    return out
def finish_positions(results):
    pos, place = {}, 1
    for grp in results or []:
        grp = grp if isinstance(grp, list) else [grp]
        for n in grp: pos[int(n)] = place
        place += len(grp)
    return pos
def race_lines(rc, ven, cap, with_results=False):
    """RACE line + runner lines exactly as DAILY_RUN step 2 (morning) or the evening results file."""
    track = g(rc, 'meeting', 'trackCondition') or rc.get('trackCondition')
    rail = rc.get('railPosition') if rc.get('railPosition') is not None else None
    head = ['RACE', ven, f(rc.get('raceNumber')), f(rc.get('raceName')), f(rc.get('raceStartTime')), f(rc.get('raceDistance')),
            f(track), f(rail), f(rc.get('hasFixedOdds')), f(rc.get('fixedOddsUpdateTime')), cap]
    if with_results: head.append(f(rc.get('raceStatus')))
    pos = finish_positions(rc.get('results')) if with_results else {}
    lines = ['|'.join(head)]
    for r in sorted(rc.get('runners') or [], key=lambda x: int(x.get('runnerNumber') or 0)):
        n = int(r.get('runnerNumber'))
        lines.append('|'.join([f(n), f(r.get('runnerName')), f(r.get('barrierNumber')), f(r.get('handicapWeight')), f(r.get('claimAmount')),
                               f(r.get('riderDriverName')), f(r.get('trainerName')), f(r.get('emergency')),
                               f(g(r, 'fixedOdds', 'returnWin')), f(g(r, 'fixedOdds', 'returnPlace')), f(g(r, 'fixedOdds', 'bettingStatus')),
                               f(pos.get(n), '-') if with_results else '-']))
    return lines
FORM_FIELDS = ('runnerNumber', 'runnerName', 'age', 'sex', ('runnerStarts', 'startSummaries', 'overall', 'numberOfStarts'),
               ('runnerStarts', 'startSummaries', 'overall', 'numberOfWins'), ('runnerStarts', 'startSummaries', 'overall', 'numberOfPlacings'),
               'runsSinceSpell', 'daysSinceLastRun', 'blinkers', 'classLevel', 'sire', 'dam', 'trainerName')
PS_FIELDS = ('startType', 'startDate', 'venueAbbreviation', 'distance', 'class', 'finishingPosition', 'numberOfStarters', 'draw',
             'margin', 'positionInRun', 'trackCondition', 'time', 'rider', 'stewardsComment')   # never 'odds'
def form_lines(fj):
    get = lambda k: g(fj, *k) if isinstance(k, tuple) else fj.get(k)
    out = ['FORM|' + '|'.join(f(get(k), '-') for k in FORM_FIELDS)]
    for ps in g(fj, 'runnerStarts', 'previousStarts') or []:
        out.append('PS|' + '|'.join(f(ps.get(k), '-') for k in PS_FIELDS))
    return out

# ---------- GitHub delivery ----------
def token():
    t = os.environ.get('RC_GITHUB_TOKEN')
    if t: return t
    p = os.path.join(HOME, 'secret', 'github_token.bin')
    if not os.path.exists(p): raise SystemExit('No GitHub token stored: run install.ps1 again (it asks for the token).')
    return dpapi(open(p, 'rb').read(), protect=False).decode('utf-8')
def dpapi(data, protect=True):
    """Windows DPAPI, machine scope + app entropy (works for tasks that run while nobody is logged on); file ACL limits it
    to Damo's account (set by install.ps1). Never used off Windows."""
    import ctypes, ctypes.wintypes as W
    class BLOB(ctypes.Structure): _fields_ = [('cbData', W.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]
    def blob(b): buf = ctypes.create_string_buffer(b, len(b)); return BLOB(len(b), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char))), buf
    ent = b'RacingIntelligence-PC-collector'
    i, ib = blob(data); e, eb = blob(ent); o = BLOB()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    ok = fn(ctypes.byref(i), (ctypes.c_wchar_p('rc') if protect else None), ctypes.byref(e), None, None, (0x4 | 0x1) if protect else 0x1, ctypes.byref(o))
    if not ok: raise SystemExit('Could not unlock the stored GitHub token (DPAPI). Run install.ps1 again.')
    r = ctypes.string_at(o.pbData, o.cbData); ctypes.windll.kernel32.LocalFree(o.pbData); return r
def gh(method, p, body=None, ok=(200,), raw=False):
    url = f"{CFG['gh_base']}/repos/{CFG['repo']}/{p}"
    hd = {'Authorization': f'Bearer {token()}', 'Accept': 'application/vnd.github.raw' if raw else 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28'}
    if body is not None: hd['Content-Type'] = 'application/json'
    return http(method, url, body, hd, ok=ok, raw=raw)
def gh_put_verified(rpath, data, msg):
    """Upload one file to branch pc-collect and read it back; returns its sha256. Raises unless the read-back matches."""
    q = urllib.parse.quote(rpath); br = CFG['branch']; want = hashlib.sha256(data).hexdigest()
    for attempt in range(4):
        try:
            meta, st = gh('GET', f'contents/{q}?ref={br}', ok=(200, 404))
            sha = meta.get('sha') if st == 200 else None
            gh('PUT', f'contents/{q}', {'message': msg, 'branch': br, 'content': base64.b64encode(data).decode(), **({'sha': sha} if sha else {})}, ok=(200, 201))
            back, _ = gh('GET', f'contents/{q}?ref={br}', raw=True)
            if hashlib.sha256(back).hexdigest() == want: return want
            log('read-back mismatch for', rpath, '- retrying')
        except HTTPFail as e:
            log('delivery attempt', attempt + 1, 'failed:', e)
        time.sleep(0 if os.environ.get('RC_FAST') else 10 * (attempt + 1))
    raise HTTPFail(f'could not deliver {rpath} with a verified read-back')
def deliver(D, job, files, manifest):
    """files: {repo path: bytes}. Each verified, then the manifest (with their sha256) is uploaded and verified last."""
    manifest['files'] = []
    for rp, b in files.items():
        manifest['files'].append({'path': rp, 'bytes': len(b), 'sha256': gh_put_verified(rp, b, f'{job} {D}: {os.path.basename(rp)}')})
    manifest.update({'delivered_verified': True, 'delivered_utc': iso(), 'collector_version': VERSION, 'host': socket.gethostname()})
    gh_put_verified(f'pc/{D}/{job}_manifest.json', json.dumps(manifest, indent=1).encode(), f'{job} {D}: manifest')
    log(job, D, 'delivered and verified:', ', '.join(x['path'] for x in manifest['files']))

# ---------- jobs ----------
def job_morning(D, force=False):
    st = load_state(D, 'morning')
    if st.get('status') == 'delivered' and not force: log('morning', D, 'already delivered'); return st
    if st.get('status') != 'complete' or force:
        started = st.get('started_utc') or iso(); st.update({'status': 'running', 'started_utc': started})
        local = bne_local(); st['late'] = local.strftime('%H:%M') > CFG['morning_late_after_local'] and local.date().strftime('%Y%m%d') == D
        meets = meetings_today(D); pause(); st['meetings'] = meets
        raw = path('data', D, 'racecards.partial')
        done = st.setdefault('races_done', {}); fails = {}
        for m in meets:
            for n in m['races']:
                k = f"{m['ven']}|{n}"
                if k in done: continue
                try:
                    rc = tab_json(u_race(D, m['ven'], n, jur(m['state']))); cap = iso()
                    lines = race_lines(rc, m['ven'], cap); done[k] = {'cap': cap, 'runners': len(lines) - 1}
                    with open(raw, 'a', encoding='utf-8') as fh: fh.write('\n'.join(lines) + '\n')
                    save_state(D, 'morning', st)
                    if os.environ.get('RC_TEST_CRASH_AFTER') and len(done) >= int(os.environ['RC_TEST_CRASH_AFTER']): os._exit(99)   # tests only
                except HTTPFail as e: fails[k] = str(e); log('race failed', k, e)
                pause()
        if fails:                                                       # one more pass for failures before giving up
            for k in list(fails):
                ven, n = k.split('|'); m = next(x for x in meets if x['ven'] == ven)
                try:
                    rc = tab_json(u_race(D, ven, int(n), jur(m['state']))); cap = iso(); lines = race_lines(rc, ven, cap)
                    done[k] = {'cap': cap, 'runners': len(lines) - 1}; fails.pop(k)
                    with open(raw, 'a', encoding='utf-8') as fh: fh.write('\n'.join(lines) + '\n')
                except HTTPFail as e: fails[k] = str(e)
                pause()
        expected = [f"{m['ven']}|{n}" for m in meets for n in m['races']]
        body = open(raw, encoding='utf-8').read() if os.path.exists(raw) else ''
        blocks, cur = {}, None                                          # keep one block per race (a re-run never duplicates)
        for line in body.splitlines():
            if line.startswith('RACE|'): cur = '|'.join(line.split('|')[1:3]); blocks[cur] = [line]
            elif cur and line: blocks[cur].append(line)
        caps = [done[k]['cap'] for k in expected if k in done]; last = max(caps) if caps else iso()
        hdr = [f'# TAB racing info-service racecards for {D[:4]}-{D[4:6]}-{D[6:]} (api.beta.tab.com.au .../meetings/R/<VEN>/races/<n>), read by the PC collector v{VERSION} on {socket.gethostname()}.',
               f'# Scheduled 07:30 Brisbane; job started {st["started_utc"]}{" (LATE: PC was not available at 07:30)" if st.get("late") else ""}. Each RACE line ends with that race\'s own observation time (UTC).',
               '# Direct JSON reads (no AI extraction). jurisdiction=QLD for QLD meetings, NSW otherwise. Prices are the evaluation layer only.']
        hdr += [f"MEET|{m['ven']}|{m['name']}|{m['state']}" for m in meets]
        text = '\n'.join(hdr + [l for k in expected if k in blocks for l in blocks[k]]) + '\n'
        fname = f'tab_{stamp(dt.datetime.fromisoformat(last.replace("Z", "+00:00")))}.raw.txt'
        write_atomic(path('data', D, fname), text)
        st.update({'status': 'complete', 'file': fname, 'races_expected': len(expected), 'races_fetched': sum(k in done for k in expected),
                   'runners': sum(done[k]['runners'] for k in expected if k in done), 'failed': fails, 'finished_utc': iso()})
        save_state(D, 'morning', st)
    text = open(path('data', D, st['file']), encoding='utf-8').read().encode('utf-8')
    man = {k: st.get(k) for k in ('status', 'started_utc', 'finished_utc', 'late', 'races_expected', 'races_fetched', 'runners', 'failed')}
    man.update({'job': 'morning', 'date': D, 'complete': not st.get('failed') and st['races_fetched'] == st['races_expected'],
                'scheduled_local': '07:30', 'meetings': [{k: m[k] for k in ('ven', 'name', 'state', 'races')} for m in st['meetings']]})
    deliver(D, 'morning', {f"pc/{D}/{st['file']}": text}, man)
    st['status'] = 'delivered'; save_state(D, 'morning', st); return st

def runners_from_card(D):
    st = load_state(D, 'morning')
    if st.get('status') not in ('complete', 'delivered'): return None, None
    out, meets = [], {m['ven']: m['state'] for m in st['meetings']}; cur = None
    for line in open(path('data', D, st['file']), encoding='utf-8'):
        p = line.rstrip('\n').split('|')
        if p[0] == 'RACE': cur = (p[1], p[2])
        elif cur and len(p) >= 11 and p[0].isdigit(): out.append((cur[0], cur[1], p[0], p[1], meets.get(cur[0], 'NSW')))
    return out, st
def job_form(D, wait_min=90, force=False):
    st = load_state(D, 'form')
    if st.get('status') == 'delivered' and not force: log('form', D, 'already delivered'); return st
    t0 = time.time()
    while True:
        targets, mst = runners_from_card(D)
        if targets is not None: break
        if time.time() - t0 > wait_min * 60: log('form: no racecards for', D, 'after waiting; exiting (catch-up retries later)'); return st
        log('form: waiting for this morning\'s racecards'); time.sleep(120)
    raw = path('data', D, 'form.raw.txt'); done = set(st.get('done', [])); bad = dict(st.get('failed', {}))
    st.update({'status': 'running', 'expected': len(targets), 'started_utc': st.get('started_utc') or iso()})
    for ven, race, n, name, state in targets:
        k = f'{ven}|{race}|{n}'
        if k in done: continue
        try:
            fj = tab_json(u_form(D, ven, race, n, jur(state))); lines = form_lines(fj); cap = iso()
            if any('$' in x for x in lines): raise HTTPFail('price-like text in a form line; refused')
            with open(raw, 'a', encoding='utf-8') as fh: fh.write('\n'.join([f'{ven}|{race}|{cap}'] + lines) + '\n')
            done.add(k); bad.pop(k, None)
        except HTTPFail as e: bad[k] = str(e); log('form failed', k, e)
        st['done'] = sorted(done); st['failed'] = bad; save_state(D, 'form', st)   # checkpoint after every runner
        if os.environ.get('RC_TEST_CRASH_AFTER') and len(done) >= int(os.environ['RC_TEST_CRASH_AFTER']): os._exit(99)   # tests only
        pause()
    save_state(D, 'form', st)
    exp = [f'{v}|{r}|{n}' for v, r, n, _, _ in targets]
    complete = all(k in done for k in exp)
    if not complete and bne_local().strftime('%H:%M') < '22:00' and st.get('passes', 0) < 3:
        st['passes'] = st.get('passes', 0) + 1; save_state(D, 'form', st); log('form incomplete; catch-up will retry the', len(bad), 'missing'); return st
    body = open(raw, 'rb').read() if os.path.exists(raw) else b''
    fname = f'form_{stamp()}.raw.txt.gz'
    man = {'job': 'form', 'date': D, 'expected': len(exp), 'retrieved': sum(k in done for k in exp), 'missing': [k for k in exp if k not in done],
           'complete': complete, 'started_utc': st['started_utc'], 'finished_utc': iso(), 'racecard_file': mst.get('file'),
           'note': 'Form lines carry no odds. Missing runners are listed, never dropped silently.'}
    deliver(D, 'form', {f'pc/{D}/{fname}': gzip.compress(body, mtime=0)}, man)
    st.update({'status': 'delivered', 'file': fname}); save_state(D, 'form', st); return st

def evening_deadline(D):
    hh, mm = map(int, CFG['evening_last_local'].split(':'))
    return dt.datetime(int(D[:4]), int(D[4:6]), int(D[6:]), hh, mm, tzinfo=BNE) + dt.timedelta(days=1)
def race_day():
    """The race day an evening run belongs to: before 05:00 Brisbane it is still the previous day's evening."""
    return (bne_local() - dt.timedelta(hours=5)).date().strftime('%Y%m%d')
def job_evening(D, final_run=None):
    targets, mst = runners_from_card(D)
    if targets is None: log('evening: no morning racecards for', D, '- nothing to capture'); return {}
    st = load_state(D, 'evening'); races = st.setdefault('races', {})
    meets = {m['ven']: m for m in mst['meetings']}
    changed = False
    for ven, m in meets.items():
        for n in m['races']:
            k = f'{ven}|{n}'
            if races.get(k, {}).get('final'): continue
            try:
                rc = tab_json(u_race(D, ven, n, jur(m['state']))); cap = iso()
                status = str(rc.get('raceStatus') or '').lower()
                races[k] = {'cap': cap, 'status': rc.get('raceStatus'), 'final': status in FINAL, 'lines': race_lines(rc, ven, cap, with_results=True)}
                changed = True
            except HTTPFail as e: log('evening race failed', k, e); races.setdefault(k, {'final': False, 'status': 'unread', 'error': str(e)})
            pause()
    if final_run is None: final_run = now_utc() >= evening_deadline(D)
    unresolved = sorted(k for k, v in races.items() if not v.get('final'))
    st.update({'unresolved': unresolved, 'last_run_utc': iso()}); save_state(D, 'evening', st)
    if not changed and st.get('delivered_unresolved') == unresolved and not (final_run and not st.get('final_delivered')): log('evening: nothing new'); return st
    order = [f'{v}|{n}' for v, m in meets.items() for n in m['races']]
    hdr = [f'# {D[:4]}-{D[4:6]}-{D[6:]} completed TAB racecards read by the PC collector v{VERSION} (direct JSON). Runner fields: runnerNumber|runnerName|barrier|handicapWeight|claimAmount|rider|trainer|emergency|fixedOdds.returnWin (final TAB fixed)|fixedOdds.returnPlace|bettingStatus|finish (TAB results array: top 4 only; a runner that ran outside the top 4 shows status Loser and finish -)',
           '# RACE line: RACE|VEN|raceNumber|raceName|raceStartTime|raceDistance|trackCondition|railPosition|hasFixedOdds|fixedOddsUpdateTime|CAPTURED_UTC|raceStatus',
           f'# Races not final at this capture (kept, marked by raceStatus): {", ".join(unresolved) or "none"}']
    text = '\n'.join(hdr + [l for k in order if k in races and 'lines' in races[k] for l in races[k]['lines']]) + '\n'
    man = {'job': 'evening', 'date': D, 'races_expected': len(order), 'races_final': sum(races.get(k, {}).get('final', False) for k in order),
           'unresolved': unresolved, 'final_run': bool(final_run), 'complete': not unresolved, 'last_capture_utc': iso()}
    deliver(D, 'evening', {f'pc/{D}/results.raw.txt': text.encode('utf-8')}, man)
    st['delivered_unresolved'] = unresolved
    if final_run: st['final_delivered'] = True
    save_state(D, 'evening', st); return st

def first_last_start(D):
    st = load_state(D, 'morning'); ts = []
    if st.get('file'):
        for line in open(path('data', D, st['file']), encoding='utf-8'):
            if line.startswith('RACE|'):
                try: ts.append(dt.datetime.fromisoformat(line.split('|')[4].replace('Z', '+00:00')))
                except ValueError: pass
    return (min(ts), max(ts)) if ts else (None, None)
def job_catchup():
    D = bne_today().strftime('%Y%m%d'); Y = (bne_today() - dt.timedelta(days=1)).strftime('%Y%m%d'); t = now_utc(); local = bne_local()
    # yesterday's evening: finish it if this is still the small hours, else make sure what we have is delivered
    ye = load_state(Y, 'evening')
    if load_state(Y, 'morning').get('file') and (not ye.get('final_delivered')):
        log('catch-up: finishing evening capture for', Y); job_evening(Y)
    if local.strftime('%H:%M') < '05:30': return
    ms = load_state(D, 'morning')
    if ms.get('status') != 'delivered':
        first, _ = first_last_start(D)
        if first is None and ms.get('status') != 'complete':          # no file yet: take first start time from TAB's calendar
            try:
                fs_ = [m['first_start'] for m in meetings_today(D) if m.get('first_start')]
                first = dt.datetime.fromisoformat(min(fs_).replace('Z', '+00:00')) if fs_ else None
            except HTTPFail as e: log('catch-up: calendar unreadable:', e)
        if ms.get('status') == 'complete' or first is None or t < first:
            log('catch-up: morning racecards for', D); job_morning(D)
        else: log('catch-up: morning racecards for', D, 'missed and racing has started; not collected late (no false pre-race snapshot)')
    fs = load_state(D, 'form')
    if fs.get('status') != 'delivered' and load_state(D, 'morning').get('status') in ('complete', 'delivered'):
        log('catch-up: form records for', D); job_form(D, wait_min=0)
    if local.strftime('%H:%M') >= '18:30': job_evening(D)

def job_selftest():
    D = bne_today().strftime('%Y%m%d')
    ms = meetings_today(D); log('TAB calendar OK:', len(ms), 'Australian thoroughbred meetings today', [m['ven'] for m in ms])
    if ms:
        m = ms[0]; rc = tab_json(u_race(D, m['ven'], m['races'][0], jur(m['state'])))
        log('TAB racecard OK:', m['ven'], 'race', m['races'][0], len(rc.get('runners') or []), 'runners')
    b = json.dumps({'host': socket.gethostname(), 'utc': iso(), 'version': VERSION}).encode()
    gh_put_verified(f'pc/selftest/{socket.gethostname()}.json', b, 'PC collector self-test')
    log('GitHub delivery OK (uploaded and read back on branch', CFG['branch'] + ')'); print('SELFTEST PASSED')
    write_atomic(path('state', 'selftest.json'), json.dumps({'passed': True, 'utc': iso(), 'meetings_today': [m['ven'] for m in ms]}))
def heartbeat(job, ok, err=''):
    try:
        b = json.dumps({'host': socket.gethostname(), 'job': job, 'ok': ok, 'error': err[:300], 'utc': iso(), 'version': VERSION}).encode()
        gh_put_verified(f'pc/heartbeat/{job}.json', b, f'heartbeat {job}')
    except Exception as e: log('heartbeat failed:', e)

def main(argv):
    job = argv[1] if len(argv) > 1 else 'status'
    pos = [a for a in argv[2:] if not a.startswith('--')]
    D = pos[0] if pos else (race_day() if job == 'evening' else bne_today().strftime('%Y%m%d'))
    if job == 'status':
        for j in ('morning', 'form', 'evening'): print(j, json.dumps({k: v for k, v in load_state(D, j).items() if k not in ('races', 'done', 'races_done')}))
        return 0
    with Lock(job):
        keep_awake(True)
        try:
            log(f'start {job} {D} v{VERSION}')
            if job == 'morning': job_morning(D, force='--force' in argv)
            elif job == 'form': job_form(D, force='--force' in argv)
            elif job == 'evening': job_evening(D)
            elif job == 'catchup': job_catchup()
            elif job == 'checktoken':                                   # installer/CI diagnostic: can this account unlock the token?
                t = token(); write_atomic(path('state', 'tokencheck.json'), json.dumps({'ok': True, 'sha256_8': hashlib.sha256(t.encode()).hexdigest()[:8], 'utc': iso()})); return 0
            elif job == 'selftest':
                try: job_selftest(); return 0
                except BaseException as e:
                    write_atomic(path('state', 'selftest.json'), json.dumps({'passed': False, 'utc': iso(), 'error': repr(e)[:500]})); raise
            else: print(__doc__); return 2
            heartbeat(job, True); log(f'end {job} {D}'); return 0
        except SystemExit: raise
        except Exception as e:
            log('ERROR', job, D, repr(e)); log(traceback.format_exc()); heartbeat(job, False, repr(e)); return 1
        finally: keep_awake(False)
if __name__ == '__main__': sys.exit(main(sys.argv))
