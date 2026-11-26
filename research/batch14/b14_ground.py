"""Batch 14 s6: extra ground, when it was covered, and (experimentally) racing without cover. Queensland tracking (distance from the rail
per 200 m segment, ground covered per run); SA where supplied. Outcome as before: next-run surprise (kg) = information the rating missed.
width_early   = mean distance from the rail in segments ending 1000+ m out
width_turn    = mean distance from the rail over 800-400 m out (approach and home turn at most Queensland tracks; geometry not verified per track)
width_straight= mean distance from the rail over the last 400 m
exposed (EXPERIMENTAL proxy) = at the 600 and 400 m marks, 3 m+ off the rail with no runner within 0.30 s ahead AND within 1.5 m laterally.
  Segment-average lateral positions and mark times cannot measure aerodynamic cover; this only separates 'wide with a horse in front' from
  'wide alone'. Reported with its agreement between the two marks; not a measurement of cover.
Interaction asked by the owner: extra ground while accelerating (field-relative speed 600-400 above the field) vs while cruising."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, os, sys, duckdb
os.environ['LEADERS_ONLY'] = '1'; sys.argv = ['x']
exec(open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0])
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct'
c = duckdb.connect('/home/claude/racing-intelligence/history/history.duckdb', read_only=True)
OUT = {}
def coef(m, k): return (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3))
for st, d0, sec, rac in [('QLD', Q, 'sectional', 'race'), ('SA', S, 'sa_sectional', 'sa_race')]:
    R = c.execute(f"select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.dist_to_rail_m rail from {sec} s join {rac} r using (race_id) where s.dist_to_rail_m is not null").fetchdf()
    R = R[R.race_id.isin(d0.race_id.unique())]
    if len(R) < 1000: OUT[st] = 'no lateral data'; continue
    K = ['race_id', 'saddlecloth']
    w = pd.DataFrame({'width_early': R[R.to_go >= 1000].groupby(K).rail.mean(), 'width_turn': R[R.to_go.between(400, 799)].groupby(K).rail.mean(),
                      'width_straight': R[R.to_go < 400].groupby(K).rail.mean()}).reset_index()
    d = d0.merge(w, on=K, how='left').dropna(subset=['early_pos', 'def800c']).copy()
    for v in ['width_early', 'width_turn', 'width_straight']: d[v + '_rel'] = d[v] - d.groupby('race_id')[v].transform('median')
    # exposed proxy at 600 and 400 marks: rail at the mark = the segment ending there (b14_build kept rail600/rail400)
    for mk in [600, 400]:
        t = d[['race_id', 'saddlecloth', f'cum{mk}', f'rail{mk}']].dropna(); cover = []
        for rid, gq in t.groupby('race_id'):
            cm = gq[f'cum{mk}'].values; rl = gq[f'rail{mk}'].values
            ahead = (cm[None, :] < cm[:, None]) & (cm[:, None] - cm[None, :] <= 0.30) & (np.abs(rl[None, :] - rl[:, None]) <= 1.5)
            cover += list(zip([rid] * len(gq), gq.saddlecloth.values, ahead.any(axis=1)))
        cv = pd.DataFrame(cover, columns=['race_id', 'saddlecloth', f'cov{mk}']); d = d.merge(cv, on=K, how='left')
    d['wide'] = ((d.rail600 >= 3) & (d.rail400 >= 3)).astype(int)
    d['exposed'] = (d.wide.astype(bool) & ~d.cov600.fillna(True).astype(bool) & ~d.cov400.fillna(True).astype(bool)).astype(int)
    d['wide_cover'] = (d.wide.astype(bool) & d.cov600.fillna(False).astype(bool) & d.cov400.fillna(False).astype(bool)).astype(int)
    agree = d[d.wide == 1]; r = {'runs': len(d), 'wide at 600 and 400 (3 m+) %': round(100 * d.wide.mean(), 1),
         'of wide runs: exposed at both marks %': round(100 * agree.exposed.mean(), 1), 'of wide runs: covered at both marks %': round(100 * agree.wide_cover.mean(), 1),
         'cover flag agreement 600 vs 400 (wide runs) %': round(100 * (agree.cov600 == agree.cov400).mean(), 1)}
    for v in ['width_early_rel', 'width_turn_rel', 'width_straight_rel']: d[v + '_z'] = d[v] / d[v].std()
    e = d.dropna(subset=['width_early_rel', 'width_turn_rel', 'width_straight_rel']).copy()
    m = smf.ols('inn_n1 ~ width_early_rel_z + width_turn_rel_z + width_straight_rel_z + ' + CTRL, e).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(e.horse)[0]})
    r['next-run kg per sd of width: early, turn, straight'] = {k: coef(m, k) for k in ['width_early_rel_z', 'width_turn_rel_z', 'width_straight_rel_z']}
    r['sd of width (m): early, turn, straight'] = [round(e[v].std(), 2) for v in ['width_early_rel', 'width_turn_rel', 'width_straight_rel']]
    e['accel_turn'] = (e.v600r > 0).astype(int)
    m2 = smf.ols('inn_n1 ~ width_turn_rel_z * accel_turn + width_early_rel_z + width_straight_rel_z + ' + CTRL, e).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(e.horse)[0]})
    r['turn width x moving up on the field 600-400 (interaction)'] = {k: coef(m2, k) for k in ['width_turn_rel_z', 'width_turn_rel_z:accel_turn']}
    w_ = e[e.wide == 1].copy()
    m3 = smf.ols('inn_n1 ~ exposed + width_turn_rel_z + ' + CTRL, w_).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(w_.horse)[0]})
    r['wide runs only: exposed (proxy) vs wide with a horse in front, next-run kg'] = {'exposed': coef(m3, 'exposed'), 'n wide runs': len(w_), 'n exposed': int(w_.exposed.sum())}
    # does this run's finish look worse when exposed (retrospective)? this-run surprise
    m4 = smf.ols('dyn_nat_inn ~ exposed + width_turn_rel_z + C(rband) + early_pos + tz + tz_miss + C(dband) + field', w_).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(w_.horse)[0]})
    r['wide runs only: exposed (proxy), THIS-run surprise kg'] = coef(m4, 'exposed')
    # is width a horse habit? split-half r of turn width (8+ runs)
    h = e.groupby('horse').filter(lambda g: len(g) >= 8).sort_values('meeting_date').copy(); h['half'] = h.groupby('horse').cumcount() % 2
    p = h.groupby(['horse', 'half']).width_turn_rel.mean().unstack().dropna(); r['turn width split-half r (horses 8+ runs)'] = (round(p[0].corr(p[1]), 3), len(p))
    OUT[st] = r; print(st, json.dumps(r, default=str), flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_ground.json', 'w'), indent=1, default=str)
