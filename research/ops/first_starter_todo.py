"""First-starter age and sex, morning list (Batch 18 A1, approved by Damo 27 Nov 2026). Before scoring, list today's runners that have no
runs in our history, so their TAB form records (age, sex) can be fetched first. Those records are the SAME records step 5b collects later:
they are written as an ordinary prices/<D>/form_<STAMP>.raw.txt file, so ops/form_manifest.py counts them as retrieved and step 5b
does not fetch them again. A runner whose record cannot be fetched keeps the existing missing-information treatment (never guessed).
Usage (from research/): python3 ops/first_starter_todo.py <YYYYMMDD> [max]  -> prices/<D>/form_todo_prescore.txt (VEN|race|runnerNumber|J)"""
import sys, glob, re, os, pandas as pd
D = sys.argv[1]; MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 90
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
card = sorted(glob.glob(f'collect/national/{D}/tab_*.raw.txt'))[-1]
known = set(pd.read_parquet('national_runs_c2.parquet' if os.path.exists('national_runs_c2.parquet') else 'national_runs.parquet', columns=['horse']).horse.unique())
meets, cur, out = {}, None, []
for l in open(card, encoding='utf-8'):
    p = l.rstrip('\n').split('|')
    if p[0] == 'MEET' and len(p) >= 4: meets[p[1]] = p[3]
    elif p[0] == 'RACE': cur = (p[1], p[2])
    elif cur and len(p) >= 11 and p[0].isdigit():
        status = (p[10] or '').lower()
        if status in ('latescratched', 'scratched'): continue
        if nk(p[1]) not in known: out.append((cur[0], cur[1], p[0], 'QLD' if meets.get(cur[0]) == 'QLD' else 'NSW', p[1]))
# race order keeps the earliest races first if the cap bites (later runners keep the missing treatment and are logged)
fp = f'prices/{D}/form_todo_prescore.txt'; os.makedirs(os.path.dirname(fp), exist_ok=True)
with open(fp, 'w') as fh:
    for o in out[:MAX]: fh.write('|'.join(o[:4]) + '\n')
print(f'first-starter list {D}: {len(out)} runners with no history | listed {min(len(out), MAX)} | not listed (cap) {max(0, len(out) - MAX)} -> {fp}')
