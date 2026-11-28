"""Batch 28 item 7: why does the consolidated rating slightly overrate established horses aged 5+ (actual/expected 0.932 -> 0.914)?
Window B (fitted before 2025, judged 2025-26) runner chances from the national harness: v2.3 (P26) and consolidated (K26).
Established = 15+ runs held and aged 5+. Split A/E by: age; experience; how far the current rating sits below the horse's own peak
(peak retention); rating trend over its last 6 runs (decline); a poor last run (surprise <= -3 kg, and > 12 L beaten: the cap); run of the
preparation; days since last run; share of lightly raced rivals; the horse's standing in the field.
Mechanism: after a poor run, does the consolidated rule leave established horses rated too high (next-run surprise vs each rule's
rating, common target as Batch 20-21)? And do the existing engine inputs absorb it? Output batch28/out_b28_older_horses.json"""
import json, numpy as np, pandas as pd
U = pd.read_parquet('/tmp/cand/runners_P26_R.parquet', columns=['race_id', 'horse', 'win', 'p_B']).merge(
    pd.read_parquet('/tmp/cand/runners_K26_R.parquet', columns=['race_id', 'horse', 'p_B']), on=['race_id', 'horse'], suffixes=('_v23', '_cons')).dropna()
F = pd.read_parquet('/tmp/cand/frames/CONS_national.parquet', columns=['race_id', 'race', 'horse', 'date', 'age_n', 'dyn_nat', 'dyn_nat_inn', 'margin_l', 'field', 'prev_date'])
C2 = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race', 'horse', 'dyn_nat', 'dyn_nat_inn']).rename(columns={'dyn_nat': 'dn23', 'dyn_nat_inn': 'inn23'})
F = F.merge(C2, on=['race', 'horse'], how='left'); F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']); g = F.groupby('horse')
F['k'] = g.cumcount(); F['days'] = (F.date - pd.to_datetime(F.prev_date)).dt.days
F['peak'] = g.dyn_nat.transform(lambda s: s.shift(1).cummax()); F['below_peak'] = F.peak - F.dyn_nat
F['trend6'] = F.dyn_nat - g.dyn_nat.shift(6)
F['last_inn'] = g.dyn_nat_inn.shift(1); F['last_margin'] = g.margin_l.shift(1)
F['prep'] = (F.days.fillna(999) >= 60).astype(int).groupby(F.horse).cumsum(); F['run_in_prep'] = F.groupby(['horse', 'prep']).cumcount() + 1
F['light_share'] = F.groupby('race_id').k.transform(lambda s: (s <= 3).mean())
F['standing'] = F.groupby('race_id').dyn_nat.rank(ascending=False, pct=True)
X = U.merge(F.drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
E = X[(X.k >= 15) & (X.age_n >= 5)].copy()
def ae(Z): return {'runners': int(len(Z)), 'A/E v2.3': round(float(Z.win.sum() / Z.p_B_v23.sum()), 3), 'A/E consolidated': round(float(Z.win.sum() / Z.p_B_cons.sum()), 3)}
out = {'established_all': ae(E), 'everyone_else': ae(X[~X.index.isin(E.index)])}
cuts = {'age': ('age_n', [4, 5, 6, 7, 8, 30], ['5yo', '6yo', '7yo', '8yo', '9yo+']), 'runs held': ('k', [14, 25, 40, 999], ['15-25', '26-40', '41+']),
        'rating below own peak (kg)': ('below_peak', [-1, 1, 3, 6, 99], ['<1', '1-3', '3-6', '6+']), 'rating trend over last 6 runs (kg)': ('trend6', [-99, -2, -0.5, 0.5, 99], ['falling 2+', 'falling 0.5-2', 'flat', 'rising']),
        'last run vs rating (kg)': ('last_inn', [-99, -6, -3, 0, 99], ['-6 or worse', '-6 to -3', '-3 to 0', 'better']), 'run of preparation': ('run_in_prep', [0, 1, 3, 99], ['1st up', '2nd-3rd', '4th+']),
        'days since last run': ('days', [-1, 20, 59, 119, 9999], ['<21', '21-59', '60-119', '120+']), 'share of rivals with 0-3 runs': ('light_share', [-0.01, 0.0, 0.2, 1], ['none', 'up to 20%', 'over 20%']),
        'standing in field (rating rank)': ('standing', [0, 0.25, 0.5, 1.01], ['top quarter', 'second quarter', 'bottom half'])}
for lab, (c, b, l) in cuts.items():
    t = pd.cut(E[c], b, labels=l); out[lab] = {str(k): ae(z) for k, z in E.groupby(t, observed=True) if len(z) >= 300}
E['heavy'] = E.last_margin > 12
out['last run beaten more than 12 L (cap applied)'] = {str(k): ae(z) for k, z in E.groupby('heavy')}
# mechanism: after a poor run, how wrong is each rule's rating on the NEXT run? (field-relative common target, established horses, 2025-26)
R = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m'])
R['perf'] = np.where(R.finish_pos.notna() & R.margin_l.notna() & R.weight_kg.notna(), -R.margin_l.clip(upper=25) * 1.5 * (1200 / R.distance_m) ** 0.8 + 0.25 * (R.weight_kg - 57), np.nan)
M = F.merge(R[['race', 'horse', 'perf']], on=['race', 'horse'], how='left'); M = M[(M.date >= '2025-01-01') & M.perf.notna() & M.dn23.notna()]
for c in ['perf', 'dyn_nat', 'dn23']: M[c + '_r'] = M[c] - M.groupby('race')[c].transform('mean')
M['err_cons'] = M.perf_r - M.dyn_nat_r; M['err_v23'] = M.perf_r - M.dn23_r
est = (M.k >= 15) & (M.age_n >= 5)
def mech(Z): return {'runs': int(len(Z)), 'mean error v2.3 (kg, + = ran better than rated)': round(float(Z.err_v23.mean()), 2), 'mean error consolidated': round(float(Z.err_cons.mean()), 2)}
out['next run after a poor run, established'] = {lab: mech(M[est & m]) for lab, m in [('last run -6 kg or worse', M.last_inn <= -6), ('last run -6 to -3', M.last_inn.between(-6, -3)), ('last run better than -3', M.last_inn > -3),
                                                                                       ('last run beaten > 12 L', M.last_margin > 12)]}
out['next run, others (reference)'] = {lab: mech(M[~est & m]) for lab, m in [('last run -6 kg or worse', M.last_inn <= -6), ('last run better than -3', M.last_inn > -3)]}
json.dump(out, open('batch28/out_b28_older_horses.json', 'w'), indent=1); print(json.dumps(out, indent=0)[:4000])
