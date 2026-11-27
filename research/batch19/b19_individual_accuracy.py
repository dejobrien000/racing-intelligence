"""Batch 19 B8: individual-performance accuracy of each rating mechanism, separately from race-level winner probability.
For every measured run in the judging windows (2024; 2025-26) by a horse with at least one earlier run, the error is the run's recorded
performance relative to its field minus the horse's pre-race rating relative to the same field (kg). The recorded performance is the
SAME uncapped figure for every mechanism (margin capped only at the 25 lengths every version uses, weight credit 0.25), so a mechanism
cannot look better by changing what it is judged against. Reported: mean squared error, mean absolute error, within-race rank correlation
of rating with finishing order, by experience group. Research only; no prices.
Usage (from research/): python3 batch19/b19_individual_accuracy.py LABEL=frame.parquet ... -> batch19/out_b19_individual_accuracy.json"""
import sys, json, numpy as np, pandas as pd
FR = dict(a.split('=', 1) for a in sys.argv[1:])
R = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'field', 'state'])
R['kgpl'] = 1.5 * (1200 / R.distance_m) ** 0.8; ok = R.finish_pos.notna() & R.margin_l.notna() & R.weight_kg.notna()
R['perf'] = np.where(ok, -R.margin_l.clip(upper=25) * R.kgpl + 0.25 * (R.weight_kg - 57), np.nan)
R = R.sort_values(['horse', 'date', 'race']); R['k'] = R.groupby('horse').cumcount()
R = R[(R.date >= '2024-01-01') & (R.state != 'QLD') & (R.field >= 6)]
R['win'] = np.where(R.date < '2025-01-01', '2024', '2025-26')
R['exp'] = pd.cut(R.k, [-1, 0, 5, 15, 999], labels=['first run held', '1-5 held', '6-15 held', '16+ held']).astype(str)
OUT = {}
for lab, f in FR.items():
    F = pd.read_parquet(f, columns=['race', 'horse', 'dyn_nat']).drop_duplicates(['race', 'horse'])
    X = R.merge(F, on=['race', 'horse'], how='inner'); X = X[X.perf.notna() & X.dyn_nat.notna() & (X.k >= 1)]
    X = X[X.groupby('race').perf.transform('count') >= 4]
    X['e'] = (X.perf - X.groupby('race').perf.transform('mean')) - (X.dyn_nat - X.groupby('race').dyn_nat.transform('mean'))
    X['rr'] = X.groupby('race').dyn_nat.rank(ascending=False); X['fr'] = X.groupby('race').finish_pos.rank()
    o = {}
    for (w, ex), g in [((w, 'all'), g) for w, g in X.groupby('win')] + list(X.groupby(['win', 'exp'])):
        rho = g.groupby('race')[['rr', 'fr']].corr().xs('rr', level=1).fr if ex == 'all' else None
        o[f'{w} | {ex}'] = {'runs': int(len(g)), 'mse': round(float((g.e ** 2).mean()), 4), 'mae': round(float(g.e.abs().mean()), 4), **({'rank_corr_with_finish': round(float(rho.mean()), 4)} if rho is not None else {})}
    OUT[lab] = o; print(lab, {k: (v['mse'], v.get('rank_corr_with_finish')) for k, v in o.items() if 'all' in k})
base = list(FR)[0]
OUT['vs_' + base] = {lab: {k: {'mse_change': round(OUT[lab][k]['mse'] - OUT[base][k]['mse'], 4), 'mae_change': round(OUT[lab][k]['mae'] - OUT[base][k]['mae'], 4)} for k in OUT[base]} for lab in FR if lab != base}
json.dump(OUT, open('batch19/out_b19_individual_accuracy.json', 'w'), indent=1)
