"""Batch 21 C9-C10: what follows a big run after a trainer change, and a big run at an unfamiliar distance (research only; Engine v2.3
frame; no prices; nothing is claimed about training methods or stable intention).
Big run = performance at least 2 kg above the horse's pre-race rating (field-relative surprise), horse with 6+ runs held, 2023 to mid-2026.
Everything used to classify a run comes from EARLIER runs; outcomes are the surprises of the next 1, 3 and 5 starts (performance minus the
rating at THAT later run: positive = the rating still under-believed the horse). Horses that did not run again are counted, not dropped.
C10 unfamiliar distance: fewer than 3 earlier runs in the run's distance band (to 1100 / 1101-1300 / 1301-1500 / 1501-1800 / 1801+) and the
horse's most-raced earlier band is a different one. Later runs are split: same new band / back to the previous main band / a neighbouring
band / other. Ability would show as positive surprises everywhere; distance suitability as positive at the new band only.
C9 trainer change: first run for a new trainer; 2nd-5th run for the new trainer; no change. Split by return to previous best (within
0.5 kg) vs beyond it, and by the trajectory before (slope of the last 5 performances: declining < -0.5 kg/run, improving > +0.5).
Controls (regression of the next-run surprise, cluster by horse): size of the big run, age, spell before the next run, distance change and
class step at the next run, going group at the next run, the next run's general trainer record (t_surp). Trainer-specific transfer record:
point-in-time mean surprise of horses in their first 3 runs after joining that trainer (shrunk, k = 10).
Usage (from research/): python3 batch21/b21_breakthroughs.py -> batch21/out_b21_breakthroughs.json"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'distance_m', 'tkey', 'class_label', 't_surp', 'cond_group'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['perf'] = U.dyn_nat + U.dyn_nat_inn
BANDS = ['to1100', '1101-1300', '1301-1500', '1501-1800', '1801+']
U['bi'] = pd.cut(U.distance_m, [0, 1100, 1300, 1500, 1800, 9999], labels=False).astype(float)
CL = {'Maiden': 0, 'Class': 1, 'Restricted': 1, 'BM': 2, 'Benchmark': 2, 'Other': 2, 'Open/Hcp': 3, 'Open': 3, 'Listed': 4, 'Group': 5}; U['cl'] = U.class_label.map(CL)
n = len(U); cols = ['k', 'band_runs', 'main_band', 'slope5', 'best', 'tr_runs', 'tr_change'] + [f'{a}{i}' for i in range(1, 6) for a in ('s', 'b', 'gap', 'cl', 'ts', 'cg')]
A_ = {c: np.full(n, np.nan) for c in cols}; d64 = U.date.values.astype('datetime64[D]').astype(np.int64)
cg = U.cond_group.astype('category'); cgc = cg.cat.codes.values.astype(float); cgc[cgc < 0] = np.nan
for h, idx in U.groupby('horse').indices.items():
    p = U.perf.values[idx]; s = U.dyn_nat_inn.values[idx]; b = U.bi.values[idx]; t = U.tkey.values[idx]; d = d64[idx]; cl = U.cl.values[idx]; ts = U.t_surp.values[idx]; cc = cgc[idx]
    for j in range(len(idx)):
        i = idx[j]; A_['k'][i] = j
        if j == 0: continue
        pb = b[:j]; q = p[:j][~np.isnan(p[:j])]
        A_['band_runs'][i] = np.sum(pb == b[j]); vb = pb[~np.isnan(pb)]
        if len(vb): A_['main_band'][i] = pd.Series(vb).value_counts().idxmax()
        if len(q) >= 5: A_['slope5'][i] = np.polyfit(np.arange(5), q[-5:], 1)[0]
        if len(q): A_['best'][i] = q.max()
        same = 0
        for jj in range(j, -1, -1):
            if t[jj] == t[j]: same += 1
            else: break
        A_['tr_runs'][i] = same; A_['tr_change'][i] = float(isinstance(t[j - 1], str) and t[j - 1] != t[j])
        for m in range(1, 6):
            if j + m < len(idx):
                A_[f's{m}'][i] = s[j + m]; A_[f'b{m}'][i] = b[j + m]; A_[f'cl{m}'][i] = cl[j + m] - cl[j + m - 1] if not np.isnan(cl[j + m]) and not np.isnan(cl[j + m - 1]) else np.nan
                A_[f'gap{m}'][i] = d[j + m] - d[j + m - 1]; A_[f'ts{m}'][i] = ts[j + m]; A_[f'cg{m}'][i] = cc[j + m]
for c, v in A_.items(): U[c] = v
# trainer-specific transfer record (point in time): surprises of horses in their first 3 runs with a new trainer, credited to that trainer
g = U[(U.tr_runs <= 3) & (U.k >= 1) & U.tkey.notna() & U.dyn_nat_inn.notna()].copy(); g = g[g.groupby(['horse', 'tkey']).tr_change.transform('max') > 0]
d = g.groupby(['tkey', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values(['tkey', 'date']); mu = float(g.dyn_nat_inn.mean())
d['cs'] = d.groupby('tkey')['sum'].cumsum() - d['sum']; d['cn'] = d.groupby('tkey')['count'].cumsum() - d['count']; d['tr_transfer_rec'] = (d.cs + 10 * mu) / (d.cn + 10) - mu
U = U.merge(d[['tkey', 'date', 'tr_transfer_rec', 'cn']].rename(columns={'cn': 'tr_transfer_n'}), on=['tkey', 'date'], how='left')
E = U[(U.date >= '2023-01-01') & (U.date <= '2026-06-30') & (U.dyn_nat_inn >= 2) & (U.k >= 6)].copy()
E['m3'] = E[['s1', 's2', 's3']].mean(axis=1, skipna=False); E['m5'] = E[['s1', 's2', 's3', 's4', 's5']].mean(axis=1, skipna=False)
def S(x, col='s1'):
    y = x[col].dropna(); return {'big_runs': int(len(x)), 'with_outcome': int(len(y)), 'mean_kg': round(float(y.mean()), 2) if len(y) else None, 'se': round(float(y.std() / np.sqrt(len(y))), 2) if len(y) > 1 else None}
OUT = {'note': 'mean surprise (kg) of later runs; positive = the rating still under-believed the horse; big runs with 6+ runs held, 2023 to Jun 2026'}
# ---------- C10 unfamiliar distance
E['unfam'] = (E.band_runs < 3) & E.main_band.notna() & (E.main_band != E.bi)
E['step'] = np.where(E.bi > E.main_band, 'stepping up', np.where(E.bi < E.main_band, 'stepping down', 'same'))
def rel(bn, bb, main):
    if np.isnan(bn): return np.nan
    if bn == bb: return 'same new distance band'
    if bn == main: return 'back to previous main band'
    if abs(bn - bb) == 1: return 'neighbouring band'
    return 'other band'
for m in range(1, 6): E[f'r{m}'] = [rel(a, b, c) for a, b, c in zip(E[f'b{m}'], E.bi, E.main_band)]
o = {}
for lab, x in [('unfamiliar distance', E[E.unfam]), ('familiar distance (control)', E[~E.unfam & (E.band_runs >= 3)])]:
    oo = {'next run, any distance': S(x), 'next 3 (all three)': S(x, 'm3'), 'next 5 (all five)': S(x, 'm5')}
    for r in ['same new distance band', 'back to previous main band', 'neighbouring band', 'other band']:
        if lab.startswith('familiar') and r != 'same new distance band': rr = {'same new distance band': 'same band', 'back to previous main band': None}.get(r)
        vals = pd.concat([x.loc[x[f'r{m}'] == r, f's{m}'] for m in range(1, 6)]) if not lab.startswith('familiar') else pd.concat([x.loc[x[f'b{m}'] == x.bi, f's{m}'] for m in range(1, 6)]) if r == 'same new distance band' else pd.concat([x.loc[(x[f'b{m}'] != x.bi) & x[f'b{m}'].notna(), f's{m}'] for m in range(1, 6)]) if r == 'neighbouring band' else pd.Series(dtype=float)
        if len(vals): oo[f'next 5 runs at: {r}' if not lab.startswith('familiar') else ('next 5 runs at the same band' if r == 'same new distance band' else 'next 5 runs at a different band')] = {'runs': int(vals.notna().sum()), 'mean_kg': round(float(vals.mean()), 2), 'se': round(float(vals.std() / np.sqrt(max(vals.notna().sum(), 1))), 2)}
    o[lab] = oo
for st, x in E[E.unfam].groupby('step'):
    o[f'unfamiliar, {st}'] = {r: {'runs': int(v.notna().sum()), 'mean_kg': round(float(v.mean()), 2)} for r in ['same new distance band', 'back to previous main band', 'neighbouring band']
                              for v in [pd.concat([x.loc[x[f'r{m}'] == r, f's{m}'] for m in range(1, 6)])] if len(v)}
OUT['C10 unfamiliar distance'] = o
# ---------- C9 trainer change
E['tc'] = np.where((E.tr_change == 1), 'first run for new trainer', np.where((E.tr_runs.between(2, 5)) & (E.groupby('horse').tr_change.transform('max') >= 0) & (E.tr_runs < E.k), '2nd-5th run for new trainer', 'no recent change'))
# 2nd-5th only counts when the horse actually changed trainer within its held history
chg = U.groupby('horse').tr_change.max(); E.loc[(E.tc == '2nd-5th run for new trainer') & ~E.horse.map(chg).eq(1), 'tc'] = 'no recent change'
E['level'] = np.where(E.perf <= E.best + 0.5, 'returning to previous best (or below)', 'beyond previous best')
E['traj'] = np.where(E.slope5 < -0.5, 'previously declining', np.where(E.slope5 > 0.5, 'previously improving', 'previously flat'))
o = {}
for k, x in E.groupby('tc'): o[k] = {'next run': S(x), 'next 3': S(x, 'm3')}
for (a, b), x in E.groupby(['tc', 'level']): o[f'{a} | {b}'] = S(x)
for (a, b), x in E.groupby(['tc', 'traj']): o[f'{a} | {b}'] = S(x)
OUT['C9 trainer change (next-run surprise)'] = o
E['first_new'] = (E.tc == 'first run for new trainer').astype(float); E['later_new'] = (E.tc == '2nd-5th run for new trainer').astype(float)
E['size'] = E.dyn_nat_inn; E['spell1'] = (E.gap1 >= 60).astype(float); E['dch1'] = (E.b1 - E.bi); E['beyond'] = (E.level == 'beyond previous best').astype(float)
E['cg1'] = E.cg1.fillna(-1).astype(int).astype(str); E['ts1'] = E.ts1.fillna(0)
R = E.dropna(subset=['s1', 'dch1', 'cl1', 'age_n']).copy()
fm = 's1 ~ first_new + later_new + size + age_n + spell1 + dch1 + cl1 + C(cg1) + ts1 + beyond + unfam'
R['unfam'] = R.unfam.astype(float)
m = smf.ols(fm, R).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(R.horse)[0]})
OUT['C9-C10 next-run surprise with controls (kg)'] = {'runs': int(m.nobs), **{v: [round(float(m.params[v]), 3)] + [round(float(x), 3) for x in m.conf_int().loc[v]] for v in ['first_new', 'later_new', 'beyond', 'unfam', 'size', 'spell1', 'ts1']}}
Rt = R[R.first_new == 1].copy(); Rt['tr_transfer_rec'] = Rt.tr_transfer_rec.fillna(0)
if len(Rt) > 200:
    mt = smf.ols('s1 ~ tr_transfer_rec + size + age_n + spell1 + dch1 + cl1 + ts1', Rt).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(Rt.horse)[0]})
    OUT['C9 trainer-specific transfer record (first run for new trainer only)'] = {'runs': int(mt.nobs), 'coef': [round(float(mt.params['tr_transfer_rec']), 3)] + [round(float(x), 3) for x in mt.conf_int().loc['tr_transfer_rec']],
                                                                                  'record_sd_kg': round(float(Rt.tr_transfer_rec.std()), 3), 'general_trainer_record_coef': round(float(mt.params['ts1']), 3)}
json.dump(OUT, open('batch21/out_b21_breakthroughs.json', 'w'), indent=1); print(json.dumps(OUT, indent=1)[:7000])
