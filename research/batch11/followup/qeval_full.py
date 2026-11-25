"""Queensland v2.1.1-style refit on a given research dir's frames; per-race log-lik for windows A (fit<2024, judge 2024) and B (fit<2025, judge 2025-26). Writes only to /tmp/exp2."""
import os, sys, json, numpy as np, pandas as pd
D, LAB = sys.argv[1], sys.argv[2]; os.chdir(D); sys.path.insert(0, D)
import hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
QT = QFAM2['Horse course/going/distance records'] + QFAM2['Jockey & trainer']; ALL = list(E.QCOEF)
x0 = E.qld_frame(pd.read_parquet('engine/frames/national_v3.parquet')); x0 = E.zcols(x0, ALL); x0 = build_terms(x0, QT); x0['meeting_date'] = pd.to_datetime(x0.meeting_date)
out = []
for win, (fe, lo, hi) in {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
    fm = x0.meeting_date < fe; em = (x0.meeting_date >= lo) & (x0.meeting_date < hi)
    b1 = E.fit(x0, ALL, fm); off = E.eta(x0, ALL, b1); b2 = fitd(x0, QT, fm, off, 100); e = off + x0[['t::' + t for t in QT]].values @ b2
    r = E.metrics(x0, e, em); r['window'] = win; r['label'] = LAB; out.append(r.reset_index())
    print(LAB, win, E.summary(r), 'a_wt_rel coef', round(float(b1[ALL.index('a_wt_rel')]), 4), flush=True)
pd.concat(out).to_parquet(f'/tmp/exp2/qres_{LAB}.parquet')
