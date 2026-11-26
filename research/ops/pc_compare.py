"""Proving period: compare the PC collector's file with Claude's own collection for the same day.
Usage (from research/): python3 ops/pc_compare.py <claude file> <pc file> [morning|evening]
Compares races and runners (name, barrier, weight, claim, rider, trainer, emergency, betting status; evening also finish and
race status). Prices are NOT compared (they move between two reads seconds apart) and are never used by the model anyway.
Prints one summary line (copy it into the log) and up to 15 differences. Exit 0 = identical on these fields, 1 = differences."""
import sys
def load(p, evening):
    races, runners, ven, rn = {}, {}, None, None
    for ln in open(p, encoding='utf-8', errors='replace'):
        f = ln.rstrip('\n').split('|')
        if f[0] == 'RACE' and len(f) > 3:
            ven, rn = f[1], f[2]; races[(ven, rn)] = (f[3], f[5], f[-1].lower() if evening else '')
        elif ven and len(f) >= 12 and f[0].isdigit():
            keep = f[1:8] + [f[10]] + ([f[-1]] if evening else [])
            runners[(ven, rn, f[0])] = [x.strip().upper() for x in keep]
    return races, runners
a, b = sys.argv[1], sys.argv[2]; ev = len(sys.argv) > 3 and sys.argv[3] == 'evening'
ra, ua = load(a, ev); rb, ub = load(b, ev)
diffs = [f'race only in Claude file: {k}' for k in sorted(set(ra) - set(rb))] + [f'race only in PC file: {k}' for k in sorted(set(rb) - set(ra))]
diffs += [f'race differs {k}: Claude {ra[k]} | PC {rb[k]}' for k in sorted(set(ra) & set(rb)) if ra[k] != rb[k]]
diffs += [f'runner only in Claude file: {k}' for k in sorted(set(ua) - set(ub))] + [f'runner only in PC file: {k}' for k in sorted(set(ub) - set(ua))]
names = ['name', 'barrier', 'weight', 'claim', 'rider', 'trainer', 'emergency', 'status', 'finish']
for k in sorted(set(ua) & set(ub)):
    d = [f'{names[i]} {x}->{y}' for i, (x, y) in enumerate(zip(ua[k], ub[k])) if x != y]
    if d: diffs.append(f'runner {k}: ' + ', '.join(d))
print(f'pc_compare {"evening" if ev else "morning"}: races Claude {len(ra)} / PC {len(rb)}, runners Claude {len(ua)} / PC {len(ub)}, differences {len(diffs)}')
for x in diffs[:15]: print('  ' + x)
sys.exit(1 if diffs else 0)
