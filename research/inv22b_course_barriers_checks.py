"""Study 10 follow-up checks (EXPLORATORY, not pre-registered): (1) prior-spread grid extended below 0.02;
(2) Plackett-Luce top-3 likelihood (uses 1st, 2nd and 3rd place, ~3x the information of winner-only) for A/C/D;
(3) descriptive actual/expected winners by course x barrier band x usual position, expectations from combined_v1."""
import numpy as np, pandas as pd
exec(open('inv22_course_barriers.py').read().split("models = {}")[0])
from scipy.stats import chi2
_r = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'barrier', 'finish_pos']]
x = x.merge(_r, on=['race_id', 'horse_id'], how='left')
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']
d1, d2 = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
# (1) extended grid on the inner split
rows = []
for a in [0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.4, 1.0]:
    taus = {'rb|': a, 'bs|': a}; spec = [('course', courses_D)]; C1, C2 = cols(d1, spec), cols(d2, spec)
    ll = races(d2, C2).loglik_per_race(H.fit(races(d1, C1), lam_for(C1.columns, taus))).sum()
    rows.append({'tau': a, 'inner_2024_loglik': round(ll, 2)})
g = pd.DataFrame(rows); g['vs_full_pooling'] = (g.inner_2024_loglik - g.inner_2024_loglik.iloc[0]).round(2); print(g.to_string(index=False)); g.to_csv('out/out_s10x_tau_grid.csv', index=False)
# (2) Plackett-Luce top-3: stage k = choose the k-th placegetter from those not yet placed
def explode(df, K=3):
    out = []
    fp = df.finish_pos.where(df.finish_pos <= df.field).fillna(99)
    for k in range(1, K + 1):
        s = df[fp >= k].copy(); s['win'] = (fp[fp >= k] == k).astype(float); s['race_id'] = s.race_id.astype(str) + f'#{k}'; out.append(s)
    e = pd.concat(out); return e[e.groupby('race_id').win.transform('sum') == 1]
def pl_score(df, spec, lam_fn, fit_df):
    Cf = cols(fit_df, spec); Cf['off'] = fit_df.offset.values; lam = np.r_[lam_fn(Cf.columns[:-1]), 1e-6]
    b = H.fit(races(fit_df, Cf), lam); Ce = cols(df, spec); Ce['off'] = df.offset.values
    R = races(df, Ce); rid = df.race_id.values[R.o][R.starts]
    return pd.DataFrame({'stage': rid, 'lp': R.loglik_per_race(b)}).assign(race=lambda t: t.stage.str.split('#').str[0]).groupby('race').lp.sum()
devE, evE = explode(dev), explode(ev)
d1E, d2E = explode(d1), explode(d2); tl = []
for a in [0.005, 0.02, 0.05, 0.1, 0.2, 0.5]:
    tt = {'rb|': a, 'bs|': a}; tl.append((pl_score(d2E, [('course', courses_D)], lambda c, tt=tt: lam_for(c, tt), d1E).sum(), a))
print('top-3 likelihood inner split by tau:', [(a, round(v, 1)) for v, a in tl])
tD = {'rb|': max(tl)[1], 'bs|': max(tl)[1]}
lamD = lambda c: lam_for(c, tD) if len(c) else np.zeros(0)
plA = pl_score(evE, [], lambda c: np.zeros(0), devE)
plD = pl_score(evE, [('course', courses_D)], lamD, devE)
plC = pl_score(evE, [('course', courses_C)], lambda c: np.full(len(c), 1e-6), devE)
mid = ev.groupby('race_id').meeting_id.first()
def bootd(a, b, reps=1000):
    d = (b - a).rename('d').to_frame().join(mid); m = d.groupby('meeting_id').d.agg(['sum', 'count']); s, n = m['sum'].values, m['count'].values
    bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(s), len(s)) for _ in range(reps))]
    return round(d.d.mean(), 5), round(np.percentile(bs, 2.5), 5), round(np.percentile(bs, 97.5), 5)
pl = pd.DataFrame([{'comparison': 'D vs A (top-3 likelihood)', **dict(zip(['gain', 'lo95', 'hi95'], bootd(plA, plD)))},
                   {'comparison': 'C vs A (top-3 likelihood)', **dict(zip(['gain', 'lo95', 'hi95'], bootd(plA, plC)))},
                   {'comparison': 'D vs C (top-3 likelihood)', **dict(zip(['gain', 'lo95', 'hi95'], bootd(plC, plD)))}])
print(pl.to_string(index=False)); pl.to_csv('out/out_s10x_plackett_luce.csv', index=False)
# (3) descriptive A/E vs combined_v1 expectation (expected = within-race softmax of the benchmark score; all periods)
x['p_exp'] = np.exp(x.offset - x.groupby('race_id').offset.transform('max')); x['p_exp'] /= x.groupby('race_id').p_exp.transform('sum')
x['bar_band'] = pd.cut(x.barrier, [0, 3, 6, 9, 30], labels=['1-3', '4-6', '7-9', '10+'])
x['pos_band'] = pd.cut(x.p_style, [-99, x.p_style.quantile(1/3), x.p_style.quantile(2/3), 99], labels=['back', 'mid', 'on-pace'])
def ae(g):
    a, e = g.win.sum(), g.p_exp.sum(); lo = chi2.ppf(0.025, 2 * a) / 2 if a else 0; hi = chi2.ppf(0.975, 2 * a + 2) / 2
    return pd.Series({'runners': len(g), 'winners': int(a), 'expected': round(e, 1), 'A/E': round(a / e, 2), 'lo95': round(lo / e, 2), 'hi95': round(hi / e, 2)})
t1 = x.groupby(['course', 'bar_band'], observed=True).apply(ae).reset_index(); t1.to_csv('out/out_s10x_ae_course_barrier.csv', index=False)
t2 = x[x.p_style.notna()].groupby(['course', 'bar_band', 'pos_band'], observed=True).apply(ae).reset_index(); t2.to_csv('out/out_s10x_ae_course_barrier_style.csv', index=False)
print(t1[t1.course.isin(['Eagle_Farm', 'Doomben', 'Sunshine_Coast', 'Ipswich', 'Toowoomba'])].to_string(index=False))
f = t2[(t2.winners >= 15) & ((t2.lo95 > 1) | (t2.hi95 < 1))]; print('cells clear of 1.0 (of', len(t2), '):'); print(f.to_string(index=False))
