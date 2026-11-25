"""Batch 11: out-of-sample (2025-26) checks under Engine v2 and Engine v2.2 (dev-fit chances): lightly raced horses (s5), light weights (s8),
quick backups by trainer (s9), Vic->Tas (s10). Horse-clustered intervals. Research only."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'b11'); from s11_common import ae
x = pd.read_parquet('b11/v22hist.parquet'); x = x[x.groupby('race_id').win.transform('sum') == 1]
x['rel'] = x.dyn_nat - x.groupby('race_id').dyn_nat.transform('mean'); x['rk'] = x.groupby('race_id').v22_dev.rank(ascending=False, method='first')
x['q3'] = pd.cut(x.groupby('race_id').dyn_nat.rank(ascending=False, pct=True), [0, 1 / 3, 2 / 3, 1.01], labels=['top third of field', 'middle third', 'bottom third'])
oos = x[x.meeting_date.dt.year >= 2025].copy()
def both(g, nm):
    a = ae(g.assign(p=g.p_v2), 'horse'); b = ae(g.assign(p=g.p_v22), 'horse')
    return {'group': nm, 'runners': a['runners'], 'wins': a['wins'], 'v2_expected': a['expected'], 'v2_ratio': a['ratio'], 'v2_ci': f"{a.get('lo95')}-{a.get('hi95')}", 'v22_expected': b['expected'], 'v22_ratio': b['ratio'], 'v22_ci': f"{b.get('lo95')}-{b.get('hi95')}"}
# ---- s5 lightly raced
rows = []
for nm, m in [('first starter (0 runs held)', oos.n_prior == 0), ('1 run held', oos.n_prior == 1), ('2 runs', oos.n_prior == 2), ('3-5 runs', oos.n_prior.between(3, 5)), ('6-14 runs', oos.n_prior.between(6, 14)), ('15+ runs', oos.n_prior >= 15)]:
    rows.append(both(oos[m], nm))
lr = oos[oos.n_prior.between(1, 3)].copy(); lr['traj'] = np.where(lr.slope5 > 0, 'rating rising', np.where(lr.slope5 < 0, 'rating falling', 'one run only'))
lr['opp'] = np.where(lr.last_race_strength > lr.groupby('race_id').dyn_nat.transform('mean'), 'last race stronger than today', 'last race weaker/equal')
for c in ['q3', 'traj', 'opp']:
    for v, g in lr.groupby(c, observed=True): rows.append(both(g, f'1-3 runs: {v}'))
ex = lr[(lr.q3 == 'top third of field') & (lr.traj == 'rating rising')]; rows.append(both(ex, '1-3 runs: top third AND rising ("exceptional")'))
ex2 = lr[(lr.rk == 1)]; rows.append(both(ex2, '1-3 runs: engine top pick'))
fs = oos[oos.n_prior == 0]
for v, g in fs.groupby(fs.rk.clip(upper=4).map({1: 'first starter ranked 1st', 2: 'ranked 2nd', 3: 'ranked 3rd', 4: 'ranked 4th+'})): rows.append(both(g, v))
R = pd.DataFrame(rows); print('== lightly raced / first starters, 2025-26 =='); print(R.to_string(index=False)); R.to_csv('b11/out_lightly_raced.csv', index=False)
# ---- s8 light weight after v2.2
W = pd.DataFrame([both(oos[oos.light_weight == 1], 'carried <=54 kg'), both(oos[oos.light_weight == 0], 'carried >54 kg'), both(oos[(oos.light_weight == 1) & (oos.class_label == 'Benchmark')], '<=54 kg in benchmark handicaps'),
                  both(oos[(oos.light_weight == 1) & (oos.class_label == 'Maiden')], '<=54 kg in maidens')])
print('== light weights, 2025-26 =='); print(W.to_string(index=False)); W.to_csv('b11/out_light_weight_v22.csv', index=False)
# ---- s10 Vic->Tas under both
vt = oos[(oos.prev_state == 'VIC') & (oos.state == 'TAS')].copy(); first = x.sort_values('meeting_date').groupby(['horse', 'state']).cumcount() == 0; vt['first'] = first.reindex(vt.index)
V = pd.DataFrame([both(vt, 'Vic->Tas all'), both(vt[vt['first']], 'first Tas start'), both(vt[~vt['first']], 'repeat Tas start'), both(oos[(oos.prev_state == 'TAS') & (oos.state == 'VIC')], 'Tas->Vic'),
                  both(oos[(oos.prev_state == 'VIC') & (oos.state == 'SA')], 'Vic->SA'), both(oos[(oos.prev_state == 'SA') & (oos.state == 'VIC')], 'SA->Vic')])
print('== moves, 2025-26 =='); print(V.to_string(index=False)); V.to_csv('b11/out_moves_v22.csv', index=False)
# ---- s9 trainer-specific quick backups: split-half persistence of shrunken trainer effects, residual to v2.2 (which already has a general quick term)
q = x[x.quick_today == 1].copy(); q['half'] = np.where(q.meeting_date.dt.year <= 2024, 'A (2022-24)', 'B (2025-26)')
o = x[x.quick_today != 1].copy(); o['half'] = np.where(o.meeting_date.dt.year <= 2024, 'A (2022-24)', 'B (2025-26)')
K = 5.0  # shrinkage: 5 expected wins of prior weight on 'no trainer effect'
def eff(d):
    g = d.groupby(['tkey', 'half']).agg(w=('win', 'sum'), e=('p_v22', 'sum'), n=('win', 'size')).reset_index(); g['shr'] = np.log((g.w + K) / (g.e + K)); return g
eq, eo = eff(q), eff(o)
m = eq.merge(eo, on=['tkey', 'half'], suffixes=('_q', '_o')); m['diff'] = m.shr_q - m.shr_o
P = m.pivot(index='tkey', columns='half', values=['diff', 'n_q']); P = P.dropna(); P.columns = [f'{a}|{b}' for a, b in P.columns]
P = P[(P['n_q|A (2022-24)'] >= 10) & (P['n_q|B (2025-26)'] >= 10)]
r = np.corrcoef(P['diff|A (2022-24)'], P['diff|B (2025-26)'])[0, 1]
print('== trainer quick backups (residual to v2.2) ==', 'trainers with >=10 quick backups in both halves:', len(P), '| split-half correlation of shrunken trainer effects:', round(r, 3))
rng = np.random.default_rng(1); null = [np.corrcoef(P['diff|A (2022-24)'], rng.permutation(P['diff|B (2025-26)'].values))[0, 1] for _ in range(2000)]; print('permutation p (one-sided):', round(float((np.array(null) >= r).mean()), 3))
top = P.sort_values('diff|A (2022-24)', ascending=False).head(10); print('top-10 trainers on 2022-24 quick-backup edge, their 2025-26 edge:'); print(top.round(2).to_string())
g = q[q.meeting_date.dt.year >= 2025]; print('general quick backups 2025-26:', both(g, 'quick backup (<=10 days)'))
pd.DataFrame({'trainers': [len(P)], 'split_half_r': [r], 'perm_p': [float((np.array(null) >= r).mean())]}).to_csv('b11/out_trainer_quick.csv', index=False)
