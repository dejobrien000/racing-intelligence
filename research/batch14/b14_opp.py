"""Batch 14 s10: do encouraging physical runs (strong last-600 speed vs the field, or an uneven last 600) show more when the NEXT race is
against weaker opposition? opp_drop = mean pre-race rating of this race's field minus that of the next race's field (kg; + = easier next time),
known before the next race. Outcome: next-run surprise (kg). Interaction terms are the test; no class-drop bonus is assumed."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, os, sys
os.environ['LEADERS_ONLY'] = '1'; sys.argv = ['x']
exec(open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0])
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct'
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'date', 'race_no', 'dyn_nat'])
V['fmean'] = V.groupby('race_id').dyn_nat.transform('mean'); V = V.sort_values(['horse', 'date', 'race_no']); V['fmean_n1'] = V.groupby('horse').fmean.shift(-1)
V['opp_drop'] = V.fmean - V.fmean_n1; V = V.rename(columns={'race_id': 'nat_race'})[['nat_race', 'horse', 'opp_drop']]
OUT = {}
for lab, d in [('QLD 2022-26', Q), ('SA 2024-26', S)]:
    d = d.merge(V, on=['nat_race', 'horse'], how='left').dropna(subset=['opp_drop', 'early_pos', 'def800c']).copy()
    d['dip'] = d.L600_avg - d.L600_min
    for v in ['L600_avg', 'dip', 'opp_drop']: d[v + '_z'] = (d[v] - d[v].mean()) / d[v].std()
    m = smf.ols('inn_n1 ~ (L600_avg_z + dip_z) * opp_drop_z + ' + CTRL, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
    OUT[lab] = {k: (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in ['L600_avg_z', 'dip_z', 'opp_drop_z', 'L600_avg_z:opp_drop_z', 'dip_z:opp_drop_z']}
    OUT[lab]['runs'] = len(d); OUT[lab]['sd opp_drop kg'] = round(d.opp_drop.std(), 2)
    print(lab, OUT[lab], flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_opp.json', 'w'), indent=1)
