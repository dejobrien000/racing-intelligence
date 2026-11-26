"""Batch 14 follow-up s7: what is the within-meeting artifact in the rating surprise (dyn_nat_inn)?
Hypothesis: the surprise is not centred within each race; it carries a race-level component (the day's track speed as estimated for the
whole meeting cannot follow changes during the day: drying, rain, wind, rail). Then any comparison of a jockey's (or trainer's) earlier
and later rides at one meeting inherits that drift. Tests: (1) is the surprise race-centred? (2) does the race-level part drift with race
order inside meetings? (3) does the jockey and trainer 'later rides go better' pattern vanish once each runner is measured relative to its
own race (surprise minus the race mean)?"""
import numpy as np, pandas as pd, statsmodels.api as sm, patsy, json
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'meeting_id', 'race_no', 'jkey', 'tkey', 'dyn_nat', 'dyn_nat_inn', 'date'])
V = V[V.dyn_nat_inn.notna()].copy(); O = {}
rm = V.groupby('race_id').dyn_nat_inn.transform('mean'); V['race_part'] = rm; V['within'] = V.dyn_nat_inn - rm
O['sd of race-mean surprise (kg) vs sd of runner surprise'] = [round(V.drop_duplicates('race_id').race_part.std(), 2), round(V.dyn_nat_inn.std(), 2)]
R = V.drop_duplicates('race_id')[['race_id', 'meeting_id', 'race_no', 'race_part']].copy(); R['n'] = R.groupby('meeting_id').race_no.transform('count')
R['pos'] = R.groupby('meeting_id').race_no.rank(pct=True); R = R[R.n >= 5]
slopes = R.groupby('meeting_id').apply(lambda g: np.polyfit(g.pos, g.race_part, 1)[0] if g.pos.nunique() > 2 else np.nan).dropna()
O['race-mean surprise vs position in the card, per meeting: mean slope, sd of slopes, share of meetings with |slope| > 2 kg'] = [round(slopes.mean(), 2), round(slopes.std(), 2), round(100 * (slopes.abs() > 2).mean(), 1)]
O['race-level surprise explained by its meeting and position in the card (R2 of meeting slope model)'] = round(1 - (R.race_part - R.groupby('meeting_id').race_part.transform('mean')).var() / R.race_part.var(), 3)
def within_meeting(key):
    W = V[V[key].notna()].sort_values([key, 'meeting_id', 'race_no']).copy(); g = W.groupby([key, 'meeting_id']); W['idx'] = g.cumcount(); W['n'] = g.race_no.transform('size'); W = W[W.n >= 2].copy()
    W['idx_c'] = W.idx.clip(upper=4).astype(str); res = {}
    for y in ['dyn_nat_inn', 'within']:
        W['y_w'] = W[y] - g[y].transform('mean').loc[W.index]; W['r_w'] = W.dyn_nat - g.dyn_nat.transform('mean').loc[W.index]
        yy, X = patsy.dmatrices('y_w ~ C(idx_c) + r_w', W, return_type='dataframe'); m = sm.OLS(yy, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(W[key])[0]})
        res[y] = {k.replace('C(idx_c)[T.', '').replace(']', ''): (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in m.params.index if 'idx_c' in k}
    return res
O['jockeys: later rides vs first ride at the meeting (kg): raw surprise / surprise relative to own race'] = within_meeting('jkey')
O['trainers: later runners vs first (kg): raw / relative to own race'] = within_meeting('tkey')
print(json.dumps(O, indent=1)); json.dump(O, open('/home/claude/racing-intelligence/research/batch14/followup/out_artifact.json', 'w'), indent=1)
# (4) is it the kg scale? the same comparison with each runner's surprise divided by its race's spread (sd of surprise in the race), and
#     with the distance and kg-per-length of the two races held fixed
U = pd.read_parquet('/home/claude/racing-intelligence/research/engine/frames/national_v3.parquet', columns=['race_id', 'horse', 'kgpl', 'distance_m', 'field', 'finish_pos'])
V2 = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'meeting_id', 'race_no', 'jkey', 'tkey', 'dyn_nat', 'dyn_nat_inn']).merge(U, on=['race_id', 'horse'], how='left')
V2 = V2[V2.dyn_nat_inn.notna()].copy(); V2['inn_sd'] = V2.dyn_nat_inn / V2.groupby('race_id').dyn_nat_inn.transform('std')
V2['fp_pct'] = (V2.finish_pos - 1) / (V2.field - 1).clip(lower=1); V2['exp_pct'] = V2.groupby('race_id').dyn_nat.rank(ascending=False, pct=True); V2['beat'] = V2.exp_pct - V2.fp_pct
def wm(key, y, extra=''):
    W = V2[V2[key].notna()].sort_values([key, 'meeting_id', 'race_no']).copy(); g = W.groupby([key, 'meeting_id']); W['idx'] = g.cumcount(); W['n'] = g.race_no.transform('size'); W = W[W.n >= 2].copy()
    g = W.groupby([key, 'meeting_id'])
    for c in [y, 'dyn_nat', 'kgpl', 'distance_m', 'field']: W[c + '_w'] = W[c] - g[c].transform('mean')
    W['idx_c'] = W.idx.clip(upper=4).astype(str)
    yy, X = patsy.dmatrices(f'{y}_w ~ C(idx_c) + dyn_nat_w' + extra, W, return_type='dataframe', NA_action='drop'); m = sm.OLS(yy, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(W.loc[yy.index, key])[0]})
    return {k.replace('C(idx_c)[T.', '').replace(']', ''): (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in m.params.index if 'idx_c' in k}
O2 = {}
for key in ['jkey', 'tkey']:
    O2[key] = {'kg surprise, distance/kg-per-length/field held fixed': wm(key, 'dyn_nat_inn', ' + kgpl_w + distance_m_w + field_w'),
               'surprise in race-spread units': wm(key, 'inn_sd'), 'finish vs rating rank (share of field)': wm(key, 'beat'),
               'finish percentile alone (lower = better)': wm(key, 'fp_pct')}
print(json.dumps(O2)); O['scale checks'] = O2; json.dump(O, open('/home/claude/racing-intelligence/research/batch14/followup/out_artifact.json', 'w'), indent=1)
# (5) race importance: hold the prize money (log) and class of the two races fixed. If the pattern goes, it is targeting (stables set
#     horses for the better races, which tend to come later in the card), not a measurement fault.
import duckdb
c = duckdb.connect('/home/claude/racing-intelligence/history/history.duckdb', read_only=True)
P = c.execute("select slug, cast(meeting_date as varchar) d, race_no, prize from bn_race").fetchdf()
parts = V2.race_id.str.split('|', expand=True); V2['slug'] = parts[1]; V2['d'] = parts[2]; V2['rn'] = parts[3].astype(int)
V2 = V2.merge(P.rename(columns={'race_no': 'rn'}), on=['slug', 'd', 'rn'], how='left'); V2['lprize'] = np.log1p(V2.prize)
O3 = {}
for key in ['jkey', 'tkey']:
    pass
def wm2(key, y, extra):
    W = V2[V2[key].notna() & V2.lprize.notna()].sort_values([key, 'meeting_id', 'race_no']).copy(); g = W.groupby([key, 'meeting_id']); W['idx'] = g.cumcount(); W['n'] = g.race_no.transform('size'); W = W[W.n >= 2].copy()
    g = W.groupby([key, 'meeting_id'])
    for cc in [y, 'dyn_nat', 'lprize', 'kgpl', 'distance_m', 'field']: W[cc + '_w'] = W[cc] - g[cc].transform('mean')
    W['idx_c'] = W.idx.clip(upper=4).astype(str)
    yy, X = patsy.dmatrices(f'{y}_w ~ C(idx_c) + dyn_nat_w' + extra, W, return_type='dataframe', NA_action='drop'); m = sm.OLS(yy, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(W.loc[yy.index, key])[0]})
    out = {k.replace('C(idx_c)[T.', '').replace(']', ''): (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in m.params.index if 'idx_c' in k}
    if 'lprize_w' in m.params: out['per unit log prize'] = (round(m.params['lprize_w'], 3), round(m.conf_int().loc['lprize_w', 0], 3), round(m.conf_int().loc['lprize_w', 1], 3))
    return out
for key in ['jkey', 'tkey']:
    O3[key] = {'kg surprise, no prize control (same rows)': wm2(key, 'dyn_nat_inn', ''), 'kg surprise, prize held fixed': wm2(key, 'dyn_nat_inn', ' + lprize_w'),
               'kg surprise, prize + distance + field held fixed': wm2(key, 'dyn_nat_inn', ' + lprize_w + distance_m_w + field_w')}
print(json.dumps(O3)); O['race importance checks'] = O3; json.dump(O, open('/home/claude/racing-intelligence/research/batch14/followup/out_artifact.json', 'w'), indent=1)
# (6) placebo orderings: number each jockey's rides at a meeting in RANDOM order, and in REVERSE race order. A real order effect shows only
#     in the true order (and flips in reverse); an estimator artifact shows in any order.
def wm3(key, order):
    W = V2[V2[key].notna()].copy(); rng = np.random.default_rng(7); W['u'] = rng.random(len(W))
    W = W.sort_values([key, 'meeting_id', 'race_no' if order != 'random' else 'u'], ascending=[True, True, order != 'reverse'])
    g = W.groupby([key, 'meeting_id']); W['idx'] = g.cumcount(); W['n'] = g.race_no.transform('size'); W = W[W.n >= 2].copy(); g = W.groupby([key, 'meeting_id'])
    for cc in ['dyn_nat_inn', 'dyn_nat']: W[cc + '_w'] = W[cc] - g[cc].transform('mean')
    W['idx_c'] = W.idx.clip(upper=4).astype(str)
    yy, X = patsy.dmatrices('dyn_nat_inn_w ~ C(idx_c) + dyn_nat_w', W, return_type='dataframe'); m = sm.OLS(yy, X).fit()
    out = {k.replace('C(idx_c)[T.', '').replace(']', ''): round(m.params[k], 3) for k in m.params.index if 'idx_c' in k}
    yy, X = patsy.dmatrices('dyn_nat_inn_w ~ C(idx_c)', W, return_type='dataframe'); m2 = sm.OLS(yy, X).fit()
    out['without the rating control'] = {k.replace('C(idx_c)[T.', '').replace(']', ''): round(m2.params[k], 3) for k in m2.params.index if 'idx_c' in k}
    return out
O4 = {f'{key} {o}': wm3(key, o) for key in ['jkey'] for o in ['true', 'reverse', 'random']}
print(json.dumps(O4)); O['placebo orderings'] = O4; json.dump(O, open('/home/claude/racing-intelligence/research/batch14/followup/out_artifact.json', 'w'), indent=1)
