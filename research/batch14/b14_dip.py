"""Batch 14 follow-up of the s2 finding: at the same average last-600 speed, a run whose WEAKEST 200 m section was weaker
(an uneven last 600) is followed by a better next run than the rating expects. What kind of unevenness is it?
dip   = mean of the three last-600 sections minus the weakest (both vs the field median); 0 = perfectly even
where = which section was weakest: 600-400, 400-200 or the final 200
pos_lost = places lost during the weakest section (measured positions at its start and end); recovered = the next section above the field
Same outcome (next-run surprise, kg), controls and bootstrap as b14_finish.py. Also: is unevenness a horse trait (split-half)?"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, os, sys
sys.argv = ['x']; os.environ['LEADERS_ONLY'] = '1'
src = open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0]; exec(src)   # load() and Q, S
OUT = {}
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct'
def prep(d):
    d = d.dropna(subset=['early_pos', 'def800c']).copy()
    V3 = d[['v600r', 'v400r', 'v200r']].values; w = np.argmin(V3, axis=1)
    d['where'] = np.array(['600-400', '400-200', 'final 200'])[w]; d['dip'] = d.L600_avg - d.L600_min
    ps = np.c_[d.pos600, d.pos400, d.pos200, d.fp]; d['pos_lost'] = ps[np.arange(len(d)), w + 1] - ps[np.arange(len(d)), w]
    nxt = np.c_[d.v400r, d.v200r, np.full(len(d), np.nan)]; d['recovered'] = (nxt[np.arange(len(d)), w] > 0).astype(int)
    d['back'] = (d.early_pos > 0.5).astype(int)
    return d
def est(d, form, terms):
    m = smf.ols(form, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    return {t: (round(m.params[t], 3), round(m.conf_int().loc[t, 0], 3), round(m.conf_int().loc[t, 1], 3)) for t in terms if t in m.params}
for lab, d in [('QLD 2022-24', Q[Q.yr <= 2024]), ('QLD 2025-26', Q[Q.yr >= 2025]), ('SA 2024-26', S)]:
    d = prep(d); sd = d.dip.std(); d['dip_z'] = d.dip / sd; d['avg_z'] = d.L600_avg / d.L600_avg.std()
    base = 'inn_n1 ~ avg_z + ' + CTRL
    r = {'runs': len(d), 'dip_sd_ms': round(sd, 3)}
    r['dip (all)'] = est(d, base + ' + dip_z', ['dip_z'])
    r['dip by weakest section'] = est(d, base + ' + dip_z:C(where)', [f'dip_z:C(where)[{w}]' for w in ['600-400', '400-200', 'final 200']])
    r['dip x recovered'] = est(d, base + ' + dip_z + dip_z:recovered', ['dip_z', 'dip_z:recovered'])
    r['dip x lost places'] = est(d, base + ' + dip_z + dip_z:I(pos_lost.clip(0, 4))', ['dip_z', 'dip_z:I(pos_lost.clip(0, 4))'])
    r['dip x back early'] = est(d, base + ' + dip_z + dip_z:back', ['dip_z', 'dip_z:back'])
    # the same, relative to the horse's own previous runs (within-horse change): prior own mean of dip, shrunk with 3 runs' weight
    d = d.sort_values(['horse', 'meeting_date']); cnt = d.groupby('horse').cumcount(); sm = d.groupby('horse').dip.cumsum() - d.dip
    d['dip_own_z'] = (d.dip - sm / (cnt + 3.0) - 0.0) / sd; d['prior_dip_z'] = (sm / (cnt + 3.0)) / sd
    r['own-norm change'] = est(d[cnt >= 3], base + ' + dip_own_z + prior_dip_z', ['dip_own_z', 'prior_dip_z'])
    # descriptive: share of each weakest-section type and next-run surprise vs fitted (top decile of dip vs bottom half)
    q = d.dip.quantile([0.5, 0.9]).values
    r['share weakest section %'] = (100 * d['where'].value_counts(normalize=True)).round(1).to_dict()
    r['top-decile dip: places lost in that section (mean)'] = round(d[d.dip >= q[1]].pos_lost.mean(), 2)
    r['top-decile dip: recovered next section %'] = round(100 * d[(d.dip >= q[1]) & (d['where'] != 'final 200')].recovered.mean(), 1)
    # horse trait? split-half correlation of mean dip (odd vs even runs, horses with 8+ runs)
    h = d.groupby('horse').filter(lambda g: len(g) >= 8).copy(); h['half'] = h.groupby('horse').cumcount() % 2
    p = h.groupby(['horse', 'half']).dip.mean().unstack().dropna(); r['trait split-half r (8+ runs)'] = (round(p[0].corr(p[1]), 3), len(p))
    OUT[lab] = r; print(lab, json.dumps(r, default=str), flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_dip.json', 'w'), indent=1, default=str)
