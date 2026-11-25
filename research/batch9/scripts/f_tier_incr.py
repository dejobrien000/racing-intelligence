"""Batch 9 F: class-of-track move (country/provincial/metro) since last start, as a term on top of Engine v2."""
import json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(12)
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
lvl = U.tier.map({'country': 0, 'provincial': 1, 'metro': 2}).astype(float)
U['tier_step'] = lvl - lvl.groupby(U.horse).shift()              # +1/+2 = moving up, -1/-2 = moving down
U['tier_up'] = (U.tier_step > 0).astype(float).where(U.tier_step.notna()); U['tier_down'] = (U.tier_step < 0).astype(float).where(U.tier_step.notna())
U['fq'] = U.groupby('race_id').dyn_nat.transform('mean'); U['opp_step'] = U.fq - U.groupby('horse').fq.shift()
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
rows = []
for kind, FAM in [('NSW_VIC_ACT', NFAM2), ('QLD', QREL)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    bd = np.array([MAN['families'][kind]['coef_per_term_sd_dev_fit'][t] for t in allt]); v2 = off + x[['t::' + a for a in allt]].values @ bd
    dev = (x.period == 'development').values; ev = ~dev; base = E.metrics(x, v2, pd.Series(ev, index=x.index))
    for c in ['tier_step', 'tier_up', 'tier_down', 'opp_step']:
        x = E.zcols(x, [c]); b = E.fit(x, [c], pd.Series(dev, index=x.index), tau=1e-6, offset=v2)
        m = E.metrics(x, E.eta(x, [c], b, offset=v2), pd.Series(ev, index=x.index)); d = m.lp - base.lp
        meets = m.meeting_id.values; um = np.unique(meets); idx = {k: np.flatnonzero(meets == k) for k in um}
        bs = [d.values[np.concatenate([idx[k] for k in rng.choice(um, len(um))])].mean() for _ in range(300)]
        rows.append({'model': kind, 'term': c, 'coef_per_sd': round(float(b[0]), 4), 'gain_2025_26': round(d.mean(), 5), 'lo95': round(np.percentile(bs, 2.5), 5), 'hi95': round(np.percentile(bs, 97.5), 5),
                     'gain_2026': round(d[(m.date.dt.year == 2026).values].mean(), 5), 'top_pick_pts': round(100 * (m.hit - base.hit).mean(), 2)}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/f_tier_incr.csv', index=False)
