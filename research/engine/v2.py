"""Batch 7, engine v2: add supported new information to the operational models JOINTLY, without double counting.
v2 score = v1 score (frozen operational model, used as a fixed offset) + sum of new-term contributions, where all new terms
are estimated together (so overlapping terms share credit) and only get credit for what v1 does not already know.
Penalty (ridge on the new terms) chosen on an inner split of development races (fit Oct 2022-Dec 2023, score 2024).
Evidence on identical 2025-26 races: cumulative steps, leave-one-family-out from the full v2 (non-additivity), per year.
Rolling-origin backtest with FULL joint refits per window (old features + new terms re-estimated every time):
  train to end-2023 -> test 2024; to end-2024 -> test 2025; to end-2025 -> test 2026.
Outputs engine/out/v2_*.csv, engine/out/v2_choice.json"""
import json, numpy as np, pandas as pd, hier_tools as H
from engine import evaltools as E
U = pd.read_parquet('engine/frames/national.parquet')
SCR = pd.read_csv('engine/out/screen_nat.csv')
INTER = SCR[SCR.family.isin(['C context', 'P pairwise', 'N nonlinear', 'T time-varying', 'R replication']) & (SCR.bh_q < 0.001) & SCR.same_sign_halves].name.tolist()   # chosen on DISCOVERY data only
NFAM2 = {'Jockey & trainer': ['j_surp', 't_surp', 'jt_surp', 'j_change'], 'Age & sex': ['age_n', 'young', 'old', 'female'],
         'Form changes & head-to-head': ['h2h', 'abs_dist_change', 'dist_change', 'dyn_traj', 'surprise_last', 'bm_change', 'wt_change'], 'Interactions (chosen on discovery data only)': INTER}
QFAM2 = {'Horse course/going/distance records': ['c_rec', 'g_rec', 'd_rec'], 'Jockey & trainer': ['j_surp', 't_surp', 'jt_surp', 'j_change'],
         'Form changes & head-to-head': ['h2h', 'dyn_traj', 'surprise_last', 'wt_change']}
def build_terms(x, names):
    """create a race-centred, development-scaled column t::<name> for every term (main effects and products)."""
    x['yr'] = (x.meeting_date.dt.year - 2024).astype(float); x['vic'] = (x.get('state', pd.Series('QLD', index=x.index)) == 'VIC').astype(float)
    x['big_field'] = (x.field >= 12).astype(float); x['field_dyn'] = x.groupby('race_id').dyn_nat.transform('mean'); x['abs_dist_change'] = x.dist_change.abs()
    for c in ['route', 'metro', 'wet']:
        if c not in x: x[c] = 0.0
    x['young'] = (x.age_n <= 3).astype(float).where(x.age_n.notna()) if 'age_n' in x else np.nan; x['old'] = (x.age_n >= 7).astype(float).where(x.age_n.notna()) if 'age_n' in x else np.nan
    base = sorted({p for n in names for p in n.replace(' squared', '').replace(' x ', '|').split('|') if p not in ('route', 'metro', 'wet', 'big_field', 'vic', 'year', 'ability', 'field strength')} | {'dyn_nat'})
    x = E.zcols(x, [b for b in base if b in x])
    x['fd_z'] = (x.field_dyn - x.field_dyn.mean()) / x.field_dyn.std(); dev = x.period == 'development'
    for n in names:
        if n == 'ability x field strength': t = x.dyn_nat_z * x.fd_z
        elif n.endswith(' squared'): t = x[n.split(' ')[0] + '_z'] ** 2
        elif ' x ' in n:
            t = 1.0
            for p in n.split(' x '): t = t * (x[p + '_z'] if p + '_z' in x else (x.yr if p == 'year' else x[p]))
        else: t = x[n + '_z'] if n + '_z' in x else x[n]
        t = pd.Series(np.nan_to_num(np.asarray(t, dtype=float)), index=x.index); t = t - t.groupby(x.race_id).transform('mean'); sd = t[dev].std() or 1.0
        x['t::' + n] = t / sd
    return x
def offset_v1(x, kind):
    if kind == 'nat':
        mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
        return sum(C2[c] * ((x[c].astype(float) - x.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0) for c in C2).values
    x = E.zcols(x, list(E.QCOEF)); return x[[c + '_z' for c in E.QCOEF]].values @ np.array(list(E.QCOEF.values()))
def fitd(x, terms, mask, off, tau):
    d = x[mask]; R = H.Races(d.race_id.values, d.win.values, off[mask.values], d[['t::' + t for t in terms]].values); return H.fit(R, np.full(len(terms), tau))
def met(x, terms, b, off, mask): return E.metrics(x, off + (x[['t::' + t for t in terms]].values @ b if terms else 0), mask)
def choose_tau(x, terms, off):
    dv = x.period == 'development'; a = dv & (x.meeting_date < '2024-01-01'); bm = dv & (x.meeting_date >= '2024-01-01'); best = None
    for tau in [1e-6, 10, 100, 1000, 5000]:
        b = fitd(x, terms, a, off, tau); r = met(x, terms, b, off, bm); ll = r.lp.sum()
        if best is None or ll > best[1]: best = (tau, ll)
    return best[0]
def run(kind, FAM):
    x = E.nat_frame(U) if kind == 'nat' else E.qld_frame(U)
    allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, kind)
    dev, ev = x.period == 'development', x.period == 'evaluation'
    r1 = met(x, [], None, off, ev); rows = [{'kind': 'version', 'model': 'v1 operational', **E.summary(r1)}]; terms = []; R = {'v1': r1}
    for fam, ts in FAM.items():                                                    # cumulative steps
        terms = terms + ts; tau = choose_tau(x, terms, off); b = fitd(x, terms, dev, off, tau); r = met(x, terms, b, off, ev)
        d = E.diff(r1, r); dp = E.diff(R[list(R)[-1]], r); R['+' + fam] = r
        rows.append({'kind': 'cumulative', 'model': '+ ' + fam, 'tau': tau, **E.summary(r), **{'vs_v1_' + k: v for k, v in d.items() if k != 'races'}, **{'step_' + k: v for k, v in dp.items() if k in ('lp', 'lp_lo', 'lp_hi', 'hit', 'top3', 'rho')}})
    full = R[list(R)[-1]]; tauF = rows[-1]['tau']; bF = fitd(x, allt, dev, off, tauF)
    for fam, ts in FAM.items():                                                    # leave one family out of the full v2
        keep = [t for t in allt if t not in ts]; b = fitd(x, keep, dev, off, tauF); r = met(x, keep, b, off, ev); d = E.diff(r, full)
        rows.append({'kind': 'leave family out', 'model': '- ' + fam, **E.summary(r), **{'family_adds_' + k: v for k, v in d.items() if k in ('lp', 'lp_lo', 'lp_hi', 'hit', 'top3', 'rho')}})
    for yr in [2025, 2026]:
        m = full.date.dt.year == yr; d = E.diff(r1[m], full[m]); rows.append({'kind': f'full v2 vs v1, {yr} only', 'model': 'v2', 'races': int(m.sum()), **{'vs_v1_' + k: v for k, v in d.items() if k != 'races'}})
    # calibration of the winner probabilities, v1 vs v2 (eval): mean predicted vs actual by decile of predicted chance
    for nm, e in [('v1', off), ('v2', off + x[['t::' + t for t in allt]].values @ bF)]:
        t = x.loc[ev, ['race_id', 'win']].copy(); t['e'] = e[ev.values]; mx = t.groupby('race_id').e.transform('max'); t['p'] = np.exp(t.e - mx); t['p'] /= t.groupby('race_id').p.transform('sum')
        t['bin'] = pd.qcut(t.p, 10, labels=False, duplicates='drop'); c = t.groupby('bin').agg(pred=('p', 'mean'), act=('win', 'mean'))
        rows.append({'kind': 'calibration', 'model': nm, 'calib_abs_error_pts': round(100 * float((c.pred - c.act).abs().mean()), 3), 'calib_top_decile_pred_vs_actual': f"{100 * c.pred.iloc[-1]:.1f} vs {100 * c.act.iloc[-1]:.1f}"})
    T = pd.DataFrame(rows); T.to_csv(f'engine/out/v2_{kind}.csv', index=False)
    coef = pd.DataFrame({'term': allt, 'coef_per_sd': np.round(bF, 4)}); coef.to_csv(f'engine/out/v2_{kind}_coefficients_devfit.csv', index=False)
    # rolling origin: everything re-estimated per window (old features + new terms), small fixed penalty on new terms
    old = E.NV2 if kind == 'nat' else list(E.QCOEF); x = E.zcols(x, old); rr = []
    for test in [2024, 2025, 2026]:
        tr = (x.meeting_date.dt.year < test).values; te = (x.meeting_date.dt.year == test).values
        d = x[tr]; R0 = H.Races(d.race_id.values, d.win.values, np.zeros(len(d)), d[[c + '_z' for c in old]].values); b0 = H.fit(R0, np.full(len(old), 1e-6))
        R2 = H.Races(d.race_id.values, d.win.values, np.zeros(len(d)), np.c_[d[[c + '_z' for c in old]].values, d[['t::' + t for t in allt]].values])
        b2 = H.fit(R2, np.r_[np.full(len(old), 1e-6), np.full(len(allt), tauF)])
        e0 = x[[c + '_z' for c in old]].values @ b0; e2 = np.c_[x[[c + '_z' for c in old]].values, x[['t::' + t for t in allt]].values] @ b2
        m0, m2 = E.metrics(x, e0, pd.Series(te, index=x.index)), E.metrics(x, e2, pd.Series(te, index=x.index)); d_ = E.diff(m0, m2)
        rr.append({'test_year': test, 'train_races': int(d.race_id.nunique()), 'v1 features fit_%': E.summary(m0)['fit_%'], 'v2 fit_%': E.summary(m2)['fit_%'], 'v1 top_pick_%': E.summary(m0)['top_pick_%'], 'v2 top_pick_%': E.summary(m2)['top_pick_%'], **{'gain_' + k: v for k, v in d_.items()}})
    RR = pd.DataFrame(rr); RR.to_csv(f'engine/out/v2_{kind}_rolling.csv', index=False)
    print(kind); print(T.to_string(index=False)); print(RR.to_string(index=False)); return T, RR, coef
run('qld', QFAM2)
run('nat', NFAM2)
