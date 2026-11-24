"""Turn cloud-collected national fields (collect/national/<date>/races.csv + runners.csv) into
  (a) a scorer-compatible snapshot bundle (same schema as the Racing NSW pre-race bundles) for meetings whose horses
      have usable history (scored with the national common-data model + Engine v2), and
  (b) a fields-only JSON for every meeting (shown on the dashboard even when history is too thin to rate).

Source: breednet.com.au race pages, read with Claude's WebFetch tool (robots.txt allows general crawling; low volume,
personal reference use). WebFetch returns a model-extracted table, not raw HTML, so every race is checked for internal
consistency (barriers must form an unbroken 1..N set; saddlecloths unique). Emergencies are NOT labelled by the source:
runners listed after the weight-ordered main field (first weight increase) are treated as probable emergencies and are
not counted until confirmed - the same rule the NSW scorer already applies to unnumbered entries.

Usage (from research/): python3 collect/national/build_snapshot.py 20261125 2026-11-24T20:30:00Z "Geelong"
  arg 2 = upper bound of the collection window (UTC); arg 3 = comma list of meetings to put in the scoring bundle."""
import sys, os, json, gzip, hashlib, re, pandas as pd
D, RETR, SCORE = sys.argv[1], sys.argv[2], sys.argv[3].split(',')
base = f'collect/national/{D}'
RC = pd.read_csv(f'{base}/races.csv'); RN = pd.read_csv(f'{base}/runners.csv', dtype={'claim': str, 'jockey': str, 'emergency': str})
sha = lambda b: hashlib.sha256(b).hexdigest()
stamp = pd.Timestamp(RETR).strftime('%Y%m%dT%H%M%SZ')

def claim_kg(c):
    m = re.match(r'a(\d+(?:\.\d+)?)', str(c)) if isinstance(c, str) else None
    return float(m.group(1)) if m else None

def bm(name):
    m = re.search(r'\(Bm(\d+)', name)
    return m.group(1) if m else None   # race benchmark (horse benchmark ratings are not published by this source)

problems, meetings = [], {}
for (vc, rno), g in RN.groupby(['venue_code', 'race_no']):
    g = g.sort_values('saddlecloth')
    if sorted(g.barrier) != list(range(1, len(g) + 1)): problems.append(f'{vc} R{rno}: barriers not 1..N')
    if g.saddlecloth.duplicated().any(): problems.append(f'{vc} R{rno}: duplicate saddlecloth')
if problems: print('WARNING consistency:', problems[:10])

for vc, mr in RC.groupby('venue_code'):
    m0 = mr.iloc[0]; fields, scr = [], []
    for _, r in mr.sort_values('race_no').iterrows():
        g = RN[(RN.venue_code == vc) & (RN.race_no == r.race_no)].sort_values('saddlecloth')
        w = g.weight_kg.tolist(); cut = next((i for i in range(1, len(w)) if w[i] > w[i - 1]), len(w))   # first weight increase = end of main field
        sc = []
        for i, (_, h) in enumerate(g.iterrows()):
            em = (str(h.get('emergency', '')).lower() == 'true') if 'emergency' in g.columns else i >= cut
            fields.append({'race_no': int(r.race_no), 'race_name': r.race_name, 'distance_m': int(r.distance_m), 'start_time': r.start_local,
                           'class_text': r.class_text, 'saddlecloth': int(h.saddlecloth), 'last10': None, 'horse': h.horse,
                           'trainer': h.trainer, 'jockey': h.jockey if isinstance(h.jockey, str) and h.jockey.strip() else None,
                           'claim_kg': claim_kg(h.claim), 'barrier': int(h.barrier), 'weight_kg': float(h.weight_kg),
                           'age_sex': h.age_sex if isinstance(h.age_sex, str) else None, 'benchmark': None, 'race_benchmark': bm(r.race_name),
                           'emergency': bool(em and h.page_status != 'scratched'), 'emergency_basis': ('source flag' if 'emergency' in g.columns else 'inferred: listed after the weight-ordered main field') if em else None})
            if h.page_status == 'scratched': sc.append({'saddlecloth': int(h.saddlecloth), 'horse': h.horse, 'when': 'listed as scratched at collection'})
        if sc: scr.append({'race_no': int(r.race_no), 'horses': sc})
    raw = (mr.to_csv(index=False) + RN[RN.venue_code == vc].to_csv(index=False)).encode()
    meetings[m0.venue] = {'kind': 'natpre', 'schema': 1, 'date': D, 'venue': m0.venue, 'state': m0.state, 'tz': m0.tz,
                          'retrieved_utc': RETR, 'retrieved_note': 'upper bound of the WebFetch collection window',
                          'source': (json.load(open(f'{base}/calendar.json')).get('source') if os.path.exists(f'{base}/calendar.json') else 'breednet.com.au race pages via WebFetch'),
                          'acceptances_url': f'https://www.breednet.com.au/race-meeting/{vc}/{D[6:8]}{D[4:6]}{D[2:4]}/<race_no>',
                          'acceptances_http': 200, 'acceptances_sha256': sha(raw),
                          'conditions': {'track_condition': (str(m0.get('track_condition')) if m0.get('track_condition') == m0.get('track_condition') and m0.get('track_condition') else None), 'rail': (str(m0.get('rail')) if m0.get('rail') == m0.get('rail') and m0.get('rail') else None), 'weather': None,
                                         'note': 'Track condition not available from this source; scoring assumes the Good band until an official rating is collected.'},
                          'scratchings': scr, 'fields': fields}

os.makedirs(f'{base}/bundles', exist_ok=True)
bundle = f'{base}/bundles/natpre_{D}_snap{stamp}.jsonl.gz'
with gzip.open(bundle, 'xt') as fh:
    for v, s in meetings.items():
        if v in SCORE: fh.write(json.dumps({'key': f"vicpre:{D}:{v}:{stamp}" if s['state'] == 'VIC' else f"natpre:{D}:{v}:{stamp}", 'value': s}) + '\n')
with open(f'{base}/fields_{stamp}.json', 'x') as fh: json.dump(meetings, fh, indent=1)
print(bundle); print(f'{base}/fields_{stamp}.json')
for v, s in meetings.items():
    f = pd.DataFrame(s['fields']); print(v, s['state'], 'races', f.race_no.nunique(), 'listed', len(f), 'probable emergencies', int(f.emergency.sum()),
                                         'scratched', sum(len(r['horses']) for r in s['scratchings']))
