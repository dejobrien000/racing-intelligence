"""Batch 28 item 10: connected form lines / entire-field underestimation (research only; no hindsight).
For a runner today (date t): its LAST race R (date d < t). Its rivals in R have run again since; their surprises in those later runs
(innovations against their own ratings, runs strictly after d and strictly before t) say whether R's field was underrated when R was rated.
  fl_since = sum of those innovations over all rivals' later runs / (number of such runs + 5)      (kg; + = R's field since ran above its ratings)
  fl_n     = number of such runs
Everything used is completed before today's race. Then the harness (consolidated engine, mode R, windows A/B) tests fl_since as one
third-layer term, and a descriptive check of whether fl_since predicts today's surprise beyond the rating.
Usage: python3 batch28/b28_form_lines.py <frame> <feat in> <feat out> <json out>"""
import sys, json, numpy as np, pandas as pd
fin, featin, featout, jout = sys.argv[1:5]
F = pd.read_parquet(fin, columns=['race_id', 'race', 'horse', 'date', 'dyn_nat_inn', 'state']); F['date'] = pd.to_datetime(F.date)
F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
F['prev_race'] = F.groupby('horse').race.shift(); F['prev_date'] = F.groupby('horse').date.shift()
# per-horse cumulative innovations including each run
F['i0'] = F.dyn_nat_inn.fillna(0.0); F['c0'] = F.dyn_nat_inn.notna().astype(float)
F['cs'] = F.groupby('horse').i0.cumsum(); F['cn'] = F.groupby('horse').c0.cumsum()
C = F[['horse', 'date', 'cs', 'cn']].copy()
# pairs: today's row i x rivals j in i's previous race
Q = F.loc[F.prev_race.notna(), ['race_id', 'horse', 'date', 'prev_race', 'prev_date']].reset_index(drop=True); Q['qi'] = np.arange(len(Q))
Rv = F[['race', 'horse']].rename(columns={'race': 'prev_race', 'horse': 'rival'})
P = Q.merge(Rv, on='prev_race'); P = P[P.rival != P.horse][['qi', 'date', 'prev_date', 'rival']]
print('pairs', len(P), flush=True)
Cr = C.rename(columns={'horse': 'rival'})
P = P.sort_values('date'); a = pd.merge_asof(P, Cr.sort_values('date'), on='date', by='rival', allow_exact_matches=False)          # before today
P2 = a.rename(columns={'cs': 'cs_t', 'cn': 'cn_t'}).sort_values('prev_date')
b = pd.merge_asof(P2, Cr.rename(columns={'date': 'prev_date'}).sort_values('prev_date'), on='prev_date', by='rival', allow_exact_matches=True)  # up to and incl. R's day
b['s'] = (b.cs_t - b.cs).clip(lower=None).fillna(0.0); b['n'] = (b.cn_t - b.cn).fillna(0.0)
b.loc[b.n <= 0, ['s', 'n']] = 0.0
G = b.groupby('qi')[['s', 'n']].sum()
Q = Q.join(G, on='qi'); Q[['s', 'n']] = Q[['s', 'n']].fillna(0.0)
Q['fl_since'] = Q.s / (Q.n + 5.0); Q['fl_n'] = Q.n
FL = Q[['race_id', 'horse', 'fl_since', 'fl_n']].drop_duplicates(['race_id', 'horse'])
X = pd.read_parquet(featin).merge(FL, on=['race_id', 'horse'], how='left'); X[['fl_since', 'fl_n']] = X[['fl_since', 'fl_n']].fillna(0.0)
X.to_parquet(featout)
# descriptive: does fl_since predict today's surprise (innovation) beyond the rating? (the innovation already nets out the rating)
D = F[['race_id', 'horse', 'date', 'dyn_nat_inn', 'state']].merge(FL, on=['race_id', 'horse'], how='left').dropna(subset=['dyn_nat_inn', 'fl_since'])
OUT = {'definition': __doc__.split('Everything')[0].strip(), 'rows_with_value': int((FL.fl_n > 0).sum()), 'rows': int(len(FL)),
       'fl_since_sd': round(float(FL.fl_since[FL.fl_n > 0].std()), 3), 'by_period': {}}
for lab, m in [('to_2023', D.date < '2024-01-01'), ('2024', (D.date >= '2024-01-01') & (D.date < '2025-01-01')), ('2025_26', D.date >= '2025-01-01')]:
    d = D[m & (D.fl_n >= 3)]; c = np.polyfit(d.fl_since, d.dyn_nat_inn, 1)
    q = pd.qcut(d.fl_since, 5, labels=False, duplicates='drop'); OUT['by_period'][lab] = {'runs': int(len(d)), 'slope_kg_per_kg': round(float(c[0]), 3),
        'mean_surprise_by_fifth': [round(float(v), 3) for v in d.groupby(q).dyn_nat_inn.mean().values]}
json.dump(OUT, open(jout, 'w'), indent=1); print(json.dumps(OUT, indent=1))
