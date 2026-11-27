"""Batch 20 C7: race-layer refinement inputs (research only). For one rating frame, adds to a copy of its harness features:
  rel          the horse's rating minus its field's mean rating (kg), from the same frame
  light_share  share of the field with 5 or fewer runs held (field-wide inexperience; NOT the maiden label)
  fsd          the field's mean rating uncertainty (kg; dyn_nat_sd)
  rel_x_light  rel x light_share   -> do rating differences carry less information in inexperienced fields?
  rel_x_fsd    rel x fsd           -> ... in fields whose ratings are uncertain overall?
  rel_x_osd    rel x the horse's own rating uncertainty -> ... for an individually uncertain horse?
The harness race-centres and scales every term, so these act as field-dependent weights on the rating; the ratings are never changed.
Usage: python3 batch20/b20_race_layer_feats.py <frame.parquet> <base feat.parquet> <out feat.parquet>"""
import sys, numpy as np, pandas as pd
FR, BASE, OUTF = sys.argv[1:4]
F = pd.read_parquet(FR, columns=['race_id', 'horse', 'date', 'race', 'dyn_nat', 'dyn_nat_sd']).sort_values(['horse', 'date', 'race'])
F['k'] = F.groupby('horse').cumcount()
g = F.groupby('race_id')
F['rel'] = F.dyn_nat - g.dyn_nat.transform('mean'); F['light_share'] = g.k.transform(lambda s: float((s <= 5).mean()))
F['fsd'] = g.dyn_nat_sd.transform('mean')
F['rel_x_light'] = F.rel * F.light_share; F['rel_x_fsd'] = F.rel * F.fsd; F['rel_x_osd'] = F.rel * F.dyn_nat_sd
X = pd.read_parquet(BASE)
X = X.drop(columns=[c for c in ['rel', 'light_share', 'fsd', 'rel_x_light', 'rel_x_fsd', 'rel_x_osd'] if c in X]).merge(F[['race_id', 'horse', 'light_share', 'fsd', 'rel_x_light', 'rel_x_fsd', 'rel_x_osd']].drop_duplicates(['race_id', 'horse']), on=['race_id', 'horse'], how='left')
X.to_parquet(OUTF); print(OUTF, len(X), 'light_share mean', round(float(X.light_share.mean()), 3))
