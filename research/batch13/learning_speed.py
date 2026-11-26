"""Batch 13 (26 Nov 2026, consolidation brief s5): is a common national learning-speed rating supported?
Learning speed = how fast the rating updates its view of a horse (v3 rating: lightly raced horses expected to improve and
their ratings move more), not the horse's physical speed. Compares the current rating (engine/frames/national.parquet) with the
v3 rating (engine/frames/national_v3.parquet, production settings) on IDENTICAL common inputs and identical races:
  common model (nat_v2 inputs) fitted on development races of all six non-Qld states, judged on 2025-26 by region;
  the same common model fitted and judged on Queensland rows (RQ-tracked + Breednet country), so Qld is tested on common inputs;
  the Queensland model (Qld inputs incl. sectionals and race shape), with and without the physical inputs;
  each split by a history-completeness proxy (first held run in the first six months of the database at age 4+ = history
  probably truncated) and by experience held (0-3, 4-10, 11+ prior runs).
2025-26 has been examined before (research-period evidence only). Writes batch13/out/learning_speed.csv."""
import numpy as np, pandas as pd
from engine import evaltools as E
U0 = pd.read_parquet('engine/frames/national.parquet'); F = pd.read_parquet('engine/frames/national_v3.parquet')
def tag_hist(x):
    first = x.groupby('horse').date.transform('min') if 'horse' in x else None
    return first
rows = []
def run(name, frame_fn, cols, splits=()):
    """Fit each rating's model on the frame's development races; judge 2025-26; report all races and each split group (by the winner's row)."""
    R = {}
    for k, U in {'current': U0, 'v3': F}.items():
        x = frame_fn(U); x = E.zcols(x, cols); dev = x.period == 'development'; ev = x.period == 'evaluation'
        r = E.metrics(x, E.eta(x, cols, E.fit(x, cols, dev)), ev)
        w = x.loc[ev & (x.win == 1)].drop_duplicates('race_id').set_index('race_id')
        for nm, fn in splits: r[nm] = fn(w).reindex(r.index).values
        R[k] = r
    d = E.diff(R['current'], R['v3']); rows.append({'test': name, 'split': 'all', 'group': 'all', **E.summary(R['current']), **{'v3_' + a: b for a, b in d.items()}})
    print(name, 'all', d, flush=True)
    for nm, _ in splits:
        for g in sorted(R['current'][nm].dropna().unique()):
            a = R['current'][R['current'][nm] == g]; b = R['v3'].loc[a.index]
            if len(a) >= 150:
                dd = E.diff(a, b); rows.append({'test': name, 'split': nm, 'group': g, 'races': len(a), **{'v3_' + k: v for k, v in dd.items()}}); print('  ', nm, g, dd, flush=True)
def natq(U):   # Queensland rows through the COMMON model (RQ-tracked and Breednet country meetings)
    N = U[(U.state == 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1].copy()
    N['fpos'] = N.finish_pos; N['meeting_date'] = N.date; return N
first = U0.assign(date=pd.to_datetime(U0.date)).sort_values('date').groupby('horse').agg(d0=('date', 'first'), a0=('age_n', 'first'))
TRUNC = ((first.d0 < '2023-04-01') & (first.a0 >= 4)).map({True: 'history probably truncated', False: 'history from early career'})
cnt = U0.assign(date=pd.to_datetime(U0.date)).sort_values(['horse', 'date', 'race_no']); cnt['held'] = cnt.groupby('horse').cumcount()
HELD = cnt.set_index('race_id' if 'race_id' in cnt else 'race').groupby(['horse']).size()   # not used directly
held_map = cnt.set_index(['race_id', 'horse']).held
def s_state(w): return w.state.map(lambda s: 'NSW/Vic/ACT' if s in ('NSW', 'VIC', 'ACT') else 'SA' if s == 'SA' else 'WA/Tas' if s in ('WA', 'TAS') else s)
def s_hist(w): return w.horse.map(TRUNC).fillna('unknown')
def s_exp(w):
    h = pd.Series([held_map.get((r, hh), np.nan) for r, hh in zip(w.index, w.horse)], index=w.index)
    return pd.cut(h, [-1, 3, 10, 1e9], labels=['0-3 runs held', '4-10 runs held', '11+ runs held']).astype(str)
NV2 = E.NV2; QALL = list(E.QCOEF); PHYS = E.QFAM['Closing sectionals'] + E.QFAM['Barrier & race shape']
run('common model, six non-Qld states (fit pooled)', E.nat_frame, NV2, [('region', s_state), ('history', s_hist), ('experience', s_exp)])
run('common model on Queensland rows (RQ-tracked + country)', natq, NV2, [('history', s_hist), ('experience', s_exp)])
run('Queensland model (all Qld inputs)', E.qld_frame, QALL)
run('Queensland model without sectionals and race shape', E.qld_frame, [c for c in QALL if c not in PHYS])
pd.DataFrame(rows).to_csv('batch13/out/learning_speed.csv', index=False); print('written batch13/out/learning_speed.csv')
