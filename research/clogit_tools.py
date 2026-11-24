"""Shared tools for within-race (conditional logit) comparisons, used by batch 2 scripts.
prep(): standardise features with development means/sds, fill missing with 0 (= average) after race-centring, add flags.
fit(): conditional logit on development races. score(): per-race log-likelihood of the actual winner and top-pick hit.
boot_diff(): bootstrap over meetings for the difference between two per-race series."""
import numpy as np, pandas as pd
from statsmodels.discrete.conditional_models import ConditionalLogit

def eligible(X):
    x = X[(X.field >= 6)].copy()
    x['n_win'] = x.groupby('race_id')['win'].transform('sum'); x['n_in'] = x.groupby('race_id')['race_id'].transform('size')
    return x[(x.n_win == 1) & (x.n_in == x.field)].copy()

def prep(x, cols, flag_groups=None):
    """Race-centre each column, scale by development sd, fill missing with 0; flag_groups: {flag_name: column whose missingness defines it}."""
    x = x.copy(); dev = x.period == 'development'
    for c in cols:
        v = x[c].astype(float)
        cen = v - v.groupby(x.race_id).transform('mean')
        sd = cen[dev].std() or 1.0
        x[c + '_z'] = (cen / sd).fillna(0.0)
    for f, c in (flag_groups or {}).items():
        m = x[c].isna().astype(float); x[f + '_z'] = m - m.groupby(x.race_id).transform('mean')
    return x

def fit(x, cols):
    z = [c + '_z' for c in cols]
    dv = x[x.period == 'development']
    m = ConditionalLogit(dv['win'].values, dv[z].values, groups=dv['race_id'].values).fit(disp=0, maxiter=200)
    return np.asarray(m.params)

def score(x, cols, beta, period='evaluation'):
    z = [c + '_z' for c in cols]
    t = x[x.period == period][['race_id', 'meeting_id', 'win', 'field']].copy()
    t['eta'] = x.loc[t.index, z].values @ beta if len(cols) else 0.0
    mx = t.groupby('race_id')['eta'].transform('max')
    t['lse'] = np.log(np.exp(t.eta - mx).groupby(t.race_id).transform('sum')) + mx
    t['lp'] = t.eta - t.lse
    t['top'] = t.groupby('race_id')['eta'].transform(lambda s: (s == s.max()) & (s.rank(method='first', ascending=False) == 1))
    r = t.groupby('race_id').agg(meeting_id=('meeting_id', 'first'), field=('field', 'first'),
                                 lp=('lp', lambda s: s[t.loc[s.index, 'win'] == 1].iloc[0]),
                                 hit=('top', lambda s: int(t.loc[s.index[s.astype(bool)], 'win'].iloc[0])))
    r['null'] = -np.log(r.field)
    return r

def fit_pct(r): return 100 * (1 - r.lp.sum() / r.null.sum())

def boot_diff(a, b, col='lp', reps=1000, seed=20261124, by='meeting'):
    """Mean per-race difference (b - a) with a 95% bootstrap interval over meetings (by='meeting') or calendar months
    (by='month', for time dependence and horses racing again within weeks); one-sided p that b is not better."""
    rng = np.random.default_rng(seed)
    d = (b[col] - a[col]); key = a.meeting_id if by == 'meeting' else a.meeting_id.str[:7]
    m = d.groupby(key).agg(['sum', 'count'])
    ids = m.index.values; s = m['sum'].values; n = m['count'].values; out = []
    for _ in range(reps):
        k = rng.integers(0, len(ids), len(ids)); out.append(s[k].sum() / n[k].sum())
    out = np.array(out)
    return d.mean(), np.percentile(out, 2.5), np.percentile(out, 97.5), float(np.mean(out <= 0))
