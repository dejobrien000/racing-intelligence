"""Pre-race feature table for batch 2: one row per runner, every input from earlier runs or from published race details.
Groups: F simple form, A ability/opposition, S sectional, P predicted race shape, T track/distance/going, R fitness/recency.
Usage: python3 features.py runs_rated_dev.parquet ../history/history.duckdb features.parquet"""
import sys, duckdb, numpy as np, pandas as pd
src, db, out = sys.argv[1:4]
d = pd.read_parquet(src).drop_duplicates(['race_id', 'horse_id'])
d['meeting_date'] = pd.to_datetime(d.meeting_date)
for c in ['margin_l', 'distance_m', 'weight_kg', 'days_since', 'l600_vs_best', 'l600_rank', 'settle_rel', 'rel_barrier', 'finish_pct', 'field']:
    d[c] = pd.to_numeric(d[c], errors='coerce').astype(float)
# last 200m per runner from the 200m sectionals
con = duckdb.connect(db, read_only=True)
l2 = con.execute("""with s as (select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.inter_s from sectional s join race r using (race_id))
                    select a.race_id, a.saddlecloth, a.inter_s - b.inter_s l200 from s a join s b on a.race_id=b.race_id and a.saddlecloth=b.saddlecloth
                    where a.to_go = 0 and b.to_go = 200""").fetchdf()
l2 = l2[l2.l200.between(10, 16)]
d = d.merge(l2, on=['race_id', 'saddlecloth'], how='left')
d.loc[~d.finished, 'l200'] = np.nan
d['l200_gap'] = d.l200 - d.groupby('race_id')['l200'].transform('min')
d['fsp_rel'] = d.fsp - d.groupby('race_id')['fsp'].transform('median')
dev = d.meeting_date < '2025-01-01'
level = d[dev].groupby('class_bucket')['rating'].median()
d['class_level'] = d.class_bucket.map(level)
d['dist_band'] = pd.cut(d.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
d['going_g'] = d.cond_group.replace({'Firm': 'Good'}).fillna('Unknown')
d = d.sort_values(['horse_id', 'meeting_date', 'race_no']).reset_index(drop=True)
g = d.groupby('horse_id')
def prev_roll(col, n=3, fn='mean'):
    return g[col].transform(lambda s: getattr(s.shift().rolling(n, min_periods=1), fn)())
X = d[['race_id', 'horse_id', 'meeting_date', 'track', 'race_no', 'field', 'win', 'finished', 'distance_m', 'class_bucket', 'race_name']].copy()
# F simple form
X['f_avgfp3'] = -prev_roll('finish_pct'); X['f_lastfp'] = -g['finish_pct'].shift()
X['f_lastlm'] = -np.log(g['margin_l'].shift() + 0.5)
starts = g.cumcount(); wins = g['win'].transform(lambda s: s.shift().fillna(0).cumsum())
X['f_cwin'] = np.where(starts > 0, wins / starts.replace(0, np.nan), np.nan); X['f_lstarts'] = np.log1p(starts)
# A ability and opposition
X['a_avg3'] = d.avg_last3; X['a_best3'] = d.best_last3; X['a_fs3'] = prev_roll('field_strength')
X['a_cls_gap'] = X.a_avg3 - d.class_level            # horse's average figure above today's class level
X['a_wt_rel'] = d.weight_kg - d.groupby('race_id')['weight_kg'].transform('mean')
# S sectional (from the last start, or the last 3)
X['s_gap600_last'] = -g['l600_vs_best'].shift().clip(upper=3); X['s_gap600_avg3'] = -prev_roll('l600_vs_best').clip(upper=3)
X['s_top3_last'] = (g['l600_rank'].shift() <= 3).astype(float).where(g['l600_rank'].shift().notna())
X['s_gap200_last'] = -g['l200_gap'].shift().clip(upper=1.5); X['s_fsp_last'] = g['fsp_rel'].shift().clip(-8, 8)
# P predicted race shape
X['p_style'] = -prev_roll('settle_rel')                      # higher = races closer to the lead
lead = (prev_roll('settle_rel') <= 0.15).astype(float)
X['p_leader'] = lead.where(prev_roll('settle_rel').notna())
X['p_nlead_others'] = X.groupby('race_id')['p_leader'].transform('sum') - X.p_leader.fillna(0)
X['p_lone'] = ((X.p_leader == 1) & (X.p_nlead_others == 0)).astype(float).where(X.p_leader.notna())
X['p_relbar'] = -d.rel_barrier                               # higher = nearer the inside
X['p_bar_x_style'] = X.p_relbar * X.p_style
X['p_lead_x_press'] = X.p_leader * X.p_nlead_others
# T track, distance, going
def record(keys, name):
    k = d[keys[0]].astype('object').astype(str)
    for kk in keys[1:]: k = k + '|' + d[kk].astype('object').astype(str)
    grp = d.assign(_k=k).groupby(['horse_id', '_k'])
    st = grp.cumcount(); wn = grp['win'].transform(lambda s: s.shift().fillna(0).cumsum())
    X[name + '_starts'] = np.log1p(st)
    X[name + '_win'] = (wn + X.f_cwin.fillna(0.1)) / (st + 1)        # shrunk towards the horse's overall win rate
for keys, name in [(['track'], 't_trk'), (['dist_band'], 't_db'), (['track', 'dist_band'], 't_td')]: record(keys, name)
fig_going = d.assign(gk=d.going_g).groupby(['horse_id', 'gk'])['rating'].transform(lambda s: s.shift().expanding().mean())
X['t_going'] = fig_going - g['rating'].transform(lambda s: s.shift().expanding().mean())
X['t_dchange'] = d.distance_m - g['distance_m'].shift(); X['t_dchange_abs'] = X.t_dchange.abs()
# R fitness and recency (days use every Australian TAB start, from Betfair)
days = d.days_since
X['r_debut'] = days.isna().astype(float)
X['r_firstup'] = (days >= 60).astype(float); X['r_7_13'] = days.between(7, 13).astype(float); X['r_28_59'] = days.between(28, 59).astype(float)
X['r_quick'] = (days <= 10).astype(float)
newprep = (days.isna() | (days >= 60)).astype(int); prep = d.assign(np_=newprep).groupby('horse_id')['np_'].cumsum()
X['r_prep'] = d.assign(p_=prep).groupby(['horse_id', 'p_']).cumcount().add(1).clip(upper=6).astype(float)
X['r_ldays'] = np.log(days.clip(7, 365))
X['venue_tier'] = np.where(d.track.isin(['Eagle_Farm', 'Doomben']), 'metro', np.where(d.track.isin(['Sunshine_Coast', 'Sunshine_Coast_Poly_Track', 'TAB_Park_Gold_Coast', 'Ipswich', 'Toowoomba']), 'provincial', 'country'))
X['period'] = np.where(X.meeting_date < '2025-01-01', 'development', 'evaluation')
X['meeting_id'] = X.meeting_date.dt.strftime('%Y-%m-%d') + '|' + X.track
X.to_parquet(out)
print(X.shape); print(X.filter(regex='^[fasptr]_').notna().mean().round(2).to_string())
