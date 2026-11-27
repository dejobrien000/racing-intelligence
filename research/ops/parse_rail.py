"""Parse pre-race rail / track capture files (RAIL|... lines) into a CSV, keeping every raw value (Batch 23 A3; provisional research
data: collected and retained, NOT served to any engine). Part-course settings are kept as written and also split into sections
(e.g. '+6m 1000m-W/Post; +3m Remainder' -> [{'section': '1000m-W/Post', 'offset_m': 6}, {'section': 'Remainder', 'offset_m': 3}]);
they are never reduced to a single number. 'True' = 0 m. Unparseable text keeps sections = [] and the raw string.
Usage (from research/): python3 ops/parse_rail.py collect/national/<D>/rail/rail_*.raw.txt  -> same name .csv beside each file"""
import sys, re, json, csv
COLS = ['venue', 'meeting_date', 'rail_raw', 'surface', 'track_rating', 'penetrometer', 'rainfall_raw', 'irrigation_raw', 'weather_raw',
        'conditions_update_raw', 'rating_update_raw', 'race_notes', 'source_code']
def sections(t):
    t = (t or '').strip()
    if not t or t.lower().startswith('not available') or t == '-': return []
    out = []
    for part in re.split(r'[;,]\s*', t):
        p = part.strip(); m = re.match(r'(?i)^\+?\s*(\d+(?:\.\d+)?)\s*m(?:etres|ts)?\b\s*(.*)$', p)
        if m: out.append({'section': (m.group(2).strip() or 'Entire'), 'offset_m': float(m.group(1))}); continue
        m = re.match(r'(?i)^true\b\s*(.*)$', p)
        if m: out.append({'section': (m.group(1).strip() or 'Entire'), 'offset_m': 0.0}); continue
        out.append({'section': p, 'offset_m': None})
    return out
for f in sys.argv[1:]:
    cap = ''; rows = []
    for line in open(f, encoding='utf-8'):
        if line.startswith('#') and 'capture_utc' in line:
            m = re.search(r'capture_utc\S*=(\S+)', line); cap = m.group(1) if m else ''
            s = re.search(r'source=(\S+)', line); src = s.group(1) if s else ''
        if not line.startswith('RAIL|'): continue
        p = line.rstrip('\n').split('|')[1:]; p += [''] * (len(COLS) - len(p))
        r = dict(zip(COLS, p[:len(COLS)])); r['sections_json'] = json.dumps(sections(r['rail_raw'])); r['capture_utc'] = cap; r['source_pattern'] = src; rows.append(r)
    out = re.sub(r'\.raw\.txt$', '.csv', f)
    with open(out, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=COLS + ['sections_json', 'capture_utc', 'source_pattern']); w.writeheader(); w.writerows(rows)
    print(out, len(rows), 'meetings;', sum(1 for r in rows if json.loads(r['sections_json'])), 'with a rail setting')
