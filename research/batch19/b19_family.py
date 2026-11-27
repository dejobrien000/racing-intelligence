"""Batch 19 C10: dam, sibling and damsire information (research only; no breeding input is approved for production).
Coverage first, then one simple point-in-time question: does the family's demonstrated ability say anything about a genuine debutant's
first run beyond general trainer form, age and sex? Family signals, all known BEFORE the debut and excluding the horse itself:
 - maternal siblings (same dam): mean of each earlier sibling's latest rating (Engine v2.3, kg) before the debut date, shrunk (k = 3)
 - full siblings (same sire and dam): same, where any exist
 - damsire: mean debut surprise of earlier genuine debutants out of the damsire's daughters, shrunk (k = 30)
Fit on 2023-24 debuts, judged on 2025-26 debuts (debut-performance error). Ratings are relative levels, so the sibling signal is the
sibling rating minus the mean rating of all horses at the same date.
Usage (from research/): python3 batch19/b19_family.py -> batch19/out_b19_family.json"""
import re, json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
P = con.execute("select name_key, sire, dam, damsire from bn_runner where dam is not null").fetchdf(); P['horse'] = P.name_key.map(nk)
P = P.groupby('horse')[['sire', 'dam', 'damsire']].agg(lambda s: s.mode().iloc[0])
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'female', 't_surp'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
H = U.groupby('horse').agg(first=('date', 'min'), age1=('age_n', 'first')); H = H.join(P, how='left')
damkeys = set(P.dam.map(nk)); horses = set(U.horse)
OUT = {'coverage': {'horses_raced': int(len(H)), 'with_pedigree': int(H.dam.notna().sum()), 'dams': int(H.dam.nunique()), 'damsires': int(H.damsire.nunique()),
                    'dams_that_raced_in_our_data': int(len(damkeys & horses)), 'horses_whose_dam_raced_in_our_data': int(H.dam.map(nk).isin(horses).sum()),
                    'horses_with_a_maternal_sibling_in_data': int((H.groupby('dam').dam.transform('count') >= 2).sum()),
                    'horses_with_a_full_sibling_in_data': int((H.groupby(['sire', 'dam']).dam.transform('count') >= 2).sum()),
                    'sire_dam_combinations': int(H.groupby(['sire', 'dam']).ngroups)}}
G = U[(U.k == 0) & U.age_n.isin([2, 3]) & (U.date >= '2023-03-01') & U.dyn_nat_inn.notna()].copy().join(H[['sire', 'dam', 'damsire']], on='horse').dropna(subset=['dam'])
# population mean rating by date (all horses' latest rating), to express sibling ratings relative to the population
lat = U[['horse', 'date', 'dyn_nat']].dropna()
popm = lat.groupby('date').dyn_nat.mean().rolling(60, min_periods=1).mean()
def sib_signal(G, by, kshr):
    rows = []
    fam = H.reset_index().dropna(subset=list(by)).groupby(list(by)).horse.apply(list).to_dict()
    L = lat.sort_values('date')
    byh = {h: g for h, g in L.groupby('horse')}
    for i, r in G.iterrows():
        sibs = [s for s in fam.get(tuple(r[c] for c in by) if len(by) > 1 else r[by[0]], []) if s != r.horse]
        vals = []
        for s in sibs:
            g = byh.get(s)
            if g is None: continue
            g = g[g.date < r.date]
            if len(g): vals.append(g.dyn_nat.iloc[-1] - popm.asof(g.date.iloc[-1]))
        rows.append((len(vals), (np.sum(vals) / (len(vals) + kshr)) if vals else 0.0))
    return pd.DataFrame(rows, index=G.index, columns=['n', 'sig'])
m = sib_signal(G, ['dam'], 3.0); G['mat_n'] = m.n; G['mat_sig'] = m.sig
f = sib_signal(G, ['sire', 'dam'], 3.0); G['full_n'] = f.n; G['full_sig'] = f.sig
# damsire: earlier genuine debutants out of the damsire's daughters (point in time, shrunk k = 30)
G = G.sort_values('date'); d = G.groupby(['damsire', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values(['damsire', 'date'])
d[['cs', 'cn']] = d.groupby('damsire')[['sum', 'count']].cumsum().values
G = pd.merge_asof(G, d[['date', 'damsire', 'cs', 'cn']].sort_values('date'), on='date', by='damsire', allow_exact_matches=False)
popd = G.dyn_nat_inn.expanding().mean().shift(1).fillna(0).values
G['ds_sig'] = ((G.cs.fillna(0) - G.cn.fillna(0) * popd) / (G.cn.fillna(0) + 30))
G['t_surp'] = G.t_surp.fillna(0); G['two'] = (G.age_n == 2).astype(float); G['female'] = G.female.fillna(0); G['yr'] = G.date.dt.year
OUT['coverage']['genuine_debuts_with_pedigree'] = int(len(G)); OUT['coverage']['with_an_earlier_maternal_sibling'] = int((G.mat_n > 0).sum()); OUT['coverage']['with_an_earlier_full_sibling'] = int((G.full_n > 0).sum())
fit = G[G.yr <= 2024]; te = G[G.yr >= 2025]; base = 'dyn_nat_inn ~ t_surp + two + female'
res = {}
m0 = smf.ols(base, fit).fit()
for lab, term in [('maternal siblings', 'mat_sig'), ('full siblings', 'full_sig'), ('damsire', 'ds_sig'), ('all three', 'mat_sig + full_sig + ds_sig')]:
    m1 = smf.ols(base + ' + ' + term, fit).fit(); e = (te.dyn_nat_inn - m0.predict(te)) ** 2 - (te.dyn_nat_inn - m1.predict(te)) ** 2
    rng = np.random.default_rng(5); bs = [e.values[rng.integers(0, len(e), len(e))].mean() for _ in range(1000)]
    res[lab] = {'fit_coef': {t: [round(float(m1.params[t]), 3), round(float(m1.bse[t]), 3)] for t in term.split(' + ')}, 'judged_2025_26_error_reduction_kg2': round(float(e.mean()), 3),
                'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)], 'debuts_judged': int(len(te))}
OUT['debut_performance'] = res
w = te[te.mat_n > 0]; OUT['maternal_signal_where_present_2025_26'] = {'debuts': int(len(w)), 'corr_with_debut_surprise': round(float(w[['mat_sig', 'dyn_nat_inn']].corr().iloc[0, 1]), 3)}
json.dump(OUT, open('batch19/out_b19_family.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
