"""Batch 11 s3: three real races traced through the database (records held, margins, weights, times, sectionals, what feeds the rating)."""
import duckdb, numpy as np, pandas as pd
c = duckdb.connect('../history/history.duckdb', read_only=True)
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'venue', 'state', 'race_no', 'distance_m', 'race_time_s', 'going', 'finish_pos', 'margin_l', 'weight_kg', 'barrier',
                                                              'field', 'run_time', 'speed', 'kgpl', 'fig_w', 'fig_n', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'q_race_id', 'jkey', 'tkey'])
U['date'] = pd.to_datetime(U.date); U = U.sort_values(['horse', 'date']); U['runs_held_before'] = U.groupby('horse').cumcount(); U['first_held'] = U.groupby('horse').date.transform('min')
def show(state, date, venue, race_no, label):
    r = U[(U.state == state) & (U.date == date) & (U.venue == venue) & (U.race_no == race_no)].sort_values('finish_pos').copy()
    print(f'\n===== {label}: {venue} {date} R{race_no} | {r.distance_m.iloc[0]}m | going {r.going.iloc[0]} | winner time {r.race_time_s.iloc[0]}s | records in rating frame {len(r)} | field col {r.field.iloc[0]}')
    r['spl_used'] = 2.4 / r.speed; r['est_time'] = r.race_time_s + r.margin_l.clip(upper=30) * r.spl_used
    cols = ['finish_pos', 'horse', 'barrier', 'weight_kg', 'margin_l', 'est_time', 'spl_used', 'fig_n', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'runs_held_before', 'first_held']
    return r[cols]
pd.set_option('display.width', 250)
# Queensland tracked race: individual times and sectionals measured
q = show('QLD', '2026-11-22', U[(U.state == 'QLD') & (U.date == '2026-11-22')].venue.value_counts().index[0], 3, 'QUEENSLAND (tracked)')
print(q.round(3).to_string(index=False))
qid = U[(U.state == 'QLD') & (U.date == '2026-11-22') & (U.venue == U[(U.state == 'QLD') & (U.date == '2026-11-22')].venue.value_counts().index[0]) & (U.race_no == 3)].q_race_id.dropna().iloc[0]
s = c.execute(f"select s.finish_pos, s.name, s.margin_l, s.finish_time_s, s.weight_kg alloc_kg, s.barrier from starter s where race_id='{qid}' order by s.finish_pos nulls last").fetchdf()
l6 = c.execute(f"select saddlecloth, sum(split_s) l600 from sectional where race_id='{qid}' and segment_end_m >= (select max(segment_end_m) from sectional where race_id='{qid}') - 600 + 1 group by 1").fetchdf()
s2 = c.execute(f"select s.name, s.saddlecloth from starter s where race_id='{qid}'").fetchdf().merge(l6, on='saddlecloth', how='left')
print('RQ starter table (official):'); print(s.merge(s2[['name', 'l600']], on='name', how='left').to_string(index=False))
print('RQ sectional rows for this race:', c.execute(f"select count(*), count(distinct saddlecloth), min(segment_end_m), max(segment_end_m) from sectional where race_id='{qid}'").fetchall())
# Victoria
v = show('VIC', '2026-11-21', 'cranbourne', 5, 'VICTORIA (Breednet results)'); print(v.round(3).to_string(index=False))
print('Breednet race row:', c.execute("select race_no, distance_m, race_time_s, last600_s, going, class from bn_race where meeting_date='2026-11-21' and slug='cranbourne' and race_no=5").fetchall())
print('Breednet runner rows (incl. unplaced/scratched):', c.execute("select count(*), count(finish_pos), count(margin_l) from bn_runner where meeting_date='2026-11-21' and slug='cranbourne' and race_no=5").fetchall(), '| Vic tracking speeds held for this race:', c.execute("select count(*) from vic_speed_runner where meeting_date='2026-11-21' and slug='cranbourne' and race_no=5").fetchall())
# SA
a = show('SA', '2026-11-21', 'morphettville', 7, 'SOUTH AUSTRALIA (Breednet results)'); print(a.round(3).to_string(index=False))
print('Breednet race row:', c.execute("select race_no, distance_m, race_time_s, last600_s, going, class from bn_race where meeting_date='2026-11-21' and slug='morphettville' and race_no=7").fetchall())
print('Breednet runner rows:', c.execute("select count(*), count(finish_pos), count(margin_l) from bn_runner where meeting_date='2026-11-21' and slug='morphettville' and race_no=7").fetchall())
