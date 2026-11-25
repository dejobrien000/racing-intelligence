"""Batch 9 study C (Qld 200m splits): is it real acceleration, or just slowing less than the others?
Part 1: next-start surprise by type, with controls (this run's rating credit, early tempo, absolute late speed, field
quality, distance change, prep stage), split 2022-24 / 2025-26. Part 2: last-start measures as terms on top of Qld v2."""
import json, numpy as np, pandas as pd, duckdb, statsmodels.formula.api as smf
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(10)
con = duckdb.connect('../history/history.duckdb', read_only=True)
S = con.execute("""select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.avg_speed_ms v, r.track, r.distance_m
                   from sectional s join race r using (race_id) where r.distance_m - s.segment_end_m in (0, 200, 400, 600, 800)""").fetchdf()
W = S.pivot_table(index=['race_id', 'saddlecloth', 'track', 'distance_m'], columns='to_go', values='v').reset_index()
W.columns = ['race_id', 'saddlecloth', 'track', 'distance_m'] + [f'v{int(c)}' for c in W.columns[4:]]
W = W.dropna(subset=['v0', 'v200', 'v400', 'v600'])
W = W[(W[['v0', 'v200', 'v400', 'v600']] > 8).all(axis=1) & (W[['v0', 'v200', 'v400', 'v600']] < 20).all(axis=1)]
md = lambda c: W.groupby('race_id')[c].transform('median')
W['acc_abs'] = W.v0 - W.v200                                   # own speed change into the last 200m (m/s); > 0 = really accelerating
W['acc_rel'] = W.acc_abs - md('acc_abs')                       # versus the field (positive = slowed less / quickened more than rivals)
W['tempo'] = md('v600'); W['tempo'] = W.tempo - W.groupby(['track', 'distance_m']).tempo.transform('median')   # race early-ish pace vs course/distance norm
W['late_abs'] = W.v0 - W.groupby(['track', 'distance_m']).v0.transform('median')                               # absolute last-200m speed vs norm
W['type'] = np.select([(W.acc_abs > 0.1) & (W.acc_rel >= 0.3), (W.acc_abs <= 0) & (W.acc_rel >= 0.3)], ['really accelerated', 'slowed less than rivals'], 'neither')
q = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'saddlecloth'])
W = W.merge(q, on=['race_id', 'saddlecloth'])
# ---------- part 1 ----------
EV = pd.read_parquet('/tmp/exp/rt/E.parquet'); EV = EV[EV.state == 'QLD']
EV = EV.merge(W[['race_id', 'horse_id', 'acc_abs', 'acc_rel', 'tempo', 'late_abs', 'type', 'distance_m']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id', 'distance_m': 'dist_t'}), on=['q_race_id', 'q_horse_id'])
fq = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'dyn_nat']).groupby('race_id').dyn_nat.mean().rename('field_q')
EV = EV.merge(fq, left_on='race_id', right_index=True, how='left'); EV['dchg'] = (EV.nx_distance_m - EV.dist_t) / 200; EV['first2'] = (EV.nx_prep_run <= 2).astype(float)
print('Qld runs:', len(EV)); print(EV.groupby(['type', 'half']).agg(runs=('Y', 'size'), this_run=('dyn_nat_inn', 'mean'), next_Y=('Y', 'mean')).round(3).to_string())
out = []
for h, d in EV.dropna(subset=['acc_abs', 'acc_rel', 'tempo', 'late_abs', 'field_q', 'dchg', 'dyn_nat_inn', 'K']).groupby('half'):
    m = smf.ols("Y ~ C(type, Treatment('neither')) + dyn_nat_inn + K + tempo + late_abs + field_q + dchg + first2", d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    for k in m.params.index:
        if k != 'Intercept': out.append({'half': h, 'term': k.replace("C(type, Treatment('neither'))[T.", '').rstrip(']'), 'kg': round(m.params[k], 3), 'plusminus95': round(1.96 * m.bse[k], 3), 'runs': len(d)})
    m2 = smf.ols("Y ~ acc_abs + acc_rel + dyn_nat_inn + K + tempo + late_abs + field_q + dchg + first2", d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    for k in ['acc_abs', 'acc_rel']: out.append({'half': h, 'term': 'continuous ' + k + ' (kg per m/s)', 'kg': round(m2.params[k], 3), 'plusminus95': round(1.96 * m2.bse[k], 3), 'runs': len(d)})
R1 = pd.DataFrame(out); print(R1.to_string(index=False)); R1.to_csv('/tmp/exp/rt/c_late_part1.csv', index=False)
# ---------- part 2: last-start measures as Qld v2 terms ----------
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U = U.merge(W[['race_id', 'horse_id', 'acc_abs', 'acc_rel', 'type']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'}), on=['q_race_id', 'q_horse_id'], how='left')
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
U['ls_acc_abs'] = g.acc_abs.shift(); U['ls_acc_rel'] = g.acc_rel.shift()
U['ls_real_acc'] = (g.type.shift() == 'really accelerated').astype(float).where(U.ls_acc_abs.notna()); U['ls_slowed_less'] = (g.type.shift() == 'slowed less than rivals').astype(float).where(U.ls_acc_abs.notna())
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
x = E.qld_frame(U); allt = sum(QREL.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'qld')
bd = np.array([MAN['families']['QLD']['coef_per_term_sd_dev_fit'][t] for t in allt]); v2 = off + x[['t::' + a for a in allt]].values @ bd
dev = (x.period == 'development').values; ev = ~dev; base = E.metrics(x, v2, pd.Series(ev, index=x.index)); rows = []
for c, nm in [('ls_acc_abs', 'last start: own acceleration in last 200m'), ('ls_acc_rel', 'last start: late speed change vs rivals'), ('ls_real_acc', 'last start: really accelerated'), ('ls_slowed_less', 'last start: only slowed less than rivals')]:
    x = E.zcols(x, [c]); b = E.fit(x, [c], pd.Series(dev, index=x.index), tau=1e-6, offset=v2)
    m = E.metrics(x, E.eta(x, [c], b, offset=v2), pd.Series(ev, index=x.index)); d = m.lp - base.lp
    meets = m.meeting_id.values; um = np.unique(meets); idx = {k: np.flatnonzero(meets == k) for k in um}
    bs = [d.values[np.concatenate([idx[k] for k in rng.choice(um, len(um))])].mean() for _ in range(300)]
    rows.append({'term': nm, 'coef_per_sd': round(float(b[0]), 4), 'gain_2025_26': round(d.mean(), 5), 'lo95': round(np.percentile(bs, 2.5), 5), 'hi95': round(np.percentile(bs, 97.5), 5),
                 'gain_2026': round(d[(m.date.dt.year == 2026).values].mean(), 5), 'top_pick_pts': round(100 * (m.hit - base.hit).mean(), 2), 'coverage_%': round(100 * x.loc[ev, c].notna().mean(), 1)}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/c_late_part2.csv', index=False)
