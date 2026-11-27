"""Batch 24 Part C8 (preliminary, research only): is there a real meeting-wide surface-speed effect beyond the existing daily variant,
and does estimating it better make time figures more repeatable?
Existing infrastructure (national.py, production figures): par = median winner's time per venue x distance (development races), daily
variant = shrunk mean of the meeting's winner-time residuals per km INCLUDING the race itself, no class/opposition allowance.
Versions compared (all use the same par):
  none      : no meeting adjustment
  existing  : production daily variant (includes the race itself)
  loro      : leave-one-race-out variant (the race cannot create its own reference), same shrinkage (n + 2)
  loro_opp  : leave-one-race-out variant of residuals after removing the field-strength effect (pre-race average rating of the field,
              fitted on development races only); a strong field running fast no longer makes the whole meeting look fast
Evaluation (independent of the engine being assessed): (1) does the LORO meeting mean predict the left-out race's own residual (a real
meeting effect)? (2) repeatability: correlation of a horse's figure with its next figure within 60 days, out-of-sample period only.
Usage (from research/): python3 batch24/b24_meeting_speed.py"""
import pandas as pd, numpy as np, json
U = pd.read_parquet('national_runs_c2.parquet', columns=['race', 'state', 'venue', 'date', 'meeting_id', 'race_no', 'distance_m', 'race_time_s', 'going', 'finish_pos',
                                                         'margin_l', 'weight_kg', 'horse', 'win', 'period', 'par', 'variant', 'km', 'n_vd', 'run_time', 'kgpl', 'bm'])
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'dyn_nat'])
U = U.merge(F.drop_duplicates(['race', 'horse']), on=['race', 'horse'], how='left')
spl, WC = 0.170, 0.25
r = U[U.win == 1].drop_duplicates('race')[['race', 'state', 'venue', 'meeting_id', 'date', 'distance_m', 'race_time_s', 'par', 'variant', 'km', 'n_vd', 'period', 'going']].copy()
r = r[r.par.notna() & (r.n_vd >= 8)]
r['res'] = (r.race_time_s - r.par) / r.km                                   # seconds per km slower than par (+ = slow)
fld = U.groupby('race').dyn_nat.mean().rename('field_rating'); r = r.join(fld, on='race')
r['vd'] = r.venue + '|' + r.distance_m.astype(int).astype(str)
r['field_rel'] = r.field_rating - r.groupby('vd').field_rating.transform('mean')     # field strength relative to the usual field there
dev = r[(r.period == 'development') & r.field_rel.notna()]
beta = float(np.polyfit(dev.field_rel, dev.res, 1)[0])                      # s/km per kg of field strength (expected negative: stronger = faster)
r['res_opp'] = r.res - beta * r.field_rel.fillna(0)
def loro(col):
    g = r.groupby('meeting_id')[col]; s, n = g.transform('sum'), g.transform('count')
    return (s - r[col]) / (n - 1 + 2)
r['v_loro'] = loro('res'); r['v_loro_opp'] = loro('res_opp'); r['n_meet'] = r.groupby('meeting_id').race.transform('count')
out = {'beta_s_per_km_per_kg_field': round(beta, 4), 'races': int(len(r))}
# (1) real meeting effect: does the other races' mean predict this race's residual?
m = r[r.n_meet >= 4]
for c, y in [('v_loro', 'res'), ('v_loro_opp', 'res_opp')]:
    b = np.polyfit(m[c], m[y], 1)[0]; cor = np.corrcoef(m[c], m[y])[0, 1]
    out[f'{c}_predicts_left_out_race'] = {'slope': round(float(b), 3), 'corr': round(float(cor), 3), 'races': int(len(m))}
out['residual_sd_s_per_km'] = round(float(r.res.std()), 3); out['loro_variant_sd'] = round(float(r.v_loro.std()), 3)
# (2) repeatability of figures under each version
U = U.merge(r[['race', 'v_loro', 'v_loro_opp']], on='race', how='left')
U = U[U.par.notna() & (U.n_vd >= 8) & U.finish_pos.notna()].copy()
base = U.kgpl * (U.par - U.run_time) / spl + WC * (U.weight_kg - 57)
vers = {'none': 0.0, 'existing': U.variant, 'loro': U.v_loro, 'loro_opp': U.v_loro_opp}
for k, v in vers.items(): U['fig_' + k] = 100 + base + U.kgpl * (U.km * v) / spl
U = U.sort_values(['horse', 'date', 'race_no']); g = U.groupby('horse')
U['gap'] = (g.date.shift(-1) - U.date).dt.days
rep = {}
for k in vers:
    U['nxt'] = g['fig_' + k].shift(-1); t = U[(U.gap <= 60) & U.nxt.notna() & U['fig_' + k].notna() & (U.period != 'development')]
    rep[k] = {'corr_with_next_figure': round(float(np.corrcoef(t['fig_' + k], t.nxt)[0, 1]), 4), 'pairs': int(len(t))}
out['repeatability_out_of_sample'] = rep
# by state (tracking states are where later sectional work happens)
st = {}
for s_, t0 in U[(U.period != 'development')].groupby('state'):
    st[s_] = {}
    for k in vers:
        nx = t0.groupby('horse')['fig_' + k].shift(-1); gp = (t0.groupby('horse').date.shift(-1) - t0.date).dt.days; ok = nx.notna() & (gp <= 60) & t0['fig_' + k].notna()
        st[s_][k] = round(float(np.corrcoef(t0.loc[ok, 'fig_' + k], nx[ok])[0, 1]), 4) if ok.sum() > 200 else None
out['repeatability_by_state'] = st
print(json.dumps(out, indent=1)); json.dump(out, open('batch24/out_b24_meeting_speed.json', 'w'), indent=1)
