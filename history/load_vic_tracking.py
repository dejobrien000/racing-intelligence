"""Victorian TripleS sectionals -> master-database tracking tables in the common tracking shape used for Queensland and SA
(approved by Damo 26 Nov 2026, foundation step 4; loaded at the weekly update). Source: the staged package
(research/staging/vic_triples, built by history/stage_vic_triples.py from the original ZIP; originals on branch raw-vic-triples).

Measured vs derived is kept explicit. Measured (from the files): each section's time, the speed AT each mark. Derived from those
measurements and labelled so: cumulative time, section average speed (length / time), position by cumulative time at each mark,
finish time (sum of a complete run's sections). NOT in these files and left NULL (never estimated): ground covered, top speed,
stride frequency and length, distance from the rail. Track configuration comes from the matching Breednet meeting (same horses,
same date), which keeps turf and synthetic courses and course variants apart; where Breednet does not have the meeting yet,
the meeting label's venue is kept and marked 'label only'.

Nothing is discarded: runners without a complete run stay in vic_starter with tracking_status and quarantine_reason, and their
sections (all zero) are not written as measurements. The Flemington 3 Oct 2026 racing.com speed pilot's extra measurements
(distance run, early/mid/late/peak speed, positions at each mark) are kept in vic_pilot_runner / vic_pilot_point.
Usage: python3 history/load_vic_tracking.py <history.duckdb> <staging dir>"""
import sys, os, re, duckdb, pandas as pd, numpy as np
DB, ST = sys.argv[1], sys.argv[2]
con = duckdb.connect(DB)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', str(s).upper()))
R = pd.read_csv(os.path.join(ST, 'races.csv'), dtype={'race_id': str, 'meeting_id': str})
U = pd.read_csv(os.path.join(ST, 'runners.csv'), dtype={'saddlecloth': str, 'meeting_id': str})
S = pd.read_csv(os.path.join(ST, 'sections.csv.gz'), dtype={'saddlecloth': str, 'meeting_id': str})
V = pd.read_csv(os.path.join(ST, 'validation.csv'))
Q = pd.read_csv(os.path.join(ST, 'quarantine_runners.csv'), dtype={'saddlecloth': str}) if os.path.exists(os.path.join(ST, 'quarantine_runners.csv')) else pd.DataFrame()
# track configuration from Breednet: the meeting slug most of the race's horses ran at on that date
bn = con.execute("""select cast(u.meeting_date as varchar) d, regexp_replace(upper(u.name_key), '[^A-Z0-9]', '', 'g') k, u.slug, u.race_no bn_race_no, u.finish_pos, u.margin_l
                    from bn_runner u join bn_meeting m using (meeting_date, slug) where m.state = 'VIC'""").fetchdf()
U['k'] = U.horse.map(nk); m = U.merge(bn, left_on=['race_date', 'k'], right_on=['d', 'k'], how='left')
cfg = m.dropna(subset=['slug']).groupby('file').slug.agg(lambda s: s.value_counts().index[0])
lab = R.set_index('file').meeting_label.str.replace(r'-Professional-\d{4}-\d{2}-\d{2}$', '', regex=True).str.replace(r'^(Sportsbet|Ladbrokes|bet365|TAB|Neds)[- ]', '', regex=True)
R['track_config'] = R.file.map(cfg); R['config_source'] = np.where(R.track_config.notna(), 'Breednet meeting (same horses, same date)', 'label only')
R['track_config'] = R.track_config.fillna(R.file.map(lab).str.lower().str.replace(r'[^a-z0-9]+', '-', regex=True))
R['vic_race_id'] = 'VIC-' + R.race_date + '-' + R.track_config + '-R' + R.race_no.astype(str)
rid = R.set_index('file').vic_race_id
VR = R.merge(V[['file', 'status', 'dead_heat', 'fastest_is_winner', 'bf_winner']].rename(columns={'status': 'validation_status'}), on='file', how='left')
VR = VR[['vic_race_id', 'race_date', 'track_config', 'config_source', 'race_no', 'race_name', 'distance_m', 'course_code', 'first_section_m', 'sections', 'runners',
         'tracked_runners', 'meeting_id', 'race_id', 'meeting_label', 'validation_status', 'dead_heat', 'fastest_is_winner', 'bf_winner', 'package_flag', 'file', 'sha256', 'source_url']]
VR = VR.rename(columns={'meeting_id': 'rc_meeting_id', 'race_id': 'rc_race_id', 'bf_winner': 'official_winner_check'}).assign(source='TripleS CSV (external weekly Racing.com session, supplied by Damo)')
# starters
m1 = m.drop_duplicates(['file', 'saddlecloth'])
qr = Q.set_index(['file', 'saddlecloth']).quarantine_reason if len(Q) else pd.Series(dtype=str)
VS = pd.DataFrame({'vic_race_id': m1.file.map(rid), 'saddlecloth': m1.saddlecloth, 'name': m1.horse, 'name_key': m1.k, 'row_order': m1.row_order,
                   'tracking_status': m1.tracking_status, 'finish_time_s_derived': np.where(m1.complete == 1, m1.total_time_s, np.nan),
                   'bn_finish_pos': m1.finish_pos, 'bn_margin_l': m1.margin_l,
                   'quarantine_reason': [qr.get((f, c)) for f, c in zip(m1.file, m1.saddlecloth)]})
# sections: measured section time and speed at the mark; derived cumulative time, average speed and position. Zero sections are not measurements.
S = S[S.section_time_s.notna() & (S.section_time_s > 0)].copy()
S['vic_race_id'] = S.file.map(rid)
S['position_by_time_derived'] = S.groupby(['file', 'section_no']).cum_time_s.rank(method='min')
VX = pd.DataFrame({'vic_race_id': S.vic_race_id, 'saddlecloth': S.saddlecloth, 'segment_end_m': S.section_end_m, 'seg_len_m': S.section_len_m,
                   'split_s': S.section_time_s, 'inter_s_derived': S.cum_time_s, 'speed_at_mark_ms': S.speed_ms_file, 'avg_speed_ms_derived': S.speed_ms_derived,
                   'position_by_time_derived': S.position_by_time_derived, 'ground_m': np.nan, 'top_speed_ms': np.nan, 'stride_freq_hz': np.nan, 'stride_len_m': np.nan,
                   'dist_to_rail_m': np.nan})
# racing.com Flemington pilot (3 Oct 2026): extras the CSVs lack
pilot_r = con.execute("select * from vic_speed_runner").fetchdf() if 'vic_speed_runner' in [t[0] for t in con.execute('show tables').fetchall()] else pd.DataFrame()
pilot_p = con.execute("select * from vic_speed_point").fetchdf() if len(pilot_r) else pd.DataFrame()
if len(pilot_r):
    fl = R[(R.race_date == '2026-10-03') & (R.meeting_id.astype(str) == str(pilot_r.meet_code.iloc[0]))].set_index('race_no').vic_race_id
    pilot_r['vic_race_id'] = pilot_r.race_no.map(fl); pilot_p['vic_race_id'] = pilot_p.race_no.map(fl)
    pilot_r = pilot_r.assign(source='racing.com speed pilot (Flemington 3 Oct 2026), archived original table vic_speed_runner')
for name, df in [('vic_race', VR), ('vic_starter', VS), ('vic_sectional', VX), ('vic_pilot_runner', pilot_r), ('vic_pilot_point', pilot_p)]:
    if not len(df): continue
    con.register('d_', df); con.execute(f'create or replace table {name} as select * from d_'); con.unregister('d_')
print(f"vic tracking: races {len(VR)} ({(VR.config_source != 'label only').sum()} configured from Breednet) | configurations {VR.track_config.nunique()} | starters {len(VS)} "
      f"(complete {int((VS.tracking_status == 'complete').sum())}, kept with reasons {int(VS.quarantine_reason.notna().sum())}) | measured sections {len(VX)} | pilot runners {len(pilot_r)}")
print('configurations:', VR.groupby('track_config').size().to_dict())
