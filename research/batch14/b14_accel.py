"""Batch 14 s4: momentum and acceleration timing (measured 200 m section speeds; coarse: no instantaneous acceleration or exact peak speed claimed).
timing = mean field-relative speed 800-400 m out minus mean field-relative speed over the last 400 m  (+ = gains on the field earlier, - = later)
Field-relative speeds mean a horse 'gaining' may partly be others slowing: relative, not absolute, acceleration.
timing_res = timing after removing what the run's circumstances explain (early position, deficit at 800, distance, field size, race tempo, track).
1) Is timing a repeatable trait of the horse? of the jockey (within the same horse)? split-half correlations.
2) Does a horse's PRIOR timing tendency (shrunk mean of earlier runs, pre-race information) relate to how well it runs relative to its rating
   (this-run surprise, kg), overall and by course? Course measure (empirical, not physical geometry): 'hold' = share of winners in the first
   three at the 400 m mark, by track (Qld tracks with 150+ races). Verified straight lengths are NOT in the database.
3) Once in front at the 200 m mark, do early-momentum leaders hold on more often than leaders who got there later? (descriptive, same-race)"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, os, sys
os.environ['LEADERS_ONLY'] = '1'; sys.argv = ['x']
exec(open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0])
OUT = {}
def prep(d):
    d = d.copy(); d['v800r'] = d.v800 - d.groupby('race_id').v800.transform('median')
    d = d.dropna(subset=['v800r', 'v600r', 'v400r', 'v200r', 'early_pos', 'def800c']).copy()
    d['timing'] = (d.v800r + d.v600r) / 2 - (d.v400r + d.v200r) / 2
    m = smf.ols('timing ~ early_pos + I(early_pos**2) + def800c + C(dband) + field + tz + tz_miss + C(track)', d).fit(); d['timing_res'] = m.resid
    d['jk'] = d.jkey.fillna(d.jockey.astype(str))
    return d.sort_values(['horse', 'meeting_date']).reset_index(drop=True)
def split_half(d, key, col, nmin):
    h = d.groupby(key).filter(lambda g: len(g) >= nmin).copy(); h['half'] = h.groupby(key).cumcount() % 2
    p = h.groupby([key, 'half'])[col].mean().unstack().dropna(); r = p[0].corr(p[1]); return round(r, 3), len(p), round(2 * r / (1 + r), 3)
for lab, d in [('QLD 2022-26', Q), ('SA 2024-26', S)]:
    d = prep(d); r = {'runs': len(d), 'timing_sd_ms': round(d.timing.std(), 3), 'timing_res_sd': round(d.timing_res.std(), 3)}
    r['share of timing explained by circumstances (R2)'] = round(1 - d.timing_res.var() / d.timing.var(), 3)
    r['horse split-half r (8+ runs) [r, horses, full-length reliability]'] = split_half(d, 'horse', 'timing_res', 8)
    d['res_wh'] = d.timing_res - d.groupby('horse').timing_res.transform('mean')          # within-horse: what changes with the rider
    r['jockey split-half r, within-horse residual (100+ rides)'] = split_half(d.sort_values('meeting_date'), 'jk', 'res_wh', 100)
    r['jockey split-half r, raw residual (100+ rides)'] = split_half(d.sort_values('meeting_date'), 'jk', 'timing_res', 100)
    # prior tendency (pre-race): shrunk mean of earlier timing_res with 4 runs' weight towards 0
    cnt = d.groupby('horse').cumcount(); sm = d.groupby('horse').timing_res.cumsum() - d.timing_res
    d['prior_timing'] = sm / (cnt + 4.0); sd = d.prior_timing[cnt >= 3].std(); d['prior_timing_z'] = d.prior_timing / sd
    trk = d.groupby('race_id').agg(track=('track', 'first')); w = d[d.fp == 1].drop_duplicates('race_id').set_index('race_id'); trk['win_top3_at400'] = (w.pos400 <= 3).reindex(trk.index)
    trk['win_top3_at400'] = trk.win_top3_at400.astype(float); hold = trk.groupby('track').win_top3_at400.agg(['mean', 'size']); hold = hold[hold['size'] >= 150]['mean']
    d['hold'] = d.track.map(hold); d['hold_z'] = (d.hold - hold.mean()) / hold.std()
    e = d[(cnt >= 3) & d.hold.notna()].copy()
    m = smf.ols('dyn_nat_inn ~ prior_timing_z * hold_z + C(rband) + C(dband) + field + early_pos + tz + tz_miss', e).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(e.horse)[0]})
    r['this-run surprise kg: prior timing (per sd), course hold (per sd), interaction'] = {k: (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in ['prior_timing_z', 'hold_z', 'prior_timing_z:hold_z']}
    # same without using this run's early position (it is partly the horse's choice of style)
    m2 = smf.ols('dyn_nat_inn ~ prior_timing_z * hold_z + C(rband) + C(dband) + field + tz + tz_miss', e).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(e.horse)[0]})
    r['... without this-run position'] = {k: (round(m2.params[k], 3), round(m2.conf_int().loc[k, 0], 3), round(m2.conf_int().loc[k, 1], 3)) for k in ['prior_timing_z', 'hold_z', 'prior_timing_z:hold_z']}
    r['tracks with a hold measure'] = {k: round(v, 3) for k, v in hold.sort_values().items()}
    # 3) leaders at the 200 m mark: who holds on? early momentum (v600r) vs late (v400r), given the lead and the rating
    L = d[d.def200 == 0].copy()
    def second(col):
        t = d[['race_id', col]].dropna().sort_values(['race_id', col]); t = t[t.groupby('race_id').cumcount() == 1]; return t.set_index('race_id')[col]
    L['lead200'] = L.race_id.map(second('def200')); L['won'] = (L.fp == 1).astype(int); L['early_mom'] = (L.v800r + L.v600r) / 2; L['late_mom'] = L.v400r
    L['rating_rank'] = L.groupby('race_id').dyn_nat.rank()  # one leader per race; rank within field computed below instead
    rr = d.groupby('race_id').dyn_nat.rank(ascending=False); L['rating_rank'] = rr.loc[L.index]
    L = L.dropna(subset=['lead200', 'early_mom', 'late_mom'])
    ml = smf.logit('won ~ lead200 + early_mom + late_mom + rating_rank + field + C(dband)', L).fit(disp=0)
    r['leaders at 200 m: odds ratio per 1 m/s (early momentum, late momentum), lead per 0.1 s'] = {
        'early_mom': round(float(np.exp(ml.params['early_mom'])), 3), 'early_ci': [round(float(np.exp(x)), 3) for x in ml.conf_int().loc['early_mom']],
        'late_mom': round(float(np.exp(ml.params['late_mom'])), 3), 'late_ci': [round(float(np.exp(x)), 3) for x in ml.conf_int().loc['late_mom']],
        'lead_per_0.1s': round(float(np.exp(0.1 * ml.params['lead200'])), 3), 'leaders': len(L), 'won_%': round(100 * L.won.mean(), 1)}
    OUT[lab] = r; print(lab, json.dumps(r, default=str)[:3000], flush=True)
    d[['race_id', 'saddlecloth', 'horse', 'jk', 'timing', 'timing_res', 'prior_timing']].to_parquet(f'/home/claude/b14/timing_{lab[:3].strip()}.parquet')
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_accel.json', 'w'), indent=1, default=str)
