"""Morning preflight (Batch 23 A1): read-only checks of today's production inputs and outputs after scoring and export. Never changes
anything and never fails the run (each check is guarded); writes outputs/preflight_<D>.json and prints one summary line plus WARN lines.
Checks: meeting and race completeness vs the calendar; runners, listed scratchings, emergencies (admitted by the gained-start rule or left
out) and missing statuses (missing information is never treated as scratched); weight and apprentice claim (claim deducted exactly once:
carried = allocated - claim); age/sex, trainer and jockey coverage; distance and class; track condition; names on the identity-correction
list (split or uncertain) appearing today; settings fingerprints (each forecast's engine files vs the files in benchmarks/); history
cutoff; dashboard file; shadows written today.
Usage (from research/): python3 ops/preflight_check.py <YYYYMMDD>"""
import sys, os, re, json, gzip, glob, hashlib, numpy as np, pandas as pd
D = sys.argv[1]; ISO = f'{D[:4]}-{D[4:6]}-{D[6:]}'; OUT = {'date': D}; WARN = []
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
def guard(name):
    def deco(fn):
        try: OUT[name] = fn()
        except Exception as e: OUT[name] = {'error': f'{type(e).__name__}: {e}'}; WARN.append(f'{name}: check could not run ({type(e).__name__})')
        return fn
    return deco
cal = json.load(open(f'collect/national/{D}/calendar.json')) if os.path.exists(f'collect/national/{D}/calendar.json') else {'meetings': []}
CAL = {m['name']: m.get('races') for m in cal['meetings']}
def bundle(kind):
    f = sorted(glob.glob(f'collect/national/{D}/bundles/{kind}_{D}_snap*.jsonl.gz'))
    return [json.loads(l)['value'] for l in gzip.open(f[-1], 'rt')] if f else []
NAT, RQ = bundle('natpre'), bundle('rqpre')
@guard('meetings')
def _():
    got = {m['venue']: len({f['race_no'] for f in m.get('fields', [])}) for m in NAT}; got.update({m['track']: len({f.get('race_no') for f in m.get('fields', [])}) for m in RQ})
    miss = {k: v for k, v in CAL.items() if k not in got}; short = {k: (got[k], v) for k, v in CAL.items() if k in got and v and got[k] < v}
    for k in miss: WARN.append(f'meeting in calendar but no fields: {k}')
    for k, (g, v) in short.items(): WARN.append(f'{k}: {g} races with fields of {v} in the calendar (fields-only or incomplete?)')
    return {'calendar': len(CAL), 'with_fields': len(got), 'missing': list(miss), 'short': short}
@guard('runners')
def _():
    r = {}
    for m in NAT:
        F = pd.DataFrame(m.get('fields', [])); scr = sum(len(s['horses']) for s in (m.get('scratchings') or []))
        em = F[F.emergency.fillna(False)] if len(F) else F
        r[m['venue']] = {'runners': int(len(F)), 'listed_scratched': int(scr), 'emergencies': int(len(em)), 'emergencies_admitted': int(em.get('emergency_gained_start', pd.Series(dtype=bool)).fillna(False).sum()) if len(em) else 0,
                         'weight_missing': int(F.weight_kg.isna().sum()), 'claim_present': int(F.claim_kg.notna().sum()), 'claim_outside_0_4': int(((F.claim_kg < 0) | (F.claim_kg > 4)).sum()),
                         'trainer_missing': int(F.trainer.isna().sum()), 'jockey_missing': int(F.jockey.isna().sum()), 'distance_missing': int((F.distance_m.fillna(0) <= 0).sum()), 'class_missing': int(F.class_text.isna().sum()),
                         'track_condition': (m.get('conditions') or {}).get('track_condition')}
        if not r[m['venue']]['track_condition']: WARN.append(f"{m['venue']}: no track condition")
        if r[m['venue']]['weight_missing']: WARN.append(f"{m['venue']}: {r[m['venue']]['weight_missing']} runners without weight")
    for m in RQ:
        F = pd.DataFrame(m.get('fields', [])); r[m['track']] = {'runners': int(len(F)), 'listed_scratched': int(sum(len(s['horses']) for s in (m.get('scratchings') or []))),
                                                               'track_condition': (m.get('conditions') or {}).get('track_condition')}
    return r
@guard('claims_deducted_once')
def _():
    bad = 0; n = 0
    for f in glob.glob(f'prospective/prerace/{D}/*/pred_*_runners.csv'):
        x = pd.read_csv(f)
        if not {'weight_kg', 'claim_used_kg', 'weight_carried_kg'} <= set(x.columns): continue
        y = x.dropna(subset=['weight_kg', 'weight_carried_kg']); n += len(y)
        bad += int((np.abs(y.weight_kg - y.claim_used_kg.fillna(0) - y.weight_carried_kg) > 1e-6).sum())
    if bad: WARN.append(f'{bad} runners where carried weight != allocated - claim')
    return {'runners_checked': n, 'mismatches': bad}
@guard('age_sex_coverage')
def _():
    f = f'collect/national/{D}/form_runners.csv'
    if not os.path.exists(f): return 'no form records yet'
    T = pd.read_csv(f); return {'runners': int(len(T)), 'age_present': round(float(T.age.notna().mean()), 3), 'sex_present': round(float(T.sex.notna().mean()), 3), 'first_starters': int((T.career_starts == 0).sum())}
@guard('ran_yesterday_still_listed')
def _():
    f = f'collect/national/{D}/form_past_starts.csv'
    if not os.path.exists(f): return 'no form records yet'
    ps = pd.read_csv(f); ps['d'] = pd.to_datetime(ps.start_date, errors='coerce'); day = pd.Timestamp(ISO)
    x = ps[(ps.d >= day - pd.Timedelta(days=2)) & (ps.d < day) & (ps.start_type.astype(str).str.lower() != 'trial')]
    scr = {nk(h['horse']) for m in NAT + RQ for s_ in (m.get('scratchings') or []) for h in s_['horses']}
    x = x.assign(scratched=x.name.map(nk).isin(scr))
    rows = [f"{r.ven} R{r.race} {r.name} (started {r.start_date} at {r.venue})" for r in x[~x.scratched].itertuples()]
    for r in rows: WARN.append(f'raced within 2 days and still a runner: {r} - possible double acceptance; status kept as listed, watch for a late scratching')
    return {'already_listed_scratched': int(x.scratched.sum()), 'still_runners': rows}
@guard('identity_list_names_today')
def _():
    C = pd.read_csv('batch21/identity_correction_monday.csv', keep_default_na=False); keys = set(C.key)
    names = [f['horse'] for m in NAT for f in m.get('fields', [])] + [f.get('horse') or f.get('name') for m in RQ for f in m.get('fields', [])]
    hit = sorted({n for n in names if n and nk(n) in keys})
    for h in hit: WARN.append(f'identity-list name racing today: {h} (check its history is the right horse)')
    return hit
@guard('fingerprints')
def _():
    files = {sha(p): p for p in glob.glob('benchmarks/**/*.json', recursive=True)}
    rows = []
    for f in glob.glob(f'prospective/prerace/{D}/*/v2_pred_*_manifest.json'):
        m = json.load(open(f)); e = m.get('engine_manifest_sha256'); v = m.get('v22_manifest_sha256')
        rows.append({'meeting': f.split('/')[-2], 'engine_release': m.get('engine_release'), 'family_file': files.get(e, 'NOT FOUND'), 'v22_file': files.get(v, '-' if not v else 'NOT FOUND'), 'history_max_date': m.get('history_max_date')})
    EXPECT = {'Engine v2.3': 'benchmarks/engine_v2_3/engine_v2.json', 'Engine v2.1.3': 'benchmarks/engine_v2_1_3/manifest.json'}   # family file each release must name (28 Nov on: scorer fix)
    for r in rows:
        if 'NOT FOUND' in (r['family_file'], r['v22_file']): WARN.append(f"{r['meeting']}: engine fingerprint does not match any settings file")
        ex = next((v for k, v in EXPECT.items() if str(r['engine_release']).startswith(k)), None)
        if ex and r['family_file'] != ex and int(D) >= 20261128: WARN.append(f"{r['meeting']}: {r['engine_release']} recorded family file {r['family_file']} (expected {ex})")
    return rows
@guard('dashboard')
def _():
    f = f'ui/data/racing_{ISO}.json'
    if not os.path.exists(f): WARN.append('dashboard data file missing'); return 'missing'
    d = json.load(open(f)); return {'meetings': len(d.get('meetings', [])), 'rated': sum(1 for m in d['meetings'] if m.get('rated'))}
@guard('shadows_today')
def _():
    o = {}
    for f in glob.glob('prospective/shadow/*/INDEX.csv'):
        try: S = pd.read_csv(f); o[f.split('/')[-2]] = int((S.date.astype(str) == D).sum())
        except Exception: o[f.split('/')[-2]] = 'unreadable'
    return o
os.makedirs('outputs', exist_ok=True); OUT['warnings'] = WARN
json.dump(OUT, open(f'outputs/preflight_{D}.json', 'w'), indent=1, default=str)
m = OUT.get('meetings', {}); print(f"preflight {D}: {m.get('with_fields', '?')}/{m.get('calendar', '?')} meetings with fields; {len(WARN)} warnings; dashboard {OUT.get('dashboard')}; shadows {OUT.get('shadows_today')}")
for w in WARN: print('WARN', w)
