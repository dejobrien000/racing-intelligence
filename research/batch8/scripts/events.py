"""Batch 8 quick tests: build a run -> next-run event table from the national frame (point-in-time).
Outcome Y = next run's surprise (dyn_nat_inn): how far the horse ran above (+) or below (-) its pre-race rating, kg,
relative to the field. Persistence of a surprise = (Y + K*inn) / inn: the share of the jump that showed up again."""
import numpy as np, pandas as pd
S = 4.5   # rating noise s_kg (benchmarks/candidates_b4_national)
U = pd.read_parquet('engine/frames/national.parquet', columns=['state', 'venue', 'date', 'race_id', 'race', 'horse', 'distance_m', 'field', 'finish_pos', 'margin_l',
     'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'age_n', 'female', 'q_race_id', 'q_horse_id', 'period', 'gap', 'win', 'tier', 'metro', 'cond_group', 'going'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
g = U.groupby('horse')
U['start_no'] = g.cumcount()                                   # career starts before this run (in our history)
U['K'] = U.dyn_nat_sd ** 2 / (U.dyn_nat_sd ** 2 + S * S)       # how much the rating moves toward a surprise
U['inn_m1'] = g.dyn_nat_inn.shift(1); U['inn_m2'] = g.dyn_nat_inn.shift(2)
U['peak'] = g.dyn_nat.cummax()                                 # best pre-race rating so far (incl. today)
U['days_prev'] = (U.date - g.date.shift(1)).dt.days
U['spell'] = (U.days_prev > 60) | U.days_prev.isna()
U['prep_run'] = U.groupby((U.spell | (U.horse != U.horse.shift())).cumsum()).cumcount() + 1
U['starts_365'] = g.apply(lambda h: h.set_index('date').win.rolling('365D').count().shift(1).values if len(h) else []).explode().values.astype(float) if False else np.nan
for c in ['date', 'dyn_nat_inn', 'dyn_nat', 'distance_m', 'race_id', 'field', 'finish_pos', 'state', 'venue', 'peak', 'prep_run', 'q_race_id', 'win', 'metro']:
    U['nx_' + c] = g[c].shift(-1)
U['gap_next'] = (U.nx_date - U.date).dt.days
U.to_parquet('/tmp/exp/rt/events.parquet')
ok = U.dyn_nat_inn.notna() & U.nx_dyn_nat_inn.notna()
print('runs', len(U), '| with this run and next run measured', int(ok.sum()), '| next within 7-120 days', int((ok & U.gap_next.between(7, 120)).sum()))
