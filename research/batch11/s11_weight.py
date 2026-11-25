"""Batch 11 s8: where does the light-weight effect come from? NSW/ACT starts where the NSW form line gives both the allocated weight
and the weight carried after the apprentice claim. Engine v2 chance (before v2.2's light-weight term). Horse-clustered intervals."""
import sys, duckdb, numpy as np, pandas as pd
sys.path.insert(0, 'b11'); from s11_common import base_p, ae
b = base_p(); b['nk'] = b.horse
con = duckdb.connect('../history/history.duckdb', read_only=True)
f = con.execute("select name_key nk, run_date, weight_kg alloc, claim_weight_kg carried, class from nsw_form_line where trial=false and weight_kg is not null and claim_weight_kg is not null").fetchdf()
f['meeting_date'] = pd.to_datetime(f.run_date); f = f.drop_duplicates(['nk', 'meeting_date'])
x = b.merge(f[['nk', 'meeting_date', 'alloc', 'carried', 'class']], on=['nk', 'meeting_date'], how='inner')
x['claim'] = (x.alloc - x.carried).clip(lower=0); x['claimed'] = x.claim > 0
x['hcp'] = x['class'].fillna('').str.contains('HCP|BM|Bench|Hcp', case=False); x['sw'] = ~x.hcp
x['light_c'] = x.carried <= 54; x['light_a'] = x.alloc <= 54
x['dn_rank'] = x.groupby('race_id').dyn_nat.rank(ascending=False, pct=True)
print('NSW/ACT starts matched to form lines:', len(x), '| share claimed', round(x.claimed.mean(), 3), '| races', x.race_id.nunique())
rows = []
for nm, m in [('all matched', x.index == x.index), ('carried <=54 (v2.2 rule)', x.light_c), ('carried >54', ~x.light_c),
              ('low ALLOCATED weight <=54, no claim', x.light_a & ~x.claimed), ('allocated >54 but claim takes it to <=54', ~x.light_a & x.light_c),
              ('claimed, still >54', x.claimed & ~x.light_c), ('any apprentice claim', x.claimed), ('no claim', ~x.claimed),
              ('handicaps: carried <=54', x.hcp & x.light_c), ('set-weight races: carried <=54', x.sw & x.light_c),
              ('carried <=54 & top-third rating', x.light_c & (x.dn_rank <= 1 / 3)), ('carried <=54 & bottom-third rating', x.light_c & (x.dn_rank > 2 / 3)),
              ('carried <=54, 2023-24', x.light_c & (x.meeting_date.dt.year <= 2024)), ('carried <=54, 2025-26', x.light_c & (x.meeting_date.dt.year >= 2025))]:
    rows.append({'group': nm, **ae(x[m], 'horse')})
R = pd.DataFrame(rows); print(R.to_string(index=False)); R.to_csv('b11/out_weight_ae.csv', index=False)
# basic vs complex: which weight description adds most on top of Engine v2 (fit <2025, judge 2025-26), NSW/ACT matched starts only
sys.path.insert(0, 'b10/scripts'); import lib10 as L
x['meeting_id'] = x.state + '|' + x.venue.astype(str) + '|' + x.meeting_date.dt.strftime('%Y-%m-%d')
x['light_c_f'] = x.light_c.astype(float); x['light_a_f'] = x.light_a.astype(float); x['claim_f'] = x.claim; x['claimed_f'] = x.claimed.astype(float)
x['carried_rel'] = x.carried - x.groupby('race_id').carried.transform('mean'); x['alloc_rel'] = x.alloc - x.groupby('race_id').alloc.transform('mean')
x = x[x.groupby('race_id').win.transform('sum') == 1]
out = []
for cols, lab in [(['light_c_f'], 'basic: carried <=54 kg'), (['claim_f'], 'claim kg only'), (['light_a_f'], 'allocated <=54 kg'), (['light_c_f', 'claim_f'], 'carried <=54 + claim kg'),
                  (['alloc_rel', 'claim_f'], 'allocated vs field + claim kg'), (['light_c_f', 'claim_f', 'light_a_f', 'alloc_rel'], 'complex: all four')]:
    out.append(L.test(x, cols, lab, 'validation'))
O = pd.DataFrame(out)[['label', 'races', 'gain', 'lo95', 'hi95', 'top_pick_pts', 'coef_per_sd']]; print(O.to_string(index=False)); O.to_csv('b11/out_weight_models.csv', index=False)
