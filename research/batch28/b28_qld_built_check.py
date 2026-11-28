"""Batch 28 item 2: built check for the Queensland common framework on the consolidated rating (QCF config 5, built through the release
chain on Queensland races only). Its dev-fit chances on 2025-26 Queensland races (release-chain output) vs Queensland production
Engine v2.1.3 (frozen, as it runs; and refitted before 2025) on the same races. Paired per-race log-likelihood, race bootstrap.
Output batch28/out_b28_qld_built_check.json"""
import json, numpy as np, pandas as pd, os, sys
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", "pd.read_parquet('engine/frames/national_v3.parquet')"); exec(src)
rng = np.random.default_rng(282)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); TAU = Q3.get('penalty_tau', 100)
COLS = list(E.QCOEF); x = E.qld_frame(U); x = E.zcols(x, COLS); x = build_terms(x, NEW)
PV = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))['coefficients_per_dev_sd']
e0 = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS]) + x[['t::' + t for t in NEW]].fillna(0.0).values @ np.array([Q3['coef_per_term_sd_dev_fit'][t] for t in NEW])
em = x.meeting_date >= '2025-01-01'; fm = (x.meeting_date < '2025-01-01') & x.period.notna()
prod = E.metrics(x, e0, em).lp
b1 = E.fit(x, COLS, fm, 1e-6); off = E.eta(x, COLS, b1); prod_refit = E.metrics(x, off + x[['t::' + t for t in NEW]].values @ fitd(x, NEW, fm, off, TAU), em).lp
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'q_race_id', 'state']); F = F[F.state == 'QLD'].dropna().drop_duplicates('race_id').set_index('race_id').q_race_id
O = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else '/tmp/q5/v22_oos_qcf5.parquet'); O['q'] = O.race_id.map(F)
w = O[O.win == 1].dropna(subset=['q']).drop_duplicates('q'); built = pd.Series(np.log(w.p.values), index=w.q.values)
def paired(a, b):
    j = pd.concat([a.rename('a'), b.rename('b')], axis=1, join='inner').dropna(); d = (j.b - j.a).values; bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1)
    return {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'ci95': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]}
out = {'built config 5 vs Qld production v2.1.3 frozen (2025-26)': paired(prod, built), 'built config 5 vs Qld production structure refitted before 2025': paired(prod_refit, built),
       'mean lp': {'production frozen': round(float(prod.mean()), 5), 'production refit': round(float(prod_refit.mean()), 5), 'built config 5': round(float(built.mean()), 5)}}
json.dump(out, open('batch28/out_b28_qld_built_check.json', 'w'), indent=1); print(json.dumps(out, indent=0))
