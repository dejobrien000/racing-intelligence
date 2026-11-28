"""Batch 27 P4: year-plus returners (research only). No blanket deduction; nothing about injury or fitness is inferred from a gap.
1 Selective continuation: of every 365+ day return (3+ held runs before), how many horses race again 1..6 times, how their FIRST-UP
  run compares between those who continue and those who stop, and recovery counted over ALL returners (stoppers shown, not dropped).
2 Who struggles (runs before 2024 only, so nothing is chosen on the judged windows): first-up surprise vs age, experience, actual time
  away, gap vs the horse's usual interval, pre-break trajectory, trainer change, distance change.
3 Engine terms for the harness (coefficients refitted inside each window by the harness, so point in time):
  ret365 = 1 if 365+ days since the previous held run; ret365_lgap = ret365 x log(days / 365); ret365_age = ret365 x max(age - 5, 0).
Writes batch27/out_b27_returners365.json and /tmp/cand/feat_ret365.parquet (race_id, horse, the three terms)."""
import json, numpy as np, pandas as pd
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'date', 'state', 'age_n', 'tkey', 'distance_m', 'dyn_nat', 'dyn_nat_inn'])
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = F.groupby('horse')
F['k'] = g.cumcount(); F['days'] = (F.date - g.date.shift()).dt.days
F['usual'] = g.days.transform(lambda s: s.shift().expanding().median())
F['traj'] = g.dyn_nat.shift(1) - g.dyn_nat.shift(4)
F['tchg'] = (g.tkey.shift() != F.tkey) & g.tkey.shift().notna() & F.tkey.notna()
F['dchg'] = np.log(F.distance_m.astype(float) / g.distance_m.shift().astype(float))
F['inn'] = F.dyn_nat_inn.astype(float)
ret = (F.days >= 365) & (F.k >= 3)
out = {}
# 1 selective continuation
idx = np.flatnonzero(ret.values); hs = F.horse.values; nxt = []
for i in idx:
    j = i + 1; c = 0; pre = F.dyn_nat.values[i]; reach = None; later = []
    while j < len(F) and hs[j] == hs[i] and c < 6 and (j == i + 1 or F.days.values[j] < 365):
        later.append(F.inn.values[j]); c += 1
        if reach is None and F.dyn_nat.values[j] >= pre - 0.5: reach = c
        j += 1
    nxt.append((i, c, reach, F.inn.values[i]))
N = pd.DataFrame(nxt, columns=['i', 'later_runs', 'reached_at', 'first_up_surprise'])
out['returns_365plus'] = int(len(N))
out['later_runs_distribution'] = {str(k): int(v) for k, v in N.later_runs.clip(upper=6).value_counts().sort_index().items()}
out['first_up_surprise_by_continuation'] = {lab: {'returns': int(len(z)), 'mean_kg': round(float(z.first_up_surprise.mean()), 2)} for lab, z in
                                            [('never ran again', N[N.later_runs == 0]), ('ran 1-2 more', N[N.later_runs.between(1, 2)]), ('ran 3-5 more', N[N.later_runs.between(3, 5)]), ('ran 6+ more', N[N.later_runs >= 6])]}
out['rating_back_within_0_5kg_of_pre_break_level'] = {'among_all_returns_pct': round(100 * float(N.reached_at.notna().mean()), 1),
                                                       'among_those_with_6_more_runs_pct': round(100 * float(N[N.later_runs >= 6].reached_at.notna().mean()), 1),
                                                       'stopped_before_6_runs_without_getting_back_pct_of_all': round(100 * float(((N.later_runs < 6) & N.reached_at.isna()).mean()), 1)}
# 2 who struggles (before 2024)
D = F[ret & (F.date < '2024-01-01') & F.inn.notna()].copy()
D['ratio'] = D.days / D.usual.clip(lower=14)
def tab(col, bins, labels):
    b = pd.cut(D[col], bins, labels=labels); t = D.groupby(b, observed=True).inn.agg(['size', 'mean'])
    return {str(k): [int(v['size']), round(float(v['mean']), 2)] for k, v in t.iterrows()}
out['before_2024'] = {'runs': int(len(D)), 'mean_kg': round(float(D.inn.mean()), 2),
                      'by_age': tab('age_n', [0, 3, 4, 5, 6, 30], ['2-3yo', '4yo', '5yo', '6yo', '7yo+']),
                      'by_runs_before': tab('k', [2, 7, 15, 30, 999], ['3-7', '8-15', '16-30', '31+']),
                      'by_days_away': tab('days', [364, 450, 600, 900, 99999], ['365-450', '451-600', '601-900', '900+']),
                      'by_gap_vs_usual': tab('ratio', [0, 10, 20, 40, 1e9], ['<10x', '10-20x', '20-40x', '40x+']),
                      'by_pre_break_trajectory_kg': tab('traj', [-99, -1, 1, 99], ['declining', 'flat', 'improving']),
                      'by_distance_change': tab('dchg', [-9, -0.1, 0.1, 9], ['shorter', 'similar', 'longer'])}
out['before_2024']['trainer_change'] = {k: [int(len(z)), round(float(z.inn.mean()), 2)] for k, z in [('changed', D[D.tchg]), ('same', D[~D.tchg])]}
# 3 terms
T = F[['race_id', 'horse']].copy(); r = ret.astype(float)
T['ret365'] = r; T['ret365_lgap'] = r * np.log(F.days.clip(lower=365) / 365.0).fillna(0); T['ret365_age'] = r * (F.age_n - 5).clip(lower=0).fillna(0)
T.drop_duplicates(['race_id', 'horse']).to_parquet('/tmp/cand/feat_ret365.parquet')
json.dump(out, open('batch27/out_b27_returners365.json', 'w'), indent=1); print(json.dumps(out, indent=0)[:2500])
