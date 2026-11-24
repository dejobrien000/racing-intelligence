"""Race-morning refresh of a saved field snapshot: apply the scratchings published by an official (or named) source
at a stated time, and write a NEW snapshot bundle (write-once). Fields, weights and barriers are unchanged; scratchings
are only ever added (a horse is never un-scratched). Every scratching must match our field by race, saddlecloth AND
horse name, or the refresh stops - this guards against mis-read source tables.

After final scratchings have closed (after_close = true), emergencies that were not scratched have gained a start
(authorities scratch the emergencies that miss out). For sources that do not label emergencies (inferred), the first k
unscratched emergencies gain a start, where k = main-field scratchings in that race.

Usage (from research/):
  python3 collect/rescratch.py <src bundle> <src key> <refresh.json>
refresh.json = {"retrieved_utc": "...", "source": "...", "after_close": true|false,
                "scratchings": [{"race_no": 3, "saddlecloth": 6, "horse": "APPIN OPAL", "when": "25/11 0711"}, ...],
                "conditions": {...optional overrides, e.g. track_condition...}}"""
import sys, os, json, gzip, re, pandas as pd
SRC, KEY, REF = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3]))
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
snap = None
with gzip.open(SRC, 'rt') as fh:
    for line in fh:
        o = json.loads(line)
        if o['key'] == KEY: snap = o['value']; snap = json.loads(snap) if isinstance(snap, str) else snap
assert snap is not None, 'source key not found'
F = {(f['race_no'], f['saddlecloth']): f for f in snap['fields'] if f.get('saddlecloth') not in (None, '')}
old = {(r['race_no'], h['saddlecloth']) for r in snap['scratchings'] for h in r['horses']}
oldname = {(r['race_no'], h['saddlecloth']): h.get('horse') for r in snap['scratchings'] for h in r['horses']}
def _ok(x):
    k = (x['race_no'], x['saddlecloth'])
    if k in oldname: return nk(oldname[k] or x['horse']) == nk(x['horse'])          # already scratched in the saved snapshot
    return k in F and nk(F[k]['horse']) == nk(x['horse'])
bad = [x for x in REF['scratchings'] if not _ok(x)]
assert not bad, f'scratchings that do not match our field (refresh stopped): {bad}'
by_race = {}
for r in snap['scratchings']: by_race.setdefault(r['race_no'], []).extend(r['horses'])
added = []
for s in REF['scratchings']:
    if (s['race_no'], s['saddlecloth']) in old: continue
    by_race.setdefault(s['race_no'], []).append({'saddlecloth': s['saddlecloth'], 'horse': F[(s['race_no'], s['saddlecloth'])]['horse'], 'when': s.get('when')}); added.append(s)
new = dict(snap); new['scratchings'] = [{'race_no': k, 'horses': sorted(v, key=lambda h: h['saddlecloth'])} for k, v in sorted(by_race.items())]
new['retrieved_utc'] = REF['retrieved_utc']; new['refresh_of'] = KEY; new['scratchings_source'] = REF['source']; new['after_scratchings_close'] = bool(REF.get('after_close'))
new['conditions'] = {**snap.get('conditions', {}), **REF.get('conditions', {})}; new['conditions']['after_final_scratchings'] = bool(REF.get('after_close')); new['conditions']['scratchings_source'] = REF['source']
gained = []
if REF.get('after_close'):
    scr = {(r['race_no'], h['saddlecloth']) for r in new['scratchings'] for h in r['horses']}; fields = [dict(f) for f in new['fields']]
    for rn in sorted({f['race_no'] for f in fields}):
        rf = [f for f in fields if f['race_no'] == rn]; em = [f for f in rf if f.get('emergency') and (rn, f['saddlecloth']) not in scr]
        if not em: continue
        inferred = any(f.get('emergency_basis') for f in em)
        k = sum(1 for f in rf if not f.get('emergency') and (rn, f['saddlecloth']) in scr) if inferred else len(em)
        for f in em[:k]: f['emergency'] = False; f['emergency_gained_start'] = True; gained.append((rn, f['saddlecloth'], f['horse']))
    new['fields'] = fields
stamp = pd.Timestamp(REF['retrieved_utc']).strftime('%Y%m%dT%H%M%SZ'); nkey = ':'.join(KEY.split(':')[:-1] + [stamp])
od = f"collect/national/{new['date']}/bundles"; os.makedirs(od, exist_ok=True)
out = f"{od}/{KEY.split(':')[0]}_{new['date']}_{KEY.split(':')[2]}_snap{stamp}.jsonl.gz"
with gzip.open(out, 'xt') as fh: fh.write(json.dumps({'key': nkey, 'value': new}) + '\n')
print(out); print(nkey); print('new scratchings:', [(s['race_no'], s['saddlecloth'], s['horse']) for s in added]); print('emergencies gaining a start:', gained)
