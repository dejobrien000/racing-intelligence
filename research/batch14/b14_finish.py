"""Batch 14 s2/s3: finishing strength conditional on earlier effort, and leader profiles (falling in vs holding on).
Question: does a run's measured late profile carry information about the horse's NEXT run that its rating (which already absorbed this
run's margin) does not? Outcome = next-run rating surprise (inn_n1, kg; + = ran better than its rating said). Prospective by construction.
Population: Queensland tracked runs (discovery 2022-24; 2025-26 re-used, Batch 12 looked at similar Qld measures); South Australia
2024-26 = independent check (SA tracking has never been used to develop a sectional feature). Measured splits only.
Model: OLS, inn_n1 on standardised features + controls (this run's surprise as a spline, pre-race rating band, early position at 800,
deficit at 800, race early tempo z, distance band, field size, preparation run, finish percentile); 95% intervals by horse-cluster bootstrap.
Features (all field-relative, so tempo, going and rail of the day cancel):
  L600_avg  headline last-600 speed (mean of the three 200 m speeds vs the field)    = "fast last 600"
  L600_min  weakest of the three last 200 m sections vs the field                   = "sustained": no section given up
  fade      final 200 minus 400-200 speed vs the field                              = held speed through the line (+) or weakened (-)
  stride    final-200 stride length minus 400-200 stride length vs the field         = lengthening (+) or shortening (-) late
  ground    ground covered vs the field median (m)
Mechanical overlap: L600_avg, L600_min and fade are built from the same three speeds; they are fitted together so each is read
holding the others fixed, and never counted as separate discoveries."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
OUT = {}
def load(st):
    X = pd.read_parquet(f'/home/claude/b14/runs_{st}.parquet')
    X = X.rename(columns={'field_x': 'field', 'field_y': 'field_nat', 'weight_kg_x': 'weight_kg', 'race_no_x': 'race_no'})
    X = X[(X.def400 < 10) & (X.def0 < 0.17 * X.m.fillna(0) + 2) & X[['v600', 'v400', 'v200']].notna().all(axis=1) & X.inn_n1.notna() & X.dyn_nat_inn.notna()].copy()
    for v in ['v600', 'v400', 'v200']: X[v + 'r'] = X[v] - X.groupby('race_id')[v].transform('median')
    X['L600_avg'] = X[['v600r', 'v400r', 'v200r']].mean(axis=1); X['L600_min'] = X[['v600r', 'v400r', 'v200r']].min(axis=1); X['fade'] = X.v200r - X.v400r
    X['stride'] = (X.sl200 - X.sl400) - (X.sl200 - X.sl400).groupby(X.race_id).transform('median') if 'sl400' in X else np.nan
    X.loc[(X.sl200 <= 0) | (X.sl400 <= 0), 'stride'] = np.nan
    X['ground'] = X.ground_m_rel if 'ground_m_rel' in X else np.nan
    X['early_pos'] = (X.pos800 - 1) / (X.field - 1).clip(lower=1); X['def800c'] = X.def800.clip(upper=4)
    X['dband'] = pd.cut(X.d, [0, 1100, 1300, 1500, 1800, 4000]).astype(str); X['rband'] = pd.qcut(X.dyn_nat, 5, labels=False, duplicates='drop').astype(str)
    X['prep'] = X.prep_idx.clip(upper=5).astype(str); X['tz'] = X.tempo_z.fillna(0).clip(-3, 3); X['tz_miss'] = X.tempo_z.isna().astype(int)
    X['yr'] = X.meeting_date.dt.year
    return X
Q, S = load('QLD'), load('SA')
FEAT = ['L600_avg', 'L600_min', 'fade', 'stride', 'ground']
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct'
def fit(d, feats, extra='', reps=200, seed=3):
    d = d.dropna(subset=feats + ['early_pos', 'def800c']).copy()
    sd = {f: d[f].std() for f in feats}
    for f in feats: d[f + '_z'] = (d[f] - d[f].mean()) / sd[f]
    form = 'inn_n1 ~ ' + ' + '.join(f + '_z' for f in feats) + ' + ' + CTRL + extra
    m = smf.ols(form, d).fit(); est = {f: m.params[f + '_z'] for f in feats}
    rng = np.random.default_rng(seed); H = d.horse.unique(); idx = d.groupby('horse').indices; B = {f: [] for f in feats}
    for _ in range(reps):
        pick = np.concatenate([idx[h] for h in rng.choice(H, len(H))]); mb = smf.ols(form, d.iloc[pick]).fit()
        for f in feats: B[f].append(mb.params[f + '_z'])
    return {f: (round(est[f], 3), round(float(np.percentile(B[f], 2.5)), 3), round(float(np.percentile(B[f], 97.5)), 3)) for f in feats}, len(d), d.horse.nunique()
import os
rows = []
for lab, d in ([] if os.environ.get('LEADERS_ONLY') else [('QLD 2022-24 (discovery)', Q[Q.yr <= 2024]), ('QLD 2025-26 (re-used)', Q[Q.yr >= 2025]), ('SA 2024-26 (independent)', S)]):
    feats = FEAT if lab.startswith('QLD') else ['L600_avg', 'L600_min', 'fade', 'stride', 'ground']
    feats = [f for f in feats if d[f].notna().mean() > 0.5]
    r, n, h = fit(d, feats)
    for f, v in r.items(): rows.append({'population': lab, 'runs': n, 'horses': h, 'feature (per 1 sd)': f, 'next_run_kg': v[0], 'lo': v[1], 'hi': v[2]})
    print(lab, n, h, r, flush=True)
O = pd.DataFrame(rows)
if len(O): O.to_csv('/home/claude/racing-intelligence/research/batch14/out_finish_features.csv', index=False)

# "Encouraging run despite an ordinary finish": finished 5th or worse, but sustained (L600_min) in the top quarter of the race field,
# vs other 5th-or-worse runners with the same controls. Reported in kg next run.
def flag_test(d, lab):
    d = d[(d.fp >= 5)].dropna(subset=['L600_min', 'early_pos', 'def800c']).copy()
    d['sust_top'] = (d.groupby('race_id').L600_min.rank(pct=True) >= 0.75).astype(int)
    d['burst_fade'] = ((d.groupby('race_id').L600_avg.rank(pct=True) >= 0.75) & (d.groupby('race_id').fade.rank(pct=True) <= 0.25)).astype(int)
    out = {}
    for flag in ['sust_top', 'burst_fade']:
        m = smf.ols(f'inn_n1 ~ {flag} + ' + CTRL, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
        out[flag] = (round(m.params[flag], 2), round(m.conf_int().loc[flag, 0], 2), round(m.conf_int().loc[flag, 1], 2), int(d[flag].sum()))
    return out
F = {} if os.environ.get('LEADERS_ONLY') else {lab: flag_test(d, lab) for lab, d in [('QLD 2022-24', Q[Q.yr <= 2024]), ('QLD 2025-26', Q[Q.yr >= 2025]), ('SA 2024-26', S)]}
print(json.dumps(F)); OUT['ordinary_finish_flags'] = F

# s3 leader profiles. Leader = first at the 400 m mark (measured cumulative time). Lead at 400 = second horse's deficit at 400 (s).
def leaders(d0, lab):
    d = d0.copy()
    def second(col):
        t = d[['race_id', col]].dropna().sort_values(['race_id', col]); t = t[t.groupby('race_id').cumcount() == 1]; return t.set_index('race_id')[col]
    sec400 = second('def400')
    L = d[d.def400 == 0].drop_duplicates('race_id').copy(); L['lead400'] = L.race_id.map(sec400)
    sec0 = second('def0'); L['lead0'] = np.where(L.fp == 1, L.race_id.map(sec0), -L.def0)    # + = winning margin, - = beaten by
    L['pressure'] = L.race_id.map(second('def800')) < 0.10       # another horse within ~half a length at 800
    L = L[L.lead400.notna() & L.lead0.notna()]
    L['profile'] = np.where(L.lead400 >= 0.25, 'clear (>=1.5 L) at 400', 'narrow (<1.5 L) at 400')
    L['outcome'] = np.where((L.fp == 1) & (L.lead0 >= L.lead400 - 0.05), 'held or extended', np.where(L.fp == 1, 'won, lead shrank (fell in)', 'caught'))
    L['tempo'] = pd.cut(L.tempo_z, [-9, -0.75, 0.75, 9], labels=['slow early', 'normal early', 'fast early']).astype(object).fillna('tempo unknown')
    L = L.dropna(subset=['inn_n1', 'dyn_nat_inn', 'rband', 'dband', 'field', 'outcome', 'profile']).copy(); L['pressure'] = L.pressure.astype(int)
    m = smf.ols('inn_n1 ~ C(outcome, Treatment("held or extended")) * C(profile) + C(tempo) + pressure + bs(dyn_nat_inn, df=4) + C(rband) + C(dband) + field', L).fit(
        cov_type='cluster', cov_kwds={'groups': pd.factorize(L.horse)[0]})
    tab = L.groupby(['profile', 'outcome']).agg(runs=('inn_n1', 'size'), this_run_kg=('dyn_nat_inn', 'mean'), final200_vs_field=('v200r', 'mean'), next_run_kg=('inn_n1', 'mean'), next_finish_pct=('fp_n1', 'mean')).round(2)
    tab2 = L.groupby(['tempo', 'outcome']).agg(runs=('inn_n1', 'size'), final200_vs_field=('v200r', 'mean'), next_run_kg=('inn_n1', 'mean')).round(2)
    coefs = {k: (round(v, 2), round(m.conf_int().loc[k, 0], 2), round(m.conf_int().loc[k, 1], 2)) for k, v in m.params.items() if 'outcome' in k or 'tempo' in k or 'pressure' in k}
    print('\n', lab, len(L), '\n', tab.to_string(), '\n', tab2.to_string(), '\n', json.dumps(coefs))
    return {'table': tab.reset_index().to_dict('records'), 'tempo_table': tab2.reset_index().to_dict('records'), 'coefs': coefs, 'leaders': len(L)}
OUT['leaders'] = {lab: leaders(d, lab) for lab, d in [('QLD 2022-26', Q), ('SA 2024-26', S)]}
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_finish_leaders.json', 'w'), indent=1, default=str)
