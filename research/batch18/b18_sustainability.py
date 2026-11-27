"""Batch 18 D3: how much of an exceptional run is kept over the next 1, 3 and 5 starts (Engine v2.3 rating frame; research only; no prices).
perf = pre-race rating + surprise (kg). Reference points use only runs BEFORE the exceptional run: rating r0, typical (median of last 5),
repeatable upper (second-best of last 6), previous career best. Outcomes use later runs; horses that do not race again within 365 days, or
have fewer than 3 / 5 later starts, are COUNTED (shares reported), never silently dropped.
Kinds: emerging breakthrough (1-5 starts held), progressive (improving trajectory, 6+ starts), return to level (within 2 kg of the previous
career best or below it, 6+ starts), unprecedented isolated (more than 3 kg above the previous best, 6+ starts, not improving).
Higher range established = median of the next 5 at least 2 kg above the previous repeatable upper; back to previous range = median of the
next 5 within 1 kg of (or below) the previous typical level.
Usage (from research/): python3 batch18/b18_sustainability.py [frame] -> batch18/out_b18_sustainability.json"""
import sys, json, numpy as np, pandas as pd
FR = sys.argv[1] if len(sys.argv) > 1 else 'engine/frames/national_c2.parquet'
U = pd.read_parquet(FR, columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn', 'age_n']).sort_values(['horse', 'date', 'race']).reset_index(drop=True)
U['perf'] = U.dyn_nat + U.dyn_nat_inn; n = len(U)
C = {c: np.full(n, np.nan) for c in ['typ5', 'rep6', 'best', 'slope5', 'k', 'n_after_365', 'p1', 'm3', 'm5', 'med5', 'r1', 'rep_any5', 'gap_prev']}
dates = U.date.values.astype('datetime64[D]').astype(np.int64)
for h, idx in U.groupby('horse').indices.items():
    p = U.perf.values[idx]; r = U.dyn_nat.values[idx]; d = dates[idx]
    for j in range(len(idx)):
        i = idx[j]; q = p[:j][~np.isnan(p[:j])]; C['k'][i] = j
        if j: C['gap_prev'][i] = d[j] - d[j - 1]
        if len(q) >= 3: C['typ5'][i] = np.median(q[-5:]); C['rep6'][i] = np.sort(q[-6:])[-2]
        if len(q): C['best'][i] = q.max()
        if len(q) >= 5: C['slope5'][i] = np.polyfit(np.arange(5), q[-5:], 1)[0]
        later = np.flatnonzero(d[j + 1:] - d[j] <= 365); C['n_after_365'][i] = len(later)
        nx = p[j + 1:j + 6]
        if j + 1 < len(idx): C['p1'][i] = nx[0]; C['r1'][i] = r[j + 1]
        if len(nx) >= 3: C['m3'][i] = np.nanmean(nx[:3])
        if len(nx) >= 5: C['m5'][i] = np.nanmean(nx); C['med5'][i] = np.nanmedian(nx); C['rep_any5'][i] = float(np.nanmax(nx) >= p[j] - 1.0)
for c, v in C.items(): U[c] = v
E = U[(U.date >= '2023-01-01') & (U.date <= '2026-06-30') & (U.dyn_nat_inn >= 2) & (U.k >= 1)].copy()   # to mid-2026 so five later starts are possible
E['band'] = pd.cut(E.dyn_nat_inn, [2, 4, 6, 8, 10, 99], labels=['2-4', '4-6', '6-8', '8-10', '10+'], right=False).astype(str)
E['kind'] = np.select([E.k <= 5, (E.slope5 > 0.5), E.perf <= E.best + 2, (E.perf > E.best + 3) & ~(E.slope5 > 0.5)],
                      ['emerging (1-5 starts)', 'progressive (improving, 6+)', 'return to level (6+)', 'unprecedented isolated (6+)'], 'other (2-3 kg above best, 6+)')
E['agegrp'] = pd.cut(E.age_n, [0, 3, 5, 99], labels=['2-3yo', '4-5yo', '6yo+']).astype(str)
def S(x):
    o = {'runs': int(len(x)), 'raced_again_365d': round(float((x.n_after_365 >= 1).mean()), 3), 'had_3_more_365d': round(float((x.n_after_365 >= 3).mean()), 3), 'had_5_more_365d': round(float((x.n_after_365 >= 5).mean()), 3)}
    gain = x.perf - x.dyn_nat
    for c, lab in [('p1', 'next'), ('m3', 'next3'), ('m5', 'next5')]:
        y = x[x[c].notna()]; g = (y.perf - y.dyn_nat)
        if len(y) < 30: continue
        kept = y[c] - y.dyn_nat
        o[lab] = {'n': int(len(y)), 'vs_pre_rating_mean': round(float(kept.mean()), 2), 'vs_pre_rating_median': round(float(kept.median()), 2), 'se': round(float(kept.std() / np.sqrt(len(y))), 2),
                  'share_of_gain_kept_median': round(float((kept / g).median()), 2), 'vs_exceptional_run': round(float((y[c] - y.perf).mean()), 2),
                  'vs_typical_before': round(float((y[c] - y.typ5).mean()), 2) if y.typ5.notna().any() else None, 'vs_repeatable_upper_before': round(float((y[c] - y.rep6).mean()), 2) if y.rep6.notna().any() else None}
        if c == 'p1': o[lab]['vs_revised_rating'] = round(float((y.p1 - y.r1).mean()), 2)
    y = x[x.med5.notna()]
    if len(y) >= 30:
        o['repeated_within_1kg_in_next5'] = round(float(y.rep_any5.mean()), 3)
        z = y[y.rep6.notna() & y.typ5.notna()]
        if len(z) >= 30:
            o['higher_range_established'] = round(float((z.med5 >= z.rep6 + 2).mean()), 3); o['back_to_previous_range'] = round(float((z.med5 <= z.typ5 + 1).mean()), 3)
    return o
OUT = {'by_band': {b: S(x) for b, x in E.groupby('band')}, 'by_kind': {k: S(x) for k, x in E.groupby('kind')},
       'by_band_x_kind': {f'{b} | {k}': S(x) for (b, k), x in E.groupby(['band', 'kind']) if len(x) >= 100},
       'by_kind_x_age': {f'{k} | {a}': S(x) for (k, a), x in E.groupby(['kind', 'agegrp']) if len(x) >= 100}}
# why 10+ isolated peaks look fine next start while 6-10 do not: what differs about them (all measured before the run)
Q = E[E.kind == 'unprecedented isolated (6+)'].copy(); Q['b2'] = np.where(Q.dyn_nat_inn >= 10, '10+', np.where(Q.dyn_nat_inn >= 6, '6-10', 'under 6'))
OUT['isolated_peaks_profile'] = {b: {'runs': int(len(x)), 'days_since_previous_run_median': float(x.gap_prev.median()), 'share_first_up_60d_plus': round(float((x.gap_prev > 60).mean()), 3),
                                     'pre_rating_vs_typical_kg': round(float((x.dyn_nat - x.typ5).mean()), 2), 'pre_rating_vs_best_kg': round(float((x.dyn_nat - x.best).mean()), 2),
                                     'starts_held_median': float(x.k.median()), 'age_median': float(x.age_n.median())} for b, x in Q.groupby('b2')}
json.dump(OUT, open('batch18/out_b18_sustainability.json', 'w'), indent=1); print(json.dumps({k: OUT[k] for k in ['by_kind', 'isolated_peaks_profile']}, indent=0)[:6000])
