"""Batch 12 s5: does an unusually weak (or strong) late sectional, relative to the horse's OWN norm, precede deterioration (improvement)
not yet in its rating? Queensland tracked runs (measured, individual). Outcome = the horse's next 1-3 rating surprises (kg: how much better
or worse it ran than its pre-race rating said, relative to the field) and finishing percentile next start (independent of the rating).
Controls: compared with horses whose CURRENT run had the same overall surprise band, same experience band and similar running position."""
import re, numpy as np, pandas as pd
X = pd.read_parquet('/home/claude/b12/sect_runs.parquet')
for c in ['sf200', 'sl200', 'sf400', 'sl400']: X.loc[X[c] <= 0, c] = np.nan
X.loc[~np.isfinite(X.early_speed), ['early_speed', 'early_speed_rel']] = np.nan
nk = lambda s: re.sub(r'[^A-Z0-9]', '', str(s).upper())
V = pd.read_parquet('/tmp/nat3/research/engine/frames/national_v3.parquet', columns=['q_race_id', 'horse', 'date', 'race_id', 'dyn_nat', 'dyn_nat_inn', 'finish_pos', 'field'])
V = V.rename(columns={'field': 'field_nat', 'finish_pos': 'finish_pos_nat', 'fp_pct': 'fp_pct_nat'}).sort_values(['horse', 'date']); g = V.groupby('horse')
V['fp_pct_nat'] = (V.finish_pos_nat - 1) / (V.field_nat - 1).clip(lower=1)
for k in [1, 2, 3]: V[f'inn_n{k}'] = g.dyn_nat_inn.shift(-k); V[f'fp_n{k}'] = g.fp_pct_nat.shift(-k)
V['next3'] = V[['inn_n1', 'inn_n2', 'inn_n3']].mean(axis=1); V['rating_after3'] = g.dyn_nat.shift(-3) - V.dyn_nat
X['horse'] = X.name_key.map(nk); X = X.merge(V.rename(columns={'q_race_id': 'race_id', 'race_id': 'nat_race'}), on=['race_id', 'horse'], how='inner')
X = X.sort_values(['horse', 'meeting_date']).reset_index(drop=True); h = X.groupby('horse')
X['n_trk'] = h.cumcount()
for col in ['retention_rel', 'v200_rel', 'accel_rel', 'v400_rel', 'early_speed_rel', 'sl200_rel', 'sf200_rel']:
    s = X[col]; cnt = s.notna().astype(float).groupby(X.horse).cumsum() - s.notna(); sm = s.fillna(0).groupby(X.horse).cumsum() - s.fillna(0)
    pm = sm / (cnt + 3.0)                                      # prior own mean, shrunk towards the field median (0) with 3 runs' weight
    resid = s - pm; X[col + '_own'] = resid / resid[X.n_trk >= 3].std()   # standardised deviation from own norm
X['weak'] = (X.retention_rel_own < -1); X['strong'] = (X.retention_rel_own > 1)
for k in [2, 3]: X[f'weak{k}'] = X.weak.astype(int).groupby(X.horse).rolling(k).sum().reset_index(level=0, drop=True).eq(k); X[f'strong{k}'] = X.strong.astype(int).groupby(X.horse).rolling(k).sum().reset_index(level=0, drop=True).eq(k)
X['sband'] = pd.cut(X.dyn_nat_inn, [-99, -4, -1.5, 1.5, 4, 99]); X['eband'] = pd.cut(X.n_trk, [2, 5, 10, 999]); X['pband'] = pd.cut(X.pos400 / X.field, [0, 0.34, 0.67, 2])
el = X[(X.n_trk >= 3) & X.inn_n1.notna()].copy()
def boot(d, k, reps=400, seed=7):
    rng = np.random.default_rng(seed); u, inv = np.unique(k, return_inverse=True); s = np.bincount(inv, d); n = np.bincount(inv)
    b = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(u), len(u)) for _ in range(reps))]; return round(float(np.percentile(b, 2.5)), 2), round(float(np.percentile(b, 97.5)), 2)
def compare(flag, label, d=el):
    d = d.copy(); d['cell'] = d.sband.astype(str) + d.eband.astype(str) + d.pband.astype(str)
    base = d[~d[flag]].groupby('cell')[['inn_n1', 'next3', 'fp_n1', 'rating_after3']].mean()
    f = d[d[flag]].copy()
    for o in ['inn_n1', 'next3', 'fp_n1', 'rating_after3']: f[o + '_x'] = f[o] - f.cell.map(base[o])
    nx = f[f.next3.notna()]
    return {'pattern': label, 'runs': len(f), 'horses': f.horse.nunique(), 'next_surprise_vs_matched_kg': round(f.inn_n1_x.mean(), 2), 'ci': boot(f.inn_n1_x.dropna().values, f.loc[f.inn_n1_x.notna(), 'horse'].values),
            'next3_mean_vs_matched_kg': round(nx.next3_x.mean(), 2), 'next_finish_pct_vs_matched': round(f.fp_n1_x.mean(), 3),
            'share_next_surprise_below_-3kg_%': round(100 * (f.inn_n1 < -3).mean(), 1), 'matched_share_below_-3kg_%': round(100 * (d[~d[flag]].inn_n1 < -3).mean(), 1),
            'recovered_next3_>=0_%': round(100 * (nx.next3 >= 0).mean(), 1), 'rating_change_over_3_starts_vs_matched_kg': round(f.rating_after3_x.mean(), 2)}
rows = [compare('weak', '1 weak final-200 retention (z<-1 vs own norm)'), compare('weak2', '2 in a row weak'), compare('weak3', '3 in a row weak'),
        compare('strong', '1 strong retention (z>+1)'), compare('strong2', '2 in a row strong'), compare('strong3', '3 in a row strong')]
cf = el[el.m <= 1.5]; rows += [compare('weak', 'weak, competitive finish only (within 1.5 L)', cf), compare('strong', 'strong, competitive finish only (within 1.5 L)', cf)]
cf1 = el[el.m <= 1.0]; rows += [compare('weak', 'weak, within 1.0 L', cf1), compare('weak2', '2 in a row weak, within 1.5 L each time', el[(el.m <= 1.5)])]
for col, lab in [('v200_rel_own', 'final-200 speed'), ('accel_rel_own', 'late acceleration'), ('v400_rel_own', '400-200 speed'), ('early_speed_rel_own', 'early speed (to 600 out)')]:
    el['_w'] = el[col] < -1; el['_s'] = el[col] > 1; rows += [compare('_w', f'weak {lab} (z<-1)'), compare('_s', f'strong {lab} (z>+1)')]
O = pd.DataFrame(rows); print(O.to_string(index=False)); O.to_csv('/home/claude/b12/out_s5_late.csv', index=False)
print('eligible runs (3+ prior tracked runs, a next start):', len(el), '| horses', el.horse.nunique(), '| years', el.meeting_date.dt.year.value_counts().sort_index().to_dict())
X.drop(columns=['sband', 'eband', 'pband']).to_parquet('/home/claude/b12/sect_runs_own.parquet')
# chronological check: the same comparisons within 2023-24 and within 2025-26 separately
rows = []
for yrs, lab in [((2022, 2023, 2024), '2022-24'), ((2025, 2026), '2025-26')]:
    sub = el[el.meeting_date.dt.year.isin(yrs)]
    for f, l in [('weak', 'weak retention'), ('weak2', '2 in a row weak')]: rows.append({'period': lab, **compare(f, l, sub)})
    rows.append({'period': lab, **compare('weak', 'weak retention within 1.0 L', sub[sub.m <= 1.0])})
    rows.append({'period': lab, **compare('weak', 'weak retention within 1.5 L', sub[sub.m <= 1.5])})
P = pd.DataFrame(rows)[['period', 'pattern', 'runs', 'next_surprise_vs_matched_kg', 'ci', 'next_finish_pct_vs_matched']]; print(P.to_string(index=False)); P.to_csv('/home/claude/b12/out_s5_late_periods.csv', index=False)
