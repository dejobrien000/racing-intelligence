"""Batch 11 s10: Victorian horses in Tasmania (and other moves): who, where, when, how often, against what. Engine v2 chance (dev-fit, before calibration)."""
import sys, numpy as np, pandas as pd, duckdb
sys.path.insert(0, 'b11'); from s11_common import base_p, ae
b = base_p(); U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'date', 'state', 'venue', 'prev_state', 'race_no', 'distance_m', 'class_label', 'tkey', 'dyn_nat', 'field'])
U = U.sort_values(['horse', 'date']); U['first_in_state'] = (U.groupby(['horse', 'state']).cumcount() == 0)
x = b.merge(U.drop(columns=[c for c in ['state', 'venue', 'date', 'dyn_nat', 'field', 'distance_m', 'race_no', 'class_label', 'tkey', 'prev_state'] if c in b.columns]), on=['race_id', 'horse'], how='left')
con = duckdb.connect('../history/history.duckdb', read_only=True)
T = con.execute("select r.meeting_date date, m.bf_track_slug venue, r.race_no, r.title from bn_race r join bn_meeting m using (meeting_date, slug)").fetchdf(); T['date'] = pd.to_datetime(T.date)
x = x.merge(T.rename(columns={'date': 'meeting_date'}), on=['meeting_date', 'venue', 'race_no'], how='left')
x['fq'] = x.groupby('race_id').dyn_nat.transform('mean'); x['month'] = x.meeting_date.dt.month
x['cup'] = x.title.fillna('').str.contains(r'\bCup\b', case=False); x['carnival'] = x.month.isin([1, 2])
x['rank'] = x.groupby('race_id').v2.rank(ascending=False, method='first')
vt = x[(x.prev_state == 'VIC') & (x.state == 'TAS')].copy()
rows = [('ALL Vic->Tas', ae(vt, 'horse'))]
for nm, m in [('Jan-Feb (summer carnival)', vt.carnival), ('Mar-Dec', ~vt.carnival), ('Cup races', vt.cup), ('not Cup races', ~vt.cup),
              ('first Tas start', vt.first_in_state), ('repeat Tas start', ~vt.first_in_state.astype(bool)), ('Launceston', vt.venue == 'launceston'), ('Hobart', vt.venue == 'hobart'), ('Devonport', vt.venue == 'devonport'),
              ('engine top pick', vt['rank'] == 1), ('engine ranked 2-4', vt['rank'].between(2, 4)), ('engine ranked 5+', vt['rank'] >= 5),
              ('sprint <=1200', vt.distance_m <= 1200), ('1201-1600', vt.distance_m.between(1201, 1600)), ('1601+', vt.distance_m > 1600),
              ('Maiden', vt.class_label == 'Maiden'), ('Benchmark', vt.class_label == 'Benchmark'), ('Class/Restricted/Other', vt.class_label.isin(['Class', 'Restricted', 'Other'])), ('Open/Listed/Group', vt.class_label.isin(['Open', 'Listed', 'Group'])),
              ('Vic rating above Tas field avg by 3kg+', (vt.dyn_nat - vt.fq) >= 3), ('within 3kg of field', (vt.dyn_nat - vt.fq).abs() < 3), ('below field by 3kg+', (vt.dyn_nat - vt.fq) <= -3),
              ('2023-24', vt.meeting_date.dt.year <= 2024), ('2025-26', vt.meeting_date.dt.year >= 2025)]:
    rows.append((nm, ae(vt[m.fillna(False).values], 'horse')))
R = pd.DataFrame([{'group': k, **v} for k, v in rows]); print(R.to_string(index=False)); R.to_csv('b11/out_vic_tas.csv', index=False)
print('unique horses', vt.horse.nunique(), '| trainers', vt.tkey.nunique(), '| starts', len(vt), '| starts per horse (max)', vt.groupby('horse').size().max())
top = vt.groupby('horse').agg(starts=('win', 'size'), wins=('win', 'sum'), expected=('p', 'sum')).sort_values('wins', ascending=False).head(10); print(top.round(2).to_string())
tt = vt.groupby('tkey').agg(starts=('win', 'size'), wins=('win', 'sum'), expected=('p', 'sum')).sort_values('wins', ascending=False).head(8); print(tt.round(2).to_string())
wo = vt.groupby('horse').agg(w=('win', 'sum'), e=('p', 'sum')); top3 = wo.w.sort_values(ascending=False).index[:3]
print('ratio without the 3 biggest-winning horses:', ae(vt[~vt.horse.isin(top3)], 'horse'))
# other moves, horse-clustered
oth = []
for a, c in [('VIC', 'SA'), ('SA', 'VIC'), ('TAS', 'VIC'), ('NSW', 'VIC'), ('VIC', 'NSW'), ('QLD', 'NSW'), ('NSW', 'QLD'), ('VIC', 'WA'), ('ACT', 'NSW'), ('NSW', 'ACT')]:
    g = x[(x.prev_state == a) & (x.state == c)]
    if len(g) > 100: oth.append({'move': f'{a}->{c}', **ae(g, 'horse')})
O = pd.DataFrame(oth); print(O.to_string(index=False)); O.to_csv('b11/out_moves.csv', index=False)
