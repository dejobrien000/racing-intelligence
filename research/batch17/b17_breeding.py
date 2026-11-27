"""Batch 17 D19/D20 preliminary: breeding as a prior (research only; point in time; no prices).
Pedigree from Breednet runner records (sire, dam, damsire per horse). For each run, the SIRE's progeny record up to the day before the
race (never later runs, never the horse itself): how much better its progeny run (surprise, kg) at today's distance band and going band
than their usual, shrunk towards zero (k = 300 progeny runs). Test: does it predict this run's surprise, and does its value fall as the
horse's OWN relevant evidence (runs at that distance band / going band) accumulates?
Maturity: within-horse rating change from the last run aged 3 to the last run aged 4, averaged by sire; repeatable across progeny
cohorts (foal-year parity)? Per Incanto shown as the owner's example, treated as a hypothesis.
Usage (from research/): python3 batch17/b17_breeding.py -> batch17/out_b17_breeding.json"""
import re, json, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
con = duckdb.connect('../history/history.duckdb', read_only=True)
P = con.execute("select name_key, sire, dam, damsire from bn_runner where sire is not null").fetchdf(); P['horse'] = P.name_key.map(nk)
P = P.groupby('horse').agg(sire=('sire', lambda s: s.mode().iloc[0]), dam=('dam', lambda s: s.mode().iloc[0]), damsire=('damsire', lambda s: s.mode().iloc[0]), nsire=('sire', 'nunique'))
P = P[P.nsire == 1]                                   # names with conflicting sires (two horses, one name) are dropped, not guessed
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'distance_m', 'gband', 'dyn_nat', 'dyn_nat_inn', 'age_n'])
U = U.merge(P[['sire', 'dam', 'damsire']], left_on='horse', right_index=True, how='left')
OUT = {'coverage': {'runs': int(len(U)), 'with_sire': round(float(U.sire.notna().mean()), 3), 'horses_with_pedigree': int(len(P)), 'sires': int(P.sire.nunique()), 'dams': int(P.dam.nunique())}}
U = U[U.sire.notna() & U.dyn_nat_inn.notna()].sort_values(['date', 'race']).reset_index(drop=True)
U['db'] = pd.cut(U.distance_m, [0, 1150, 1450, 1750, 9999], labels=['sprint', 'short-mid', 'mile', 'staying']).astype(str); U['gb'] = np.where(U.gband.isin(['soft', 'heavy']), 'wet', 'dry')
K = 300.0
def prior(keycols, tag):
    """point-in-time progeny mean surprise in this cell minus the sire's overall progeny mean, shrunk; earlier DATES only"""
    d = U[['date'] + keycols + ['dyn_nat_inn']].copy(); d['one'] = 1.0
    def cum(cols):
        g = d.groupby(cols + ['date'], sort=False)[['dyn_nat_inn', 'one']].sum().reset_index().sort_values(cols + ['date'])
        g[['s', 'n']] = g.groupby(cols)[['dyn_nat_inn', 'one']].cumsum().values - g[['dyn_nat_inn', 'one']].values
        return d.merge(g[cols + ['date', 's', 'n']], on=cols + ['date'], how='left')
    d['horse'] = U.horse.values
    cell = cum(keycols); base = cum(keycols[:1]); hc = cum(['horse'] + keycols[1:]); hb = cum(['horse'])   # the horse's own earlier runs are taken OUT of its sire's record
    cs, cn = cell.s - hc.s.fillna(0), cell.n - hc.n.fillna(0); bs, bn = base.s - hb.s.fillna(0), base.n - hb.n.fillna(0)
    m_cell = cs / (cn + K); m_base = bs / (bn + K)
    U[tag] = (m_cell - m_base).values; U[tag + '_n'] = cn.values
prior(['sire', 'db'], 'sire_dist'); prior(['sire', 'gb'], 'sire_going')
# the horse's own evidence in that cell before this run
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U['own_dist_n'] = U.groupby(['horse', 'db']).cumcount(); U['own_going_n'] = U.groupby(['horse', 'gb']).cumcount(); U['own_n'] = U.groupby('horse').cumcount()
E = U[(U.date >= '2024-01-01')].copy(); E['sd_z'] = E.sire_dist / E.sire_dist.std(); E['sg_z'] = E.sire_going / E.sire_going.std()
def fitg(d, var):
    m = smf.ols(f'dyn_nat_inn ~ {var}', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    return [int(m.nobs), round(float(m.params[var]), 3), round(float(m.conf_int().loc[var, 0]), 3), round(float(m.conf_int().loc[var, 1]), 3)]
OUT['sire_distance_prior_kg_per_sd_by_own_runs_at_that_distance'] = {lab: fitg(E[sel], 'sd_z') for lab, sel in [('0', E.own_dist_n == 0), ('1-2', E.own_dist_n.between(1, 2)), ('3-5', E.own_dist_n.between(3, 5)), ('6+', E.own_dist_n >= 6)]}
OUT['sire_going_prior_kg_per_sd_by_own_runs_on_that_going'] = {lab: fitg(E[sel & (E.gb == 'wet')], 'sg_z') for lab, sel in [('0', E.own_going_n == 0), ('1-2', E.own_going_n.between(1, 2)), ('3+', E.own_going_n >= 3)]}
OUT['sire_distance_prior_first_three_career_runs'] = fitg(E[E.own_n <= 2], 'sd_z')
# maturity: rating change from the last run at age 3 to the last run at age 4, by sire, cohort split by birth-year parity
A = U[U.age_n.isin([3, 4])].sort_values(['horse', 'date']).groupby(['horse', 'age_n']).agg(r=('dyn_nat', 'last'), date=('date', 'last'), sire=('sire', 'first')).reset_index()
W = A.pivot_table(index=['horse', 'sire'], columns='age_n', values='r').dropna().reset_index(); W.columns = ['horse', 'sire', 'r3', 'r4']; W['d'] = W.r4 - W.r3
yr = A[A.age_n == 4].set_index('horse').date.dt.year; W['cohort_odd'] = W.horse.map(yr) % 2
S = W.groupby(['sire', 'cohort_odd']).d.agg(['mean', 'count']).unstack()
S = S[(S[('count', 0)] >= 15) & (S[('count', 1)] >= 15)]
OUT['maturity_3_to_4'] = {'horses': int(len(W)), 'mean_change_kg': round(float(W.d.mean()), 2), 'sires_with_15_plus_each_cohort': int(len(S)),
                          'cohort_split_corr_of_sire_means': round(float(np.corrcoef(S[('mean', 0)], S[('mean', 1)])[0, 1]), 3) if len(S) >= 5 else None}
sm = W.groupby('sire').d.agg(['mean', 'count', 'std']); sm['se'] = sm['std'] / np.sqrt(sm['count']); sm['shrunk'] = sm['mean'] * sm['count'] / (sm['count'] + 30) + W.d.mean() * 30 / (sm['count'] + 30)
pi = sm[sm.index.str.contains('Per Incanto', case=False)]
OUT['per_incanto_example'] = {k: (round(float(v), 2) if isinstance(v, (float, np.floating)) else int(v)) for k, v in pi.iloc[0].items()} if len(pi) else None
OUT['sire_maturity_top_and_bottom_shrunk'] = {'top': sm[sm['count'] >= 40].sort_values('shrunk', ascending=False).head(5).round(2).reset_index().to_dict('records'),
                                              'bottom': sm[sm['count'] >= 40].sort_values('shrunk').head(5).round(2).reset_index().to_dict('records')}
json.dump(OUT, open('batch17/out_b17_breeding.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=0, default=str)[:4000])
