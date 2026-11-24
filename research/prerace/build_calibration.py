"""Selection-strength calibration layer v1 (built 24 Nov 2026, before any race from 25 Nov).
For each operational frozen candidate, take every 2025-01-01..2026-11-23 race it scored (coefficients were fixed on
earlier races, so these are out-of-sample), and record the model's top chance and whether the top pick won.
Calibration = logistic regression of 'top pick won' on logit(top chance) and log(field size), per jurisdiction family.
Uncertainty = 400 meeting-bootstrap refits; the daily report shows the 80% band.
'No clear selection' rule (data-driven, not a chosen cut): the race's calibrated top-pick chance, at the LOWER end of its
80% band, is no better than picking a runner at random (1 / field).
Writes benchmarks/selection_strength_v1/manifest.json + races.csv. Never refitted from daily results."""
import json, os, hashlib, numpy as np, pandas as pd, statsmodels.api as sm
rng = np.random.default_rng(7)
def race_table(x, lp_col, fam):
    e = np.exp(x[lp_col] - x.groupby('race_id')[lp_col].transform('max')); x = x.assign(p=e / e.groupby(x.race_id).transform('sum'))
    x = x.sort_values(['race_id', lp_col], ascending=[True, False]); t = x.groupby('race_id').head(1)
    f = x.groupby('race_id').size().rename('field'); sec = x.groupby('race_id').p.apply(lambda s: s.iloc[1] if len(s) > 1 else 0).rename('p_second')
    return t[['race_id', 'meeting_id', 'p', 'win']].rename(columns={'p': 'p_top', 'win': 'top_won'}).merge(f, on='race_id').merge(sec, on='race_id').assign(family=fam)
# ---- Queensland: 'combined_v1 + national dynamic rating' (the Qld operational candidate) ----
from clogit_tools import eligible, prep
mq = json.load(open('benchmarks/candidates_b4_national/manifest.json')); CQ = mq['coefficients_per_dev_sd']
X = pd.read_parquet('features.parquet').merge(pd.read_parquet('dyn_nat_qld.parquet'), on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna()}.items(): X[k] = v.astype(float)
xq = prep(eligible(X), sorted(CQ)); xq['lp'] = sum(CQ[c] * xq[c + '_z'] for c in CQ)
TQ = race_table(xq[xq.period == 'evaluation'], 'lp', 'QLD')
def kg_slope(x, lp, dyn):
    d = x[x.period == 'development']; a = d[lp] - d.groupby('race_id')[lp].transform('mean'); b = d[dyn] - d.groupby('race_id')[dyn].transform('mean'); ok = a.notna() & b.notna()
    return float((a[ok] * b[ok]).sum() / (b[ok] ** 2).sum())   # score units per kg of rating, all correlated factors included
SLOPE = {'QLD': kg_slope(xq, 'lp', 'dyn_nat')}
# ---- NSW / Vic / ACT: nat_v2 (+ horse records) ----
src = open('inv30_horse_suitability.py').read().split("best = None")[0]; exec(src); add_records(1)
mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
N = U[(U.state != 'QLD') & (U.field >= 6)].copy(); N['n_win'] = N.groupby('race_id').win.transform('sum'); N = N[N.n_win == 1]
for c in C2: N[c + '_z'] = ((N[c].astype(float) - N.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0)
N['lp'] = sum(C2[c] * N[c + '_z'] for c in C2)
TN = race_table(N[N.period == 'evaluation'], 'lp', 'NSW_VIC_ACT'); SLOPE['NSW_VIC_ACT'] = kg_slope(N, 'lp', 'dyn_nat')
T = pd.concat([TQ, TN], ignore_index=True)
lg = lambda p: np.log(p / (1 - p))
def design(d): return sm.add_constant(np.column_stack([lg(d.p_top.clip(1e-4, 1 - 1e-4)), np.log(d.field)]), has_constant='add')
out = {'built_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'data_window': '2025-01-01 to 2026-11-23 (out-of-sample for the frozen coefficients)', 'families': {}}
for fam, d in T.groupby('family'):
    m = sm.Logit(d.top_won.astype(float), design(d)).fit(disp=0); b = m.params.values
    meets = d.meeting_id.unique(); idx = {k: np.where(d.meeting_id.values == k)[0] for k in meets}; B = []
    for _ in range(400):
        pick = np.concatenate([idx[k] for k in rng.choice(meets, len(meets))]); dd = d.iloc[pick]
        try: B.append(sm.Logit(dd.top_won.astype(float), design(dd)).fit(disp=0).params.values)
        except Exception: pass
    cal = d.assign(cal=m.predict(design(d))); cal['bin'] = pd.cut(cal.p_top, [0, .15, .2, .25, .3, .4, 1])
    tab = cal.groupby('bin', observed=True).agg(races=('top_won', 'size'), model_top_chance=('p_top', 'mean'), calibrated=('cal', 'mean'), actual_win_rate=('top_won', 'mean')).round(3)
    terc = [float(v) for v in np.percentile(cal.cal, [100 / 3, 200 / 3])]
    out['families'][fam] = {'score_per_kg_total': SLOPE[fam], 'strength_terciles_2025_26': terc, 'races': len(d), 'top_pick_win_rate': round(float(d.top_won.mean()), 4), 'coef_const_logit_logfield': [float(v) for v in b],
                            'bootstrap_coefs': [[float(v) for v in bb] for bb in B], 'field_term_z': round(float(np.asarray(m.tvalues)[2]), 2),
                            'calibration_table': tab.reset_index().astype({'bin': str}).to_dict('records')}
    print(fam, 'score per kg', round(SLOPE[fam], 4), 'terciles', np.round(np.percentile(cal.cal, [100 / 3, 200 / 3]), 3), len(d), 'races | coefficients', np.round(b, 3), '| field term z', round(float(np.asarray(m.tvalues)[2]), 2)); print(tab.to_string())
os.makedirs('benchmarks/selection_strength_v1', exist_ok=True)
T.to_csv('benchmarks/selection_strength_v1/races.csv', index=False)
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
out['code_sha256_16'] = {p: h(p) for p in ['prerace/build_calibration.py', 'inv30_horse_suitability.py']}
out['strength_labels'] = 'descriptive tiers relative to this family\'s own 2025-26 races: strong = top third of calibrated strength, moderate = middle third, weak (no clear selection) = bottom third; insufficient information = top pick or more than half the field has no prior form'
out['final_rating_kg'] = 'race-relative model score / score_per_kg_total (development-period within-race slope of score on the opposition-aware rating, so 1 kg of final rating = 1 kg of rating difference on average)'
out['prospective_rule'] = 'fixed; evaluated on races from 2026-11-25; never refitted from individual results'
json.dump(out, open('benchmarks/selection_strength_v1/manifest.json', 'w'), indent=1)
