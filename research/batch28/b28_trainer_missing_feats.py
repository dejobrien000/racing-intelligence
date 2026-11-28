"""Batch 28 item 12: trainer transfer (normalised) and the missing-career initial expectation, on the consolidated rating (research only).
Trainer keys are already 'initial surname' lower case; a change counts as a GENUINE transfer only when the old and new keys share no
surname word (so 'c maher' -> 'c maher & d eustace', partnerships and spelling variants are not transfers).
  tr_new1    first run for a new trainer (genuine transfer; previous trainer known)
  tr_new2_5  2nd-5th run for that new trainer
  miss_first first run we hold for a horse whose history is NOT complete (experience file 'probable_incomplete' or 'late_maiden'),
             i.e. it has raced (or is old enough to have) before our records start; genuine debutants are excluded (they are 'complete')
Also a descriptive table: mean surprise (innovation) for each group, by period. Then the harness tests (cand_eval EXTRA).
Usage: python3 batch28/b28_trainer_missing_feats.py <frame> <feat in> <feat out> <json out>"""
import sys, re, json, numpy as np, pandas as pd
fin, featin, featout, jout = sys.argv[1:5]
F = pd.read_parquet(fin, columns=['race_id', 'race', 'horse', 'date', 'tkey', 'dyn_nat_inn', 'age_n']); F['date'] = pd.to_datetime(F.date)
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'source']).rename(columns={'race_key': 'race'})
F = F.merge(E, on=['race', 'horse'], how='left').sort_values(['horse', 'date', 'race']).reset_index(drop=True)
g = F.groupby('horse'); F['k'] = g.cumcount(); F['ptk'] = g.tkey.shift()
sur = lambda t: set(w for w in re.split(r'[^a-z]+', str(t).lower()) if len(w) > 1)
chg = F.tkey.notna() & F.ptk.notna() & (F.tkey != F.ptk)
F['genuine'] = False; F.loc[chg, 'genuine'] = [len(sur(a) & sur(b)) == 0 for a, b in zip(F.loc[chg, 'tkey'], F.loc[chg, 'ptk'])]
F['spell_id'] = F.genuine.astype(int).groupby(F.horse).cumsum()            # trainer stint since the last genuine transfer
F['stint_run'] = F.groupby(['horse', 'spell_id']).cumcount() + 1
F['tr_new1'] = (F.genuine).astype(float); F['tr_new2_5'] = ((F.spell_id > 0) & F.stint_run.between(2, 5)).astype(float)
F['miss_first'] = ((F.k == 0) & F.source.isin(['probable_incomplete', 'late_maiden'])).astype(float)
OUT = {'changes_all': int(chg.sum()), 'changes_genuine': int(F.genuine.sum()), 'changes_variant_or_partnership': int((chg & ~F.genuine).sum()), 'by_period': {}}
F['per'] = np.where(F.date < '2024-01-01', 'to_2023', np.where(F.date < '2025-01-01', '2024', '2025_26'))
for p_, d in F[F.dyn_nat_inn.notna()].groupby('per'):
    OUT['by_period'][p_] = {lab: [int(m.sum()), round(float(d.dyn_nat_inn[m].mean()), 3)] for lab, m in
                            [('genuine transfer, first run', d.tr_new1 == 1), ('variant/partnership change, first run', (d.tkey != d.ptk) & d.ptk.notna() & (d.tr_new1 == 0)),
                             ('2nd-5th run with new trainer', d.tr_new2_5 == 1), ('first held run, history incomplete', d.miss_first == 1),
                             ('first held run, genuine debutant (complete, 2-3yo)', (d.k == 0) & (d.source == 'complete') & d.age_n.isin([2, 3])), ('all runs', d.k >= 0)]}
X = pd.read_parquet(featin).merge(F[['race_id', 'horse', 'tr_new1', 'tr_new2_5', 'miss_first']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
X[['tr_new1', 'tr_new2_5', 'miss_first']] = X[['tr_new1', 'tr_new2_5', 'miss_first']].fillna(0.0); X.to_parquet(featout)
json.dump(OUT, open(jout, 'w'), indent=1); print(json.dumps(OUT, indent=1))
