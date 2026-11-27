"""Batch 19 B6: is it age or experience? (research only; no prices). Among horses whose WHOLE career is in our data (first run held a genuine
debut: aged 2-3, from March 2023), runs held = true career starts, so age and experience can be separated. For good runs (surprise >= 2 kg),
the share of the gain kept over the next 1 / 3 starts by age x career starts. Compared with horses whose careers began before our data.
Also the TAB form records (26-27 Nov 2026, as-at race morning) show how often a horse aged 5+ with few runs held is genuinely lightly raced.
Usage (from research/): python3 batch19/b19_age_vs_experience.py -> batch19/out_b19_age_vs_experience.json"""
import json, numpy as np, pandas as pd
src = open('batch18/b18_sustainability.py').read(); src = src[:src.index('OUT = {')]; exec(src)
first = U.groupby('horse').date.transform('min'); age1 = U.groupby('horse').age_n.transform('first')
U['complete'] = (first >= '2023-03-01') & age1.isin([2, 3]); E = E.join(U[['complete']])
E['starts'] = pd.cut(E.k, [0, 2, 5, 11, 999], labels=['1-2', '3-5', '6-11', '12+']).astype(str)
E['age'] = pd.cut(E.age_n, [0, 3, 4, 5, 99], labels=['2-3', '4', '5', '6+']).astype(str)
def cell(x):
    o = {'runs': int(len(x))}
    for c, lab in [('p1', 'next'), ('m3', 'next3')]:
        y = x[x[c].notna()]
        if len(y) >= 50: o[lab] = round(float(((y[c] - y.dyn_nat) / (y.perf - y.dyn_nat)).median()), 3)
    y = x[x.p1.notna()]
    if len(y) >= 50: o['next_vs_revised_kg'] = round(float((y.p1 - y.r1).mean()), 2)
    return o
OUT = {'complete_history': {f'age {a} | starts {s}': cell(x) for (a, s), x in E[E.complete].groupby(['age', 'starts']) if len(x) >= 50},
       'career_began_before_our_data': {f'age {a} | starts held {s}': cell(x) for (a, s), x in E[~E.complete].groupby(['age', 'starts']) if len(x) >= 50}}
# present-day check from TAB's as-at career starts
R = []
for D in ['20261126', '20261127']:
    a = pd.read_csv(f'collect/national/{D}/form_runners.csv'); b = pd.read_csv(f'collect/national/{D}/form_runner_status.csv')
    R.append(a.merge(b[['ven', 'race', 'n', 'held_starts']], on=['ven', 'race', 'n'], how='left'))
X = pd.concat(R).dropna(subset=['career_starts', 'held_starts', 'age']); X['age'] = X.age.astype(int)
lr = X[(X.held_starts < 6) & (X.age >= 5)]
OUT['tab_form_check_26_27_nov'] = {'runners': int(len(X)), 'aged_5plus_with_under_6_held': int(len(lr)), 'of_those_career_under_6': int((lr.career_starts < 6).sum()),
                                   'of_those_career_12plus': int((lr.career_starts >= 12).sum()),
                                   'held_exceeds_career_share_by_state_group': {'Qld meetings': round(float((X[X.ven.isin(['CNS', 'SSC', 'ROC'])].held_starts > X[X.ven.isin(['CNS', 'SSC', 'ROC'])].career_starts).mean()), 3),
                                                                                'other meetings': round(float((X[~X.ven.isin(['CNS', 'SSC', 'ROC'])].held_starts > X[~X.ven.isin(['CNS', 'SSC', 'ROC'])].career_starts).mean()), 3)}}
json.dump(OUT, open('batch19/out_b19_age_vs_experience.json', 'w'), indent=1)
for sec in ['complete_history', 'career_began_before_our_data']:
    print('==', sec)
    for k, v in OUT[sec].items(): print(f'{k:28s}', v)
print(OUT['tab_form_check_26_27_nov'])
