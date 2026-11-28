"""Batch 26 Part 6 follow-up checks (research only).
(a) Is the distance-specific measure distance-specific, or just general under-rating? Control for the horse's general shrunk mean surprise
    over ALL earlier runs (gen = sum inn / (n + 3)) and its last-3 mean surprise; then test the distance-specific part dspec = dsuit - gen*w,
    where w is the share of the kernel evidence (so a horse with all runs at this distance has dspec ~ 0 by construction).
(b) Further step-ups: after a strong (+2 kg or better) first step-up, compare the next run's surprise when it (i) steps up again, (ii) stays
    within 15%, (iii) comes back down; benchmark against strong runs that were NOT step-ups followed by the same three choices.
Writes batch26/out_b26_distance_b.json and adds gen/dspec to /tmp/cand/feat_dsuit.parquet."""
import json, numpy as np, pandas as pd
rng = np.random.default_rng(267)
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'race_id', 'horse', 'date', 'dyn_nat_inn', 'dist_change', 'd_rec', 'age_n'])
F['date'] = pd.to_datetime(F.date); F = F.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
D = pd.read_parquet('/tmp/cand/feat_dsuit.parquet'); F = F.merge(D, on=['race_id', 'horse'], how='left')
g = F.groupby('horse'); F['k'] = g.cumcount()
x = F.dyn_nat_inn.fillna(0); c = F.dyn_nat_inn.notna().astype(float)
F['gen'] = (x.groupby(F.horse).cumsum() - x) / ((c.groupby(F.horse).cumsum() - c) + 3.0)
F['last3'] = g.dyn_nat_inn.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
F['n_prior'] = c.groupby(F.horse).cumsum() - c
F['wshare'] = (F.dsuit_ev + 3.0) / (F.n_prior + 3.0)
F['dspec'] = F.dsuit - F.gen * F.dsuit_ev / (F.dsuit_ev + 3.0)    # distance-weighted mean minus what the general mean would give with the same evidence
F['absdc'] = F.dist_change.abs(); F['win_'] = np.where(F.date < '2025-01-01', '2023-24', '2025-26')
F[['race_id', 'horse', 'dsuit', 'dsuit_ev', 'dslope', 'gen', 'dspec']].fillna(0.0).drop_duplicates(['race_id', 'horse']).to_parquet('/tmp/cand/feat_dsuit.parquet')
def reg(Z, cols, ctrl, boot=150):
    use = cols + ctrl; Z = Z[['dyn_nat_inn', 'horse'] + use].dropna()
    Xs = Z[use].astype(float).copy()
    for cc in cols: Xs[cc] = (Xs[cc] - Xs[cc].mean()) / Xs[cc].std()
    M = np.c_[np.ones(len(Z)), Xs.values]; y = Z.dyn_nat_inn.values; b = np.linalg.lstsq(M, y, rcond=None)[0]
    idx = pd.Series(np.arange(len(Z))).groupby(Z.horse.values).indices; keys = np.array(list(idx), dtype=object); bs = []
    for _ in range(boot):
        p = np.concatenate([idx[h] for h in rng.choice(keys, len(keys))]); bs.append(np.linalg.lstsq(M[p], y[p], rcond=None)[0])
    bs = np.array(bs)
    return {'n': int(len(Z)), **{cc: {'kg_per_sd': round(float(b[1 + use.index(cc)]), 3), 'ci': [round(float(np.percentile(bs[:, 1 + use.index(cc)], 2.5)), 3),
                                                                                       round(float(np.percentile(bs[:, 1 + use.index(cc)], 97.5)), 3)]} for cc in cols}}
CT = ['dist_change', 'absdc', 'age_n', 'k']
base = (F.k >= 3) & F.dyn_nat_inn.notna() & (F.date >= '2023-07-01')
out = {'a': {}}
for w in ['2023-24', '2025-26']:
    Z = F[base & (F.win_ == w)]
    out['a'][w] = {'general_only': reg(Z, ['gen', 'last3'], CT), 'general_plus_dsuit': reg(Z, ['gen', 'last3', 'dsuit'], CT),
                   'general_plus_dspec_plus_d_rec': reg(Z, ['gen', 'last3', 'dspec', 'd_rec'], CT)}
    for lab, m in [('evidence < 2', Z.dsuit_ev < 2), ('evidence 2-5', Z.dsuit_ev.between(2, 5)), ('evidence > 5', Z.dsuit_ev > 5)]:
        out['a'][w][f'dspec_with_general_{lab}'] = reg(Z[m], ['gen', 'last3', 'dspec'], CT, boot=100)
    print(w, json.dumps(out['a'][w]['general_plus_dspec_plus_d_rec']), flush=True)
# (b) further step-ups
F['next_inn'] = g.dyn_nat_inn.shift(-1); F['next_dc'] = g.dist_change.shift(-1)
F['up'] = (F.dist_change.astype(float).fillna(0) > 0.14).to_numpy()
nd_ = F.next_dc.astype(float).fillna(0).to_numpy(); F['nextcat'] = np.select([nd_ > 0.14, nd_ < -0.14], ['up again', 'back down'], 'similar')
F['dyn_nat_inn'] = F.dyn_nat_inn.astype(float); F['next_inn'] = F.next_inn.astype(float)
S = F[(F.dyn_nat_inn >= 2) & F.next_inn.notna() & (F.k >= 2)]
out['b'] = {}
for lab, m in [('strong run on a step up', S.up), ('strong run, not a step up', ~S.up)]:
    Q = S[m]; out['b'][lab] = {cat: {'n': int((Q.nextcat == cat).sum()), 'next_surprise_kg': round(float(Q[Q.nextcat == cat].next_inn.mean()), 3),
                                     'se': round(float(Q[Q.nextcat == cat].next_inn.std() / np.sqrt(max((Q.nextcat == cat).sum(), 1))), 3)} for cat in ['up again', 'similar', 'back down']}
W = F[(F.dyn_nat_inn < 2) & F.next_inn.notna() & (F.k >= 2)]
out['b']['all other runs (reference)'] = {cat: {'n': int((W.nextcat == cat).sum()), 'next_surprise_kg': round(float(W[W.nextcat == cat].next_inn.mean()), 3)} for cat in ['up again', 'similar', 'back down']}
json.dump(out, open('batch26/out_b26_distance_b.json', 'w'), indent=1)
print(json.dumps(out['b'], indent=0))
