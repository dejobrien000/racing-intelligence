"""Batch 4, Study 10 NSW replication (EXPLORATORY: not in the pre-registered P1-P5, Queensland only).
Racing NSW career form lines (barrier, 800m position, field, finish) for horses that raced in NSW Jul-Nov 2026:
survivor-biased (horses still racing), partial fields. Runner-level logistic: win ~ field size + prior form +
weight + relative barrier + barrier x usual position, then course deviations of the two barrier terms:
pooled vs independent courses vs partial pooling (prior spread chosen on an inner time split), fitted before Jul 2025 (survivor sample is thin earlier),
scored Jul 2025-Nov 2026 on log-likelihood per runner-line. Usage: python3 inv26_nsw_course_barriers.py ../history/history.duckdb"""
import sys, duckdb, numpy as np, pandas as pd
from scipy.optimize import minimize
rng = np.random.default_rng(20261124)
con = duckdb.connect(sys.argv[1], read_only=True)
d = con.execute("""select name_key, dob, run_date, track_code, distance_m, finish_pos, field, weight_kg, barrier, pos800, margin_l
                   from nsw_form_line where not trial and field >= 5 order by name_key, dob, run_date""").fetchdf()
d['hk'] = d.name_key + '|' + d.dob.fillna(''); d['run_date'] = pd.to_datetime(d.run_date)
d = d.drop_duplicates(['hk', 'run_date'])
d['fp'] = d.finish_pos.where(d.finish_pos <= d.field)
d['fpct'] = (d.fp - 1) / (d.field - 1); d['spos'] = (d.pos800 - 1) / (d.field - 1)
g = d.groupby('hk')
d['prev_fpct3'] = g.fpct.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
d['prev_lm'] = np.log(g.margin_l.shift().clip(0, 30) + 0.5)
d['styl'] = -g.spos.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())          # higher = usually nearer the lead
d['n_prev'] = g.cumcount()
d = d[(d.run_date >= '2022-10-01') & d.fp.notna() & d.barrier.notna()].copy()
d['win'] = (d.fp == 1).astype(float)
d['relbar'] = -((d.barrier.clip(upper=d.field) - 1) / (d.field - 1))                          # higher = nearer the inside
d['has_prev'] = d.prev_fpct3.notna().astype(float); d['has_style'] = d.styl.notna().astype(float)
for c in ['prev_fpct3', 'prev_lm', 'styl']: d[c] = d[c].fillna(d[c].mean())
d['bxs'] = d.relbar * (d.styl - d.styl.mean())
d['wt'] = d.weight_kg.fillna(d.weight_kg.mean()) - 57; d['lfield'] = np.log(d.field)
d['dev'] = d.run_date < '2025-07-01'; d['meeting'] = d.run_date.dt.strftime('%Y-%m-%d') + '|' + d.track_code
BASE = ['lfield', 'prev_fpct3', 'prev_lm', 'has_prev', 'wt', 'styl', 'has_style', 'relbar', 'bxs']
mu, sd = d.loc[d.dev, BASE].mean(), d.loc[d.dev, BASE].std()
Z = ((d[BASE] - mu) / sd).values; Z = np.c_[np.ones(len(d)), Z]
cnt = d[d.dev].track_code.value_counts(); C = sorted(cnt[cnt >= 800].index)
def dev_cols(df):
    m = np.stack([(df.track_code == c).values for c in C], 1).astype(float)
    rb = (df.relbar.values - mu['relbar'])[:, None] / sd['relbar'] * m; bs = (df.bxs.values - mu['bxs'])[:, None] / sd['bxs'] * m
    return np.c_[rb, bs]
D = dev_cols(d)
def fit(X, y, lam):
    def f(b):
        eta = X @ b; ll = (y * eta - np.logaddexp(0, eta)).sum(); p = 1 / (1 + np.exp(-eta))
        return -ll + 0.5 * (lam * b * b).sum(), -(X.T @ (y - p)) + lam * b
    return minimize(f, np.zeros(X.shape[1]), jac=True, method='L-BFGS-B', options={'maxiter': 3000}).x
def ll_rows(X, y, b): eta = X @ b; return y * eta - np.logaddexp(0, eta)
y = d.win.values; dv = d.dev.values; ev = ~dv
inner1 = dv & (d.run_date < '2024-10-01').values; inner2 = dv & ~inner1
k0 = Z.shape[1]
def lam_vec(tau): return np.r_[np.full(k0, 1e-6), np.full(D.shape[1], 1 / tau ** 2)]
XA = Z; XD = np.c_[Z, D]
grid = []
for tau in [0.01, 0.03, 0.1, 0.3, 1.0, 1e3]:
    b = fit(XD[inner1], y[inner1], lam_vec(tau)); grid.append((tau, ll_rows(XD[inner2], y[inner2], b).sum()))
g0 = ll_rows(XA[inner2], y[inner2], fit(XA[inner1], y[inner1], np.full(k0, 1e-6))).sum()
print('inner split (2024) log-lik vs pooled by tau:', [(t, round(v - g0, 2)) for t, v in grid])
tau = max(grid, key=lambda t: t[1])[0]
bA = fit(XA[dv], y[dv], np.full(k0, 1e-6)); bC = fit(XD[dv], y[dv], lam_vec(1e3)); bD = fit(XD[dv], y[dv], lam_vec(tau))
lA, lC, lD = ll_rows(XA[ev], y[ev], bA), ll_rows(XD[ev], y[ev], bC), ll_rows(XD[ev], y[ev], bD)
mt = d.meeting.values[ev]
def boot(a, b, reps=1000):
    df = pd.DataFrame({'m': mt, 'd': b - a}).groupby('m').d.agg(['sum', 'count']); s, n = df['sum'].values, df['count'].values
    bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(s), len(s)) for _ in range(reps))]
    return round((b - a).mean(), 5), round(np.percentile(bs, 2.5), 5), round(np.percentile(bs, 97.5), 5)
res = pd.DataFrame([{'comparison': 'partial pooling vs pooled', **dict(zip(['gain_per_line', 'lo95', 'hi95'], boot(lA, lD)))},
                    {'comparison': 'independent courses vs pooled', **dict(zip(['gain_per_line', 'lo95', 'hi95'], boot(lA, lC)))},
                    {'comparison': 'partial pooling vs independent', **dict(zip(['gain_per_line', 'lo95', 'hi95'], boot(lC, lD)))}])
res['lines_scored'] = int(ev.sum()); res['tau'] = tau; print(res.to_string(index=False)); res.to_csv('out/out_s10nsw_primary.csv', index=False)
pool_rb = bA[1 + BASE.index('relbar')] / sd['relbar']; pool_bs = bA[1 + BASE.index('bxs')]
b1 = fit(XD[inner1], y[inner1], lam_vec(1e3)); b2 = fit(XD[inner2], y[inner2], lam_vec(1e3)); n = len(C)
t = pd.DataFrame({'course': C, 'dev_lines': [int(cnt[c]) for c in C], 'barrier_dev_independent': bC[k0:k0 + n].round(3), 'barrier_dev_partial': bD[k0:k0 + n].round(3),
                  'style_dev_independent': bC[k0 + n:].round(3), 'style_dev_partial': bD[k0 + n:].round(3), 'barrier_dev_2022_23': b1[k0:k0 + n].round(3), 'barrier_dev_2024': b2[k0:k0 + n].round(3)})
t = t.sort_values('dev_lines', ascending=False); print(t.to_string(index=False)); t.to_csv('out/out_s10nsw_by_course.csv', index=False)
print('pooled: inside vs widest win-odds ratio, typical runner', round(float(np.exp(pool_rb)), 2), '| barrier x style coef (per sd)', round(pool_bs, 3),
      '| stability corr barrier devs 2022-23 vs 2024', round(np.corrcoef(b1[k0:k0 + n], b2[k0:k0 + n])[0, 1], 3),
      '| style devs', round(np.corrcoef(b1[k0 + n:], b2[k0 + n:])[0, 1], 3), '| courses', n, '| dev lines', int(dv.sum()))
