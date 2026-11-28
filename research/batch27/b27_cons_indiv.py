"""Batch 27 P2 (part 4 of the consolidated review, replacing the frame-surprise version, which compared against each rule's OWN capped
performance figure and so was not like for like). Individual accuracy on ONE common target, exactly as Batch 20-21:
perf = -margin (capped at 25 L) x kg per length + 0.25 x (weight - 57); error = (field-relative perf - field-relative pre-race rating)^2;
calibration slope of field-relative perf on field-relative rating; within-race rank correlation with finishing order.
Non-Qld, fields of 6+, runs with 1+ earlier run; window A = 2024, B = 2025-26. Output: merged into batch27/out_b27_cons_review.json"""
import json, numpy as np, pandas as pd
R = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'field', 'state'])
R['kgpl'] = 1.5 * (1200 / R.distance_m) ** 0.8; ok = R.finish_pos.notna() & R.margin_l.notna() & R.weight_kg.notna()
R['perf'] = np.where(ok, -R.margin_l.clip(upper=25) * R.kgpl + 0.25 * (R.weight_kg - 57), np.nan)
R = R.sort_values(['horse', 'date', 'race']); R['k'] = R.groupby('horse').cumcount()
R = R[(R.date >= '2024-01-01') & (R.state != 'QLD') & (R.field >= 6)].copy(); R['w'] = np.where(R.date < '2025-01-01', 'A', 'B')
A = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=['race', 'horse', 'dyn_nat', 'age_n', 'tier', 'class_label', 'prev_date', 'date'])
B = pd.read_parquet('/tmp/cand/frames/CONS_national.parquet', columns=['race', 'horse', 'dyn_nat']).rename(columns={'dyn_nat': 'dn_cons'})
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'source']).rename(columns={'race_key': 'race'})
R = R.merge(A.drop(columns=['date']), on=['race', 'horse'], how='inner').merge(B, on=['race', 'horse'], how='inner').merge(E, on=['race', 'horse'], how='left')
R = R[R.perf.notna() & R.dyn_nat.notna() & R.dn_cons.notna() & (R.k >= 1)].copy()
for c in ['perf', 'dyn_nat', 'dn_cons']: R[c + '_r'] = R[c] - R.groupby('race')[c].transform('mean')
R['days'] = (pd.to_datetime(R.date) - pd.to_datetime(R.prev_date)).dt.days
R['ageb'] = pd.cut(R.age_n, [0, 2, 3, 4, 5, 30], labels=['2yo', '3yo', '4yo', '5yo', '6yo+']).astype(str)
R['expb'] = pd.cut(R.k, [0, 3, 10, 25, 999], labels=['1-3 runs', '4-10', '11-25', '26+']).astype(str)
R['stage'] = np.where((R.k >= 15) & (R.age_n >= 5), 'established (15+ runs, 5yo+)', np.where(R.k <= 5, 'emerging (1-5 runs)', 'middle'))
R['gap'] = pd.cut(R.days, [-1, 13, 59, 119, 364, 10000], labels=['<14d', '14-59d', '60-119d', '120-364d', '365d+']).astype(str)
R['hist'] = R.source.fillna('unknown').astype(str)
R['cls'] = np.where(R.class_label.astype(str).str.contains('Maiden'), 'Maiden', np.where(R.class_label.astype(str).isin(['Benchmark', 'BM']), 'Benchmark', 'Other'))
def m(Z):
    if len(Z) < 500: return None
    o = {'runs': int(len(Z))}
    for lab, c in [('v2.3', 'dyn_nat_r'), ('consolidated', 'dn_cons_r')]:
        o[f'error_kg2 {lab}'] = round(float(((Z.perf_r - Z[c]) ** 2).mean()), 2)
        o[f'slope {lab}'] = round(float((Z.perf_r * Z[c]).sum() / (Z[c] ** 2).sum()), 3)
    rc = Z.groupby('race').apply(lambda g: pd.Series({'a': g.dyn_nat.corr(-g.finish_pos, method='spearman'), 'b': g.dn_cons.corr(-g.finish_pos, method='spearman')}) if len(g) >= 4 else pd.Series({'a': np.nan, 'b': np.nan}))
    o['rank_corr v2.3'] = round(float(rc.a.mean()), 3); o['rank_corr consolidated'] = round(float(rc.b.mean()), 3)
    return o
res = {}
for w in ['A', 'B']:
    Z = R[R.w == w]; r = {'all': m(Z)}
    if w == 'B':
        for dim in ['ageb', 'expb', 'stage', 'gap', 'hist', 'state', 'tier', 'cls']:
            for v in sorted(Z[dim].dropna().astype(str).unique()):
                g = m(Z[Z[dim].astype(str) == v])
                if g: r[f'{dim}={v}'] = g
    res[w] = r; print(w, json.dumps(r['all']), flush=True)
o = json.load(open('batch27/out_b27_cons_review.json')); o.pop('individual_2025_26', None); o['individual_common_target'] = res
json.dump(o, open('batch27/out_b27_cons_review.json', 'w'), indent=1, default=str)
