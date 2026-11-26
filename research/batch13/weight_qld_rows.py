"""Batch 13 (26 Nov 2026, brief s2/s6): the national rating's history takes Queensland rows from Racing Queensland (ALLOCATED weight) and
every other state from Breednet (CARRIED weight). Test: rebuild the national rating with Queensland rows on Breednet's carried weight
where Breednet holds the run (sandbox frame /tmp/b0/research/engine/frames/national.parquet, national.py patched in the sandbox only)
and compare on identical races with the common model: fit on development races, judge 2025-26, by region and on Queensland rows.
Writes batch13/out/weight_qld_rows.csv. Research only."""
import sys, pandas as pd, numpy as np
from engine import evaltools as E
A = pd.read_parquet('engine/frames/national.parquet'); B = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else '/tmp/b0/research/engine/frames/national.parquet')
def natq(U):
    N = U[(U.state == 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1].copy(); N['fpos'] = N.finish_pos; N['meeting_date'] = N.date; return N
rows = []
for name, fn in [('six non-Qld states', E.nat_frame), ('Queensland rows', natq)]:
    R = {}
    for k, U in {'production (Qld allocated)': A, 'Qld rows carried': B}.items():
        x = E.zcols(fn(U), E.NV2); dev = x.period == 'development'; ev = x.period == 'evaluation'
        r = E.metrics(x, E.eta(x, E.NV2, E.fit(x, E.NV2, dev)), ev); r['state'] = x.loc[ev].groupby('race_id').state.first().reindex(r.index).values; R[k] = r
    d = E.diff(R['production (Qld allocated)'], R['Qld rows carried']); rows.append({'population': name, 'group': 'all', **d}); print(name, d, flush=True)
    if name.startswith('six'):
        for g, st in [('NSW/Vic/ACT', ['NSW', 'VIC', 'ACT']), ('SA', ['SA']), ('WA/Tas', ['WA', 'TAS'])]:
            a = R['production (Qld allocated)'][R['production (Qld allocated)'].state.isin(st)]; b = R['Qld rows carried'].loc[a.index]
            dd = E.diff(a, b); rows.append({'population': name, 'group': g, **dd}); print('  ', g, dd, flush=True)
chg = (A.weight_kg != B.weight_kg) & (A.state == 'QLD'); print('Qld rows whose weight changed:', int(chg.sum()), 'of', int((A.state == 'QLD').sum()))
pd.DataFrame(rows).to_csv('batch13/out/weight_qld_rows.csv', index=False)
