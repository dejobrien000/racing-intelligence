"""Batch 10 candidate features. Every feature uses only the horse's (or jockey's / trainer's) EARLIER runs.
perf = the run's measured level on the rating scale (pre-race rating + race-relative surprise), kg units.
Output b10/out/feat.parquet keyed by race_id + horse (and q_race_id / q_horse_id for Qld)."""
import numpy as np, pandas as pd
U = pd.read_parquet('engine/frames/national.parquet')
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
inn = U.dyn_nat_inn; U['perf'] = U.dyn_nat + inn
F = U[['race_id', 'horse', 'q_race_id', 'q_horse_id', 'date', 'state']].copy()
dev = U.date < '2025-01-01'; pop_var = float(inn[dev].var()); print('population surprise sd (kg):', round(pop_var ** .5, 2))
# ---------- 5. career trajectory and individual variability ----------
pc = inn.notna().astype(float); pv = inn.fillna(0.0)
n = g[['dyn_nat_inn']].transform(lambda s: s.notna().cumsum().shift(fill_value=0)).iloc[:, 0]
s1 = pv.groupby(U.horse).cumsum() - pv; s2 = (pv ** 2).groupby(U.horse).cumsum() - pv ** 2
k = 5.0; F['n_prior'] = n
F['h_sd'] = np.sqrt((s2 - s1 ** 2 / n.replace(0, np.nan) + k * pop_var) / (n - 1).clip(lower=0).add(k)).where(n >= 1)   # shrunk own variability
last = lambda col, w: g[col].transform(lambda s: s.shift().rolling(w, min_periods=max(2, w // 2)))
r5sd = g['dyn_nat_inn'].transform(lambda s: s.shift().rolling(5, min_periods=3).std())
F['recent_var_ratio'] = (r5sd / F.h_sd).where(n >= 8)                                            # unusual recent variability
strong = (inn > 3).astype(float).where(inn.notna()).fillna(0); weak = (inn < -3).astype(float).where(inn.notna()).fillna(0)
p_s, p_w = float((inn[dev] > 3).mean()), float((inn[dev] < -3).mean())
F['strong_rate'] = ((strong.groupby(U.horse).cumsum() - strong) + 5 * p_s) / (n + 5) - p_s
F['weak_rate'] = ((weak.groupby(U.horse).cumsum() - weak) + 5 * p_w) / (n + 5) - p_w
pf = U.perf
F['short_mean'] = g['perf'].transform(lambda s: s.shift().rolling(5, min_periods=3).mean())
F['long_mean'] = g['perf'].transform(lambda s: s.shift(6).rolling(15, min_periods=5).mean())   # runs 6-20 back
F['gap_long'] = F.long_mean - U.dyn_nat                         # + = rated below its longer-run level (Horse A); ~0 for Horse B
F['gap_long_z'] = F.gap_long / F.h_sd                            # same, in units of the horse's own normal swings
F['short_vs_long'] = F.short_mean - F.long_mean
cm = g['perf'].transform(lambda s: s.shift().cummax()); F['below_best'] = cm - U.dyn_nat
top3 = g['perf'].transform(lambda s: s.shift().expanding(3).apply(lambda a: np.sort(a[~np.isnan(a)])[-3:].mean() if (~np.isnan(a)).sum() >= 3 else np.nan, raw=True))
sec = g['perf'].transform(lambda s: s.shift().expanding(2).apply(lambda a: np.sort(a[~np.isnan(a)])[-2] if (~np.isnan(a)).sum() >= 2 else np.nan, raw=True))
F['isolated_peak'] = (cm - sec).where(n >= 6)                    # one-off peak: best minus second best
F['below_top3'] = top3 - U.dyn_nat                               # below its sustained best level
def slope(a):
    m = ~np.isnan(a)
    if m.sum() < 4: return np.nan
    t = np.arange(len(a))[m]; y = a[m]; t = t - t.mean(); return float((t * (y - y.mean())).sum() / (t ** 2).sum())
F['slope15'] = g['perf'].transform(lambda s: s.shift().rolling(15, min_periods=8).apply(slope, raw=True))
F['slope5'] = g['perf'].transform(lambda s: s.shift().rolling(5, min_periods=4).apply(slope, raw=True))
F['neg_run'] = g['dyn_nat_inn'].transform(lambda s: (s.shift() < 0).astype(float).rolling(5, min_periods=3).sum())
F['steady_decline'] = (F.slope15 * (F.gap_long > 0)).where(F.slope15.notna())   # long slide (A) vs not
# ---------- 6. preparations ----------
gapd = (U.date - g.date.shift()).dt.days; newprep = gapd.isna() | (gapd > 60)
U['prep_id'] = newprep.groupby(U.horse).cumsum(); gp = U.groupby(['horse', 'prep_id'])
U['prep_run'] = gp.cumcount() + 1; F['prep_run'] = U.prep_run
U['prep_mean'] = gp['perf'].transform('mean')                    # (whole-prep mean: used only for COMPLETED earlier preps below)
U['rel_in_prep'] = U.perf - U.prep_mean
# horse's typical shape at this prep run number, from EARLIER preps only (k=2 shrink to 0)
hp = U[['horse', 'prep_id', 'prep_run', 'rel_in_prep']].copy()
agg = hp.groupby(['horse', 'prep_run', 'prep_id']).rel_in_prep.mean().reset_index().sort_values(['horse', 'prep_run', 'prep_id'])
agg['cs'] = agg.groupby(['horse', 'prep_run']).rel_in_prep.cumsum() - agg.rel_in_prep; agg['cn'] = agg.groupby(['horse', 'prep_run']).cumcount()
look = U[['horse', 'prep_run', 'prep_id']].merge(agg[['horse', 'prep_run', 'prep_id', 'cs', 'cn']], on=['horse', 'prep_run', 'prep_id'], how='left')
F['prep_shape'] = (look.cs / (look.cn + 2)).where(look.cn > 0).values
pk = U.loc[U.dropna(subset=['perf']).groupby(['horse', 'prep_id']).perf.idxmax()][['horse', 'prep_id', 'prep_run']].rename(columns={'prep_run': 'peak_run'})
pk = pk.sort_values(['horse', 'prep_id']); pk['prev_peak_run'] = pk.groupby('horse').peak_run.transform(lambda s: s.shift().expanding().mean())
F['runs_to_usual_peak'] = (U[['horse', 'prep_id']].merge(pk[['horse', 'prep_id', 'prev_peak_run']], on=['horse', 'prep_id'], how='left').prev_peak_run.values - U.prep_run.values)
e3 = U.perf.where(U.prep_run <= 3); U['e3'] = e3
cur_e3 = U.groupby(['horse', 'prep_id']).e3.transform(lambda s: s.shift().expanding().mean())
pe = U.groupby(['horse', 'prep_id']).e3.mean().reset_index().sort_values(['horse', 'prep_id']); pe['prev_e3'] = pe.groupby('horse').e3.transform(lambda s: s.shift().expanding().mean())
prev_e3 = U[['horse', 'prep_id']].merge(pe[['horse', 'prep_id', 'prev_e3']], on=['horse', 'prep_id'], how='left').prev_e3.values
F['early_prep_vs_usual'] = (cur_e3 - prev_e3).where(U.prep_run >= 4)        # this prep's first 3 runs vs earlier preps' first 3
bestp = U.groupby(['horse', 'prep_id']).perf.transform(lambda s: s.shift().cummax()); lastp = U.groupby(['horse', 'prep_id']).perf.shift()
F['dip_from_prep_best'] = (bestp - lastp).where(U.prep_run >= 3)              # e.g. 86 -> 83: last run below this prep's best
# ---------- 7. workload ----------
gs = [gapd.groupby(U.horse).shift(i) for i in range(4)]                  # gs[0] = days since last run (today), gs[1] = gap before that ...
q = [(x <= 10).astype(float).where(x.notna()) for x in gs]
F['quick_today'] = q[0]; F['isolated_quick'] = (q[0] * (1 - q[1].fillna(0))).where(q[0].notna())
F['consec_quick'] = (q[0].fillna(0) * (1 + q[1].fillna(0) * (1 + q[2].fillna(0) * (1 + q[3].fillna(0))))).where(gs[0].notna())
nq = lambda x: x.between(11, 35).astype(float)
F['sched_A'] = (nq(gs[3]) * nq(gs[2]) * nq(gs[1]) * q[0].fillna(0)).where(gs[3].notna())         # 21,21,21,7
F['sched_B'] = (nq(gs[3]) * gs[2].between(11, 17) * q[1].fillna(0) * q[0].fillna(0)).where(gs[3].notna())   # 21,14,7,7
F['sched_C'] = (q[3].fillna(0) * q[2].fillna(0) * q[1].fillna(0) * q[0].fillna(0)).where(gs[3].notna())     # 7,7,7,7
# rolling counts by date (closed left = earlier runs only)
def roll_count(days):
    out = np.zeros(len(U)); d = U.date.values.astype('datetime64[D]').astype(np.int64); h = U.horse.values
    start = 0
    for i in range(len(U)):
        if i == 0 or h[i] != h[i - 1]: start = i
        j = start
        # earlier runs of this horse within window
        cnt = 0
        for jj in range(i - 1, start - 1, -1):
            if d[i] - d[jj] <= days: cnt += 1
            else: break
        out[i] = cnt
    return out
for w in [28, 60]:
    F[f'starts_{w}d'] = roll_count(w)
def roll_dist(days):
    out = np.zeros(len(U)); d = U.date.values.astype('datetime64[D]').astype(np.int64); h = U.horse.values; m = U.distance_m.fillna(0).values; start = 0
    for i in range(len(U)):
        if i == 0 or h[i] != h[i - 1]: start = i
        s = 0.0
        for jj in range(i - 1, start - 1, -1):
            if d[i] - d[jj] <= days: s += m[jj]
            else: break
        out[i] = s
    return out
F['metres_42d'] = roll_dist(42)
F['prep_days'] = (U.date - U.groupby(['horse', 'prep_id']).date.transform('min')).dt.days
U['fq'] = U.groupby('race_id').dyn_nat.transform('mean'); F['last_race_strength'] = g.fq.shift() - U.fq     # + = last race was stronger than today's
F['opp_step'] = U.fq - g.fq.shift()
# ---------- 9. jockeys and trainers as dynamic participants (surprises = performance beyond the horse's own rating) ----------
def person_hist(key, half_life=120, k=30):
    """exponentially weighted (by days) shrunk mean of a person's EARLIER-dated ride surprises; plus tail rates."""
    d = U[[key, 'date']].copy(); d['v'] = inn; d = d[d[key].notna()]
    day = d.groupby([key, 'date']).v.agg(['sum', 'count', lambda s: (s < -4).sum(), lambda s: (s > 4).sum()]).reset_index()
    day.columns = [key, 'date', 'sv', 'cv', 'bad', 'good']; day = day[day.cv > 0].sort_values([key, 'date'])
    lam = np.log(2) / half_life; res = []
    for _, grp in day.groupby(key, sort=False):
        t = grp.date.values.astype('datetime64[D]').astype(np.int64); sv, cv, b, gd = grp.sv.values, grp.cv.values, grp.bad.values, grp.good.values
        S = C = B = G = 0.0; last = None; rec = np.empty((len(grp), 4))
        for i in range(len(grp)):
            if last is not None:
                f = np.exp(-lam * (t[i] - last)); S *= f; C *= f
            rec[i] = (S, C, B, G); S += sv[i]; C += cv[i]; B += b[i]; G += gd[i]; last = t[i]
        res.append(pd.DataFrame(rec, columns=['S', 'C', 'B', 'G'], index=grp.index))
    R = pd.concat(res); day = day.join(R); ntot = day.groupby(key).cv.cumsum() - day.cv
    day[key + '_recent'] = day.S / (day.C + k); day[key + '_n_all'] = ntot
    pb, pg = float((inn[dev] < -4).mean()), float((inn[dev] > 4).mean())
    day[key + '_bad'] = (day.B + 20 * pb) / (ntot + 20) - pb; day[key + '_good'] = (day.G + 20 * pg) / (ntot + 20) - pg
    return U[[key, 'date']].merge(day[[key, 'date', key + '_recent', key + '_bad', key + '_good']], on=[key, 'date'], how='left')
for key in ['jkey', 'tkey']:
    h = person_hist(key); F[key + '_recent'] = h[key + '_recent'].values; F[key + '_bad'] = h[key + '_bad'].values; F[key + '_good'] = h[key + '_good'].values
F['j_recent_vs_career'] = F.jkey_recent - U.j_surp; F['t_recent_vs_career'] = F.tkey_recent - U.t_surp
# ---------- 8. trainer decisions: trainer's earlier surprise on the SAME kind of decision, beyond the trainer's general form ----------
dch = np.log(U.distance_m / g.distance_m.shift())
dec = {'dist_up': dch >= np.log(1.18), 'dist_down': dch <= -np.log(1.18), 'quick': gapd <= 10, 'long_break': gapd > 90,
       'class_up': F.opp_step > 2, 'class_down': F.opp_step < -2, 'jockey_change': U.jkey != g.jkey.shift()}
for nm, m in dec.items():
    m = m.fillna(False) & U.tkey.notna(); d = pd.DataFrame({'t': U.tkey, 'date': U.date, 'v': inn.where(m)})
    day = d[m].groupby(['t', 'date']).v.agg(['sum', 'count']).reset_index().sort_values(['t', 'date'])
    day['cs'] = day.groupby('t')['sum'].cumsum() - day['sum']; day['cn'] = day.groupby('t')['count'].cumsum() - day['count']
    lk = d[['t', 'date']].merge(day[['t', 'date', 'cs', 'cn']], on=['t', 'date'], how='left')
    # for dates where this trainer made no such decision, carry forward the latest totals
    allday = d[['t', 'date']].drop_duplicates().merge(day[['t', 'date', 'cs', 'cn', 'sum', 'count']], on=['t', 'date'], how='left').sort_values(['t', 'date'])
    allday['cs2'] = (allday['sum'].fillna(0).groupby(allday.t).cumsum() - allday['sum'].fillna(0)); allday['cn2'] = (allday['count'].fillna(0).groupby(allday.t).cumsum() - allday['count'].fillna(0))
    lk = d[['t', 'date']].merge(allday[['t', 'date', 'cs2', 'cn2']], on=['t', 'date'], how='left')
    skill = (lk.cs2 + 15 * U.t_surp.fillna(0).values) / (lk.cn2 + 15) - U.t_surp.fillna(0).values
    F['tdec_' + nm] = np.where(m.values, skill.values, np.nan)          # only on runs where today's run IS that decision
F['improving'] = (U.dyn_traj > 0).astype(float).where(U.dyn_traj.notna())
F['dist_up_improving'] = (dec['dist_up'].astype(float) * F.improving).where(F.improving.notna() & dch.notna())
F['dist_up_declining'] = (dec['dist_up'].astype(float) * (1 - F.improving)).where(F.improving.notna() & dch.notna())
F.to_parquet('b10/out/feat.parquet'); print(F.shape); print(F.drop(columns=['race_id', 'horse', 'q_race_id', 'q_horse_id', 'date', 'state']).notna().mean().round(2).to_string())
