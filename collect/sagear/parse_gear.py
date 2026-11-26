"""Racing SA 'Gear Change Race Order' PDFs -> staging rows (one per horse per gear item). Research data only.

Usage: python3 collect/sagear/parse_gear.py <out.csv> <pdf>...   (needs pdftotext from poppler-utils)
The document lists, per race and horse, every declared gear item with its state: On (unchanged, carried before),
First Time, Again, Off First Time, Off Again, Gelded. A horse that is not listed carries no declared gear in THIS
document ('not listed'), which is not the same as confirmed absence for late changes: late gear changes made after
'Date Printed' appear only in the stewards' report (retrospective).
TIMING: available_from_local = the document's 'Date Printed' (Adelaide local time). It is pre-race information when that
time is before the race; a document printed after a race must never be used for that race.
Lines that cannot be placed are written with parse_note so nothing is dropped silently."""
import sys, re, csv, subprocess, os, hashlib, datetime as dt
out, pdfs = sys.argv[1], sys.argv[2:]
STATE = r'(Off First Time|Off Again|First Time|Again|On|Off|Gelded)'
CLS = {'On': 'unchanged (carried before)', 'First Time': 'first time', 'Again': 'again (resumed)', 'Off First Time': 'removed (first time)',
       'Off Again': 'removed (again)', 'Off': 'removed', 'Gelded': 'gelded since last start'}
def nk(s): return re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', s.upper()))
rows = []
for p in pdfs:
    raw = open(p, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    txt = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
    printed = meet_date = meet_name = None; race = rclass = horse = sc = None; n_items = 0
    for ln in txt.split('\n'):
        s = ln.strip()
        if not s: continue
        g = re.search(r'Date Printed\s*:\s*\w+,\s*(\d{1,2} \w+ \d{4})\s+(\d{1,2}:\d{2}:\d{2})', s)
        if g: printed = printed or dt.datetime.strptime(g.group(1) + ' ' + g.group(2), '%d %B %Y %H:%M:%S').strftime('%Y-%m-%d %H:%M:%S'); continue
        if s == 'Gear Change Race Order' or re.search(r'\bPage\s+\d+\s*$', s): continue
        g = re.match(r'^(\d{1,2}/\d{2}/\d{2,4})\s+(.+)$', s)
        if g and not re.search(STATE + r'$', s):
            d = g.group(1); meet_date = meet_date or dt.datetime.strptime(d, '%d/%m/%y' if len(d.split('/')[-1]) == 2 else '%d/%m/%Y').strftime('%Y-%m-%d')
            meet_name = meet_name or g.group(2).strip(); continue
        g = re.match(r'^(\d{1,2})\s{6,}(\S.*)$', ln.rstrip())                     # race line: number, wide gap, race class
        if g: race, rclass, horse, sc = int(g.group(1)), g.group(2).strip(), None, None; continue
        g = re.match(r'^(.+?)\s{3,}' + STATE + r'$', s)                            # gear item line
        if g and horse:
            rows.append({'file': os.path.basename(p), 'sha256': sha, 'date_printed_local': printed, 'meeting_date': meet_date, 'meeting': meet_name,
                         'race_no': race, 'race_class': rclass, 'saddlecloth': sc, 'horse': horse, 'horse_key': nk(horse),
                         'gear_item': g.group(1).strip(), 'state': g.group(2), 'state_class': CLS[g.group(2)], 'parse_note': ''}); n_items += 1; continue
        g = re.match(r'^(\d{1,2})\s{1,5}([A-Za-z].*)$', s)                         # horse line: saddlecloth, horse name
        if g and race is not None: sc, horse = int(g.group(1)), g.group(2).strip(); continue
        rows.append({'file': os.path.basename(p), 'sha256': sha, 'date_printed_local': printed, 'meeting_date': meet_date, 'meeting': meet_name,
                     'race_no': race, 'horse': horse, 'parse_note': 'unplaced line: ' + s[:200]})
    print(f'{os.path.basename(p)}: printed {printed} | meeting {meet_date} {meet_name} | gear items {n_items}', file=sys.stderr)
cols = ['file', 'sha256', 'date_printed_local', 'meeting_date', 'meeting', 'race_no', 'race_class', 'saddlecloth', 'horse', 'horse_key',
        'gear_item', 'state', 'state_class', 'parse_note']
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
