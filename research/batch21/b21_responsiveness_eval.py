"""Batch 21 B6/B8 (from batch20/b20_race_layer_eval.py): seven rating mechanisms and certainty-weighting interactions.
Original Batch 20 description follows. Batch 20 C6-C8: six separate measures for the rating mechanisms (current v2.3 = C2; stronger = U5EA2: 12 L cap, good runs 1+0.8exp(-n/6),
5yo+ exposed; certainty-weighted reference = PW2) crossed with the existing and refined race layers (RL + rel_x_*), all on production speed
figures (sandbox history identical to production: OFF2 vs C2 max difference 0.0). Judged on the same races, cutoffs and targets as every
earlier national harness test (non-Qld, fields of 6+; window A = 2024 fitted on earlier races, window B = 2025-26).
  1 individual performance error   mean squared (field-relative performance - field-relative pre-race rating), kg^2, runs with 1+ earlier run
  2 individual calibration         slope of field-relative performance on field-relative rating (1 = rating gaps the right size; <1 = too wide)
  3 ranking accuracy               within-race rank correlation of rating with finishing order
  4 race probability calibration   logistic slope of win on logit(model probability) (1 = calibrated; <1 = overconfident)
  5 overall race accuracy          log-likelihood of the winner per race vs the baseline (bootstrap 95%), top-pick strike
  6 by field type                  2-5 within terciles of field inexperience (share of the field with 5 or fewer runs held)
Research only; no prices anywhere. Usage (from research/): python3 batch20/b20_race_layer_eval.py"""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(20)
R = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'field', 'state'])
R['kgpl'] = 1.5 * (1200 / R.distance_m) ** 0.8; ok = R.finish_pos.notna() & R.margin_l.notna() & R.weight_kg.notna()
R['perf'] = np.where(ok, -R.margin_l.clip(upper=25) * R.kgpl + 0.25 * (R.weight_kg - 57), np.nan)
R = R.sort_values(['horse', 'date', 'race']); R['k'] = R.groupby('horse').cumcount()
LS = R.groupby('race').k.apply(lambda s: float((s <= 5).mean())).rename('light_share')
R = R[(R.date >= '2024-01-01') & (R.state != 'QLD') & (R.field >= 6)].copy(); R['win'] = np.where(R.date < '2025-01-01', 'A', 'B')
q = LS.reindex(R.race.unique()).quantile([1 / 3, 2 / 3]).values
band = lambda s: pd.cut(s, [-0.01, q[0], q[1], 1.01], labels=['established fields', 'mixed fields', 'inexperienced fields']).astype(str)
R = R.join(LS, on='race'); R['ftype'] = band(R.light_share)
OUT = {'field_type_cut_points_share_5_or_fewer_held': [round(float(x), 3) for x in q]}
def indiv(f):
    F = pd.read_parquet(f, columns=['race', 'horse', 'dyn_nat']).drop_duplicates(['race', 'horse'])
    X = R.merge(F, on=['race', 'horse']); X = X[X.perf.notna() & X.dyn_nat.notna() & (X.k >= 1)]; X = X[X.groupby('race').perf.transform('count') >= 4].copy()
    X['pr'] = X.perf - X.groupby('race').perf.transform('mean'); X['rr'] = X.dyn_nat - X.groupby('race').dyn_nat.transform('mean'); X['e'] = X.pr - X.rr
    X['a'] = X.groupby('race').dyn_nat.rank(ascending=False); X['b'] = X.groupby('race').finish_pos.rank()
    o = {}
    for key, g in [('all', X)] + list(X.groupby('ftype')):
        rho = g.groupby('race')[['a', 'b']].corr().xs('a', level=1).b
        o[key] = {'runs': int(len(g)), 'error_kg2': round(float((g.e ** 2).mean()), 3), 'calibration_slope': round(float((g.pr * g.rr).sum() / (g.rr ** 2).sum()), 3),
                  'rank_corr': round(float(rho.mean()), 4)}
    return o
def probs(V):
    P = pd.read_parquet(f'/tmp/cand/runners_{V}_R.parquet', columns=['race_id', 'meeting_date', 'win', 'p_A', 'p_B'])
    d = pd.to_datetime(P.meeting_date); P['p'] = np.where(d < pd.Timestamp('2025-01-01'), P.p_A, P.p_B); P = P[P.p.notna() & (d >= pd.Timestamp('2024-01-01'))].copy()
    P['race'] = P.race_id; P = P.join(LS, on='race'); P['ftype'] = band(P.light_share); return P
def calib(P):
    x = np.log(np.clip(P.p.values, 1e-6, 1 - 1e-6) / (1 - np.clip(P.p.values, 1e-6, 1 - 1e-6))); y = P.win.values.astype(float); a, b = 0.0, 1.0
    for _ in range(30):   # two-parameter logistic fit by Newton
        z = a + b * x; m = 1 / (1 + np.exp(-z)); w = m * (1 - m); g = np.array([(y - m).sum(), ((y - m) * x).sum()]); H = np.array([[w.sum(), (w * x).sum()], [(w * x).sum(), (w * x * x).sum()]])
        step = np.linalg.solve(H, g); a, b = a + step[0], b + step[1]
        if np.abs(step).max() < 1e-8: break
    return round(float(b), 3)
def race(V, base):
    a = pd.read_parquet(f'/tmp/cand/res_{V}_R.parquet'); b = pd.read_parquet(f'/tmp/cand/res_{base}_R.parquet'); a['race'] = a.race_id
    j = a.set_index(['window', 'race_id'])[['lp', 'hit']].join(b.set_index(['window', 'race_id'])[['lp', 'hit']], lsuffix='_v', rsuffix='_b', how='inner').reset_index()
    j = j.join(LS, on='race_id'); j['ftype'] = band(j.light_share); o = {}
    for key, g in [('all', j)] + list(j.groupby('ftype')):
        dd = (g.lp_v - g.lp_b).values; bs = dd[rng.integers(0, len(dd), (2000, len(dd)))].mean(1)
        o[key] = {'races': int(len(g)), 'gain_per_race': round(float(dd.mean()), 5), 'ci95': np.percentile(bs, [2.5, 97.5]).round(5).tolist(), 'top_pick_pts': round(100 * float(g.hit_v.mean() - g.hit_b.mean()), 2)}
    for w in ['A', 'B']:
        dd = (j[j.window == w].lp_v - j[j.window == w].lp_b).values; o['window_' + w] = round(float(dd.mean()), 5)
    return o
V7 = [('1 Engine v2.3 (production)', 'C2'), ('2 Cap-only', 'CAP2'), ('3 Uniform 1.3x', 'UR2'), ('4 Age-aware (frozen shadow rule)', 'U5EC2'),
      ('5 History-completeness (v3 experience)', 'U5EH3'), ('6 Stronger, age floor', 'U5EA2'), ('7 Stronger, history-completeness', 'U5EH8'),
      ('PW alone', 'PW2'), ('PW + history-completeness', 'PWH3'), ('PW + stronger history-completeness', 'PWH8')]
MECH = {k: f'/tmp/cand/frames/{v}_national.parquet' for k, v in V7}
EXPF = pd.read_parquet('/tmp/cand/experience_b21.parquet').rename(columns={'race_key': 'race'}).drop_duplicates(['race', 'horse'])
R = R.merge(EXPF[['race', 'horse', 'source']], on=['race', 'horse'], how='left'); R['source'] = R.source.fillna('unknown')
def indiv_src(f):
    F = pd.read_parquet(f, columns=['race', 'horse', 'dyn_nat']).drop_duplicates(['race', 'horse'])
    X = R.merge(F, on=['race', 'horse']); X = X[X.perf.notna() & X.dyn_nat.notna() & (X.k >= 1)]; X = X[X.groupby('race').perf.transform('count') >= 4].copy()
    X['e'] = (X.perf - X.groupby('race').perf.transform('mean')) - (X.dyn_nat - X.groupby('race').dyn_nat.transform('mean'))
    return {s_: {'runs': int(len(g)), 'error_kg2': round(float((g.e ** 2).mean()), 3)} for s_, g in X.groupby('source')}
OUT['individual'] = {k: indiv(f) for k, f in MECH.items()}; print(json.dumps({k: v['all'] for k, v in OUT['individual'].items()}, indent=0), flush=True)
OUT['individual_by_experience_source'] = {k: indiv_src(f) for k, f in MECH.items()}
VAR = {k: v for k, v in V7}
OUT['probability_calibration_slope'] = {}
for k, V in VAR.items():
    P = probs(V); OUT['probability_calibration_slope'][k] = {'all': calib(P), **{t: calib(g) for t, g in P.groupby('ftype')}}
print(json.dumps(OUT['probability_calibration_slope'], indent=0), flush=True)
OUT['race_vs_C2'] = {k: race(V, 'C2') for k, V in VAR.items() if V != 'C2'}
OUT['race_PW_added'] = {'PW + history-completeness vs history-completeness': race('PWH3', 'U5EH3'), 'PW + stronger vs stronger (history-completeness)': race('PWH8', 'U5EH8')}
OUT['race_stronger_vs_completeness'] = {'7 vs 5': race('U5EH8', 'U5EH3'), '7 vs 6': race('U5EH8', 'U5EA2'), '5 vs 4': race('U5EH3', 'U5EC2')}
json.dump(OUT, open('batch21/out_b21_responsiveness_eval.json', 'w'), indent=1)
for s_ in ['race_vs_C2', 'race_PW_added', 'race_stronger_vs_completeness']:
    for k, v in OUT[s_].items(): print(s_, k, v['all'], {t: v[t]['gain_per_race'] for t in ['established fields', 'mixed fields', 'inexperienced fields']}, 'A', v['window_A'], 'B', v['window_B'])
