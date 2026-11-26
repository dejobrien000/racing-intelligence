import numpy as np, pandas as pd, json
rng = np.random.default_rng(3)
def load(f): return pd.read_parquet(f)
F = {'C2 R': 'res_C2_R.parquet', 'C2+hcp': 'res_C2+wt_x_hcp_R.parquet', 'C2J jt (k734)': 'res_C2J+j_spec+t_spec_R.parquet', 'C2J jt (k60, earlier)': 'old/res_C2J+j_spec+t_spec_R_k60.parquet',
     'C2D (j_spec inside j_surp)': 'res_C2D_R.parquet', 'C2J hcp+jt': 'res_C2J+wt_x_hcp+j_spec+t_spec_R.parquet', 'C2D+hcp': 'res_C2D+wt_x_hcp_R.parquet'}
R = {k: load(v) for k, v in F.items()}
def diff(a, b, win):
    x = R[a][R[a].window == win].set_index('race_id'); y = R[b][R[b].window == win].set_index('race_id')
    j = x[['lp', 'hit']].join(y[['lp', 'hit']], lsuffix='_a', rsuffix='_b', how='inner'); d = (j.lp_a - j.lp_b).values
    bs = d[rng.integers(0, len(d), (2000, len(d)))].mean(1); lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(window=win, variant=a, against=b, races=len(j), gain=round(d.mean(), 5), lo95=round(lo, 5), hi95=round(hi, 5), top_pick_pts=round(100 * (j.hit_a.mean() - j.hit_b.mean()), 2))
rows = []
for win in ['A', 'B']:
    for a, b in [('C2J jt (k60, earlier)', 'C2 R'), ('C2J jt (k734)', 'C2 R'), ('C2D (j_spec inside j_surp)', 'C2 R'), ('C2+hcp', 'C2 R'), ('C2J hcp+jt', 'C2 R'), ('C2D+hcp', 'C2 R'),
                 ('C2J hcp+jt', 'C2+hcp'), ('C2D+hcp', 'C2+hcp')]: rows.append(diff(a, b, win))
out = pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv('/home/claude/racing-intelligence/research/batch14/followup/out_engine_small_improvements.csv', index=False)
