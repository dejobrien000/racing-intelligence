"""Batch 25 Part B (Damo 28 Nov 8:19am): meeting-specific physical performance. RESEARCH ONLY - nothing served.

Measured tracking only (Racing Queensland 200 m splits; Racing SA tracking): genuinely independent of our ratings. Nothing here uses
a rating except the OUTCOME (does the measure tell us something the opposition-aware rating does not?).

Per run, phase speeds (m/s): early = jump to the 600 m mark; middle = 600 -> 200 m; late = last 200 m; late400 = last 400 m (400 m to go -> line).
Course par = median by track x exact distance (course constant, all years). dev = speed - par.
MEETING SURFACE (leave-one-race-out): for race r at meeting M (track x date), the mean race-median dev of the OTHER races at M, per
phase. RACE TEMPO = race-median early dev - meeting surface early (how much faster/slower this race went early than the day's other
races at the same course) - surface speed of the day and race tempo are kept separate.
Measures (each standardised; + = better/faster unless stated):
  M1 late400 benchmark: own late400 dev - meeting surface late400 - tempo and position effects (fitted on Qld 2022-24 only)
  M2 early benchmark: own early dev - meeting surface early (absolute early speed for the day; includes the race's tempo)
  M3 middle benchmark: own 600-200 m dev - meeting surface middle - tempo/position effects
  M4 acceleration (600-400 speed minus 800-600 speed) vs the meeting's other runners in the same position band
  M5 speed retention (last 200 speed minus best of the 600-200 m segments) vs the meeting's other runners in the same band
  M6 race-shape cost: how much the horse's position at the 600 and the race's tempo worked against it (expected finish percentile
     from position x tempo, fitted on Qld 2022-24; + = shape worked against the horse)
  M7 against the day's lane/position pattern: from the OTHER races at the meeting, the day's finish advantage by distance from the rail
     and by position at the 400 (shrunk); the horse's expected disadvantage from where it raced (+ = it raced where the day was bad)
  M8 exceptional against tempo: M1 for runners whose position made the tempo unfavourable (on-pace in a fast-early race, back in a
     slow-early race) - interaction M1 x unfavourable tempo
  M9 physical development: M1 (and M2) now minus the horse's mean over its previous 3 tracked runs (own history)
Outcome: next-run rating surprise (kg, relative to the field) and mean of the next 3, controlling for this run's surprise, field-
relative rating, field size, distance, first-up and the production Qld physical inputs (settling position, last-200 vs race median).
Windows: Qld 2022-24 discovery, Qld 2025-26 replication (re-used period), SA 2024-26 independent check (SA rating = Engine v2.3).
95% intervals: bootstrap by horse (200). Output batch25/out_b25_physical.json."""
import json, time, numpy as np, pandas as pd
T0 = time.time(); log = lambda *a: print(f'[{time.time()-T0:6.0f}s]', *a, flush=True)
rng = np.random.default_rng(25)

def load(st):
    X = pd.read_parquet(f'/home/claude/b14/runs_{st}.parquet')
    X = X.rename(columns={'field_x': 'field_t'})
    for c_ in X.columns:
        if str(X[c_].dtype) in ('Float64', 'Int64', 'Int32', 'Float32', 'boolean'): X[c_] = X[c_].astype('float64')
    if st == 'SA':      # SA outcome from the production national rating (Engine v2.3 history, national_c2), not the Qld v3 rating
        N = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race_id', 'horse', 'date', 'dyn_nat', 'dyn_nat_inn', 'field', 'state'])
        N = N.sort_values(['horse', 'date', 'race_id']); g = N.groupby('horse')
        N['inn_n1'] = g.dyn_nat_inn.shift(-1); N['next3'] = pd.concat([g.dyn_nat_inn.shift(-k) for k in (1, 2, 3)], axis=1).mean(axis=1)
        N['rel'] = N.dyn_nat - N.groupby('race_id').dyn_nat.transform('mean')
        X = X.drop(columns=['dyn_nat', 'dyn_nat_inn', 'inn_n1', 'next3']).merge(N[['race_id', 'horse', 'dyn_nat', 'dyn_nat_inn', 'inn_n1', 'next3', 'rel']].rename(columns={'race_id': 'nat_race'}),
                                                                             on=['nat_race', 'horse'], how='left')
    else:
        X['rel'] = X.dyn_nat - X.groupby('nat_race').dyn_nat.transform('mean')
    X['year'] = X.meeting_date.dt.year; X['meet'] = X.track.astype(str) + '|' + X.meeting_date.dt.strftime('%Y-%m-%d')
    X['early'] = (X.d - 600) / X.cum600; X['middle'] = 400 / (X.cum200 - X.cum600); X['late'] = X.v200; X['late400'] = 400 / (X.cum0 - X.cum400)
    for c in ['early', 'middle', 'late', 'late400']: X.loc[~X[c].between(9, 22), c] = np.nan
    X['acc'] = X.v600 - X.v800; X['ret'] = X.v200 - X[['v600', 'v400']].max(axis=1)
    X['posr600'] = (X.pos600 - 1) / (X.field_t - 1).clip(lower=1); X['posr400'] = (X.pos400 - 1) / (X.field_t - 1).clip(lower=1)
    X['band'] = pd.cut(X.posr600, [-0.01, 0.2, 0.5, 0.8, 1.01], labels=False)
    for c_ in X.columns:
        if str(X[c_].dtype) in ('Float64', 'Int64', 'Int32', 'Float32', 'boolean'): X[c_] = X[c_].astype('float64')
    X = X[X.d >= 1000].copy()
    return X

def build(X, fit=None):
    for c in ['early', 'middle', 'late', 'late400']:
        par = X.groupby(['track', 'd'])[c].transform('median'); n = X.groupby(['track', 'd'])[c].transform('count')
        X[c + '_dev'] = (X[c] - par).where(n >= 30)
        rm = X.groupby('race_id')[c + '_dev'].transform('median'); X[c + '_rmed'] = rm
        R = X.drop_duplicates('race_id')[['race_id', 'meet', c + '_rmed']]
        s = R.groupby('meet')[c + '_rmed'].transform('sum'); k = R.groupby('meet')[c + '_rmed'].transform('count')
        R['loro'] = ((s - R[c + '_rmed']) / (k - 1)).where(k >= 3)       # mean of the OTHER races (needs 2+ others)
        X[c + '_surf'] = X.race_id.map(R.set_index('race_id').loro)
    X['tempo'] = X.early_rmed - X.early_surf
    X['onpace'] = (X.posr600 <= 0.2).astype(float); X['back'] = (X.posr600 >= 0.6).astype(float)
    # M1/M3: late400 / middle benchmarks net of the day's surface, race tempo and position (coefficients from Qld 2022-24)
    feats = lambda Z: np.c_[np.ones(len(Z)), Z.tempo, Z.tempo * Z.onpace, Z.tempo * Z.back, Z.def600.clip(upper=8), Z.def600.clip(upper=8) ** 2, Z.posr600, Z.rail400.clip(upper=8)]
    fit = fit or {}
    for c, key in [('late400', 'M1'), ('middle', 'M3')]:
        y = X[c + '_dev'] - X[c + '_surf']; Z = X[['tempo', 'onpace', 'back', 'def600', 'posr600', 'rail400']]
        ok = y.notna() & Z.notna().all(axis=1)
        if key not in fit:
            tr = ok & (X.year <= 2024)
            fit[key] = np.linalg.lstsq(feats(X[tr]), y[tr].values, rcond=None)[0]
        X[key] = np.nan; X.loc[ok, key] = y[ok].values - feats(X[ok]) @ fit[key]
    X['M2'] = X.early_dev - X.early_surf
    # M4/M5 vs the meeting's other races, same position band (leave-one-race-out)
    for c, key in [('acc', 'M4'), ('ret', 'M5')]:
        R = X.groupby(['meet', 'band', 'race_id'])[c].agg(['sum', 'count']).reset_index()
        T = R.groupby(['meet', 'band'])[['sum', 'count']].transform('sum')
        R['loro'] = ((T['sum'] - R['sum']) / (T['count'] - R['count'])).where((T['count'] - R['count']) >= 8)
        X = X.drop(columns=[key + '_b'], errors='ignore').merge(R[['meet', 'band', 'race_id', 'loro']].rename(columns={'loro': key + '_b'}), on=['meet', 'band', 'race_id'], how='left')
        X[key] = X[c] - X[key + '_b']
    # M6 race-shape cost: expected finish percentile from position at the 600 x tempo (fit Qld 2022-24)
    sf = lambda Z: np.c_[np.ones(len(Z)), Z.posr600, Z.posr600 ** 2, Z.tempo, Z.tempo * Z.posr600, Z.tempo * Z.posr600 ** 2]
    ok = X[['posr600', 'tempo', 'fp_pct']].notna().all(axis=1)
    if 'M6' not in fit:
        tr = ok & (X.year <= 2024); fit['M6'] = np.linalg.lstsq(sf(X[tr]), X.loc[tr, 'fp_pct'].values, rcond=None)[0]
        fit['M6_notempo'] = np.linalg.lstsq(sf(X[tr])[:, :3], X.loc[tr, 'fp_pct'].values, rcond=None)[0]
    X['M6'] = np.nan; e1 = sf(X[ok]) @ fit['M6']; e0 = sf(X[ok])[:, :3] @ fit['M6_notempo']
    X.loc[ok, 'M6'] = e1 - 0.5                                                                     # expected finish percentile given shape (0.5 = neutral; + = shape against)
    X.loc[ok, 'M6_tempo_part'] = e1 - e0                                                           # the part due to this race's tempo
    # M7 the day's lane/position pattern from the OTHER races at the meeting
    out = []
    for m, G in X[X.rail400.notna() & X.posr400.notna()].groupby('meet'):
        races = G.race_id.unique()
        if len(races) < 4: continue
        for r in races:
            O = G[G.race_id != r]
            A = np.c_[np.ones(len(O)), O.rail400.clip(upper=8) - O.rail400.clip(upper=8).mean(), O.posr400 - 0.5]
            b = np.linalg.lstsq(A, O.fp_pct.values, rcond=None)[0]; nb = len(O); b[1:] *= nb / (nb + 150.0)   # shrink small days
            Gr = G[G.race_id == r]
            cost = b[1] * (Gr.rail400.clip(upper=8) - Gr.rail400.clip(upper=8).mean()) + b[2] * (Gr.posr400 - Gr.posr400.mean())
            out.append(pd.DataFrame({'race_id': r, 'saddlecloth': Gr.saddlecloth, 'M7': cost.values, 'lane_slope': b[1], 'pos_slope': b[2]}))
    L = pd.concat(out); X = X.merge(L, on=['race_id', 'saddlecloth'], how='left')
    X['unfav'] = np.where(X.onpace == 1, X.tempo, np.where(X.back == 1, -X.tempo, 0.0))
    X = X.sort_values(['horse', 'meeting_date', 'race_id']); g = X.groupby('horse')
    for k in ['M1', 'M2']: X[k + '_own3'] = g[k].transform(lambda s: s.shift().rolling(3, min_periods=2).mean()); X['M9_' + k] = X[k] - X[k + '_own3']
    return X, fit

CTRL = ['dyn_nat_inn', 'rel', 'field_t', 'd', 'first_up', 'settle_rel', 'v200_rel']
def test(X, col, outcome='inn_n1', extra=None, label=None):
    Z = X.copy(); Z['first_up'] = (Z.gap.fillna(999) > 60).astype(float)
    cols = [col] + (extra or []) + [c for c in CTRL if c in Z and Z[c].notna().mean() > 0.5]     # SA has no settling-position field
    Z = Z[[outcome, 'horse'] + cols].dropna(); Z = Z[np.isfinite(Z[[outcome] + cols].astype(float)).all(axis=1)]
    if len(Z) < 300: return None
    sd = Z[col].std(); Z[col] = (Z[col] - Z[col].mean()) / sd
    for e in (extra or []): Z[e] = (Z[e] - Z[e].mean()) / Z[e].std()
    Xm = np.c_[np.ones(len(Z)), Z[cols].values.astype(float)]; y = Z[outcome].values.astype(float)
    b = np.linalg.lstsq(Xm, y, rcond=None)[0][1]
    hs = Z.horse.values; idx = pd.Series(np.arange(len(Z))).groupby(hs).indices; uh = np.array(list(idx.keys()), dtype=object); bs = []
    for _ in range(200):
        pick = np.concatenate([idx[h] for h in rng.choice(uh, len(uh))]); bs.append(np.linalg.lstsq(Xm[pick], y[pick], rcond=None)[0][1])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return {'kg_per_sd': round(float(b), 3), 'ci': [round(float(lo), 3), round(float(hi), 3)], 'n': int(len(Z)), 'sd_raw': round(float(sd), 4)}

res = {}
Q = load('QLD'); Q, FIT = build(Q); log('Qld built', len(Q))
S_ = load('SA'); S_, _ = build(S_, fit=dict(FIT)); log('SA built', len(S_))
windows = [('Qld 2022-24', Q[Q.year <= 2024]), ('Qld 2025-26', Q[Q.year >= 2025]), ('SA 2024-26', S_)]
# surface vs tempo: how much of the race-to-race variation is the day's surface and how much the race's own tempo
for name, W in windows:
    R = W.drop_duplicates('race_id')
    v = {}
    for c in ['early', 'late400']:
        ok = R[[c + '_rmed', c + '_surf']].notna().all(axis=1)
        v[c + '_r_race_vs_day_others'] = round(float(np.corrcoef(R.loc[ok, c + '_rmed'], R.loc[ok, c + '_surf'])[0, 1]), 3)
    ok = R[['tempo', 'late400_rmed', 'late400_surf']].notna().all(axis=1)
    v['tempo_sd_ms'] = round(float(R.loc[ok, 'tempo'].std()), 3)
    v['corr_tempo_vs_day_surface_early'] = round(float(np.corrcoef(R.loc[ok, 'tempo'], R.loc[ok, 'early_surf'].fillna(0))[0, 1]), 3)
    v['corr_tempo_vs_race_late_net_of_surface'] = round(float(np.corrcoef(R.loc[ok, 'tempo'], R.loc[ok, 'late400_rmed'] - R.loc[ok, 'late400_surf'])[0, 1]), 3)
    v['races'] = int(len(R)); v['meetings'] = int(R.meet.nunique())
    res.setdefault('surface_vs_tempo', {})[name] = v
log('surface/tempo', json.dumps(res['surface_vs_tempo']))
MEAS = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M6_tempo_part', 'M7', 'M9_M1', 'M9_M2']
for name, W in windows:
    r = {}
    for m in MEAS:
        r[m] = {'next_run': test(W, m), 'next_3': test(W, m, 'next3')}
    W2 = W.copy(); W2['M8'] = W2.M1 * W2.unfav
    r['M8_M1_x_unfavourable_tempo'] = {'next_run': test(W2, 'M8', extra=['M1', 'unfav']), 'next_3': test(W2, 'M8', 'next3', extra=['M1', 'unfav'])}
    # how much of each measure the rating already carries: correlation with this run's surprise and the rating change it causes
    r['corr_with_this_run_surprise'] = {m: round(float(W[[m, 'dyn_nat_inn']].dropna().corr().iloc[0, 1]), 3) for m in MEAS}
    res.setdefault('tests', {})[name] = r
    log(name, json.dumps({m: r[m]['next_run'] for m in MEAS + ['M8_M1_x_unfavourable_tempo']}))
    json.dump(res, open('batch25/out_b25_physical.json', 'w'), indent=1, default=str)
res['fit_coefficients'] = {k: [round(float(x), 5) for x in v] for k, v in FIT.items()}
# horse-level repeatability of the benchmarks (are they traits?): split-half by run order, horses with 6+ tracked runs, Qld
rep = {}
for m in ['M1', 'M2', 'M3', 'M4', 'M5']:
    Z = Q[['horse', m]].dropna(); Z['k'] = Z.groupby('horse').cumcount(); Z = Z[Z.groupby('horse')[m].transform('size') >= 6]
    a = Z[Z.k % 2 == 0].groupby('horse')[m].mean(); b = Z[Z.k % 2 == 1].groupby('horse')[m].mean()
    rep[m] = {'horses': int(len(a)), 'split_half_r': round(float(np.corrcoef(a, b.reindex(a.index))[0, 1]), 3)}
res['repeatability_qld'] = rep; log('repeatability', json.dumps(rep))
Q.to_parquet('/home/claude/b14/b25_phys_QLD.parquet'); S_.to_parquet('/home/claude/b14/b25_phys_SA.parquet')
json.dump(res, open('batch25/out_b25_physical.json', 'w'), indent=1, default=str)
log('done')
