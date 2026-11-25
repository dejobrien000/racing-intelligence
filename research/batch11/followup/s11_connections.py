"""Batch 11 follow-up s5: interstate rating connections from individual performance residuals (all runners, not just winners).
Residual = the rating update's surprise (kg): how much better (+) or worse (-) a horse ran than its pre-race rating said, relative to the field.
Final database frame. Horse-clustered bootstrap. Research only."""
import numpy as np, pandas as pd
U = pd.read_parquet('/tmp/nat3/research/engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'state', 'venue', 'tkey', 'dyn_nat', 'dyn_nat_inn', 'finish_pos', 'field'])
U = U[U.dyn_nat_inn.notna()].sort_values(['horse', 'date']).copy(); g = U.groupby('horse')
U['prev_state'] = g.state.shift(); U['prev_inn'] = g.dyn_nat_inn.shift(); U['n_in_state'] = U.groupby(['horse', 'state']).cumcount(); U['runs'] = g.cumcount()
U['next_state'] = g.state.shift(-1); U['next_inn'] = g.dyn_nat_inn.shift(-1)
def ci(v, k, reps=500, seed=4):
    rng = np.random.default_rng(seed); u, inv = np.unique(k, return_inverse=True); s = np.bincount(inv, v); n = np.bincount(inv)
    b = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(reps))]; return round(float(np.percentile(b, 2.5)), 2), round(float(np.percentile(b, 97.5)), 2)
rows = []
mv = U[(U.prev_state.notna()) & (U.prev_state != U.state) & (U.runs >= 3)]
for (a, b), h in mv.groupby(['prev_state', 'state']):
    if len(h) < 150: continue
    f = h[h.n_in_state == 0]; r = U[(U.state == b) & (U.n_in_state.between(1, 3)) & U.horse.isin(f.horse) & (U.date > U.horse.map(f.groupby('horse').date.min()))]
    rows.append({'move': f'{a}->{b}', 'runs': len(h), 'horses': h.horse.nunique(), 'first_start_in_state_runs': len(f), 'first_start_mean_kg': round(f.dyn_nat_inn.mean(), 2), 'first_ci': ci(f.dyn_nat_inn.values, f.horse.values),
                 'next_1-3_starts_mean_kg': round(r.dyn_nat_inn.mean(), 2), 'prev_run_before_move_kg': round(f.prev_inn.mean(), 2)})
R = pd.DataFrame(rows).sort_values('first_start_mean_kg'); print(R.to_string(index=False)); R.to_csv('b11/out_connections.csv', index=False)
print('all runs with 3+ prior runs, same state as last start: mean surprise', round(U[(U.prev_state == U.state) & (U.runs >= 3)].dyn_nat_inn.mean(), 3))
# connectors: horses racing in both Vic and Tas, by year of their Tas start
vt = U[(U.state == 'TAS')]; hv = set(U[U.state == 'VIC'].horse)
print('Tas runs whose horse also raced in Vic (any time held):', round(vt.horse.isin(hv).mean(), 3), '| by year', vt.assign(c=vt.horse.isin(hv)).groupby(vt.date.dt.year).c.mean().round(3).to_dict())
print('horses with runs in both Vic and Tas:', len(hv & set(vt.horse)), '| Tas horses', vt.horse.nunique())
# trainer placement: Vic-based trainers' first Tas starts vs Tas-based trainers' horses returning from Vic
f = mv[(mv.prev_state == 'VIC') & (mv.state == 'TAS') & (mv.n_in_state == 0)].copy()
tas_tr = set(U[U.state == 'TAS'].groupby('tkey').size().loc[lambda s: s >= 50].index)
f['tas_trainer'] = f.tkey.isin(tas_tr)
for k, h in f.groupby('tas_trainer'): print('Vic->Tas first starts, Tas-based trainer' if k else 'Vic->Tas first starts, Vic-based trainer', len(h), round(h.dyn_nat_inn.mean(), 2), ci(h.dyn_nat_inn.values, h.horse.values))
