"""Batch 20 F14-F15: family information AFTER trainer performance, trainer readiness, age, sex and race circumstances; and grouped breeding
x trainer (research only; no breeding input is approved for production; no prices).
Builds on batch19/b19_family.py (same population: genuine debutants aged 2-3 from March 2023 with a pedigree; same point-in-time family
signals: maternal siblings k=3, full siblings k=3, damsire k=30) and adds, all known before the debut:
  debut_rec   the trainer's earlier debutants' mean debut surprise (shrunk k=15; the trainer debut shadow's definition)
  sire_sig    the sire's earlier genuine debutants' mean debut surprise (shrunk k=30)
  race        maiden or not, distance band, field size, venue tier
Fit on 2023-24 debuts, judged on 2025-26 debuts (debut-performance error reduction, kg^2, bootstrap 95%). Then:
  F15  does a family/sire signal matter more for 'ready on debut' stables or for stables whose debutants usually need the run?
       (interaction with debut_rec), and is it the same at the 2nd/3rd start after the trainer early record (development)?
Usage (from research/): python3 batch20/b20_family_trainer.py -> batch20/out_b20_family_trainer.json"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
src = open('batch19/b19_family.py').read(); src = src[src.index('import re'):src.index("fit = G[G.yr <= 2024]")]
src = src.replace("columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'female', 't_surp']", "columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'female', 't_surp', 'tkey', 'distance_m', 'field', 'class_label', 'tier', 'r_debut']")
exec(src)
K = 15
def pit(ev, by, val, k):
    d = ev.groupby([by, 'date'])[val].agg(['sum', 'count']).reset_index().sort_values([by, 'date'])
    d['cs'] = d.groupby(by)['sum'].cumsum(); d['cn'] = d.groupby(by)['count'].cumsum(); return d[[by, 'date', 'cs', 'cn']].sort_values('date')
ALL = U[(U.k == 0) & U.age_n.isin([2, 3]) & (U.date >= '2023-03-01') & U.dyn_nat_inn.notna() & U.tkey.notna()].copy().join(H[['sire']], on='horse')
mu = float(ALL.dyn_nat_inn.mean())
G = G.sort_values('date'); G = pd.merge_asof(G, pit(ALL, 'tkey', 'dyn_nat_inn', K).rename(columns={'cs': 'tcs', 'cn': 'tcn'}), on='date', by='tkey', allow_exact_matches=False)
G['debut_rec'] = (G.tcs.fillna(0) + K * mu) / (G.tcn.fillna(0) + K) - mu
G = pd.merge_asof(G, pit(ALL.dropna(subset=['sire']), 'sire', 'dyn_nat_inn', 30).rename(columns={'cs': 'scs', 'cn': 'scn'}), on='date', by='sire', allow_exact_matches=False)
G['sire_sig'] = (G.scs.fillna(0) + 30 * mu) / (G.scn.fillna(0) + 30) - mu
G['maiden'] = (G.class_label == 'Maiden').astype(float); G['dband'] = pd.cut(G.distance_m, [0, 1100, 1300, 1600, 9999]).astype(str)
G['fsz'] = G.field.clip(4, 16); G['tier'] = G.tier.fillna('unknown').astype(str)
fit = G[G.yr <= 2024]; te = G[G.yr >= 2025]
BASES = {'Batch 19 base (trainer form, age, sex)': 'dyn_nat_inn ~ t_surp + two + female',
         'Batch 20 base (+ trainer readiness and race circumstances)': 'dyn_nat_inn ~ t_surp + debut_rec + two + female + maiden + C(dband) + fsz + C(tier)'}
OUT = {'debuts_fit_2023_24': int(len(fit)), 'debuts_judged_2025_26': int(len(te)), 'coverage_sire_signal_with_10plus_earlier': round(float((G.scn.fillna(0) >= 10).mean()), 3)}
def judge(base, term):
    m0 = smf.ols(base, fit).fit(); m1 = smf.ols(base + ' + ' + term, fit).fit(); e = (te.dyn_nat_inn - m0.predict(te)) ** 2 - (te.dyn_nat_inn - m1.predict(te)) ** 2
    rng = np.random.default_rng(5); bs = [e.values[rng.integers(0, len(e), len(e))].mean() for _ in range(1000)]
    return {'fit_coef': {t: [round(float(m1.params[t]), 3), round(float(m1.bse[t]), 3)] for t in term.split(' + ') if t in m1.params}, 'error_reduction_kg2': round(float(e.mean()), 3),
            'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)]}
OUT['F14 debut performance'] = {}
for bl, base in BASES.items():
    for lab, term in [('maternal siblings', 'mat_sig'), ('full siblings', 'full_sig'), ('damsire', 'ds_sig'), ('sire', 'sire_sig'), ('all family + sire', 'mat_sig + full_sig + ds_sig + sire_sig')]:
        OUT['F14 debut performance'][f'{bl} | {lab}'] = judge(base, term)
OUT['F14 trainer readiness itself (beyond Batch 19 base)'] = judge(BASES['Batch 19 base (trainer form, age, sex)'], 'debut_rec')
# F15: breeding x trainer readiness
base = BASES['Batch 20 base (+ trainer readiness and race circumstances)']
for lab, term in [('maternal x trainer readiness', 'mat_sig + mat_sig:debut_rec'), ('damsire x trainer readiness', 'ds_sig + ds_sig:debut_rec'), ('sire x trainer readiness', 'sire_sig + sire_sig:debut_rec')]:
    G2 = G.dropna(subset=['tkey']); m = smf.ols(base + ' + ' + term, G2).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(G2.tkey)[0]}); it = term.split(' + ')[1]
    OUT.setdefault('F15 interaction (all debuts, cluster by trainer)', {})[lab] = {'main': round(float(m.params[term.split(' + ')[0]]), 3), 'interaction': round(float(m.params[it]), 3), 'ci95': [round(float(x), 3) for x in m.conf_int().loc[it]]}
# development: family signal at the 2nd/3rd start after the trainer early record (batch20/b20_trainer_early.py definitions)
V = U[U.horse.isin(G.horse) & U.k.isin([1, 2]) & U.dyn_nat_inn.notna()].merge(G[['horse', 'mat_sig', 'ds_sig', 'sire_sig', 'full_sig', 'debut_rec', 'two', 'tkey']].rename(columns={'tkey': 'debut_tkey'}), on='horse')
V = V[(V.date >= '2024-01-01') & V.debut_tkey.notna()].copy(); V['t_surp'] = V.t_surp.fillna(0); V['female'] = V.female.fillna(0)
m = smf.ols('dyn_nat_inn ~ t_surp + debut_rec + two + female + mat_sig + ds_sig + sire_sig + full_sig', V).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(V.debut_tkey)[0]})
OUT['F14 2nd-3rd start surprise (development), family terms after trainer terms'] = {'runs': int(m.nobs), **{t: [round(float(m.params[t]), 3)] + [round(float(x), 3) for x in m.conf_int().loc[t]] for t in ['mat_sig', 'ds_sig', 'sire_sig', 'full_sig']}}
json.dump(OUT, open('batch20/out_b20_family_trainer.json', 'w'), indent=1)
for k, v in OUT.items(): print(k, json.dumps(v)[:900])
