"""Batch 12 s3: handicap residual by weight vs field, 2025-26 (window B chances: fitted before 2025), per variant/mode.
actual / expected wins, 95% interval by race bootstrap. Usage: python3 hcp_resid.py B0_P B0_R C2_R ..."""
import sys, numpy as np, pandas as pd
rng = np.random.default_rng(12)
def ae(g):
    w = g.groupby('race_id').agg(a=('win', 'sum'), e=('p_B', 'sum')); r = w.a.sum() / w.e.sum()
    idx = rng.integers(0, len(w), (400, len(w))); A, E = w.a.values[idx].sum(1), w.e.values[idx].sum(1)
    lo, hi = np.percentile(A / E, [2.5, 97.5]); return len(g), int(w.a.sum()), round(w.e.sum(), 1), round(r, 2), f'{lo:.2f}-{hi:.2f}'
rows = []
for tag in sys.argv[1:]:
    d = pd.read_parquet(f'/tmp/cand/runners_{tag}.parquet'); d = d[d.p_B.notna()].copy(); d['win'] = d.win.astype(float)
    hcp = d.class_label.isin(['Benchmark', 'BM', 'Open/Hcp'])
    d['wb'] = pd.cut(d.a_wt_rel, [-99, -3, -1, 1, 3, 99], labels=['3 kg+ under field', '1-3 under', 'within 1', '1-3 over', '3 kg+ over'])
    groups = {'all 2025-26': d, 'carried <=54 kg': d[d.weight_kg <= 54], '<=54 kg in benchmark handicaps': d[(d.weight_kg <= 54) & (d.class_label == 'Benchmark')]}
    for b in d.wb.cat.categories: groups[f'handicaps: {b}'] = d[hcp & (d.wb == b)]
    for k, g in groups.items():
        n, a, e, r, ci = ae(g); rows.append(dict(variant=tag, group=k, runners=n, wins=a, expected=e, actual_over_expected=r, ci=ci))
out = pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv('/tmp/cand/out_hcp_resid.csv', index=False)
