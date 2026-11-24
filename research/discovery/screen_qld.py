"""Discovery engine, first screen (Queensland tracked races, richest data).
Every candidate is one term added to the frozen baseline (combined_v1 + national dynamic rating, as an offset) in a
within-race conditional logit. Racing logic decides what is built; the data decides the weights.
  DISCOVERY  = races before 1 Jan 2025 (estimate, standard error, two-halves stability, BH screening).
  CONFIRMATION = 1 Jan 2025 - 23 Nov 2026 (coefficient frozen from discovery; out-of-sample fit gain, meeting bootstrap).
  Untouched future = pre-race predictions from 25 Nov 2026 (anything promoted is frozen and tested there).
Families: (A) the 15 directed investigations from the brief; (B) a systematic pairwise screen of base features;
(C) feature x context (tier, going band, distance band, field size). Minimum effective sample: the term must vary
within at least 300 discovery races. Outputs discovery/out/*.csv"""
import os, json, numpy as np, pandas as pd, itertools
import hier_tools as H, dyn_rating as DR, dyn_rating_innov as DI
from clogit_tools import eligible, prep
from statsmodels.stats.multitest import multipletests
os.makedirs('discovery/out', exist_ok=True); rng = np.random.default_rng(20261125)
mn = json.load(open('benchmarks/candidates_b4_national/manifest.json')); COEF = mn['coefficients_per_dev_sd']; pn = mn['dynamic_rating_params']
# ---------------- national history: rating, surprises, records, head-to-head ----------------
U = pd.read_parquet('national_runs.parquet')
qt = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'track']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'})
U = U.merge(qt, on=['q_race_id', 'q_horse_id'], how='left'); U['config'] = np.where(U.state == 'QLD', U.track, U.venue)
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0), 'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, sd_, inn = DI.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
ix = PN.idx.values; U['dyn_nat'] = pd.Series(mu, index=ix).reindex(np.arange(len(U))).values; U['innov'] = pd.Series(inn, index=ix).reindex(np.arange(len(U))).values
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
gw = U.going.astype(str).str.lower(); U['wet'] = gw.str.contains('soft|heavy').astype(float)
v = U.innov.fillna(0.0); c = U.innov.notna().astype(int)
for key, nm in [('config', 'c_rec')]:
    grp = [U.horse, U[key]]; U[nm] = (v.groupby(grp).cumsum() - v) / ((c.groupby(grp).cumsum() - c) + 1)
U['dyn_traj'] = U.dyn_nat - g.dyn_nat.shift(2)                                                # rating change over the last two runs (pre-race to pre-race)
U['surprise_last'] = g.innov.shift(); U['surprise_avg3'] = g.innov.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
# head-to-head: earlier meetings with today's rivals (all states held)
P = U[U.finish_pos.notna() & (U.finish_pos <= U.field)][['race', 'date', 'horse', 'finish_pos']]
pp = P.merge(P, on=['race', 'date'], suffixes=('', '_o')); pp = pp[pp.horse != pp.horse_o]
pp['beat'] = np.sign(pp.finish_pos_o - pp.finish_pos)
pp = pp.sort_values(['horse', 'horse_o', 'date']); gg = pp.groupby(['horse', 'horse_o'])
pp['n_prev'] = gg.cumcount(); pp['b_prev'] = gg.beat.cumsum() - pp.beat
pp['h2h'] = pp.b_prev / (pp.n_prev + 1); pp['has_prev'] = (pp.n_prev > 0).astype(int)
hh = pp.groupby(['race', 'horse']).agg(h2h=('h2h', 'mean'), h2h_pairs=('has_prev', 'sum')).reset_index()
U = U.merge(hh, on=['race', 'horse'], how='left')
U.loc[U.h2h_pairs.fillna(0) == 0, 'h2h'] = np.nan
q = U[U.state == 'QLD'][['q_race_id', 'q_horse_id', 'dyn_nat', 'c_rec', 'dyn_traj', 'surprise_last', 'surprise_avg3', 'h2h', 'h2h_pairs', 'wet']].rename(columns={'q_race_id': 'race_id', 'q_horse_id': 'horse_id'}).dropna(subset=['race_id'])
# ---------------- Qld frame ----------------
X = pd.read_parquet('features.parquet').merge(q, on=['race_id', 'horse_id'], how='left')
X = X.merge(pd.read_parquet('pace_figures.parquet')[['race_id', 'horse_id', 'rec_rating_pa1', 'rec_late_fig']], on=['race_id', 'horse_id'], how='left')
rr = pd.read_parquet('runs_rated_dev.parquet')[['race_id', 'horse_id', 'meeting_date', 'race_no', 'weight_kg', 'class_bucket', 'rating', 'tempo', 'ground_extra', 'fsp', 'distance_m', 'cond_group']]
rr['meeting_date'] = pd.to_datetime(rr.meeting_date); rr = rr.sort_values(['horse_id', 'meeting_date', 'race_no']); gr = rr.groupby('horse_id')
lvl = rr[rr.meeting_date < '2025-01-01'].groupby('class_bucket').rating.median(); rr['cls_lvl'] = rr.class_bucket.map(lvl)
rr['cls_change'] = rr.cls_lvl - gr.cls_lvl.shift()                                           # + = stepping up in class
rr['wt_change'] = rr.weight_kg - gr.weight_kg.shift()                                         # + = carrying more than last start
rr['fig_traj'] = gr.rating.shift() - gr.rating.transform(lambda s: s.shift(2).rolling(3, min_periods=1).mean())   # last figure vs the three before it
rr['tempo_last'] = gr.tempo.shift(); rr['ground_last'] = gr.ground_extra.shift(); rr['fsp_last'] = gr.fsp.shift()
X = X.merge(rr[['race_id', 'horse_id', 'cls_change', 'wt_change', 'fig_traj', 'tempo_last', 'ground_last', 'fsp_last', 'cond_group']], on=['race_id', 'horse_id'], how='left')
X['route'] = (X.distance_m >= 1400).astype(float); X['metro'] = (X.venue_tier == 'metro').astype(float)
X['gb_wet'] = X.cond_group.isin(['Soft', 'Heavy']).astype(float); X['big_field'] = (X.field >= 12).astype(float)
X['field_dyn'] = X.groupby('race_id').dyn_nat.transform('mean')
has = X.f_avgfp3.notna()
for k, v_ in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v_.astype(float)
BASE = ['dyn_nat', 'a_avg3', 'a_best3', 'a_fs3', 'a_cls_gap', 'a_wt_rel', 'f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 's_gap600_last', 's_gap600_avg3', 's_fsp_last', 'p_style', 'p_relbar',
        't_going', 't_dchange', 'r_prep', 'r_ldays', 'c_rec', 'rec_rating_pa1', 'cls_change', 'wt_change', 'fig_traj', 'dyn_traj', 'surprise_last', 'h2h', 'ground_last', 'tempo_last']
x = prep(eligible(X), sorted(set(COEF) | set(BASE) | {'surprise_avg3'}))
x['offset'] = x[[c_ + '_z' for c_ in COEF]].values @ np.array(list(COEF.values()))
for k_ in ['route', 'metro', 'gb_wet', 'big_field', 'wet']: x[k_] = x[k_].fillna(0)
x['fd_z'] = (x.field_dyn - x.field_dyn.mean()) / x.field_dyn.std()
dev, ev = x[x.period == 'development'], x[x.period == 'evaluation']; d1, d2 = dev[dev.meeting_date < '2024-01-01'], dev[dev.meeting_date >= '2024-01-01']
mid = ev.drop_duplicates('race_id').set_index('race_id').meeting_id
def term(df, expr):
    t = expr(df).astype(float).values; t = t - pd.Series(t, index=df.index).groupby(df.race_id).transform('mean').values      # race-centred: only within-race differences count
    return t
def run(name, family, expr, rationale, data='Qld tracked'):
    t_dev, t_ev = term(dev, expr), term(ev, expr); s = np.nanstd(t_dev) or 1.0
    t_dev, t_ev = np.nan_to_num(t_dev / s), np.nan_to_num(t_ev / s)
    nvar = int(pd.Series(np.abs(t_dev) > 1e-9).groupby(dev.race_id.values).any().sum())
    if nvar < 300: return {'name': name, 'family': family, 'note': f'too little variation ({nvar} races)'}
    Rd = H.Races(dev.race_id.values, dev.win.values, dev.offset.values, t_dev[:, None]); b = H.fit(Rd, np.array([1e-6])); se = H.posterior_sd(Rd, b, np.array([1e-6]))[0]
    ll0 = Rd.loglik_per_race(np.zeros(1)).sum(); ll1 = Rd.loglik_per_race(b).sum()
    def half(dd, tt): return H.fit(H.Races(dd.race_id.values, dd.win.values, dd.offset.values, tt[:, None]), np.array([1e-6]))[0]
    m1 = (dev.meeting_date < '2024-01-01').values; b1, b2 = half(d1, t_dev[m1]), half(d2, t_dev[~m1])
    Re = H.Races(ev.race_id.values, ev.win.values, ev.offset.values, t_ev[:, None]); rid = ev.race_id.values[Re.o][Re.starts]
    gain = pd.Series(Re.loglik_per_race(b) - Re.loglik_per_race(np.zeros(1)), index=rid)
    hit = pd.Series(Re.top_hit(b) - Re.top_hit(np.zeros(1)), index=rid)
    m = gain.groupby(mid.reindex(gain.index).values).agg(['sum', 'count']); su, n = m['sum'].values, m['count'].values
    bs = [su[i].sum() / n[i].sum() for i in (rng.integers(0, len(su), len(su)) for _ in range(500))]
    from scipy.stats import norm
    return {'name': name, 'family': family, 'rationale': rationale, 'data': data, 'races_with_variation_dev': nvar, 'coef_per_sd': round(float(b[0]), 4), 'se': round(float(se), 4),
            'z': round(float(b[0] / se), 2), 'p_discovery': float(2 * norm.sf(abs(b[0] / se))), 'dev_loglik_gain': round(ll1 - ll0, 2),
            'coef_2022_23': round(float(b1), 4), 'coef_2024': round(float(b2), 4), 'same_sign_halves': bool(np.sign(b1) == np.sign(b2)),
            'confirm_gain_per_race': round(float(gain.mean()), 5), 'confirm_lo95': round(float(np.percentile(bs, 2.5)), 5), 'confirm_hi95': round(float(np.percentile(bs, 97.5)), 5),
            'confirm_top_pick_change_pts': round(100 * float(hit.mean()), 2), 'confirm_races': len(gain),
            'corr_with_baseline': round(float(np.corrcoef(t_dev, dev.offset.values - dev.groupby('race_id').offset.transform('mean').values)[0, 1]), 3)}
Z = lambda c_: (lambda d: d[c_ + '_z'])
D = []
# (A) directed investigations from the brief (numbered as in the brief)
A = [('1 opposition strength x class change', lambda d: d.a_fs3_z * d.cls_change_z, 'a horse that has met strong fields may handle a rise in class better'),
     ('2 horse course record x running style', lambda d: d.c_rec_z * d.p_style_z, 'course specialists may be specialists only when they can race on the speed (or back)'),
     ('3 pace-corrected figure x distance change', lambda d: d.rec_rating_pa1_z * d.t_dchange_z, 'figures may transfer less well when distance changes'),
     ('4 barrier x usual settling position (pooled; course version = Study 10)', lambda d: d.p_relbar_z * d.p_style_z, 'inside gate should matter more for horses that settle back'),
     ('5 weight change x opposition strength', lambda d: d.wt_change_z * d.a_fs3_z, 'a weight rise may bite harder on horses facing tougher company'),
     ('6 preparation stage x recent improvement', lambda d: d.r_prep_z * d.fig_traj_z, 'improvement early in a prep may continue; late in a prep may not'),
     ('7 horse course record x wet going today', lambda d: d.c_rec_z * d.gb_wet, 'a course record may not transfer to a wet track'),
     ('8 last closing sectional x last-start tempo x route distance', lambda d: d.s_gap600_last_z * d.tempo_last_z * d.route, 'a fast finish off a slow early pace may flatter, especially over ground'),
     ('9 ground covered last start x finishing speed last start', lambda d: d.ground_last_z * d.s_fsp_last_z, 'a horse that ran wide and still finished well may be better than its figure'),
     ('10 head-to-head record x changed distance', lambda d: d.h2h_z * d.t_dchange_abs.fillna(0) / 400, 'earlier wins over today\'s rivals may count less when the distance has changed'),
     ('10b head-to-head record (main effect)', lambda d: d.h2h_z, 'has this horse beaten today\'s rivals before, beyond what ratings say?'),
     ('11 rating trajectory x days between runs', lambda d: d.dyn_traj_z * d.r_ldays_z, 'a rising rating may continue only if the horse backs up quickly'),
     ('12 ability x field strength (within-race slope)', lambda d: d.dyn_nat_z * d.fd_z, 'ability may separate horses more in strong fields'),
     ('12b ability x metro venue', lambda d: d.dyn_nat_z * d.metro, 'ability may separate horses more at metro meetings'),
     ('13 leader x pace pressure x metro (course version = Study 14b)', lambda d: d.p_lead_x_press_z * d.metro, 'pace pressure may hurt leaders more at metro tracks'),
     ('14 class advantage x weight carried', lambda d: d.a_cls_gap_z * d.a_wt_rel_z, 'a class edge may survive top weight'),
     ('15 late speed x course (pooled proxy: x route)', lambda d: d.s_gap600_avg3_z * d.route, 'late speed may matter more over longer trips (geometry table pending)')]
for nm, ex, why in A: D.append(run(nm, 'A directed', ex, why))
# (M) new single features not in the baseline (main effects)
for f_, why in [('surprise_last', 'how far the horse beat (or missed) its own rating last start'), ('surprise_avg3', 'average of the last three surprises'), ('dyn_traj', 'rating change over the last two runs'),
                ('fig_traj', 'last figure vs the three before it'), ('cls_change', 'class step today vs last start'), ('wt_change', 'weight change since last start'),
                ('tempo_last', 'early tempo of the last race'), ('ground_last', 'extra ground covered last start'), ('rec_rating_pa1', 'pace-corrected figure (PA1)')]:
    D.append(run(f'{f_} (main effect)', 'M new feature', (lambda f_: (lambda d: d[f_ + '_z']))(f_), why))
# (B) systematic pairwise screen of base features
for a, b_ in itertools.combinations(BASE, 2):
    D.append(run(f'{a} x {b_}', 'B pairwise', (lambda a, b_: (lambda d: d[a + '_z'] * d[b_ + '_z']))(a, b_), 'systematic screen'))
# (C) feature x context
for f_ in BASE:
    for ctx in ['route', 'metro', 'gb_wet', 'big_field']:
        D.append(run(f'{f_} x {ctx}', 'C context', (lambda f_, ctx: (lambda d: d[f_ + '_z'] * d[ctx]))(f_, ctx), 'does this factor matter more in this context?'))
R0 = pd.DataFrame([r for r in D if r and 'p_discovery' in r])
# (D) three-factor follow-ups chosen on DISCOVERY evidence only: the 15 strongest discovery pairs x each context
top = R0[(R0.family == 'B pairwise') & R0.same_sign_halves].nsmallest(15, 'p_discovery').name.tolist()
for nm in top:
    a, b_ = nm.split(' x ')
    for ctx in ['route', 'metro', 'gb_wet']:
        D.append(run(f'{a} x {b_} x {ctx}', 'D three-factor', (lambda a, b_, ctx: (lambda d: d[a + '_z'] * d[b_ + '_z'] * d[ctx]))(a, b_, ctx), 'does the pair matter more in this context? (pair chosen on discovery data only)'))
R = pd.DataFrame([r for r in D if r and 'p_discovery' in r])
R['bh_discovery_q'] = multipletests(R.p_discovery, method='fdr_bh')[1]
R['passes_discovery'] = (R.bh_discovery_q < 0.10) & R.same_sign_halves
R['confirmed'] = R.passes_discovery & (R.confirm_lo95 > 0)
R.sort_values('p_discovery').to_csv('discovery/out/screen_qld.csv', index=False)
pd.DataFrame([r for r in D if r and 'note' in r]).to_csv('discovery/out/screen_qld_skipped.csv', index=False)
print('candidates tested', len(R), '| pass discovery (BH 10% + stable halves)', int(R.passes_discovery.sum()), '| also confirmed out-of-sample', int(R.confirmed.sum()))
cols = ['name', 'family', 'coef_per_sd', 'se', 'p_discovery', 'bh_discovery_q', 'same_sign_halves', 'confirm_gain_per_race', 'confirm_lo95', 'confirm_hi95', 'confirm_top_pick_change_pts', 'corr_with_baseline']
print(R[R.family.isin(['A directed', 'M new feature'])][cols].to_string(index=False))
# course-specificity of confirmed terms: per-track coefficient (all periods), heterogeneity Q and I^2
allx = pd.concat([dev, ev]); rows_ = []
for nm, fam in R[R.confirmed][['name', 'family']].values:
    parts = nm.replace(' (main effect)', '').split(' x ')
    def ex(d, parts=parts):
        out = 1.0
        for p_ in parts: out = out * (d[p_ + '_z'] if p_ + '_z' in d else d[p_])
        return out
    try: t_all = term(allx, ex)
    except Exception: continue
    t_all = np.nan_to_num(t_all / (np.nanstd(t_all) or 1)); bs_, ses_ = [], []
    for trk, gi in allx.groupby('track').groups.items():
        sub = allx.loc[gi]
        if sub.race_id.nunique() < 150: continue
        tt = t_all[allx.index.get_indexer(gi)]; Rt = H.Races(sub.race_id.values, sub.win.values, sub.offset.values, tt[:, None])
        bb = H.fit(Rt, np.array([1e-6])); se_ = H.posterior_sd(Rt, bb, np.array([1e-6]))[0]; bs_.append(bb[0]); ses_.append(se_)
        rows_.append({'term': nm, 'track': trk, 'races': sub.race_id.nunique(), 'coef': round(float(bb[0]), 4), 'se': round(float(se_), 4)})
    bs_, w_ = np.array(bs_), 1 / np.array(ses_) ** 2; pooled = (bs_ * w_).sum() / w_.sum(); Q = float(((bs_ - pooled) ** 2 * w_).sum()); k_ = len(bs_)
    rows_.append({'term': nm, 'track': 'ALL (pooled)', 'races': None, 'coef': round(pooled, 4), 'se': round(float(1 / np.sqrt(w_.sum())), 4), 'Q': round(Q, 1), 'df': k_ - 1, 'I2_%': round(max(0, (Q - (k_ - 1)) / Q) * 100, 1) if Q > 0 else 0})
CS = pd.DataFrame(rows_); CS.to_csv('discovery/out/screen_qld_course_specificity.csv', index=False); print(CS[CS.track == 'ALL (pooled)'].to_string(index=False))
print(R[R.passes_discovery].sort_values('confirm_gain_per_race', ascending=False)[cols].head(25).to_string(index=False))
