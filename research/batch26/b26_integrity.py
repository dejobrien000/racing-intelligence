"""Batch 26 Part 1: Saturday 28 Nov operational integrity (read-only audit; changes nothing).
For production and every shadow: which races were forecast, when (scored time in the file's manifest / filename and the git commit
that first stored it), whether each forecast was stored before its race started, duplicates (a race forecast twice by the same
engine), skipped races, and the scoring timestamps. Then the inputs actually used vs missing when the forecasts were made.
Output: batch26/out_b26_integrity.json and a printed summary."""
import glob, json, os, re, subprocess, collections, datetime as dt
import pandas as pd
D = '20261128'; os.chdir('/home/claude/racing-intelligence/research')
TZ = {'AEDT': 11, 'AEST': 10, 'ACDT': 10.5, 'AWST': 8, 'ACST': 9.5}
R = pd.read_csv(f'collect/national/{D}/races.csv')
def start_utc(r):
    t = dt.datetime.strptime(r.start_local.upper(), '%I:%M%p'); h = TZ[r.tz]
    return (dt.datetime(2026, 11, 28, t.hour, t.minute) - dt.timedelta(hours=h)).replace(tzinfo=dt.timezone.utc)
R['start_utc'] = R.apply(start_utc, axis=1)
R['vkey'] = R.venue.str.replace(r'[^A-Za-z]', '', regex=True).str.lower()
R['rid'] = R.vkey + '|' + R.race_no.astype(str)
RATED = R[R.state != 'NT']
first_commit = {}
def commit_time(path):
    if path not in first_commit:
        o = subprocess.run(['git', 'log', '--diff-filter=A', '--format=%cI', '--', path], capture_output=True, text=True).stdout.strip().splitlines()
        first_commit[path] = o[-1] if o else None
    return first_commit[path]
def races_in(path):
    """race numbers covered by a saved forecast file (races.csv or runners.csv)"""
    x = pd.read_csv(path)
    col = 'race_id' if 'race_id' in x else ('race_no' if 'race_no' in x else None)
    if col is None: return set()
    if col == 'race_id': return set(int(m.group(1)) for m in (re.search(r'(?:-R|\|)(\d+)$', str(v)) for v in x.race_id) if m)
    return set(int(v) for v in x.race_no.dropna())
out = {'date': D, 'races_listed': int(len(R)), 'races_rated_expected': int(len(RATED)), 'first_start_utc': str(R.start_utc.min())}
# production: dashboard ranking (national + Qld) - one file, predicted_utc per race
P = pd.read_csv(glob.glob(f'prospective/daily/{D}/ranking_v2_*_races.csv')[0])
P['vkey'] = P.meeting.str.replace(r'[^A-Za-z]', '', regex=True).str.lower(); P['rid'] = P.vkey + '|' + P.race_no.astype(str)
P = P.merge(R[['rid', 'start_utc']], on='rid', how='left'); P['pred'] = pd.to_datetime(P.predicted_utc, utc=True)
out['production'] = {'races': int(P.rid.nunique()), 'rows': int(len(P)), 'duplicates': int(P.rid.duplicated().sum()),
                     'missing_vs_rated': sorted(set(RATED.rid) - set(P.rid)), 'extra': sorted(set(P.rid) - set(RATED.rid)),
                     'predicted_utc_min': str(P.pred.min()), 'predicted_utc_max': str(P.pred.max()),
                     'all_before_start': bool((P.pred < P.start_utc).all()), 'min_margin_minutes': round(float((P.start_utc - P.pred).dt.total_seconds().min() / 60), 1),
                     'model_versions': P.model_version.value_counts().to_dict(),
                     'stored_in_commit_utc': commit_time(glob.glob(f'prospective/daily/{D}/ranking_v2_*_races.csv')[0])}
# pre-race stores (production per venue) and shadows: per engine, per venue files
def audit(root, label):
    res = {'venues': {}, 'races': 0, 'duplicates': [], 'late': [], 'files': 0}
    for vdir in sorted(glob.glob(f'{root}/{D}/*')):
        vkey = re.sub(r'[^A-Za-z]', '', os.path.basename(vdir)).lower()
        files = sorted(glob.glob(f'{vdir}/*races.csv')) or sorted(glob.glob(f'{vdir}/*runners.csv'))
        mans = sorted(glob.glob(f'{vdir}/*manifest.json'))
        cover = collections.Counter(); stamps = []
        for f in files:
            for rn in races_in(f): cover[rn] += 1
        for m in mans:
            try: stamps.append(json.load(open(m)).get('scored_utc'))
            except Exception: pass
        stamps = [pd.Timestamp(s) for s in stamps if s]
        last = max(stamps) if stamps else None
        vr = R[R.vkey == vkey]
        first_start = vr.start_utc.min() if len(vr) else None
        commits = sorted(filter(None, [commit_time(f) for f in files + mans]))
        res['venues'][vkey] = {'races': len(cover), 'listed': int(len(vr)), 'files': len(files), 'scored_utc_last': str(last) if last is not None else None,
                               'first_start_utc': str(first_start), 'committed_utc': commits[-1] if commits else None,
                               'before_first_race': bool(last is not None and first_start is not None and last < first_start)}
        res['races'] += len(cover); res['files'] += len(files)
        if any(v > 1 for v in cover.values()) and len(files) == 1: res['duplicates'].append(vkey)
        if last is not None and first_start is not None and not last < first_start: res['late'].append(vkey)
    return res
out['prerace_store_production'] = audit('prospective/prerace', 'production')
SH = sorted(os.path.basename(p) for p in glob.glob('prospective/shadow/*') if os.path.isdir(p))
out['shadows'] = {}
for s in SH:
    root = f'prospective/shadow/{s}/prerace' if os.path.isdir(f'prospective/shadow/{s}/prerace') else f'prospective/shadow/{s}'
    a = audit(root, s); out['shadows'][s] = {k: a[k] for k in ['races', 'files', 'duplicates', 'late']}
    out['shadows'][s]['venues'] = {v: (x['races'], x['scored_utc_last'], x['committed_utc'], x['before_first_race']) for v, x in a['venues'].items()}
json.dump(out, open('batch26/out_b26_integrity.json', 'w'), indent=1, default=str)
print(json.dumps({k: out[k] for k in ['races_listed', 'races_rated_expected', 'first_start_utc']}))
print('production', json.dumps({k: v for k, v in out['production'].items()}))
p = out['prerace_store_production']; print('prerace store', p['races'], 'races', p['files'], 'files; dup', p['duplicates'], 'late', p['late'])
for s, a in out['shadows'].items(): print(s, a['races'], 'races', a['files'], 'files; dup', a['duplicates'], 'late', a['late'], '| last scored', max((v[1] or '') for v in a['venues'].values()))
