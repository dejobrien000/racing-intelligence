"""Batch 8: does a candidate term add anything ON TOP OF ENGINE v2? One term at a time, v2 score held fixed as an offset.
Fit the one coefficient on development races (before 2025), judge the log-likelihood gain on 2025-26 (meeting bootstrap)."""
import json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(8)
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
U['start_no'] = g.cumcount(); U['inn_m2'] = g.dyn_nat_inn.shift(2); U['inn_m1'] = g.dyn_nat_inn.shift(1)
U['rise2'] = ((U.inn_m1 > 1) & (U.inn_m2 > 1)).astype(float); U['early'] = (U.start_no <= 6).astype(float); U['veteran'] = (U.start_no >= 25).astype(float)
U['below_peak'] = g.dyn_nat.cummax() - U.dyn_nat
U['sl_early'] = U.surprise_last * U.early; U['sl_rise2'] = U.surprise_last * U.rise2; U['sl_vet'] = U.surprise_last * U.veteran
U['old_below_peak'] = U.below_peak * (U.age_n >= 6).astype(float).where(U.age_n.notna())
U['young_below_peak'] = U.below_peak * (U.age_n <= 4).astype(float).where(U.age_n.notna())
U['starts_in_age'] = U.start_no - U.groupby('age_n').start_no.transform('median')
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
CANDS = ['sl_early', 'sl_rise2', 'sl_vet', 'old_below_peak', 'young_below_peak', 'starts_in_age', 'age_n', 'below_peak']
rows = []
for kind, FAM in [('QLD', QREL), ('NSW_VIC_ACT', NFAM2)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    bd = np.array([MAN['families'][kind]['coef_per_term_sd_dev_fit'][t] for t in allt]); v2 = off + x[['t::' + a for a in allt]].values @ bd
    dev = (x.period == 'development').values; ev = ~dev
    base = E.metrics(x, v2, pd.Series(ev, index=x.index))
    for c in CANDS:
        if c not in x or x[c].notna().sum() == 0: continue
        x = E.zcols(x, [c]); b = E.fit(x, [c], pd.Series(dev, index=x.index), tau=1e-6, offset=v2)
        e = E.eta(x, [c], b, offset=v2); m = E.metrics(x, e, pd.Series(ev, index=x.index))
        d = (m.lp - base.lp); meets = m.meeting_id.values; um = np.unique(meets); idx = {k: np.flatnonzero(meets == k) for k in um}
        bs = [d.values[np.concatenate([idx[k] for k in rng.choice(um, len(um))])].mean() for _ in range(300)]
        y26 = (m.date.dt.year == 2026).values
        rows.append({'model': kind, 'term': c, 'coef_per_sd': round(float(b[0]), 4), 'gain_per_race_2025_26': round(d.mean(), 5), 'lo95': round(np.percentile(bs, 2.5), 5), 'hi95': round(np.percentile(bs, 97.5), 5),
                     'gain_2026_only': round(d[y26].mean(), 5), 'top_pick_change_pts': round(100 * (m.hit - base.hit).mean(), 2), 'races': len(m), 'coverage_%': round(100 * x.loc[ev, c].notna().mean(), 1)})
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/incr_results.csv', index=False)
