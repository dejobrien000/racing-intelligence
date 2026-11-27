"""Batch 16 C13 / C14 / C16 on the Engine v2.3 rating frame (research only; point in time; no prices).
Performance figure: perf = pre-race rating + surprise (kg); surprise = this run relative to the field minus the rating relative to the
field. Next-run surprise is the test of whether a rating moved the right amount.
C13 race strength: (a) do runners from the same race share their next-run error (a sign the race's level was mis-set)? (b) does that
shared error grow with field uncertainty (lightly raced, uncertain ratings)? (c) does one extreme defeat inflate everyone else's credit?
(d) several lightly raced horses improving at once.
C14 ceiling vs repeatable: earlier best, second best, typical (median of last 5), how many runs near the best, how isolated the best is.
C16 consistency: is horse-specific variability persistent (split halves, periods), asymmetric, and does it change how far a surprise
should move the rating?
Usage (from research/): python3 batch16/c13_14_16.py [frame] -> batch16/out_c13_14_16.json"""
import sys, json, numpy as np, pandas as pd, statsmodels.formula.api as smf
FR = sys.argv[1] if len(sys.argv) > 1 else 'engine/frames/national_c2.parquet'
U = pd.read_parquet(FR, columns=['horse', 'date', 'race', 'state', 'field', 'class_label', 'dyn_nat', 'dyn_nat_sd', 'dyn_nat_inn', 'margin_l'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
U['n_prior'] = g.cumcount(); U['nxt'] = g.dyn_nat_inn.shift(-1); U['perf'] = U.dyn_nat + U.dyn_nat_inn
OUT = {}
cl = lambda m, k: [round(float(m.params[k]), 3), round(float(m.conf_int().loc[k, 0]), 3), round(float(m.conf_int().loc[k, 1]), 3)]
E = U[(U.date >= '2024-01-01') & U.dyn_nat_inn.notna()].copy()
# ---------- C13 ----------
R = E.groupby('race').agg(n=('nxt', 'count'), mnxt=('nxt', 'mean'), vnxt=('nxt', 'var'), unc=('dyn_nat_sd', 'mean'), light=('n_prior', lambda s: float((s <= 3).mean())),
                          spread=('dyn_nat', 'std'), field=('field', 'first'), maiden=('class_label', lambda s: s.iloc[0] == 'Maiden'), minn=('dyn_nat_inn', 'min'))
R = R[R.n >= 5]
within = float((R.vnxt / R.n).mean()); between = float(R.mnxt.var())
OUT['c13_shared_next_run_error'] = {'races': int(len(R)), 'variance_of_race_mean_next_surprise': round(between, 3), 'expected_if_independent': round(within, 3),
                                    'shared_component_kg_sd': round(float(np.sqrt(max(between - within, 0))), 3)}
R['uncq'] = pd.qcut(R.unc, 4, labels=['most certain', 'q2', 'q3', 'least certain']).astype(str)
OUT['c13_shared_error_by_field_uncertainty'] = {k: {'races': int(len(v)), 'shared_sd_kg': round(float(np.sqrt(max(v.mnxt.var() - (v.vnxt / v.n).mean(), 0))), 3), 'mean_next': round(float(v.mnxt.mean()), 3)} for k, v in R.groupby('uncq')}
OUT['c13_shared_error_maiden_vs_other'] = {('maiden' if k else 'other'): {'races': int(len(v)), 'shared_sd_kg': round(float(np.sqrt(max(v.mnxt.var() - (v.vnxt / v.n).mean(), 0))), 3)} for k, v in R.groupby('maiden')}
# (c) an extreme defeat in the race: next-run surprise of the OTHER runners
E['race_min'] = E.race.map(R.minn); E['own_extreme'] = E.dyn_nat_inn <= -15
others = E[~E.own_extreme & E.nxt.notna()]
others['race_has_extreme'] = others.race_min <= -15
m = smf.ols('nxt ~ race_has_extreme + dyn_nat_inn + C(state)', others).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(others.horse)[0]})
OUT['c13_others_next_surprise_when_race_had_a_15kg_plus_defeat'] = cl(m, 'race_has_extreme[T.True]'); OUT['c13_races_with_extreme_defeat_share'] = round(float((R.minn <= -15).mean()), 3)
# (d) several lightly raced horses improving at once: >=3 runners with <=3 prior runs and surprise > +5
E['lr_up'] = (E.n_prior <= 3) & (E.dyn_nat_inn > 5); k3 = E.groupby('race').lr_up.transform('sum') >= 3
oth = E[~E.lr_up & E.nxt.notna()].assign(multi=k3[~E.lr_up & E.nxt.notna()])
m = smf.ols('nxt ~ multi + dyn_nat_inn + C(state)', oth).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(oth.horse)[0]})
OUT['c13_others_next_surprise_when_3plus_lightly_raced_improved'] = cl(m, 'multi[T.True]')
OUT['c13_lightly_raced_improvers_own_next_surprise'] = round(float(E[E.lr_up].nxt.mean()), 3)
# ---------- C14 ----------
top1 = np.full(len(U), np.nan); top2 = top1.copy(); near = top1.copy(); since = top1.copy()
for h, idx in U.groupby('horse').indices.items():
    p = U.perf.values[idx]
    for j in range(1, len(idx)):
        q = p[:j]; q = q[~np.isnan(q)]
        if len(q) == 0: continue
        srt = np.sort(q); top1[idx[j]] = srt[-1]; top2[idx[j]] = srt[-2] if len(srt) >= 2 else np.nan
        near[idx[j]] = float((q >= srt[-1] - 3).sum()); pj = p[:j]; since[idx[j]] = float(j - 1 - np.nanargmax(pj))
U['top1'] = top1; U['top2'] = top2; U['near_top'] = near; U['since_top'] = since
U['typ'] = g.perf.transform(lambda s: s.shift().rolling(5, min_periods=3).median())
C = U[(U.date >= '2024-01-01') & U.dyn_nat_inn.notna() & (U.n_prior >= 5)].copy()
for c in ['top1', 'top2', 'typ']: C[c + '_gap'] = C[c] - C.dyn_nat
C['isolated'] = C.top1 - C.top2; C['logn'] = np.log(C.n_prior)
for per, d in [('2024', C[C.date < '2025-01-01']), ('2025-26', C[C.date >= '2025-01-01'])]:
    d = d.dropna(subset=['top1_gap', 'top2_gap', 'typ_gap', 'isolated', 'near_top', 'since_top'])
    m = smf.ols('dyn_nat_inn ~ top2_gap + isolated + typ_gap + near_top + np.log1p(since_top) + logn', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    OUT[f'c14_ceiling_{per}'] = {k: cl(m, k) for k in ['top2_gap', 'isolated', 'typ_gap', 'near_top', 'np.log1p(since_top)', 'logn']}; OUT[f'c14_ceiling_{per}']['n'] = int(m.nobs)
# example shapes: same average, different spread (last 5 runs)
C['m5'] = C.groupby('horse').perf.transform(lambda s: s.shift().rolling(5, min_periods=5).mean()); C['s5'] = C.groupby('horse').perf.transform(lambda s: s.shift().rolling(5, min_periods=5).std())
cc = C.dropna(subset=['m5', 's5']); cc['shape'] = pd.qcut(cc.s5, 3, labels=['steady (like B)', 'middle', 'up-and-down (like A)']).astype(str)
cc['vs_avg'] = cc.perf - cc.m5
OUT['c14_next_run_vs_last5_average_by_spread'] = {k: {'runs': int(len(v)), 'perf_minus_last5_avg': round(float(v.vs_avg.mean()), 2), 'surprise_vs_rating': round(float(v.dyn_nat_inn.mean()), 2), 'sd_of_next_perf_around_avg': round(float(v.vs_avg.std()), 2)} for k, v in cc.groupby('shape')}
# ---------- C16 ----------
H = U[U.dyn_nat_inn.notna()].copy(); H['k'] = H.groupby('horse').cumcount()
a = H[H.k % 2 == 0].groupby('horse').dyn_nat_inn.agg(['std', 'count', 'skew']); b = H[H.k % 2 == 1].groupby('horse').dyn_nat_inn.agg(['std', 'count', 'skew'])
j = a.join(b, lsuffix='_odd', rsuffix='_even'); j = j[(j.count_odd >= 8) & (j.count_even >= 8)]
OUT['c16_split_half_reliability'] = {'horses': int(len(j)), 'sd_corr': round(float(j.std_odd.corr(j.std_even)), 3), 'skew_corr': round(float(j.skew_odd.corr(j.skew_even)), 3)}
p1 = H[H.date < '2024-07-01'].groupby('horse').dyn_nat_inn.agg(['std', 'count', 'skew']); p2 = H[H.date >= '2025-01-01'].groupby('horse').dyn_nat_inn.agg(['std', 'count', 'skew'])
jj = p1.join(p2, lsuffix='_early', rsuffix='_late'); jj = jj[(jj.count_early >= 8) & (jj.count_late >= 8)]
OUT['c16_period_persistence'] = {'horses': int(len(jj)), 'sd_corr_2022_24H1_vs_2025_26': round(float(jj.std_early.corr(jj.std_late)), 3), 'skew_corr': round(float(jj.skew_early.corr(jj.skew_late)), 3)}
# does a big surprise from an inconsistent horse persist less? (prior sd from earlier runs only)
U['psd'] = g.dyn_nat_inn.transform(lambda s: s.shift().expanding(8).std())
B = U[(U.date >= '2024-01-01') & U.psd.notna() & U.nxt.notna() & (U.dyn_nat_inn.abs() >= 6)].copy()
B['sdq'] = pd.qcut(B.psd, 3, labels=['consistent', 'middle', 'inconsistent']).astype(str); B['dir'] = np.where(B.dyn_nat_inn > 0, 'big run (+6 kg or more)', 'big defeat (-6 kg or worse)')
B['lnp'] = np.log1p(B.n_prior); B['big_run'] = (B.dyn_nat_inn > 0).astype(int)
B['incons'] = (B.sdq == 'inconsistent').astype(int); B['midd'] = (B.sdq == 'middle').astype(int)
mm = smf.ols('nxt ~ incons * big_run + midd * big_run + lnp + dyn_nat_inn', B).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(B.horse)[0]})
OUT['c16_controlled_inconsistent_vs_consistent'] = {'after big defeat': cl(mm, 'incons'), 'extra after big run': cl(mm, 'incons:big_run')}
OUT['c16_next_surprise_after_big_surprise_by_consistency'] = {f'{d} | {q}': [int(len(v)), round(float(v.nxt.mean()), 2), round(float(v.nxt.std() / np.sqrt(len(v))), 2)] for (d, q), v in B.groupby(['dir', 'sdq'])}
# uncertainty about ability vs variability: rating sd (Kalman) vs own-performance sd, for lightly raced vs established
V = U[(U.date >= '2024-01-01') & U.psd.notna()]
OUT['c16_rating_uncertainty_vs_variability_corr'] = round(float(V.dyn_nat_sd.corr(V.psd)), 3)
json.dump(OUT, open(sys.argv[2] if len(sys.argv) > 2 else 'batch16/out_c13_14_16.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:6000])
