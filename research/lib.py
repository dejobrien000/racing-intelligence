import numpy as np, pandas as pd
from scipy import stats
def ae(g, win='win', field='field'):
    """Actual/expected wins where expected = 1/field per runner (no-information baseline)."""
    n = len(g); w = g[win].sum(); e = (1.0 / g[field]).sum()
    lo, hi = (stats.chi2.ppf(0.025, 2*w)/2 if w > 0 else 0.0), stats.chi2.ppf(0.975, 2*(w+1))/2
    return pd.Series({'runs': n, 'wins': int(w), 'win_pct': round(100*w/n, 1) if n else np.nan,
                      'expected_wins': round(e, 1), 'A/E': round(w/e, 2) if e else np.nan,
                      'A/E_lo95': round(lo/e, 2) if e else np.nan, 'A/E_hi95': round(hi/e, 2) if e else np.nan})
def ae_table(df, by, **kw):
    return df.groupby(by, observed=True).apply(lambda g: ae(g, **kw), include_groups=False).reset_index()
def dist_band(d):
    return pd.cut(d, [0, 1100, 1250, 1450, 1700, 2100, 4000], labels=['<=1100','1101-1250','1251-1450','1451-1700','1701-2100','2101+'])
