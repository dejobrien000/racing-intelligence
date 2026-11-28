"""Batch 27 P4: individual performance uncertainty (research only; display/understanding, not an engine input).
Audit first: what the rating mechanism and engine already carry - rating sd (Kalman posterior, dyn_nat_sd), assumed race noise s = 4.5 kg,
the engine's rating_uncertainty, hsd_x_rel (horse variability x relative rating), recent_var_ratio, log_runs_held terms.
Then a predictive distribution for one horse's next performance (Batch 20-21 common target: field-relative performance), mean = b x
field-relative rating (b fitted on 2023), spread from four separately measured sources:
  A ability uncertainty   = dyn_nat_sd^2 (the rating's own posterior variance)
  B genuine variability   = the horse's shrunk variance of its earlier surprises (6 runs' weight to the population)
  C today's circumstances = unfamiliar trip (no run within 10%), first at the course, 120+ days since last run, maiden race
  D missing/unreliable    = history incomplete (experience-file source not 'complete'), no time figure history
Variance model fitted on 2023 runs only (regression of squared error on the components, non-negative); 80% interval from the 10th/90th
percentiles of the standardised error in 2023. Judged on 2024 and 2025-26: coverage (should be ~80%), median width, by age, experience,
class, field size, gap, history completeness - against a one-width-for-all interval. Then: are the engine's chances miscalibrated by
uncertainty? (actual/expected wins by predicted-sd decile, v2.3 and consolidated harness runners, 2025-26). Output out_b27_uncertainty.json"""
import json, numpy as np, pandas as pd
R = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'field', 'state', 'venue'])
R['kgpl'] = 1.5 * (1200 / R.distance_m) ** 0.8; ok = R.finish_pos.notna() & R.margin_l.notna() & R.weight_kg.notna()
R['perf'] = np.where(ok, -R.margin_l.clip(upper=25) * R.kgpl + 0.25 * (R.weight_kg - 57), np.nan)
A = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'age_n', 'class_label', 'a_avg3'] if False else ['race', 'race_id', 'horse', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'age_n', 'class_label'])
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'source']).rename(columns={'race_key': 'race'})
R = R.merge(A, on=['race', 'horse'], how='inner').merge(E, on=['race', 'horse'], how='left')
R['date'] = pd.to_datetime(R.date); R = R.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = R.groupby('horse')
R['k'] = g.cumcount(); R['days'] = (R.date - g.date.shift()).dt.days
x = R.dyn_nat_inn.astype(float); c = x.notna().astype(float); xs = x.fillna(0)
s1 = xs.groupby(R.horse).cumsum() - xs; s2 = (xs ** 2).groupby(R.horse).cumsum() - xs ** 2; n = c.groupby(R.horse).cumsum() - c
POP = 28.9
R['hvar'] = ((s2 - s1 ** 2 / n.replace(0, np.nan)).fillna(0) + 6 * POP) / (n + 6)            # shrunk variance of earlier surprises
ld = np.log(R.distance_m.astype(float))
def seen_within(gr, tol=0.10):
    out = np.zeros(len(gr), dtype=bool); v = gr.values
    for i in range(1, len(v)): out[i] = (np.abs(v[:i] - v[i]) <= tol).any()
    return pd.Series(out, index=gr.index)
R['ld'] = ld; R['new_trip'] = (~R.groupby('horse').ld.apply(seen_within).reset_index(level=0, drop=True).reindex(R.index)).astype(float)
R['vk'] = R.horse + '|' + R.venue.astype(str); R['new_course'] = (R.groupby('vk').cumcount() == 0).astype(float)
R['spell'] = (R.days >= 120).astype(float); R['maiden'] = R.class_label.astype(str).str.contains('Maiden').astype(float)
R['incomplete'] = (R.source.fillna('complete').astype(str) != 'complete').astype(float)
R = R[(R.state != 'QLD') & (R.field >= 6) & R.perf.notna() & R.dyn_nat.notna() & (R.k >= 1) & (R.date >= '2023-01-01')].copy()
for col in ['perf', 'dyn_nat']: R[col + '_r'] = R[col] - R.groupby('race')[col].transform('mean')
R['per'] = np.where(R.date < '2024-01-01', 'fit 2023', np.where(R.date < '2025-01-01', '2024', '2025-26'))
F = R[R.per == 'fit 2023']; b = float((F.perf_r * F.dyn_nat_r).sum() / (F.dyn_nat_r ** 2).sum())
R['err'] = R.perf_r - b * R.dyn_nat_r
X = lambda Z: np.c_[np.ones(len(Z)), Z.dyn_nat_sd ** 2, Z.hvar, Z.new_trip, Z.new_course, Z.spell, Z.maiden, Z.incomplete]
names = ['constant', 'A rating variance', 'B horse variability', 'C new trip', 'C new course', 'C 120d+ spell', 'C maiden race', 'D history incomplete']
F = R[R.per == 'fit 2023']; coef = np.linalg.lstsq(X(F), F.err.values ** 2, rcond=None)[0]; coef = np.maximum(coef, 0); coef[0] = max(coef[0], 1.0)
R['sig'] = np.sqrt(X(R) @ coef); R['z'] = R.err / R.sig
F = R[R.per == 'fit 2023']; q10, q90 = np.percentile(F.z, [10, 90]); c10, c90 = np.percentile(F.err, [10, 90])
R['lo'] = R.sig * q10; R['hi'] = R.sig * q90; R['inside'] = (R.err >= R.lo) & (R.err <= R.hi); R['inside0'] = (R.err >= c10) & (R.err <= c90)
R['ageb'] = pd.cut(R.age_n, [0, 2, 3, 4, 5, 30], labels=['2yo', '3yo', '4yo', '5yo', '6yo+']).astype(str)
R['expb'] = pd.cut(R.k, [0, 3, 10, 25, 999], labels=['1-3 runs', '4-10', '11-25', '26+']).astype(str)
R['fieldb'] = pd.cut(R.field, [0, 8, 12, 30], labels=['<=8', '9-12', '13+']).astype(str)
R['gapb'] = pd.cut(R.days, [-1, 59, 119, 364, 10000], labels=['<60d', '60-119d', '120-364d', '365d+']).astype(str)
R['cls'] = np.where(R.maiden == 1, 'Maiden', np.where(R.class_label.astype(str).isin(['Benchmark', 'BM']), 'Benchmark', 'Other'))
R['hist'] = np.where(R.incomplete == 1, 'incomplete/uncertain', 'complete')
def cov(Z):
    return {'runs': int(len(Z)), 'coverage_model_pct': round(100 * float(Z.inside.mean()), 1), 'median_width_model_kg': round(float((Z.hi - Z.lo).median()), 2),
            'coverage_one_width_pct': round(100 * float(Z.inside0.mean()), 1), 'width_one_width_kg': round(float(c90 - c10), 2)}
out = {'audit': {'in the rating': 'posterior sd per horse (dyn_nat_sd; starts 5 kg, shrinks with runs, grows 0.05 kg2/day idle); assumed race noise s = 4.5 kg',
                 'in the engine (v2.2 terms)': 'rating_uncertainty (= rating sd), hsd_x_rel (horse variability x relative rating), recent_var_ratio, log_runs_held - race probabilities already use A and B partly',
                 'on the dashboard': 'rating sd shown as +/- on ability; experience label; evidence gaps list - no performance interval'},
       'mean_slope_b_fit2023': round(b, 3), 'variance_model_kg2': dict(zip(names, [round(float(v), 3) for v in coef])),
       'standardised_error_q10_q90_fit2023': [round(float(q10), 3), round(float(q90), 3)]}
out['coverage'] = {}
for p in ['2024', '2025-26']:
    Z = R[R.per == p]; r = {'all': cov(Z)}
    for dim in ['ageb', 'expb', 'cls', 'fieldb', 'gapb', 'hist']:
        for v in sorted(Z[dim].dropna().unique()):
            if (Z[dim] == v).sum() >= 500: r[f'{dim}={v}'] = cov(Z[Z[dim] == v])
    out['coverage'][p] = r
    print(p, json.dumps(r['all']), flush=True)
# sharpness: do wide and narrow intervals really differ in realised spread? (deciles of predicted sd, 2025-26)
Z = R[R.per == '2025-26']; d = pd.qcut(Z.sig, 5, labels=False, duplicates='drop')
out['by_predicted_spread_quintile_2025_26'] = {int(k): {'predicted_sd_kg': round(float(v.sig.mean()), 2), 'realised_sd_kg': round(float(v.err.std()), 2), 'coverage_pct': round(100 * float(v.inside.mean()), 1)} for k, v in Z.groupby(d)}
# race-probability calibration by uncertainty (engine runners, window B)
for lab, f in [('v2.3', '/tmp/cand/runners_P26_R.parquet'), ('consolidated', '/tmp/cand/runners_K26_R.parquet')]:
    U = pd.read_parquet(f, columns=['race_id', 'horse', 'win', 'p_B']).dropna(subset=['p_B']).merge(R[['race_id', 'horse', 'sig']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='inner')
    q = pd.qcut(U.sig, 5, labels=False, duplicates='drop')
    out[f'engine_AE_by_spread_quintile_{lab}'] = {int(k): {'runners': int(len(v)), 'A/E': round(float(v.win.sum() / v.p_B.sum()), 3)} for k, v in U.groupby(q)}
json.dump(out, open('batch27/out_b27_uncertainty.json', 'w'), indent=1, default=str)
print(json.dumps({k: out[k] for k in ['variance_model_kg2', 'standardised_error_q10_q90_fit2023', 'by_predicted_spread_quintile_2025_26', 'engine_AE_by_spread_quintile_v2.3', 'engine_AE_by_spread_quintile_consolidated']}))
