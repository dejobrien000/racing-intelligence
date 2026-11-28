"""Batch 26 Part 4: why the three Batch 25 measures work - overlap, interactions and where they hold. RESEARCH ONLY.
Tables: /home/claude/b14/b25_phys_{QLD,SA}.parquet (built by batch25/b25_physical.py; measured tracking only).
M3 = 600-200 m speed vs the day's other races (tempo/position adjusted); M1 = last-400 speed vs the day (adjusted); M6t = race shape
due to the race's tempo given the horse's position (+ = tempo worked against it); M5 = speed retention vs the day; M2 = early speed.
Outcome = next-run rating surprise (kg), controls as Batch 25 (this run's surprise, rating vs field, field, distance, first-up,
settling position where held, last-200 vs race median). Standardised measures; 95% intervals by horse bootstrap (150).
Questions (Damo, Batch 26 Part 4):
  Q1 overlap: correlations; each alone vs all three together (does each keep its effect when the others are in?)
  Q2 interactions: M3 x M1, M3 x M6t, M1 x M6t (not assumed additive)
  Q3 does M3 capture sustained speed development? (M3 vs ground gained 600->200, mid-race speed rise, and the effect split by it)
  Q4 does M1 capture speed retention or favourable earlier tempo? (M1's effect by tempo for the horse's position; controlling M5, M2)
  Q5 does M6t pick out demanding runs? (M6t x this run's surprise: are good runs against tempo worth more?)
  Q6 heterogeneity: by distance, course (track), age, experience and running style
Output batch26/out_b26_why.json."""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(264)
Q = pd.read_parquet('/home/claude/b14/b25_phys_QLD.parquet'); S = pd.read_parquet('/home/claude/b14/b25_phys_SA.parquet')
for X in (Q, S):
    X['first_up'] = (X.gap.fillna(999) > 60).astype(float)
    X['gain600_200'] = (X.pos600 - X.pos200) / (X.field_t - 1).clip(lower=1)       # field share of places gained 600 -> 200 m
    X['midrise'] = X.v400 - X.v600                                                 # speed change 600-400 -> 400-200
    X['age_n'] = pd.to_numeric(X.age_n, errors='coerce'); X['k'] = X.n_runs
CTRL = ['dyn_nat_inn', 'rel', 'field_t', 'd', 'first_up', 'settle_rel', 'v200_rel']
def fit(Z, cols, outcome='inn_n1', boot=150, report=None):
    use = cols + [c for c in CTRL if c in Z and Z[c].notna().mean() > 0.5]
    Z = Z[[outcome, 'horse'] + use].dropna(); Z = Z[np.isfinite(Z[[outcome] + use].astype(float)).all(axis=1)]
    if len(Z) < 400: return None
    M = np.c_[np.ones(len(Z)), Z[use].values.astype(float)]; y = Z[outcome].values.astype(float)
    b = np.linalg.lstsq(M, y, rcond=None)[0]
    idx = pd.Series(np.arange(len(Z))).groupby(Z.horse.values).indices; keys = np.array(list(idx), dtype=object); bs = []
    for _ in range(boot):
        pick = np.concatenate([idx[h] for h in rng.choice(keys, len(keys))]); bs.append(np.linalg.lstsq(M[pick], y[pick], rcond=None)[0])
    bs = np.array(bs); rep = report or cols
    return {'n': int(len(Z)), **{c: {'kg_per_sd': round(float(b[1 + use.index(c)]), 3), 'ci': [round(float(np.percentile(bs[:, 1 + use.index(c)], 2.5)), 3), round(float(np.percentile(bs[:, 1 + use.index(c)], 97.5)), 3)]} for c in rep}}
def zs(X, cols):
    X = X.copy()
    for c in cols: X[c] = (X[c] - X[c].mean()) / X[c].std()
    return X
W = {'Qld 2022-24': Q[Q.year <= 2024], 'Qld 2025-26': Q[Q.year >= 2025], 'SA 2024-26': S}
MS = ['M1', 'M3', 'M6_tempo_part']
out = {}
for name, X0 in W.items():
    X = zs(X0, MS + ['M5', 'M2', 'gain600_200', 'midrise', 'unfav'])
    r = {}
    r['Q1_correlations'] = X[MS + ['M5', 'M2', 'dyn_nat_inn', 'gain600_200', 'midrise']].corr().round(3).loc[MS].to_dict()
    r['Q1_each_alone'] = {m: fit(X, [m]) for m in MS}
    r['Q1_all_three_together'] = fit(X, MS)
    for a, b in [('M3', 'M1'), ('M3', 'M6_tempo_part'), ('M1', 'M6_tempo_part')]:
        X[f'{a}x{b}'] = X[a] * X[b]
    r['Q2_interactions'] = fit(X, MS + ['M3xM1', 'M3xM6_tempo_part', 'M1xM6_tempo_part'])
    # Q3 sustained speed development: does M3 work through places gained / speed rise mid-race?
    r['Q3_M3_with_gain_and_midrise'] = fit(X, ['M3', 'gain600_200', 'midrise'])
    X['gain_hi'] = (X0.gain600_200 > 0).astype(float).values
    r['Q3_M3_when_gaining_ground'] = fit(X[X.gain_hi == 1], ['M3']); r['Q3_M3_when_not_gaining'] = fit(X[X.gain_hi == 0], ['M3'])
    # Q4 retention or favourable tempo? M1 by tempo for the horse's position; with M5 and M2 held
    t = X0.unfav
    r['Q4_M1_with_retention_and_early'] = fit(X, ['M1', 'M5', 'M2'])
    r['Q4_M1_tempo_favoured'] = fit(X[(t < -0.15).values], ['M1']); r['Q4_M1_tempo_neutral'] = fit(X[t.abs().le(0.15).values], ['M1'])
    r['Q4_M1_tempo_against'] = fit(X[(t > 0.15).values], ['M1'])
    # Q5 demanding runs: tempo cost x this run's surprise
    X['inn_z'] = (X.dyn_nat_inn - X.dyn_nat_inn.mean()) / X.dyn_nat_inn.std(); X['M6xinn'] = X.M6_tempo_part * X.inn_z
    r['Q5_tempo_cost_x_this_run'] = fit(X, ['M6_tempo_part', 'M6xinn'])
    # Q6 heterogeneity
    het = {}
    dband = pd.cut(X0.d, [0, 1100, 1400, 1800, 4000], labels=['<=1100', '1101-1400', '1401-1800', '1800+']).astype(str).values
    for lab, grp in [('distance', dband),
                     ('age', pd.cut(X0.age_n, [0, 3, 5, 20], labels=['2-3', '4-5', '6+']).astype(str).values),
                     ('experience', pd.cut(X0.k, [-1, 5, 15, 999], labels=['<6 runs', '6-15', '16+']).astype(str).values),
                     ('style', pd.cut(X0.posr600, [-0.01, 0.2, 0.5, 0.8, 1.01], labels=['leader/on-pace', 'handy', 'midfield', 'back']).astype(str).values)]:
        het[lab] = {}
        grp = np.array([str(v) for v in grp])
        for g_ in sorted(set(grp)):
            if g_ in ('nan', 'None'): continue
            m = grp == g_; het[lab][g_] = {mm: (lambda f_: f_[mm] if f_ else None)(fit(X[m], [mm], boot=100)) for mm in MS}
    tr = X0.track.value_counts(); top = tr[tr >= 2500].index.tolist()
    het['course'] = {t_: {mm: (lambda f_: f_[mm] if f_ else None)(fit(X[(X0.track == t_).values], [mm], boot=60)) for mm in MS} for t_ in top}
    r['Q6_heterogeneity'] = het
    out[name] = r
    print(name, json.dumps({k: r[k] for k in ['Q1_all_three_together', 'Q2_interactions', 'Q4_M1_tempo_favoured', 'Q4_M1_tempo_against', 'Q5_tempo_cost_x_this_run']}), flush=True)
    json.dump(out, open('batch26/out_b26_why.json', 'w'), indent=1, default=str)
