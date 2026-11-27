"""Batch 25 Part A (Damo 28 Nov 8:19am): rating-scale stability. RESEARCH ONLY - nothing here is served, frozen engines untouched.

Question: the rating scale drifts mechanically (Batch 24). Which parts of the rating mechanism cause it, does a stable scale help the
uses Damo listed, and can the drift be stopped without forcing annual averages to match?

Rating mechanism re-run here (same runs, same order, every run rated before it is used), from the production run table
(national_runs_c2.parquet = Engine v2.3 history, weight credit 0.25 kg/kg):
  P0   production rule (s 4.5, q 0.05, sig0 5.0, d0 2.0, margins capped at 25 L)
  C0   consolidated-candidate rule (12 L cap in the figure, good runs x (1 + 0.8 exp(-n/6)) with history-completeness experience n,
       certainty-weighted race reference)
  +K   CONSERVATIVE update (route b): inside each race the net rating change the race creates (sum of K x surprise, which is not zero
       because K differs between horses and good runs are scaled) is taken back from every runner in proportion to K, so a race no
       longer creates or destroys rating; relative moves are unchanged in sign and nearly unchanged in size
  +D   ADAPTIVE start (route b): a horse with no held run starts d0_t below its field's known horses, where d0_t follows (point in
       time, only earlier debuts) how far real first runs finished from their starting level, instead of a fixed 2.0 kg
Post-hoc re-anchoring (route a), applied to the ratings of a variant, point in time (month m uses months before m only):
  AF   time-figure anchor: offset(m) = mean over ESTABLISHED horses (8+ held runs, aged 4-7) of [pre-race rating - beta x their
       mean time figure over the previous 5 runs], tier-adjusted, relative to the first year; ratings shifted by -offset(m).
       Time figures (venue x distance par + daily variant from times only) never use ratings, so the anchor is independent.
  AR   reference-horse chain: offset increments = mean change in rating of the same established horses between consecutive
       months minus beta x their mean change in time figure (their genuine change, measured physically).
Neither forces population averages: horses keep their differences; a horse that genuinely improves still rises.

Decomposition of the drift (per year): net rating created per run inside races, split by who creates it (first held run, runs 2-3,
returns from 90+ days, the good-run multiplier, other established runs); entry level of newcomers vs their field; level at exit and
decline before exit (selective retirement); turnover (share of runs by horses that entered that year); genuine development (time-
figure change with age, converted to kg) - the part a stable scale must keep.

Uses tested (stable scale should help; each reported for every variant):
  T0 forecast accuracy (Gaussian log-likelihood of race-relative performance, 2024 and 2025-26) - must not get worse
  T1 scale drift vs physical measure (yearly intercept of rating on time figure, established horses) - target 0
  T2 historical peaks: peak rating vs peak time figure across horses peaking in different years (residual trend by peak year, R2)
  T8 official class anchor: mean rating of runners in BM58/64/70/78 races by year (handicappers' scale; uses neither our ratings
     nor time figures) - the non-circular check of the time-figure anchor
  Anchors are fitted on half the horses; T1 (hold-out), T2, T3 and T6 are measured on the other half (avoids circular evaluation)
  T3 decline detection: same-horse 10-15-month changes, rating vs time figure (bias and correlation), 6yo+
  T4 career development: rating change by age vs time-figure change by age (agreement)
  T5 long-break returners: surprise at the first run back (120+ days) by year (trend) and its spread
  T6 interstate comparisons: state level (rating - beta x figure, established metro/provincial horses) by year (stability)
  T7 venue strength: venue-year field rating vs venue-year time figure (within-venue year-to-year agreement)
Outputs: batch25/out_b25_scale.json (+ csv tables). Usage (from research/): python3 batch25/b25_scale.py"""
import os, sys, json, time
os.environ['WCREDIT'] = '0.25'
import numpy as np, pandas as pd
sys.path.insert(0, '.')
import dyn_rating as DR
T0 = time.time(); log = lambda *a: print(f'[{time.time()-T0:6.0f}s]', *a, flush=True)
S, Q, SIG0, D0 = 4.5, 0.05, 5.0, 2.0

U = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'state',
                                                         'venue', 'tier', 'field', 'fig_n', 'gap', 'bm', 'class_label'])
U['date'] = pd.to_datetime(U.date); U['row'] = np.arange(len(U))
A = pd.read_parquet('engine/frames/age_at_run.parquet').drop_duplicates(['race_key', 'horse'])
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'n_eff']).drop_duplicates(['race_key', 'horse'])
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                   'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'row': U.row})
d = DR.prepare(dn)
ok_ = d.perf.notna()
d['perf12'] = np.where(ok_, -d.margin_l.clip(upper=12) * d.kgpl + 0.25 * (d.weight_kg - 57), np.nan)
d = d.merge(A, on=['race_key', 'horse'], how='left').merge(E, on=['race_key', 'horse'], how='left')
d = d.sort_values(['date', 'race_key', 'finish_pos'], na_position='last').reset_index(drop=True)
if os.environ.get('SMOKE'): d = d[d.date < '2024-03-01'].reset_index(drop=True)
log('prepared', len(d), 'runs', d.race_key.nunique(), 'races')

def rate(d, rule='P0', conserve=False, adaptive=False):
    """Returns per-run arrays: pre, post (rating after the run; = pre if not used), sd, innov (surprise), K, created (this run's
    share of the race's net created rating), gx (good-run multiplier used), first (no held run before), d0 used."""
    perf = (d.perf12 if rule == 'C0' else d.perf).values
    ref = rule == 'C0'; neff = d.n_eff.values.astype(float)
    n = len(d); pre = np.full(n, np.nan); post = np.full(n, np.nan); sd = np.full(n, np.nan); inn = np.full(n, np.nan)
    Kx = np.full(n, np.nan); cre = np.full(n, np.nan); gxa = np.full(n, np.nan); first = np.zeros(n, bool); d0u = np.full(n, np.nan)
    mu, var, last, cnt = {}, {}, {}, {}
    horses = d.horse.values; dates = d.date.values.astype('datetime64[D]').astype(np.int64); keys = d.race_key.values
    starts = np.r_[0, np.flatnonzero(keys[1:] != keys[:-1]) + 1, n]
    d0 = D0; dbuf = []
    for a, b in zip(starts[:-1], starts[1:]):
        hs = horses[a:b]; t = dates[a]
        known = [mu[h] for h in hs if h in mu]; base = (np.mean(known) if known else 0.0) - d0
        isnew = np.array([h not in mu for h in hs]); first[a:b] = isnew; d0u[a:b] = d0
        m = np.array([mu.get(h, base) for h in hs])
        v = np.array([min(var[h] + Q * (t - last[h]), SIG0 ** 2) if h in var else SIG0 ** 2 for h in hs])
        pre[a:b] = m; sd[a:b] = np.sqrt(v); post[a:b] = m
        ok = ~np.isnan(perf[a:b])
        if ok.sum() >= 2:
            pm, mm, vv = perf[a:b][ok], m[ok], v[ok]; pv = vv + S * S
            if ref: w = (1 / pv) / (1 / pv).sum(); u = (pm - (w * pm).sum()) - (mm - (w * mm).sum())
            else: u = (pm - pm.mean()) - (mm - mm.mean())
            idx = np.arange(a, b)[ok]; inn[idx] = u; K = vv / pv; Kx[idx] = K
            if rule == 'C0':
                ne = np.array([cnt.get(h_, 0) for h_ in hs[ok]], float); ne = np.where(np.isnan(neff[a:b][ok]), ne, neff[a:b][ok])
                gx = np.where(u > 0, 1 + 0.8 * np.exp(-ne / 6.0), 1.0)
            else: gx = np.ones(ok.sum())
            gxa[idx] = gx; dm = K * gx * u
            c = dm.sum()
            if conserve and abs(c) > 0: dm = dm - c * K / K.sum()
            cre[idx] = dm                 # this run's actual rating change (sums to the race's net created rating; ~0 when conserving)
            m2 = m.copy(); m2[ok] = mm + dm; post[idx] = m2[ok]
            v2 = v.copy(); v2[ok] = (1 - K) * vv
            if adaptive:          # realised first-run level vs the level it was given; d0 follows the last 2,000 first runs (point in time)
                nw = isnew[ok]
                if nw.any():
                    dbuf.extend(list(u[nw])); dbuf = dbuf[-2000:]
                    if len(dbuf) >= 200: d0 = float(np.clip(D0 - np.mean(dbuf), 0.0, 4.0))
            for h_ in hs[ok]: cnt[h_] = cnt.get(h_, 0) + 1
            m, v = m2, v2
        for h, mm_, vv_, o in zip(hs, m, v, ok):
            if o or h not in mu: mu[h] = mm_; var[h] = vv_; last[h] = t
    return dict(pre=pre, post=post, sd=sd, inn=inn, K=Kx, cre=cre, gx=gxa, first=first, d0=d0u)

base = d[['race_key', 'horse', 'date', 'row', 'age', 'n_eff']].copy()
base = base.merge(U[['row', 'state', 'venue', 'tier', 'field', 'fig_n', 'gap', 'distance_m']], on='row', how='left')
base['year'] = base.date.dt.year; base['month'] = base.date.dt.to_period('M')
base = base.sort_values(['horse', 'date', 'race_key']).reset_index()     # 'index' = position in d
base['k'] = base.groupby('horse').cumcount()
g = base.groupby('horse'); base['fig_prev5'] = g.fig_n.transform(lambda s: s.shift().rolling(5, min_periods=3).mean())
base['next_date'] = g.date.shift(-1); base['last_run'] = base.next_date.isna()
base = base.set_index('index').sort_index()
base['dband'] = pd.cut(base.distance_m, [0, 1100, 1300, 1500, 1800, 2200, 5000], labels=False)
NAT = base.state != 'QLD'
EST = (base.k >= 8) & base.age.between(4, 7) & base.fig_prev5.notna() & (base.field >= 6)
import zlib
HB = base.horse.map(lambda h: zlib.crc32(str(h).encode()) % 2 == 1)    # hold-out half of horses: anchors are fitted on the other half only
bmv = U.set_index('row').reindex(base.row)['bm'] if 'bm' in U else None

def ll(inn, sd):
    pv = sd ** 2 + S * S; return -0.5 * np.log(2 * np.pi * pv) - inn ** 2 / (2 * pv)

def tier_adjust(df, col):          # remove tier and distance-band level differences (estimated on 2022-23 only)
    ref = df[df.year <= 2023]; adj = (ref.groupby(['tier', 'dband'])[col].mean() - ref[col].mean()).rename('_adj').reset_index()
    m = df[['tier', 'dband']].merge(adj, on=['tier', 'dband'], how='left')['_adj'].fillna(0.0).values
    return df[col] - m

def fit_beta(R, mask):             # kg per time-figure point, established horses 2022-23 (cross-section, within tier x distance)
    x = base.loc[mask, 'fig_prev5'].astype(float); y = R[mask]
    grp = base.loc[mask, 'tier'].astype(str) + base.loc[mask, 'dband'].astype(str)
    xd = x - x.groupby(grp).transform('mean'); yd = y - y.groupby(grp).transform('mean')
    return float((xd * yd).sum() / (xd ** 2).sum())

def anchors(R, beta):
    """Point-in-time offsets by month. AF: established horses' rating minus beta x figure, tier-adjusted; offset(m) = EWMA of the
    monthly residual mean over months BEFORE m, relative to the first 12 months. AR: same horses month to month."""
    df = base.loc[EST & NAT & ~HB, ['month', 'year', 'tier', 'dband', 'horse', 'fig_prev5']].copy(); df['R'] = R[df.index]
    df['res'] = df.R - beta * df.fig_prev5.astype(float); df['res'] = tier_adjust(df, 'res')
    mm = df.groupby('month').res.mean(); months = pd.period_range(base.month.min(), base.month.max(), freq='M')
    mm = mm.reindex(months)
    ref0 = mm.iloc[:12].mean(); off_af = (mm.ewm(alpha=0.5, ignore_na=True).mean().shift(1) - ref0).fillna(0.0)
    # AR: same horse in consecutive months: mean over horses of [dR - beta dF]
    hm = df.groupby(['horse', 'month']).agg(R=('R', 'mean'), F=('fig_prev5', 'mean')).reset_index().sort_values(['horse', 'month'])
    hm['pm'] = hm.groupby('horse').month.shift(); hm['dR'] = hm.R - hm.groupby('horse').R.shift(); hm['dF'] = hm.F.astype(float) - hm.groupby('horse').F.shift().astype(float)
    mi = hm.month.map(lambda p: p.year * 12 + p.month); hm['gapm'] = mi - mi.groupby(hm.horse).shift()
    hm = hm[hm.pm.notna() & (hm.gapm <= 2)]
    inc = (hm.dR - beta * hm.dF).groupby(hm.month).mean().reindex(months).fillna(0.0)
    off_ar = inc.cumsum().shift(1).fillna(0.0)
    return off_af, off_ar, mm

def evaluate(name, r, offset=None):
    out = {}
    R = pd.Series(r['pre'], index=base.index); Rp = pd.Series(r['post'], index=base.index)
    if offset is not None:
        o = base.month.map(offset).astype(float).fillna(0.0).values; R = R - o; Rp = Rp - o
    inn = pd.Series(r['inn'], index=base.index); sdv = pd.Series(r['sd'], index=base.index)
    # T0 accuracy (unchanged by post-hoc anchors: a month's shift is common to the whole race)
    L = ll(inn, sdv)
    for lab, msk in [('2024', base.year == 2024), ('2025-26', base.year >= 2025)]:
        mk = msk & NAT & inn.notna() & (base.field >= 6); out[f'T0_loglik_{lab}'] = round(float(L[mk].mean()), 5); out[f'T0_n_{lab}'] = int(mk.sum())
    beta = fit_beta(R, EST & NAT & (base.year <= 2023)); out['beta_kg_per_fig_point'] = round(beta, 4)
    # T1 drift vs physical measure: yearly intercept of (rating - beta x figure), established horses, tier/distance adjusted
    df = base.loc[EST & NAT, ['year', 'tier', 'dband']].copy(); df['res'] = R[df.index] - beta * base.loc[df.index, 'fig_prev5'].astype(float)
    df['res'] = tier_adjust(df, 'res'); yr = df.groupby('year').res.mean(); yr = yr - yr.iloc[0]
    out['T1_level_vs_figure_by_year'] = {int(k): round(float(v), 2) for k, v in yr.items()}
    yrs = np.array(list(yr.index), float); out['T1_drift_kg_per_year'] = round(float(np.polyfit(yrs[1:], yr.values[1:], 1)[0]), 3) if len(yrs) > 2 else None
    dfb = df[HB[df.index].values]; yb = dfb.groupby('year').res.mean(); yb = yb - yb.iloc[0]
    out['T1_holdout_level_by_year'] = {int(k): round(float(v), 2) for k, v in yb.items()}
    out['T1_holdout_drift_kg_per_year'] = round(float(np.polyfit(np.array(list(yb.index), float)[1:], yb.values[1:], 1)[0]), 3) if len(yb) > 2 else None
    # T8 official class anchor (handicappers' benchmark ratings; independent of our ratings AND of time figures): mean pre-race
    # rating of runners in Benchmark races at the common levels, by year, relative to 2023; slope 2023-26
    b8 = base.loc[NAT & (base.field >= 6), ['year']].copy(); b8['bm'] = U.set_index('row').loc[base.loc[b8.index, 'row'], 'bm'].values
    b8['cl'] = U.set_index('row').loc[base.loc[b8.index, 'row'], 'class_label'].values; b8['R'] = R[b8.index]
    b8 = b8[b8.cl.isin(['Benchmark', 'BM']) & b8.bm.isin([58, 64, 70, 78])]
    t8 = b8.groupby(['bm', 'year']).R.mean().unstack(); t8 = t8.sub(t8.get(2023), axis=0)
    out['T8_bm_level_by_year_vs_2023'] = {int(b): {int(y): round(float(v), 2) for y, v in r_.dropna().items()} for b, r_ in t8.iterrows()}
    ys = [y for y in [2023, 2024, 2025, 2026] if y in t8.columns]
    out['T8_drift_kg_per_year'] = round(float(np.mean([np.polyfit(np.array(ys, float), t8.loc[b, ys].values.astype(float), 1)[0] for b in t8.index])), 3)
    out['mean_rating_by_year'] = {int(k): round(float(v), 2) for k, v in R[NAT & (base.field >= 6)].groupby(base.year).mean().items()}
    # T2 peaks: per horse (12+ runs, NAT), peak = best 3-run mean of post-race rating after run 5; peak figure = best 3-run mean of fig_n
    hh = base.loc[NAT & HB, ['horse', 'k', 'year', 'fig_n', 'tier']].copy(); hh['Rp'] = Rp[hh.index]     # hold-out horses only
    hh = hh[hh.groupby('horse').k.transform('max') >= 11]
    hh = hh.sort_values(['horse', 'k']); hh['rp3'] = hh.groupby('horse').Rp.transform(lambda s: s.rolling(3).mean())
    hh['f3'] = hh.groupby('horse').fig_n.transform(lambda s: s.astype(float).rolling(3, min_periods=2).mean())
    h5 = hh[(hh.k >= 5) & hh.rp3.notna()]; ip = h5.groupby('horse').rp3.idxmax().dropna(); pk = h5.loc[ip, ['horse', 'year', 'rp3']].set_index('horse')
    pk['f3'] = h5.groupby('horse').f3.max()
    pk = pk.dropna(); X = np.c_[np.ones(len(pk)), pk.f3.values]; bb = np.linalg.lstsq(X, pk.rp3.values, rcond=None)[0]; res = pk.rp3.values - X @ bb
    out['T2_peaks_n'] = len(pk); out['T2_peak_R2'] = round(float(1 - res.var() / pk.rp3.var()), 4)
    out['T2_peak_residual_by_peak_year'] = {int(k): round(float(v), 2) for k, v in pd.Series(res, index=pk.year.values).groupby(level=0).mean().items()}
    out['T2_residual_trend_kg_per_year'] = round(float(np.polyfit(pk.year.values.astype(float), res, 1)[0]), 3)
    # T3 decline: same horse, runs 300-450 days apart, 6yo+ at the later run, both with 5-run figure means
    dd = base.loc[NAT & HB & (base.k >= 8) & base.fig_prev5.notna(), ['horse', 'date', 'age', 'fig_prev5']].copy(); dd['R'] = R[dd.index]
    dd = dd.sort_values(['horse', 'date']); pairs = []
    for h, gg in dd.groupby('horse', sort=False):
        if len(gg) < 2: continue
        dts = gg.date.values; j = np.searchsorted(dts, dts + np.timedelta64(300, 'D'))
        for i0, j0 in enumerate(j):
            if j0 < len(gg) and (dts[j0] - dts[i0]) <= np.timedelta64(450, 'D'):
                pairs.append((gg.R.values[j0] - gg.R.values[i0], float(gg.fig_prev5.values[j0]) - float(gg.fig_prev5.values[i0]), gg.age.values[j0], pd.Timestamp(dts[j0]).year))
    P = pd.DataFrame(pairs, columns=['dR', 'dF', 'age', 'year'])
    for lab, pm_ in [('6yo+', P.age >= 6), ('all', P.age > 0)]:
        q_ = P[pm_]; out[f'T3_{lab}_pairs'] = len(q_); out[f'T3_{lab}_corr'] = round(float(np.corrcoef(q_.dR, q_.dF)[0, 1]), 4)
        out[f'T3_{lab}_bias_kg'] = round(float((q_.dR - beta * q_.dF).mean()), 3)
        out[f'T3_{lab}_decliners_flagged'] = round(float(((q_.dR < -2) & (q_.dF < 0)).sum() / max(1, (q_.dR < -2).sum())), 4)   # share of rating declines >2 kg confirmed by slower figures
    # T4 development by age: mean dR and beta x dF per run-to-run step, by age
    ag = base.loc[NAT].sort_values(['horse', 'date']); ag['F'] = ag.fig_n.astype(float); ag['dF'] = ag.groupby('horse').F.diff(); ag['dRr'] = R[ag.index].groupby(ag.horse).diff()
    tab = ag[ag.age.between(2, 9) & ag.dF.notna() & ag.dRr.notna()].groupby('age').agg(n=('dF', 'size'), dR=('dRr', 'mean'), dF=('dF', 'mean'))
    tab['beta_dF'] = beta * tab.dF; out['T4_by_age'] = {int(a): {'n': int(x.n), 'rating_change_per_run': round(float(x.dR), 3), 'figure_change_kg': round(float(x.beta_dF), 3)} for a, x in tab.iterrows()}
    out['T4_mean_abs_gap'] = round(float((tab.dR - tab.beta_dF).abs().mean()), 3)
    # T5 long-break returners: surprise at the first run back after 120+ days, by year
    rt = base[NAT & (base.gap >= 120) & (base.k >= 3) & inn.notna()].copy(); rt['inn'] = inn[rt.index]
    out['T5_returners_by_year'] = {int(k): round(float(v), 3) for k, v in rt.groupby('year').inn.mean().items()}
    rt['rel'] = R[rt.index] - R.groupby(base.race_key).transform('mean')[rt.index]
    out['T5_returner_mean_surprise'] = round(float(rt.inn.mean()), 3); out['T5_returner_n'] = len(rt)
    # T6 interstate: state level by year (established metro/provincial horses, rating - beta x figure)
    s6 = base.loc[EST & NAT & HB & base.tier.isin(['metro', 'provincial']), ['state', 'year', 'tier', 'dband']].copy()
    s6['res'] = R[s6.index] - beta * base.loc[s6.index, 'fig_prev5'].astype(float); s6['res'] = tier_adjust(s6, 'res')
    sy = s6.groupby(['state', 'year']).res.mean().unstack(); sy = sy.sub(sy.mean(axis=0), axis=1)      # relative to the national level that year
    out['T6_state_level_by_year'] = {s: {int(y): round(float(v), 2) for y, v in r_.dropna().items()} for s, r_ in sy.iterrows()}
    out['T6_mean_sd_across_years'] = round(float(sy.std(axis=1).mean()), 3)
    # T7 venue strength: venue x year mean pre-race rating of runners vs mean time figure
    v7 = base.loc[NAT & (base.field >= 6), ['venue', 'year', 'fig_n']].copy(); v7['R'] = R[v7.index]
    vy = v7.groupby(['venue', 'year']).agg(R=('R', 'mean'), F=('fig_n', 'mean'), n=('R', 'size')); vy = vy[vy.n >= 100].reset_index()
    vy['F'] = vy.F.astype(float); vy = vy.sort_values(['venue', 'year']); vy['dR'] = vy.groupby('venue').R.diff(); vy['dF'] = vy.groupby('venue').F.diff()
    q7 = vy.dropna(subset=['dR', 'dF']); out['T7_venue_year_changes'] = len(q7); out['T7_corr_rating_vs_figure_change'] = round(float(np.corrcoef(q7.dR, q7.dF)[0, 1]), 4)
    out['T7_mean_bias_kg'] = round(float((q7.dR - beta * q7.dF).mean()), 3)
    out['T7_cross_section_corr'] = round(float(vy.groupby('year').apply(lambda x: np.corrcoef(x.R, x.F)[0, 1]).mean()), 4)
    return out

def decompose(name, r):
    """Where the scale's movement comes from, by year (national states)."""
    df = base[['year', 'k', 'gap', 'field', 'race_key', 'horse', 'last_run', 'date']].copy()
    for c in ['pre', 'post', 'inn', 'K', 'cre', 'gx', 'first']: df[c] = r[c]
    df = df[NAT]
    df['cls'] = np.select([df['first'], df.k.between(1, 2), df.gap >= 90], ['first_held_run', 'runs_2_3', 'return_90d+'], 'established')
    used = df.inn.notna()
    out = {}
    for y, gy in df.groupby('year'):
        gu = gy[used.loc[gy.index]]; nr = len(gu)
        rr = {'runs': int(nr), 'net_created_per_run_kg': round(float(gu.cre.sum() / nr), 4)}
        # split the net created rating: K-asymmetry (K differs) vs good-run multiplier
        Kbar = gu.groupby('race_key').K.transform('mean')
        rr['from_K_differences'] = round(float(((gu.K - Kbar) * gu.inn).sum() / nr), 4)
        rr['from_good_run_multiplier'] = round(float((gu.K * (gu.gx - 1) * gu.inn).sum() / nr), 4)
        for c, gc in gu.groupby('cls'): rr[f'created_by_{c}'] = round(float(gc.cre.sum() / nr), 4)
        fr = gy[gy['first']]; rr['entrants'] = int(len(fr))
        kn = gy[~gy['first']].groupby('race_key').pre.mean()
        rr['entrant_start_vs_field_known_kg'] = round(float((fr.pre - fr.race_key.map(kn)).mean()), 3)
        rr['first_run_surprise_kg'] = round(float(fr.inn.mean()), 3)
        ex = gy[gy.last_run & (gy.date < pd.Timestamp('2026-05-01'))]
        rr['exits'] = int(len(ex)); rr['exit_level_vs_field_kg'] = round(float((ex.post - gy.groupby('race_key').pre.transform('mean')[ex.index]).mean()), 3)
        rr['turnover_share_runs_by_this_years_entrants'] = round(float(gy.horse.isin(fr.horse).mean()), 4)
        out[int(y)] = rr
    # selective retirement: rating at exit relative to the horse's own peak, and figure decline before exit
    hx = df.sort_values(['horse', 'date']); hx['peak'] = hx.groupby('horse').post.cummax()
    lx = hx[hx.last_run & (hx.date < pd.Timestamp('2026-05-01')) & (hx.k >= 5)]
    out['exit_below_own_peak_kg'] = round(float((lx.post - lx.peak).mean()), 3); out['exit_n'] = int(len(lx))
    return out

R_ALL = {}; res = {}
for name, kw in [('P0', dict(rule='P0')), ('P0+K', dict(rule='P0', conserve=True)), ('P0+K+D', dict(rule='P0', conserve=True, adaptive=True)),
                 ('P0+D', dict(rule='P0', adaptive=True)), ('C0', dict(rule='C0')), ('C0+K', dict(rule='C0', conserve=True)),
                 ('C0+K+D', dict(rule='C0', conserve=True, adaptive=True))][:(2 if os.environ.get('SMOKE') else 99)]:
    r = rate(d, **kw); log('rated', name); R_ALL[name] = r
    res[name] = {'decomposition': decompose(name, r), 'tests': evaluate(name, r)}
    res[name]['d0_final'] = round(float(np.nanmean(r['d0'][-5000:])), 3)
    log(name, json.dumps({k: res[name]['tests'][k] for k in ['T0_loglik_2024', 'T0_loglik_2025-26', 'T1_drift_kg_per_year', 'T2_peak_R2', 'T2_residual_trend_kg_per_year', 'T3_6yo+_bias_kg', 'T6_mean_sd_across_years', 'T7_mean_bias_kg', 'T1_holdout_drift_kg_per_year', 'T8_drift_kg_per_year']}))
    json.dump(res, open(os.environ.get('OUT','batch25/out_b25_scale.json'), 'w'), indent=1, default=str)
for name in ['P0', 'C0']:
    r = R_ALL[name]; R = pd.Series(r['pre'], index=base.index)
    beta = fit_beta(R, EST & NAT & (base.year <= 2023)); af, ar, mm = anchors(R, beta)
    for lab, off in [('AF', af), ('AR', ar)]:
        res[f'{name}+{lab}'] = {'tests': evaluate(f'{name}+{lab}', r, offset=off), 'offset_by_month': {str(k): round(float(v), 3) for k, v in off.items()}}
        log(f'{name}+{lab}', json.dumps({k: res[f'{name}+{lab}']['tests'][k] for k in ['T1_drift_kg_per_year', 'T2_peak_R2', 'T2_residual_trend_kg_per_year', 'T3_6yo+_bias_kg', 'T6_mean_sd_across_years', 'T7_mean_bias_kg', 'T1_holdout_drift_kg_per_year', 'T8_drift_kg_per_year']}))
    json.dump(res, open(os.environ.get('OUT','batch25/out_b25_scale.json'), 'w'), indent=1, default=str)
log('done')
