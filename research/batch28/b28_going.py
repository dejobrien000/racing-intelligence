"""Batch 28 item 8: individual going suitability (preregistered: preregistered/2026-11-28_b28_going_suitability.md).
Usage: python3 batch28/b28_going.py <frame in> <frame out with g_rec replaced> [individual]"""
import sys, json, numpy as np, pandas as pd
fin, fout = sys.argv[1], sys.argv[2]; IND = len(sys.argv) > 3
F = pd.read_parquet(fin); F['_o'] = np.arange(len(F))
S = F[['_o', 'horse', 'date', 'race', 'going', 'dyn_nat_inn', 'g_rec', 'distance_m', 'win']].copy(); S['date'] = pd.to_datetime(S.date)
S['cat'] = S.going.replace({'Firm': 'Good', 'S': 'Soft'}).fillna('Good')
S = S.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = S.groupby('horse')
x = S.dyn_nat_inn.astype(float); c = x.notna().astype(float); xs = x.fillna(0)
n_all = g.cumcount() * 0 + (c.groupby(S.horse).cumsum() - c); s_all = xs.groupby(S.horse).cumsum() - xs
S['gen'] = s_all / (n_all + 3.0)
key = S.horse + '|' + S.cat; gc_ = S.groupby(key)
n_cat = c.groupby(key).cumsum() - c; s_cat = xs.groupby(key).cumsum() - xs
S['gspec'] = s_cat / (n_cat + 3.0) - S.gen * n_cat / (n_cat + 3.0); S['n_cat'] = n_cat
S['wins_cat'] = (S.win.astype(float)).groupby(key).cumsum() - S.win.astype(float)
S = S.set_index('_o').reindex(F._o)
F['g_rec'] = S.gspec.values; F.drop(columns=['_o']).to_parquet(fout)
print('frame written', fout, 'gspec sd', round(float(np.nanstd(S.gspec.values)), 3))
if IND:
    rng = np.random.default_rng(288); T = S.reset_index(drop=True)
    T['k'] = T.groupby('horse').cumcount(); T['last3'] = T.groupby('horse').dyn_nat_inn.transform(lambda s: s.shift(1).rolling(3, min_periods=1).mean())
    T['g_rec_old'] = pd.read_parquet(fin, columns=['g_rec']).g_rec.values[S.index.values] if False else F.loc[S.index, 'g_rec'] if False else np.nan
    O = pd.read_parquet(fin, columns=['race', 'horse', 'g_rec']).rename(columns={'g_rec': 'g_rec_old'}); T = T.merge(O, on=['race', 'horse'], how='left')
    T['win_'] = np.where(T.date < '2025-01-01', '2023-24', '2025-26'); base = (T.k >= 3) & T.dyn_nat_inn.notna() & (T.date >= '2023-07-01')
    def reg(Z, cols, boot=120):
        use = cols + ['k']; Z = Z[['dyn_nat_inn', 'horse'] + use].dropna(); Xs = Z[use].astype(float).copy()
        for cc in cols: Xs[cc] = (Xs[cc] - Xs[cc].mean()) / Xs[cc].std()
        M = np.c_[np.ones(len(Z)), Xs.values]; y = Z.dyn_nat_inn.values; b = np.linalg.lstsq(M, y, rcond=None)[0]
        idx = pd.Series(np.arange(len(Z))).groupby(Z.horse.values).indices; keys = np.array(list(idx), dtype=object); bs = []
        for _ in range(boot):
            p = np.concatenate([idx[h] for h in rng.choice(keys, len(keys))]); bs.append(np.linalg.lstsq(M[p], y[p], rcond=None)[0])
        bs = np.array(bs)
        return {'n': int(len(Z)), **{cc: {'kg_per_sd': round(float(b[1 + use.index(cc)]), 3), 'ci': [round(float(np.percentile(bs[:, 1 + use.index(cc)], 2.5)), 3), round(float(np.percentile(bs[:, 1 + use.index(cc)], 97.5)), 3)]} for cc in cols}}
    out = {}
    for w in ['2023-24', '2025-26']:
        Z = T[base & (T.win_ == w)]
        out[w] = {'general + gspec + going record': reg(Z, ['gen', 'last3', 'gspec', 'g_rec_old'])}
        for cat in ['Good', 'Soft', 'Heavy', 'Synthetic']:
            m = Z.cat == cat
            if m.sum() > 3000: out[w][f'today {cat}'] = reg(Z[m], ['gen', 'last3', 'gspec'], boot=80)
        print(w, json.dumps(out[w]['general + gspec + going record']), flush=True)
    # winners on a surface vs consistent over-performers (descriptive, 2025-26, wet tracks)
    Z = T[base & (T.win_ == '2025-26') & T.cat.isin(['Soft', 'Heavy']) & (T.n_cat >= 2)]
    out['wet: next wet run surprise (kg)'] = {lab: [int(m.sum()), round(float(Z[m].dyn_nat_inn.mean()), 2)] for lab, m in [
        ('has won on this going, gspec <= 0', (Z.wins_cat > 0) & (Z.gspec <= 0)), ('has won on this going, gspec > 0.5', (Z.wins_cat > 0) & (Z.gspec > 0.5)),
        ('never won on it, gspec > 0.5', (Z.wins_cat == 0) & (Z.gspec > 0.5)), ('never won on it, gspec <= 0', (Z.wins_cat == 0) & (Z.gspec <= 0))]}
    T['rng'] = pd.cut(T.distance_m.astype(float), [0, 1200, 1800, 9999], labels=['sprint', 'middle', 'staying']).astype(str)
    out['heavy x distance (2025-26, gspec kg per sd)'] = {r: reg(T[base & (T.win_ == '2025-26') & (T.cat == 'Heavy') & (T.rng == r)], ['gen', 'last3', 'gspec'], boot=60) for r in ['sprint', 'middle', 'staying']}
    json.dump(out, open('batch28/out_b28_going.json', 'w'), indent=1); print(json.dumps({k: out[k] for k in ['wet: next wet run surprise (kg)']}))
