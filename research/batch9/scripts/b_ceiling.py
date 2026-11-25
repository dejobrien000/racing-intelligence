"""Batch 9 study B: proven ceiling vs current form. Which circumstances separate a temporary dip from a decline?
Each term added alone on top of the full Engine v2 score (fixed offset); fit before 2025, judged on 2025-26."""
import json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(9)
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
U['start_no'] = g.cumcount(); U['peak'] = g.dyn_nat.cummax(); U['below_peak'] = U.peak - U.dyn_nat
newpk = (U.dyn_nat >= U.peak - 1e-9) & (U.start_no > 0)           # rating at a new high: set by the PREVIOUS run
U['prev_dist'] = g.distance_m.shift(); U['prev_gband'] = g.gband.shift(); U['prev_date'] = g.date.shift()
for c in ['prev_dist', 'prev_gband', 'start_no', 'prev_date']:
    U['pk_' + c] = U[c].where(newpk); U['pk_' + c] = U.groupby('horse')['pk_' + c].ffill()
U['runs_since_peak'] = U.start_no - U.pk_start_no; U['days_since_peak'] = (U.date - U.pk_prev_date).dt.days
U['first_up'] = ((U.date - U.prev_date).dt.days > 60).astype(float)
U['trip_back'] = (((U.distance_m - U.pk_prev_dist).abs() <= 100) & ((U.prev_dist - U.pk_prev_dist).abs() >= 200)).astype(float)
U['going_back'] = ((U.gband == U.pk_prev_gband) & (U.prev_gband != U.pk_prev_gband)).astype(float)
U['established'] = ((U.start_no >= 15)).astype(float)
bp = U.below_peak
T = {'below_peak': bp,
     'below_peak x recent dip (1-2 runs since peak)': bp * U.runs_since_peak.between(1, 2),
     'below_peak x long decline (6+ runs since peak)': bp * (U.runs_since_peak >= 6),
     'below_peak x 7yo+': bp * (U.age_n >= 7),
     'below_peak x first-up today': bp * U.first_up,
     'below_peak x back to peak trip': bp * U.trip_back,
     'below_peak x back to peak going': bp * U.going_back,
     'below_peak x peak within 120 days': bp * (U.days_since_peak <= 120),
     'recent form x established horse': U.f_avgfp3 * U.established,
     'last finish x established horse': U.f_lastfp * U.established}
names = {}
for i, (k, v) in enumerate(T.items()): U[f'cand{i}'] = v.astype(float).where(bp.notna()); names[f'cand{i}'] = k
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
rows = []
for kind, FAM in [('NSW_VIC_ACT', NFAM2), ('QLD', QREL)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    bd = np.array([MAN['families'][kind]['coef_per_term_sd_dev_fit'][t] for t in allt]); v2 = off + x[['t::' + a for a in allt]].values @ bd
    dev = (x.period == 'development').values; ev = ~dev; base = E.metrics(x, v2, pd.Series(ev, index=x.index))
    for c, nm in names.items():
        if c not in x or x[c].notna().sum() == 0: continue
        x = E.zcols(x, [c]); b = E.fit(x, [c], pd.Series(dev, index=x.index), tau=1e-6, offset=v2)
        m = E.metrics(x, E.eta(x, [c], b, offset=v2), pd.Series(ev, index=x.index)); d = m.lp - base.lp
        meets = m.meeting_id.values; um = np.unique(meets); idx = {k: np.flatnonzero(meets == k) for k in um}
        bs = [d.values[np.concatenate([idx[k] for k in rng.choice(um, len(um))])].mean() for _ in range(300)]
        y26 = (m.date.dt.year == 2026).values
        rows.append({'model': kind, 'term': nm, 'coef_per_sd': round(float(b[0]), 4), 'gain_2025_26': round(d.mean(), 5), 'lo95': round(np.percentile(bs, 2.5), 5), 'hi95': round(np.percentile(bs, 97.5), 5), 'gain_2026': round(d[y26].mean(), 5),
                     'share_of_runners_nonzero_%': round(100 * (x.loc[ev, c].fillna(0) != 0).mean(), 1)})
        print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/b_ceiling.csv', index=False)
