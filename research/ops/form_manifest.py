"""Expected-vs-retrieved manifest for one day's TAB form records (DAILY_RUN step 5b). Resumable: re-run any time.
Usage: python3 ops/form_manifest.py <YYYYMMDD> [racecard raw]   (default racecard = newest collect/national/<D>/tab_*.raw.txt)
Reads every prices/<D>/form_*.raw.txt (all attempts, in time order), keeps the LATEST complete record per runner
(a record whose past-start lines all have 15 fields beats a malformed one), and writes:
  prices/<D>/form_manifest.csv   one row per expected runner: status retrieved / malformed / missing, past-start lines,
                                 malformed lines, source file and capture time of the record kept
  prices/<D>/form_todo.txt       VEN|race|runnerNumber|J for every runner still missing or malformed (next attempt reads this)
Nothing is dropped: malformed lines stay in the raw files and are counted here."""
import sys, os, glob, csv
D = sys.argv[1]
card = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(f'collect/national/{D}/tab_*.raw.txt'))[-1]
J = {}; exp = []; cur = None; meets = {}
for l in open(card, encoding='utf-8'):
    p = l.rstrip('\n').split('|')
    if p[0] == 'MEET' and len(p) >= 4: meets[p[1]] = p[3]
    elif p[0] == 'RACE': cur = (p[1], p[2])
    elif cur and len(p) >= 11 and p[0].isdigit(): exp.append((cur[0], cur[1], p[0], p[1]))
jur = lambda v: 'QLD' if meets.get(v) == 'QLD' else 'NSW'
best = {}
for f in sorted(glob.glob(f'prices/{D}/form_*.raw.txt')):
    ven = race = cap = None; rec = None
    def close(rec):
        if rec: 
            k = rec['key']; old = best.get(k)
            if old is None or rec['bad'] == 0 or old['bad'] > 0: best[k] = rec
    for line in open(f, encoding='utf-8'):
        t = [x.strip() for x in line.rstrip('\n').split('|')]
        if len(t) == 3 and not t[0].startswith(('FORM', 'PS')): close(rec); rec = None; ven, race, cap = t; continue
        if t[0] == 'FORM' and len(t) >= 12: close(rec); rec = {'key': (ven, race, t[1]), 'ps': 0, 'bad': 0, 'file': os.path.basename(f), 'cap': cap}
        elif t[0] == 'PS' and rec: rec['ps'] += 1; rec['bad'] += (len(t) < 15)
    close(rec)
rows, todo = [], []
for v, r, n, name in exp:
    b = best.get((v, r, n))
    st = 'missing' if b is None else ('malformed' if b['bad'] else 'retrieved')
    rows.append({'ven': v, 'race': r, 'n': n, 'name': name, 'status': st, 'ps_lines': b['ps'] if b else 0, 'malformed_lines': b['bad'] if b else 0,
                 'file': b['file'] if b else '', 'captured_utc': b['cap'] if b else ''})
    if st != 'retrieved': todo.append(f'{v}|{r}|{n}|{jur(v)}')
os.makedirs(f'prices/{D}', exist_ok=True)
with open(f'prices/{D}/form_manifest.csv', 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
open(f'prices/{D}/form_todo.txt', 'w').write('\n'.join(todo) + ('\n' if todo else ''))
c = {s: sum(x['status'] == s for x in rows) for s in ('retrieved', 'malformed', 'missing')}
print(f"form manifest {D}: expected {len(rows)} | retrieved {c['retrieved']} | malformed {c['malformed']} | missing {c['missing']} | todo -> prices/{D}/form_todo.txt")
