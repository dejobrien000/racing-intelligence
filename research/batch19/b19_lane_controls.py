"""Batch 19 A4: does extra ground or tempo explain the lane-bias relationship? (research only; no prices; no release).
Same lane help as Batch 18 (the meeting's lane effect from the OTHER races at the meeting x the horse's own straight lane relative to its
race). Added measurements, all from tracking: extra ground = ground covered relative to the race (Qld: starter ground_m; SA: ground relative
to the winner), both centred within race; tempo = the race's early speed relative to its last 600 m (mean over runners of segment average
speeds), standardised within course x distance band, and its interaction with early position (on-pace horses gain in slowly run races).
Tests: (1) this run's surprise on help with barrier + early position (Batch 18), then + extra ground, then + early position x tempo;
(2) the help re-estimated from other races AFTER removing ground and pace-position effects; (3) next-run reversal with the same controls.
Usage (from research/): python3 batch19/b19_lane_controls.py -> batch19/out_b19_lane_controls.json"""
import json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
con = duckdb.connect('../history/history.duckdb', read_only=True)
def tempo_from(SEC, R):
    S = SEC.merge(R[['rid', 'distance_m']], on='rid'); S = S[S.avg_speed_ms.notna()]
    e = S[S.segment_end_m <= S.distance_m - 600].groupby('rid').avg_speed_ms.mean(); l = S[S.segment_end_m > S.distance_m - 600].groupby('rid').avg_speed_ms.mean()
    return (e / l).rename('tempo_raw')
# ---------- Queensland ----------
src = open('batch17/b17_track_bias.py').read(); src = src[:src.index("OUT = {'coverage'")]; exec(src)       # X (Qld tracked runs, lane, early_pos, barrier_rel ...)
G = con.execute("select s.race_id, s.saddlecloth, sum(s.ground_m) as ground_m from sectional s group by 1, 2").fetchdf()   # ground covered = sum of segment ground (the starter total has data errors)
X = X.merge(G, on=['race_id', 'saddlecloth'], how='left', suffixes=('', '_g'))
SECq = con.execute("select race_id as rid, saddlecloth, segment_end_m, avg_speed_ms from sectional").fetchdf(); Rq = R.rename(columns={'race_id': 'rid'})
X = X.join(tempo_from(SECq, Rq), on='race_id'); X['rid'] = X.race_id; X['ground'] = X.ground_m.where((X.ground_m - X.distance_m).abs() <= 200)
F2 = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'q_race_id', 'q_horse_id', 'dyn_nat_inn']).sort_values(['horse', 'date', 'race'])
F2['nxt'] = F2.groupby('horse').dyn_nat_inn.shift(-1); F2 = F2.dropna(subset=['q_race_id']); F2['q_horse_id'] = F2.q_horse_id.astype(str)
X = X.merge(F2[['q_race_id', 'q_horse_id', 'nxt', 'horse']], on=['q_race_id', 'q_horse_id'], how='left'); X['course'] = X.track
Q = X[['rid', 'meeting', 'course', 'distance_m', 'dyn_nat_inn', 'lane', 'barrier_rel', 'early_rel', 'ground', 'tempo_raw', 'nxt', 'horse']].assign(state='QLD')
# ---------- South Australia ----------
Ra = con.execute("select r.race_id as rid, r.track, r.meeting_date, r.race_no, r.distance_m from sa_race r join sa_race_checks c using(race_id) where c.pass").fetchdf()
Sa = con.execute("select race_id as rid, saddlecloth, name_key, barrier, ground_rel_winner_m from sa_starter where not coalesce(scratched, false)").fetchdf()
SECa = con.execute("select race_id as rid, saddlecloth, segment_end_m, position, dist_to_rail_m, avg_speed_ms from sa_sectional").fetchdf()
first = SECa.loc[SECa.groupby('rid').segment_end_m.transform('min') == SECa.segment_end_m].set_index(['rid', 'saddlecloth']).position
last4 = SECa.merge(Ra[['rid', 'distance_m']], on='rid'); last4 = last4[last4.segment_end_m > last4.distance_m - 400].groupby(['rid', 'saddlecloth']).dist_to_rail_m.mean()
A = Sa.merge(Ra, on='rid'); A['race'] = 'SA|' + A.track.str.lower().str.replace('_', '-') + '|' + pd.to_datetime(A.meeting_date).dt.strftime('%Y-%m-%d') + '|' + A.race_no.astype(str)
Fn = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date', 'dyn_nat_inn', 'field', 'state']).sort_values(['horse', 'date', 'race'])
Fn['nxt'] = Fn.groupby('horse').dyn_nat_inn.shift(-1); A = A.merge(Fn[Fn.state == 'SA'], left_on=['race', 'name_key'], right_on=['race', 'horse'])
A['early_pos'] = [first.get(k, np.nan) for k in zip(A.rid, A.saddlecloth)]; A['lane'] = [last4.get(k, np.nan) for k in zip(A.rid, A.saddlecloth)]
A['barrier_rel'] = (A.barrier.astype(float) - 1) / (A.field - 1); A['early_rel'] = (A.early_pos - 1) / (A.field - 1); A['ground'] = A.ground_rel_winner_m
A = A.join(tempo_from(SECa[['rid', 'saddlecloth', 'segment_end_m', 'avg_speed_ms']], Ra), on='rid'); A['meeting'] = A.track + '|' + A.meeting_date.astype(str); A['course'] = A.track
A = A[(A.field >= 6)]
Sx = A[['rid', 'meeting', 'course', 'distance_m', 'dyn_nat_inn', 'lane', 'barrier_rel', 'early_rel', 'ground', 'tempo_raw', 'nxt', 'horse']].assign(state='SA')
def analyse(Z):
    Z = Z.copy()
    for c in ['distance_m', 'dyn_nat_inn', 'lane', 'barrier_rel', 'early_rel', 'ground', 'tempo_raw', 'nxt']: Z[c] = pd.to_numeric(Z[c], errors='coerce').astype(float)
    Z = Z.dropna(subset=['dyn_nat_inn', 'barrier_rel']).copy()
    for c in ['barrier_rel', 'early_rel', 'lane', 'ground']: Z[c + '_w'] = Z[c] - Z.groupby('rid')[c].transform('mean')
    Z['y_w'] = Z.dyn_nat_inn - Z.groupby('rid').dyn_nat_inn.transform('mean')
    Z['dband'] = pd.cut(Z.distance_m, [0, 1100, 1300, 1500, 1800, 9999]).astype(str)
    Z['tempo_z'] = (Z.tempo_raw - Z.groupby(['course', 'dband']).tempo_raw.transform('mean')) / Z.groupby(['course', 'dband']).tempo_raw.transform('std')
    Z['pace_x'] = Z.early_rel_w * Z.tempo_z.fillna(0)
    def help_from(yc):
        Z['lxy'] = (Z.lane_w * Z[yc]).fillna(0); Z['lxx'] = (Z.lane_w ** 2).fillna(0)
        m = Z.groupby('meeting')[['lxy', 'lxx']].transform('sum'); r = Z.groupby('rid')[['lxy', 'lxx']].transform('sum')
        return ((m.lxy - r.lxy) / (m.lxx - r.lxx).replace(0, np.nan)) * Z.lane_w
    Z['help'] = help_from('y_w')
    ok = Z.ground_w.notna() & Z.early_rel_w.notna(); adj = smf.ols('y_w ~ ground_w + early_rel_w + pace_x - 1', Z[ok]).fit()
    Z['y_adj'] = Z.y_w; Z.loc[ok, 'y_adj'] = Z.loc[ok, 'y_w'] - adj.predict(Z[ok]); Z['help2'] = help_from('y_adj')
    d = Z[np.isfinite(Z.help) & ok].copy()
    for c in ['help', 'help2']: d[c] = d[c].clip(d[c].quantile(0.01), d[c].quantile(0.99))
    cl = lambda f, dd, g: smf.ols(f, dd).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(dd[g])[0]})
    ci = lambda mm, k: [round(float(mm.params[k]), 3), round(float(mm.conf_int().loc[k, 0]), 3), round(float(mm.conf_int().loc[k, 1]), 3)]
    o = {'runs': int(len(d)), 'meetings': int(d.meeting.nunique()), 'ground_coverage': round(float(Z.ground.notna().mean()), 3), 'tempo_coverage': round(float(Z.tempo_raw.notna().mean()), 3),
         'ground_and_pace_effects_kg': {k: ci(adj, k) for k in ['ground_w', 'early_rel_w', 'pace_x']},
         'this_run': {'barrier + early (Batch 18)': ci(cl('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w', d, 'meeting'), 'help'),
                      '+ extra ground': ci(cl('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w + ground_w', d, 'meeting'), 'help'),
                      '+ extra ground + early position x tempo': ci(cl('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w + ground_w + pace_x', d, 'meeting'), 'help'),
                      'help re-estimated after removing ground and pace effects (all controls)': ci(cl('dyn_nat_inn ~ help2 + barrier_rel_w + early_rel_w + ground_w + pace_x', d, 'meeting'), 'help2')},
         'corr_help_with_help_adjusted': round(float(d[['help', 'help2']].corr().iloc[0, 1]), 3)}
    dn = d.dropna(subset=['nxt'])
    o['next_run'] = {'help (Batch 18)': ci(cl('nxt ~ help + dyn_nat_inn', dn, 'horse'), 'help'), 'help adjusted, with ground and pace in the run': ci(cl('nxt ~ help2 + dyn_nat_inn + ground_w + pace_x', dn, 'horse'), 'help2')}
    return o
OUT = {'QLD': analyse(Q), 'SA': analyse(Sx)}
json.dump(OUT, open('batch19/out_b19_lane_controls.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
