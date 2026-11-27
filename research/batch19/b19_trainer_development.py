"""Batch 19 C11: observable trainer development patterns for genuine debutants (research only; not an input; no claim about stable policy).
For horses whose whole career is in our data (debut aged 2-3, from March 2023):
 - early improvement: mean surprise at the 2nd and 3rd starts (performance beyond what the rating already expected);
 - first-preparation development: rating after the first preparation (last run before the first gap of 60+ days, or the 6th start)
   minus the rating after the debut;
 - 'ready on debut': debut performance minus the horse's level after 6 starts (how much of its early ability it showed first time).
Trainer means (shrunk, k = 10) in 2023-24 debuts vs 2025-26 debuts for trainers with 15+ debutants in each, against meeting-shuffled halves.
Also: are 'ready on debut' stables the ones whose horses improve less afterwards? Age-at-debut and debut-distance patterns by trainer.
Usage (from research/): python3 batch19/b19_trainer_development.py -> batch19/out_b19_trainer_development.json"""
import json, numpy as np, pandas as pd
U = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'tkey', 'dyn_nat', 'dyn_nat_inn', 'age_n', 'distance_m'])
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); U['k'] = U.groupby('horse').cumcount()
first = U[U.k == 0].set_index('horse'); gen = first[first.age_n.isin([2, 3]) & (first.date >= '2023-03-01') & first.tkey.notna()].index
V = U[U.horse.isin(gen)].copy(); V['perf'] = V.dyn_nat + V.dyn_nat_inn
V['gap'] = V.groupby('horse').date.diff().dt.days
rows = []
for h, g in V.groupby('horse'):
    g = g.reset_index(drop=True)
    if len(g) < 3 or g.dyn_nat_inn.iloc[:3].isna().any(): continue
    brk = g.index[(g.gap >= 60)].min() if (g.gap >= 60).any() else len(g); end = min(brk, 6) - 1
    r = {'horse': h, 'tkey': g.tkey.iloc[0], 'debut_date': g.date.iloc[0], 'age': g.age_n.iloc[0], 'dist': g.distance_m.iloc[0],
         'early_improvement': float(g.dyn_nat_inn.iloc[1:3].mean()), 'prep_dev': (float(g.dyn_nat.iloc[end + 1] - g.dyn_nat.iloc[1]) if end + 1 < len(g) and end >= 1 else np.nan),
         'ready_on_debut': (float(g.perf.iloc[0] - g.dyn_nat.iloc[6]) if len(g) > 6 else np.nan)}
    rows.append(r)
Hh = pd.DataFrame(rows); Hh['per'] = np.where(Hh.debut_date < '2025-01-01', 'a', 'b')
rng = np.random.default_rng(11)
def persist(col, k=10):
    d = Hh.dropna(subset=[col]); mu = d[col].mean()
    def tmeans(x): g = x.groupby('tkey')[col].agg(['sum', 'count']); return ((g['sum'] - g['count'] * mu) / (g['count'] + k)), g['count']
    ma, na = tmeans(d[d.per == 'a']); mb, nb = tmeans(d[d.per == 'b']); keep = na.index.intersection(nb.index); keep = keep[(na[keep] >= 15) & (nb[keep] >= 15)]
    obs = float(np.corrcoef(ma[keep], mb[keep])[0, 1]) if len(keep) > 8 else np.nan; null = []
    for _ in range(200):
        s = d.assign(per=np.where(rng.random(len(d)) < 0.5, 'a', 'b')); a_, _n = tmeans(s[s.per == 'a']); b_, _m = tmeans(s[s.per == 'b']); null.append(np.corrcoef(a_[keep], b_[keep])[0, 1])
    return {'horses': int(len(d)), 'trainers_15plus_each_period': int(len(keep)), 'corr_2023_24_vs_2025_26': round(obs, 3), 'random_split_corr_mean': round(float(np.nanmean(null)), 3)}, ma, mb, keep
OUT = {}; M = {}
for col in ['early_improvement', 'prep_dev', 'ready_on_debut']:
    o, ma, mb, keep = persist(col); OUT[col] = o; M[col] = (ma + mb) / 2
J = pd.DataFrame(M).dropna()
OUT['ready_on_debut_vs_later_development_trainer_corr'] = {'early_improvement': round(float(J[['ready_on_debut', 'early_improvement']].corr().iloc[0, 1]), 3), 'prep_dev': round(float(J[['ready_on_debut', 'prep_dev']].corr().iloc[0, 1]), 3), 'trainers': int(len(J))}
T = Hh.groupby('tkey').agg(n=('horse', 'count'), two=('age', lambda s: float((s == 2).mean())), short=('dist', lambda s: float((s <= 1100).mean())))
T = T[T.n >= 30]; T = T.join(pd.DataFrame(M))
OUT['debut_patterns_trainers_30plus'] = {'trainers': int(len(T)), 'share_debuting_at_two_sd_across_trainers': round(float(T.two.std()), 3), 'share_debuting_at_1100m_or_less_sd': round(float(T.short.std()), 3),
                                         'corr_two_share_with_early_improvement': round(float(T[['two', 'early_improvement']].corr().iloc[0, 1]), 3), 'corr_short_share_with_ready_on_debut': round(float(T[['short', 'ready_on_debut']].corr().iloc[0, 1]), 3)}
json.dump(OUT, open('batch19/out_b19_trainer_development.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
