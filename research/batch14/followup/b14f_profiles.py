"""Batch 14 follow-up s1/s2/s3/s8: physical performance profiles, each horse's normal profile vs abnormal changes, longer-term
trajectories with drop-out, and stewards' reports as supplementary evidence. Research only; nothing changes production.
Sections (field-relative speeds, m/s; measured 200 m averages): a = 600-400 m out, b = 400-200, c = final 200.
Continuous measures: level m = (a+b+c)/3; slope = c - a (+ = finished stronger than it ran 600-400); bend = b - (a+c)/2 (- = mid dip);
recovery = c - b. Descriptive profiles from the two steps (b-a, c-b), each 'up', 'flat' or 'down' with a dead zone of D m/s
(D = 0.5 x the sd of the steps across all runs, so 'flat' is defined by the data):
  Steady (flat, flat); Dip and recover (down, up) = fast-slow-fast; Surge then fade (up, down) = slow-fast-slow;
  Building (up/flat or flat/up or up/up) = slow-fast-fast / slow-slow-fast; Late fade (flat, down) = fast-fast-slow;
  Early fade (down, flat) = fast-slow-slow; Progressive fade (down, down) = fast-slow-slower.
Level (fast-fast-fast vs slow-slow-slow) is the continuous m, not a profile.
Outcomes: rating surprise next run, mean of next 3 and next 5 (kg); rating change after 1/3/5 starts; next start within 180 days.
Controls (all models): this run's surprise (spline), rating band, early position, deficit at 800, early tempo z, distance band, field size,
preparation stage, finish percentile, level m, track (course), field mean rating (opposition), going.
Qld 2022-24 discovery, Qld 2025-26 re-used, SA 2024-26 check (SA used for these hypotheses in Batch 14 already)."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json, os, sys, re
os.environ['LEADERS_ONLY'] = '1'; sys.argv = ['x']
exec(open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0])   # Q, S with load()
def cfit(form, f, key='horse'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
def co(m, k, nd=3): return (round(m.params[k], nd), round(m.conf_int().loc[k, 0], nd), round(m.conf_int().loc[k, 1], nd)) if k in m.params else None
V = pd.read_parquet('/home/claude/racing-intelligence/research/engine/frames/national_v3.parquet', columns=['race_id', 'horse', 'date', 'race_no', 'dyn_nat', 'dyn_nat_inn', 'going', 'gap'])
V = V.sort_values(['horse', 'date', 'race_no']); g = V.groupby('horse'); V['fmean'] = V.groupby('race_id').dyn_nat.transform('mean')
for k in [1, 3, 5]: V[f'rat_chg{k}'] = g.dyn_nat.shift(-k) - V.dyn_nat
for k in [4, 5]: V[f'inn_n{k}'] = g.dyn_nat_inn.shift(-k)
V['gap_next'] = g.gap.shift(-1).astype(float); V['next5'] = pd.concat([g.dyn_nat_inn.shift(-k) for k in range(1, 6)], axis=1).mean(axis=1)
V = V.rename(columns={'race_id': 'nat_race'})[['nat_race', 'horse', 'fmean', 'going', 'rat_chg1', 'rat_chg3', 'rat_chg5', 'next5', 'gap_next']]
ST = pd.read_csv('/home/claude/racing-intelligence/research/staging/stewards/stewards_events.csv.gz', low_memory=False); ST['date'] = pd.to_datetime(ST.date)
TAG = ['held_up', 'checked', 'restrained', 'bumped', 'wide', 'wide_no_cover', 'wide_cover', 'unable_improve', 'disappointed_run', 'weakened', 'rider_concern', 'performance_concern', 'vet_finding', 'slow_begin', 'over_raced', 'laid_hung', 'shifted']
SS = ST[ST.role == 'subject'].groupby(['state', 'date', 'horse'])[TAG + ['ph_straight', 'ph_turn']].max().reset_index()
SM = ST[ST.role == 'mentioned'].groupby(['state', 'date', 'horse'])[['checked', 'bumped', 'held_up']].max().add_prefix('m_').reset_index()
SC = ST[ST.role == 'subject'][['state', 'date']].drop_duplicates(); SC['report_held'] = 1
OUT = {}
def prep(d0, st):
    d = d0.merge(V, on=['nat_race', 'horse'], how='left').dropna(subset=['early_pos', 'def800c']).copy()
    d['a'], d['b'], d['c'] = d.v600r, d.v400r, d.v200r; d['m'] = (d.a + d.b + d.c) / 3; d['slope'] = d.c - d.a; d['bend'] = d.b - (d.a + d.c) / 2; d['recovery'] = d.c - d.b
    d['dip'] = d.m - d[['a', 'b', 'c']].min(axis=1)
    s1, s2 = d.b - d.a, d.c - d.b; D = 0.5 * pd.concat([s1, s2]).std()
    st1 = np.where(s1 > D, 'up', np.where(s1 < -D, 'down', 'flat')); st2 = np.where(s2 > D, 'up', np.where(s2 < -D, 'down', 'flat'))
    P = {('flat', 'flat'): 'Steady', ('down', 'up'): 'Dip and recover', ('up', 'down'): 'Surge then fade', ('up', 'flat'): 'Building', ('flat', 'up'): 'Building',
         ('up', 'up'): 'Building', ('flat', 'down'): 'Late fade', ('down', 'flat'): 'Early fade', ('down', 'down'): 'Progressive fade'}
    d['profile'] = [P[(x, y)] for x, y in zip(st1, st2)]; d['D'] = D
    d['going'] = d.going.fillna('?').astype(str); d['fmean_c'] = d.fmean - d.dyn_nat
    d['dkey'] = d.meeting_date.dt.normalize()
    d = d.merge(SS.rename(columns={'date': 'dkey'}), on=['state', 'dkey', 'horse'], how='left').merge(SM.rename(columns={'date': 'dkey'}), on=['state', 'dkey', 'horse'], how='left') \
         .merge(SC.rename(columns={'date': 'dkey'}), on=['state', 'dkey'], how='left')
    d['report_held'] = d.report_held.fillna(0); d['commented'] = d[TAG].notna().any(axis=1).astype(int)
    for t in TAG + ['ph_straight', 'ph_turn', 'm_checked', 'm_bumped', 'm_held_up']: d[t] = d[t].fillna(0)
    d['interference'] = ((d.held_up + d.checked + d.m_checked + d.m_held_up) > 0).astype(int)
    return d
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct + m + C(track) + fmean_c + C(going)'
for lab, d0, st in [('QLD 2022-24', Q[Q.yr <= 2024], 'QLD'), ('QLD 2025-26', Q[Q.yr >= 2025], 'QLD'), ('SA 2024-26', S, 'SA')]:
    d = prep(d0, st); r = {'runs': len(d), 'dead zone m/s': round(d.D.iloc[0], 3), 'profile share %': (100 * d.profile.value_counts(normalize=True)).round(1).to_dict()}
    # 1) profiles vs Steady, horizons
    for y in ['inn_n1', 'next3', 'next5', 'rat_chg5']:
        f = d.dropna(subset=[y]); mm = cfit(f'{y} ~ C(profile, Treatment("Steady")) + ' + CTRL, f)
        r[f'profiles vs Steady: {y}'] = {k.split('[T.')[1][:-1]: co(mm, k, 2) for k in mm.params.index if 'profile' in k}
    # is the unevenness value in the shape terms? dip alone vs continuous shape vs both
    f = d.dropna(subset=['inn_n1'])
    m1 = cfit('inn_n1 ~ I(dip/dip.std()) + ' + CTRL, f); m2 = cfit('inn_n1 ~ I(slope/slope.std()) + I(bend/bend.std()) + ' + CTRL, f)
    m3 = cfit('inn_n1 ~ I(dip/dip.std()) + I(recovery/recovery.std()) + I(slope/slope.std()) + ' + CTRL, f)
    r['dip alone (per sd)'] = co(m1, 'I(dip / dip.std())'); r['shape: slope, bend (per sd)'] = [co(m2, 'I(slope / slope.std())'), co(m2, 'I(bend / bend.std())')]
    r['dip with recovery and slope (per sd)'] = {'dip': co(m3, 'I(dip / dip.std())'), 'recovery': co(m3, 'I(recovery / recovery.std())'), 'slope': co(m3, 'I(slope / slope.std())')}
    r['model fit R2 (dip, shape)'] = [round(m1.rsquared, 4), round(m2.rsquared, 4)]
    # same average, different shape: within the middle third of level m, next-run surprise by profile (raw means, for illustration)
    mid = f[(f.m > f.m.quantile(1 / 3)) & (f.m < f.m.quantile(2 / 3))]
    r['middle third of average speed: mean next-run kg by profile (raw)'] = mid.groupby('profile').inn_n1.agg(['mean', 'size']).round(2).to_dict('index')
    # 3) stewards: coverage and what each profile's runs had REPORTED (subject paragraph), and whether profiles hold up with/without reports
    held = d[d.report_held == 1]
    r['stewards: runs at meetings with a report held %'] = round(100 * d.report_held.mean(), 1); r['of those, runs with a paragraph about the horse %'] = round(100 * held.commented.mean(), 1)
    tab = held.groupby('profile')[['interference', 'held_up', 'checked', 'weakened', 'performance_concern', 'unable_improve', 'wide', 'wide_no_cover']].mean().mul(100).round(1)
    r['stewards: share of runs with each reported event, by profile %'] = tab.to_dict('index')
    hf = held.dropna(subset=['inn_n1']).copy()
    if len(hf) > 2000:
        m4 = cfit('inn_n1 ~ I(dip/dip.std()) * interference + weakened + performance_concern + wide_no_cover + ' + CTRL, hf)
        r['stewards: dip per sd, dip x reported interference, reported interference, weakened, performance concern, no cover (next-run kg)'] = {
            k: co(m4, k) for k in ['I(dip / dip.std())', 'I(dip / dip.std()):interference', 'interference', 'weakened', 'performance_concern', 'wide_no_cover']}
    # measured width vs reported width
    if 'rail400' in d:
        r['measured width at 400 (m), runs reported wide vs not'] = held.groupby('wide').rail400.mean().round(2).to_dict()
    OUT[lab] = r; print(lab, json.dumps(r, default=str)[:2500], '\n', flush=True)
    if lab.startswith('QLD 2025'): d_q2 = d
    if lab.startswith('QLD 2022'): d_q1 = d
    if lab.startswith('SA'): d_sa = d
pd.concat([d_q1, d_q2, d_sa]).to_parquet('/home/claude/b14/profiles.parquet')
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/followup/out_profiles.json', 'w'), indent=1, default=str)
