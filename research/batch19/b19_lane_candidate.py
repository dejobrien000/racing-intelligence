"""Batch 19 A4: lane-adjusted rating candidates, Queensland and South Australia (research form; no release; shadow later).
Simple, reproducible adjustment: adj_kg = share_state x help, where help = the meeting's lane effect estimated from the OTHER races at the
meeting AFTER removing extra-ground and pace-position effects (batch19/b19_lane_controls.py) x the horse's own straight lane relative to its
race, clipped to its 1st-99th percentile. The share is each state's own calibration (this-run slope with barrier, early position, extra
ground and tempo x position held constant), on completed meetings before the period judged: Queensland on meetings before 2024; SA on 2024
meetings (SA tracking starts in 2024, so only 2025-26 is a clean SA test). Recorded performances are never changed; only the figure the
rating learns from. Output: /tmp/cand/lane_adj_b19.parquet (race_key, horse, adj_kg) + calibration record.
Usage (from research/): python3 batch19/b19_lane_candidate.py -> batch19/out_b19_lane_candidate.json"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
src = open('batch19/b19_lane_controls.py').read(); src = src[:src.index('def analyse(Z):')]; exec(src)
Fk = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'q_race_id', 'q_horse_id']).dropna(subset=['q_race_id']); Fk['q_horse_id'] = Fk.q_horse_id.astype(str)
Qk = X[['q_race_id', 'q_horse_id', 'meeting_date']].merge(Fk, on=['q_race_id', 'q_horse_id'], how='left')
Q['race_key'] = Qk.race.values; Q['md'] = pd.to_datetime(Qk.meeting_date.values)
Sx['race_key'] = A['race'].values; Sx['md'] = pd.to_datetime(A.meeting_date.values)
def build(Z, cal_mask_fn):
    Z = Z.copy()
    for c in ['distance_m', 'dyn_nat_inn', 'lane', 'barrier_rel', 'early_rel', 'ground', 'tempo_raw']: Z[c] = pd.to_numeric(Z[c], errors='coerce').astype(float)
    Z = Z.dropna(subset=['dyn_nat_inn', 'barrier_rel'])
    for c in ['barrier_rel', 'early_rel', 'lane', 'ground']: Z[c + '_w'] = Z[c] - Z.groupby('rid')[c].transform('mean')
    Z['y_w'] = Z.dyn_nat_inn - Z.groupby('rid').dyn_nat_inn.transform('mean'); Z['dband'] = pd.cut(Z.distance_m, [0, 1100, 1300, 1500, 1800, 9999]).astype(str)
    Z['tempo_z'] = (Z.tempo_raw - Z.groupby(['course', 'dband']).tempo_raw.transform('mean')) / Z.groupby(['course', 'dband']).tempo_raw.transform('std')
    Z['pace_x'] = Z.early_rel_w * Z.tempo_z.fillna(0)
    ok = Z.ground_w.notna() & Z.early_rel_w.notna(); cal0 = Z[ok & cal_mask_fn(Z)]
    adj = smf.ols('y_w ~ ground_w + early_rel_w + pace_x - 1', cal0).fit()                       # ground/pace effects from the calibration period only
    Z['y_adj'] = Z.y_w; Z.loc[ok, 'y_adj'] = Z.loc[ok, 'y_w'] - adj.predict(Z[ok])
    Z['lxy'] = (Z.lane_w * Z.y_adj).fillna(0); Z['lxx'] = (Z.lane_w ** 2).fillna(0)
    m = Z.groupby('meeting')[['lxy', 'lxx']].transform('sum'); r = Z.groupby('rid')[['lxy', 'lxx']].transform('sum')
    Z['help'] = ((m.lxy - r.lxy) / (m.lxx - r.lxx).replace(0, np.nan)) * Z.lane_w
    lo, hi = Z.help.quantile(0.01), Z.help.quantile(0.99); Z['help'] = Z.help.clip(lo, hi)
    c = Z[ok & cal_mask_fn(Z) & Z.help.notna()]
    cal = smf.ols('dyn_nat_inn ~ help + barrier_rel_w + early_rel_w + ground_w + pace_x', c).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(c.meeting)[0]})
    share = float(cal.params['help']); Z['adj_kg'] = (share * Z.help).fillna(0.0)
    rec = {'share': [round(share, 3), round(float(cal.conf_int().loc['help', 0]), 3), round(float(cal.conf_int().loc['help', 1]), 3)], 'calibration_runs': int(cal.nobs),
           'ground_pace_effects_calibration': {k: round(float(v), 3) for k, v in adj.params.items()}, 'runs_adjusted': int((Z.adj_kg != 0).sum()), 'adj_sd_kg': round(float(Z.adj_kg[Z.adj_kg != 0].std()), 3)}
    return Z[Z.race_key.notna() & (Z.adj_kg != 0)][['race_key', 'horse', 'adj_kg']], rec
oq, rq = build(Q, lambda z: z.md < '2024-01-01'); osa, rsa = build(Sx, lambda z: (z.md >= '2024-01-01') & (z.md < '2025-01-01'))
out = pd.concat([oq, osa]).drop_duplicates(['race_key', 'horse']); out.to_parquet('/tmp/cand/lane_adj_b19.parquet')
OUT = {'QLD': rq, 'SA': rsa, 'rows': int(len(out))}; json.dump(OUT, open('batch19/out_b19_lane_candidate.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
