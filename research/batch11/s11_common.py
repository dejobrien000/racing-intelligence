import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
def base_p(years=(2023, 2024, 2025, 2026)):
    b = L.base('nat'); b = b[b.meeting_date.dt.year.isin(years)].copy()
    mx = b.groupby('race_id').v2.transform('max'); b['p'] = np.exp(b.v2 - mx); b['p'] /= b.groupby('race_id').p.transform('sum'); return b
def ae(g, cluster=None, reps=400, seed=3):
    """actual/expected wins with a cluster (horse) bootstrap CI"""
    w, e = g.win.sum(), g.p.sum(); out = {'runners': len(g), 'wins': int(w), 'expected': round(float(e), 1), 'ratio': round(float(w / e), 2) if e else np.nan}
    if cluster is not None and len(g) > 20:
        rng = np.random.default_rng(seed); k = g[cluster].values; u, inv = np.unique(k, return_inverse=True); sw = np.bincount(inv, g.win.values); se = np.bincount(inv, g.p.values)
        bs = [sw[i].sum() / se[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(reps))]; out['lo95'], out['hi95'] = round(float(np.percentile(bs, 2.5)), 2), round(float(np.percentile(bs, 97.5)), 2); out['clusters'] = len(u)
    return out
