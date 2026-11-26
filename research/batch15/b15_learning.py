"""Batch 15 (brief s7): should the rating's learning speed (how far one run moves it) depend on the horse's situation?
Production update: rating moves by K x surprise, K = var / (var + 4.5^2), var growing with time off and shrinking with runs (Engine v2.3).
If the move were right, the NEXT run's surprise would not depend on this run's surprise. So, within each group, next-run surprise is
regressed on this run's surprise, separately for good (pos) and poor (neg) runs:
  slope on pos > 0  -> good runs should move the rating further (under-reaction);   slope on neg < 0 -> poor runs move it too far.
Implied best multiplier of the move = (K + slope) / K (K = the group's average gain).
Groups (all pre-race information): career experience held; rating uncertainty; established ability (rating level, quintiles within
state-year); recent consistency (sd of the last 5 surprises); repeated direction (the previous run's surprise had the same sign);
historical completeness (first run held came within the first 6 months of the database at age 4+ = history probably truncated);
and margin size of this run (heavy defeats). Runs Jul 2023 - May 2026 (next run observed), all states, production v2.3 rating."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'horse', 'date', 'state', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'age_n', 'margin_l', 'r_ldays'])
U['date'] = pd.to_datetime(U.date); U = U.sort_values(['horse', 'date', 'race_id']).reset_index(drop=True)
first = U.groupby('horse').date.transform('min'); first_age = U.groupby('horse').age_n.transform('first')
U['truncated'] = ((first < U.date.min() + pd.Timedelta(days=183)) & (first_age >= 4)).astype(int)
M = U[U.dyn_nat_inn.notna()].copy(); g = M.groupby('horse')
M['inn1'] = g.dyn_nat_inn.shift(-1); M['n_prior'] = g.cumcount(); M['prev_inn'] = g.dyn_nat_inn.shift(1)
M['cons'] = g.dyn_nat_inn.transform(lambda s: s.shift().rolling(5, min_periods=3).std())
M = M[(M.date >= '2023-07-01') & M.inn1.notna()].copy()
M['K'] = M.dyn_nat_sd ** 2 / (M.dyn_nat_sd ** 2 + 4.5 ** 2)
M['neg'] = M.dyn_nat_inn.clip(upper=0); M['pos'] = M.dyn_nat_inn.clip(lower=0)
M['yr'] = M.date.dt.year
M['ability'] = M.groupby(['state', 'yr']).dyn_nat.transform(lambda s: pd.qcut(s.rank(method='first'), 5, labels=['lowest', 'low', 'middle', 'high', 'highest'])).astype(str)
G = {'experience held': pd.cut(M.n_prior, [-1, 3, 10, 30, 999], labels=['0-3 runs', '4-10', '11-30', '31+']).astype(str),
     'rating uncertainty': pd.qcut(M.dyn_nat_sd, 4, labels=['lowest', 'low', 'high', 'highest']).astype(str),
     'established ability (rating level)': M.ability,
     'recent consistency (sd of last 5 surprises)': pd.qcut(M.cons, 3, labels=['consistent', 'middling', 'erratic']).astype(str).where(M.cons.notna(), 'under 3 runs'),
     'previous run went the same way': np.where(M.prev_inn.isna(), 'no previous run', np.where(np.sign(M.prev_inn) == np.sign(M.dyn_nat_inn), 'same direction (repeat)', 'opposite direction')),
     'history completeness': np.where(M.truncated == 1, 'history probably truncated', 'full history held'),
     'beaten margin this run': pd.cut(M.margin_l.fillna(0), [-1, 3, 10, 25, 999], labels=['under 3 L', '3-10 L', '10-25 L', '25 L+']).astype(str),
     'age': pd.cut(M.age_n, [0, 3, 5, 20], labels=['2-3', '4-5', '6+']).astype(str)}
OUT = {}
def fit(d):
    m = smf.ols('inn1 ~ neg + pos', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    K = d.K.mean(); f = lambda k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)]
    return {'runs': int(m.nobs), 'avg gain K': round(K, 3), 'slope poor runs': f('neg'), 'slope good runs': f('pos'),
            'implied multiplier poor runs': round((K + m.params['neg']) / K, 2), 'implied multiplier good runs': round((K + m.params['pos']) / K, 2)}
for per, d0 in [('2023-24', M[M.yr <= 2024]), ('2025-26', M[M.yr >= 2025])]:
    r = {'all runs': fit(d0)}
    for gname, gser in G.items():
        gs = pd.Series(gser, index=M.index).loc[d0.index]
        r[gname] = {lv: fit(dd) for lv, dd in d0.groupby(gs) if len(dd) > 3000}
    OUT[per] = r
    print(per, json.dumps(r)[:4000], flush=True)
json.dump(OUT, open('batch15/out_learning.json', 'w'), indent=1)
