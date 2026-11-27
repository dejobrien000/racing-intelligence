"""Batch 16 B9: the update-rule candidate AS BUILT by the release chain vs Engine v2.3 as built (= production), same races, 2025-26
out-of-sample chances from each build's development fit (b10/scripts/build_v22.py output). Meeting bootstrap 95% intervals. No prices.
Usage: python3 batch16/b9_built_check.py <candidate oos> <v2.3 oos> -> batch16/out_b9_built_check.json"""
import sys, json, numpy as np, pandas as pd
a = pd.read_parquet(sys.argv[2]); b = pd.read_parquet(sys.argv[1])
def per_race(o):
    w = o[o.win == 1].groupby('race_id').p.first(); top = o.loc[o.groupby('race_id').p.idxmax()].set_index('race_id').win
    return pd.DataFrame({'lp': np.log(w.clip(lower=1e-9)), 'hit': top.reindex(w.index), 'meeting': o.groupby('race_id').meeting_id.first().reindex(w.index), 'state': o.groupby('race_id').state.first().reindex(w.index)})
A, B = per_race(a), per_race(b); j = A.index.intersection(B.index); A, B = A.loc[j], B.loc[j]
d = pd.DataFrame({'d': B.lp - A.lp, 'h': (B.hit - A.hit) * 100, 'meeting': A.meeting, 'state': A.state, 'yr': [r.split('|')[2][:4] if '|' in str(r) else '' for r in j]}, index=j)
def ci(x, reps=1000, seed=7):
    rng = np.random.default_rng(seed); g = x.groupby('meeting'); s = g.d.sum(); n = g.d.count(); hs = g.h.sum(); um = s.index.values
    bs = []; bh = []
    for _ in range(reps):
        k = rng.integers(0, len(um), len(um)); bs.append(s.values[k].sum() / n.values[k].sum()); bh.append(hs.values[k].sum() / n.values[k].sum())
    return {'races': int(len(x)), 'gain': round(float(x.d.mean()), 5), 'lo': round(float(np.percentile(bs, 2.5)), 5), 'hi': round(float(np.percentile(bs, 97.5)), 5),
            'top_pick_pts': round(float(x.h.mean()), 2), 'tp_lo': round(float(np.percentile(bh, 2.5)), 2), 'tp_hi': round(float(np.percentile(bh, 97.5)), 2)}
OUT = {'all 2025-26': ci(d), 'top_pick_rate_candidate': round(float(B.hit.mean() * 100), 2), 'top_pick_rate_v2_3': round(float(A.hit.mean() * 100), 2)}
for s_, x in d.groupby('state'): OUT['state ' + s_] = ci(x)
for y, x in d.groupby('yr'):
    if y: OUT['year ' + y] = ci(x)
json.dump(OUT, open('batch16/out_b9_built_check.json', 'w'), indent=1); print(json.dumps(OUT, indent=0))
