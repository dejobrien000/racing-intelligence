"""Batch 29 item 3, Part B of preregistered/2026-11-28_b29_older_horses_heavy_defeats.md (written before this ran).
Next-run surprise (innovation vs the Engine v2.5 rating carried in) after a defeat of more than 12 lengths, established horses
(15+ held runs, aged 5+ at the next run), national states. Reference: next runs after a 6-12 L defeat.
Development = races to 31 Dec 2023 (all description); confirmation = 2024 (one pre-stated comparison per hypothesis); 2025-26 reported,
labelled as previously seen. Usage (from research/): python3 batch29/b29_heavy_defeats.py <consolidated frame> <dspec feature file>"""
import sys, json, numpy as np, pandas as pd
fin, fds = sys.argv[1:3]
F = pd.read_parquet(fin, columns=['race_id', 'race', 'horse', 'date', 'state', 'age_n', 'dyn_nat', 'dyn_nat_inn', 'margin_l', 'weight_kg', 'distance_m'])
F = F.drop_duplicates(['race_id', 'horse']).merge(pd.read_parquet(fds, columns=['race_id', 'horse', 'dspec']), on=['race_id', 'horse'], how='left')
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
g = F.groupby('horse'); F['k'] = g.cumcount(); F['r_ldays'] = (F.date - g.date.shift()).dt.days
# AMENDMENT 28 Nov 2026 (made after the first run, see the preregistration note): a second target that does not apply the 12 L cap to the
# next run itself. Common margin performance (margins to 25 L, 1.5 kg per length at 1200 m, 0.25 kg per kg carried), field-relative, minus
# the field-relative rating carried in scaled by a slope fitted on all national runs of 2023 (development).
F['perf'] = np.where(F.margin_l.notna() & F.weight_kg.notna(), -F.margin_l.clip(upper=25) * 1.5 * (1200 / F.distance_m) ** 0.8 + 0.25 * (F.weight_kg - 57), np.nan)
F['perf_r'] = F.perf - F.groupby('race_id').perf.transform('mean'); F['dn_r'] = F.dyn_nat - F.groupby('race_id').dyn_nat.transform('mean')
_d = F[(F.date.dt.year == 2023) & (F.state != 'QLD') & F.perf_r.notna() & F.dn_r.notna()]; B_SLOPE = float((_d.perf_r * _d.dn_r).sum() / (_d.dn_r ** 2).sum())
F['cerr'] = F.perf_r - B_SLOPE * F.dn_r
F['peak'] = g.dyn_nat.transform(lambda s: s.cummax())                       # peak of pre-race ratings to date (incl. this run)
F['near_peak'] = (F.peak - F.dyn_nat) <= 1.0
F['trend6'] = F.dyn_nat - g.dyn_nat.shift(6)
F['heavy'] = F.margin_l > 12; F['mid'] = F.margin_l.between(6, 12)
F['heavy_prev3'] = g.heavy.transform(lambda s: s.shift(1).rolling(3, min_periods=1).sum()).fillna(0) > 0
# runs since the last run carried in within 1 kg of the peak to date (0 = this run)
idx = np.where(F.near_peak, F.k, np.nan); F['lastnear'] = pd.Series(idx).groupby(F.horse).ffill().values; F['since_near'] = F.k - F.lastnear
# preparation stage: runs since the last gap of 60+ days (0 = first-up)
F['newprep'] = (F.r_ldays >= 60) | (F.k == 0); F['prep_id'] = F.newprep.astype(int).groupby(F.horse).cumsum(); F['prep_run'] = F.groupby(['horse', 'prep_id']).cumcount()
# previous recovery: earlier poor runs (inn <= -3) and whether the next run had inn >= 0; counted only for pairs completed before this run
F['next_inn'] = g.dyn_nat_inn.shift(-1)
F['poor'] = F.dyn_nat_inn <= -3
pair_done = F.poor & F.next_inn.notna()
F['rec_n'] = (pair_done.astype(int)).groupby(F.horse).cumsum().groupby(F.horse).shift(1).fillna(0)   # pairs whose poor run is before this run
F['rec_y'] = ((pair_done & (F.next_inn >= 0)).astype(int)).groupby(F.horse).cumsum().groupby(F.horse).shift(1).fillna(0)
# the pair (poor run j-1 -> j) completes AT run j, so a pair whose poor run is the immediately preceding run is excluded here (its next is this run)
F['recovery_rate'] = np.where(F.rec_n >= 2, F.rec_y / F.rec_n.replace(0, np.nan), np.nan)
# next run after each defeat run j
nx = F.groupby('horse').shift(-1)[['race_id', 'date', 'age_n', 'k', 'dyn_nat_inn', 'state', 'cerr']].add_prefix('n_')
X = pd.concat([F, nx], axis=1)
X = X[X.n_race_id.notna() & X.n_dyn_nat_inn.notna() & (X.n_k >= 15) & (X.n_age_n >= 5) & (X.n_state != 'QLD')]
X['per'] = np.where(X.n_date < '2024-01-01', 'development (to 2023)', np.where(X.n_date < '2025-01-01', 'confirmation 2024', '2025-26 (seen before)'))
rng = np.random.default_rng(11)
def mci(v):
    v = np.asarray(v, float); v = v[~np.isnan(v)]
    if len(v) < 20: return {'n': int(len(v)), 'mean_kg': None}
    bs = v[rng.integers(0, len(v), (1000, len(v)))].mean(1)
    return {'n': int(len(v)), 'mean_kg': round(float(v.mean()), 3), 'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
def diff(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a[~np.isnan(a)]; b = b[~np.isnan(b)]
    if len(a) < 20 or len(b) < 20: return None
    bs = a[rng.integers(0, len(a), (1000, len(a)))].mean(1) - b[rng.integers(0, len(b), (1000, len(b)))].mean(1)
    return {'diff_kg': round(float(a.mean() - b.mean()), 3), 'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
H = X[X.heavy]; R = X[X.mid]
HYP = {
 'H1 repeated (another >12 L in the previous 3) vs isolated': (H.heavy_prev3, ~H.heavy_prev3),
 'H2 falling trend (<= -0.5 kg over 6 runs) vs flat or rising': (H.trend6 <= -0.5, H.trend6 > -0.5),
 'H3 30+ held runs vs 15-29': (H.k >= 30, H.k.between(15, 29)),
 'H4 recovered < half the time vs >= half (2+ earlier pairs)': (H.recovery_rate < 0.5, H.recovery_rate >= 0.5),
 'H5 last near-peak run 8+ runs ago vs 1-3 runs ago': (H.since_near >= 8, H.since_near.between(1, 3)),
 'H6 third-up or later vs first-up after 120+ days': (H.prep_run >= 2, (H.prep_run == 0) & (H.r_ldays >= 120)),
 'H7 suitable distance (dspec > -1) vs unsuitable (dspec <= -1)': (H.dspec > -1, H.dspec <= -1)}
OUT = {'definition': __doc__.split('Usage')[0].strip(), 'slope_2023': round(B_SLOPE, 3), 'by_target': {}}
for tg, col in [('engine innovation (preregistered; caps the next run too)', 'n_dyn_nat_inn'), ('common margin target (amendment)', 'n_cerr')]:
  OUT['by_target'][tg] = {}
  for per in ['development (to 2023)', 'confirmation 2024', '2025-26 (seen before)']:
    hp = H.per == per; o = {'after >12 L defeat': mci(H[col][hp]), 'after 6-12 L defeat (reference)': mci(R[col][R.per == per])}
    for lab, (a, b) in HYP.items():
        o[lab] = {'first group': mci(H[col][hp & a]), 'second group': mci(H[col][hp & b]), 'first minus second': diff(H[col][hp & a], H[col][hp & b])}
    OUT['by_target'][tg][per] = o
OUT['by_period'] = OUT['by_target']['engine innovation (preregistered; caps the next run too)']
# pre-stated confirmation rule: a hypothesis 'confirms' if development shows the predicted sign (first group more overrated = negative diff)
# with a 95% interval excluding 0 AND 2024 shows the same sign with its 95% interval excluding 0
pred_sign = {'H1': -1, 'H2': -1, 'H3': -1, 'H4': -1, 'H5': -1, 'H6': -1, 'H7': -1}
OUT['verdicts'] = {}
for tg, BP in OUT['by_target'].items():
  ver = {}
  for lab in HYP:
    d1 = BP['development (to 2023)'][lab]['first minus second']; d2 = BP['confirmation 2024'][lab]['first minus second']
    sg = pred_sign[lab[:2]]
    ok = lambda d: d is not None and (d['ci95'][1] < 0 if sg < 0 else d['ci95'][0] > 0)
    ver[lab] = 'confirmed (development and 2024)' if ok(d1) and ok(d2) else 'development only' if ok(d1) else ('too few runs in development' if d1 is None else 'not supported in development') + ('; 2024 shows it' if ok(d2) else '')
  OUT['verdicts'][tg] = ver
json.dump(OUT, open('batch29/out_b29_heavy_defeats.json', 'w'), indent=1)
print(json.dumps(OUT['verdicts'], indent=1))
