"""Batch 11 s12: simplification. Refit the whole scoring model jointly (all v1 inputs + v2 terms [+ v2.2 terms for national]) with and without
candidate inputs; fit on races before 2025, judge 2025-26 (log-likelihood per race, meeting bootstrap). Gain > 0 from dropping = the input was hurting;
~0 = redundant; < 0 = it earns its place. Queensland uses the Engine v2 Queensland frame (national dynamic rating) as a proxy for v2.1.1. Research only."""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
U0, E, NFAM2, QFAM2, build_terms = g['U'], g['E'], g['NFAM2'], g['QFAM2'], g['build_terms']
def run(x, cols, variants, tag):
    yr = x.meeting_date.dt.year; fitm = pd.Series((yr <= 2024).values, index=x.index); evm = pd.Series((yr >= 2025).values, index=x.index)
    x = L.prep_z(x.copy(), cols, fitm); res = {}
    for nm, drop in variants.items():
        c = [k for k in cols if k not in drop]; b = L.clogit_fit(x, c, fitm, np.zeros(len(x)), ridge=1.0)
        e = x[[k + '_z' for k in c]].values @ b; res[nm] = L.race_lp(x, e, evm); print(tag, nm, 'cols', len(c), 'mean lp', round(res[nm].lp.mean(), 5), flush=True)
    out = []
    for nm in variants:
        if nm == 'full': continue
        d = res[nm].lp - res['full'].lp; h = (res[nm].hit - res['full'].hit) * 100; lo, hi, p = L.boot(d.values, res[nm].meeting_id.values)
        out.append({'model': tag, 'dropped': nm, 'races': len(d), 'gain_from_dropping': round(d.mean(), 5), 'lo95': round(lo, 5), 'hi95': round(hi, 5), 'top_pick_pts': round(h.mean(), 2),
                    'verdict': 'hurting (drop)' if lo > 0 else ('earns its place' if hi < 0 else 'redundant (no measurable effect)')})
    return out
# national
mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); C2 = list(mn['candidates']['nat_v2 (+ horse records)'])
x = E.nat_frame(U0); allt = sum(NFAM2.values(), []); x = build_terms(x, allt)
V = pd.read_parquet('b11/v22hist.parquet'); M22 = json.load(open('benchmarks/engine_v2_2/manifest.json')); T22 = M22['terms']
x = x.merge(V[['race_id', 'horse'] + T22], on=['race_id', 'horse'], how='left'); x['meeting_date'] = pd.to_datetime(x.meeting_date)
x = x.rename(columns={'t::' + a: 'tt_' + a.replace(':', '_').replace('*', 'X') for a in allt}); tcols = ['tt_' + a.replace(':', '_').replace('*', 'X') for a in allt]
cols = C2 + tcols + T22
NV = {'full': [], 'last-start finish': ['f_lastfp'], 'career strike rate': ['f_cwin'], 'older ability figures (a_rec)': ['a_rec'], 'first-up flag': ['r_firstup'],
      'all four together': ['f_lastfp', 'f_cwin', 'a_rec', 'r_firstup']}
out = run(x, cols, NV, 'national (Engine v2.2 inputs)')
# queensland
q = E.qld_frame(U0); qt = sum(QFAM2.values(), []); q = build_terms(q, qt); q['meeting_date'] = pd.to_datetime(q.meeting_date)
q = q.rename(columns={'t::' + a: 'tt_' + a.replace(':', '_').replace('*', 'X') for a in qt}); qcols = list(E.QCOEF) + ['tt_' + a.replace(':', '_').replace('*', 'X') for a in qt]
TRK = E.QFAM['Track/distance/going history']; SEC = E.QFAM['Closing sectionals']
QV = {'full': [], 'last-start finish': ['f_lastfp'], 'track/distance/going history family': TRK, 'closing sectionals family': SEC, 'all three together': ['f_lastfp'] + TRK + SEC}
out += run(q, qcols, QV, 'Queensland (Engine v2 Qld inputs, proxy)')
O = pd.DataFrame(out); print(O.to_string(index=False)); O.to_csv('b11/out_simplify.csv', index=False)
