"""Batch 7, discovery screen 2: NSW / Vic / ACT (Breednet full fields; no sectionals or barriers in history).
Same discipline as screen 1: one term at a time on top of the frozen operational model (nat_v2, as an offset, scaled
exactly as in pre-race scoring), within-race conditional logit.
  DISCOVERY = races before 2025 (estimate, se, 2 halves same sign, BH 10%); CONFIRMATION = 2025-26 (coefficient fixed,
  meeting-bootstrap CI of the fit gain); plus top pick / top-3 / ordering changes on confirmation races.
Families: M new single features incl. the untested jockey, trainer, age, sex, class-change families; N nonlinear shapes;
T time-varying (does an effect drift by year?); C feature x context; P pairwise among core + new; R replication of the
Qld Batch 6 findings. Course-specificity (per configuration, Q and I^2) for anything that passes both stages.
Outputs engine/out/screen_nat*.csv"""
import json, itertools, numpy as np, pandas as pd, hier_tools as H
from scipy.stats import norm
from statsmodels.stats.multitest import multipletests
from engine import evaltools as E
rng = np.random.default_rng(20261125)
U = pd.read_parquet('engine/frames/national.parquet'); x = E.nat_frame(U)
mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
for c in C2: x[c + '_fz'] = ((x[c].astype(float) - x.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0)
x['offset'] = sum(C2[c] * x[c + '_fz'] for c in C2)
x['big_field'] = (x.field >= 12).astype(float); x['vic'] = (x.state == 'VIC').astype(float); x['yr'] = (x.date.dt.year - 2024).astype(float)
x['abs_dist_change'] = x.dist_change.abs(); x['dyn_gap_top'] = x.dyn_nat - x.groupby('race_id').dyn_nat.transform('max')
x['field_dyn'] = x.groupby('race_id').dyn_nat.transform('mean'); x['young'] = (x.age_n <= 3).astype(float).where(x.age_n.notna()); x['old'] = (x.age_n >= 7).astype(float).where(x.age_n.notna())
NEW = ['surprise_last', 'surprise_avg3', 'dyn_traj', 'h2h', 'j_surp', 't_surp', 'jt_surp', 'j_change', 'same_jockey', 'wt_change', 'dist_change', 'abs_dist_change', 'bm_change', 'age_n', 'young', 'old', 'female', 'first_at_course', 'dyn_nat_sd', 'dyn_gap_top']
CORE = list(C2)
x = E.zcols(x, sorted(set(NEW + CORE)))
x['fd_z'] = (x.field_dyn - x.field_dyn.mean()) / x.field_dyn.std()
dev, ev = x[x.period == 'development'].copy(), x[x.period == 'evaluation'].copy()
mid = dev.date.quantile(0.5); h1 = (dev.date < mid).values
evmid = ev.drop_duplicates('race_id').set_index('race_id').meeting_id
print('discovery races', dev.race_id.nunique(), dev.date.min().date(), '-', dev.date.max().date(), '| confirmation races', ev.race_id.nunique())
def term(df, expr):
    t = np.asarray(expr(df), dtype=float); t = np.where(np.isfinite(t), t, 0.0)
    return t - pd.Series(t, index=df.index).groupby(df.race_id.values).transform('mean').values
def run(name, family, expr, why):
    td, te = term(dev, expr), term(ev, expr); s = np.std(td) or 1.0; td, te = td / s, te / s
    nvar = int(pd.Series(np.abs(td) > 1e-9).groupby(dev.race_id.values).any().sum())
    if nvar < 300: return {'name': name, 'family': family, 'note': f'too little variation ({nvar} races)'}
    R = H.Races(dev.race_id.values, dev.win.values, dev.offset.values, td[:, None]); b = H.fit(R, np.array([1e-6])); se = H.posterior_sd(R, b, np.array([1e-6]))[0]
    b1 = H.fit(H.Races(dev.race_id.values[h1], dev.win.values[h1], dev.offset.values[h1], td[h1][:, None]), np.array([1e-6]))[0]
    b2 = H.fit(H.Races(dev.race_id.values[~h1], dev.win.values[~h1], dev.offset.values[~h1], td[~h1][:, None]), np.array([1e-6]))[0]
    Re = H.Races(ev.race_id.values, ev.win.values, ev.offset.values, te[:, None]); rid = ev.race_id.values[Re.o][Re.starts]
    gain = pd.Series(Re.loglik_per_race(b) - Re.loglik_per_race(np.zeros(1)), index=rid); hit = Re.top_hit(b) - Re.top_hit(np.zeros(1))
    e0 = ev.offset.values; e1 = e0 + b[0] * te
    def top3(e):
        t_ = pd.DataFrame({'r': ev.race_id.values, 'e': e, 'w': ev.win.values}); t_['rk'] = t_.groupby('r').e.rank(ascending=False, method='first'); return t_[t_.w == 1].rk.le(3).mean()
    m = gain.groupby(evmid.reindex(gain.index).values).agg(['sum', 'count']); su, n = m['sum'].values, m['count'].values
    bs = [su[i].sum() / n[i].sum() for i in (rng.integers(0, len(su), len(su)) for _ in range(300))]
    return {'name': name, 'family': family, 'rationale': why, 'races_with_variation_dev': nvar, 'coef_per_sd': round(float(b[0]), 4), 'se': round(float(se), 4),
            'p_discovery': float(2 * norm.sf(abs(b[0] / se))), 'coef_half1': round(float(b1), 4), 'coef_half2': round(float(b2), 4), 'same_sign_halves': bool(np.sign(b1) == np.sign(b2)),
            'confirm_gain_per_race': round(float(gain.mean()), 5), 'confirm_lo95': round(float(np.percentile(bs, 2.5)), 5), 'confirm_hi95': round(float(np.percentile(bs, 97.5)), 5),
            'confirm_top_pick_change_pts': round(100 * float(np.mean(hit)), 2), 'confirm_top3_change_pts': round(100 * (top3(e1) - top3(e0)), 2), 'confirm_races': len(gain)}
Z = lambda c: (lambda d: d[c + '_z'])
D = []
WHY = {'surprise_last': 'beat its own rating last start', 'surprise_avg3': 'beat its rating on average over 3 starts', 'dyn_traj': 'rating rising over the last two runs', 'h2h': "earlier record against today's rivals",
       'j_surp': "jockey's earlier rides beat their horses' ratings (shrunk)", 't_surp': "trainer's earlier runners beat their ratings (shrunk)", 'jt_surp': 'this jockey-trainer combination', 'j_change': 'jockey upgrade vs last start',
       'same_jockey': 'same jockey as last start', 'wt_change': 'weight change since last start', 'dist_change': 'distance up (+) or down (-) since last start', 'abs_dist_change': 'size of the distance change',
       'bm_change': 'benchmark class change since last start', 'age_n': 'age in years', 'young': '3yo or younger', 'old': '7yo or older', 'female': 'mare or filly', 'first_at_course': 'first run at this course configuration',
       'dyn_nat_sd': 'rating uncertainty (few or old runs)', 'dyn_gap_top': 'kg behind the top-rated runner in the race'}
for f in NEW: D.append(run(f + ' (main effect)', 'M new feature', Z(f), WHY[f]))
# N nonlinear shapes (U-shapes, thresholds) of core and new features
for f in ['dyn_nat', 'a_wt_rel', 'f_lstarts', 'r_ldays', 'age_n', 'dist_change', 'j_surp', 'c_rec', 'a_fs3', 'f_avgfp3']:
    D.append(run(f + ' squared', 'N nonlinear', (lambda f: (lambda d: d[f + '_z'] ** 2))(f), 'curved effect: extremes matter more/less than a straight line says'))
D.append(run('top-rated runner flag', 'N nonlinear', lambda d: (d.dyn_gap_top >= 0).astype(float), 'is being the top-rated runner worth more than the kg suggests?'))
D.append(run('more than 5 kg behind top-rated', 'N nonlinear', lambda d: (d.dyn_gap_top < -5).astype(float), 'threshold: well out of the race on ratings'))
# T time-varying: does the effect drift year by year?
for f in ['dyn_nat', 'f_lstarts', 'f_avgfp3', 'a_fs3', 'c_rec', 'a_wt_rel', 'r_ldays']:
    D.append(run(f + ' x year', 'T time-varying', (lambda f: (lambda d: d[f + '_z'] * d.yr))(f), 'is this relationship getting stronger or weaker over time?'))
# C feature x context
for f in ['dyn_nat', 'f_avgfp3', 'f_lstarts', 'a_fs3', 'a_wt_rel', 'c_rec', 'g_rec', 'j_surp', 't_surp', 'surprise_last', 'age_n', 'r_ldays']:
    for ctx in ['route', 'metro', 'wet', 'big_field', 'vic']:
        D.append(run(f'{f} x {ctx}', 'C context', (lambda f, ctx: (lambda d: d[f + '_z'] * d[ctx]))(f, ctx), 'does this factor matter more in this context?'))
# R replication of Qld Batch 6
for nm, ex, why in [('surprise_last x a_best3', lambda d: d.surprise_last_z * d.a_best3_z, 'Qld: corroborated improvement'), ('dyn_traj x a_best3', lambda d: d.dyn_traj_z * d.a_best3_z, 'Qld: corroborated improvement'),
                    ('dyn_traj x a_rec', lambda d: d.dyn_traj_z * d.a_rec_z, 'Qld: a_avg3 x dyn_traj (closest national analogue)'), ('ability x field strength', lambda d: d.dyn_nat_z * d.fd_z, 'Qld watch list #12'),
                    ('c_rec x wet', lambda d: d.c_rec_z * d.wet, 'Qld #7'), ('class edge (a_fs3) x weight', lambda d: d.a_fs3_z * d.a_wt_rel_z, 'Qld #14 analogue')]:
    D.append(run(nm, 'R replication', ex, why))
# P pairwise among core + new (reduced set)
PS = ['dyn_nat', 'f_avgfp3', 'f_lstarts', 'a_fs3', 'a_best3', 'a_wt_rel', 'c_rec', 'r_ldays', 'surprise_last', 'dyn_traj', 'h2h', 'j_surp', 't_surp', 'age_n', 'dist_change', 'bm_change']
for a, b_ in itertools.combinations(PS, 2):
    D.append(run(f'{a} x {b_}', 'P pairwise', (lambda a, b_: (lambda d: d[a + '_z'] * d[b_ + '_z']))(a, b_), 'systematic screen'))
R = pd.DataFrame([r for r in D if 'p_discovery' in r])
R['bh_q'] = multipletests(R.p_discovery, method='fdr_bh')[1]; R['passes_discovery'] = (R.bh_q < 0.10) & R.same_sign_halves; R['confirmed'] = R.passes_discovery & (R.confirm_lo95 > 0)
R.sort_values('p_discovery').to_csv('engine/out/screen_nat.csv', index=False); pd.DataFrame([r for r in D if 'note' in r]).to_csv('engine/out/screen_nat_skipped.csv', index=False)
print('tested', len(R), '| pass discovery', int(R.passes_discovery.sum()), '| confirmed', int(R.confirmed.sum()), '| positive in confirmation', int((R.confirm_lo95 > 0).sum()), 'vs ~', round(0.025 * len(R)), 'by chance')
cols = ['name', 'family', 'coef_per_sd', 'se', 'bh_q', 'same_sign_halves', 'confirm_gain_per_race', 'confirm_lo95', 'confirm_hi95', 'confirm_top_pick_change_pts', 'confirm_top3_change_pts']
print(R[R.family.isin(['M new feature', 'R replication'])][cols].to_string(index=False))
print(R[R.confirmed].sort_values('confirm_gain_per_race', ascending=False)[cols].to_string(index=False))
# course-specificity for confirmed terms (configurations with 300+ races)
allx = pd.concat([dev, ev]); big = allx.groupby('config').race_id.nunique(); big = big[big >= 300].index; rows_ = []
for nm in R[R.confirmed].name:
    fn = next(r for r in D if r.get('name') == nm)
    ex = {'M new feature': None}
    parts = nm.replace(' (main effect)', '').replace(' squared', '').split(' x ')
    def ex(d, nm=nm, parts=parts):
        if nm.endswith(' squared'): return d[parts[0] + '_z'] ** 2
        out = 1.0
        for p_ in parts: out = out * (d[p_ + '_z'] if p_ + '_z' in d else d[p_])
        return out
    try: t_all = term(allx, ex)
    except Exception as e_: print('skip', nm, e_); continue
    t_all = t_all / (np.std(t_all) or 1); bs_, ses_ = [], []
    for cfg in big:
        m_ = (allx.config == cfg).values; sub = allx[m_]
        Rt = H.Races(sub.race_id.values, sub.win.values, sub.offset.values, t_all[m_][:, None]); bb = H.fit(Rt, np.array([1e-6])); se_ = H.posterior_sd(Rt, bb, np.array([1e-6]))[0]
        bs_.append(bb[0]); ses_.append(se_); rows_.append({'term': nm, 'config': cfg, 'races': sub.race_id.nunique(), 'coef': round(float(bb[0]), 4), 'se': round(float(se_), 4)})
    bs_, w_ = np.array(bs_), 1 / np.array(ses_) ** 2; pooled = (bs_ * w_).sum() / w_.sum(); Q = float(((bs_ - pooled) ** 2 * w_).sum()); k_ = len(bs_)
    from scipy.stats import chi2
    rows_.append({'term': nm, 'config': 'ALL (pooled)', 'coef': round(pooled, 4), 'Q': round(Q, 1), 'df': k_ - 1, 'p_heterogeneity': round(float(chi2.sf(Q, k_ - 1)), 4), 'I2_%': round(max(0, (Q - (k_ - 1)) / Q) * 100, 1) if Q > 0 else 0})
CS = pd.DataFrame(rows_); CS.to_csv('engine/out/screen_nat_course_specificity.csv', index=False)
if len(CS): print(CS[CS.config == 'ALL (pooled)'].to_string(index=False))
