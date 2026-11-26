"""Pick the best results file for a race day when several exist (Claude's 11:20pm capture, the PC's evening deliveries).
Usage (from research/): python3 ops/pick_results.py <YYYYMMDD>  -> prints the path with the most final races (ties: newest).
A race counts as final when its RACE line ends with Paying, Final or Abandoned (case-insensitive)."""
import sys, glob, os
D = sys.argv[1]
FINAL = {'paying', 'final', 'abandoned'}
best = None
for p in sorted(glob.glob(f'collect/national/{D}/results_*.raw.txt')):
    races = final = 0
    for ln in open(p, encoding='utf-8', errors='replace'):
        if ln.startswith('RACE|'):
            races += 1; final += ln.rstrip('\n').split('|')[-1].strip().lower() in FINAL
    key = (final, os.path.basename(p))
    print(f'{p}: {final}/{races} final', file=sys.stderr)
    if best is None or key > best[0]: best = (key, p)
if not best: print('none'); sys.exit(2)
print(best[1])
