"""Batch 3, Studies 7-9 (plan: batch03_plan.md). National run table, within-venue figures, venue offsets from shippers,
R20 benchmark comparison, common-feature replication of the evidence groups, and cross-state transfer.
Same figure method in every state: winner's time + margins, par per venue x distance (development races only),
daily variant, no class allowance; national figure = within-venue figure + venue offset (Eagle Farm = 0).
Usage: python3 national.py <history.duckdb> [split_date]   (default split 2025-01-01) -> out/out_nat_*.csv"""
import sys, re, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr
from clogit_tools import prep, fit, score, fit_pct, boot_diff
db = sys.argv[1]; SPLIT = sys.argv[2] if len(sys.argv) > 2 else '2025-01-01'
import os; NAT_STATES = os.environ.get('NAT_STATES', 'NSW,VIC,ACT').split(',')   # SA/WA/TAS added only by a deliberate database release
con = duckdb.connect(db, read_only=True)
slug = lambda t: re.sub(r'[^a-z0-9]+', '-', str(t).lower().replace('&', 'and').replace('_', ' ')).strip('-')
alias = {'caulfield-heath': 'caulfield', 'sandown-hillside': 'sandown', 'sandown-lakeside': 'sandown', 'randwick-kensington': 'randwick', 'kensington': 'randwick',
         'the-valley': 'moonee-valley', 'beaumont-newcastle': 'newcastle', 'newcastle-beaumont': 'newcastle', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill',
         'pakenham-synthetic': 'pakenham', 'ballarat-synthetic': 'ballarat', 'geelong-synthetic': 'geelong', 'sunshine-coast-poly-track': 'sunshine-coast'}
METRO = {'eagle-farm', 'doomben', 'randwick', 'rosehill', 'warwick-farm', 'canterbury', 'flemington', 'caulfield', 'moonee-valley', 'sandown', 'morphettville', 'morphettville-parks', 'ascot', 'belmont'}   # SA/WA metro added 25 Nov 2026 (no effect on NSW/Vic/ACT rows)
PROV = {'sunshine-coast', 'gold-coast', 'ipswich', 'toowoomba', 'newcastle', 'kembla-grange', 'hawkesbury', 'wyong', 'gosford', 'canberra', 'pakenham', 'ballarat',
        'geelong', 'cranbourne', 'bendigo', 'mornington', 'kilmore', 'seymour', 'sale', 'werribee', 'yarra-valley', 'moe', 'warrnambool', 'illawarra-grange'}
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
# ---------- unified run table ----------
q = pd.read_parquet('runs.parquet')
vm = dict(con.execute("select track, bf_track from venue_map where rk = 1").fetchall()); vm['TAB_Park_Gold_Coast'] = 'Gold Coast'
Q = pd.DataFrame({'state': 'QLD', 'venue': q.track.map(lambda t: alias.get(slug(vm.get(t, t)), slug(vm.get(t, t)))), 'date': pd.to_datetime(q.meeting_date),
                  'race_no': q.race_no, 'distance_m': q.distance_m, 'race_time_s': q.race_time_s, 'going': q.cond_group, 'finish_pos': q.finish_pos, 'margin_l': q.margin_l,
                  'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'horse': q.name_key.map(nk),
                  'bm': np.where(q.class_group == 'BM', q.class_num, np.nan), 'class_label': q.class_group, 'barrier': q.barrier, 'settle_rel': q.settle_rel,
                  'q_race_id': q.race_id, 'q_horse_id': q.horse_id})   # Qld keys carried through for linking only
B = con.execute("""select m.state, m.bf_track_slug venue, u.meeting_date date, u.race_no, r.distance_m, r.race_time_s, r.going, u.finish_pos, u.margin_l, u.weight_kg,
                   u.name_key horse, r.class class_label from bn_runner u join bn_meeting m using (meeting_date, slug) join bn_race r using (meeting_date, slug, race_no)
                   where m.state in (""" + ','.join(f"'{x}'" for x in NAT_STATES) + """) and not r.is_trial""").fetchdf()
B['venue'] = B.venue.map(lambda s: alias.get(s, s)); B['date'] = pd.to_datetime(B.date); B['horse'] = B.horse.map(nk)
B['bm'] = B.class_label.str.extract(r'Benchmark (\d+)', expand=False).astype(float); B['barrier'] = np.nan; B['settle_rel'] = np.nan
B['class_label'] = B.class_label.str.extract(r'^(Maiden|Benchmark|Class|Open|Restricted|Group|Listed)', expand=False).fillna('Other')
if os.environ.get('NAT_QLD_BN', '0') == '1':   # Breednet Qld meetings NOT covered by RQ tracking (country meetings, pre-tracking gaps); off until a database release
    BQ = con.execute("""select m.state, m.bf_track_slug venue, u.meeting_date date, u.race_no, r.distance_m, r.race_time_s, r.going, u.finish_pos, u.margin_l, u.weight_kg,
                        u.name_key horse, r.class class_label from bn_runner u join bn_meeting m using (meeting_date, slug) join bn_race r using (meeting_date, slug, race_no)
                        where m.state = 'QLD' and not r.is_trial""").fetchdf()
    BQ['venue'] = BQ.venue.map(lambda s: alias.get(s, s)); BQ['date'] = pd.to_datetime(BQ.date); BQ['horse'] = BQ.horse.map(nk)
    BQ['bm'] = BQ.class_label.str.extract(r'Benchmark (\d+)', expand=False).astype(float); BQ['barrier'] = np.nan; BQ['settle_rel'] = np.nan
    BQ['class_label'] = BQ.class_label.str.extract(r'^(Maiden|Benchmark|Class|Open|Restricted|Group|Listed)', expand=False).fillna('Other')
    qm = set(Q.date.dt.strftime('%Y-%m-%d') + '|' + Q.venue); BQ['mid'] = BQ.date.dt.strftime('%Y-%m-%d') + '|' + BQ.venue
    # safety net: a Breednet meeting sharing most of its horses with a same-day RQ meeting is the same meeting under another name
    ov = BQ[~BQ.mid.isin(qm)].merge(Q[['date', 'horse']].drop_duplicates(), on=['date', 'horse']).groupby('mid').size() / BQ.groupby('mid').size()
    same = set(ov[ov >= 0.5].index); keep = ~BQ.mid.isin(qm) & ~BQ.mid.isin(same)
    print('Breednet Qld meetings:', BQ.mid.nunique(), '| already RQ-tracked:', BQ[BQ.mid.isin(qm)].mid.nunique(), '| same horses as an RQ meeting:', len(same), '| added:', BQ[keep].mid.nunique())
    B = pd.concat([B, BQ[keep].drop(columns='mid')], ignore_index=True)
U = pd.concat([Q, B], ignore_index=True)
U = U[~U.class_label.fillna('').str.contains('Hurdle|Steeple')]
U['race'] = U.state + '|' + U.venue + '|' + U.date.dt.strftime('%Y-%m-%d') + '|' + U.race_no.astype(str)
U['field'] = U.groupby('race')['race'].transform('size'); U['win'] = (U.finish_pos == 1).astype(int)
U['tier'] = np.where(U.venue.isin(METRO), 'metro', np.where(U.venue.isin(PROV), 'provincial', 'country'))
U['period'] = np.where(U.date < SPLIT, 'development', 'evaluation')
U['meeting_id'] = U.date.dt.strftime('%Y-%m-%d') + '|' + U.venue
U = U.drop_duplicates(['race', 'horse'])
print('unified runs:', len(U), U.groupby('state').race.nunique().to_dict(), '| split', SPLIT)
# ---------- within-venue figures ----------
r = U[U.win == 1].drop_duplicates('race')[['race', 'state', 'venue', 'meeting_id', 'distance_m', 'race_time_s', 'period']].copy()
r = r[(r.distance_m / r.race_time_s).between(14, 19)]
r['vd'] = r.venue + '|' + r.distance_m.astype(int).astype(str); r['km'] = r.distance_m / 1000; r['variant'] = 0.0
for it in range(6):
    dv = r[r.period == 'development']
    par = (dv.race_time_s - dv.km * dv.variant).groupby(dv.vd).median(); r['par'] = r.vd.map(par)
    res = (r.race_time_s - r.par) / r.km; gm = res.groupby(r.meeting_id)
    r['variant'] = r.meeting_id.map(gm.sum() / (gm.count() + 2))
r['n_vd'] = r.vd.map(r[r.period == 'development'].groupby('vd').race.count()).fillna(0)
U = U.merge(r[['race', 'par', 'variant', 'km', 'n_vd']].assign(speed=r.distance_m / r.race_time_s), on='race', how='left')
spl = 2.4 / U.speed
U['run_time'] = U.race_time_s + U.margin_l.clip(upper=30).fillna(np.nan) * spl
U.loc[U.finish_pos == 1, 'run_time'] = U.race_time_s
U['kgpl'] = 1.5 * (1200 / U.distance_m) ** 0.8
U['fig_w'] = 100 + U.kgpl * ((U.par + U.km * U.variant) - U.run_time) / spl + (U.weight_kg - 57)
U.loc[(U.n_vd < 8) | U.finish_pos.isna(), 'fig_w'] = np.nan
# ---------- venue offsets from horses that move between venues within 60 days ----------
U = U.sort_values(['horse', 'date', 'race_no']).reset_index(drop=True)
g = U.groupby('horse')
U['prev_venue'] = g.venue.shift(); U['prev_fig'] = g.fig_w.shift(); U['prev_date'] = g.date.shift(); U['prev_state'] = g.state.shift()
U['gap'] = (U.date - U.prev_date).dt.days
def offsets(pairs):
    venues = sorted(set(pairs.venue) | set(pairs.prev_venue)); ix = {v: i for i, v in enumerate(venues)}
    n = len(pairs); rows = np.r_[np.arange(n), np.arange(n), [n]]; cols = np.r_[pairs.venue.map(ix).values, pairs.prev_venue.map(ix).values, [ix['eagle-farm']]]
    vals = np.r_[np.ones(n), -np.ones(n), [100.0]]
    # a horse's national figure should not change just because it changed venue: (fig_B + off_B) = (fig_A + off_A)  =>  off_B - off_A = fig_A - fig_B
    A = coo_matrix((vals, (rows, cols)), shape=(n + 1, len(venues))).tocsr(); y = np.r_[(pairs.prev_fig - pairs.fig_w).values, [0.0]]
    sol = lsqr(A, y, damp=0.05)[0]; cnt = pd.concat([pairs.venue, pairs.prev_venue]).value_counts()
    return pd.DataFrame({'venue': venues, 'offset': sol, 'pairs': [int(cnt.get(v, 0)) for v in venues]})
pairs = U[U.gap.between(7, 60) & U.fig_w.notna() & U.prev_fig.notna() & (U.venue != U.prev_venue)]
off = offsets(pairs); off = off[off.pairs >= 30]
off_a = offsets(pairs[pairs.date < SPLIT]).rename(columns={'offset': 'offset_dev', 'pairs': 'pairs_dev'})
off_b = offsets(pairs[pairs.date >= SPLIT]).rename(columns={'offset': 'offset_eval', 'pairs': 'pairs_eval'}) if (pairs.date >= SPLIT).sum() > 500 else pd.DataFrame(columns=['venue', 'offset_eval', 'pairs_eval'])
off = off.merge(off_a, on='venue', how='left').merge(off_b, on='venue', how='left')
off['state'] = off.venue.map(U.drop_duplicates('venue').set_index('venue').state); off['tier'] = off.venue.map(lambda v: 'metro' if v in METRO else ('provincial' if v in PROV else 'country'))
off.sort_values('offset', ascending=False).to_csv('out/out_nat_venue_offsets.csv', index=False)
stab = off.dropna(subset=['offset_dev', 'offset_eval']); stab = stab[(stab.pairs_dev >= 30) & (stab.pairs_eval >= 30)]
print('venue offsets:', len(off), 'venues;', 'stability corr dev vs eval:', round(stab[['offset_dev', 'offset_eval']].corr().iloc[0, 1], 3) if len(stab) > 5 else 'n/a', 'on', len(stab), 'venues')
print(off.groupby(['state', 'tier']).offset.agg(['median', 'count']).round(2).to_string())
U['fig_n'] = U.fig_w + U.venue.map(off.set_index('venue').offset)
# ---------- Study 7 / R20: winners' national figure by benchmark band and state ----------
wn = U[(U.win == 1) & U.bm.notna() & U.fig_n.notna()].drop_duplicates('race').copy()
wn['band'] = pd.cut(wn.bm, [0, 61, 67, 75, 81, 200], labels=['BM58', 'BM64', 'BM72', 'BM78', 'BM84+']).astype(str)
wn['dist_band'] = pd.cut(wn.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
rows = []
for band, h in wn.groupby('band'):
    if h.state.nunique() < 2: continue
    h = h.dropna(subset=['fig_n', 'state', 'tier', 'dist_band', 'going'])   # (Breednet Qld country races can lack a going description)
    m = smf.ols("fig_n ~ C(state, Treatment('QLD')) + C(tier) + C(dist_band) + C(going)", data=h).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(h.meeting_id)[0]})
    for st in ['NSW', 'VIC', 'ACT']:
        t = f"C(state, Treatment('QLD'))[T.{st}]"
        if t in m.params: rows.append({'band': band, 'state_vs_QLD': st, 'winners_state': int((h.state == st).sum()), 'winners_QLD': int((h.state == 'QLD').sum()),
                                       'figure_difference_kg': round(m.params[t], 2), 'lo95': round(m.conf_int().loc[t, 0], 2), 'hi95': round(m.conf_int().loc[t, 1], 2), 'p': round(m.pvalues[t], 4)})
r20 = pd.DataFrame(rows); r20.to_csv('out/out_nat_r20.csv', index=False); print(r20.to_string(index=False))
med = wn.groupby(['band', 'state', 'tier']).fig_n.agg(['median', 'count']).round(1).reset_index(); med.to_csv('out/out_nat_r20_medians.csv', index=False)
# ---------- pre-race common features (identical definitions in every state) ----------
U.loc[U.finish_pos > U.field, 'finish_pos'] = np.nan                                    # non-finisher codes
U['fpct'] = np.where(U.field > 1, (U.finish_pos - 1) / (U.field - 1), np.nan)
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
def rec(s):
    a = s.shift().values; out = np.full(len(a), np.nan)
    for i in range(len(a)):
        h = a[max(0, i - 5):i + 1][::-1]; h = h[~np.isnan(h)]
        if len(h): out[i] = np.dot(h, wts[:len(h)]) / wts[:len(h)].sum()
    return pd.Series(out, index=s.index)
g = U.groupby('horse')
U['f_avgfp3'] = -g.fpct.transform(lambda s: s.shift().rolling(3, min_periods=1).mean()); U['f_lastfp'] = -g.fpct.shift()
U['f_lastlm'] = -np.log(g.margin_l.shift().clip(0, 30).fillna(0) + 0.5).where(g.fpct.shift().notna())
st_ = g.cumcount(); wn_ = g.win.transform(lambda s: s.shift().fillna(0).cumsum())
U['f_cwin'] = np.where(st_ > 0, wn_ / st_.replace(0, np.nan), np.nan); U['f_lstarts'] = np.log1p(st_)
U['a_rec'] = g.fig_n.transform(rec); U['a_best3'] = g.fig_n.transform(lambda s: s.shift().rolling(3, min_periods=1).max())
best3_now = U.a_best3
def strength(s):
    s = s.dropna().sort_values(ascending=False); return s.head(max(3, len(s) // 2)).mean() if len(s) >= 3 else np.nan
U['fs'] = U.race.map(U.groupby('race').a_best3.apply(strength)); g = U.groupby('horse')
U['a_fs3'] = g.fs.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
U['a_wt_rel'] = U.weight_kg - U.groupby('race').weight_kg.transform('mean')
# days since: every Australian TAB start (Betfair) plus these runs
bf = con.execute("select meeting_date, name_key from bf_runner where state <> 'NZ'").fetchdf(); bf['horse'] = bf.name_key.map(nk); bf['date'] = pd.to_datetime(bf.meeting_date)
alls = pd.concat([bf[['horse', 'date']], U[['horse', 'date']]]).drop_duplicates().sort_values(['horse', 'date']); alls['prev'] = alls.groupby('horse').date.shift()
U = U.merge(alls, on=['horse', 'date'], how='left'); days = (U.date - U.prev).dt.days
U['r_debut'] = days.isna().astype(float); U['r_firstup'] = (days >= 60).astype(float); U['r_7_13'] = days.between(7, 13).astype(float)
U['r_28_59'] = days.between(28, 59).astype(float); U['r_quick'] = (days <= 10).astype(float); U['r_ldays'] = np.log(days.clip(7, 365))
has = U.f_avgfp3.notna(); U['missform'] = (~has).astype(float); U['missfig'] = (has & U.a_rec.isna()).astype(float)
U['shipper'] = ((U.prev_state.notna()) & (U.prev_state != U.state) & U.gap.between(1, 60)).astype(float)
U['race_id'] = U.race
U.to_parquet('national_runs.parquet')
F = ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform']; A = ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig']; R = ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays']   # r_debut left out: outside Qld it duplicates the no-earlier-run flag
# missing-data rates per state (runners in races of 6+)
el = U[(U.field >= 6)]
miss = el.groupby('state')[['f_avgfp3', 'a_rec', 'a_fs3', 'a_wt_rel', 'r_ldays', 'barrier', 'settle_rel']].agg(lambda s: round(100 * s.isna().mean(), 1)); miss.to_csv('out/out_nat_missing.csv'); print('missing % per state:\n', miss.to_string())
# ---------- Study 8: common-feature model by state group and tier ----------
def elig(x):
    x = x[x.field >= 6].copy(); x['n_win'] = x.groupby('race_id').win.transform('sum'); return x[x.n_win == 1]
out = []
for label, sel in [('NSW/ACT/Vic metro', (U.state != 'QLD') & (U.tier == 'metro')), ('NSW/ACT/Vic provincial', (U.state != 'QLD') & (U.tier == 'provincial')),
                   ('NSW/ACT/Vic country', (U.state != 'QLD') & (U.tier == 'country')), ('Qld metro (same common features)', (U.state == 'QLD') & (U.tier == 'metro')),
                   ('Qld all tracked (same common features)', U.state == 'QLD')]:
    x = elig(U[sel]);
    if x[x.period == 'evaluation'].race_id.nunique() < 50 or x[x.period == 'development'].race_id.nunique() < 50:
        out.append({'sample': label, 'note': 'too few races in one period'}); continue
    x = prep(x, F + A + R + ['shipper'])
    res = {k: score(x, v, fit(x, v)) for k, v in {'F': F, 'F+R': F + R, 'F+A': F + A, 'F+A+R': F + A + R}.items()}
    e = x[x.period == 'evaluation']
    base = {'sample': label, 'races_scored': len(res['F']), 'runners_scored': len(e), 'horses_scored': e.horse.nunique(), 'races_fitted': x[x.period == 'development'].race_id.nunique(),
            'fit_F_%': round(fit_pct(res['F']), 2), 'fit_FAR_%': round(fit_pct(res['F+A+R']), 2), 'top_pick_F_%': round(100 * res['F'].hit.mean(), 1), 'top_pick_FAR_%': round(100 * res['F+A+R'].hit.mean(), 1)}
    for nm, a_, b_ in [('A beyond F+R', 'F+R', 'F+A+R'), ('R beyond F+A', 'F+A', 'F+A+R')]:
        m1, lo1, hi1, p1 = boot_diff(res[a_], res[b_]); m2, lo2, hi2, p2 = boot_diff(res[a_], res[b_], by='month')
        base.update({f'{nm}: gain': round(m1, 4), f'{nm}: lo95 meetings': round(lo1, 4), f'{nm}: hi95 meetings': round(hi1, 4), f'{nm}: lo95 months': round(lo2, 4), f'{nm}: hi95 months': round(hi2, 4),
                     f'{nm}: p': round(p1, 4)})
    out.append(base)
s8 = pd.DataFrame(out); s8.to_csv('out/out_nat_replication.csv', index=False); print(s8.T.to_string())
# ---------- Study 9: transfer -- consecutive figures within state vs across states; shipper coefficient ----------
cp = U[U.gap.between(7, 60) & U.fig_n.notna() & U.prev_fig.notna()].copy()
cp['prev_fig_n'] = cp.prev_fig + cp.prev_venue.map(off.set_index('venue').offset)
cp['move'] = np.where(cp.prev_state == cp.state, 'same state', 'different state')
tr = cp.groupby('move').apply(lambda h: pd.Series({'pairs': len(h), 'horses': h.horse.nunique(), 'corr_national': round(h[['fig_n', 'prev_fig_n']].corr().iloc[0, 1], 3),
       'corr_within_venue_only': round(h[['fig_w', 'prev_fig']].corr().iloc[0, 1], 3), 'mean_change_kg': round((h.fig_n - h.prev_fig_n).mean(), 2)}), include_groups=False)
by_dir = cp[cp.move == 'different state'].groupby(['prev_state', 'state']).apply(lambda h: pd.Series({'pairs': len(h), 'corr_national': round(h[['fig_n', 'prev_fig_n']].corr().iloc[0, 1], 3) if len(h) > 20 else np.nan,
       'mean_change_kg': round((h.fig_n - h.prev_fig_n).mean(), 2)}), include_groups=False)
tr.to_csv('out/out_nat_transfer_pairs.csv'); by_dir.to_csv('out/out_nat_transfer_by_direction.csv'); print(tr.to_string()); print(by_dir.to_string())
x = elig(U[U.state.isin(['QLD', 'NSW', 'VIC', 'ACT'])])
x = prep(x, F + A + R + ['shipper']); x['fig_x_ship_z'] = x['a_rec_z'] * x['shipper']   # interaction on the same per-sd scale as the figure
from statsmodels.discrete.conditional_models import ConditionalLogit
dvx = x[x.a_rec.notna()]
mm = ConditionalLogit(dvx.win.values, dvx[[c + '_z' for c in ['a_rec', 'shipper', 'fig_x_ship'] + F + R]].values, groups=dvx.race_id.values).fit(disp=0, maxiter=200)
b, V = np.asarray(mm.params), mm.cov_params()
ratio = (b[0] + b[2]) / b[0]; grad = np.array([-b[2] / b[0] ** 2, 0, 1 / b[0]]); se = float(np.sqrt(grad @ np.asarray(V)[:3, :3] @ grad))
p9 = {'figure_coef_stayers': round(b[0], 3), 'interaction': round(b[2], 3), 'ratio_shippers_to_stayers': round(ratio, 3), 'lo95': round(ratio - 1.96 * se, 3), 'hi95': round(ratio + 1.96 * se, 3),
      'shipper_runs': int(dvx.shipper.sum()), 'races': dvx.race_id.nunique(), 'note': 'all periods pooled; descriptive check of transfer'}
pd.DataFrame([p9]).to_csv('out/out_nat_transfer_coef.csv', index=False); print(p9)
