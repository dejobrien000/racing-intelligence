"""Shared adapter (Batch 17 B2, approved by Damo 27 Nov 2026): Queensland morning fields (rqpre bundle, Racing Queensland) restated in
the national field format, so the national scorers (prerace/score_national_prerace.py, engine/score_v2.py) can score Queensland meetings
with the common national framework's Queensland coefficients. SHADOW ONLY: never used by production.

Nothing is invented: every field value is copied from the Racing Queensland snapshot; values that snapshot does not carry (apprentice
claim, age/sex, benchmark) are left empty exactly as the national format allows. The course key ('config') is the Queensland tracked
course name used in history (runs.parquet), so course records match history; the venue is Breednet's slug, as in national history.
The output keeps the source snapshot's key, retrieval time and fields-PDF fingerprint.
Usage (from research/): python3 ops/qld_common_adapter.py <YYYYMMDD> <out dir>  -> prints the written bundle path"""
import sys, os, re, gzip, json, glob
D, OUT = sys.argv[1], sys.argv[2]
# Racing Queensland track names -> tracked-course names in history (sponsor names) ; poly track kept apart as in history
CONFIG = {'Sunshine Coast': 'Sunshine_Coast', 'Sunshine Coast Poly Track': 'Sunshine_Coast_Poly_Track', 'Eagle Farm': 'Eagle_Farm', 'Doomben': 'Doomben',
          'Ipswich': 'Ipswich', 'Toowoomba': 'Toowoomba', 'Townsville': 'Townsville', 'Rockhampton': 'Rockhampton', 'Mackay': 'Mackay', 'Dalby': 'Dalby',
          'Kilcoy': 'Kilcoy', 'Cairns': 'Ladbrokes_Cannon_Park', 'Gold Coast': 'TAB_Park_Gold_Coast', 'Warwick': 'Picklebet_Park_Warwick'}
VENUE = {'Sunshine Coast Poly Track': 'Sunshine Coast'}          # Breednet venue slug is the same course for turf and poly
src = sorted(glob.glob(f'collect/national/{D}/bundles/rqpre_{D}_snap*.jsonl.gz'))
if not src: print('no Queensland bundle'); sys.exit(0)
src = src[-1]; out = []
with gzip.open(src, 'rt') as fh:
    for line in fh:
        if not line.strip(): continue
        o = json.loads(line); v = o['value']; v = json.loads(v) if isinstance(v, str) else v
        trk = v['track']; cfg = CONFIG.get(trk, trk.replace(' ', '_'))
        fields = [{'race_no': f['race_no'], 'race_name': f.get('race_name'), 'distance_m': f.get('distance_m'), 'start_time': f.get('start_time'), 'class_text': f.get('race_name'),
                   'saddlecloth': f.get('saddlecloth'), 'last10': None, 'horse': f.get('horse'), 'trainer': f.get('trainer'), 'jockey': f.get('jockey'), 'claim_kg': None,
                   'barrier': f.get('barrier'), 'weight_kg': f.get('weight_kg'), 'age_sex': None, 'benchmark': None, 'race_benchmark': None,
                   'emergency': bool(f.get('emergency')), 'emergency_basis': None, 'config': cfg} for f in v['fields']]
        key = 'qcfpre:' + o['key'].split(':', 1)[1]                 # same date / meeting / snapshot stamp as the Racing Queensland key
        out.append({'key': key, 'value': {'kind': 'qcfpre', 'schema': 'national field format (adapted from Racing Queensland)', 'date': v['date'], 'venue': VENUE.get(trk, trk),
                    'state': 'QLD', 'tz': 'Australia/Brisbane', 'retrieved_utc': v['retrieved_utc'], 'retrieved_note': f"adapted from {o['key']}", 'source': v.get('source'),
                    'acceptances_url': None, 'acceptances_http': None, 'acceptances_sha256': v.get('fields_pdf_sha256'), 'source_bundle': os.path.basename(src),
                    'conditions': {'track_condition': v['conditions'].get('track_condition'), 'rail': v['conditions'].get('rail'), 'weather': None,
                                   'scratchings_close': v['conditions'].get('scratchings_close')},
                    'scratchings': v.get('scratchings', []), 'fields': fields}})
os.makedirs(OUT, exist_ok=True); dst = os.path.join(OUT, os.path.basename(src).replace('rqpre_', 'qcfpre_'))
with gzip.open(dst, 'wt') as fh:
    for r in out: fh.write(json.dumps(r) + '\n')
print(dst)
