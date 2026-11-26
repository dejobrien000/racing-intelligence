"""Engine v2.2 terms (benchmarks/engine_v2_2/manifest.json), for NSW/VIC/ACT/SA/WA/TAS meetings. Queensland stays on v2.1.
raw(T, H_): today's runners T + the history frame before the race date H_ -> the 14 raw Batch 10 features, computed with
exactly the same code path as the research build (research/batch10/scripts/feat10.py): history rows and today's rows are
stacked per horse and every feature uses earlier rows only. terms(T): race-centred, missing -> 0 (no information), scaled
by the release's frozen SDs. Missing information is never treated as poor performance."""
import json, os, numpy as np, pandas as pd
MPATH = os.path.join(os.path.dirname(__file__), '..', 'benchmarks', *(('engine_v2_3', 'engine_v2_2.json') if os.environ.get('ENGINE_C2', '0') == '1' else ('engine_v2_2', 'manifest.json')))
M = json.load(open(MPATH))
K = M['constants']; VL = M['venue_level_kg']; AL = M['venue_alias']
def _slope(a):
    m = ~np.isnan(a)
    if m.sum() < 4: return np.nan
    t = np.arange(len(a))[m]; y = a[m]; t = t - t.mean(); return float((t * (y - y.mean())).sum() / (t ** 2).sum())
def _top3(a):
    a = a[~np.isnan(a)]; return np.sort(a)[-3:].mean() if len(a) >= 3 else np.nan
def raw(T, H_):
    T = T.copy(); hh = H_[H_.horse.isin(T.horse)][['horse', 'date', 'race', 'venue', 'dyn_nat', 'dyn_nat_inn']].copy(); hh['today'] = False
    td = pd.DataFrame({'horse': T.horse.values, 'date': pd.to_datetime(T.date.values), 'race': '~today|' + T.race_id.astype(str).values, 'venue': T.venue.map(lambda v: AL.get(v, v)).values,
                       'dyn_nat': T.dyn_nat.values, 'dyn_nat_inn': np.nan, 'today': True, 'tix': T.index.values})
    U = pd.concat([hh, td], ignore_index=True).sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
    inn = U.dyn_nat_inn; U['perf'] = U.dyn_nat + inn; pv = inn.fillna(0.0)
    n = g['dyn_nat_inn'].transform(lambda s: s.notna().cumsum().shift(fill_value=0))
    s1 = pv.groupby(U.horse).cumsum() - pv; s2 = (pv ** 2).groupby(U.horse).cumsum() - pv ** 2; k = float(K['h_sd_shrink_runs']); pop = float(K['pop_var_surprise_kg2'])
    U['n_prior'] = n; U['h_sd'] = np.sqrt((s2 - s1 ** 2 / n.replace(0, np.nan) + k * pop) / (n - 1).clip(lower=0).add(k)).where(n >= 1)
    r5sd = g['dyn_nat_inn'].transform(lambda s: s.shift().rolling(5, min_periods=3).std()); U['recent_var_ratio'] = (r5sd / U.h_sd).where(n >= 8)
    short = g['perf'].transform(lambda s: s.shift().rolling(5, min_periods=3).mean()); long_ = g['perf'].transform(lambda s: s.shift(6).rolling(15, min_periods=5).mean())
    U['gap_long_z'] = (long_ - U.dyn_nat) / U.h_sd; U['short_vs_long'] = short - long_
    U['below_top3'] = g['perf'].transform(lambda s: s.shift().expanding(3).apply(_top3, raw=True)) - U.dyn_nat
    U['slope15'] = g['perf'].transform(lambda s: s.shift().rolling(15, min_periods=8).apply(_slope, raw=True))
    U['neg_run'] = g['dyn_nat_inn'].transform(lambda s: (s.shift() < 0).astype(float).rolling(5, min_periods=3).sum())
    gapd = (U.date - g.date.shift()).dt.days; U['quick_today'] = (gapd <= K['quick_days']).astype(float).where(gapd.notna())
    newprep = gapd.isna() | (gapd > K['prep_gap_days']); U['prep_id'] = newprep.groupby(U.horse).cumsum(); gp = U.groupby(['horse', 'prep_id']); U['prep_run'] = gp.cumcount() + 1
    U['e3'] = U.perf.where(U.prep_run <= 3); cur = U.groupby(['horse', 'prep_id']).e3.transform(lambda s: s.shift().expanding().mean())
    pe = U.groupby(['horse', 'prep_id']).e3.mean().reset_index().sort_values(['horse', 'prep_id']); pe['prev_e3'] = pe.groupby('horse').e3.transform(lambda s: s.shift().expanding().mean())
    prev = U[['horse', 'prep_id']].merge(pe[['horse', 'prep_id', 'prev_e3']], on=['horse', 'prep_id'], how='left').prev_e3.values
    U['early_prep_vs_usual'] = (cur - prev).where(U.prep_run >= 4)
    lvl = U.venue.map(VL); U['venue_step'] = lvl - lvl.groupby(U.horse).shift()
    td = U[U.today].set_index('tix')
    for c in ['n_prior', 'h_sd', 'recent_var_ratio', 'gap_long_z', 'short_vs_long', 'below_top3', 'slope15', 'neg_run', 'quick_today', 'early_prep_vs_usual', 'venue_step']: T['b22_' + c] = td[c].reindex(T.index).values
    T['b22_hsd_x_rel'] = T.b22_h_sd * (T.dyn_nat - T.groupby('race_id').dyn_nat.transform('mean'))
    T['b22_recentform_x_established'] = T.f_avgfp3 * (T.b22_n_prior >= K['established_runs']) if 'f_avgfp3' in T else np.nan
    T['b22_light_weight'] = (T.weight_kg <= K['light_weight_kg']).astype(float).where(T.weight_kg.notna())
    T['b22_log_runs_held'] = np.log1p(T.b22_n_prior); T['b22_rating_uncertainty'] = T.rating_sd_kg_national if 'rating_sd_kg_national' in T else np.nan
    return T
def terms(T, which='all_races'):
    C = M[f'coef_per_sd_{which}']; S = M[f'term_sd_{which}']; out = {}
    for c in M['terms']:
        v = pd.to_numeric(T['b22_' + c], errors='coerce'); t = (v - v.groupby(T.race_id).transform('mean')).fillna(0.0) / S[c]; out[c] = t * C[c]
    return pd.DataFrame(out, index=T.index)
