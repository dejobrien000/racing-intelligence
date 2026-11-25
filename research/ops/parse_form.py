"""Parse TAB form records captured in the daily run (DAILY_RUN.md step 5b) into two research tables.
Usage: python3 ops/parse_form.py <form raw.txt> <out dir>. Research data only: never an input to the live ratings.
Odds are never stored: a past-start line holding a price-like field is refused."""
import sys, os, re, pandas as pd
raw, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
R, P = [], []; ven = race = cap = None; cur = None
for line in open(raw, encoding='utf-8'):
    t = [x.strip() for x in line.rstrip('\n').split('|')]
    if len(t) == 3 and not t[0].startswith(('FORM', 'PS')): ven, race, cap = t; continue
    if t[0] == 'FORM' and len(t) >= 12:
        cur = {'ven': ven, 'race': race, 'captured_utc': cap, 'n': t[1], 'name': t[2], 'age': t[3], 'sex': t[4], 'career_starts': t[5], 'career_wins': t[6], 'career_places': t[7],
               'runs_since_spell': t[8], 'days_since_last_run': t[9], 'blinkers': t[10], 'class_level': t[11],
               'sire': t[12] if len(t) > 12 else None, 'dam': t[13] if len(t) > 13 else None, 'trainer': t[14] if len(t) > 14 else None}; R.append(cur)
    elif t[0] == 'PS' and cur and len(t) >= 15:
        if any('$' in x for x in t): raise SystemExit(f'price text found, refusing: {line.strip()}')
        P.append({'ven': ven, 'race': race, 'n': cur['n'], 'name': cur['name'], 'start_type': t[1], 'start_date': t[2], 'venue': t[3], 'distance': t[4], 'class': t[5], 'finish': t[6],
                  'starters': t[7], 'barrier': t[8], 'margin': t[9], 'position_in_run': t[10], 'track_condition': t[11], 'time': t[12], 'rider': t[13], 'stewards_comment': '|'.join(t[14:])})
pd.DataFrame(R).to_csv(os.path.join(out, 'form_runners.csv'), index=False); pd.DataFrame(P).to_csv(os.path.join(out, 'form_past_starts.csv'), index=False)
print('form records', len(R), '| past starts', len(P))
