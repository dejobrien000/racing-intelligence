"""Batch 15 (27 Nov 2026 brief s2): how does the production rating respond to poor runs, and do horses recover?
Production rating = Engine v2.3 national margin rating (engine/frames/national_c2.parquet, dyn_nat; Qld rows included).
Per run i of a horse: R = pre-race rating (kg), inn = how much better (+) or worse (-) than the rating the run was, relative to the field (kg),
A = R + inn = the run's performance on the rating scale. Next runs i+1..i+5 of the same horse (measured runs only).
Compared for every size of surprise:
  vs revised rating      : inn of the next run(s)  (0 = the revised rating was right on average)
  vs pre-run rating      : A(next) - R(i)          (did the horse get back to where it was rated before the poor run?)
  vs established level   : A(next) - L(i), L = mean A over the previous 3-5 measured runs (the horse's normal level)
  recovered share        : (mean A next 5 - A(i)) / (R(i) - A(i))  for poor runs
Overreaction test: next-run inn regressed on this run's inn (split negative/positive), with age, experience, rating uncertainty,
days since last run, days to the next run, prep stage; cluster-robust by horse. With an ideal update the slope is 0;
a negative slope on poor runs = the rating drops too far after them. Dropout bound: horses that never race again within 365 days.
Physical link (Qld 2022-26 and SA 2024-26 tracked runs, Batch 14 profiles): poor runs with and without an abnormal decline in finish.
Runs from 1 Jul 2023 (rating burn-in). 2024 and 2025-26 reported separately; neither is untouched for the physical items."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
OUT = {}
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'horse', 'date', 'state', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'age_n', 'r_ldays', 'r_firstup', 'f_lstarts', 'finish_pos', 'margin_l', 'class_label', 'distance_m'])
U['date'] = pd.to_datetime(U.date); U = U.sort_values(['horse', 'date', 'race_id']).reset_index(drop=True)
M = U[U.dyn_nat_inn.notna()].copy()                       # measured runs only (finished, margin known)
M['A'] = M.dyn_nat + M.dyn_nat_inn
g = M.groupby('horse')
for k in range(1, 6):
    M[f'R{k}'] = g.dyn_nat.shift(-k); M[f'inn{k}'] = g.dyn_nat_inn.shift(-k); M[f'A{k}'] = g.A.shift(-k); M[f'd{k}'] = g.date.shift(-k)
M['n_prior'] = g.cumcount()
M['L'] = g.A.transform(lambda s: s.shift().rolling(5, min_periods=3).mean())
M['gap_next'] = (M.d1 - M.date).dt.days; M['gap_prev'] = M.r_ldays
M['next3_inn'] = M[['inn1', 'inn2', 'inn3']].mean(axis=1); M['next5_inn'] = M[[f'inn{k}' for k in range(1, 6)]].mean(axis=1)
M['next3_A'] = M[['A1', 'A2', 'A3']].mean(axis=1); M['next5_A'] = M[[f'A{k}' for k in range(1, 6)]].mean(axis=1)
M['dR'] = M.R1 - M.dyn_nat
# races again within 365 days (any start, measured or not)
gu = U.groupby('horse'); U['d_next_any'] = gu.date.shift(-1)
M = M.merge(U[['race_id', 'horse', 'd_next_any']], on=['race_id', 'horse'], how='left')
M['raced_again'] = ((M.d_next_any - M.date).dt.days <= 365).astype(float)
last_date = U.date.max(); M = M[M.date <= last_date - pd.Timedelta(days=200)]          # leave time to race again
M = M[M.date >= '2023-07-01'].copy()
M['band'] = pd.cut(M.dyn_nat_inn, [-99, -10, -6, -3, 3, 6, 10, 99], labels=['10+ worse', '6-10 worse', '3-6 worse', 'normal (+-3)', '3-6 better', '6-10 better', '10+ better'])
M['period'] = np.where(M.date < '2025-01-01', '2023-24', '2025-26')
def tab(d):
    r = d.groupby('band', observed=True).agg(runs=('A', 'size'), raced_again_pct=('raced_again', lambda s: 100 * s.mean()), rating_change=('dR', 'mean'),
        next1_vs_revised=('inn1', 'mean'), next3_vs_revised=('next3_inn', 'mean'), next5_vs_revised=('next5_inn', 'mean'),
        next1_vs_prerun=('A1', lambda s: np.nan), )
    r['next1_vs_prerun'] = d.groupby('band', observed=True).apply(lambda x: (x.A1 - x.dyn_nat).mean())
    r['next5_vs_prerun'] = d.groupby('band', observed=True).apply(lambda x: (x.next5_A - x.dyn_nat).mean())
    r['next5_vs_established'] = d.groupby('band', observed=True).apply(lambda x: (x.next5_A - x.L).mean())
    r['this_run_vs_established'] = d.groupby('band', observed=True).apply(lambda x: (x.A - x.L).mean())
    r['recovered_share_5'] = d.groupby('band', observed=True).apply(lambda x: ((x.next5_A - x.A) / (x.dyn_nat - x.A)).median())
    return r.round(2)
for p, d in M.groupby('period'):
    t = tab(d); OUT[f'bands {p}'] = t.reset_index().to_dict('records'); print(p); print(t.to_string(), flush=True)
# baseline drift: what a 'normal' run is followed by (subtract to compare bands)
# overreaction regression
M['neg'] = M.dyn_nat_inn.clip(upper=0); M['pos'] = M.dyn_nat_inn.clip(lower=0)
M['exp'] = pd.cut(M.n_prior, [-1, 3, 10, 30, 999], labels=['0-3', '4-10', '11-30', '31+']).astype(str)
M['sdb'] = pd.qcut(M.dyn_nat_sd, 4, labels=['low unc', 'mid-low', 'mid-high', 'high unc']).astype(str)
M['age_b'] = M.age_n.clip(2, 8).fillna(4)
M['gp'] = np.log1p(M.gap_prev.clip(0, 400).fillna(400)); M['gn'] = np.log1p(M.gap_next.clip(0, 400))
reg = {}
for p, d in M.dropna(subset=['inn1']).groupby('period'):
    m = smf.ols('inn1 ~ neg + pos + C(age_b) + C(exp) + C(sdb) + gp + gn + r_firstup', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    reg[p] = {k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)] for k in ['neg', 'pos']}
    # by experience and uncertainty: slope on negative surprises
    for col in ['exp', 'sdb']:
        for lv, dd in d.groupby(col):
            mm = smf.ols('inn1 ~ neg + pos + gp + gn', dd).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(dd.horse)[0]})
            reg[p][f'neg slope | {col}={lv}'] = [round(mm.params['neg'], 3), round(mm.conf_int().loc['neg', 0], 3), round(mm.conf_int().loc['neg', 1], 3), int(mm.nobs)]
OUT['overreaction regression: next-run surprise per kg of this run surprise (neg part, pos part)'] = reg; print(json.dumps(reg), flush=True)
# what kind of poor run is over-penalised? big poor runs (inn <= -6): mean next-run surprise by circumstance, vs normal runs
P_ = M[M.dyn_nat_inn <= -6].copy(); N_ = M[M.dyn_nat_inn.abs() <= 3]
base = N_.inn1.mean()
def ci(s):
    s = s.dropna(); return [round(s.mean(), 2), round(s.mean() - 1.96 * s.std() / np.sqrt(len(s)), 2), round(s.mean() + 1.96 * s.std() / np.sqrt(len(s)), 2), int(len(s))]
sub = {'all big poor runs': P_.inn1,
       'beaten 10+ lengths': P_[P_.margin_l >= 10].inn1, 'beaten under 10 lengths': P_[P_.margin_l < 10].inn1,
       'first-up (60+ days)': P_[P_.r_firstup == 1].inn1, 'not first-up': P_[P_.r_firstup != 1].inn1,
       '0-3 runs held': P_[P_.exp == '0-3'].inn1, '4-10 runs held': P_[P_.exp == '4-10'].inn1, '11-30 runs held': P_[P_.exp == '11-30'].inn1, '31+ runs held': P_[P_.exp == '31+'].inn1,
       'age 2-3': P_[P_.age_n <= 3].inn1, 'age 4-5': P_[P_.age_n.between(4, 5)].inn1, 'age 6+': P_[P_.age_n >= 6].inn1,
       'next run within 21 days': P_[P_.gap_next <= 21].inn1, 'next run 22-60 days': P_[P_.gap_next.between(22, 60)].inn1, 'next run 61+ days': P_[P_.gap_next > 60].inn1}
OUT['next-run surprise after a big poor run (6+ kg worse than rated), by circumstance (mean, 95%, n); normal runs are followed by'] = {'normal runs baseline': round(base, 3), **{k: ci(v) for k, v in sub.items()}}
print(json.dumps(OUT['next-run surprise after a big poor run (6+ kg worse than rated), by circumstance (mean, 95%, n); normal runs are followed by']), flush=True)
# physical decline link (tracked Qld + SA): same-size poor runs with / without an abnormal decline in finish (Batch 14 follow-up definition)
P = pd.read_parquet('/home/claude/b14/profiles.parquet', columns=['state', 'nat_race', 'horse', 'meeting_date', 'slope', 'profile', 'performance_concern', 'interference', 'wide_no_cover', 'vet_finding', 'report_held'])
P = P.dropna(subset=['slope']).sort_values(['horse', 'meeting_date']).copy(); gp_ = P.groupby('horse'); cnt = gp_.cumcount()
P['usual'] = (gp_.slope.cumsum() - P.slope) / (cnt + 3.0); P['decl'] = np.where(cnt >= 3, ((P.slope - P.usual) / np.where(P.state == 'QLD', 0.466, 0.413)) < -1.5, np.nan)
P['fade'] = P.profile.isin(['Progressive fade', 'Late fade']).astype(float)
T = M.merge(P.rename(columns={'nat_race': 'race_id'})[['race_id', 'horse', 'decl', 'fade', 'profile', 'performance_concern', 'interference', 'vet_finding']], on=['race_id', 'horse'], how='inner')
T = T[T.decl.notna()]
phys = {}
for nm, d in [('all tracked', T), ('tracked poor runs (3+ kg worse)', T[T.dyn_nat_inn <= -3]), ('tracked big poor runs (6+ kg worse)', T[T.dyn_nat_inn <= -6])]:
    for flag in ['decl', 'fade']:
        a, b = d[d[flag] == 1], d[d[flag] == 0]
        phys[f'{nm} | {flag}=1 vs 0'] = {'n': [int(len(a)), int(len(b))], 'this run surprise': [round(a.dyn_nat_inn.mean(), 2), round(b.dyn_nat_inn.mean(), 2)],
            'rating change': [round(a.dR.mean(), 2), round(b.dR.mean(), 2)], 'next1 vs revised': [ci(a.inn1), ci(b.inn1)], 'next5 vs revised': [ci(a.next5_inn), ci(b.next5_inn)],
            'next5 vs pre-run rating': [ci(a.next5_A - a.dyn_nat), ci(b.next5_A - b.dyn_nat)], 'next5 vs established level': [ci(a.next5_A - a.L), ci(b.next5_A - b.L)],
            'raced again within 365 d %': [round(100 * a.raced_again.mean(), 1), round(100 * b.raced_again.mean(), 1)]}
# regression: does the physical flag add to the size of the surprise in predicting the bounce?
d = T.dropna(subset=['inn1'])
m = smf.ols('inn1 ~ neg + pos + decl + fade + C(state) + gp + gn + C(exp)', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
phys['regression next1 ~ surprise + decline + fade (+controls)'] = {k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)] for k in ['neg', 'pos', 'decl', 'fade']}
m2 = smf.ols('inn1 ~ neg + pos + decl * neg + C(state) + gp + gn + C(exp)', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
phys['regression with decline x size of poor run'] = {k: [round(m2.params[k], 3), round(m2.conf_int().loc[k, 0], 3), round(m2.conf_int().loc[k, 1], 3)] for k in ['neg', 'decl', 'decl:neg']}
OUT['physical decline vs same-size poor runs (tracked Qld/SA, production v2.3 rating)'] = phys; print(json.dumps(phys, default=str), flush=True)
json.dump(OUT, open('batch15/out_responsiveness.json', 'w'), indent=1, default=str)
M[['race_id', 'horse', 'date', 'state', 'dyn_nat', 'dyn_nat_inn', 'inn1', 'next5_inn', 'dR', 'L', 'A', 'next5_A', 'raced_again', 'n_prior', 'age_n']].to_parquet('/home/claude/b14/b15_resp.parquet')
