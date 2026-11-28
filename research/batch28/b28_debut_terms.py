"""Batch 28 combined national candidate: historical values of the two debut terms, point-in-time, with exactly the serving definitions in
engine/v22.py (trainer_debut, sire_debut), so the release chain fits what serving computes.
  tr_debut_g    genuine debutant (first run held, aged 2-3): shrunk mean (k = 15) of its trainer's EARLIER genuine debutants' debut surprise
                minus the population running mean, from March 2023
  sire_debut_x  genuine debutant: its sire's EARLIER genuine debutants' mean debut surprise shrunk k = 30 towards the mean of all earlier such
                debuts, minus that mean (sire from the pedigree held for the horse; serving prefers TAB's pre-race form record, same name key)
Earlier = strictly earlier race dates (serving only ever sees completed days). 0 for every other runner.
Parity: re-computes a sample of dates with the serving functions themselves on history before that date.
Usage: python3 batch28/b28_debut_terms.py <frame parquet> <out parquet>"""
import sys, re, json, numpy as np, pandas as pd, duckdb
sys.path.insert(0, '.')
fin, fout = sys.argv[1:3]
nk_ = lambda s_: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s_).upper()))
F = pd.read_parquet(fin); F['date'] = pd.to_datetime(F.date)
h = F[['race_id', 'race', 'horse', 'date', 'tkey', 'age_n', 'dyn_nat_inn']].sort_values(['horse', 'date', 'race']).copy(); h['kk'] = h.groupby('horse').cumcount()
con = duckdb.connect('../history/history.duckdb', read_only=True)
P = con.execute("select name_key, sire from bn_runner where sire is not null").fetchdf(); con.close()
P['horse'] = P.name_key.map(nk_); P['sk'] = P.sire.map(nk_); smap = P.groupby('horse').sk.agg(lambda s_: s_.mode().iloc[0])
gen = (h.kk == 0) & h.age_n.isin([2, 3])
Dd = h[gen & (h.date >= pd.Timestamp('2023-03-01')) & h.dyn_nat_inn.notna() & h.tkey.notna()].copy(); Dd['sk'] = Dd.horse.map(smap)
# population running mean (serving: mean over earlier debut dates); per-day totals then strictly-earlier cumulative sums
day = Dd.groupby('date').dyn_nat_inn.agg(['sum', 'count']).sort_index(); cum = day.cumsum().shift(1)
popm = (cum['sum'] / cum['count'])                                  # trainer term: running mean before each debut day (serving 'pop')
Dd = Dd.join(popm.rename('pop'), on='date'); Dd['r'] = Dd.dyn_nat_inn - Dd['pop'].fillna(0)
T = h[gen].copy(); T['sk'] = T.horse.map(smap)
dates = np.sort(T.date.unique())
def earlier(df, key, val):
    """for each (key, date) the sum and count of val over rows with date strictly before"""
    g = df.groupby([key, 'date'])[val].agg(['sum', 'count']).reset_index().sort_values([key, 'date'])
    g[['cs', 'cn']] = g.groupby(key)[['sum', 'count']].cumsum().values
    return g[[key, 'date', 'cs', 'cn']]
# trainer: serving uses r computed with the pop of each EARLIER debut's own day (fixed once that day is done), k = 15
gt = earlier(Dd, 'tkey', 'r').sort_values('date'); T = T.sort_values('date')
T = pd.merge_asof(T, gt, on='date', by='tkey', allow_exact_matches=False); T['tr_debut_g'] = T.cs.fillna(0) / (T.cn.fillna(0) + 15.0)
T = T.drop(columns=['cs', 'cn'])
# sire: mu = mean of ALL earlier debuts (dates strictly before), k = 30
cu = day.cumsum(); allm = pd.DataFrame({'date': day.index, 'mu': (cu['sum'] / cu['count']).values})
T = pd.merge_asof(T.sort_values('date'), allm.sort_values('date'), on='date', allow_exact_matches=False)  # all debuts on earlier days
gs = earlier(Dd.dropna(subset=['sk']), 'sk', 'dyn_nat_inn').sort_values('date')
T = pd.merge_asof(T, gs, on='date', by='sk', allow_exact_matches=False); mu = T.mu.fillna(0.0)
T['sire_debut_x'] = np.where(T.sk.notna(), (T.cs.fillna(0) + 30 * mu) / (T.cn.fillna(0) + 30) - mu, 0.0)
T['sire_debut_x'] = np.where(T.mu.notna(), T.sire_debut_x, 0.0)
O = F[['race_id', 'horse']].merge(T[['race_id', 'horse', 'tr_debut_g', 'sire_debut_x']], on=['race_id', 'horse'], how='left').fillna({'tr_debut_g': 0.0, 'sire_debut_x': 0.0})
O.drop_duplicates(['race_id', 'horse']).to_parquet(fout)
# ---------- parity with the serving functions on sample dates ----------
import importlib; v22 = importlib.import_module('engine.v22')
rng = np.random.default_rng(7); samp = [pd.Timestamp(d) for d in rng.choice(dates[dates >= np.datetime64('2023-06-01')], 6, replace=False)]
par = []
for d in samp:
    H_ = F[F.date < d]; Td = F[(F.date == d)][['race_id', 'horse', 'tkey', 'age_n', 'date', 'race']].copy()
    Td['b22_n_prior'] = Td.horse.map(H_.groupby('horse').size()).fillna(0); Td['race_no'] = 0; Td['saddlecloth'] = 0
    s_t = v22.trainer_debut(Td, H_); s_s = v22.sire_debut(Td, H_)
    m = Td[['race_id', 'horse']].assign(st=s_t, ss=s_s).merge(O, on=['race_id', 'horse'])
    par.append({'date': str(d.date()), 'runners': int(len(m)), 'debut_terms_nonzero': int((m.ss != 0).sum()),
                'max_diff_trainer': float(np.abs(m.st - m.tr_debut_g).max()), 'max_diff_sire': float(np.abs(m.ss - m.sire_debut_x).max())})
print(json.dumps({'rows': int(len(O)), 'nonzero_trainer': int((O.tr_debut_g != 0).sum()), 'nonzero_sire': int((O.sire_debut_x != 0).sum()), 'parity': par}, indent=1))
