"""Batch 14 s8/s9: physical deterioration and failure to accelerate, relative to each horse's OWN earlier runs, with the owner's context.
Builds on Batch 12 s5 (one weak final-200 retention -> +0.52 kg bounce next start; repeats not clearly different).
Per run, three components vs the field and then vs the horse's own prior mean (shrunk, 3 runs' weight), standardised:
  cruise  = mean field-relative speed 800-400 m out                    (cruising speed before the turn/straight)
  kick    = speed 400-200 minus speed 600-400, field-relative           (how much more it found when the race quickened)
  hold    = speed final 200 minus 400-200, field-relative              (endurance through the line)
A 'flat' run = kick z < -1 with cruise z > -0.5 (normal cruising, little extra when asked: the owner's description; we cannot see when the
rider asked). 'Faded' = hold z < -1 with kick z > -0.5. 'Slow throughout' = cruise z < -1. Repeats = the same pattern on consecutive starts.
Context of the run: first-up (first run of a preparation), up 200 m+ in distance, fast early tempo (z > 0.75), later in a preparation (4th run+),
familiar distance (within 100 m of a distance it has run 3+ times before).
Outcomes: next-run surprise (kg), whether the pattern recurs next start, rating change over the next 3 starts, and whether the horse
races again within 120 days (a selection check: horses that stop racing cannot show recovery)."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, os, sys
os.environ['LEADERS_ONLY'] = '1'; sys.argv = ['x']
exec(open('/home/claude/racing-intelligence/research/batch14/b14_finish.py').read().split("FEAT = ")[0])
CTRL = 'bs(dyn_nat_inn, df=5) + C(rband) + early_pos + def800c + tz + tz_miss + C(dband) + field + fp_pct'
VV = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'date', 'distance_m']).sort_values(['horse', 'date'])
VV['dist_prev'] = VV.groupby('horse').distance_m.shift(1).astype(float); VV = VV.rename(columns={'race_id': 'nat_race'})[['nat_race', 'horse', 'dist_prev']]
def prep(d):
    d = d.merge(VV, on=['nat_race', 'horse'], how='left'); d['v800r'] = d.v800 - d.groupby('race_id').v800.transform('median')
    d = d.dropna(subset=['v800r', 'v600r', 'v400r', 'v200r', 'early_pos', 'def800c']).sort_values(['horse', 'meeting_date']).reset_index(drop=True)
    d['cruise'] = (d.v800r + d.v600r) / 2; d['kick'] = d.v400r - d.v600r; d['hold'] = d.v200r - d.v400r
    cnt = d.groupby('horse').cumcount(); d['n_prior'] = cnt
    for c in ['cruise', 'kick', 'hold']:
        sm = d.groupby('horse')[c].cumsum() - d[c]; res = d[c] - sm / (cnt + 3.0); d[c + '_z'] = res / res[cnt >= 3].std()
    d['flat'] = ((d.kick_z < -1) & (d.cruise_z > -0.5)).astype(int); d['faded'] = ((d.hold_z < -1) & (d.kick_z > -0.5)).astype(int); d['slow'] = (d.cruise_z < -1).astype(int)
    g = d.groupby('horse')
    for p in ['flat', 'faded', 'slow']:
        run = d[p].copy(); k = np.zeros(len(d), dtype=int); prev_h = None; acc = 0
        for i, (h, v) in enumerate(zip(d.horse.values, run.values)):
            acc = acc + 1 if (h == prev_h and v) else (1 if v else 0); prev_h = h; k[i] = acc
        d[p + '_streak'] = k; d[p + '_next'] = g[p].shift(-1)
    d['prep_idx'] = d.prep_idx.astype(float); d['dist_change'] = d.dist_change.astype(float); d['gap_n1'] = d.gap_n1.astype(float)
    d['firstup'] = (d.prep_idx == 1).astype(int); d['dist_up'] = ((d.d.astype(float) - d.dist_prev) >= 200).astype(int); d['fast_tempo'] = (d.tempo_z.astype(float) > 0.75).astype(int)
    d['late_prep'] = (d.prep_idx >= 4).astype(int)
    d['dkey'] = (d.d / 100).round(); seen = d.groupby(['horse', 'dkey']).cumcount(); d['familiar'] = (seen >= 3).astype(int)
    d['rating_after3'] = g.dyn_nat.shift(-3) - d.dyn_nat; d['races_again_120'] = (d.gap_n1.fillna(999) <= 120).astype(int)
    return d[d.n_prior >= 3].copy()
OUT = {}
def coef(m, k): return (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3))
for lab, d0 in [('QLD 2022-26', Q), ('SA 2024-26', S)]:
    d = prep(d0); r = {'runs (3+ prior tracked runs)': len(d), 'share flat %': round(100 * d.flat.mean(), 1), 'share faded %': round(100 * d.faded.mean(), 1), 'share slow %': round(100 * d.slow.mean(), 1)}
    cl = lambda e: {'groups': pd.factorize(e.horse)[0]}
    for p in ['flat', 'faded', 'slow']:
        e = d[d.inn_n1.notna()].copy(); e['s1'] = (e[p + '_streak'] == 1).astype(int); e['s2'] = (e[p + '_streak'] == 2).astype(int); e['s3'] = (e[p + '_streak'] >= 3).astype(int)
        m = smf.ols('inn_n1 ~ s1 + s2 + s3 + ' + CTRL, e).fit(cov_type='cluster', cov_kwds=cl(e))
        r[f'{p}: next-run kg after 1 / 2 / 3+ in a row'] = {'1': coef(m, 's1'), '2': coef(m, 's2'), '3+': coef(m, 's3'), 'n': [int(e.s1.sum()), int(e.s2.sum()), int(e.s3.sum())]}
        # context of a single occurrence (interaction with the pattern)
        ctx = {}
        for c in ['firstup', 'dist_up', 'fast_tempo', 'late_prep', 'familiar']:
            mc = smf.ols(f'inn_n1 ~ {p} * {c} + ' + CTRL, e).fit(cov_type='cluster', cov_kwds=cl(e))
            ctx[c] = {'pattern': coef(mc, p), 'pattern x context': coef(mc, f'{p}:{c}'), 'n pattern & context': int((e[p] * e[c]).sum())}
        r[f'{p}: context'] = ctx
        # does it recur? P(same pattern next start | streak) vs base rate
        f = d[d[p + '_next'].notna()]
        r[f'{p}: recurs next start % by streak (0,1,2,3+)'] = [round(100 * f[f[p + '_streak'].clip(upper=3) == k][p + '_next'].mean(), 1) for k in range(4)]
        r[f'{p}: races again within 120 days % by streak (0,1,2,3+)'] = [round(100 * d[d[p + '_streak'].clip(upper=3) == k].races_again_120.mean(), 1) for k in range(4)]
        g3 = d[d.rating_after3.notna()]
        r[f'{p}: rating change over next 3 starts kg by streak (0,1,2,3+)'] = [round(g3[g3[p + '_streak'].clip(upper=3) == k].rating_after3.mean(), 2) for k in range(4)]
    # 'late preparation, familiar distance, repeated flat' (the owner's most concerning case) vs everything else
    e = d[d.inn_n1.notna()].copy(); e['concern'] = ((e.flat_streak >= 2) & (e.late_prep == 1) & (e.familiar == 1)).astype(int)
    m = smf.ols('inn_n1 ~ concern + flat + ' + CTRL, e).fit(cov_type='cluster', cov_kwds=cl(e))
    r["owner's concerning case (2+ flat in a row, 4th run+ of a preparation, familiar distance): next-run kg beyond a single flat run"] = {'coef': coef(m, 'concern'), 'n': int(e.concern.sum())}
    OUT[lab] = r; print(lab, json.dumps(r, default=str)[:4000], flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_deter.json', 'w'), indent=1, default=str)
