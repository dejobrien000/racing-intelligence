"""Batch 29 item 4: matched historical performance tables for the BUILT engines (release-chain dev-fit chances on races not used to fit).
National (NSW, Vic, ACT, SA, WA, Tas; 2025-26): Engine v2.3, Engine v2.5, combined candidate ('v2.6') on identical races and runners.
Queensland (2025-26): Engine v2.1.3 (production structure, v3 rating) and Qld common framework config 5, on the races both scored.
Metrics: average log-likelihood of the winner per race; top-ranked runner won; winner ranked in top 3; probability calibration (expected
calibration error over 10 equal-count bins, percentage points); performance-ranking correlation (Spearman, model order vs finishing
order, averaged over races); individual performance prediction error (mean squared error, kg^2, of a field-relative margin-based
performance figure predicted from the engine's field-relative score, slope fitted on 2025 races and judged on 2026 races).
Uncertainty: 95% bootstrap intervals over races for every difference vs the baseline engine. Historical research only (not live).
A relative gain in statistical accuracy is NOT the same relative gain in winners. Usage (from research/): python3 batch29/b29_perf_tables.py"""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(29)
def perf_fig(D):
    return np.where(D.margin_l.notna() & D.weight_kg.notna(), -D.margin_l.clip(upper=25) * 1.5 * (1200 / D.distance_m) ** 0.8 + 0.25 * (D.weight_kg - 57), np.nan)
def per_race(O):
    """O: runners with race_id, p, e, win, finish_pos, perf_r, date. Returns per-race table."""
    O = O.copy(); O['rk'] = O.groupby('race_id').p.rank(ascending=False, method='first')
    W = O[O.win == 1].groupby('race_id').agg(lp=('p', lambda s: float(np.log(s).mean())), wrk=('rk', 'min'))
    R = O.groupby('race_id').agg(field=('p', 'size'), date=('date', 'first'))
    def sp(g):
        g = g.dropna(subset=['finish_pos'])
        return g.rk.corr(g.finish_pos, method='spearman') if len(g) >= 3 else np.nan
    R['spearman'] = O.groupby('race_id')[['rk', 'finish_pos']].apply(sp)
    R = R.join(W); R['top1'] = (R.wrk == 1).astype(float); R['top3'] = (R.wrk <= 3).astype(float)
    return R
def ece(O):
    b = pd.qcut(O.p.rank(method='first'), 10, labels=False); g = O.groupby(b).agg(p=('p', 'mean'), w=('win', 'mean'), n=('p', 'size'))
    return float((g.n * (g.p - g.w).abs()).sum() / g.n.sum() * 100)
def ind_err(O):
    O = O.dropna(subset=['perf_r']).copy(); O['e_r'] = O.e - O.groupby('race_id').e.transform('mean')
    f = O[O.date.dt.year == 2025]; t = O[O.date.dt.year == 2026]
    b = float((f.perf_r * f.e_r).sum() / (f.e_r ** 2).sum()); t = t.assign(se=(t.perf_r - b * t.e_r) ** 2)
    return t.groupby('race_id').se.mean(), b
def boot(d):
    d = np.asarray(d, float); d = d[~np.isnan(d)]; bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1)
    return [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]
def table(models, base):
    """models: {label: runner frame}. Same races required."""
    races = set.intersection(*[set(O.race_id) for O in models.values()])
    out = {}; PR = {}; IE = {}
    for lab, O in models.items():
        O = O[O.race_id.isin(races)]; R = per_race(O); PR[lab] = R; ie, b = ind_err(O); IE[lab] = ie
        out[lab] = {'races': int(len(R)), 'runners': int(len(O)), 'mean_field': round(float(R.field.mean()), 2),
                    'avg_loglik_per_race': round(float(R.lp.mean()), 5), 'top_ranked_won_pct': round(float(R.top1.mean() * 100), 2),
                    'winner_in_top3_pct': round(float(R.top3.mean() * 100), 2), 'calibration_error_pts': round(ece(O), 3),
                    'rank_correlation_spearman': round(float(R.spearman.mean()), 4) if R.spearman.notna().any() else None,
                    'individual_error_kg2_2026': round(float(ie.mean()), 3), 'races_2026_for_error': int(ie.notna().sum()), 'error_slope_kg_per_score_2025': round(b, 3)}
    B = PR[base]
    for lab in models:
        if lab == base: continue
        R = PR[lab].reindex(B.index); o = out[lab]
        d_lp = R.lp - B.lp; d1 = (R.top1 - B.top1) * 100; d3 = (R.top3 - B.top3) * 100; dsp = (R.spearman - B.spearman); die = (IE[lab] - IE[base]).dropna()
        o['vs_' + base] = {'loglik_gain_per_race': round(float(d_lp.mean()), 5), 'loglik_ci95': boot(d_lp),
                           'top_ranked_won_pts': round(float(d1.mean()), 2), 'top_ranked_won_ci95': [round(x, 2) for x in boot(d1)],
                           'winner_in_top3_pts': round(float(d3.mean()), 2), 'winner_in_top3_ci95': [round(x, 2) for x in boot(d3)],
                           'rank_correlation_gain': round(float(dsp.mean()), 4), 'rank_correlation_ci95': [round(x, 4) for x in boot(dsp)],
                           'individual_error_change_kg2': round(float(die.mean()), 3), 'individual_error_ci95': [round(x, 3) for x in boot(die)],
                           'individual_error_change_pct': round(float(die.mean() / IE[base].reindex(die.index).mean() * 100), 2),
                           'top_ranked_won_relative_pct': round(float(d1.mean() / (B.top1.mean() * 100) * 100), 2)}
    return out
# ---------------- national ----------------
FR = pd.read_parquet('engine/frames/national_consolidated.parquet', columns=['race_id', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m'])
FR = FR.drop_duplicates(['race_id', 'horse']); FR['date'] = pd.to_datetime(FR.date); FR['perf'] = perf_fig(FR); FR['perf_r'] = FR.perf - FR.groupby('race_id').perf.transform('mean')
V6 = pd.read_parquet('/tmp/cmb/research/out_combined/oos.parquet')                      # has horse; row order identical to the other two
V5 = pd.read_parquet('/tmp/cc/out/v22_oos.parquet'); V3 = pd.read_parquet('/tmp/c2_v22_oos.parquet')
assert (V5.race_id.values == V6.race_id.values).all() and (V5.win.values == V6.win.values).all() and (V3.race_id.values == V6.race_id.values).all() and (V3.win.values == V6.win.values).all()
for V in (V5, V3): V['horse'] = V6.horse.values
NAT = {}
for lab, V in [('Engine v2.3', V3), ('Engine v2.5', V5), ('Combined candidate (v2.6)', V6)]:
    NAT[lab] = V[['race_id', 'horse', 'p', 'e', 'win']].merge(FR, on=['race_id', 'horse'], how='left')
OUT = {'definition': __doc__.split('Usage')[0].strip(), 'national_2025_26': table(NAT, 'Engine v2.3')}
OUT['national_2025_26']['Engine v2.5']['vs_Engine_v2.3_note'] = 'v2.5 = the consolidated rating, released 29 Nov 2026'
# v2.6 also against v2.5
t = table({k: NAT[k] for k in ['Engine v2.5', 'Combined candidate (v2.6)']}, 'Engine v2.5'); OUT['national_2025_26']['Combined candidate (v2.6)']['vs_Engine v2.5'] = t['Combined candidate (v2.6)']['vs_Engine v2.5']
# ---------------- Queensland ----------------
Q3 = pd.read_parquet('engine/frames/national_v3.parquet', columns=['race_id', 'q_race_id', 'horse', 'state', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'win'])
Q3 = Q3[Q3.state == 'QLD'].drop_duplicates(['race_id', 'horse'])
QP = pd.read_parquet('/tmp/qld213_oos.parquet'); QC = pd.read_parquet('/tmp/q5/v22_oos_qcf5.parquet')
def attach(O, key, F):
    """attach horses by matching each race's runner order to the frame's order (checked by the win sequence)"""
    F = F[F[key].isin(set(O.race_id))]; F = F.set_index(key)
    out = []; bad = 0
    for rid, g in O.groupby('race_id', sort=False):
        f = F.loc[[rid]] if rid in F.index else None
        if f is None or len(f) != len(g) or not (f.win.values == g.win.values).all(): bad += 1; continue
        out.append(g.assign(horse=f.horse.values, finish_pos=f.finish_pos.values, margin_l=f.margin_l.values, weight_kg=f.weight_kg.values, distance_m=f.distance_m.values, date=pd.to_datetime(f.date.values)))
    return pd.concat(out), bad
FC = pd.read_parquet('engine/frames/national_consolidated.parquet', columns=['race_id', 'q_race_id', 'state']); FC = FC[FC.state == 'QLD'].drop_duplicates('race_id')
QC['race_id'] = QC.race_id.map(FC.set_index('race_id').q_race_id)
common = set(QP.race_id) & set(QC.race_id)
QPr = QP[QP.race_id.isin(common)].assign(finish_pos=np.nan, perf_r=np.nan, date=pd.to_datetime(QP.race_id.str[:8], format='%Y%m%d'))
QCr = QC[QC.race_id.isin(common)].assign(finish_pos=np.nan, perf_r=np.nan, date=pd.to_datetime(QC.race_id.str[:8], format='%Y%m%d'))
def race_only(models, base):
    out = {}; PR = {}
    for lab, O in models.items():
        R = per_race(O.assign(e=O.e)); PR[lab] = R
        out[lab] = {'races': int(len(R)), 'runners': int(len(O)), 'mean_field': round(float(R.field.mean()), 2), 'avg_loglik_per_race': round(float(R.lp.mean()), 5),
                    'top_ranked_won_pct': round(float(R.top1.mean() * 100), 2), 'winner_in_top3_pct': round(float(R.top3.mean() * 100), 2), 'calibration_error_pts': round(ece(O), 3),
                    'rank_correlation_spearman': 'not available: runner order is not recoverable from the saved v2.1.3 file', 'individual_error_kg2_2026': 'not available (same reason)'}
    B = PR[base]
    for lab in models:
        if lab == base: continue
        R = PR[lab].reindex(B.index); d_lp = R.lp - B.lp; d1 = (R.top1 - B.top1) * 100; d3 = (R.top3 - B.top3) * 100
        out[lab]['vs_' + base] = {'loglik_gain_per_race': round(float(d_lp.mean()), 5), 'loglik_ci95': boot(d_lp), 'top_ranked_won_pts': round(float(d1.mean()), 2),
                                  'top_ranked_won_ci95': [round(x, 2) for x in boot(d1)], 'winner_in_top3_pts': round(float(d3.mean()), 2), 'winner_in_top3_ci95': [round(x, 2) for x in boot(d3)],
                                  'calibration_error_change_pts': round(out[lab]['calibration_error_pts'] - out[base]['calibration_error_pts'], 3)}
    return out
OUT['queensland_2025_26'] = race_only({'Qld Engine v2.1.3': QPr, 'Qld config 5': QCr}, 'Qld Engine v2.1.3')
OUT['notes'] = ['Historical research on past races (2025-26), dev-fit chances; not live performance. 2025-26 has been studied repeatedly.',
                'A gain in log-likelihood or calibration is a gain in statistical accuracy; it does not translate one-for-one into more winners.',
                'Queensland config 5 and the combined candidate are candidates, not production. The Queensland barrier candidate is not built yet.']
json.dump(OUT, open('batch29/out_b29_perf_tables.json', 'w'), indent=1); print(json.dumps(OUT, indent=1)[:7000])
