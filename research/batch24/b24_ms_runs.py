"""Batch 24 (research only): national run table with the field-strength-adjusted daily variant ('incl_opp' in b24_meeting_speed.py).
Starts from the production Engine v2.3 run table (national_runs_c2.parquet) and changes ONLY the meeting adjustment inside the time
figures: variant = shrunk mean (n + 2) of the meeting's winner-time residuals per km after removing the field-strength effect (pre-race
average rating of each field from the production frame; slope fitted on development races only). fig_n moves by
kgpl * km * (new - old variant) / 0.170; venue offsets are left as fitted (second-order). a_rec, a_best3, fs, a_fs3 and missfig are
then recomputed with the production definitions (national.py). Usage (from research/): python3 batch24/b24_ms_runs.py <out.parquet>"""
import sys, numpy as np, pandas as pd
OUT = sys.argv[1]; spl = 0.170
U = pd.read_parquet('national_runs_c2.parquet')
F = pd.read_parquet('engine/frames/national_c2.parquet', columns=['race', 'horse', 'dyn_nat']).drop_duplicates(['race', 'horse'])
fr = U[['race', 'horse']].merge(F, on=['race', 'horse'], how='left').groupby('race').dyn_nat.mean().rename('field_rating')
r = U[U.win == 1].drop_duplicates('race')[['race', 'venue', 'meeting_id', 'distance_m', 'race_time_s', 'par', 'variant', 'km', 'n_vd', 'period']].copy()
r = r[r.par.notna()].join(fr, on='race'); r['res'] = (r.race_time_s - r.par) / r.km
r['vd'] = r.venue + '|' + r.distance_m.astype(int).astype(str); r['field_rel'] = r.field_rating - r.groupby('vd').field_rating.transform('mean')
dev = r[(r.period == 'development') & r.field_rel.notna() & (r.n_vd >= 8)]
beta = float(np.polyfit(dev.field_rel, dev.res, 1)[0]); r['res_opp'] = r.res - beta * r.field_rel.fillna(0)
g = r.groupby('meeting_id').res_opp; r['v_new'] = g.transform('sum') / (g.transform('count') + 2)
U = U.merge(r[['race', 'v_new']], on='race', how='left'); U['v_new'] = U.v_new.fillna(U.variant)
d = U.kgpl * U.km * (U.v_new - U.variant) / spl
print('beta', round(beta, 4), '| figure change kg: mean', round(float(d.mean()), 3), 'sd', round(float(d.std()), 3), '| runs with figures', int(U.fig_n.notna().sum()))
U['fig_n'] = U.fig_n + d.where(U.fig_n.notna(), 0.0)
U = U.sort_values(['horse', 'date', 'race_no']).reset_index(drop=True)
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
def rec(s):
    a = s.shift().values; out = np.full(len(a), np.nan)
    for i in range(len(a)):
        h = a[max(0, i - 5):i + 1][::-1]; h = h[~np.isnan(h)]
        if len(h): out[i] = np.dot(h, wts[:len(h)]) / wts[:len(h)].sum()
    return pd.Series(out, index=s.index)
g = U.groupby('horse')
U['a_rec'] = g.fig_n.transform(rec); U['a_best3'] = g.fig_n.transform(lambda s: s.shift().rolling(3, min_periods=1).max())
def strength(s):
    s = s.dropna().sort_values(ascending=False); return s.head(max(3, len(s) // 2)).mean() if len(s) >= 3 else np.nan
U['fs'] = U.race.map(U.groupby('race').a_best3.apply(strength)); g = U.groupby('horse')
U['a_fs3'] = g.fs.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
has = U.f_avgfp3.notna(); U['missfig'] = (has & U.a_rec.isna()).astype(float)
U = U.drop(columns=['v_new']); U.to_parquet(OUT); print('written', OUT, len(U))
