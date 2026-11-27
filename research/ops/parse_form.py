"""Parse TAB form records captured in the daily run (DAILY_RUN.md step 5b) into research tables.
Usage: python3 ops/parse_form.py <out dir> <form raw.txt> [more raw files ...]
   or: python3 ops/parse_form.py <form raw.txt> <out dir>            (old two-argument form, one file)
Several raw files for one day (a first pass plus re-reads) are combined: per runner (meeting, race, number) the LATEST record
whose past-start lines all have 15 fields is kept; if every copy is malformed the latest copy is kept and its short lines are
listed in form_rejected_lines.csv (kept aside, never guessed). Mostly research data; from 28 Nov 2026 age and sex from these records feed the
live ratings for runners with no history only (Batch 18 A1, switch ops/agesex_tab_enabled).
Odds are never stored: a past-start line holding a price-like field is refused."""
import sys, os, pandas as pd
a = sys.argv[1:]
if len(a) == 2 and os.path.isfile(a[0]) and not os.path.isfile(a[1]): out, raws = a[1], [a[0]]
else: out, raws = a[0], a[1:]
os.makedirs(out, exist_ok=True)
recs = {}   # key -> (order, record dict, past starts, bad lines)
order = 0
for raw in raws:
    ven = race = cap = None; cur = None
    def keep(cur):
        if not cur: return
        k = (cur[0]['ven'], cur[0]['race'], cur[0]['n']); old = recs.get(k)
        if old is None or not cur[2] or old[2]: recs[k] = (order, *cur)
    for line in open(raw, encoding='utf-8'):
        t = [x.strip() for x in line.rstrip('\n').split('|')]
        if len(t) == 3 and not t[0].startswith(('FORM', 'PS')): keep(cur); cur = None; ven, race, cap = t; continue
        if t[0] == 'FORM' and len(t) >= 12:
            keep(cur); order += 1
            r = {'ven': ven, 'race': race, 'captured_utc': cap, 'n': t[1], 'name': t[2], 'age': t[3], 'sex': t[4], 'career_starts': t[5], 'career_wins': t[6],
                 'career_places': t[7], 'runs_since_spell': t[8], 'days_since_last_run': t[9], 'blinkers': t[10], 'class_level': t[11],
                 'sire': t[12] if len(t) > 12 else None, 'dam': t[13] if len(t) > 13 else None, 'trainer': t[14] if len(t) > 14 else None,
                 'source_file': os.path.basename(raw)}
            cur = (r, [], [])
        elif t[0] == 'PS' and cur:
            r = cur[0]
            if len(t) < 15:
                cur[2].append({'ven': ven, 'race': race, 'n': r['n'], 'name': r['name'], 'fields': len(t), 'line': line.strip(), 'source_file': os.path.basename(raw)}); continue
            if any('$' in x for x in t): raise SystemExit(f'price text found, refusing: {line.strip()}')
            cur[1].append({'ven': ven, 'race': race, 'n': r['n'], 'name': r['name'], 'start_type': t[1], 'start_date': t[2], 'venue': t[3], 'distance': t[4],
                           'class': t[5], 'finish': t[6], 'starters': t[7], 'barrier': t[8], 'margin': t[9], 'position_in_run': t[10], 'track_condition': t[11],
                           'time': t[12], 'rider': t[13], 'stewards_comment': '|'.join(t[14:])})
    keep(cur)
R = [v[1] for v in recs.values()]; P = [p for v in recs.values() for p in v[2]]; BAD = [b for v in recs.values() for b in v[3]]
pd.DataFrame(R).to_csv(os.path.join(out, 'form_runners.csv'), index=False); pd.DataFrame(P).to_csv(os.path.join(out, 'form_past_starts.csv'), index=False)
pd.DataFrame(BAD, columns=['ven', 'race', 'n', 'name', 'fields', 'line', 'source_file']).to_csv(os.path.join(out, 'form_rejected_lines.csv'), index=False)
print('form records', len(R), '| past starts', len(P), '| rejected PS lines (too few fields, see form_rejected_lines.csv)', len(BAD),
      ('runners: ' + ', '.join(sorted({f"{b['ven']} R{b['race']} n{b['n']}" for b in BAD}))) if BAD else '')
