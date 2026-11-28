"""Batch 26 Part 5: long-break returners and individual fresh performance. RESEARCH ONLY - no deduction, no production change.
Batch 25 definition (reproduced exactly): a run after a break of 120+ days (gap = days since the horse's previous held run), by a
horse with 3+ held runs before it, national states (not Qld), surprise = the production rating's race-relative surprise (kg,
dyn_nat_inn in the Engine v2.3 frame; the Batch 25 re-run matched it exactly). Batch 25 mean: -0.82 kg.
Nothing here infers injury or fitness from the gap; gaps are just time between held runs (unheld runs are possible: see Part 1).
Questions: already captured by the engine's fitness and spacing inputs? (actual vs predicted wins of returners, harness runner files);
gap vs the horse's usual interval; age; experience; previous first-up performances (repeatability, pooling); preparation number;
distance on resumption; second- and third-up; pre-break trajectory; trainer change during the break; return to the earlier level
(temporary vs persistent). Output batch26/out_b26_returners.json."""
import json, numpy as np, pandas as pd
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'date', 'state', 'dyn_nat', 'dyn_nat_inn', 'gap', 'age_n', 'tkey',
                                                                  'distance_m', 'field', 'finish_pos', 'win'])
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = F.groupby('horse')
F['k'] = g.cumcount(); F['perf'] = F.dyn_nat + F.dyn_nat_inn
F['prev_gaps_med'] = g.gap.transform(lambda s: s.shift().rolling(6, min_periods=3).median())
F['newprep'] = F.gap.isna() | (F.gap >= 60); F['prep'] = F.newprep.astype(int).groupby(F.horse).cumsum(); F['prun'] = F.groupby(['horse', 'prep']).cumcount() + 1
F['prev_dist'] = g.distance_m.shift(); F['prev_tkey'] = g.tkey.shift()
F['traj5'] = g.dyn_nat_inn.transform(lambda s: s.shift().rolling(5, min_periods=3).mean())          # mean surprise over the last 5 runs before
F['rating_change5'] = F.dyn_nat - g.dyn_nat.shift(5)
NAT = F.state != 'QLD'
RET = NAT & (F.gap >= 120) & (F.k >= 3) & F.dyn_nat_inn.notna()
out = {'definition': 'gap >= 120 days since the previous held run, 3+ held runs before, national states, surprise = dyn_nat_inn (Engine v2.3 rating)',
       'returner_runs': int(RET.sum()), 'mean_surprise_kg': round(float(F.loc[RET, 'dyn_nat_inn'].mean()), 3),
       'se': round(float(F.loc[RET, 'dyn_nat_inn'].std() / np.sqrt(RET.sum())), 3)}
def tab(mask, by, minn=150):
    x = F[mask & F.dyn_nat_inn.notna()]; t = x.groupby(by, observed=True).dyn_nat_inn.agg(['size', 'mean', 'std'])
    t = t[t['size'] >= minn]
    return {str(k): {'runs': int(r['size']), 'surprise_kg': round(float(r['mean']), 3), 'se': round(float(r['std'] / np.sqrt(r['size'])), 3)} for k, r in t.iterrows()}
GB = pd.cut(F.gap, [0, 13, 27, 59, 89, 119, 179, 364, 5000], labels=['<14', '14-27', '28-59', '60-89', '90-119', '120-179', '180-364', '365+'])
out['by_gap_all_runs_k3plus'] = tab(NAT & (F.k >= 3), GB)
ratio = F.gap / F.prev_gaps_med
out['by_gap_vs_usual_interval'] = tab(RET, pd.cut(ratio, [0, 3, 6, 10, 1000], labels=['<3x usual', '3-6x', '6-10x', '10x+']))
out['by_age'] = tab(RET, pd.cut(F.age_n, [0, 3, 4, 5, 6, 20], labels=['2-3', '4', '5', '6', '7+']))
out['by_experience'] = tab(RET, pd.cut(F.k, [2, 7, 15, 30, 999], labels=['3-7 runs', '8-15', '16-30', '31+']))
out['by_preparation_number'] = tab(RET, pd.cut(F.prep, [0, 2, 3, 4, 999], labels=['2nd prep', '3rd', '4th', '5th+']))
dch = F.distance_m - F.prev_dist
out['by_distance_on_resumption_vs_last_start'] = tab(RET, pd.cut(dch, [-5000, -201, 200, 5000], labels=['shorter by 200m+', 'within 200m', 'longer by 200m+']))
out['by_pre_break_trajectory'] = tab(RET, pd.cut(F.traj5, [-50, -1.5, 1.5, 50], labels=['declining (last 5 below rating)', 'flat', 'improving']))
tc = (F.tkey != F.prev_tkey) & F.prev_tkey.notna() & F.tkey.notna()
out['by_trainer_change_during_break'] = tab(RET, tc.map({True: 'trainer changed', False: 'same trainer'}))
# second- and third-up, and runs 4-6, after a 120+ day break (relative to the then-current rating, which already updated)
P = F[NAT & (F.k >= 3)].copy(); P['ret_gap'] = P.groupby(['horse', 'prep']).gap.transform('first')
P = P[P.ret_gap >= 120]
out['by_run_in_preparation_after_120d_break'] = {str(k): {'runs': int(v['size']), 'surprise_kg': round(float(v['mean']), 3)} for k, v in P[P.dyn_nat_inn.notna()].groupby(P.prun.clip(upper=7)).dyn_nat_inn.agg(['size', 'mean']).iterrows()}
# return to the earlier level: performance in runs 1-6 of the preparation vs the rating carried into the break
pre = P[P.prun == 1][['horse', 'prep', 'dyn_nat']].rename(columns={'dyn_nat': 'pre_break_rating'})
Q = P.merge(pre, on=['horse', 'prep']); Q['vs_pre'] = Q.perf - Q.pre_break_rating
lev = Q[Q.perf.notna()].groupby(Q.prun.clip(upper=7)).vs_pre.agg(['size', 'mean'])
out['performance_vs_pre_break_rating_by_run'] = {str(k): {'runs': int(r['size']), 'kg': round(float(r['mean']), 3)} for k, r in lev.iterrows()}
best = Q[Q.prun <= 6].groupby(['horse', 'prep']).agg(best=('vs_pre', 'max'), runs=('vs_pre', 'count'), first=('vs_pre', 'first'))
best = best[best.runs >= 4]
out['preparations_with_4plus_runs'] = int(len(best))
out['share_reaching_pre_break_level_within_6_runs'] = round(float((best.best >= 0).mean()), 3)
out['share_first_up_below_but_later_recovered'] = round(float(((best['first'] < -1) & (best.best >= 0)).sum() / max(1, (best['first'] < -1).sum())), 3)
# persistent decline: horses whose best of runs 2-6 stays 2+ kg below the pre-break rating
b26 = Q[(Q.prun >= 2) & (Q.prun <= 6)].groupby(['horse', 'prep']).vs_pre.agg(['max', 'count']); b26 = b26[b26['count'] >= 3]
out['share_persistently_2kg_below_pre_break_runs_2_to_6'] = round(float((b26['max'] < -2).mean()), 3)
# individual repeatability of first-up surprise across preparations (120+ day returns)
fu = F[RET][['horse', 'date', 'dyn_nat_inn']].sort_values(['horse', 'date'])
fu['prev_mean'] = fu.groupby('horse').dyn_nat_inn.transform(lambda s: s.shift().expanding().mean()); fu['prev_n'] = fu.groupby('horse').cumcount()
r1 = fu[fu.prev_n >= 1]
out['repeatability'] = {'returns_with_an_earlier_return': int(len(r1)), 'corr_with_earlier_first_up_mean': round(float(r1[['dyn_nat_inn', 'prev_mean']].corr().iloc[0, 1]), 3)}
# pooling: best shrinkage k for predicting this first-up surprise from earlier ones: est = mean_all + n/(n+k) (prev_mean - mean_all)
mu = float(F.loc[RET, 'dyn_nat_inn'].mean()); best_k = None
for kk in [0.5, 1, 2, 4, 8, 16, 1e9]:
    est = mu + r1.prev_n / (r1.prev_n + kk) * (r1.prev_mean - mu); mse = float(((r1.dyn_nat_inn - est) ** 2).mean())
    out['repeatability'][f'mse_k={kk:g}'] = round(mse, 3)
    if best_k is None or mse < best_k[1]: best_k = (kk, mse)
out['repeatability']['best_shrink_k'] = best_k[0]
# already captured? actual vs predicted wins for returners in the refitted Engine v2.3 harness (window A = 2024, B = 2025-26)
try:
    Rn = pd.read_parquet('/tmp/cand/runners_P26_R.parquet', columns=['race_id', 'horse', 'win', 'p_A', 'p_B'])
    X = Rn.merge(F[['race_id', 'horse', 'gap', 'k']], on=['race_id', 'horse'], how='left')
    cal = {}
    for w in ['A', 'B']:
        x = X[X['p_' + w].notna()]; gb = pd.cut(x.gap, [0, 59, 119, 179, 364, 5000], labels=['<60', '60-119', '120-179', '180-364', '365+'])
        t = x.groupby(gb, observed=True).agg(runners=('win', 'size'), wins=('win', 'sum'), expected=('p_' + w, 'sum'))
        cal[w] = {str(k): {'runners': int(r.runners), 'actual_vs_expected': round(float(r.wins / r.expected), 3)} for k, r in t.iterrows()}
    out['engine_actual_vs_expected_wins_by_gap'] = cal
except Exception as e:
    out['engine_actual_vs_expected_wins_by_gap'] = f'not available: {e}'
json.dump(out, open('batch26/out_b26_returners.json', 'w'), indent=1)
print(json.dumps(out, indent=1)[:6000])
