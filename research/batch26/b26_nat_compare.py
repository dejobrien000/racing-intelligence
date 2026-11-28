"""Batch 26 Part 3: paired comparison of national-harness runs (refit mode R; A = fit before 2024, judge 2024; B = fit before 2025,
judge 2025-26) with and without the measured physical inputs. Matched samples: all national races; SA races; races where at least half
the runners have an earlier tracked run; races where none do (should be unaffected - no penalty for missing measurement).
Also the per-runner check: do horses WITHOUT tracking get lower chances after the inputs are added? (they must not).
Usage: python3 batch26/b26_nat_compare.py <base tag> <variant tag> -> prints and appends to batch26/out_b26_national_phys.json"""
import sys, json, os, numpy as np, pandas as pd
rng = np.random.default_rng(26)
A, B = sys.argv[1], sys.argv[2]
ra = pd.read_parquet(f'/tmp/cand/res_{A}_R.parquet'); rb = pd.read_parquet(f'/tmp/cand/res_{B}_R.parquet')
P = pd.read_parquet('/tmp/cand/feat_phys.parquet', columns=['race_id', 'horse', 'ph_n', 'ph_src'])
cov = P.assign(t=P.ph_n > 0).groupby('race_id').t.mean()
st = P.race_id.str.split('|').str[0]; stt = pd.Series(st.values, index=P.race_id).groupby(level=0).first()
out = {'base': A, 'variant': B}
for w in ['A', 'B']:
    x = ra[ra.window == w].set_index('race_id')[['lp', 'hit']].join(rb[rb.window == w].set_index('race_id')[['lp', 'hit']], lsuffix='_a', rsuffix='_b', how='inner')
    x['cov'] = cov.reindex(x.index).values; x['state'] = stt.reindex(x.index).values
    res = {}
    for lab, m in [('all national races', x.index == x.index), ('SA races', x.state == 'SA'), ('races half+ tracked', x['cov'] >= 0.5),
                   ('races with no tracked runner', x['cov'] == 0)]:
        d = (x.lp_b - x.lp_a)[m].values
        if len(d) < 50: continue
        bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1); lo, hi = np.percentile(bs, [2.5, 97.5])
        res[lab] = {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'ci95': [round(float(lo), 5), round(float(hi), 5)],
                    'top_pick_pts': round(float(100 * (x.hit_b[m].mean() - x.hit_a[m].mean())), 2)}
    out[w] = res
# runner level: untracked horses' chances before vs after (window B)
fa, fb = f'/tmp/cand/runners_{A}_R.parquet', f'/tmp/cand/runners_{B}_R.parquet'
if os.path.exists(fa) and os.path.exists(fb):
    ua = pd.read_parquet(fa, columns=['race_id', 'horse', 'p_B']); ub = pd.read_parquet(fb, columns=['race_id', 'horse', 'p_B'])
    u = ua.merge(ub, on=['race_id', 'horse'], suffixes=('_a', '_b')).merge(P, on=['race_id', 'horse'], how='left'); u = u[u.p_B_a.notna()]
    u['tracked'] = u.ph_n.fillna(0) > 0
    mixed = u.groupby('race_id').tracked.transform('mean').between(0.01, 0.99)
    g = u[mixed].groupby('tracked')
    out['runner_check_window_B_mixed_races'] = {('tracked' if k else 'untracked'): {'runners': int(len(v)), 'mean_chance_before_pct': round(float(100 * v.p_B_a.mean()), 3),
                                                  'mean_chance_after_pct': round(float(100 * v.p_B_b.mean()), 3)} for k, v in g}
print(json.dumps(out, indent=1))
f = 'batch26/out_b26_national_phys.json'; allr = json.load(open(f)) if os.path.exists(f) else {}
allr[f'{B} vs {A}'] = out; json.dump(allr, open(f, 'w'), indent=1)
