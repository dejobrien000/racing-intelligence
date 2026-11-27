"""Batch 16 B10 (part 2): horses moving between states. For each run whose previous run was in a different state, its innovation
(performance relative to the field minus pre-race rating relative to the field, kg) shows whether the rating carried across the
border was right: positive = the horse ran better than the rating said. Compared with same-state runs and by state pair, on a frame.
Usage: python3 batch16/b10_interstate.py <label>=<frame.parquet> [...] -> batch16/out_b10_interstate.json"""
import sys, json, numpy as np, pandas as pd
OUT = {}
for spec in sys.argv[1:]:
    lab, path = spec.split('=', 1)
    U = pd.read_parquet(path, columns=['horse', 'date', 'race', 'state', 'dyn_nat_inn']).sort_values(['horse', 'date', 'race'])
    U['prev_state'] = U.groupby('horse').state.shift(); U = U[U.dyn_nat_inn.notna() & U.prev_state.notna() & (U.date >= '2024-01-01')]
    U['move'] = np.where(U.state == U.prev_state, 'same state', U.prev_state + '->' + U.state)
    g = U.groupby('move').dyn_nat_inn.agg(['size', 'mean', 'std']); g['se'] = g['std'] / np.sqrt(g['size'])
    g = g[g['size'] >= 150].sort_values('mean')
    same = float(U[U.move == 'same state'].dyn_nat_inn.mean())
    OUT[lab] = {'same_state_mean': round(same, 3), 'pairs': {k: [int(r['size']), round(float(r['mean']) - same, 2), round(float(r.se), 2)] for k, r in g.iterrows() if k != 'same state'},
                'abs_pair_deviation_weighted': round(float(np.average((g.drop('same state', errors='ignore')['mean'] - same).abs(), weights=g.drop('same state', errors='ignore')['size'])), 3)}
    print(lab, json.dumps(OUT[lab])[:1500], flush=True)
prev = {}
try: prev = json.load(open('batch16/out_b10_interstate.json'))
except Exception: pass
prev.update(OUT); json.dump(prev, open('batch16/out_b10_interstate.json', 'w'), indent=1)
