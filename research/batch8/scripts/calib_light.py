# Calibration audit: engine v2 out-of-sample (2025-26) predictions, by career starts. Read-only.
import json, numpy as np, pandas as pd, statsmodels.api as sm
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json'))
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
lg = lambda p: np.log(p / (1 - p)); des = lambda d: sm.add_constant(np.column_stack([lg(d.p.clip(1e-4, 1 - 1e-4)), np.log(d.field)]), has_constant='add')
rows = []
for kind, FAM in [('QLD', QREL), ('NSW_VIC_ACT', NFAM2)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    bd = np.array([MAN['families'][kind]['coef_per_term_sd_dev_fit'][t] for t in allt]); ev = x.period == 'evaluation'
    t = x.loc[ev, ['race_id', 'meeting_id', 'win', 'date', 'horse']].copy(); t['e'] = (off + x[['t::' + a for a in allt]].values @ bd)[ev.values]
    t['starts'] = np.round(np.expm1(x.loc[ev, 'f_lstarts'])) if x['f_lstarts'].max() < 10 else x.loc[ev, 'f_lstarts']
    t['figs'] = x.loc[ev, 'fig_n'] if 'fig_n' in x else np.nan
    mx = t.groupby('race_id').e.transform('max'); t['p'] = np.exp(t.e - mx); t['p'] /= t.groupby('race_id').p.transform('sum'); t['field'] = t.groupby('race_id').win.transform('size')
    # honest check: calibration fitted on 2025, judged on 2026
    a, b = t[t.date.dt.year == 2025], t[t.date.dt.year == 2026]
    m = sm.Logit(a.win.astype(float), des(a)).fit(disp=0); t.loc[b.index, 'cal26'] = m.predict(des(b))
    t['kind'] = kind; rows.append(t)
T = pd.concat(rows)
T['pband'] = pd.cut(T.p, [0, .1, .2, .3, .4, .5, 1.0], labels=['<10', '10-20', '20-30', '30-40', '40-50', '50+'])
T['exp'] = np.select([T.starts <= 0, T.starts <= 3, T.starts <= 9], ['debut', '1-3 starts', '4-9 starts'], '10+ starts')
g = T.groupby(['kind', 'pband', 'exp'], observed=True).agg(runners=('win', 'size'), model_pct=('p', 'mean'), won_pct=('win', 'mean')).reset_index()
g[['model_pct', 'won_pct']] *= 100
print(g[g.pband.isin(['30-40', '40-50', '50+'])].round(1).to_string(index=False))
h = T[T.date.dt.year == 2026].groupby(['kind', 'pband'], observed=True).agg(runners=('win', 'size'), raw=('p', 'mean'), cal_2025fit=('cal26', 'mean'), won=('win', 'mean')).reset_index()
h[['raw', 'cal_2025fit', 'won']] *= 100; print(h.round(1).to_string(index=False))
print(T.groupby('kind').starts.describe())
T.to_parquet('/tmp/exp/calib_oos.parquet')
