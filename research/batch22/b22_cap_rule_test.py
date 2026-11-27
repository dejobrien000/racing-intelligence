"""Batch 22 A3: does a cap on inferred career starts improve experience estimation? (validation only; truth sources are never inputs)
Candidate rules for runs labelled 'probably incomplete' (all other labels keep their observed counts; verified TAB counts always win):
  R0 current: observed + typical starts at the age of the first known start (Batch 21 v3)
  R1 plausibility cap: R0, but never above the 75th percentile of starts reached BY THE AGE AT THIS RUN among complete-history horses
     (fitted on runs before 2024) - age as an upper plausibility bound, not a count
  R2 observed only (no inference)
  R3 half the typical starts added
Truth used to score (never an input): NSW form-line careers (horses whose NSW form starts 2019 or later, trials excluded) at each run;
the 26-27 Nov TAB career counts are too few for the probably-incomplete group (12) and are reported only in Batch 21.
Scored on the number itself and on the quantity the rating actually uses, the response multiplier m = 1 + a exp(-n/6)
(a = 0.3 history-completeness rule; a = 0.8 stronger rule). Groups: left-censored (first known start before Jul 2020), imported or
older debut outside a maiden (first known later, aged 5+), plus the other labels for reference.
Usage (from research/): python3 batch22/b22_cap_rule_test.py"""
import re, json, duckdb, numpy as np, pandas as pd
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
con = duckdb.connect('../history/history.duckdb', read_only=True)
E = pd.read_parquet('/tmp/cand/experience_b21.parquet')
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'date', 'age_n']).rename(columns={'race': 'race_key'})
E = E.merge(F, on=['race_key', 'horse'])
bf = con.execute("select distinct meeting_date, name_key from bf_runner where state <> 'NZ'").fetchdf(); bf['horse'] = bf.name_key.map(nk); bf['date'] = pd.to_datetime(bf.meeting_date)
fk = pd.concat([bf[['horse', 'date']], F[['horse', 'date']]]).groupby('horse').date.min().rename('first_known')
E = E.join(fk, on='horse')
E['grp'] = np.where(E.source != 'probable_incomplete', E.source, np.where(E.first_known < pd.Timestamp('2020-07-01'), 'probably incomplete: left-censored', 'probably incomplete: import / older non-maiden'))
# complete-history reference (before 2024): starts reached by age, median and 75th percentile
C = E[(E.source == 'complete') & (E.date < pd.Timestamp('2024-01-01'))]
p75 = C.groupby(C.age_n.clip(2, 9))['observed'].quantile(0.75)
for a in range(2, 13): p75.loc[a] = p75.get(a, p75[p75.index <= a].iloc[-1])
p75 = p75.sort_index().cummax()
cap = E.age_n.clip(2, 12).map(p75).fillna(np.inf)   # no age -> no cap
pi = E.source == 'probable_incomplete'
E['R0'] = E.n_eff; E['R1'] = np.where(pi, np.minimum(E.n_eff, np.maximum(cap, E.observed)), E.n_eff)
E['R2'] = np.where(pi, E.observed, E.n_eff); E['R3'] = np.where(pi, E.observed + 0.5 * E.inferred_added, E.n_eff)
# truth: NSW form-line counts before the run, horses whose NSW form starts 2019+
L = con.execute("select name_key, run_date, trial from nsw_form_line").fetchdf(); L = L[~L.trial.fillna(False).astype(bool)]
L['horse'] = L.name_key.map(nk); L['date'] = pd.to_datetime(L.run_date); L = L.drop_duplicates(['horse', 'date']).sort_values(['horse', 'date'])
first = L.groupby('horse').date.min(); ok = set(first[first >= pd.Timestamp('2019-01-01')].index)
V = E[E.horse.isin(ok)].copy(); arr = L[L.horse.isin(ok)].groupby('horse').date.apply(np.array).to_dict()
V['truth'] = [int((arr[h] < d).sum()) for h, d in zip(V.horse, V.date)]
m = lambda n, a: 1 + a * np.exp(-np.asarray(n, float) / 6)
OUT = {'p75_starts_by_age_cap': {int(k): float(v) for k, v in p75.items()}, 'validation_runs': int(len(V)), 'validation_horses': int(V.horse.nunique())}
for g, x in V.groupby('grp'):
    o = {'runs': int(len(x)), 'horses': int(x.horse.nunique())}
    for r in ['R0', 'R1', 'R2', 'R3']:
        d = x[r] - x.truth
        o[r] = {'median_diff': float(d.median()), 'mean_abs_diff': round(float(d.abs().mean()), 2), 'over_by_5plus': round(float((d >= 5).mean()), 3), 'under_by_5plus': round(float((d <= -5).mean()), 3),
                'mean_abs_m_error_gentle': round(float(np.abs(m(x[r], 0.3) - m(x.truth, 0.3)).mean()), 4), 'mean_abs_m_error_strong': round(float(np.abs(m(x[r], 0.8) - m(x.truth, 0.8)).mean()), 4)}
    OUT[g] = o
OUT['runs_whose_value_the_cap_changes'] = {g: int(((x.R1 != x.R0)).sum()) for g, x in E.groupby('grp')}
json.dump(OUT, open('batch22/out_b22_cap_rule_test.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
