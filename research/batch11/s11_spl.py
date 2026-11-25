"""Batch 11 s7: seconds per official length, from Queensland tracked individual finish times."""
import duckdb, numpy as np, pandas as pd
c = duckdb.connect('/tmp/natq/history2/history.duckdb', read_only=True)
s = c.execute("""select s.race_id, s.meeting_date, s.track, s.saddlecloth, s.finish_pos fp, s.margin_l m, s.finish_time_s t, r.distance_m d, r.track_rating_tracking going, r.race_time_s rt
  from starter s join race r using (race_id) where s.result_state='Finished' and s.finish_time_s is not null and s.margin_l is not null""").fetchdf()
last = c.execute("""select race_id, saddlecloth, avg_speed_ms v from (select *, row_number() over (partition by race_id, saddlecloth order by segment_end_m desc) k from sectional) where k=1""").fetchdf()
s = s.merge(last, on=['race_id', 'saddlecloth'], how='left')
w = s[s.fp == 1].groupby('race_id').agg(tw=('t', 'min'), vw=('v', 'mean')); s = s.join(w, on='race_id')
s['dt'] = s.t - s.tw; y = s[(s.fp > 1) & (s.m >= 0.5) & (s.m <= 12) & s.dt.notna()].copy(); y['spl'] = y.dt / y.m
y['yr'] = pd.to_datetime(y.meeting_date).dt.year; y['dband'] = pd.cut(y.d, [0, 1100, 1300, 1600, 2000, 4000], labels=['<=1100', '1101-1300', '1301-1600', '1601-2000', '2000+'])
y['g'] = y.going.astype(str).str[:1].map({'F': 'Firm', 'G': 'Good', 'S': 'Soft', 'H': 'Heavy'}).fillna('other')
y['spd'] = y.d / y.rt; y['sband'] = pd.qcut(y.spd, 4, labels=['slowest quarter', 'q2', 'q3', 'fastest quarter'])
y['mband'] = pd.cut(y.m, [0, 1, 2, 4, 7, 12], labels=['0.5-1L', '1-2L', '2-4L', '4-7L', '7-12L'])
out = []
for k in ['yr', 'dband', 'g', 'sband', 'mband']:
    for v, g in y.groupby(k, observed=True): out.append({'by': k, 'group': str(v), 'runners': len(g), 'median_s_per_L': round(g.spl.median(), 4), 'p10': round(g.spl.quantile(.1), 4), 'p90': round(g.spl.quantile(.9), 4), 'implied_m_per_L_at_finish_speed': round((g.spl * g.vw).median(), 2)})
O = pd.DataFrame(out); print(O.to_string(index=False)); O.to_csv('b11/out_spl.csv', index=False)
print('overall', round(y.spl.median(), 4), 'n', len(y), '| engine assumption 2.4m/avg speed median', round((2.4 / y.spd).median(), 4))
# chronological check: fit s/L on 2023-24, check 2025-26 time-gap prediction error vs engine rule
tr = y[y.yr <= 2024]; te = y[y.yr >= 2025]; k = tr.spl.median()
for nm, pred in [('fixed median from 2023-24 (%.4f s/L)' % k, te.m * k), ('engine rule 2.4m / race speed', te.m * 2.4 / te.spd), ('ChatGPT 0.167 s/L', te.m * 0.167)]:
    e = te.dt - pred; print(f'{nm}: mean error {e.mean():+.3f}s, median abs error {e.abs().median():.3f}s, n {len(te)}')
print('raceday share where every runner sits within 0.002 s/L of the race median:', round(float(y.groupby('race_id').spl.apply(lambda v: (v - v.median()).abs().max() < 0.002).mean()), 3))
