"""Leakage guard for the jockey/trainer finding: rebuild j_surp / t_surp from rides at least 7 (and 28) days before the race
instead of 1 day, and re-test them on top of the frozen NSW/Vic model (same design as screen 2). If the effect were
leaking from same-week information it would collapse; a real effect barely moves."""
import numpy as np, pandas as pd, json, hier_tools as H
from engine import evaltools as E
U = pd.read_parquet('engine/frames/national.parquet').sort_values(['date', 'race']).reset_index(drop=True)
def lagged(key, lag, k=50):
    v = U.dyn_nat_inn; d = pd.DataFrame({'g': U[key], 'date': U.date, 'v': v.fillna(0.0), 'c': v.notna().astype(float)}).dropna(subset=['g'])
    day = d.groupby(['g', 'date'])[['v', 'c']].sum().reset_index().sort_values('date'); day[['sv', 'sc']] = day.groupby('g')[['v', 'c']].cumsum().values
    q = pd.DataFrame({'g': U[key], 'date': U.date - pd.Timedelta(days=lag), 'i': U.index}).dropna(subset=['g']).sort_values('date')
    m = pd.merge_asof(q, day[['g', 'date', 'sv', 'sc']].sort_values('date'), on='date', by='g', allow_exact_matches=False)   # strictly before (race date - lag)
    out = pd.Series(np.nan, index=U.index); out.loc[m.i.values] = (m.sv.fillna(0) / (m.sc.fillna(0) + k)).values; return out
for lag in [1, 7, 28]:
    U[f'j{lag}'] = lagged('jkey', lag); U[f't{lag}'] = lagged('tkey', lag)
print('check lag-1 rebuild equals the frame (corr):', round(U[['j1', 'j_surp']].corr().iloc[0, 1], 4), round(U[['t1', 't_surp']].corr().iloc[0, 1], 4))
x = E.nat_frame(U); mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
x['offset'] = sum(C2[c] * ((x[c].astype(float) - x.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0) for c in C2).values
cols = [f'{p}{l}' for p in 'jt' for l in (1, 7, 28)]; x = E.zcols(x, cols); dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']
for c in cols:
    b = H.fit(H.Races(dev.race_id.values, dev.win.values, dev.offset.values, dev[[c + '_z']].values), np.array([1e-6]))
    Re = H.Races(ev.race_id.values, ev.win.values, ev.offset.values, ev[[c + '_z']].values)
    print(c, 'coef', round(float(b[0]), 4), 'confirmation gain/race', round(float((Re.loglik_per_race(b) - Re.loglik_per_race(np.zeros(1))).mean()), 5))
