"""Batch 27 P2: consolidated rating candidate - release-readiness review (research only; reuses saved harness runs, no refits).
Compares the consolidated candidate (harness K26: consolidated rating frame, all three layers refitted) with Engine v2.3 (harness P26)
on the same races. Window A = fit before 2024, judged 2024; B = fit before 2025, judged 2025-26 (both previously examined periods).
1 race accuracy (paired log-lik per race) overall and by state, tier, class, field size, distance, share of inexperienced runners;
2 runner calibration (actual/expected wins by predicted-chance bin; expected calibration error);
3 actual/expected by age, experience, established vs emerging, history completeness (experience-file source), days since last run;
4 individual performance accuracy from the rating frames (mean squared surprise, kg2; within-race rank correlation rating vs finish)
   by the same groups, runs from 2025.
Output batch27/out_b27_cons_review.json"""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(27)
out = {}
ra = pd.read_parquet('/tmp/cand/res_P26_R.parquet'); rb = pd.read_parquet('/tmp/cand/res_K26_R.parquet')
cols = ['race', 'race_id', 'horse', 'date', 'state', 'tier', 'class_label', 'field', 'distance_m', 'age_n', 'dyn_nat', 'dyn_nat_inn', 'fpct', 'prev_date']
C2 = pd.read_parquet('/tmp/cand/frames/C2_national.parquet', columns=cols); CO = pd.read_parquet('/tmp/cand/frames/CONS_national.parquet', columns=['race', 'horse', 'dyn_nat', 'dyn_nat_inn'])
C2['date'] = pd.to_datetime(C2.date); C2 = C2.sort_values(['horse', 'date', 'race']); C2['k'] = C2.groupby('horse').cumcount()
C2['days'] = (C2.date - pd.to_datetime(C2.prev_date)).dt.days
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'source']).rename(columns={'race_key': 'race'})
C2 = C2.merge(E, on=['race', 'horse'], how='left')
def cls(c):
    c = str(c)
    if 'Maiden' in c: return 'Maiden'
    if c in ('Benchmark', 'BM'): return 'Benchmark'
    if 'Group' in c or 'Listed' in c or 'Open' in c or 'Hcp' in c: return 'Open/Hcp/Stakes'
    return 'Other/Class'
C2['cls'] = C2.class_label.map(cls)
C2['fieldb'] = pd.cut(C2.field, [0, 8, 12, 30], labels=['<=8', '9-12', '13+']).astype(str)
C2['distb'] = pd.cut(C2.distance_m.astype(float), [0, 1100, 1400, 1800, 4000], labels=['<=1100', '1101-1400', '1401-1800', '1800+']).astype(str)
C2['inexp'] = C2.groupby('race_id').k.transform(lambda s: (s <= 3).mean())
C2['inexpb'] = pd.cut(C2.inexp, [-0.01, 0.0, 0.3, 1.0], labels=['none', 'up to 30%', 'over 30%']).astype(str)
C2['ageb'] = pd.cut(C2.age_n, [0, 2, 3, 4, 5, 30], labels=['2yo', '3yo', '4yo', '5yo', '6yo+']).astype(str)
C2['expb'] = pd.cut(C2.k, [-1, 0, 3, 10, 25, 999], labels=['debut', '1-3 runs', '4-10', '11-25', '26+']).astype(str)
C2['stage'] = np.where((C2.k >= 15) & (C2.age_n >= 5), 'established (15+ runs, 5yo+)', np.where(C2.k <= 5, 'emerging (0-5 runs)', 'middle'))
C2['gap'] = pd.cut(C2.days, [-1, 13, 59, 119, 364, 10000], labels=['<14d', '14-59d', '60-119d', '120-364d', '365d+']).astype(str)
C2['hist'] = C2.source.fillna('unknown').astype(str)
# 1 race-level
R = C2.groupby('race_id').agg(state=('state', 'first'), tier=('tier', 'first'), cls=('cls', 'first'), fieldb=('fieldb', 'first'), distb=('distb', 'first'), inexpb=('inexpb', 'first'))
def paired(w, m=None):
    x = ra[ra.window == w].set_index('race_id').lp.to_frame('a').join(rb[rb.window == w].set_index('race_id').lp.to_frame('b'), how='inner').join(R, how='left')
    if m is not None: x = x[m(x)]
    d = (x.b - x.a).values
    if len(d) < 80: return None
    bs = d[rng.integers(0, len(d), (800, len(d)))].mean(1)
    return {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'ci95': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]}
out['race'] = {}
for w in ['A', 'B']:
    r = {'all': paired(w)}
    for dim in ['state', 'tier', 'cls', 'fieldb', 'distb', 'inexpb']:
        for v in sorted(R[dim].dropna().astype(str).unique()):
            g = paired(w, lambda x, dim=dim, v=v: x[dim].astype(str) == v)
            if g: r[f'{dim}={v}'] = g
    out['race'][w] = r
print(json.dumps(out['race']['B']['all']), json.dumps(out['race']['A']['all']), flush=True)
# 2-3 runner calibration
ua = pd.read_parquet('/tmp/cand/runners_P26_R.parquet', columns=['race_id', 'horse', 'win', 'p_A', 'p_B']); ub = pd.read_parquet('/tmp/cand/runners_K26_R.parquet', columns=['race_id', 'horse', 'p_A', 'p_B'])
U = ua.merge(ub, on=['race_id', 'horse'], suffixes=('_v23', '_cons')).merge(C2.drop_duplicates(['race_id', 'horse'])[['race_id', 'horse', 'ageb', 'expb', 'stage', 'gap', 'hist', 'state']], on=['race_id', 'horse'], how='left')
def cal(Z, pa, pb):
    Z = Z[Z[pa].notna() & Z[pb].notna()]
    o = {}
    for lab, p in [('v2.3', pa), ('consolidated', pb)]:
        b = pd.cut(Z[p], [0, .02, .05, .1, .2, .35, 1.0])
        t = Z.groupby(b, observed=True).agg(n=('win', 'size'), wins=('win', 'sum'), exp=(p, 'sum'))
        t['ae'] = (t.wins / t.exp).round(3)
        o[lab] = {'bins': {str(k): {'runners': int(v.n), 'A/E': float(v.ae)} for k, v in t.iterrows()},
                  'ece_pct_pts': round(float((t.wins - t.exp).abs().sum() / t.n.sum() * 100), 3)}
    return o
out['calibration'] = {'A': cal(U, 'p_A_v23', 'p_A_cons'), 'B': cal(U, 'p_B_v23', 'p_B_cons')}
out['groups_actual_vs_expected_B'] = {}
ZB = U[U.p_B_v23.notna() & U.p_B_cons.notna()]
for dim in ['ageb', 'expb', 'stage', 'gap', 'hist', 'state']:
    t = ZB.groupby(dim).agg(runners=('win', 'size'), wins=('win', 'sum'), e23=('p_B_v23', 'sum'), econs=('p_B_cons', 'sum'))
    out['groups_actual_vs_expected_B'][dim] = {str(k): {'runners': int(v.runners), 'A/E v2.3': round(float(v.wins / v.e23), 3), 'A/E consolidated': round(float(v.wins / v.econs), 3)} for k, v in t.iterrows() if v.runners >= 300}
# 4 individual accuracy from the rating frames (runs from 2025, horse already rated)
I = C2[['race', 'race_id', 'horse', 'date', 'k', 'ageb', 'expb', 'stage', 'gap', 'hist', 'state', 'tier', 'cls', 'fpct', 'dyn_nat', 'dyn_nat_inn']].merge(CO.rename(columns={'dyn_nat': 'dn_cons', 'dyn_nat_inn': 'inn_cons'}), on=['race', 'horse'], how='left')
I = I[(I.date >= '2025-01-01') & (I.k >= 1) & I.dyn_nat_inn.notna() & I.inn_cons.notna()]
def acc(Z):
    if len(Z) < 500: return None
    r23 = Z.groupby('race_id').apply(lambda g: g.dyn_nat.corr(-g.fpct, method='spearman') if len(g) >= 4 else np.nan).mean()
    rco = Z.groupby('race_id').apply(lambda g: g.dn_cons.corr(-g.fpct, method='spearman') if len(g) >= 4 else np.nan).mean()
    return {'runs': int(len(Z)), 'mse_kg2 v2.3': round(float((Z.dyn_nat_inn ** 2).mean()), 2), 'mse_kg2 consolidated': round(float((Z.inn_cons ** 2).mean()), 2),
            'rank_corr v2.3': round(float(r23), 3), 'rank_corr consolidated': round(float(rco), 3)}
out['individual_2025_26'] = {'all': acc(I)}
for dim in ['ageb', 'expb', 'stage', 'gap', 'hist', 'state', 'tier', 'cls']:
    for v in sorted(I[dim].dropna().astype(str).unique()):
        a = acc(I[I[dim].astype(str) == v])
        if a: out['individual_2025_26'][f'{dim}={v}'] = a
json.dump(out, open('batch27/out_b27_cons_review.json', 'w'), indent=1, default=str)
print(json.dumps(out['individual_2025_26']['all']), json.dumps({k: v['ece_pct_pts'] for k, v in out['calibration']['B'].items()}))
