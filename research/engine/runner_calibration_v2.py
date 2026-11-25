"""Runner calibration v2 ('bent line', Batch 9 study E, approved by Damo 25 Nov 2026 for display from that day).
Same inputs as engine/runner_calibration.py (engine v2 out-of-sample predictions on 2025-26), but the log-odds term may bend
at three knots (50th, 90th, 98th percentiles), which shrinks the top end harder. Validated by fitting on 2025 and judging on
2026 (research/batch9/out/e_calib.csv): top-end over-statement removed, overall accuracy unchanged, no runner reordered.
Writes benchmarks/engine_v2/runner_calibration_v2.json. Display only: never feeds ratings or picks."""
import json, numpy as np, pandas as pd, statsmodels.api as sm, sys
T = pd.read_parquet(sys.argv[1] if len(sys.argv) > 1 else '/tmp/exp/calib_oos.parquet'); rng = np.random.default_rng(26)
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
def X(z, f, k): return sm.add_constant(np.column_stack([z] + [np.maximum(z - kk, 0) for kk in k] + [np.log(f)]), has_constant='add')
OUT = {'built_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'method': 'bent_line', 'what': 'P(win) for any runner given engine v2 model chance (log-odds with 3 bends) and field size; fitted on 2025-26 out-of-sample predictions', 'families': {}}
for kind, t in T.groupby('kind'):
    z = lg(t.p.values); k = [float(v) for v in np.percentile(z, [50, 90, 98])]
    m = sm.Logit(t.win.astype(float).values, X(z, t.field.values, k)).fit(disp=0); t = t.assign(cal=m.predict(X(z, t.field.values, k)))
    meets = t.meeting_id.unique(); idx = {mm: np.where(t.meeting_id.values == mm)[0] for mm in meets}; B = []
    for _ in range(200):
        pick = np.concatenate([idx[mm] for mm in rng.choice(meets, len(meets))]); d = t.iloc[pick]
        B.append([float(v) for v in sm.Logit(d.win.astype(float).values, X(lg(d.p.values), d.field.values, k)).fit(disp=0).params])
    top = t.sort_values(['race_id', 'p'], ascending=[True, False]).groupby('race_id').head(1)
    terc = [float(v) for v in np.percentile(top.cal, [100 / 3, 200 / 3])]
    top = top.assign(tier=np.select([top.cal >= terc[1], top.cal >= terc[0]], ['strong', 'moderate'], 'weak'))
    tiers = top.groupby('tier').agg(races=('win', 'size'), mean_calibrated=('cal', 'mean'), top_pick_won=('win', 'mean')).round(4).reset_index().to_dict('records')
    t['bin'] = pd.qcut(t.p, 10, labels=False, duplicates='drop')
    tab = t.groupby('bin').agg(runners=('win', 'size'), model_chance=('p', 'mean'), calibrated=('cal', 'mean'), actual=('win', 'mean')).reset_index(drop=True)
    OUT['families'][kind] = {'races': int(t.race_id.nunique()), 'runners': int(len(t)), 'knots_logit': k, 'coef_const_logitp_bends_logfield': [float(v) for v in m.params], 'bootstrap_coefs': B,
                             'top_pick_terciles': terc, 'top_pick_tiers_2025_26': tiers, 'deciles': [{kk: (round(float(v), 4) if kk != 'runners' else int(v)) for kk, v in r.items()} for r in tab.to_dict('records')]}
    print(kind, 'knots', np.round(k, 2), 'terciles', np.round(terc, 3), '| top decile model/cal/actual', tab.iloc[-1][['model_chance', 'calibrated', 'actual']].round(3).to_dict())
json.dump(OUT, open('benchmarks/engine_v2/runner_calibration_v2.json', 'w'), indent=1)
