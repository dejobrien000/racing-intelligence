"""Batch 21 E13: sire debut record (and family) for first starters (research and candidate testing only; the trainer debut shadow is
untouched; nothing here is ability the horse has demonstrated).
Population and point-in-time signals as batch20/b20_family_trainer.py (exec'd unchanged up to its fit): genuine debutants aged 2-3 from
March 2023 with a pedigree; every family / sire / trainer signal uses only EARLIER horses and excludes the horse itself (shrinkage:
siblings k=3, damsire and sire k=30, trainer k=15). Added control: field strength (mean pre-race rating of the rated runners in the race).
Fit 2023-24 debuts, judge 2025-26 debuts (debut-performance error reduction, kg^2, bootstrap 95%).
  1 initial expected performance: sire, trainer, sire + trainer, maternal, damsire, all family, all family + trainer
  2 initial uncertainty: is the debut miss larger when the sire record is thin? (squared residual by sire record depth)
  3 race forecasts: harness terms sire_debut_x / tr_debut_x (non-zero only on genuine debuts) -> /tmp/cand/sire_debut.parquet
  4 by age at debut and debut distance
  5 sanity: the same sire signal on the first HELD run of horses with probably incomplete histories (not debuts) should show nothing
Usage (from research/): python3 batch21/b21_sire_debut.py"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
src = open('batch20/b20_family_trainer.py').read(); src = src[src.index("import json"):src.rindex("fit = G[G.yr <= 2024]")]
exec(src)
FS = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'dyn_nat', 'date'])
k_all = FS.sort_values(['horse', 'date', 'race']).groupby('horse').cumcount(); FS['rated'] = k_all > 0
fsd = FS[FS.rated].groupby('race').dyn_nat.mean().rename('field_strength')
G = G.join(fsd, on='race'); G['field_strength'] = G.field_strength.fillna(G.field_strength.mean())
fit = G[G.yr <= 2024]; te = G[G.yr >= 2025]
base = 'dyn_nat_inn ~ t_surp + two + female + maiden + C(dband) + fsz + C(tier) + field_strength'
rng = np.random.default_rng(13)
def judge(term, fit=fit, te=te, base=base):
    m0 = smf.ols(base, fit).fit(); m1 = smf.ols(base + ' + ' + term, fit).fit(); e = (te.dyn_nat_inn - m0.predict(te)) ** 2 - (te.dyn_nat_inn - m1.predict(te)) ** 2
    bs = [e.values[rng.integers(0, len(e), len(e))].mean() for _ in range(1000)]
    return {'debuts_judged': int(e.notna().sum()), 'error_reduction_kg2': round(float(e.mean()), 3), 'ci95': [round(float(np.percentile(bs, 2.5)), 3), round(float(np.percentile(bs, 97.5)), 3)],
            'coef': {t: round(float(m1.params[t]), 3) for t in term.replace(':', ' + ').split(' + ') if t in m1.params}}
OUT = {'debuts_fit': int(len(fit)), 'debuts_judged': int(len(te)), 'base': base}
OUT['1 initial expected performance'] = {lab: judge(t) for lab, t in [('sire', 'sire_sig'), ('trainer', 'debut_rec'), ('sire + trainer', 'sire_sig + debut_rec'), ('maternal siblings', 'mat_sig'),
                                                                       ('damsire', 'ds_sig'), ('all family', 'mat_sig + full_sig + ds_sig + sire_sig'), ('all family + trainer', 'mat_sig + full_sig + ds_sig + sire_sig + debut_rec')]}
# 2 uncertainty: squared residual of the sire + trainer model by sire record depth (judged debuts)
m = smf.ols(base + ' + sire_sig + debut_rec', fit).fit(); te = te.assign(res2=(te.dyn_nat_inn - m.predict(te)) ** 2, depth=pd.cut(te.scn.fillna(0), [-1, 9, 49, 199, 1e9], labels=['0-9 earlier debutants', '10-49', '50-199', '200+']).astype(str))
OUT['2 debut miss (squared, kg^2) by sire record depth'] = {k: {'debuts': int(len(g)), 'mean_sq_miss': round(float(g.res2.mean()), 2)} for k, g in te.groupby('depth')}
# 4 by age and debut distance (sire term only, same fit; judged within each group)
OUT['4 sire term by group'] = {}
for col in ['two', 'dband']:
    for k, g in te.groupby(col):
        if len(g) >= 500: OUT['4 sire term by group'][f'{col}={k}'] = judge('sire_sig', te=g)
# 5 sanity: first held run of probably-incomplete horses (aged 4+ at first held run or held from the start of our data)
first = U[U.k == 0].set_index('horse'); notdeb = first[(first.age_n >= 4) | (first.date < '2023-03-01')].index
N = U[(U.k == 0) & U.horse.isin(notdeb) & U.dyn_nat_inn.notna()].join(H[['sire']], on='horse').dropna(subset=['sire']).sort_values('date')
N = pd.merge_asof(N, pit(ALL.dropna(subset=['sire']), 'sire', 'dyn_nat_inn', 30).rename(columns={'cs': 'scs', 'cn': 'scn'}), on='date', by='sire', allow_exact_matches=False)
N['sire_sig'] = (N.scs.fillna(0) + 30 * mu) / (N.scn.fillna(0) + 30) - mu
mN = smf.ols('dyn_nat_inn ~ sire_sig', N).fit(cov_type='HC1'); OUT['5 sanity: first held run, not a debut'] = {'runs': int(mN.nobs), 'sire_coef': [round(float(mN.params['sire_sig']), 3)] + [round(float(x), 3) for x in mN.conf_int().loc['sire_sig']]}
OUT['5 for comparison: genuine debuts'] = {'coef': round(float(smf.ols('dyn_nat_inn ~ sire_sig', G).fit().params['sire_sig']), 3)}
# 3 harness terms
G[['race', 'horse', 'sire_sig', 'debut_rec']].rename(columns={'sire_sig': 'sire_debut_x', 'debut_rec': 'tr_debut_x'}).to_parquet('/tmp/cand/sire_debut_race.parquet')
json.dump(OUT, open('batch21/out_b21_sire_debut.json', 'w'), indent=1); print(json.dumps(OUT, indent=1)[:6000])
