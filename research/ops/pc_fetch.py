"""Use the PC collector's verified files (branch pc-collect) in the daily run; the Claude collection stays the fallback.
Usage (from research/):
  python3 ops/pc_fetch.py <YYYYMMDD> morning [--wait MIN]   -> collect/national/<D>/tab_<stamp>.raw.txt
  python3 ops/pc_fetch.py <YYYYMMDD> form    [--wait MIN]   -> prices/<D>/form_pc_<stamp>.raw.txt (form_manifest/parse_form read it)
  python3 ops/pc_fetch.py <YYYYMMDD> evening [--wait MIN]   -> collect/national/<D>/results_<stamp>.raw.txt (+ copy in prices/<D>/)
  python3 ops/pc_fetch.py <YYYYMMDD> status
Exit 0 = PC data used (complete). Exit 3 = PC data present but incomplete (written, caller decides: the morning run falls back
to its own TAB reads for a complete card; evening/form keep the PC file and fill gaps). Exit 2 = nothing usable from the PC.
Only files listed in a manifest with delivered_verified=true are read, and each file's sha256 is checked again here."""
import sys, os, json, hashlib, gzip, subprocess, time
D, JOB = sys.argv[1], sys.argv[2]
WAIT = int(sys.argv[sys.argv.index('--wait') + 1]) if '--wait' in sys.argv else 0
ROOT = subprocess.run(['git', 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
def fetch():
    r = subprocess.run(['git', '-C', ROOT, 'fetch', '-q', '--depth', '1', 'origin', 'pc-collect'], capture_output=True, text=True)
    return r.returncode == 0
def show(p):
    r = subprocess.run(['git', '-C', ROOT, 'show', f'FETCH_HEAD:{p}'], capture_output=True)
    return r.stdout if r.returncode == 0 else None
def manifest(job):
    b = show(f'pc/{D}/{job}_manifest.json')
    return json.loads(b) if b else None
if JOB == 'status':
    fetch()
    for j in ('morning', 'form', 'evening'):
        m = manifest(j); print(j, json.dumps({k: m.get(k) for k in ('complete', 'late', 'races_fetched', 'races_expected', 'retrieved', 'expected', 'unresolved', 'final_run', 'delivered_utc')}) if m else 'none')
    sys.exit(0)
t0 = time.time()
while True:
    m = manifest(JOB) if fetch() else None
    if m and m.get('delivered_verified') and (m.get('complete') or time.time() - t0 >= WAIT * 60): break
    if time.time() - t0 >= WAIT * 60: print(f'pc_fetch {JOB} {D}: no verified PC delivery' + (' (incomplete)' if m else '')); sys.exit(2)
    time.sleep(60)
files = {}
for f in m['files']:
    b = show(f['path'])
    if b is None or hashlib.sha256(b).hexdigest() != f['sha256']: print(f'pc_fetch: {f["path"]} missing or sha256 mismatch; not used'); sys.exit(2)
    files[f['path']] = b
(p, b), = files.items()
name = os.path.basename(p)
if JOB == 'morning':
    os.makedirs(f'collect/national/{D}', exist_ok=True); out = f'collect/national/{D}/{name}'
    open(out, 'wb').write(b)
elif JOB == 'form':
    os.makedirs(f'prices/{D}', exist_ok=True); out = f'prices/{D}/' + name.replace('form_', 'form_pc_').replace('.gz', '')
    open(out, 'wb').write(gzip.decompress(b))
elif JOB == 'evening':
    st = m.get('last_capture_utc', '').replace('-', '').replace(':', '') or 'pc'
    os.makedirs(f'collect/national/{D}', exist_ok=True); os.makedirs(f'prices/{D}', exist_ok=True)
    out = f'collect/national/{D}/results_{st}.raw.txt'; open(out, 'wb').write(b); open(f'prices/{D}/results_{st}.raw.txt', 'wb').write(b)
else: print('unknown job'); sys.exit(2)
info = {k: m.get(k) for k in ('complete', 'late', 'races_fetched', 'races_expected', 'retrieved', 'expected', 'missing', 'unresolved', 'final_run', 'started_utc', 'delivered_utc', 'host', 'collector_version')}
print(f'pc_fetch {JOB} {D}: {out} {json.dumps({k: v for k, v in info.items() if v not in (None, [], {})})}')
sys.exit(0 if m.get('complete') else 3)
