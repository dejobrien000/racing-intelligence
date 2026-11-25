"""Batch 12 s3: paired comparison of the weight candidate variants against the complete production v2.2 (B0 mode P) and the
refitted baseline (B0 mode R). Per-race log-likelihood differences, 95% interval by race bootstrap."""
import glob, numpy as np, pandas as pd
rng = np.random.default_rng(3)
R = pd.concat([pd.read_parquet(f) for f in glob.glob('/tmp/cand/res_*.parquet')])
R['key'] = R.variant + ' ' + R['mode']
def diff(a, b, win):
    x = R[(R.key == a) & (R.window == win)].set_index('race_id'); y = R[(R.key == b) & (R.window == win)].set_index('race_id')
    j = x[['lp', 'hit']].join(y[['lp', 'hit']], lsuffix='_a', rsuffix='_b', how='inner'); d = (j.lp_a - j.lp_b).values
    bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1); lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(window=win, variant=a, against=b, races=len(j), gain=round(d.mean(), 5), lo95=round(lo, 5), hi95=round(hi, 5),
                top_pick_pts=round(100 * (j.hit_a.mean() - j.hit_b.mean()), 2))
rows = []
keys = sorted(R.key.unique())
for win in ['A', 'B']:
    for k in keys:
        if k != 'B0 P': rows.append(diff(k, 'B0 P', win))
    for a, b in [('C2 R', 'B0 R'), ('W025 R', 'B0 R'), ('S1 R', 'B0 R'), ('C2 R-noW', 'B0 R-noW'), ('W025 R-noW', 'B0 R-noW'), ('S1 R-noW', 'B0 R-noW'),
                 ('B0 R-noW', 'B0 R'), ('C2 R-noW', 'C2 R')]:
        if a in keys and b in keys: rows.append(diff(a, b, win))
out = pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv('/tmp/cand/out_compare.csv', index=False)
lev = R.groupby(['window', 'key']).agg(races=('lp', 'size'), mean_lp=('lp', 'mean'), top_pick=('hit', 'mean')).round(5); print(lev.to_string())
lev.to_csv('/tmp/cand/out_levels.csv')
