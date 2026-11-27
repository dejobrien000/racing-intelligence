"""Batch 16 C17: what happens to a horse's measured performance after it changes stable. Research only (descriptive + incremental test).
Frame: Engine v2.3 national rating frame (six states + Qld results in the national rating). Performance = this run's surprise against
the opposition-aware rating (kg; + = better than the rating expected); the rating already moves with every run, so a surprise means the
rating did NOT anticipate the change. Point in time: every control uses earlier runs only.
Trainer change: trainer key differs from the horse's previous run AND the two names share no surname (so 'S Kendrick' -> 'S & B Kendrick'
partnership renames are NOT changes). First run back from 120+ days is a 'spell'.
Questions: (1) first-up-for-new-stable surprise vs comparable same-stable runs; (2) runs 2-5 for the new stable; (3) by horse age,
experience, recent trajectory (declining vs steady), interstate move; (4) incremental to the dynamic trainer assessment (t_surp);
(5) do some receiving trainers repeatedly get more improvement than expected (split-period persistence)? (6) horses that never return."""
import re, json, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'state', 'tkey', 't_surp', 't_n', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'r_ldays', 'distance_m', 'class_label'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
U['prev_t'] = g.tkey.shift(); U['prev_state'] = g.state.shift(); U['gap'] = (U.date - g.date.shift()).dt.days; U['n_prior'] = g.cumcount()
U['prev_inn'] = g.dyn_nat_inn.shift(); U['prev3_inn'] = g.dyn_nat_inn.transform(lambda s: s.shift().rolling(3, min_periods=3).mean())
sur = lambda t: {w for w in re.split(r'[^A-Z]+', str(t).upper()) if len(w) >= 3} - {'AND', 'THE', 'RACING', 'STABLES', 'PTY', 'LTD'}
def changed(a, b):
    if pd.isna(a) or pd.isna(b) or a == b: return False
    return len(sur(a) & sur(b)) == 0
U['tchange'] = [changed(a, b) for a, b in zip(U.prev_t, U.tkey)]
U['tk_rename'] = U.tkey.notna() & U.prev_t.notna() & (U.tkey != U.prev_t) & ~U.tchange
# runs-for-current-stable counter (resets at each genuine change)
U['stint'] = U.tchange.astype(int).groupby(U.horse).cumsum(); U['run_in_stint'] = U.groupby(['horse', 'stint']).cumcount() + 1
U['ever_changed'] = U.groupby('horse').tchange.transform('max')
U['spell'] = (U.gap >= 120).astype(int); U['interstate'] = (U.state != U.prev_state) & U.prev_state.notna()
U['traj'] = np.select([U.prev3_inn <= -2, U.prev3_inn >= 2], ['declining', 'improving'], 'steady'); U.loc[U.prev3_inn.isna(), 'traj'] = 'short history'
U['exp'] = pd.cut(U.n_prior, [0, 5, 15, 30, 999], labels=['1-5', '6-15', '16-30', '31+'], right=True).astype(str)
U['ageb'] = pd.cut(U.age_n, [0, 3, 5, 7, 20], labels=['2-3', '4-5', '6-7', '8+']).astype(str)
U['gapb'] = pd.cut(U.gap, [0, 21, 42, 90, 180, 9999], labels=['<=21', '22-42', '43-90', '91-180', '181+']).astype(str)
E = U[(U.n_prior >= 3) & U.dyn_nat_inn.notna() & U.prev_t.notna() & (U.date >= '2023-07-01')].copy()
OUT = {'runs': int(len(E)), 'trainer_changes': int(E.tchange.sum()), 'partnership_or_name_changes_excluded': int(E.tk_rename.sum())}
# (1) first run for the new stable vs other runs, controlling gap, spell, age, experience, trajectory, interstate, state; cluster by horse
f = 'dyn_nat_inn ~ tchange + C(gapb) + C(ageb) + C(exp) + C(traj) + interstate + C(state)'
def fit(d, f=f):
    need = [c for c in ['dyn_nat_inn', 'tchange', 'new', 'gapb', 'ageb', 'exp', 'traj', 'interstate', 'state', 't_surp'] if c in d.columns and c in f]
    d = d.dropna(subset=need); return smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
ci = lambda m, k: [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)]
m = fit(E); OUT['first_run_new_stable_kg'] = ci(m, 'tchange[T.True]')
m2 = fit(E, f + ' + t_surp'); OUT['first_run_new_stable_kg_given_trainer_assessment'] = ci(m2, 'tchange[T.True]'); OUT['t_surp_coef'] = ci(m2, 't_surp')
for per, d in [('2023-24', E[E.date < '2025-01-01']), ('2025-26', E[E.date >= '2025-01-01'])]: OUT[f'first_run_new_stable_kg_{per}'] = ci(fit(d, f + ' + t_surp'), 'tchange[T.True]')
# (2) later runs in the new stint vs same-run-number of horses that never changed (stint 0), same controls
L_ = E[(E.stint >= 1) & E.run_in_stint.between(2, 5)].copy(); C_ = E[(E.ever_changed == 0) & (E.n_prior >= 5)].copy()
L_['new'] = 1; C_['new'] = 0; LC = pd.concat([L_, C_])
OUT['runs_2_to_5_new_stable_kg_given_trainer_assessment'] = ci(fit(LC, 'dyn_nat_inn ~ new + C(gapb) + C(ageb) + C(exp) + C(traj) + interstate + C(state) + t_surp'), 'new')
# (3) heterogeneity of the first run (raw means relative to comparable non-change runs' fitted value)
E['resid'] = m2.resid.reindex(E.index)
first = E[E.tchange]
OUT['first_run_by_trajectory'] = {k: [int(len(v)), round(float(v.resid.mean()), 2), round(float(v.resid.std() / np.sqrt(len(v))), 2)] for k, v in first.groupby('traj')}
OUT['first_run_by_age'] = {k: [int(len(v)), round(float(v.resid.mean()), 2)] for k, v in first.groupby('ageb')}
OUT['first_run_by_experience'] = {k: [int(len(v)), round(float(v.resid.mean()), 2)] for k, v in first.groupby('exp')}
OUT['first_run_interstate_vs_same_state'] = {str(k): [int(len(v)), round(float(v.resid.mean()), 2)] for k, v in first.groupby('interstate')}
OUT['first_run_after_spell_vs_not'] = {str(k): [int(len(v)), round(float(v.resid.mean()), 2)] for k, v in first.groupby('spell')}
# (4) regression to the mean check: horses whose last 3 runs were poor, with vs without a stable change
dec = E[E.traj == 'declining']; OUT['declining_horses_change_vs_no_change_raw_mean_inn'] = {str(k): [int(len(v)), round(float(v.dyn_nat_inn.mean()), 2)] for k, v in dec.groupby('tchange')}
# (5) receiving trainers: average first-run residual of incoming horses, 2023-24 vs 2025-26 (trainers with 20+ incoming in both)
rt = first.assign(per=np.where(first.date < '2025-01-01', 'a', 'b')).groupby(['tkey', 'per']).resid.agg(['size', 'mean']).unstack()
ok = rt[(rt[('size', 'a')] >= 20) & (rt[('size', 'b')] >= 20)]
OUT['receiving_trainer_persistence'] = {'trainers': int(len(ok)), 'corr_first_run_uplift_2023_24_vs_2025_26': round(float(np.corrcoef(ok[('mean', 'a')], ok[('mean', 'b')])[0, 1]), 3) if len(ok) >= 5 else None}
# (6) selection: horses that never race again within 365 days after their last run, by whether that last run was a stable's first run
cut = U.date.max() - pd.Timedelta(days=365); last = U[U.date <= cut].copy(); nxt = U.groupby('horse').date.shift(-1).reindex(last.index)
last['gone'] = (nxt - last.date).dt.days.fillna(9999) > 365
OUT['no_run_within_365_days_after_run'] = {'first_run_for_new_stable': round(float(last[last.tchange].gone.mean()), 3), 'other_runs': round(float(last[~last.tchange].gone.mean()), 3)}
json.dump(OUT, open('batch16/out_c17_trainer_change.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:3500])
