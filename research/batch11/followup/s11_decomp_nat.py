"""Batch 11 follow-up: what share of the national race-relative score comes from each kind of evidence (2025-26 races, Engine v2.2 dev-fit).
Share = cov(family contribution, total score) / var(total), within race (sums to 1)."""
import sys, json, numpy as np, pandas as pd
src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
U0, E, NFAM2, build_terms, offset_v1 = g['U'], g['E'], g['NFAM2'], g['build_terms'], g['offset_v1']
mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
F2 = json.load(open('benchmarks/engine_v2/manifest.json'))['families']['NSW_VIC_ACT']; M22 = json.load(open('benchmarks/engine_v2_2/manifest.json'))
x = E.nat_frame(U0); x['meeting_date'] = pd.to_datetime(x.meeting_date); allt = sum(NFAM2.values(), []); x = build_terms(x, allt)
x = x[x.meeting_date.dt.year >= 2025].copy()
fam = {'Margin-based rating (dyn_nat: margins, weight carried, opposition)': ['dyn_nat'],
       'Time-based figures (a_rec, a_best3: winner time vs par minus margin)': ['a_rec', 'a_best3', 'missfig'],
       'Opposition faced (a_fs3)': ['a_fs3'], 'Weight today vs field (a_wt_rel)': ['a_wt_rel'],
       'Recent form (finish positions, last margin, strike rate, starts)': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'],
       'Fitness and spacing': ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays'], 'Horse course/going/distance records (rating surprises)': ['c_rec', 'g_rec', 'd_rec']}
C = pd.DataFrame(index=x.index)
for k, cols in fam.items():
    C[k] = sum(C2[c] * ((x[c].astype(float) - x.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0) for c in cols if c in C2)
for f, terms in NFAM2.items():
    C['v2: ' + f] = x[['t::' + t for t in terms]].fillna(0.0).values @ np.array([F2['coef_per_term_sd_dev_fit'][t] for t in terms])
V = pd.read_parquet('b11/v22hist.parquet', columns=['race_id', 'horse'] + M22['terms'])
x = x.merge(V, on=['race_id', 'horse'], how='left') if False else x
xv = x[['race_id', 'horse']].merge(V, on=['race_id', 'horse'], how='left'); xv.index = x.index
for f, terms in M22['term_families'].items():
    C['v2.2: ' + f] = sum(M22['coef_per_sd_dev_fit'][t] * ((pd.to_numeric(xv[t], errors='coerce') - pd.to_numeric(xv[t], errors='coerce').groupby(x.race_id).transform('mean')).fillna(0.0) / M22['term_sd_dev_fit'][t]).values for t in terms)
C = C.sub(C.groupby(x.race_id.values).transform('mean'))
tot = C.sum(axis=1); out = pd.DataFrame({'share_of_score_variation_%': (100 * C.apply(lambda c: np.cov(c, tot)[0, 1]) / tot.var()).round(1),
                                          'sd_kg_equiv': (C.std() / json.load(open('benchmarks/engine_v2_1/manifest.json'))['families']['NSW_VIC_ACT']['score_per_kg_total']).round(2)})
print(out.sort_values('share_of_score_variation_%', ascending=False).to_string()); out.to_csv('b11/out_decomp_national.csv')
print('races', x.race_id.nunique(), 'runners', len(x))
