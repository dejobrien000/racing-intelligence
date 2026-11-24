"""Feature audit (brief 24 Nov, Part 8 / 14A): how much does each operational feature and feature family add?
Qld operational model (combined_v1 + national rating, 41 terms) and NSW/Vic/ACT operational model (nat_v2, 20 terms).
For each: refit on development races without the feature (drop-one) or without the family (drop-family), and the family
ALONE (with nothing else), then compare on identical 2025-26 races. Redundant = useful alone, but losing it costs nothing.
Outputs engine/out/ablation_*.csv"""
import os, numpy as np, pandas as pd
from engine import evaltools as E
os.makedirs('engine/out', exist_ok=True)
U = pd.read_parquet('engine/frames/national.parquet')
def audit(x, ALL, FAM, tag):
    x = E.zcols(x, ALL); dev = (x.period == 'development'); ev = (x.period == 'evaluation')
    full = E.metrics(x, E.eta(x, ALL, E.fit(x, ALL, dev)), ev); rows = [{'set': 'FULL MODEL', 'kind': 'full', **E.summary(full)}]
    def drop(cols, kind, name):
        keep = [c for c in ALL if c not in cols]; r = E.metrics(x, E.eta(x, keep, E.fit(x, keep, dev)), ev); d = E.diff(r, full)   # full minus dropped = what the dropped part adds
        rows.append({'set': name, 'kind': kind, **E.summary(r), **{'adds_' + k: v for k, v in d.items() if k != 'races'}})
    for fam, cols in FAM.items(): drop(cols, 'drop family', fam)
    for c in ALL: drop([c], 'drop one', c)
    null = E.metrics(x, np.zeros(len(x)), ev)
    for fam, cols in FAM.items():
        r = E.metrics(x, E.eta(x, cols, E.fit(x, cols, dev)), ev); d = E.diff(null, r)
        rows.append({'set': fam, 'kind': 'family alone', **E.summary(r), **{'alone_' + k: v for k, v in d.items() if k != 'races'}})
    # stability: what each family adds in 2025 vs 2026 separately
    for fam, cols in FAM.items():
        keep = [c for c in ALL if c not in cols]; r = E.metrics(x, E.eta(x, keep, E.fit(x, keep, dev)), ev)
        for yr in [2025, 2026]:
            m = full.date.dt.year == yr; d = E.diff(r[m], full[m]); rows.append({'set': fam, 'kind': f'drop family {yr}', 'adds_lp': d['lp'], 'adds_lp_lo': d['lp_lo'], 'adds_lp_hi': d['lp_hi'], 'adds_hit': d['hit']})
    T = pd.DataFrame(rows); T.to_csv(f'engine/out/ablation_{tag}.csv', index=False); return T
cols = ['set', 'kind', 'fit_%', 'top_pick_%', 'adds_lp', 'adds_lp_lo', 'adds_lp_hi', 'adds_hit', 'adds_top3', 'adds_rho', 'alone_lp']
xq = E.qld_frame(U); TQ = audit(xq, list(E.QCOEF), E.QFAM, 'qld')
print('QLD'); print(TQ[TQ.kind.isin(['full', 'drop family', 'family alone'])][[c for c in cols if c in TQ]].to_string(index=False))
print(TQ[TQ.kind == 'drop one'].sort_values('adds_lp', ascending=False)[['set', 'adds_lp', 'adds_lp_lo', 'adds_lp_hi', 'adds_hit', 'adds_rho']].to_string(index=False))
xn = E.nat_frame(U); TN = audit(xn, E.NV2, E.NFAM, 'nat')
print('NSW/VIC/ACT'); print(TN[TN.kind.isin(['full', 'drop family', 'family alone'])][[c for c in cols if c in TN]].to_string(index=False))
print(TN[TN.kind == 'drop one'].sort_values('adds_lp', ascending=False)[['set', 'adds_lp', 'adds_lp_lo', 'adds_lp_hi', 'adds_hit', 'adds_rho']].to_string(index=False))
