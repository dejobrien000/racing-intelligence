"""Daily TAB racecards and nightly results -> master-database staging tables (approved by Damo 26 Nov 2026, foundation step 1;
runs at the weekly update). Every file is kept as its own snapshot: the 7:30am pre-race card, the evening results capture and
any later re-read (amendments) stay side by side with their own capture times. Nothing is overwritten by a later file.

MARKET SEPARATION: the files also carry TAB fixed prices (win/place). Those columns are NOT read: no price column exists in these
tables. Prices stay in prices/ for display and returns only.

Usage: python3 history/load_tab_daily.py <history.duckdb> <collect/national dir> [<pc dir>]
Tables (replaced as a whole each run from the files, so the load is repeatable):
  tab_file    one row per file: kind (morning | results), race_date, sha256, captured range, races, runners
  tab_race    one row per race per file: venue code, meeting name, state, race no, name, start (UTC), distance, track condition,
              rail (null when TAB gives none), captured_utc, race_status (results files only)
  tab_runner  one row per runner per file: saddlecloth, horse, name_key, barrier, allocated weight, claim (claim_kg 0 when TAB
              says none, i.e. -1; claim_raw keeps TAB's value), rider, trainer, emergency, betting_status (incl. scratchings),
              finish_pos and finish_supplied. TAB results give finishing positions 1-4 ONLY: finish_supplied = 1 for those,
              0 for every other runner (unknown place, NOT unplaced-by-evidence). Barrier 0 or blank = not given (null)."""
import sys, os, re, glob, hashlib, json, datetime as dt
import duckdb, pandas as pd
DB, NAT = sys.argv[1], sys.argv[2]; PC = sys.argv[3] if len(sys.argv) > 3 else None
def nk(s): return re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', str(s).upper()))
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return None
nul = lambda x: None if x in (None, '', 'null', 'None', '-') else x
F, RACES, RUN = [], [], []
paths = sorted(glob.glob(os.path.join(NAT, '*', 'tab_*.raw.txt'))) + sorted(glob.glob(os.path.join(NAT, '*', 'results_*.raw.txt')))
if PC: paths += sorted(glob.glob(os.path.join(PC, '*', '*.raw.txt')))
for p in paths:
    kind = 'results' if os.path.basename(p).startswith('results') else 'morning'
    D = os.path.basename(os.path.dirname(p)); rd = f'{D[:4]}-{D[4:6]}-{D[6:]}' if re.fullmatch(r'\d{8}', D) else None
    raw = open(p, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    meet = {}
    rc = os.path.join(os.path.dirname(p), 'races.csv'); cj = os.path.join(os.path.dirname(p), 'calendar.json')
    if os.path.exists(rc):
        for r in pd.read_csv(rc, dtype=str).itertuples():
            meet[str(getattr(r, 'venue_code')).upper()] = (getattr(r, 'venue'), getattr(r, 'state'))
    if os.path.exists(cj):   # the day's calendar names each meeting's TAB code
        for m in json.load(open(cj)).get('meetings', []):
            if m.get('tab_code'): meet[m['tab_code'].upper()] = (m.get('name'), m.get('state'))
    cur = None; nr = nn = 0; caps = []
    for ln in raw.decode('utf-8', 'replace').splitlines():
        if not ln or ln.startswith('#'): continue
        f = ln.split('|')
        if f[0] == 'MEET' and len(f) >= 4: meet[f[1]] = (f[2], f[3]); continue
        if f[0] == 'RACE':
            ven = f[1]; mn, st = meet.get(ven, (None, None)); cap = f[10] if len(f) > 10 else None; caps.append(cap)
            cur = {'file': os.path.relpath(p), 'kind': kind, 'race_date': rd, 'venue_code': ven, 'meeting_name': mn, 'state': st, 'race_no': int(f[2]),
                   'race_name': f[3], 'start_utc': nul(f[4]), 'distance_m': num(nul(f[5])), 'track_condition': nul(f[6]), 'rail': nul(f[7]),
                   'captured_utc': cap, 'race_status': (f[11] if kind == 'results' and len(f) > 11 else None)}
            RACES.append(cur); nr += 1; continue
        if cur is None or not f[0].isdigit() or len(f) < 11: continue
        fin = f[11] if len(f) > 11 else '-'
        cl = num(nul(f[4]))
        RUN.append({'file': cur['file'], 'kind': kind, 'race_date': rd, 'venue_code': cur['venue_code'], 'race_no': cur['race_no'], 'saddlecloth': int(f[0]),
                    'horse': f[1], 'name_key': nk(f[1]), 'barrier': (int(float(f[2])) if num(nul(f[2])) and float(f[2]) > 0 else None),
                    'weight_alloc_kg': num(nul(f[3])), 'claim_raw': cl, 'claim_kg': (0.0 if cl is not None and cl < 0 else cl),
                    'rider': nul(f[5]), 'trainer': nul(f[6]), 'emergency': str(f[7]).lower() == 'true', 'betting_status': nul(f[10]),
                    'finish_pos': (int(fin) if kind == 'results' and fin.isdigit() else None),
                    'finish_supplied': int(kind == 'results' and fin.isdigit()), 'captured_utc': cur['captured_utc']})
        nn += 1
    caps = [c for c in caps if c]
    F.append({'file': os.path.relpath(p), 'kind': kind, 'race_date': rd, 'sha256': sha, 'bytes': len(raw), 'races': nr, 'runners': nn,
              'captured_first_utc': min(caps) if caps else None, 'captured_last_utc': max(caps) if caps else None,
              'loaded_utc': dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')})
con = duckdb.connect(DB)
for name, rows in [('tab_file', F), ('tab_race', RACES), ('tab_runner', RUN)]:
    df = pd.DataFrame(rows)
    assert not any(re.search(r'price|odds|win$|place$|return', c, re.I) for c in df.columns), f'market column in {name}'
    con.register('d_', df); con.execute(f'create or replace table {name} as select * from d_'); con.unregister('d_')
k = pd.DataFrame(RUN)
print(f"tab daily: files {len(F)} ({sum(f['kind'] == 'morning' for f in F)} morning, {sum(f['kind'] == 'results' for f in F)} results) | races {len(RACES)} | runner rows {len(RUN)}"
      + (f" | barriers given {int(k.barrier.notna().sum())} | finishing positions supplied {int(k.finish_supplied.sum())} (TAB gives 1-4 only)" if len(k) else ''))
