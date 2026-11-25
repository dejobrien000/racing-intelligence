"""Batch 10, Queensland tracked races (RQ tracking): running style vs today's opposition (s3), distance x class change by
finishing profile (s4), performance composition under workload (s7). Engine v2 QLD family score held fixed. Pre-race features only."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
R = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'meeting_date', 'settle_rel', 'rel_barrier', 'field', 'distance_m', 'scratched'])
R = R[~R.scratched.fillna(False)].copy(); R['meeting_date'] = pd.to_datetime(R.meeting_date); R = R.sort_values(['horse_id', 'meeting_date']).reset_index(drop=True)
R['sr'] = R.settle_rel.clip(0, 1); g = R.groupby('horse_id')
R['style5'] = g.sr.transform(lambda s: s.shift().rolling(5, min_periods=2).mean())
R['lead_rate5'] = g.sr.transform(lambda s: (s.shift() <= 0.15).astype(float).where(s.shift().notna()).rolling(5, min_periods=2).mean())
R['leader'] = (R.style5 <= 0.2).astype(float).where(R.style5.notna())
grp = R.groupby('race_id')
R['n_other_leaders'] = (grp.leader.transform('sum') - R.leader.fillna(0)).where(R.leader.notna())
R['style_rank_pct'] = grp.style5.rank(method='average', pct=True)                               # 0 = the most forward-running horse in today's field
R['ahead_gap'] = R.style5 - (grp.style5.transform(lambda s: s.nsmallest(2).iloc[-1] if s.notna().sum() >= 2 else np.nan))   # how far behind the 2nd most forward
R['prev_sr'] = g.sr.shift(); R['prev_style'] = g.style5.shift()
R['disrupted_last'] = (R.prev_sr - R.prev_style).where(R.prev_style.notna())                      # + = settled further back than usual last start
N = pd.read_parquet('engine/frames/national.parquet', columns=['q_race_id', 'q_horse_id', 'dyn_nat_inn', 'dist_change']).dropna(subset=['q_race_id'])
N = N.rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
R = R.merge(N, on=['race_id', 'horse_id'], how='left'); g = R.groupby('horse_id')
R['prev_inn'] = g.dyn_nat_inn.shift()
R['disrupted_and_beaten'] = (R.disrupted_last.clip(lower=0) * (R.prev_inn < 0)).where(R.disrupted_last.notna() & R.prev_inn.notna())
F = pd.read_parquet('b10/out/feat.parquet', columns=['q_race_id', 'q_horse_id', 'opp_step', 'consec_quick']).dropna(subset=['q_race_id']).rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
R = R.merge(F, on=['race_id', 'horse_id'], how='left')
R['leader_x_comp'] = R.leader * R.n_other_leaders; R['leader_x_wide'] = R.leader * R.rel_barrier; R['leader_x_wide_x_comp'] = R.leader * R.rel_barrier * R.n_other_leaders
R['leader_x_stronger'] = R.leader * R.opp_step.clip(lower=0); R['backmarker_x_stronger'] = (R.style5 >= 0.7).astype(float).where(R.style5.notna()) * R.opp_step.clip(lower=0)
# finishing profile at the last tracked run (late acceleration in the final 200 m relative to the 400-200 m section)
E = pd.read_parquet('/tmp/exp/rt/E_qld_sect.parquet', columns=['q_race_id', 'q_horse_id', 'date', 'r_acclast', 'r_v0']).dropna(subset=['q_race_id'])
E = E.rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'})
R = R.merge(E[['race_id', 'horse_id', 'r_acclast']], on=['race_id', 'horse_id'], how='left').sort_values(['horse_id', 'meeting_date']).reset_index(drop=True); g = R.groupby('horse_id')
R['last_acc'] = g.r_acclast.shift(); R['acc_trend'] = R.last_acc - g.r_acclast.transform(lambda s: s.shift(2).rolling(3, min_periods=2).mean())
up = (R.dist_change >= np.log(1.12)).astype(float); dn = (R.dist_change <= -np.log(1.12)).astype(float); st = (R.opp_step >= 1.5).astype(float); wk = (R.opp_step <= -1.5).astype(float)
R['late_x_dist_up'] = R.last_acc * up; R['late_x_stronger'] = R.last_acc * st; R['late_x_up_and_stronger'] = R.last_acc * up * st; R['late_x_dist_down'] = R.last_acc * dn
R['late_x_same_trip_same_class'] = R.last_acc * (1 - up) * (1 - dn) * (1 - st) * (1 - wk)
R['acc_trend_x_backups'] = R.acc_trend * R.consec_quick.fillna(0)
b = L.base('qld'); x = b.merge(R.drop(columns=['meeting_date', 'field', 'distance_m']), on=['race_id', 'horse_id'], how='left')
S = {'3 style vs opposition': ['style5', 'lead_rate5', 'style_rank_pct', 'ahead_gap', 'n_other_leaders', 'leader_x_comp', 'leader_x_wide', 'leader_x_wide_x_comp', 'leader_x_stronger', 'backmarker_x_stronger', 'disrupted_last', 'disrupted_and_beaten'],
     '4 distance x class by profile': ['last_acc', 'late_x_dist_up', 'late_x_stronger', 'late_x_up_and_stronger', 'late_x_dist_down', 'late_x_same_trip_same_class'],
     '7 composition (Qld)': ['acc_trend', 'acc_trend_x_backups']}
rows = []
for sec, cols in S.items():
    for c in cols:
        r = L.test(x, [c], c, 'discovery'); r['section'] = sec; rows.append(r); print(sec, {k: r.get(k) for k in ['label', 'gain', 'lo95', 'hi95', 'p', 'coverage_%']}, flush=True)
D = pd.DataFrame(rows); D['bh_pass'] = L.bh(D.p.values, 0.10); D.to_csv('b10/out/q10_discovery.csv', index=False)
V = pd.DataFrame([dict(L.test(x, [c], c, 'validation'), section=D.set_index('label').section[c]) for c in D[D.bh_pass].label]); V.to_csv('b10/out/q10_validation.csv', index=False); print(V.to_string() if len(V) else 'no discovery passers')
# descriptive (s4): next-start surprise by last-run profile x today's trip/class change (all tracked runs, plain averages with SE)
x2 = R.dropna(subset=['last_acc', 'dist_change', 'opp_step', 'dyn_nat_inn']).copy()
x2['profile'] = np.where(x2.last_acc >= x2.last_acc.quantile(.67), 'accelerated late', np.where(x2.last_acc <= x2.last_acc.quantile(.33), 'slowed late', 'middle'))
x2['trip'] = np.select([x2.dist_change >= np.log(1.12), x2.dist_change <= -np.log(1.12)], ['longer', 'shorter'], 'same')
x2['class'] = np.select([x2.opp_step >= 1.5, x2.opp_step <= -1.5], ['stronger', 'weaker'], 'similar')
t = x2.groupby(['profile', 'trip', 'class']).dyn_nat_inn.agg(['size', 'mean', 'std']).reset_index(); t['se'] = t['std'] / np.sqrt(t['size'])
t = t.rename(columns={'size': 'runs', 'mean': 'surprise_vs_rating_kg'}).drop(columns='std').round(3); t.to_csv('b10/out/q10_profile_table.csv', index=False); print(t.to_string(index=False))
