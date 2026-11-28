"""Batch 26 Part 2: why the rating scale STRETCHES, and whether level AND spread can be stabilised point in time. RESEARCH ONLY.
Re-uses the Batch 25 rating re-run (batch25/b25_scale.py definitions: same runs, same order, P0 production and C0 consolidated rules).
References: time figures (independent physical measure, own limits: course par + daily variant, weak within-horse development) and the
handicappers' official benchmark classes (independent human scale; class mix changes). Neither is treated as ground truth.
S1 rating distribution by official class and year (BM58/64/70/78): mean, sd, p10/p50/p90, against the same runners' time figures
S2 spread vs the physical measure: slope of rating on 5-run time figure (established horses) by year, overall, by tier and state
S3 composition: within each class and year - runs held, age, share of horses in their first history year; class gap for horses with
   20+ held runs only (fixed experience); same-horse vs entrant vs leaver contributions to a class's level change 2023 -> 2026
S4 mechanism: net rating change per run by grade and year (grade flows / asymmetric responsiveness); entry level by grade
S5 anchors (point in time, fitted on half the horses, months BEFORE the month only):
   AF   level, by the month of the race (Batch 25: uniform within a race = display level only)
   AFs  level + spread, by race month: R' = c + s (R - c), s = slope_ref / slope_m (rating per figure point), two references:
        'ref23' = 2023 slope, 'cum' = slope over all months to date
   AFu  level by the month the horse's rating was LAST UPDATED (its previous run) - reconstructs each carried rating on the scale of
        its own time, so within-race differences (e.g. long-break returners vs active horses) and historical inputs change
   AFus level + spread by last-update month
Tests: Batch 25 T0-T8 (T0 = forecast log-likelihood now recomputed with the transformed ratings), plus
   T9  grade ladder: kg per official BM point by year, and each grade's level sd across years (stable ladder = lower)
   T10 long-term form: surprise of returners by break length (90-179, 180-364, 365+ days) - a stale scale shows up here
   T11 historical input: last-start field strength (mean pre-race rating of that race's runners) raw vs reconstructed, by gap
Output batch26/out_b26_stretch.json."""
import os, sys, json, time
sys.argv = ['b26']
src = open('batch25/b25_scale.py').read().split("R_ALL = {}; res = {}")[0]
exec(src)
T1 = time.time()
r_P0 = rate(d, rule='P0'); r_C0 = rate(d, rule='C0'); log('rated P0, C0')
bmv = U.set_index('row')['bm']; clv = U.set_index('row')['class_label']
base['bm'] = bmv.reindex(base.row).values; base['cl'] = clv.reindex(base.row).values
BMR = NAT & base.cl.isin(['Benchmark', 'BM']) & base.bm.isin([58, 64, 70, 78]) & (base.field >= 6)
base['entry_year'] = base.groupby('horse').year.transform('min')
# previous run month (the month a carried pre-race rating was last updated)
order = base.sort_values(['horse', 'date', 'race_key']).index
pm = base.loc[order].groupby('horse').month.shift(); base['prev_month'] = pm.reindex(base.index)
out = {}

def describe(name, R):
    o = {}
    df = base.loc[BMR, ['bm', 'year', 'k', 'age', 'entry_year', 'fig_prev5', 'horse']].copy(); df['R'] = R[df.index]
    t = df.groupby(['bm', 'year']).R.describe(percentiles=[.1, .5, .9])[['count', 'mean', 'std', '10%', '50%', '90%']].round(2)
    o['S1_rating_by_class_year'] = {f'{int(b)}|{int(y)}': r_.to_dict() for (b, y), r_ in t.iterrows()}
    f = df.groupby(['bm', 'year']).fig_prev5.mean().unstack().round(2); o['S1_figure_by_class_year'] = {int(b): {int(y): v for y, v in r_.dropna().items()} for b, r_ in f.iterrows()}
    g = df.groupby(['bm', 'year']).R.mean().unstack(); o['S1_class_gap_78_minus_58_rating'] = {int(y): round(float(g.loc[78, y] - g.loc[58, y]), 2) for y in g.columns}
    o['S1_class_gap_78_minus_58_figure_points'] = {int(y): round(float(f.loc[78, y] - f.loc[58, y]), 2) for y in f.columns if pd.notna(f.loc[78, y])}
    e = df[df.k >= 20]; ge = e.groupby(['bm', 'year']).R.mean().unstack()
    o['S3_class_gap_20plus_runs'] = {int(y): round(float(ge.loc[78, y] - ge.loc[58, y]), 2) for y in ge.columns if pd.notna(ge.loc[78, y]) and pd.notna(ge.loc[58, y])}
    comp = df.groupby(['bm', 'year']).agg(runs_held=('k', 'mean'), age=('age', 'mean'), first_history_year=('entry_year', lambda s: float((s == df.loc[s.index, 'year']).mean())))
    o['S3_composition'] = {f'{int(b)}|{int(y)}': {k: round(float(v), 2) for k, v in r_.items()} for (b, y), r_ in comp.iterrows()}
    # same-horse vs entrant vs leaver contributions to each class's mean change 2023 -> 2026 (horse means)
    c = {}
    for b in [58, 64, 70, 78]:
        a = df[(df.bm == b) & (df.year == 2023)].groupby('horse').R.mean(); z = df[(df.bm == b) & (df.year == 2026)].groupby('horse').R.mean()
        both = a.index.intersection(z.index)
        c[b] = {'change_all': round(float(z.mean() - a.mean()), 2), 'horses_2023': int(len(a)), 'horses_2026': int(len(z)), 'in_both': int(len(both)),
                'same_horses_change': round(float((z[both] - a[both]).mean()), 2) if len(both) > 20 else None,
                'leavers_vs_stayers_2023': round(float(a.drop(both).mean() - a[both].mean()), 2) if len(both) > 20 else None,
                'entrants_vs_stayers_2026': round(float(z.drop(both).mean() - z[both].mean()), 2) if len(both) > 20 else None}
    o['S3_class_change_decomposition_2023_2026'] = c
    # S2 slope of rating on figure, established horses, by year; by tier; by state
    def slope(m):
        x = base.loc[m, 'fig_prev5'].astype(float); y = R[m]
        return round(float(np.polyfit(x, y, 1)[0]), 4) if m.sum() > 500 else None
    o['S2_slope_by_year'] = {int(y): slope(EST & NAT & (base.year == y)) for y in range(2023, 2027)}
    o['S2_slope_by_tier_year'] = {t_: {int(y): slope(EST & NAT & (base.tier == t_) & (base.year == y)) for y in range(2023, 2027)} for t_ in ['metro', 'provincial', 'country']}
    o['S2_slope_by_state_year'] = {s_: {int(y): slope(EST & (base.state == s_) & (base.year == y)) for y in range(2023, 2027)} for s_ in ['NSW', 'VIC', 'SA', 'WA', 'QLD']}
    o['S2_sd_rating_established_by_year'] = {int(y): round(float(R[EST & NAT & (base.year == y)].std()), 3) for y in range(2023, 2027)}
    o['S2_sd_figure_established_by_year'] = {int(y): round(float(base.loc[EST & NAT & (base.year == y), 'fig_prev5'].astype(float).std()), 3) for y in range(2023, 2027)}
    return o

def mechanism(name, r):
    df = base[['year', 'bm', 'cl', 'k', 'field']].copy(); df['dR'] = r['post'] - r['pre']; df['used'] = ~np.isnan(r['inn']); df['first'] = r['first']
    df = df[NAT & df.used & df.cl.isin(['Benchmark', 'BM']) & df.bm.isin([58, 64, 70, 78])]
    o = {'net_change_per_run_by_grade_year': {f'{int(b)}|{int(y)}': round(float(v), 3) for (b, y), v in df.groupby(['bm', 'year']).dR.mean().items()}}
    est = df[df.k >= 8]; o['established_change_per_run_by_grade_year'] = {f'{int(b)}|{int(y)}': round(float(v), 3) for (b, y), v in est.groupby(['bm', 'year']).dR.mean().items()}
    # movement between grades: consecutive runs of the same horse in different BM grades within 60 days -> rating change across the move
    m = base[NAT & base.cl.isin(['Benchmark', 'BM']) & base.bm.notna()][['horse', 'date', 'bm', 'year']].copy(); m['R'] = r['pre'][m.index]
    m = m.sort_values(['horse', 'date']); m['pbm'] = m.groupby('horse').bm.shift(); m['pR'] = m.groupby('horse').R.shift(); m['pd'] = m.groupby('horse').date.shift()
    m = m[m.pbm.notna() & ((m.date - m.pd).dt.days <= 60)]; m['step'] = np.sign(m.bm - m.pbm)
    o['grade_moves'] = {f'{lab}|{int(y)}': round(float(v), 3) for (s_, y), v in m.groupby(['step', 'year']).apply(lambda q: (q.R - q.pR).mean()).items() for lab in [{-1.0: 'down', 0.0: 'same', 1.0: 'up'}[s_]]}
    return o

HALF = ~HB          # anchors fitted on this half of the horses
def monthly_fit(R):
    """per month: established-horse mean of rating, mean figure, and slope of rating on figure (tier/distance adjusted), fit half only"""
    df = base.loc[EST & NAT & HALF, ['month', 'tier', 'dband', 'fig_prev5', 'year']].copy(); df['R'] = R[df.index]; df['F'] = df.fig_prev5.astype(float)
    df['Ra'] = tier_adjust(df, 'R')
    g = df.groupby('month'); months = pd.period_range(base.month.min(), base.month.max(), freq='M')
    mR = g.Ra.mean().reindex(months); mF = g.F.mean().reindex(months)
    sl = g.apply(lambda q: np.polyfit(q.F, q.Ra, 1)[0] if len(q) > 200 else np.nan).reindex(months)
    return months, mR, mF, sl

def build_anchor(R, beta, kind, ref):
    months, mR, mF, sl = monthly_fit(R)
    res_m = (mR - beta * mF)                                                    # level residual per month
    lvl = res_m.ewm(alpha=0.5, ignore_na=True).mean().shift(1); lvl0 = res_m.iloc[:12].mean(); off = (lvl - lvl0).fillna(0.0)
    ctr = mR.ewm(alpha=0.5, ignore_na=True).mean().shift(1).bfill()
    slp = sl.ewm(alpha=0.3, ignore_na=True).mean().shift(1)
    if ref == 'ref23': sref = float(sl[[m for m in sl.index if m.year == 2023]].mean())
    else: sref = None
    if ref == 'cum': s_ = (sl.expanding().mean().shift(1) / slp)
    elif ref == 'ref23': s_ = (sref / slp)
    else: s_ = pd.Series(1.0, index=months)
    s_ = s_.clip(0.6, 1.6).fillna(1.0)
    return off, ctr, s_

def transform(r, beta, kind, ref=None):
    R = pd.Series(r['pre'], index=base.index); Rp = pd.Series(r['post'], index=base.index)
    off, ctr, s_ = build_anchor(R, beta, kind, ref)
    use_m = base.prev_month.fillna(base.month) if kind == 'update' else base.month   # month whose scale the carried rating belongs to (first runs: today's)
    o = use_m.map(off).astype(float).fillna(0.0).values; c = use_m.map(ctr).astype(float).fillna(0.0).values; s = use_m.map(s_).astype(float).fillna(1.0).values
    om = base.month.map(off).astype(float).fillna(0.0).values; cm = base.month.map(ctr).astype(float).fillna(0.0).values; sm = base.month.map(s_).astype(float).fillna(1.0).values
    Rn = c + s * ((R.values - o) - c)
    Rpn = cm + sm * ((Rp.values - om) - cm)       # post-race rating lives on this race's month scale
    # recompute the race-relative surprise with the transformed pre-race ratings (perf is unchanged); sd scales with s
    inn = pd.Series(r['inn'], index=base.index); ok = inn.notna()
    pre = R.where(ok); prel = pre - pre.groupby(base.race_key).transform('mean'); perf_rel = inn + prel
    Rn_s = pd.Series(Rn, index=base.index).where(ok); rn_rel = Rn_s - Rn_s.groupby(base.race_key).transform('mean')
    r2 = dict(r); r2['pre'] = Rn; r2['post'] = Rpn; r2['inn'] = (perf_rel - rn_rel).values; r2['sd'] = r['sd'] * s
    return r2, {'offset_last': round(float(off.iloc[-1]), 3), 'scale_last': round(float(s_.iloc[-1]), 3)}

def extra_tests(r):
    R = pd.Series(r['pre'], index=base.index); inn = pd.Series(r['inn'], index=base.index); o = {}
    df = base.loc[BMR, ['bm', 'year']].copy(); df['R'] = R[df.index]
    g = df.groupby(['year', 'bm']).R.mean().unstack()
    o['T9_kg_per_bm_point_by_year'] = {int(y): round(float(np.polyfit(np.array([58, 64, 70, 78], float), g.loc[y, [58, 64, 70, 78]].values.astype(float), 1)[0]), 3) for y in g.index if g.loc[y].notna().all()}
    rel = g.sub(g.mean(axis=1), axis=0); o['T9_grade_level_sd_across_years'] = round(float(rel.loc[2023:].std().mean()), 3)
    rt = base[NAT & (base.k >= 3) & inn.notna() & (base.gap >= 90)].copy(); rt['inn'] = inn[rt.index]
    rt['gb'] = pd.cut(rt.gap, [89, 179, 364, 5000], labels=['90-179', '180-364', '365+']).astype(str)
    o['T10_returner_surprise_by_break'] = {k: round(float(v), 3) for k, v in rt.groupby('gb').inn.mean().items()}
    o['T10_returner_surprise_by_break_year'] = {f'{a}|{int(b)}': round(float(v), 3) for (a, b), v in rt.groupby(['gb', 'year']).inn.mean().items()}
    # T11 historical input: last-start field strength (race mean of pre-race ratings at the horse's previous run)
    fs = R.groupby(base.race_key).transform('mean'); x = base[['horse', 'date', 'race_key', 'gap']].copy(); x['fs'] = fs
    x = x.sort_values(['horse', 'date', 'race_key']); x['last_fs'] = x.groupby('horse').fs.shift()
    x['cur_fs'] = fs[x.index]
    q = x[NAT[x.index] & x.last_fs.notna() & x.gap.notna()]
    q['gb'] = pd.cut(q.gap, [0, 28, 89, 179, 5000], labels=['<=28', '29-89', '90-179', '180+']).astype(str)
    o['T11_last_start_field_minus_this_field_kg_by_gap'] = {k: round(float(v), 3) for k, v in (q.last_fs - q.cur_fs).groupby(q.gb).mean().items()}
    return o

KEYS = ['T0_loglik_2024', 'T0_loglik_2025-26', 'T1_holdout_drift_kg_per_year', 'T8_drift_kg_per_year', 'T2_peak_R2', 'T2_residual_trend_kg_per_year', 'T3_6yo+_bias_kg', 'T5_returner_mean_surprise', 'T6_mean_sd_across_years', 'T7_mean_bias_kg']
for name, r in [('P0', r_P0), ('C0', r_C0)]:
    out[name] = {'describe': describe(name, pd.Series(r['pre'], index=base.index)), 'mechanism': mechanism(name, r), 'tests': evaluate(name, r), 'extra': extra_tests(r)}
    log(name, json.dumps({k: out[name]['tests'][k] for k in KEYS}), json.dumps(out[name]['extra']['T9_kg_per_bm_point_by_year']))
    json.dump(out, open('batch26/out_b26_stretch.json', 'w'), indent=1, default=str)
    Rr = pd.Series(r['pre'], index=base.index); beta = fit_beta(Rr, EST & NAT & HALF & (base.year <= 2023))
    for lab, kind, ref in [('AF', 'race', None), ('AFs-ref23', 'race', 'ref23'), ('AFs-cum', 'race', 'cum'), ('AFu', 'update', None), ('AFus-cum', 'update', 'cum')]:
        r2, info = transform(r, beta, kind, ref)
        k = f'{name}+{lab}'
        out[k] = {'info': info, 'describe': {kk: v for kk, v in describe(k, pd.Series(r2['pre'], index=base.index)).items() if kk.startswith(('S1_class_gap', 'S2_slope_by_year', 'S3_class_gap'))},
                  'tests': evaluate(k, r2), 'extra': extra_tests(r2)}
        log(k, json.dumps(info), json.dumps({kk: out[k]['tests'][kk] for kk in KEYS}), json.dumps(out[k]['describe'].get('S1_class_gap_78_minus_58_rating')))
        json.dump(out, open('batch26/out_b26_stretch.json', 'w'), indent=1, default=str)
log('done')
