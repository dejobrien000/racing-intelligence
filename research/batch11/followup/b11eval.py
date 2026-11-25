import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/b10/research/b10/scripts'); import lib10 as L
V = sys.argv[1]
src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
U0, E, NFAM2, build_terms = g['U'], g['E'], g['NFAM2'], g['build_terms']
C2 = list(json.load(open('benchmarks/candidates_national_common/manifest.json'))['candidates']['nat_v2 (+ horse records)'])
x = E.nat_frame(U0); allt = sum(NFAM2.values(), []); x = build_terms(x, allt); x['meeting_date'] = pd.to_datetime(x.meeting_date)
x = x.rename(columns={'t::' + a: 'tt_' + a.replace(':', '_').replace('*', 'X') for a in allt}); cols = C2 + ['tt_' + a.replace(':', '_').replace('*', 'X') for a in allt]
out = []
for w, (fe, lo, hi) in {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = pd.Series((x.meeting_date < fe).values, index=x.index); em = pd.Series(((x.meeting_date >= lo) & (x.meeting_date < hi)).values, index=x.index)
    z = L.prep_z(x.copy(), cols, fm); b = L.clogit_fit(z, cols, fm, np.zeros(len(z)), ridge=1.0); e = z[[c + '_z' for c in cols]].values @ b
    r = L.race_lp(z, e, em); r['window'] = w; r['variant'] = V; out.append(r.reset_index())
    print(V, w, 'races', len(r), 'mean lp', round(r.lp.mean(), 5), 'top pick', round(100 * r.hit.mean(), 2), 'a_wt_rel coef', round(float(b[cols.index('a_wt_rel')]), 4), 'dyn_nat coef', round(float(b[cols.index('dyn_nat')]), 4), flush=True)
pd.concat(out).to_parquet(f'/tmp/exp/res_{V}.parquet')
