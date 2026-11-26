"""Batch 14 follow-up s9: Pride Of Jenni, full measured sectional profiles. Doomben Cup 2000 m, 24 May 2025 and 23 May 2026 (Qld tracking:
200 m segments from the start, split time, average and top speed, stride length and frequency, distance from the rail, position), and
Caulfield 27 Sep 2026 R5 1600 m (Victorian sections from the user-supplied TripleS files, 100 m/200 m sections, times and speeds only).
Measured values are reported as measured; derived values (speed = 200 m / split, lengths at 0.17 s per length is NOT used - lengths are
computed from the race's own average speed and a 2.4 m length) are labelled. No inference about why speed changed."""
import duckdb, numpy as np, pandas as pd, json
con = duckdb.connect('/home/claude/racing-intelligence/history/history.duckdb', read_only=True)
NAT = pd.read_parquet('engine/frames/national_v3.parquet', columns=['race_id', 'q_race_id', 'horse', 'venue', 'date', 'distance_m', 'dyn_nat', 'fig_w', 'going', 'finish_pos', 'field', 'margin_l', 'class_label'])
OUT = {}; L = 2.4
S = pd.read_csv('staging/stewards/stewards_events.csv.gz', low_memory=False)
def nat_rows(qid):
    r = NAT[NAT.q_race_id == qid].copy(); return r
for qid in ['20250524-Doomben-R8', '20260523-Doomben-R8']:
    race = con.execute('select * from race where race_id=?', [qid]).df().iloc[0]
    st = con.execute("select saddlecloth, name, name_key, finish_pos, margin_l, finish_time_s, ground_m, barrier, weight_kg, jockey, trainer from starter where race_id=? and coalesce(scratched,false)=false", [qid]).df()
    se = con.execute('select * from sectional where race_id=? order by saddlecloth, segment_end_m', [qid]).df()
    se = se.merge(st[['saddlecloth', 'name_key', 'finish_pos']], on='saddlecloth')
    se['seg'] = se.segment_end_m.astype(int); se['speed'] = 200 / se.split_s   # race-distance speed (derived); avg_speed_ms is the device's measured speed over the ground actually covered
    se['cum'] = se.groupby('saddlecloth').split_s.cumsum()
    lead = se.groupby('seg').cum.min().rename('lead_cum'); se = se.merge(lead, on='seg'); se['behind_leader_s'] = (se.cum - se.lead_cum).round(2)
    se['second_cum'] = se.groupby('seg').cum.transform(lambda x: np.sort(x.values)[1])
    med = se.groupby('seg')[['speed', 'stride_len_m', 'stride_freq_hz', 'dist_to_rail_m']].median().add_prefix('field_med_')
    se = se.merge(med, on='seg')
    me = se[se.name_key.str.upper().str.contains('PRIDE OF JENNI')].copy()
    win = se[se.finish_pos == 1].copy(); wname = st.loc[st.finish_pos == 1, 'name'].iloc[0]
    me = me.merge(win[['seg', 'speed', 'cum']].rename(columns={'speed': 'win_speed', 'cum': 'win_cum'}), on='seg')
    rk = se.assign(rk=se.groupby('seg').speed.rank(ascending=False, method='min')); me['speed_rank'] = me.seg.map(rk[rk.name_key.str.upper().str.contains('PRIDE OF JENNI')].set_index('seg').rk)
    me['lead_over_next_s'] = np.where(me.behind_leader_s == 0, (me.second_cum - me.cum).round(2), np.nan)
    me['vs_field_ms'] = (me.speed - me.field_med_speed).round(2); me['vs_winner_ms'] = (me.speed - me.win_speed).round(2)
    me['vs_field_lengths'] = ((200 / me.field_med_speed - me.split_s) * me.speed / L).round(2)   # derived: + = lengths gained on a median-speed runner in the segment
    me['ahead_of_winner_s'] = (me.win_cum - me.cum).round(2)
    me['to_go_m'] = int(race.distance_m) - me.seg
    tab = me[['seg', 'to_go_m', 'split_s', 'speed', 'avg_speed_ms', 'top_speed_ms', 'field_med_speed', 'win_speed', 'vs_field_ms', 'vs_field_lengths', 'speed_rank', 'position', 'behind_leader_s', 'lead_over_next_s',
              'ahead_of_winner_s', 'stride_len_m', 'field_med_stride_len_m', 'stride_freq_hz', 'field_med_stride_freq_hz', 'dist_to_rail_m', 'field_med_dist_to_rail_m']].round(3)
    tab.to_csv(f'batch14/followup/poj_{qid}.csv', index=False)
    n = nat_rows(qid); her = n[n.horse.astype(str).str.upper().str.replace(' ', '').str.contains('PRIDEOFJENNI')]
    me_st = st[st.name_key.str.upper().str.contains('PRIDE OF JENNI')].iloc[0]
    half = int(race.distance_m) // 2
    def halves(rows): a = rows[rows.seg <= half].split_s.sum(); b = rows[rows.seg > half].split_s.sum(); return round(a, 2), round(b, 2)
    OUT[qid] = {'race': race.race_name, 'going': race.track_rating_tracking, 'rail': race.rail, 'race_time_s': float(race.race_time_s), 'runners': len(st),
        'her': {'finish': int(me_st.finish_pos), 'margin_L': float(me_st.margin_l), 'barrier': int(me_st.barrier), 'weight_kg': float(me_st.weight_kg), 'jockey': me_st.jockey,
                'ground_covered_m (measured)': float(me_st.ground_m), 'field median ground_m': float(st.ground_m.median()), 'winner ground_m': float(st.loc[st.finish_pos == 1, 'ground_m'].iloc[0]),
                'pre-race rating (kg)': round(float(her.dyn_nat.iloc[0]), 2) if len(her) else None, 'time figure this run (fig_w: kg scale, 100 = par for course and distance after the day variant and weight credit)': round(float(her.fig_w.iloc[0]), 2) if len(her) and pd.notna(her.fig_w.iloc[0]) else None,
                'first half / second half (s)': halves(me), 'stride: mean length m, mean frequency Hz': (round(me.stride_len_m.mean(), 2), round(me.stride_freq_hz.mean(), 2))},
        'times': {'her finishing time (winner time + her deficit, s)': round(float(race.race_time_s) + float(me.behind_leader_s.iloc[-1]), 2)},
        'winner': {'name': wname, 'pre-race rating (kg)': round(float(n[n.finish_pos == 1].dyn_nat.iloc[0]), 2) if (n.finish_pos == 1).any() else None, 'first half / second half (s)': halves(se[se.finish_pos == 1]), 'ground_m': float(st.loc[st.finish_pos == 1, 'ground_m'].iloc[0])},
        'field': {'pre-race ratings (kg) sorted': sorted([round(float(v), 1) for v in n.dyn_nat.dropna()], reverse=True), 'her rating rank': int((n.dyn_nat > (her.dyn_nat.iloc[0] if len(her) else 99)).sum() + 1) if len(her) else None,
                  'field mean rating': round(float(n.dyn_nat.mean()), 2), 'class': n.class_label.iloc[0] if len(n) else None,
                  'median first half / second half (s)': (round(float(se[se.seg <= half].groupby('saddlecloth').split_s.sum().median()), 2), round(float(se[se.seg > half].groupby('saddlecloth').split_s.sum().median()), 2))},
        'stewards (QRIC report text, as published; reported, not observed)': S[(S.date == str(race.meeting_date)[:10]) & (S.race_no == int(race.race_no)) & (S.venue_text.astype(str) == 'doom')][['horse', 'role', 'text']].to_dict('records'),
        'table': tab.to_dict('records')}
# tempo from the b14 tracked-run table
R = pd.read_parquet('/home/claude/b14/runs_QLD.parquet', columns=['race_id', 'name_key', 'tempo_z'])
for qid in OUT: OUT[qid]['tempo_z (leader speed to 600 m out, standardised for course and distance)'] = round(float(R[R.race_id == qid].tempo_z.iloc[0]), 2)
# Caulfield (Victorian sections; times and speeds only)
S = pd.read_csv('staging/vic_triples/sections.csv.gz'); c = S[(S.meeting_id == 5195477) & (S.race_no == 5)].copy()
c['cum'] = c.groupby('saddlecloth').section_time_s.cumsum() if 'cum_time_s' not in c else c.cum_time_s
c['seg'] = c.section_end_m.astype(int)
lead = c.groupby('seg').cum_time_s.min().rename('lead_cum'); c = c.merge(lead, on='seg'); c['behind_leader_s'] = (c.cum_time_s - c.lead_cum).round(2)
c['second_cum'] = c.groupby('seg').cum_time_s.transform(lambda x: np.sort(x.values)[1])
c['speed'] = c.section_len_m / c.section_time_s; c['field_med_speed'] = c.groupby('seg').speed.transform('median')
c['speed_rank'] = c.groupby('seg').speed.rank(ascending=False, method='min')
me = c[c.horse.str.upper() == 'PRIDE OF JENNI'].copy(); me['lead_over_next_s'] = np.where(me.behind_leader_s == 0, (me.second_cum - me.cum_time_s).round(2), np.nan)
me['vs_field_ms'] = (me.speed - me.field_med_speed).round(2); me['to_go_m'] = 1600 - me.seg
ct = me[['seg', 'to_go_m', 'section_len_m', 'section_time_s', 'speed', 'field_med_speed', 'vs_field_ms', 'speed_rank', 'behind_leader_s', 'lead_over_next_s']].round(3)
ct.to_csv('batch14/followup/poj_caulfield_20260927_R5.csv', index=False)
n = NAT[NAT.race_id == 'VIC|caulfield|2026-09-27|5']; her = n[n.horse.astype(str).str.upper().str.replace(' ', '').str.contains('PRIDEOFJENNI')]
nr = n[n.race_id == her.race_id.iloc[0]] if len(her) else n.iloc[:0]
def h(rows, d): a = rows[rows.seg <= d // 2].section_time_s.sum(); b = rows[rows.seg > d // 2].section_time_s.sum(); return round(a, 2), round(b, 2)
OUT['Caulfield 2026-09-27 R5 1600 m'] = {'runners': int(c.saddlecloth.nunique()), 'going (national frame)': her.going.iloc[0] if len(her) else None,
    'her': {'finish': int(her.finish_pos.iloc[0]) if len(her) else None, 'pre-race rating (kg)': round(float(her.dyn_nat.iloc[0]), 2) if len(her) else None,
            'time figure (fig_w, kg scale, 100 = par)': round(float(her.fig_w.iloc[0]), 2) if len(her) and pd.notna(her.fig_w.iloc[0]) else None, 'first half / second half (s)': h(me, 1600)},
    'field': {'pre-race ratings (kg) sorted': sorted([round(float(v), 1) for v in nr.dyn_nat.dropna()], reverse=True), 'class': nr.class_label.iloc[0] if len(nr) else None,
              'median first half / second half (s)': (round(float(c[c.seg <= 800].groupby('saddlecloth').section_time_s.sum().median()), 2), round(float(c[c.seg > 800].groupby('saddlecloth').section_time_s.sum().median()), 2))},
    'not held': 'stride, distance from the rail and ground covered are not in the Victorian files', 'table': ct.to_dict('records')}
# her career rating path (national frame)
H = NAT[NAT.horse.astype(str).str.upper().str.replace(' ', '').str.contains('PRIDEOFJENNI')].sort_values('date')
OUT['career (national frame)'] = H[['date', 'venue', 'distance_m', 'going', 'finish_pos', 'field', 'margin_l', 'dyn_nat', 'fig_w']].assign(date=lambda d: d.date.astype(str).str[:10]).round(2).to_dict('records')
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'date', 'venue', 'distance_m', 'dyn_nat', 'dyn_nat_inn', 'finish_pos', 'field'])
V = V[V.horse.astype(str).str.contains('PRIDEOFJENNI')].sort_values('date')
OUT['rating surprise per run (kg: ran better (+) or worse (-) than her pre-race rating said, race-centred; population sd 5.5)'] = V.assign(date=V.date.astype(str).str[:10]).round(2)[['date', 'venue', 'distance_m', 'finish_pos', 'field', 'dyn_nat', 'dyn_nat_inn']].to_dict('records')
OUT['course facts (public track guides, not measured here)'] = {'Doomben': 'circumference 1,715 m, home straight about 350 m, right-handed, tight turns; 2000 m start in the straight = about one full lap',
    'Caulfield': 'circumference 2,080 m, home straight 367 m, left-handed, triangular with long sweeping turns'}
json.dump(OUT, open('batch14/followup/out_poj.json', 'w'), indent=1, default=str)
for k, v in OUT.items():
    if k.startswith('career') or not isinstance(v, dict) or 'table' not in v: continue
    print(k, json.dumps({a: b for a, b in v.items() if a != 'table'}, default=str))
    print(pd.DataFrame(v['table']).to_string(index=False))
print(pd.DataFrame(OUT['career (national frame)']).to_string(index=False))
