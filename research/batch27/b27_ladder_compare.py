"""Batch 27 P3: preregistered distance comparisons and the combination ladder (paired per-race log-likelihood, 95% race bootstrap).
Reads the national harness outputs /tmp/cand/res_<tag>_R.parquet. Output batch27/out_b27_ladder.json"""
import json, os, numpy as np, pandas as pd
rng = np.random.default_rng(2727)
def lp(tag, w):
    f = f'/tmp/cand/res_{tag}_R.parquet'
    if not os.path.exists(f): return None
    r = pd.read_parquet(f); return r[r.window == w].drop_duplicates('race_id').set_index('race_id').lp
def cmp(a, b):
    o = {}
    for w in ['A', 'B']:
        x, y = lp(a, w), lp(b, w)
        if x is None or y is None: return None
        j = pd.concat([x.rename('a'), y.rename('b')], axis=1, join='inner'); d = (j.b - j.a).values
        bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1)
        o[w] = {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'ci95': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]}
    return o
L4 = 'K27dR+wt_x_hcp+tr_debut_x+sire_debut_x'
C = {
 'D1 v2.3: distance record replaced (vs v2.3)': ('P26', 'P26dR'),
 'D2 consolidated: distance record replaced (vs consolidated)': ('K26', 'K27dR'),
 'D3 Qld common config 2: distance record replaced': ('Q26', 'Q27dR'),
 'D3b Qld common on consolidated: distance record replaced': ('QK27', 'QK27dR'),
 'L1 consolidated rating (vs v2.3)': ('P26', 'K26'),
 'L2 + handicap weight slope (vs L1)': ('K26', 'K27+wt_x_hcp'),
 'L3 + distance replacement (vs L2)': ('K27+wt_x_hcp', 'K27dR+wt_x_hcp'),
 'L4 + trainer and sire debut (vs L3)': ('K27dR+wt_x_hcp', L4),
 'L5 + 365-day returner terms (vs L4)': (L4, L4 + '+ret365+ret365_lgap+ret365_age'),
 'L2 vs v2.3': ('P26', 'K27+wt_x_hcp'), 'L3 vs v2.3': ('P26', 'K27dR+wt_x_hcp'), 'L4 vs v2.3': ('P26', L4), 'L5 vs v2.3': ('P26', L4 + '+ret365+ret365_lgap+ret365_age'),
 'ablation L4 minus consolidated rating': (L4, 'P27dR+wt_x_hcp+tr_debut_x+sire_debut_x'),
 'ablation L4 minus handicap weight': (L4, 'K27dR+tr_debut_x+sire_debut_x'),
 'ablation L4 minus distance replacement': (L4, 'K27+wt_x_hcp+tr_debut_x+sire_debut_x'),
 'ablation L4 minus debut terms': (L4, 'K27dR+wt_x_hcp'),
 'reference: v2.4 analogue (v2.3 + handicap weight)': ('P26', 'P27+wt_x_hcp'),
 'reference: returner terms on v2.3': ('P26', 'P27+ret365+ret365_lgap+ret365_age'),
 'reference: returner terms on consolidated': ('K26', 'K27+ret365+ret365_lgap+ret365_age'),
}
out = {}
for k, (a, b) in C.items():
    r = cmp(a, b)
    if r: out[k] = r; print(f"{k:62s} A {r['A']['gain']:+.5f} {r['A']['ci95']}  B {r['B']['gain']:+.5f} {r['B']['ci95']}")
    else: print(k, 'missing', a, b)
json.dump(out, open('batch27/out_b27_ladder.json', 'w'), indent=1)
