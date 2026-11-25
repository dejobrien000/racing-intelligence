"""Batch 10 s10: where does Engine v2 systematically over- or under-estimate? Actual wins / expected wins (expected = engine
chance before calibration) by pre-race subgroup. Discovery = 2023-24; a pattern counts only if it is strong there (|z| >= 4,
roughly Bonferroni over ~150 cells) AND points the same way in 2025-26. West states (SA/WA/TAS) shown separately as a transfer check."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, 'b10/scripts'); import lib10 as L
b = L.base('nat'); b = b[b.meeting_date.dt.year >= 2023].copy()
mx = b.groupby('race_id').v2.transform('max'); b['p'] = np.exp(b.v2 - mx); b['p'] /= b.groupby('race_id').p.transform('sum')
b['rank'] = b.groupby('race_id').v2.rank(ascending=False, method='first')
U = pd.read_parquet('engine/frames/national.parquet', columns=['race_id', 'horse', 'gband', 'dband', 'age_n', 'female', 'gap', 'dyn_nat_sd', 'wt_change', 'dist_change', 'j_n', 't_n', 'prev_state', 'weight_kg', 'f_lastfp'])
F = pd.read_parquet('b10/out/feat.parquet', columns=['race_id', 'horse', 'prep_run', 'consec_quick', 'n_prior', 'h_sd'])
b = b.merge(U, on=['race_id', 'horse'], how='left').merge(F, on=['race_id', 'horse'], how='left')
b['rel'] = b.dyn_nat - b.groupby('race_id').dyn_nat.transform('mean')
cut = lambda s, bins, labels: pd.cut(s, bins, labels=labels).astype(str)
D = {'state': b.state, 'tier': b.tier, 'field': cut(b.field, [0, 7, 9, 11, 13, 30], ['<=7', '8-9', '10-11', '12-13', '14+']),
     'distance': b.dband, 'going': b.gband, 'age': cut(b.age_n, [0, 2, 3, 4, 5, 6, 20], ['2', '3', '4', '5', '6', '7+']), 'sex': b.female.map({1.0: 'mare/filly', 0.0: 'male'}),
     'days since run': cut(b.gap, [0, 10, 17, 27, 45, 90, 2000], ['<=10', '11-17', '18-27', '28-45', '46-90', '90+']), 'prep run': cut(b.prep_run, [0, 1, 2, 3, 5, 8, 99], ['1st up', '2nd', '3rd', '4-5', '6-8', '9+']),
     'career runs held': cut(b.n_prior, [-1, 0, 2, 5, 10, 20, 999], ['0', '1-2', '3-5', '6-10', '11-20', '21+']), 'engine rank': cut(b['rank'], [0, 1, 2, 3, 5, 8, 99], ['1', '2', '3', '4-5', '6-8', '9+']),
     'rating vs field (kg)': cut(b.rel, [-99, -6, -3, -1, 1, 3, 6, 99], ['<-6', '-6..-3', '-3..-1', '-1..1', '1..3', '3..6', '>6']), 'rating certainty': cut(b.dyn_nat_sd, [0, 2.3, 2.7, 3.2, 99], ['very sure', 'sure', 'unsure', 'very unsure']),
     'weight change': cut(b.wt_change, [-99, -2.5, -0.5, 0.5, 2.5, 99], ['down 3+', 'down 1-2', 'same', 'up 1-2', 'up 3+']), 'trip change': cut(b.dist_change, [-9, -0.15, -0.05, 0.05, 0.15, 9], ['much shorter', 'shorter', 'same', 'longer', 'much longer']),
     'jockey rides held': cut(b.j_n, [-1, 50, 200, 800, 1e6], ['<50', '50-200', '200-800', '800+']), 'trainer runners held': cut(b.t_n, [-1, 30, 150, 600, 1e6], ['<30', '30-150', '150-600', '600+']),
     'consecutive quick backups': cut(b.consec_quick, [-1, 0, 1, 2, 9], ['0', '1', '2', '3+']), 'own variability': cut(b.h_sd, [0, 4.5, 5.2, 6, 99], ['steady', 'average', 'variable', 'very variable']),
     'last start finish': cut(b.f_lastfp, [0, 1, 3, 6, 99], ['won', '2-3', '4-6', '7+']), 'carried weight': cut(b.weight_kg, [0, 54, 56, 58, 70], ['<=54', '54.5-56', '56.5-58', '58.5+'])}
b['P'] = np.where(b.meeting_date.dt.year <= 2024, 'disc', 'check'); b['W'] = np.where(b.state.isin(['SA', 'WA', 'TAS']), 'west', 'east')
rows = []
for dim, v in D.items():
    b['_v'] = v.values
    g = b[b._v != 'nan'].groupby(['_v', 'P', 'W']).agg(n=('win', 'size'), w=('win', 'sum'), e=('p', 'sum'), var=('p', lambda s: (s * (1 - s)).sum())).reset_index()
    for lvl, gg in g.groupby('_v'):
        r = {'dimension': dim, 'level': lvl}
        for P_ in ['disc', 'check']:
            s = gg[gg.P == P_]; n, w, e, va = s.n.sum(), s.w.sum(), s.e.sum(), s['var'].sum()
            r[f'{P_}_runners'] = int(n); r[f'{P_}_ratio'] = round(w / e, 3) if e else np.nan; r[f'{P_}_z'] = round((w - e) / np.sqrt(va), 1) if va else np.nan
        sw = gg[(gg.P == 'check') & (gg.W == 'west')]; r['west_check_ratio'] = round(sw.w.sum() / sw.e.sum(), 3) if sw.e.sum() else np.nan
        rows.append(r)
R = pd.DataFrame(rows); R['found'] = (R.disc_z.abs() >= 4) & (np.sign(R.disc_ratio - 1) == np.sign(R.check_ratio - 1)) & ((R.check_ratio - 1).abs() >= 0.5 * (R.disc_ratio - 1).abs())
R.to_csv('b10/out/s10_resid.csv', index=False); print(R[R.found].sort_values('disc_z').to_string(index=False)); print('\nstrong in discovery but NOT replicated:'); print(R[(R.disc_z.abs() >= 4) & ~R.found].to_string(index=False))
