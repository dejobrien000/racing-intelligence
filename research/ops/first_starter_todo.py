"""First-starter age and sex, morning list (Batch 18 A1, approved by Damo 27 Nov 2026). Before scoring, list today's runners whose age or
sex production would otherwise serve as missing, so step 3b can fetch TAB's own form record for them (score_v2 fills ANY missing age/sex
from that record when ops/agesex_tab_enabled is on; nothing is guessed).
Batch 27 (28 Nov 2026, operational correction - collection order only, no change to what is served or how):
  - true race-start order (the old list followed the card's meeting order, so Gold Coast R1 first starters were cut by the cutoff on 28 Nov);
  - meetings in states we do not rate (NT: Darwin is fields-only) are left out - their records were fetched for nothing;
  - also lists horses WITH held runs whose latest held run carries no age (production would serve age missing: 7 runners on 28 Nov);
  - within a race, horses with no held runs first (genuinely unraced or history not held), then the missing-age horses.
Usage (from research/): python3 ops/first_starter_todo.py <YYYYMMDD> [max]  -> prices/<D>/form_todo_prescore.txt (VEN|race|runnerNumber|J)"""
import sys, glob, re, os, pandas as pd
D = sys.argv[1]; MAX = int(sys.argv[2]) if len(sys.argv) > 2 else 90
RATED = {'NSW', 'VIC', 'QLD', 'SA', 'WA', 'TAS', 'ACT'}
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
card = sorted(glob.glob(f'collect/national/{D}/tab_*.raw.txt'))[-1]
known = set(pd.read_parquet('national_runs_c2.parquet' if os.path.exists('national_runs_c2.parquet') else 'national_runs.parquet', columns=['horse']).horse.unique())
age_missing = set()
if os.path.exists('engine/frames/national_c2.parquet'):
    H = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'age_n']).sort_values(['horse', 'date'])
    L = H.groupby('horse').tail(1); age_missing = set(L[L.age_n.isna()].horse)
meets, cur, out, skipped = {}, None, [], 0
for l in open(card, encoding='utf-8'):
    p = l.rstrip('\n').split('|')
    if p[0] == 'MEET' and len(p) >= 4: meets[p[1]] = p[3]
    elif p[0] == 'RACE': cur = (p[1], p[2], p[4] if len(p) > 4 else '')
    elif cur and len(p) >= 11 and p[0].isdigit():
        status = (p[10] or '').lower()
        if status in ('latescratched', 'scratched'): continue
        k = nk(p[1]); kind = 0 if k not in known else (1 if k in age_missing else None)
        if kind is None: continue
        if meets.get(cur[0]) not in RATED: skipped += 1; continue
        out.append((cur[2], kind, cur[0], int(cur[1]), int(p[0]), 'QLD' if meets.get(cur[0]) == 'QLD' else 'NSW'))
out.sort(key=lambda o: (o[0], o[2], o[3], o[1], o[4]))          # race start (UTC ISO sorts as text), then race, unraced before missing-age
fp = f'prices/{D}/form_todo_prescore.txt'; os.makedirs(os.path.dirname(fp), exist_ok=True)
with open(fp, 'w') as fh:
    for o in out[:MAX]: fh.write(f'{o[2]}|{o[3]}|{o[4]}|{o[5]}\n')
n0 = sum(1 for o in out if o[1] == 0); n1 = len(out) - n0
print(f'first-starter list {D}: {n0} runners with no held runs + {n1} with held runs but no age | listed {min(len(out), MAX)} | '
      f'not listed (cap) {max(0, len(out) - MAX)} | left out (meetings not rated, e.g. NT) {skipped} -> {fp}')
