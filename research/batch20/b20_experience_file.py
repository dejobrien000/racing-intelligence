"""Batch 20 B4 (v2): experience used by the history-completeness responsiveness candidate, one row per completed run, point in time.
Each run gets n_eff (the experience the update-rule taper uses) and a source label. Nothing here uses information from after the run,
except where marked as a population-level table fitted on runs before 2024 only.

  known starts  = distinct earlier Australian TAB start dates in the Betfair runner list (Jan 2020 on; names and dates only, no prices) or in
                  our rating history. Betfair lists contain very few scratchings (0.7% of Queensland rows checked against RQ scratchings).
  verified      TAB's as-at career starts for that horse on that race day (morning form record, collected from 25 Nov 2026): n_eff = TAB starts.
                Never projected back to earlier runs.
  complete      first known start on or after 1 Jul 2020 (six months into the Betfair list) at age 4 or less: n_eff = known starts.
  late_maiden   first known start on or after 1 Jul 2020 at age 5+ in a maiden race: treated as a genuinely inexperienced older horse,
                n_eff = known starts (no floor: an older horse is NOT assumed experienced).
  probable_incomplete  first known start before 1 Jul 2020 (career may start before the list), or at age 5+ outside a maiden race (import,
                overseas or earlier career): n_eff = known starts + the typical number of starts by that age among complete-history horses
                (table fitted on runs before 1 Jan 2024; inferred, not verified).
Usage (from research/): python3 batch20/b20_experience_file.py <frame.parquet> <out.parquet>"""
import sys, glob, re, json, duckdb, numpy as np, pandas as pd
FR, OUTF = sys.argv[1], sys.argv[2]
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
con = duckdb.connect('../history/history.duckdb', read_only=True)
U = pd.read_parquet(FR, columns=['race', 'horse', 'date', 'age_n', 'class_label']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
bf = con.execute("select distinct meeting_date, name_key, race_type from bf_runner where state <> 'NZ'").fetchdf(); bf['horse'] = bf.name_key.map(nk); bf['date'] = pd.to_datetime(bf.meeting_date)
bf = bf[bf.horse.isin(set(U.horse))]
S = pd.concat([bf[['horse', 'date']].assign(mdn=bf.race_type.eq('Mdn')), U[['horse', 'date']].assign(mdn=U.class_label.eq('Maiden'))])
S = S.groupby(['horse', 'date'], as_index=False).mdn.max().sort_values(['horse', 'date'])
S['known_before'] = S.groupby('horse').cumcount()
first = S.groupby('horse').first().rename(columns={'date': 'first_known', 'mdn': 'first_mdn'})[['first_known', 'first_mdn']]
U = U.merge(S[['horse', 'date', 'known_before']], on=['horse', 'date'], how='left').merge(first, left_on='horse', right_index=True, how='left')
a1 = U.groupby('horse').age_n.transform('first'); d1 = U.groupby('horse').date.transform('first')
U['age_first_known'] = (a1 - ((d1 - U.first_known).dt.days / 365.25)).round()
early = U.first_known < pd.Timestamp('2020-07-01'); old = U.age_first_known >= 5
U['source'] = np.where(early, 'probable_incomplete', np.where(~old, 'complete', np.where(U.first_mdn, 'late_maiden', 'probable_incomplete')))
# typical starts by age among complete-history horses, from runs before 2024 (population table; inferred)
C = U[(U.source == 'complete') & (U.date < pd.Timestamp('2024-01-01'))]
tab = C.groupby(C.age_n.clip(2, 9)).known_before.median()
for a in range(2, 13): tab.loc[a] = tab.get(a, tab[tab.index <= a].iloc[-1] if (tab.index <= a).any() else 0.0)
tab = tab.sort_index().cummax()   # never fewer expected starts at an older age
prior = U.age_first_known.clip(2, 12).map(tab).fillna(0.0)
U['n_eff'] = np.where(U.source == 'probable_incomplete', U.known_before + prior, U.known_before).astype(float)
V = []
for f in sorted(glob.glob('collect/national/*/form_runners.csv')):
    d = pd.read_csv(f, usecols=['name', 'career_starts']); d['date'] = pd.Timestamp(f.split('/')[2]); d['horse'] = d.name.map(nk); V.append(d.dropna(subset=['career_starts']))
if V:
    V = pd.concat(V).drop_duplicates(['horse', 'date'])
    U = U.merge(V[['horse', 'date', 'career_starts']], on=['horse', 'date'], how='left')
    v = U.career_starts.notna(); U.loc[v, 'n_eff'] = U.loc[v, 'career_starts'].astype(float); U.loc[v, 'source'] = 'verified'
U[['race', 'horse', 'n_eff', 'source']].rename(columns={'race': 'race_key'}).to_parquet(OUTF)
held = U.groupby('horse').cumcount()
info = {'runs_by_source': U.source.value_counts().to_dict(), 'typical_starts_by_age_table': {int(k): float(v) for k, v in tab.items()},
        'known_minus_held_median_by_source': U.assign(g=U.known_before - held).groupby('source').g.median().round(1).to_dict(),
        'share_n_eff_ge_24_aged_5plus': round(float((U[U.age_n >= 5].n_eff >= 24).mean()), 3)}
json.dump(info, open('batch20/out_b20_experience_file.json', 'w'), indent=1); print(OUTF, info)
