"""Batch 14 follow-up s4/s5: horse and rider momentum profiles (descriptive, research only) and rider late-speed retention ('finishing
strength'), validated in South Australia, with controls, and tested for value beyond the existing dynamic jockey assessment (j_surp).
Measured 200 m section speeds, field-relative unless stated. Coarse: no instantaneous acceleration, no claim about when a rider asked.
timing  = mean(v 800-600, v 600-400) - mean(v 400-200, final 200)   (+ = gains on the field earlier)
hold    = final 200 - (400-200)                                  (late-speed retention vs the field; = 'recovery' in b14f_profiles)
acc_abs = absolute speed change 600-400 -> 400-200 (m/s); acc_rel = the same field-relative. A relative gain while absolute speed falls
          = a gain made because others slowed more.
prolonged = field-relative speed rose over 2+ consecutive sections from 1000 m out; rapid = one rise > the dead zone D and no other rise
sustained = number of the last four sections at least 0.2 m/s above the field median"""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json, os
def cfit(form, f, key='horse'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
def co(m, k, nd=3): return (round(m.params[k], nd), round(m.conf_int().loc[k, 0], nd), round(m.conf_int().loc[k, 1], nd)) if k in m.params else None
P = pd.read_parquet('/home/claude/b14/profiles.parquet')
for v in ['v1000', 'v800']: P[v + 'r'] = P[v] - P.groupby('race_id')[v].transform('median')
P['timing'] = (P.v800r + P.v600r) / 2 - (P.v400r + P.v200r) / 2; P['hold'] = P.v200r - P.v400r
P['acc_abs'] = P.v400 - P.v600; P['acc_rel'] = P.v400r - P.v600r
rises = np.c_[(P.v800r - P.v1000r), (P.v600r - P.v800r), (P.v400r - P.v600r), (P.v200r - P.v400r)]; D = P.D
up = rises > D.values[:, None]; P['n_rises'] = up.sum(axis=1)
cons = np.zeros(len(P), int)
for i in range(3): cons = np.maximum(cons, (up[:, i] & up[:, i + 1]).astype(int))
P['prolonged'] = cons; P['rapid'] = ((P.n_rises == 1) & (rises.max(axis=1) > 2 * D.values)).astype(int)
P['sustained'] = (np.c_[P.v800r, P.v600r, P.v400r, P.v200r] > 0.2).sum(axis=1)
P['jk'] = P.jkey.fillna(P.jockey.astype(str)); P['tk'] = P.tkey.fillna(P.trainer.astype(str))
P = P.dropna(subset=['timing', 'hold']).sort_values(['meeting_date', 'race_id']).reset_index(drop=True)
OUT = {}
# actual vs relative acceleration
OUT['relative gains made while absolute speed fell, % of relative gains (600-400 -> 400-200)'] = round(100 * ((P.acc_rel > 0) & (P.acc_abs < 0)).sum() / (P.acc_rel > 0).sum(), 1)
OUT['correlation absolute vs relative acceleration'] = round(P.acc_abs.corr(P.acc_rel), 3)
OUT['profile measures share of runs: prolonged %, rapid %, sustained>=3 %'] = [round(100 * P.prolonged.mean(), 1), round(100 * P.rapid.mean(), 1), round(100 * (P.sustained >= 3).mean(), 1)]
def split_half(d, key, col, nmin):
    h = d.groupby(key).filter(lambda g: len(g) >= nmin).copy(); h['half'] = h.groupby(key).cumcount() % 2
    p = h.groupby([key, 'half'])[col].mean().unstack().dropna(); r = p[0].corr(p[1]); return (round(r, 3), len(p))
# controlled residuals (circumstances): position, deficit at 800, tempo, distance, track, opposition, prep, field
def resid(d, col):
    y, X = patsy.dmatrices(f'{col} ~ early_pos + I(early_pos**2) + def800c + tz + tz_miss + C(dband) + C(track) + fmean_c + C(prep) + field', d, return_type='dataframe', NA_action='drop')
    r = pd.Series(np.nan, index=d.index); r.loc[y.index] = sm.OLS(y, X).fit().resid.values; return r
pers = {}
for st in ['QLD', 'SA']:
    d = P[P.state == st].copy()
    for col in ['timing', 'hold', 'prolonged', 'sustained']:
        d[col + '_res'] = resid(d, col)
        d[col + '_wh'] = d[col + '_res'] - d.groupby('horse')[col + '_res'].transform('mean')                    # same horse, different riders
        d[col + '_wht'] = d[col + '_wh'] - d.groupby('tk')[col + '_wh'].transform('mean')                      # and the trainer's average removed
        pers[f'{st} {col}'] = {'horse split-half (8+ runs)': split_half(d.sort_values('meeting_date'), 'horse', col + '_res', 8),
                               'rider within-horse split-half (100+ rides)': split_half(d.sort_values('meeting_date'), 'jk', col + '_wh', 100),
                               'rider within-horse, trainer removed (100+ rides)': split_half(d.sort_values('meeting_date'), 'jk', col + '_wht', 100)}
    # stability of horse timing across courses and running styles
    h = d.dropna(subset=['timing_res']).copy(); tr = h.groupby(['horse', 'track']).timing_res.agg(['mean', 'size']).reset_index(); tr = tr[tr['size'] >= 3]
    pairs = tr.merge(tr, on='horse'); pairs = pairs[pairs.track_x < pairs.track_y].drop_duplicates('horse')
    pers[f'{st} horse timing: same horse at two different courses (3+ runs each) r, horses'] = (round(pairs.mean_x.corr(pairs.mean_y), 3), len(pairs))
    h['style'] = np.where(h.early_pos < 0.5, 'on pace', 'back'); sy = h.groupby(['horse', 'style']).timing_res.agg(['mean', 'size']).unstack()
    sy = sy[(sy['size'] >= 3).all(axis=1)]
    pers[f'{st} horse timing: same horse when on pace vs when back (3+ each) r, horses'] = (round(sy['mean']['on pace'].corr(sy['mean']['back']), 3), len(sy))
    # rider within-horse timing: stable across trainers? split each rider's rides by trainer (two trainer groups)
    w = d.dropna(subset=['timing_wh']).copy(); w['tg'] = pd.factorize(w.tk)[0] % 2
    tg = w.groupby(['jk', 'tg']).timing_wh.agg(['mean', 'size']).unstack(); tg = tg[(tg['size'] >= 50).all(axis=1)]
    pers[f'{st} rider within-horse timing: two different sets of trainers (50+ each) r, riders'] = (round(tg['mean'][0].corr(tg['mean'][1]), 3), len(tg))
    P.loc[d.index, ['timing_res', 'hold_res', 'timing_wh', 'hold_wh']] = d[['timing_res', 'hold_res', 'timing_wh', 'hold_wh']].values
OUT['persistence and stability'] = pers; print(json.dumps(pers), flush=True)
# descriptive profiles (research only): shrunk means with intervals, horses 10+ tracked runs and riders 200+ tracked rides
def profile_table(key, nmin, k_prior, cols):
    g = P.groupby(key); n = g.size(); rows = []
    for c in cols:
        s = g[c].agg(['sum', 'count', 'std']); s['shrunk'] = s['sum'] / (s['count'] + k_prior); s['se'] = s['std'] / np.sqrt(s['count'] + k_prior)
        s.columns = [f'{c}_{x}' for x in s.columns]; rows.append(s[[f'{c}_shrunk', f'{c}_se']])
    T = pd.concat(rows, axis=1); T['n'] = n; T['state'] = g.state.agg(lambda x: x.mode().iloc[0]); return T[T.n >= nmin].round(3)
H = profile_table('horse', 10, 4, ['timing_res', 'hold_res', 'prolonged', 'sustained']); H['dip_recover_%'] = (100 * P.groupby('horse').profile.apply(lambda x: (x == 'Dip and recover').mean())).round(1)
J = profile_table('jk', 200, 50, ['timing_wh', 'hold_wh'])
name = P.groupby('jk').jockey.agg(lambda x: x.mode().iloc[0] if len(x.dropna()) else ''); J['rider'] = name
H.sort_values('timing_res_shrunk').to_csv('/home/claude/racing-intelligence/research/batch14/followup/horse_momentum_profiles.csv')
J.sort_values('timing_wh_shrunk').to_csv('/home/claude/racing-intelligence/research/batch14/followup/rider_momentum_profiles.csv')
OUT['profiles written'] = {'horses (10+ tracked runs)': len(H), 'riders (200+ tracked rides)': len(J)}
OUT["riders: LATE movers (most - timing)"] = J.nsmallest(5, 'timing_wh_shrunk')[['rider', 'state', 'n', 'timing_wh_shrunk', 'timing_wh_se']].values.tolist()[::-1]
OUT["riders: EARLY movers (largest + timing)"] = J.nlargest(5, 'timing_wh_shrunk')[['rider', 'state', 'n', 'timing_wh_shrunk', 'timing_wh_se']].values.tolist()
OUT['riders: best late retention (within-horse hold, shrunk)'] = J.nlargest(5, 'hold_wh_shrunk')[['rider', 'state', 'n', 'hold_wh_shrunk', 'hold_wh_se']].values.tolist()
OUT['riders: weakest late retention'] = J.nsmallest(5, 'hold_wh_shrunk')[['rider', 'state', 'n', 'hold_wh_shrunk', 'hold_wh_se']].values.tolist()
OUT['riders: sd of shrunk tendency vs typical se (timing, hold)'] = [round(J.timing_wh_shrunk.std(), 3), round(J.timing_wh_se.median(), 3), round(J.hold_wh_shrunk.std(), 3), round(J.hold_wh_se.median(), 3)]
# prospective: rider's and horse's PRIOR tendencies (earlier dates only, shrunk) -> this run's surprise; beyond j_surp; complement/conflict
def prior(key, col, k):
    t = P[[key, 'meeting_date', col]].dropna(); day = t.groupby([key, 'meeting_date'])[col].agg(['sum', 'count']).reset_index().sort_values('meeting_date')
    day['cs'] = day.groupby(key)['sum'].cumsum() - day['sum']; day['cc'] = day.groupby(key)['count'].cumsum() - day['count']; day['p'] = day.cs / (day.cc + k)
    return P[[key, 'meeting_date']].merge(day[[key, 'meeting_date', 'p', 'cc']], on=[key, 'meeting_date'], how='left')
for key, col, k, nm in [('jk', 'hold_wh', 50, 'r_hold'), ('jk', 'timing_wh', 50, 'r_timing'), ('horse', 'timing_res', 4, 'h_timing'), ('horse', 'hold_res', 4, 'h_hold')]:
    x = prior(key, col, k); P[nm] = x.p.values; P[nm + '_n'] = x.cc.values
for nm in ['r_hold', 'r_timing', 'h_timing', 'h_hold']: P[nm + '_z'] = P[nm] / P[nm].std()
CT = 'C(rband) + C(dband) + field + tz + tz_miss + C(track) + fmean_c + C(prep)'
pro = {}
for st in ['QLD', 'SA']:
    f = P[(P.state == st) & (P.r_hold_n >= 50) & P.j_surp.notna()].copy()
    m = cfit('dyn_nat_inn ~ j_surp + r_hold_z + r_timing_z + ' + CT, f, 'jk')
    pro[f'{st} this-run surprise kg per sd: rider prior hold, rider prior timing (beyond j_surp)'] = {'r_hold_z': co(m, 'r_hold_z'), 'r_timing_z': co(m, 'r_timing_z'), 'rides': int(m.nobs)}
    g2 = f[f.h_timing_n >= 3].copy()
    m2 = cfit('dyn_nat_inn ~ j_surp + r_hold_z * h_timing_z + r_timing_z * h_timing_z + ' + CT, g2, 'jk')
    pro[f'{st} horse timing x rider tendencies (interaction, kg per sd^2)'] = {k: co(m2, k) for k in ['r_hold_z:h_timing_z', 'h_timing_z:r_timing_z', 'h_timing_z']}
OUT['prospective (this run, beyond j_surp)'] = pro; print(json.dumps(pro), flush=True)
P[['state', 'race_id', 'horse', 'jk', 'meeting_date', 'r_hold', 'r_timing', 'r_hold_n', 'h_timing', 'h_hold']].to_parquet('/home/claude/b14/rider_priors.parquet')
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/followup/out_riders.json', 'w'), indent=1, default=str)
