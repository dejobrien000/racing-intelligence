"""Batch 20 F13: trainer early improvement at the 2nd and 3rd career starts (research and candidate testing only; no production change;
the frozen trainer debut shadow is untouched). Observable patterns only: nothing here measures deliberate trainer policy.
Population: genuine debutants (first run held aged 2-3, from March 2023, and no earlier Australian TAB start in the Betfair runner list).
Target: the surprise at the horse's 2nd and 3rd starts (performance beyond what its rating already expected, kg; dyn_nat_inn).
Trainer records, point in time (only horses whose runs were completed on EARLIER dates; shrunk towards the mean with k = 15 horses):
  early_rec  mean surprise of the trainer's earlier horses at their 2nd/3rd starts
  debut_rec  mean debut surprise of the trainer's earlier debutants (same definition as the trainer debut shadow)
  t_surp     the trainer's general surprise record already in the frame (all runs)
Controls: age, female, the horse's own debut surprise (initial quality / regression), class step from the previous run, trainer change since
debut, a spell before the run (60+ days: first-preparation vs between-preparation development), start number, the trainer's earlier
continuation rate (share of its debutants that had a 2nd start: selective continuation). Cluster-robust by trainer.
Outputs: batch20/out_b20_trainer_early.json; /tmp/cand/tr_early.parquet (race_id, horse, tr_early_x) for the harness test.
Usage (from research/): python3 batch20/b20_trainer_early.py"""
import json, numpy as np, pandas as pd, statsmodels.formula.api as smf
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'date', 'tkey', 'dyn_nat_inn', 'age_n', 'female', 'class_label', 'r_debut', 't_surp', 'state'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
f0 = U[U.k == 0].set_index('horse'); gen = f0[f0.age_n.isin([2, 3]) & (f0.date >= '2023-03-01') & (f0.r_debut == 1) & f0.tkey.notna()].index
V = U[U.horse.isin(gen) & (U.k <= 2)].copy(); V['gap'] = V.groupby('horse').date.diff().dt.days
V['debut_tkey'] = V.groupby('horse').tkey.transform('first'); V['debut_surp'] = V.groupby('horse').dyn_nat_inn.transform('first')
CL = {'Maiden': 0, 'Class': 1, 'Restricted': 1, 'BM': 2, 'Benchmark': 2, 'Other': 2, 'Open/Hcp': 3, 'Open': 3, 'Listed': 4, 'Group': 5}
V['cl'] = V.class_label.map(CL); V['class_step'] = V.groupby('horse').cl.diff()
mu_e = V[V.k.isin([1, 2])].dyn_nat_inn.mean(); mu_d = V[V.k == 0].dyn_nat_inn.mean(); K = 15
def pit(ev, val, mu, name):   # point-in-time shrunk trainer mean from events on strictly earlier dates
    d = ev.groupby(['tkey', 'date'])[val].agg(['sum', 'count']).reset_index().sort_values(['tkey', 'date'])
    d['cs'] = d.groupby('tkey')['sum'].cumsum() - d['sum']; d['cn'] = d.groupby('tkey')['count'].cumsum() - d['count']
    d[name] = (d.cs + K * mu) / (d.cn + K); d[name + '_n'] = d.cn; return d[['tkey', 'date', name, name + '_n']]
E2 = V[V.k.isin([1, 2]) & V.dyn_nat_inn.notna()].assign(tkey=lambda x: x.debut_tkey)   # credited to the trainer who started the horse
D0 = V[(V.k == 0) & V.dyn_nat_inn.notna()]
# continuation: debutants whose 2nd start happened; counted at the debut date + 120 days (known by then), never earlier
C = V[V.k == 0][['horse', 'tkey', 'date']].merge(V[V.k == 1][['horse']].assign(cont=1.0), on='horse', how='left').fillna({'cont': 0.0}); C['date'] = C.date + pd.Timedelta(days=120)
def asof(T, R, name):   # attach the latest record dated before each run (merge_asof needs global date order)
    R = R.sort_values('date'); T = T.sort_values('date')
    return pd.merge_asof(T, R, on='date', by='tkey', allow_exact_matches=False, direction='backward')
T = V[V.k.isin([1, 2])].copy(); T['tkey'] = T.debut_tkey
T = asof(T, pit(E2, 'dyn_nat_inn', mu_e, 'early_rec'), 'early_rec'); T = asof(T, pit(D0, 'dyn_nat_inn', mu_d, 'debut_rec'), 'debut_rec')
T = asof(T, pit(C, 'cont', C.cont.mean(), 'cont_rec'), 'cont_rec')
T['early_rec'] = T.early_rec.fillna(mu_e); T['debut_rec'] = T.debut_rec.fillna(mu_d); T['cont_rec'] = T.cont_rec.fillna(C.cont.mean())
T['early_rec_n'] = T.early_rec_n.fillna(0); T['trainer_change'] = (T.tkey_x if 'tkey_x' in T else T.tkey) != T.debut_tkey
T['spell'] = (T.gap >= 60).astype(float); T['start3'] = (T.k == 2).astype(float); T['win'] = np.where(T.date < '2025-01-01', '2024 and before', '2025-26')
T = T[T.dyn_nat_inn.notna() & (T.date >= '2024-01-01')].copy(); T['female'] = T.female.astype(float); T['age3'] = (T.age_n >= 3).astype(float)
# trainer change needs the run's own trainer
own = U[['race', 'horse', 'tkey']].rename(columns={'tkey': 'run_tkey'}); T = T.merge(own, on=['race', 'horse'], how='left'); T['trainer_change'] = (T.run_tkey != T.debut_tkey).astype(float)
OUT = {'population': {'genuine_debutants': int(len(gen)), 'runs_2nd_3rd_judged_2024_on': int(len(T)), 'trainers': int(T.debut_tkey.nunique())}}
for c in ['early_rec', 'debut_rec', 't_surp']: T[c + '_z'] = (T[c] - T[c].mean()) / T[c].std()
OUT['record_sd_kg'] = {c: round(float(T[c].std()), 3) for c in ['early_rec', 'debut_rec', 't_surp']}
OUT['record_correlations'] = T[['early_rec', 'debut_rec', 't_surp', 'cont_rec']].corr().round(3).to_dict()
fm = {'early record alone': 'dyn_nat_inn ~ early_rec', 'with general and debut records': 'dyn_nat_inn ~ early_rec + debut_rec + t_surp',
      'with all controls': 'dyn_nat_inn ~ early_rec + debut_rec + t_surp + age3 + female + debut_surp + class_step + trainer_change + spell + start3 + cont_rec'}
OUT['models'] = {}
VARS = ['dyn_nat_inn', 'early_rec', 'debut_rec', 't_surp', 'age3', 'female', 'debut_surp', 'class_step', 'trainer_change', 'spell', 'start3', 'cont_rec']
def fit(f, d):
    used = [v for v in VARS if v in f.replace('~', ' ').replace('+', ' ').split()]; d = d.dropna(subset=used)
    return smf.ols(f, d).fit(cov_type='cluster', cov_kwds={'groups': d.debut_tkey.astype('category').cat.codes})
for w, g in [('all', T)] + list(T.groupby('win')):
    for lab, f in fm.items():
        m = fit(f, g)
        OUT['models'][f'{w} | {lab}'] = {'runs': int(m.nobs), **{v: {'coef': round(float(m.params[v]), 3), 'ci95': [round(float(x), 3) for x in m.conf_int().loc[v]]} for v in m.params.index if v != 'Intercept'}}
# first-preparation vs after a spell, and 2nd vs 3rd start
for lab, d in [('within first preparation', T[T.spell == 0]), ('after a spell', T[T.spell == 1]), ('2nd start', T[T.k == 1]), ('3rd start', T[T.k == 2])]:
    m = fit(fm['with all controls'].replace(' + spell', '' if 'spell' in lab or 'preparation' in lab else ' + spell').replace(' + start3', '' if 'start' in lab else ' + start3'), d)
    OUT['models'][f'subgroup | {lab}'] = {'runs': int(m.nobs), 'early_rec': {'coef': round(float(m.params['early_rec']), 3), 'ci95': [round(float(x), 3) for x in m.conf_int().loc['early_rec']]}}
# well-supported records only (20+ earlier early starts)
d = T[T.early_rec_n >= 20]; m = fit(fm['with all controls'], d)
OUT['models']['subgroup | trainer record on 20+ earlier starts'] = {'runs': int(m.nobs), 'early_rec': {'coef': round(float(m.params['early_rec']), 3), 'ci95': [round(float(x), 3) for x in m.conf_int().loc['early_rec']]}}
# harness term: the early record (relative to its mean) at a genuine debutant's 2nd/3rd start, 0 elsewhere; point in time for every run since 2022
A = V[V.k.isin([1, 2])].copy(); A['tkey'] = A.debut_tkey; A = asof(A, pit(E2, 'dyn_nat_inn', mu_e, 'early_rec'), 'early_rec'); A['tr_early_x'] = (A.early_rec.fillna(mu_e) - mu_e)
A[['race_id', 'horse', 'tr_early_x']].drop_duplicates(['race_id', 'horse']).to_parquet('/tmp/cand/tr_early.parquet')
json.dump(OUT, open('batch20/out_b20_trainer_early.json', 'w'), indent=1)
for k, v in OUT['models'].items(): print(k, v['runs'], v.get('early_rec'))
print(OUT['record_correlations']['early_rec'])
