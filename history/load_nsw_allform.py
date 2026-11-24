"""Load Racing NSW "All Form" bundles (racing_nsw_allform_*.jsonl.gz, keys nswform:KEY) into history.duckdb.
Each horse's career form lines become one row per past run in table nsw_form_line (deduplicated across meetings:
the same run seen on several form pages is kept once, from the latest page). Prices were removed by the collector;
the loader refuses a line that still has a price sequence.
Usage: python3 load_nsw_allform.py <bundle folder> <history.duckdb>"""
import sys, os, re, glob, gzip, json, duckdb, pandas as pd
folder, db = sys.argv[1], sys.argv[2]
HDR = re.compile(r"^\d+\s+(?P<name>.+?)\s+(?:\([^)]*\)\s+)?(?P<age>\d+) year old (?P<colour>[a-z/ ]+?) (?P<sex>colt|filly|gelding|mare|horse|rig) \((?P<dob>[\d-]+)\) Sire: (?P<sire>.+?) Dam: (?P<dam>.+?)(?: View|$)", re.I)
HEAD = re.compile(r"^(?P<trk>.+?) (?P<date>\d{2}[A-Z][a-z]{2}\d{2}) (?P<dist>\d+)m (?P<going>[A-Za-z]+)(?P<gnum>\d*) (?P<rest>.*)$")
MID = re.compile(r"^(?P<cls>.*?)\s*\$(?P<prize>[\d,]+)(?: \(\$(?P<won>[\d,]+)\))? (?P<jockey>.+?) (?P<wt>[\d.]+)kg(?: \(cd (?P<cd>[\d.]+)kg\))? Barrier (?P<bar>\d+)(?: Rtg (?P<rtg>\d+))?")
TAIL = re.compile(r"(?P<time>\d+:\d{2}\.\d{2})(?: \(600m (?P<l600>[\d.]+)\))?(?:, (?P<mgn>[\d.]+)L)?(?:, (?P<p800>\d+)\w{2}@800m)?(?:, (?P<p400>\d+)\w{2}@400m)?")
best, horses = {}, {}
for f in sorted(glob.glob(os.path.join(folder, 'racing_nsw_allform_*.jsonl.gz'))):
    for line in gzip.open(f, 'rt', encoding='utf-8'):
        if not line.strip(): continue
        o = json.loads(line); v = o['value']; stamp = v.get('retrieved_utc', '')
        for h in v.get('horses', []):
            m = HDR.match(h.get('header', ''))
            if not m: continue
            name = re.sub(r'\s+', ' ', m.group('name')).strip(); nk = re.sub(r'\s*\([A-Z]{2,3}\)$', '', name).upper().replace("'", '')
            hid = (nk, m.group('dob')); horses[hid] = {'name_key': nk, 'horse': name, 'dob': m.group('dob'), 'sex': m.group('sex').lower(), 'colour': m.group('colour'),
                                                       'sire': m.group('sire').strip(), 'dam': m.group('dam').strip()}
            for ln in h.get('lines', []):
                t, pos = ln.get('txt', ''), ln.get('pos', '')
                if re.search(r'\$\d[\d.]*/\$', t): raise SystemExit('price sequence found; refusing to load')
                hm = HEAD.match(t)
                if not hm or not pos: continue
                k = (nk, m.group('dob'), hm.group('date'), hm.group('trk'), hm.group('dist'))
                if k in best and best[k][0] >= stamp: continue
                pm = re.match(r'^(?P<trial>T)?(?P<p>\d+|[A-Z]+) of (?P<n>\d+)', pos)
                mid = MID.match(hm.group('rest')); tail = TAIL.search(t)
                best[k] = (stamp, {'name_key': nk, 'dob': m.group('dob'), 'run_date': pd.to_datetime(hm.group('date'), format='%d%b%y').date(), 'track_code': hm.group('trk'),
                    'distance_m': int(hm.group('dist')), 'going': hm.group('going'), 'going_num': int(hm.group('gnum')) if hm.group('gnum') else None,
                    'trial': bool(pm and pm.group('trial')), 'finish_raw': pos, 'finish_pos': int(pm.group('p')) if pm and pm.group('p').isdigit() else None,
                    'field': int(pm.group('n')) if pm else None, 'class': mid.group('cls').strip() if mid else None,
                    'prize': int(mid.group('prize').replace(',', '')) if mid else None, 'jockey': mid.group('jockey') if mid else None,
                    'weight_kg': float(mid.group('wt')) if mid else None, 'claim_weight_kg': float(mid.group('cd')) if mid and mid.group('cd') else None,
                    'barrier': int(mid.group('bar')) if mid else None, 'nsw_rating': int(mid.group('rtg')) if mid and mid.group('rtg') else None,
                    'race_time_s': (lambda s: int(s.split(':')[0]) * 60 + float(s.split(':')[1]))(tail.group('time')) if tail else None,
                    'race_last600_s': float(tail.group('l600')) if tail and tail.group('l600') else None, 'margin_l': float(tail.group('mgn')) if tail and tail.group('mgn') else None,
                    'pos800': int(tail.group('p800')) if tail and tail.group('p800') else None, 'pos400': int(tail.group('p400')) if tail and tail.group('p400') else None,
                    'line': t, 'retrieved_utc': stamp})
lines = pd.DataFrame([v for _, v in best.values()]); hz = pd.DataFrame(list(horses.values()))
con = duckdb.connect(db)
for name, df in [('nsw_form_line', lines), ('nsw_form_horse', hz)]:
    con.execute(f'drop table if exists {name}'); con.register('df', df); con.execute(f'create table {name} as select * from df'); con.unregister('df')
print('horses', len(hz), 'career lines', len(lines), 'race lines', int((~lines.trial).sum()))
print(con.execute("""select extract(year from run_date) y, count(*) lines, count(*) filter (where not trial) races, count(distinct name_key) horses,
                     round(avg(case when barrier is not null then 1 else 0 end) filter (where not trial)*100,1) pct_barrier_races,
                     round(avg(case when pos400 is not null then 1 else 0 end) filter (where not trial)*100,1) pct_400_races,
                     round(avg(case when race_last600_s is not null then 1 else 0 end) filter (where not trial)*100,1) pct_l600_races from nsw_form_line group by 1 order by 1""").fetchdf().to_string(index=False))
print(con.execute("select track_code, count(*) n from nsw_form_line group by 1 order by 2 desc limit 25").fetchdf().T.to_string())
