"""Batch 8, quick test 4 (Qld only, 200m sectionals): finishing profiles of run t and the horse's next-start surprise."""
import numpy as np, pandas as pd, duckdb, statsmodels.formula.api as smf
pd.set_option('display.width', 220)
con = duckdb.connect('../history/history.duckdb', read_only=True)
S = con.execute("""select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.avg_speed_ms v, s.position pos
                   from sectional s join race r using (race_id) where r.distance_m - s.segment_end_m in (0, 200, 400, 600, 800)""").fetchdf()
W = S.pivot_table(index=['race_id', 'saddlecloth'], columns='to_go', values=['v', 'pos']).reset_index()
W.columns = ['race_id', 'saddlecloth'] + [f'{a}{int(b)}' for a, b in W.columns[2:]]
W = W.dropna(subset=['v0', 'v200', 'v400', 'pos800', 'pos0'])
q = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'saddlecloth', 'field', 'finish_pos', 'distance_m'])
W = W.merge(q, on=['race_id', 'saddlecloth'])
W = W[W.finish_pos.notna()]
med = lambda c: W.groupby('race_id')[c].transform('median')
W['acc_300'] = W.v200 - W.v400; W['acc_last'] = W.v0 - W.v200            # speed change into the 400-200 and the last 200
W['r_v0'] = W.v0 - med('v0'); W['r_v200'] = W.v200 - med('v200'); W['r_acc300'] = W.acc_300 - med('acc_300'); W['r_acclast'] = W.acc_last - med('acc_last')
n0 = len(W); W = W[(W.r_v0.abs() < 4) & (W.r_v200.abs() < 4) & (W.r_acclast.abs() < 4) & (W.r_acc300.abs() < 4)].copy(); print('dropped implausible speed rows:', n0 - len(W), 'of', n0)
W['pos800_pct'] = W.pos800 / W.field; W['gained'] = W.pos800 - W.pos0
W['profile'] = np.select([
    (W.pos800 <= 3) & (W.r_acc300 >= 0.15) & (W.r_v0 >= 0.2),                     # (i) on speed, kicks around 300m, extends late
    (W.r_acclast >= 0.3) & (W.r_v200 >= 0) & (W.pos800 > 3),                      # (ii) keeps strong speed while others tire (not on speed)
    (W.pos800_pct >= 0.6) & (W.gained >= 3) & (W.r_v0 <= 0.2),                     # (iii) back, passes tiring horses, no unusual speed
    (W.r_acclast >= 0.5) & (W.r_v200 < 0)],                                         # (iv) only kicks in the last 200m
    ['(i) on-speed, kicks at 300m, extends', '(ii) holds speed as others tire', '(iii) passes tiring horses, ordinary speed', '(iv) late-only kick'], 'other')
E = pd.read_parquet('/tmp/exp/rt/E.parquet')
E = E[E.state == 'QLD'].merge(W[['race_id', 'horse_id', 'profile', 'r_v0', 'r_v200', 'r_acc300', 'r_acclast', 'pos800_pct', 'gained', 'v0', 'v200', 'distance_m']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id', 'distance_m': 'dist_t'}),
            on=['q_race_id', 'q_horse_id'], how='inner')
print('Qld runs with sectionals and a measured next start (7-120 days):', len(E), '| horses', E.horse.nunique())
r = E.groupby(['profile', 'half']).agg(runs=('Y', 'size'), this_run_surprise=('dyn_nat_inn', 'mean'), K=('K', 'mean'), next_surprise_Y=('Y', 'mean'), Ysd=('Y', 'std')).reset_index()
r['Y_se'] = r.Ysd / np.sqrt(r.runs); print(r.drop(columns='Ysd').round(3).to_string(index=False))
# hold this run's surprise constant: does the profile still say something about the next start?
for h, d in E.groupby('half'):
    m = smf.ols("Y ~ C(profile, Treatment('other')) + dyn_nat_inn + K", d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    print('\n', h, 'Y on profile, holding this run\'s surprise fixed (kg, 95% half-width)')
    for k in m.params.index:
        if 'profile' in k: print('  ', k.split('[T.')[1][:-1], round(m.params[k], 3), '+/-', round(1.96 * m.bse[k], 3))
# continuous version
for h, d in E.dropna(subset=['r_v0', 'r_v200', 'r_acc300', 'r_acclast', 'pos800_pct', 'dyn_nat_inn', 'K']).groupby('half'):
    m = smf.ols('Y ~ r_v0 + r_v200 + r_acc300 + r_acclast + pos800_pct + dyn_nat_inn + K', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    print('\n', h, 'continuous sectional measures (kg per m/s, or per share of field):'); print((m.params.round(3).astype(str) + ' +/- ' + (1.96 * m.bse).round(3).astype(str)).to_string())
# ---------- C2: late acceleration x step up ----------
E['move'] = np.select([E.nx_distance_m - E.dist_t >= 200, (E.nx_distance_m - E.dist_t).abs() < 100, E.nx_distance_m - E.dist_t <= -200], ['up 200m+', 'same trip', 'down 200m+'], 'other')
E['late'] = np.select([E.r_acclast >= 0.5, E.r_acclast <= -0.3], ['strong late acceleration', 'faded late'], 'middling')
t = E[E.move != 'other'].groupby(['late', 'move', 'half']).agg(runs=('Y', 'size'), Y=('Y', 'mean'), Ysd=('Y', 'std')).reset_index(); t['Y_se'] = t.Ysd / np.sqrt(t.runs)
print('\nC2 late acceleration x next-start distance move'); print(t.drop(columns='Ysd').round(3).to_string(index=False))
for h, d in E[E.move.isin(['up 200m+', 'same trip'])].dropna(subset=['r_acclast', 'dyn_nat_inn', 'K']).groupby('half'):
    m = smf.ols("Y ~ r_acclast * C(move) + dyn_nat_inn + K", d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    k = [i for i in m.params.index if ':' in i][0]; print(h, 'extra effect of late acceleration when stepping up (kg per m/s):', round(m.params[k], 3), '+/-', round(1.96 * m.bse[k], 3), '| n', len(d))
E.to_parquet('/tmp/exp/rt/E_qld_sect.parquet')
