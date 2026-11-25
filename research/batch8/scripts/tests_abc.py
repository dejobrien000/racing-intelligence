import numpy as np, pandas as pd, statsmodels.formula.api as smf
pd.set_option('display.width', 220)
E = pd.read_parquet('/tmp/exp/rt/events.parquet')
E = E[E.dyn_nat_inn.notna() & E.nx_dyn_nat_inn.notna() & E.gap_next.between(7, 120) & (E.start_no >= 2)].copy()
E['Y'] = E.nx_dyn_nat_inn; E['half'] = np.where(E.nx_date < '2025-01-01', 'A 2022-24', 'B 2025-26')
E['carried'] = E.Y + E.K * E.dyn_nat_inn          # next performance relative to the rating BEFORE this run's update
def summ(d, by):
    r = d.groupby(by, observed=True).agg(runs=('Y', 'size'), horses=('horse', 'nunique'), mean_surprise=('dyn_nat_inn', 'mean'), K=('K', 'mean'), Y=('Y', 'mean'), Ysd=('Y', 'std')).reset_index()
    r['Y_se'] = r.Ysd / np.sqrt(r.runs); r['persist'] = (r.Y + r.K * r.mean_surprise) / r.mean_surprise
    return r.drop(columns='Ysd').round(3)
print('ALL: overall slope of carried on surprise (share of a surprise that shows up again next start)')
for h, d in E.groupby('half'):
    m = smf.ols('carried ~ dyn_nat_inn', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    print(h, 'runs', len(d), 'persistence', round(m.params['dyn_nat_inn'], 3), '+/-', round(1.96 * m.bse['dyn_nat_inn'], 3), '| mean K (what the rating assumes)', round(d.K.mean(), 3))
# ---------- T1: big jump, sudden vs gradual ----------
B = E[E.dyn_nat_inn >= 4].copy()
B['pattern'] = np.select([(B.inn_m1 > 1) & (B.inn_m2 > 1), (B.inn_m1 <= 0) & (B.inn_m2 <= 0)], ['after two rises (gradual)', 'out of the blue (sudden)'], 'mixed')
B['stage'] = np.select([B.prep_run <= 2, B.prep_run <= 4], ['1st-2nd up', '3rd-4th up'], '5th+ up')
print('\nT1 big upside surprise (+4 kg or more): next-start surprise Y and persistence')
print(summ(B, ['pattern', 'half']).to_string(index=False))
print(summ(B, ['stage', 'half']).to_string(index=False))
B['exp'] = pd.cut(B.start_no, [1, 5, 12, 25, 999], labels=['3-5 starts', '6-12', '13-25', '26+'])
print(summ(B, ['exp', 'half']).to_string(index=False))
# downside too
D = E[E.dyn_nat_inn <= -4].copy(); D['pattern'] = np.select([(D.inn_m1 < -1) & (D.inn_m2 < -1), (D.inn_m1 >= 0) & (D.inn_m2 >= 0)], ['after two falls', 'out of the blue'], 'mixed')
print('\nT1b big downside surprise (-4 kg or worse)'); print(summ(D, ['pattern', 'half']).to_string(index=False))
# ---------- T2: proven ceiling vs current ----------
N = E.copy(); N['below_peak'] = N.nx_peak - N.nx_dyn_nat   # at the next start: best rating so far minus current rating
N['band'] = pd.cut(N.below_peak, [-0.01, 1, 3, 6, 10, 99], labels=['at peak (<1kg)', '1-3 kg below', '3-6 kg below', '6-10 kg below', '10+ kg below'])
N['age_b'] = pd.cut(N.age_n, [0, 4, 6, 20], labels=['2-4yo', '5-6yo', '7yo+'])
print('\nT2 proven ceiling: next-start surprise by how far the horse sits below its best rating')
print(summ(N, ['band', 'half']).to_string(index=False))
print(summ(N[N.half == 'B 2025-26'], ['band', 'age_b']).to_string(index=False))
# ---------- T3: age x experience ----------
X = E.copy(); X['age_b'] = pd.cut(X.age_n, [0, 3, 4, 5, 6, 7, 20], labels=['2-3', '4', '5', '6', '7', '8+'])
X['starts_b'] = pd.cut(X.start_no, [1, 8, 20, 40, 999], labels=['3-8', '9-20', '21-40', '41+'])
print('\nT3 age x career starts (in our history): next-start surprise Y (kg)')
for h, d in X.groupby('half'):
    t = d.pivot_table(index='age_b', columns='starts_b', values='Y', aggfunc='mean', observed=True).round(2)
    n = d.pivot_table(index='age_b', columns='starts_b', values='Y', aggfunc='size', observed=True)
    print(h); print(t.to_string()); print(n.to_string())
E.to_parquet('/tmp/exp/rt/E.parquet')
