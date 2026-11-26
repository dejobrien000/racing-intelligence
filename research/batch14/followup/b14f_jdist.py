"""Batch 14 follow-up s6: is jockey distance specialisation a genuine small contribution or noise? All states, national v3 frame.
Outcome: rating surprise (kg, race-centred). Everything 'prior' uses strictly earlier dates. Specialists are chosen on data before 2025 only.
1) persistence by year: each jockey's prior staying-minus-sprint (before the year) vs what happened in the year (40+ rides per band in it)
2) optimal shrinkage: true spread of band-specific jockey form from split-half covariance; prior weight k = noise per ride / true variance
3) pre-specified specialists (top 10% |staying - sprint| on pre-2025 data, 80+ rides in each band): is the effect larger for them in 2025-26?
4) continuous vs bands: six finer distance groups with neighbour smoothing vs the three bands, same shrinkage
5) relation to rider momentum timing and late retention (Qld tracking riders)
Writes the optimal-shrinkage j_spec and t_spec into the Engine v2.3 harness feature file (f_C2J) and a frame variant (C2D) in which the
existing jockey assessment j_surp is replaced by j_surp + j_spec (one input, same family) for the engine tests."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
def cfit(form, f, key='jkey'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
def co(m, k, nd=3): return (round(m.params[k], nd), round(m.conf_int().loc[k, 0], nd), round(m.conf_int().loc[k, 1], nd)) if k in m.params else None
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'date', 'race_no', 'state', 'distance_m', 'jkey', 'tkey', 'dyn_nat', 'dyn_nat_inn', 'j_surp', 'j_n'])
V = V[V.dyn_nat_inn.notna() & V.jkey.notna()].copy(); V['date'] = pd.to_datetime(V.date); V['yr'] = V.date.dt.year
V['band'] = pd.cut(V.distance_m.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
V['band6'] = pd.cut(V.distance_m.astype(float), [0, 1050, 1250, 1450, 1650, 2050, 5000], labels=['b1', 'b2', 'b3', 'b4', 'b5', 'b6']).astype(str)
V['rband'] = pd.qcut(V.dyn_nat, 5, labels=False, duplicates='drop').astype(str); V = V.sort_values(['date', 'race_no']).reset_index(drop=True)
OUT = {}; sig2 = V.dyn_nat_inn.var()
# 1) persistence by year
py = {}
for Y in [2024, 2025, 2026]:
    pre = V[V.date < f'{Y}-01-01']; cur = V[V.yr == Y]
    def spec(d, nmin):
        t = d.groupby(['jkey', 'band']).dyn_nat_inn.agg(['mean', 'size']).unstack('band'); t = t[(t['size'][['sprint', 'staying']] >= nmin).all(axis=1)]
        return (t['mean']['staying'] - t['mean']['sprint'])
    a, b = spec(pre, 40), spec(cur, 40); j = a.index.intersection(b.index); py[str(Y)] = (round(a[j].corr(b[j]), 3), len(j))
OUT['1 persistence: prior staying-minus-sprint vs that year (r, jockeys)'] = py
# 2) optimal shrinkage from split-half covariance (rides before 2025)
A = V[V.date < '2025-01-01'].copy(); A['half'] = A.groupby(['jkey', 'band']).cumcount() % 2
t = A.groupby(['jkey', 'band', 'half']).dyn_nat_inn.agg(['mean', 'size']).reset_index()
jm = A.groupby(['jkey', 'half']).dyn_nat_inn.mean().rename('jall').reset_index(); t = t.merge(jm, on=['jkey', 'half']); t['dev'] = t['mean'] - t.jall
w = t.pivot_table(index=['jkey', 'band'], columns='half', values=['dev', 'size']).dropna(); w = w[(w['size'] >= 40).all(axis=1)]
true_var = np.cov(w['dev'][0], w['dev'][1])[0, 1]; k_opt = sig2 / true_var if true_var > 0 else np.inf
OUT['2 shrinkage: true sd of band-specific jockey form (kg), noise sd per ride, optimal prior weight (rides) vs 60 used'] = [round(np.sqrt(max(true_var, 0)), 3), round(np.sqrt(sig2), 2), round(k_opt, 0)]
# prior band and overall (strictly earlier dates) with a given k
def prior(key, grp, k):
    day = V.groupby([key, grp, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    day['cs'] = day.groupby([key, grp])['sum'].cumsum() - day['sum']; day['cc'] = day.groupby([key, grp])['count'].cumsum() - day['count']
    al = V.groupby([key, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date'); al['as'] = al.groupby(key)['sum'].cumsum() - al['sum']; al['ac'] = al.groupby(key)['count'].cumsum() - al['count']
    X = V[[key, grp, 'date']].merge(day[[key, grp, 'date', 'cs', 'cc']], on=[key, grp, 'date'], how='left').merge(al[[key, 'date', 'as', 'ac']], on=[key, 'date'], how='left')
    return (X['cs'] / (X['cc'] + k) - X['as'] / (X['ac'] + k)).fillna(0).values, X['cc'].fillna(0).values
kk = int(min(max(k_opt, 20), 2000))
V['j_spec60'], V['j_bn'] = prior('jkey', 'band', 60); V['j_spec_opt'], _ = prior('jkey', 'band', kk); V['t_spec_opt'], _ = prior('tkey', 'band', kk)
V['j_spec6'], _ = prior('jkey', 'band6', kk)
e = V[(V.j_n >= 100) & (V.date >= '2023-07-01') & V.j_surp.notna()].copy(); e['nb'] = e.groupby(['jkey', 'band']).cumcount()
res = {}
for nm in ['j_spec60', 'j_spec_opt', 'j_spec6']:
    m = cfit(f'dyn_nat_inn ~ j_surp + {nm} + t_spec_opt + C(band) + C(rband) + C(state)', e)
    res[nm] = {'coef (kg per kg)': co(m, nm), 'sd of input kg': round(e[nm].std(), 3), 'kg per sd': round(m.params[nm] * e[nm].std(), 3), 'R2': round(m.rsquared, 5)}
OUT['2/4 shrinkage and representation (2023-26, beyond j_surp and trainer distance form)'] = res
# 3) pre-specified specialists: chosen on pre-2025 data only
P = V[V.date < '2025-01-01'].groupby(['jkey', 'band']).dyn_nat_inn.agg(['sum', 'count']).unstack('band')
ok = (P['count'][['sprint', 'staying']] >= 80).all(axis=1); P = P[ok]
sh = lambda b: P['sum'][b] / (P['count'][b] + kk); spec_pre = (sh('staying') - sh('sprint')); thr = spec_pre.abs().quantile(0.9); specialists = set(spec_pre[spec_pre.abs() >= thr].index)
f = V[(V.date >= '2025-01-01') & V.j_surp.notna() & (V.j_n >= 100)].copy(); f['specialist'] = f.jkey.isin(specialists).astype(int)
m = cfit('dyn_nat_inn ~ j_surp + j_spec_opt * specialist + t_spec_opt + C(band) + C(rband) + C(state)', f)
OUT['3 pre-specified specialists (top 10% on pre-2025 data), 2025-26: j_spec effect for others, extra for specialists'] = {'others': co(m, 'j_spec_opt'), 'specialists extra': co(m, 'j_spec_opt:specialist'),
    'n specialists': len(specialists), 'n eligible jockeys': int(ok.sum()), 'rides by specialists 2025-26': int(f.specialist.sum())}
# 5) relation to rider timing and late retention (Qld tracking riders)
try:
    J = pd.read_csv('/home/claude/racing-intelligence/research/batch14/followup/rider_momentum_profiles.csv').set_index('jk')
    s_all = V.groupby(['jkey', 'band']).dyn_nat_inn.agg(['sum', 'count']).unstack('band'); s_all = s_all[(s_all['count'][['sprint', 'staying']] >= 40).all(axis=1)]
    spec_all = s_all['sum']['staying'] / (s_all['count']['staying'] + kk) - s_all['sum']['sprint'] / (s_all['count']['sprint'] + kk)
    jj = J.join(spec_all.rename('spec'), how='inner')
    OUT['5 riders: staying-minus-sprint form vs momentum timing and late retention (r, riders)'] = {'timing': round(jj.spec.corr(jj.timing_wh_shrunk), 3), 'hold': round(jj.spec.corr(jj.hold_wh_shrunk), 3), 'riders': len(jj)}
except Exception as ex: OUT['5'] = str(ex)[:100]
print(json.dumps(OUT, default=str), flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/followup/out_jdist.json', 'w'), indent=1, default=str)
# engine-test inputs on the Engine v2.3 (C2) frame's own surprise, same optimal shrinkage
U = pd.read_parquet('/tmp/cand/frames/C2_national.parquet'); U['date_'] = pd.to_datetime(U.date)
W = U[['race_id', 'horse', 'date_', 'distance_m', 'jkey', 'tkey', 'dyn_nat_inn']].rename(columns={'date_': 'date'}).copy()
W['band'] = pd.cut(W.distance_m.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
V = W[W.dyn_nat_inn.notna()]
for key, nm in [('jkey', 'j_spec'), ('tkey', 't_spec')]:
    v = V[V[key].notna()]; day = v.groupby([key, 'band', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    day['cs'] = day.groupby([key, 'band'])['sum'].cumsum() - day['sum']; day['cc'] = day.groupby([key, 'band'])['count'].cumsum() - day['count']
    al = v.groupby([key, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date'); al['as'] = al.groupby(key)['sum'].cumsum() - al['sum']; al['ac'] = al.groupby(key)['count'].cumsum() - al['count']
    X = W[[key, 'band', 'date']].merge(day[[key, 'band', 'date', 'cs', 'cc']], on=[key, 'band', 'date'], how='left').merge(al[[key, 'date', 'as', 'ac']], on=[key, 'date'], how='left')
    W[nm] = (X['cs'] / (X['cc'] + kk) - X['as'] / (X['ac'] + kk)).fillna(0).values
F = pd.read_parquet('/tmp/cand/f_C2/b10/out/feat.parquet'); n0 = len(F)
F = F.merge(W[['race_id', 'horse', 'j_spec', 't_spec']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left'); assert len(F) == n0
F[['j_spec', 't_spec']] = F[['j_spec', 't_spec']].fillna(0); F.to_parquet('/tmp/cand/f_C2J/b10/out/feat.parquet')
U = U.merge(W[['race_id', 'horse', 'j_spec']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
U['j_surp'] = U.j_surp + U.j_spec.fillna(0).where(U.j_surp.notna()); U = U.drop(columns=['j_spec', 'date_'])
U.to_parquet('/tmp/cand/frames/C2D_national.parquet'); print('engine inputs written: k =', kk)
