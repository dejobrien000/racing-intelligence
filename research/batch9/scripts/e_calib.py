"""Batch 9 study E: stronger shrinkage of high win chances. Fit each calibration on 2025 races, judge on 2026 (unseen).
Rankings within a race cannot change: every method is an increasing function of the model chance (checked)."""
import numpy as np, pandas as pd, statsmodels.api as sm
from sklearn.isotonic import IsotonicRegression
T = pd.read_parquet('/tmp/exp/calib_oos.parquet'); T = T[T.p.notna()]
lg = lambda p: np.log(np.clip(p, 1e-4, 1 - 1e-4) / (1 - np.clip(p, 1e-4, 1 - 1e-4)))
def spl(z, knots): return np.column_stack([z] + [np.maximum(z - k, 0) for k in knots])
rows, bands = [], []
for kind, d in T.groupby('kind'):
    a, b = d[d.date.dt.year == 2025].copy(), d[d.date.dt.year == 2026].copy()
    za, zb = lg(a.p), lg(b.p); fa, fb = np.log(a.field), np.log(b.field)
    knots = np.percentile(za, [50, 90, 98])
    M = {}
    M['raw model chance'] = b.p.values
    m1 = sm.Logit(a.win, sm.add_constant(np.column_stack([za, fa]))).fit(disp=0); M['current (straight line on log-odds + field)'] = m1.predict(sm.add_constant(np.column_stack([zb, fb])))
    m2 = sm.Logit(a.win, sm.add_constant(np.column_stack([spl(za, knots), fa]))).fit(disp=0); M['bent line: extra shrink at the top'] = m2.predict(sm.add_constant(np.column_stack([spl(zb, knots), fb])))
    iso = IsotonicRegression(out_of_bounds='clip', increasing=True).fit(a.p, a.win); M['isotonic (step curve)'] = iso.predict(b.p)
    for k, pr in M.items():
        pr = np.clip(pr, 1e-4, 1 - 1e-4); y = b.win.values
        # monotone check inside races: does the method ever reorder two runners of the same race?
        o = pd.DataFrame({'r': b.race_id.values, 'p': b.p.values, 'c': pr}); bad = (o.groupby('r').apply(lambda t: (t.p.rank() - t.c.rank(method='average')).abs().max() > 0.5 if len(t) > 1 else False)).mean()
        top = b.p.values >= 0.5
        rows.append({'region': kind, 'method': k, 'runners_2026': len(b), 'log_loss': round(-np.mean(y * np.log(pr) + (1 - y) * np.log(1 - pr)), 5), 'brier': round(np.mean((pr - y) ** 2), 5),
                     '50%+ shown': round(100 * pr[top].mean(), 1), '50%+ won': round(100 * y[top].mean(), 1), '40-50% shown': round(100 * pr[(b.p.values >= .4) & (b.p.values < .5)].mean(), 1),
                     '40-50% won': round(100 * y[(b.p.values >= .4) & (b.p.values < .5)].mean(), 1), 'races_reordered_%': round(100 * bad, 2)})
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/e_calib.csv', index=False)
