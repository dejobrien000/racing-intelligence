"""Batch 26 Part 6: individual distance suitability - substantive framework (research only; no production change).
Point in time: every quantity at a run uses only the horse's EARLIER held runs (Engine v2.3 frame, national states + Qld rows).
Separates, per horse and distance:
  general sustainable ability = the opposition-aware rating (dyn_nat)
  ability expressed at distance d = kernel-smoothed mean surprise (kg vs the rating) of earlier runs near d on log distance
      (bandwidth h = 0.12, ~12% of distance), shrunk to 0 with k = 3 runs:  suit(d) = sum w*inn / (sum w + 3)
  evidence at d = sum of kernel weights (effective runs near d); uncertainty sd ~ 5.4 / sqrt(evidence + 3)
  repeatable competitive range = distances where suit >= -1 kg with evidence >= 2 (reported as span in metres)
  emerging suitability = slope of surprise on log distance over the horse's last 6 runs (kg per doubling), shrunk
dist_change in the frame is log(distance / previous distance).
Tests (target = this run's surprise, kg; controls: distance change, |distance change|, age, runs held, existing distance record d_rec):
  T1 does suit(today's distance) predict beyond d_rec? (coef per sd, by window; and by evidence level)
  T2 adjacent distances: for a step to an unraced distance band, does suit at the nearest raced distance + emerging slope carry over?
  T3 does a strong run over a longer trip predict suitability for a FURTHER increase? (second step-ups after a successful first)
  T4 link to measured physical performance (Qld/SA tracked horses): do the horse's mid-to-late speed (M3), last-400 (M1) and speed
     retention (M5) benchmarks predict how it handles a step UP or DOWN in trip, beyond suit?
Output batch26/out_b26_distance.json and /tmp/cand/feat_dsuit.parquet (race_id, horse, dsuit, dsuit_ev, dslope) for the harness."""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(266)
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'date', 'state', 'dyn_nat', 'dyn_nat_inn', 'distance_m', 'dist_change',
                                                                  'd_rec', 'd_rec_n', 'age_n', 'field'])
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
F['k'] = F.groupby('horse').cumcount(); F['ld'] = np.log(F.distance_m.astype(float))
H, K = 0.12, 3.0
n = len(F); suit = np.full(n, np.nan); ev = np.zeros(n); slope = np.full(n, np.nan); maxd_ok = np.full(n, np.nan); mind_ok = np.full(n, np.nan)
nearest_gap = np.full(n, np.nan)
hs = F.horse.values; ld = F.ld.values; inn = F.dyn_nat_inn.values
starts = np.r_[0, np.flatnonzero(hs[1:] != hs[:-1]) + 1, n]
grid = np.log(np.arange(800, 3300, 100.0))
for a, b in zip(starts[:-1], starts[1:]):
    for i in range(a + 1, b):
        j = np.arange(a, i); ok = ~np.isnan(inn[j]); j = j[ok]
        if len(j) == 0: continue
        w = np.exp(-(ld[i] - ld[j]) ** 2 / (2 * H * H)); s = w.sum()
        suit[i] = (w * inn[j]).sum() / (s + K); ev[i] = s; nearest_gap[i] = np.abs(ld[i] - ld[j]).min()
        jj = j[-6:]
        if len(jj) >= 3 and np.ptp(ld[jj]) > 0.05:
            x = ld[jj] - ld[jj].mean(); y = inn[jj] - inn[jj].mean(); slope[i] = (x * y).sum() / ((x * x).sum() + 0.05) * np.log(2)     # kg per doubling, shrunk
        if i - a >= 4:
            W = np.exp(-(grid[:, None] - ld[j][None, :]) ** 2 / (2 * H * H)); S = W.sum(1); sg = (W * inn[j][None, :]).sum(1) / (S + K)
            okg = (sg >= -1.0) & (S >= 2.0)
            if okg.any(): mind_ok[i] = np.exp(grid[okg].min()); maxd_ok[i] = np.exp(grid[okg].max())
F['dsuit'] = suit; F['dsuit_ev'] = ev; F['dslope'] = slope; F['range_min'] = mind_ok; F['range_max'] = maxd_ok; F['nearest_lgap'] = nearest_gap
F['dsuit_sd'] = 5.4 / np.sqrt(F.dsuit_ev + K)
F[['race_id', 'horse', 'dsuit', 'dsuit_ev', 'dslope']].fillna({'dsuit': 0.0, 'dsuit_ev': 0.0, 'dslope': 0.0}).drop_duplicates(['race_id', 'horse']).to_parquet('/tmp/cand/feat_dsuit.parquet')
F['win_'] = np.where(F.date < '2025-01-01', '2023-24', '2025-26')
def reg(Z, cols, ctrl, boot=150):
    use = cols + ctrl; Z = Z[['dyn_nat_inn', 'horse'] + use].dropna()
    if len(Z) < 500: return None
    Xs = Z[use].astype(float).copy()
    for c in cols: Xs[c] = (Xs[c] - Xs[c].mean()) / Xs[c].std()
    M = np.c_[np.ones(len(Z)), Xs.values]; y = Z.dyn_nat_inn.values
    b = np.linalg.lstsq(M, y, rcond=None)[0]; idx = pd.Series(np.arange(len(Z))).groupby(Z.horse.values).indices; keys = np.array(list(idx), dtype=object); bs = []
    for _ in range(boot):
        p = np.concatenate([idx[h] for h in rng.choice(keys, len(keys))]); bs.append(np.linalg.lstsq(M[p], y[p], rcond=None)[0])
    bs = np.array(bs)
    return {'n': int(len(Z)), **{c: {'kg_per_sd': round(float(b[1 + use.index(c)]), 3), 'ci': [round(float(np.percentile(bs[:, 1 + use.index(c)], 2.5)), 3), round(float(np.percentile(bs[:, 1 + use.index(c)], 97.5)), 3)]} for c in cols}}
F['absdc'] = F.dist_change.abs()
CT = ['dist_change', 'absdc', 'age_n', 'k']
base = (F.k >= 3) & F.dyn_nat_inn.notna() & (F.date >= '2023-07-01')
out = {'runs_tested': int(base.sum())}
out['T1'] = {}
for w in ['2023-24', '2025-26']:
    Z = F[base & (F.win_ == w)]
    out['T1'][w] = {'suit_alone': reg(Z, ['dsuit'], CT), 'd_rec_alone': reg(Z, ['d_rec'], CT), 'suit_plus_d_rec': reg(Z, ['dsuit', 'd_rec'], CT),
                    'suit_plus_slope': reg(Z, ['dsuit', 'dslope'], CT)}
    for lab, m in [('evidence < 2', Z.dsuit_ev < 2), ('evidence 2-5', Z.dsuit_ev.between(2, 5)), ('evidence > 5', Z.dsuit_ev > 5)]:
        out['T1'][w][f'suit_{lab}'] = reg(Z[m], ['dsuit'], CT, boot=100)
    print(w, json.dumps(out['T1'][w]['suit_plus_d_rec']), flush=True)
# T2 new distance: today's trip more than ~25% from anything raced before (log gap > 0.22)
nd = base & (F.nearest_lgap > 0.22)
out['T2_new_distance'] = {'runs': int(nd.sum()), 'suit_and_slope': reg(F[nd], ['dsuit', 'dslope'], CT),
                          'up_in_trip': reg(F[nd & (F.dist_change > 0)], ['dsuit', 'dslope'], CT), 'down_in_trip': reg(F[nd & (F.dist_change < 0)], ['dsuit', 'dslope'], CT)}
# T3 second step-up after a strong first step-up (each step up = 15%+ longer than the previous run)
G = F.sort_values(['horse', 'date']).copy(); G['up'] = G.dist_change > 0.14            # dist_change is log(distance / previous distance): 15%+ longer
G['up_idx'] = G.groupby('horse').up.cumsum(); fu = G[G.up & (G.up_idx == 1)][['horse', 'date', 'dyn_nat_inn', 'distance_m']].rename(columns={'dyn_nat_inn': 'first_up_surprise', 'date': 'd1', 'distance_m': 'dist1'})
su = G[G.up & (G.up_idx == 2)][['horse', 'date', 'dyn_nat_inn', 'distance_m']].merge(fu, on='horse')
su = su[su.distance_m > su.dist1]
out['T3_further_step_up'] = {'horses': int(len(su)), 'corr_first_step_surprise_vs_second': round(float(su[['dyn_nat_inn', 'first_up_surprise']].corr().iloc[0, 1]), 3),
                             'second_step_surprise_after_strong_first(>=+2kg)': round(float(su[su.first_up_surprise >= 2].dyn_nat_inn.mean()), 3),
                             'second_step_surprise_after_other_first': round(float(su[su.first_up_surprise < 2].dyn_nat_inn.mean()), 3),
                             'n_strong_first': int((su.first_up_surprise >= 2).sum())}
# T4 link to measured physical benchmarks (Qld + SA tracked horses): prior benchmarks x direction of today's trip change
P = pd.read_parquet('/tmp/cand/feat_phys.parquet', columns=['race_id', 'horse', 'ph_m3p', 'ph_m1p', 'ph_n'])
T = []
for st in ['QLD', 'SA']:
    q = pd.read_parquet(f'/home/claude/b14/b25_phys_{st}.parquet', columns=['horse', 'meeting_date', 'M5']).rename(columns={'meeting_date': 'tdate'}); T.append(q)
T = pd.concat(T).sort_values(['horse', 'tdate']); T['m5s'] = T.M5.fillna(0).groupby(T.horse).cumsum(); T['m5c'] = T.M5.notna().astype(float).groupby(T.horse).cumsum()
T = T.groupby(['horse', 'tdate']).last().reset_index()
Fs = F[['race_id', 'horse', 'date']].sort_values('date'); M5 = pd.merge_asof(Fs, T.sort_values('tdate'), left_on='date', right_on='tdate', by='horse', allow_exact_matches=False)
M5['ph_m5p'] = M5.m5s / (M5.m5c + 3.0)
Y = F.merge(P, on=['race_id', 'horse'], how='left').merge(M5[['race_id', 'horse', 'ph_m5p']], on=['race_id', 'horse'], how='left')
tr = base.values & (Y.ph_n.fillna(0).values >= 2)
out['T4_physical_x_trip'] = {}
for lab, m in [('step up 15%+', Y.dist_change > 0.14), ('similar trip', Y.dist_change.abs() <= 0.14), ('step down 15%+', Y.dist_change < -0.14)]:
    out['T4_physical_x_trip'][lab] = reg(Y[tr & m.values], ['ph_m3p', 'ph_m1p', 'ph_m5p', 'dsuit'], CT)
# a worked example of the profile for horses racing on 28 Nov would be served only after approval; here: population summary
r = F[(F.k >= 8) & F.range_min.notna()]
out['competitive_range_span_m_horses_8plus_runs'] = {'median': float(np.nanmedian(r.range_max - r.range_min)), 'p25': float(np.nanpercentile(r.range_max - r.range_min, 25)),
                                                     'p75': float(np.nanpercentile(r.range_max - r.range_min, 75))}
json.dump(out, open('batch26/out_b26_distance.json', 'w'), indent=1, default=str)
print(json.dumps({k: out[k] for k in ['T2_new_distance', 'T3_further_step_up', 'T4_physical_x_trip', 'competitive_range_span_m_horses_8plus_runs']}, indent=0)[:3500])
