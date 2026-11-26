"""Batch 14 follow-up s2/s8: each horse's NORMAL finishing profile vs abnormal CHANGES, and what follows over 1, 3 and 5 starts.
Uses /home/claude/b14/profiles.parquet (b14f_profiles.py). Measure: slope = final-200 speed minus 600-400 speed, field-relative (m/s;
+ = finished stronger than it was running 600-400 out, - = slowed more than the field).
usual  = the horse's shrunk mean slope over its EARLIER tracked runs (3 runs' weight towards the population mean); needs 3+ earlier runs
change = (slope - usual) / within-horse sd (pooled)   -> z
Established style (from earlier runs only): habitual fader (usual < -0.10), strong finisher (usual > +0.05), in between.
Abnormal decline: z < -1.5 (finished much weaker than its own normal); abnormal improvement: z > +1.5. Repeated: same direction 2+ starts in a row.
Outcomes: rating surprise next 1 / mean next 3 / mean next 5 (kg); rating change after 1, 3, 5 starts (kg); returned to normal at the
next tracked run (|z| < 1); next start within 180 days (drop-out check). Controls as in b14f_profiles (this-run surprise, rating band,
position, tempo, distance, field, preparation stage, finish, level, track, opposition, going). Qld 2022-26 pooled, SA separately.
Survivorship: horses that stop racing cannot show recovery; drop-out is reported and a worst-case bound is given."""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
def cfit(form, f, key='horse'):
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop'); return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
def co(m, k, nd=2): return (round(m.params[k], nd), round(m.conf_int().loc[k, 0], nd), round(m.conf_int().loc[k, 1], nd)) if k in m.params else None
P = pd.read_parquet('/home/claude/b14/profiles.parquet').sort_values(['state', 'horse', 'meeting_date']).reset_index(drop=True)
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct + m + C(track) + fmean_c + C(going)'
OUT = {}
for st in ['QLD', 'SA']:
    d = P[P.state == st].copy(); g = d.groupby('horse'); n = g.cumcount(); mu = d.slope.mean()
    d['usual'] = ((g.slope.cumsum() - d.slope) + 3 * mu) / (n + 3); d['n_prior'] = n
    w = d[n >= 5]; sdw = (w.slope - w.usual).std(); d['z'] = (d.slope - d.usual) / sdw
    d = d[d.n_prior >= 3].copy(); g = d.groupby('horse')
    d['style'] = np.where(d.usual < -0.10, 'habitual fader', np.where(d.usual > 0.05, 'strong finisher', 'in between'))
    d['decl'] = (d.z < -1.5).astype(int); d['impr'] = (d.z > 1.5).astype(int)
    d['decl2'] = ((d.decl == 1) & (g.decl.shift(1) == 1)).astype(int); d['impr2'] = ((d.impr == 1) & (g.impr.shift(1) == 1)).astype(int)
    d['z_next'] = g.z.shift(-1); d['back_to_normal'] = (d.z_next.abs() < 1).astype(float).where(d.z_next.notna())
    d['races_on'] = (d.gap_next.fillna(9999) <= 180).astype(int); d['early_prep'] = (d.prep_idx.astype(float) <= 2).astype(int)
    r = {'runs with 3+ earlier tracked runs': len(d), 'horses': d.horse.nunique(), 'within-horse sd of slope (m/s)': round(sdw, 3),
         'population sd of slope': round(P[P.state == st].slope.std(), 3), 'share abnormal decline %': round(100 * d.decl.mean(), 1), 'share abnormal improvement %': round(100 * d.impr.mean(), 1),
         'style share %': (100 * d['style'].value_counts(normalize=True)).round(1).to_dict()}
    # a) same raw finish, different meaning? raw slope vs change from normal, fitted together
    f = d.dropna(subset=['inn_n1']).copy(); f['slope_s'] = f.slope / f.slope.std(); f['z_s'] = f.z / f.z.std(); f['usual_s'] = f.usual / f.slope.std()
    m = cfit('inn_n1 ~ z_s + usual_s + ' + CTRL, f); r['next run kg: change from own normal (per sd), own normal (per sd)'] = [co(m, 'z_s'), co(m, 'usual_s')]
    m = cfit('inn_n1 ~ slope_s + ' + CTRL, f); r['next run kg: raw slope (per sd), for comparison'] = co(m, 'slope_s')
    m = cfit('inn_n1 ~ slope_s * C(style) + ' + CTRL, f); r['raw slope effect by established style (interaction vs habitual fader)'] = {k: co(m, k) for k in m.params.index if 'slope_s' in k}
    # b) abnormal changes, isolated vs repeated, across horizons
    hz = {}
    for y in ['inn_n1', 'next3', 'next5', 'rat_chg1', 'rat_chg3', 'rat_chg5']:
        f = d.dropna(subset=[y]); mm = cfit(f'{y} ~ decl + decl2 + impr + impr2 + ' + CTRL, f)
        hz[y] = {'decline (isolated)': co(mm, 'decl'), 'decline repeated (extra)': co(mm, 'decl2'), 'improvement (isolated)': co(mm, 'impr'), 'improvement repeated (extra)': co(mm, 'impr2'), 'n': len(f)}
    r['abnormal changes vs normal runs'] = hz
    # c) persistence: does the change last? back to normal next tracked run %, and repeat probability
    r['next tracked run back within normal range % (all / after decline / after improvement)'] = [round(100 * d.back_to_normal.mean(), 1), round(100 * d[d.decl == 1].back_to_normal.mean(), 1), round(100 * d[d.impr == 1].back_to_normal.mean(), 1)]
    r['repeat next tracked run % (decline after decline vs base / improvement after improvement vs base)'] = [round(100 * (d[d.decl == 1].z_next < -1.5).mean(), 1), round(100 * (d.z_next < -1.5).mean(), 1),
                                                                                                         round(100 * (d[d.impr == 1].z_next > 1.5).mean(), 1), round(100 * (d.z_next > 1.5).mean(), 1)]
    # d) drop-out (survivorship) and a worst-case bound for 'decline'
    r['races again within 180 days % (normal / decline / repeated decline / improvement)'] = [round(100 * d[(d.decl == 0) & (d.impr == 0)].races_on.mean(), 1), round(100 * d[d.decl == 1].races_on.mean(), 1),
                                                                                             round(100 * d[d.decl2 == 1].races_on.mean(), 1), round(100 * d[d.impr == 1].races_on.mean(), 1)]
    f = d.dropna(subset=['next5']); q10 = f.next5.quantile(0.10)
    b = d.copy(); b['next5_b'] = b.next5.where(b.next5.notna() | (b.races_on == 1), q10)          # horses that stopped: assume a bottom-decile outcome
    mm = cfit('next5_b ~ decl + decl2 + impr + impr2 + ' + CTRL, b.dropna(subset=['next5_b']))
    r['worst-case bound: stopped horses given a bottom-decile next-5 (decline, repeated decline)'] = [co(mm, 'decl'), co(mm, 'decl2')]
    # e) context: early vs later in a preparation, distance change, fast tempo
    ctx = {}
    for c, expr in [('early in preparation (runs 1-2)', 'early_prep'), ('distance up 200 m+', 'dist_up'), ('fast early tempo', 'fast_tempo')]:
        f = d.dropna(subset=['next5']).copy()
        if c.startswith('distance'): f['dist_up'] = ((f.d.astype(float) - f.groupby('horse').d.shift(1).astype(float)) >= 200).astype(int)
        if c.startswith('fast'): f['fast_tempo'] = (f.tempo_z.astype(float) > 0.75).astype(int)
        mm = cfit(f'next5 ~ decl * {expr} + impr * {expr} + ' + (CTRL.replace(' + C(prep)', '') if expr == 'early_prep' else CTRL), f)
        ctx[c] = {'decline': co(mm, 'decl'), 'decline x context': co(mm, f'decl:{expr}'), 'improvement x context': co(mm, f'impr:{expr}'), 'n decline in context': int((f.decl * f[expr]).sum())}
    r['context (mean of next 5, kg)'] = ctx
    # f) did the rating already take it in? rating change at once (rat_chg1) vs later (rat_chg5 - rat_chg1), raw means
    r['raw: rating change after 1 start / after 5 starts (normal, decline, improvement)'] = {k: [round(v.rat_chg1.mean(), 2), round(v.rat_chg5.mean(), 2)] for k, v in
                                                                                         [('normal', d[(d.decl == 0) & (d.impr == 0)]), ('decline', d[d.decl == 1]), ('improvement', d[d.impr == 1])]}
    OUT[st] = r; print(st, json.dumps(r, default=str)[:4000], '\n', flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/followup/out_norms.json', 'w'), indent=1, default=str)
