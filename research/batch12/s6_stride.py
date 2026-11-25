"""Batch 12 s6: stride length and frequency (Queensland tracking). Reliability, then whether stride composition changes at similar speed
precede different next-start results. speed = frequency x length (checked), so composition is split as log speed = log f + log L."""
import numpy as np, pandas as pd
X = pd.read_parquet('/home/claude/b12/sect_runs_own.parquet')
for c in ['sf200', 'sl200', 'sf400', 'sl400']: X.loc[X[c] <= 0, c] = np.nan
X['prod_err'] = (X.sf200 * X.sl200 / X.v200 - 1).abs()
print('final-200: frequency x length vs speed, median abs error', round(X.prod_err.median(), 4), '| 95th pct', round(X.prod_err.quantile(.95), 4))
print('distinct frequency values (0.1 Hz steps):', X.sf200.round(2).nunique(), '| share of runs with frequency AND length present', round(X[['sf200', 'sl200']].notna().all(axis=1).mean(), 3))
X = X.sort_values(['horse', 'meeting_date']); g = X.groupby('horse')
for c in ['sl200', 'sf200']:
    X[c + '_fr'] = np.log(X[c]) - np.log(X[c]).groupby(X.race_id).transform('median')     # field-relative log stride length / frequency
    X[c + '_prev'] = g[c + '_fr'].shift()
X['v_fr'] = np.log(X.v200) - np.log(X.v200).groupby(X.race_id).transform('median'); X['v_prev'] = g.v_fr.shift()
ok = X[['sl200_fr', 'sl200_prev']].notna().all(axis=1)
print('run-to-run correlation (same horse, field-relative): stride length', round(X.loc[ok, ['sl200_fr', 'sl200_prev']].corr().iloc[0, 1], 3),
      '| frequency', round(X.loc[ok, ['sf200_fr', 'sf200_prev']].corr().iloc[0, 1], 3), '| final-200 speed', round(X.loc[ok, ['v_fr', 'v_prev']].corr().iloc[0, 1], 3))
print('by year: median final-200 stride length (m) and frequency (Hz):'); print(X.groupby(X.meeting_date.dt.year)[['sl200', 'sf200']].median().round(3).to_string())
# own norm (shrunk), composition change at similar speed
for c in ['sl200_fr', 'sf200_fr', 'v_fr']:
    s = X[c]; cnt = s.notna().astype(float).groupby(X.horse).cumsum() - s.notna(); sm = s.fillna(0).groupby(X.horse).cumsum() - s.fillna(0)
    r = s - sm / (cnt + 3.0); X[c + '_own'] = r / r[X.n_trk >= 3].std()
el = X[(X.n_trk >= 3) & X.inn_n1.notna() & X.sl200_fr_own.notna()].copy()
el['cell'] = pd.cut(el.dyn_nat_inn, [-99, -4, -1.5, 1.5, 4, 99]).astype(str) + pd.cut(el.n_trk, [2, 5, 10, 999]).astype(str)
same_speed = el.v_fr_own.abs() < 0.5
pats = {'shorter strides, higher frequency, same speed': same_speed & (el.sl200_fr_own < -1) & (el.sf200_fr_own > 1),
        'longer strides, lower frequency, same speed': same_speed & (el.sl200_fr_own > 1) & (el.sf200_fr_own < -1),
        'shorter strides (any speed)': el.sl200_fr_own < -1, 'longer strides (any speed)': el.sl200_fr_own > 1,
        'higher frequency (any speed)': el.sf200_fr_own > 1, 'lower frequency (any speed)': el.sf200_fr_own < -1}
rows = []
for lab, m in pats.items():
    base = el[~m].groupby('cell')[['inn_n1', 'fp_n1']].mean(); f = el[m]
    d = f.inn_n1 - f.cell.map(base.inn_n1); dp = f.fp_n1 - f.cell.map(base.fp_n1)
    rng = np.random.default_rng(3); u, inv = np.unique(f.horse.values, return_inverse=True); s = np.bincount(inv, d.fillna(0).values); n = np.bincount(inv)
    bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(400))]
    rows.append({'pattern': lab, 'runs': len(f), 'horses': f.horse.nunique(), 'next_surprise_vs_matched_kg': round(d.mean(), 2), 'ci': (round(np.percentile(bs, 2.5), 2), round(np.percentile(bs, 97.5), 2)), 'next_finish_pct_vs_matched': round(dp.mean(), 3)})
O = pd.DataFrame(rows); print(O.to_string(index=False)); O.to_csv('/home/claude/b12/out_s6_stride.csv', index=False)
rows = []
for yrs, lab in [((2022, 2023, 2024), '2022-24'), ((2025, 2026), '2025-26')]:
    sub = el[el.meeting_date.dt.year.isin(yrs)]; ss = sub.v_fr_own.abs() < 0.5
    m = ss & (sub.sl200_fr_own < -1) & (sub.sf200_fr_own > 1); base = sub[~m].groupby('cell').inn_n1.mean(); f = sub[m]; d = f.inn_n1 - f.cell.map(base)
    rows.append({'period': lab, 'runs': len(f), 'next_surprise_vs_matched_kg': round(d.mean(), 2), 'se': round(d.std() / np.sqrt(len(d)), 2)})
print('shorter strides + higher frequency at the same speed, by period:', rows)
