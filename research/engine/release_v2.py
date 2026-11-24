"""Release engine v2 (versioned). Uses the exact term definitions from engine/v2.py (executed up to its run() function).
  Qld v2  = Qld v1 operational score (fixed) + horse records + jockey & trainer   (form-change family dropped: it HURT on 2025-26)
  NSW/Vic/ACT v2 = nat_v2 operational score (fixed) + jockey & trainer + age & sex + form changes & head-to-head + interactions
  chosen on discovery data only.
Coefficients of the new terms are re-estimated on ALL races to 23 Nov 2026 (development + evaluation) with the penalty chosen
on the development inner split; scaling constants are the development ones (unchanged). The evidence for the release is
the identical-race comparison (dev fit -> 2025-26) and the rolling-origin backtest in engine/out/v2_*.csv.
Also builds selection-strength calibration v2 (from dev-fit v2 predictions on 2025-26, out-of-sample) and the kg-equivalent
scale. Writes benchmarks/engine_v2/manifest.json (+ calibration races csv). v1 stays frozen and is still scored daily."""
import json, os, hashlib, numpy as np, pandas as pd, statsmodels.api as sm, hier_tools as H
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
NREL = NFAM2
os.makedirs('benchmarks/engine_v2', exist_ok=True); rng = np.random.default_rng(7); OUT = {'released_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'families': {}}
def scaling(x, terms):
    """development scaling constants: base feature race-centred sd, and each term's race-centred sd (as build_terms made them)."""
    dev = x.period == 'development'; base = {}
    for c in [c[:-2] for c in x.columns if c.endswith('_z') and c[:-2] in x.columns]:
        v = x[c].astype(float); cen = v - v.groupby(x.race_id).transform('mean'); s = cen[dev].std(); base[c] = float(s) if s == s and s else 1.0
    tsd = {}
    for n in terms:
        # rebuild the unscaled term exactly as build_terms did, to recover its sd
        if n == 'ability x field strength': t = x.dyn_nat_z * x.fd_z
        elif n.endswith(' squared'): t = x[n.split(' ')[0] + '_z'] ** 2
        elif ' x ' in n:
            t = 1.0
            for p in n.split(' x '): t = t * (x[p + '_z'] if p + '_z' in x else (x.yr if p == 'year' else x[p]))
        else: t = x[n + '_z'] if n + '_z' in x else x[n]
        t = pd.Series(np.nan_to_num(np.asarray(t, dtype=float)), index=x.index); t = t - t.groupby(x.race_id).transform('mean'); tsd[n] = float(t[dev].std() or 1.0)
    return base, tsd, {'field_dyn_mean': float(x.field_dyn.mean()), 'field_dyn_sd': float(x.field_dyn.std())}
for kind, FAM in [('QLD', QREL), ('NSW_VIC_ACT', NREL)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U)
    allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    dev, ev = x.period == 'development', x.period == 'evaluation'; allr = dev | ev
    tau = choose_tau(x, allt, off)
    b_dev = fitd(x, allt, dev, off, tau); b_all = fitd(x, allt, allr, off, tau)
    base, tsd, ctx = scaling(x, allt)
    # kg-equivalent scale: development within-race slope of the v2 score on the opposition-aware rating
    e_dev = off + x[['t::' + t for t in allt]].values @ b_dev; d = x[dev].assign(e=e_dev[dev.values])
    a_ = d.e - d.groupby('race_id').e.transform('mean'); r_ = d.dyn_nat - d.groupby('race_id').dyn_nat.transform('mean'); ok = a_.notna() & r_.notna()
    slope = float((a_[ok] * r_[ok]).sum() / (r_[ok] ** 2).sum())
    # calibration v2 from out-of-sample (dev-fit) predictions on 2025-26
    t = x.loc[ev, ['race_id', 'meeting_id', 'win']].copy(); t['e'] = e_dev = (off + x[['t::' + t_ for t_ in allt]].values @ b_dev)[ev.values]
    mx = t.groupby('race_id').e.transform('max'); t['p'] = np.exp(t.e - mx); t['p'] /= t.groupby('race_id').p.transform('sum'); t = t.sort_values(['race_id', 'e'], ascending=[True, False])
    top = t.groupby('race_id').head(1).set_index('race_id'); top['field'] = t.groupby('race_id').size()
    D = pd.DataFrame({'p_top': top.p, 'top_won': top.win, 'field': top.field, 'meeting_id': top.meeting_id})
    lg = lambda p: np.log(p / (1 - p)); des = lambda d_: sm.add_constant(np.column_stack([lg(d_.p_top.clip(1e-4, 1 - 1e-4)), np.log(d_.field)]), has_constant='add')
    m = sm.Logit(D.top_won.astype(float), des(D)).fit(disp=0); B = []
    meets = D.meeting_id.unique(); idx = {k: np.where(D.meeting_id.values == k)[0] for k in meets}
    for _ in range(300):
        pick = np.concatenate([idx[k] for k in rng.choice(meets, len(meets))]); dd = D.iloc[pick]
        try: B.append([float(v) for v in sm.Logit(dd.top_won.astype(float), des(dd)).fit(disp=0).params.values])
        except Exception: pass
    cal = m.predict(des(D)); terc = [float(v) for v in np.percentile(cal, [100 / 3, 200 / 3])]
    D.assign(cal=cal).to_csv(f'benchmarks/engine_v2/calibration_races_{kind}.csv', index=True)
    OUT['families'][kind] = {'v1_offset': 'benchmarks/candidates_b4_national (combined_v1 + national rating)' if kind == 'QLD' else 'benchmarks/candidates_national_common nat_v2',
                             'term_families': FAM, 'penalty_tau': tau, 'coef_per_term_sd_all_races': dict(zip(allt, map(float, b_all))), 'coef_per_term_sd_dev_fit': dict(zip(allt, map(float, b_dev))),
                             'base_feature_dev_sd': base, 'term_dev_sd': tsd, 'context': ctx, 'score_per_kg_total': slope,
                             'calibration': {'coef_const_logit_logfield': [float(v) for v in m.params.values], 'bootstrap_coefs': B, 'strength_terciles_2025_26': terc,
                                             'races': len(D), 'top_pick_win_rate': float(D.top_won.mean())}}
    print(kind, 'terms', len(allt), 'tau', tau, 'score per kg', round(slope, 4), 'calibration', np.round(m.params.values, 3), 'terciles', np.round(terc, 3), 'top pick win', round(D.top_won.mean(), 4))
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
OUT['code_sha256_16'] = {p: h(p) for p in ['engine/lab.py', 'engine/evaltools.py', 'engine/v2.py', 'engine/release_v2.py', 'dyn_rating.py', 'dyn_rating_innov.py']}
OUT['data_sha256_16'] = {'engine/frames/national.parquet': h('engine/frames/national.parquet'), 'features.parquet': h('features.parquet'), 'national_runs.parquet': h('national_runs.parquet')}
OUT['evidence'] = ['engine/out/v2_qld.csv', 'engine/out/v2_nat.csv', 'engine/out/v2_qld_rolling.csv', 'engine/out/v2_nat_rolling.csv', 'engine/out/check_people_lag (28-day lag keeps the effect)']
OUT['rule'] = 'v1 remains frozen and is scored alongside; v2 is the operational ranking from 25 Nov 2026; any v3 must beat v2 on identical races'
os.makedirs('benchmarks/engine_v2', exist_ok=True); json.dump(OUT, open('benchmarks/engine_v2/manifest.json', 'w'), indent=1)
