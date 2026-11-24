"""Non-additivity check and the start of the improvement chain: each v2 family ALONE on top of v1 (dev fit -> 2025-26) vs all
together; plus the NSW/Vic chain's first link (common features only, no national rating). Outputs engine/out/additivity.csv"""
import numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
rows = []
for kind, FAM in [('qld', {k: QFAM2[k] for k in ['Horse course/going/distance records', 'Jockey & trainer']}), ('nat', NFAM2)]:
    x = E.nat_frame(U) if kind == 'nat' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, kind)
    dev, ev = x.period == 'development', x.period == 'evaluation'; r1 = met(x, [], None, off, ev); tot = 0
    for fam, ts in FAM.items():
        tau = choose_tau(x, ts, off); r = met(x, ts, fitd(x, ts, dev, off, tau), off, ev); d = E.diff(r1, r); tot += d['lp']
        rows.append({'model': kind, 'family alone on top of v1': fam, 'gain_lp': d['lp'], 'lo': d['lp_lo'], 'hi': d['lp_hi'], 'top_pick_pts': d['hit']})
    tau = choose_tau(x, allt, off); r = met(x, allt, fitd(x, allt, dev, off, tau), off, ev); d = E.diff(r1, r)
    rows.append({'model': kind, 'family alone on top of v1': 'SUM of the separate gains', 'gain_lp': round(tot, 5)})
    rows.append({'model': kind, 'family alone on top of v1': 'ALL TOGETHER (jointly fitted)', 'gain_lp': d['lp'], 'lo': d['lp_lo'], 'hi': d['lp_hi'], 'top_pick_pts': d['hit']})
    if kind == 'nat':
        F_ = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform']; A_ = ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']; R_ = ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays']
        x = E.zcols(x, F_ + A_ + R_); r0 = E.metrics(x, E.eta(x, F_ + A_ + R_, E.fit(x, F_ + A_ + R_, dev)), ev)
        rows.append({'model': kind, 'family alone on top of v1': 'CHAIN START: common features only (no national rating)', **E.summary(r0)})
T = pd.DataFrame(rows); T.to_csv('engine/out/additivity.csv', index=False); print(T.to_string(index=False))
