"""Batch 11 s12 follow-up (approved by Damo 25 Nov 2026): Queensland simplification on Engine v2.1.1 (v3 rating frame, final database).
Same model as v2.1.1 (v1 inputs refitted on the fitting races, v2 terms penalty 100), refitted without: last-start finish; the
track/distance/going history family; the closing sectionals family; and combinations. Two windows: A = fit before 2024, judge 2024;
B = fit before 2025, judge 2025-26 (the v2.1.1 setting; this period has been examined repeatedly). Research only."""
import json, numpy as np, pandas as pd, hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; ALL = list(E.QCOEF)
TRK = E.QFAM['Track/distance/going history']; SEC = E.QFAM['Closing sectionals']
F = pd.read_parquet('engine/frames/national_v3.parquet')
x0 = E.qld_frame(F); x0 = E.zcols(x0, ALL); x0 = build_terms(x0, QT); x0['meeting_date'] = pd.to_datetime(x0.meeting_date)
V = {'full v2.1.1': [], 'drop last-start finish': ['f_lastfp'], 'drop track/distance/going history': TRK, 'drop closing sectionals': SEC,
     'drop last-start finish + track history': ['f_lastfp'] + TRK, 'drop all three': ['f_lastfp'] + TRK + SEC}
rows = []; coefs = {}
for win, (fit_end, ev_lo, ev_hi) in {'A: fit <2024, judge 2024': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B: fit <2025, judge 2025-26': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = x0.meeting_date < fit_end; em = (x0.meeting_date >= ev_lo) & (x0.meeting_date < ev_hi); res = {}
    for nm, drop in V.items():
        cols = [c for c in ALL if c not in drop]; b1 = E.fit(x0, cols, fm); off = E.eta(x0, cols, b1)
        b2 = fitd(x0, QT, fm, off, 100); e = off + x0[['t::' + t for t in QT]].values @ b2
        res[nm] = E.metrics(x0, e, em); coefs[(win, nm)] = dict(zip(cols, map(float, b1)))
        print(win, nm, E.summary(res[nm]), flush=True)
    for nm in V:
        if nm == 'full v2.1.1': continue
        d = E.diff(res['full v2.1.1'], res[nm]); r26 = res[nm][res[nm].date.dt.year == 2026]; f26 = res['full v2.1.1'][res['full v2.1.1'].date.dt.year == 2026]
        d26 = E.diff(f26, r26) if len(r26) else {}
        rows.append({'window': win, 'variant': nm, **{k: d[k] for k in ['races', 'lp', 'lp_lo', 'lp_hi', 'hit', 'hit_lo', 'hit_hi', 'top3', 'rho']}, 'lp_2026': d26.get('lp'), 'lp_2026_lo': d26.get('lp_lo'), 'lp_2026_hi': d26.get('lp_hi')})
O = pd.DataFrame(rows); print(O.to_string(index=False)); O.to_csv('/tmp/natq/b11/qld_simplify_v211.csv', index=False)
json.dump({f'{a} | {b}': v for (a, b), v in coefs.items()}, open('/tmp/natq/b11/qld_simplify_v211_coefs.json', 'w'), indent=1)
