"""Batch 14 s11/s12: jockey distance specialisation and workload across a meeting. All states (national v3 frame, Oct 2022 - Nov 2026).
Measure throughout: the run's rating surprise (dyn_nat_inn, kg) = how much better or worse the horse ran than its own pre-race rating said,
relative to the field. The horse's ability is already in its rating, so this is a horse-quality-adjusted measure; the existing dynamic
jockey assessment (j_surp: the jockey's recent average surprise) is the production comparison.
s11 distance specialisation: bands sprint (<=1200 m), middle (1300-1600), staying (1700+).
  a) persistence: a jockey's staying-minus-sprint surprise in 2022-24 vs 2025-26 (jockeys with 40+ rides in each band in each period),
     raw and after removing the trainer's own staying-minus-sprint tendency (stables target distances).
  b) prospective: the jockey's prior band-specific surprise (all earlier rides in that band, shrunk with 60 rides' weight) on top of j_surp.
s12 workload: the jockey's earlier rides at the same meeting (count, metres ridden, staying rides) -> this ride's surprise, compared
  WITHIN each jockey (jockey means removed) with race number, rating band, class and distance controls; also by current distance band and
  for high-volume riders (5+ rides at the meeting); Queensland: scheduled minutes since the previous ride (start times; a labelled proxy).
No market data."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json, re
OUT = {}
def cfit(form, f, key='jkey'):
    import patsy
    y, X = patsy.dmatrices(form, f, return_type='dataframe', NA_action='drop')
    import statsmodels.api as sm
    return sm.OLS(y, X).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.loc[y.index, key])[0]})
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet')
V = V[V.dyn_nat_inn.notna() & V.jkey.notna()].copy(); V['date'] = pd.to_datetime(V.date)
V['band'] = pd.cut(V.distance_m.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
V['per'] = np.where(V.date < '2025-01-01', 'A', 'B'); V['rband'] = pd.qcut(V.dyn_nat, 5, labels=False, duplicates='drop').astype(str)
V['cls'] = V.class_label.fillna('?').astype(str)
# a) persistence of specialisation
def spec(d, key):
    t = d.groupby([key, 'per', 'band']).dyn_nat_inn.agg(['mean', 'size']).unstack('band')
    ok = (t['size'][['sprint', 'staying']] >= 40).all(axis=1); t = t[ok]
    s = (t['mean']['staying'] - t['mean']['sprint']).unstack('per').dropna(); return s
r = {}
s = spec(V, 'jkey'); r['jockeys with 40+ sprint and 40+ staying rides in both periods'] = len(s)
r['raw: correlation 2022-24 vs 2025-26 of staying-minus-sprint surprise'] = round(s['A'].corr(s['B']), 3)
r['raw: sd of staying-minus-sprint across jockeys, kg (A, B)'] = [round(s['A'].std(), 2), round(s['B'].std(), 2)]
# sampling noise alone: sd expected from rides (per-ride sd ~5.3 kg)
tt = V.groupby(['jkey', 'per', 'band']).size().unstack('band')
# remove trainer tendency: surprise minus the trainer's band mean (shrunk 30 rides) within period
tb = V.groupby(['tkey', 'per', 'band']).dyn_nat_inn.agg(['sum', 'count']).reset_index(); tb['t_adj'] = tb['sum'] / (tb['count'] + 30)
V = V.merge(tb[['tkey', 'per', 'band', 't_adj']], on=['tkey', 'per', 'band'], how='left'); V['inn_tadj'] = V.dyn_nat_inn - V.t_adj.fillna(0)
s2 = V.assign(dyn_nat_inn=V.inn_tadj).pipe(spec, 'jkey'); r['trainer-adjusted: correlation 2022-24 vs 2025-26'] = round(s2['A'].corr(s2['B']), 3)
# trainer persistence for comparison
st = spec(V, 'tkey'); r['trainers (same test): correlation'] = (round(st['A'].corr(st['B']), 3), len(st))
# split-half within period A (odd/even rides) as an upper bound on reliability
VA = V[V.per == 'A'].sort_values('date').copy(); VA['half'] = VA.groupby(['jkey', 'band']).cumcount() % 2; VA['per'] = VA.half.map({0: 'A', 1: 'B'})
sh = spec(VA, 'jkey'); r['split-half within 2022-24 (odd vs even rides): correlation'] = (round(sh['A'].corr(sh['B']), 3), len(sh))
OUT['s11 persistence'] = r; print(json.dumps(r), flush=True)
# b) prospective value on top of j_surp: prior band-specific jockey surprise (strictly earlier dates), shrunk
V = V.sort_values(['date', 'race_no']).reset_index(drop=True)
day = V.groupby(['jkey', 'band', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
day['csum'] = day.groupby(['jkey', 'band'])['sum'].cumsum() - day['sum']; day['ccnt'] = day.groupby(['jkey', 'band'])['count'].cumsum() - day['count']
dall = V.groupby(['jkey', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
dall['asum'] = dall.groupby('jkey')['sum'].cumsum() - dall['sum']; dall['acnt'] = dall.groupby('jkey')['count'].cumsum() - dall['count']
V = V.merge(day[['jkey', 'band', 'date', 'csum', 'ccnt']], on=['jkey', 'band', 'date'], how='left').merge(dall[['jkey', 'date', 'asum', 'acnt']], on=['jkey', 'date'], how='left')
V['j_band'] = V.csum / (V.ccnt + 60); V['j_all'] = V.asum / (V.acnt + 60); V['j_spec'] = V.j_band - V.j_all       # band-specific minus overall (both shrunk)
e = V[(V.acnt >= 100) & V.j_surp.notna()].copy()
res = {}
for lab, f in [('all 2023-26', e[e.date >= '2023-07-01']), ('2025-26', e[e.date >= '2025-01-01'])]:
    m = cfit('dyn_nat_inn ~ j_surp + j_all + j_spec + C(band) + C(rband) + C(state)', f)
    res[lab] = {k: (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in ['j_surp', 'j_all', 'j_spec']}
    res[lab]['rides'] = len(f); res[lab]['sd of j_spec kg'] = round(f.j_spec.std(), 3)
OUT['s11 prospective (kg per 1 kg of prior surprise)'] = res; print(json.dumps(res), flush=True)
# tracking: is a jockey's late speed retention (hold) repeatable within the same horse? by band (Qld)
try:
    T = pd.read_parquet('/home/claude/b14/runs_QLD.parquet'); T = T.rename(columns={'field_x': 'field'})
    for v in ['v400', 'v200']: T[v + 'r'] = T[v] - T.groupby('race_id')[v].transform('median')
    T['hold'] = T.v200r - T.v400r; T = T.dropna(subset=['hold', 'jkey']); T['hold_wh'] = T.hold - T.groupby('horse').hold.transform('mean')
    T['band'] = pd.cut(T.d.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
    hh = {}
    for b in ['sprint', 'middle', 'staying', 'all']:
        tb_ = T if b == 'all' else T[T.band == b]
        g = tb_.groupby('jkey').filter(lambda x: len(x) >= 60).sort_values('meeting_date').copy(); g['half'] = g.groupby('jkey').cumcount() % 2
        p = g.groupby(['jkey', 'half']).hold_wh.mean().unstack().dropna(); hh[b] = (round(p[0].corr(p[1]), 3), len(p))
    OUT['Qld tracking: jockey late-retention (within-horse) split-half r, jockeys with 60+ rides'] = hh; print(json.dumps(hh), flush=True)
except Exception as ex: print('tracking part failed', ex)
# s12 workload
W = V.sort_values(['jkey', 'meeting_id', 'race_no']).copy(); g = W.groupby(['jkey', 'meeting_id'])
W['ride_idx'] = g.cumcount(); W['dist_before'] = g.distance_m.cumsum().astype(float) - W.distance_m.astype(float)
W['stay_before'] = (W.band == 'staying').astype(int).groupby([W.jkey, W.meeting_id]).cumsum() - (W.band == 'staying').astype(int)
W['rides_meeting'] = g.race_no.transform('size'); W['inn_wj'] = W.dyn_nat_inn - W.groupby('jkey').dyn_nat_inn.transform('mean')
W['ride_c'] = W.ride_idx.clip(upper=6).astype(str); W['race_no_c'] = W.race_no.clip(upper=10).astype(str)
wk = {}
for lab, f in [('all rides', W), ('high-volume meetings (5+ rides)', W[W.rides_meeting >= 5])]:
    m = cfit('inn_wj ~ C(ride_c) + C(race_no_c) + C(rband) + C(band) + C(state) + field', f)
    wk[lab] = {k.replace('C(ride_c)[T.', 'earlier rides = ').replace(']', ''): (round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)) for k in m.params.index if 'ride_c' in k}
    wk[lab]['rides'] = len(f)
    m2 = cfit('inn_wj ~ I(dist_before/1000) + stay_before + C(race_no_c) + C(rband) + C(band) + C(state) + field', f)
    wk[lab]['per 1,000 m ridden earlier'] = tuple(round(x, 3) for x in [m2.params['I(dist_before / 1000)'], *m2.conf_int().loc['I(dist_before / 1000)']])
    wk[lab]['per staying ride earlier'] = tuple(round(x, 3) for x in [m2.params['stay_before'], *m2.conf_int().loc['stay_before']])
for b in ['sprint', 'middle', 'staying']:
    f = W[W.band == b]; m2 = cfit('inn_wj ~ I(dist_before/1000) + C(race_no_c) + C(rband) + C(state) + field', f)
    wk[f'current race {b}: per 1,000 m ridden earlier'] = tuple(round(x, 3) for x in [m2.params['I(dist_before / 1000)'], *m2.conf_int().loc['I(dist_before / 1000)']])
# individual jockeys: is a workload slope a repeatable trait? (slope in 2022-24 vs 2025-26, jockeys with 300+ rides after a 3rd ride in each)
sl = {}
for per in ['A', 'B']:
    f = W[W.per == per]; s_ = f.groupby('jkey').apply(lambda x: np.polyfit(x.dist_before / 1000, x.inn_wj, 1)[0] if (x.dist_before > 0).sum() >= 300 else np.nan); sl[per] = s_
sl = pd.DataFrame(sl).dropna(); wk['individual workload slopes: correlation 2022-24 vs 2025-26'] = (round(sl.A.corr(sl.B), 3), len(sl))
# Queensland scheduled intervals (start times are scheduled, not actual: a proxy)
try:
    import duckdb
    c = duckdb.connect('/home/claude/racing-intelligence/history/history.duckdb', read_only=True)
    st_ = c.execute("select race_id q_race_id, meeting_date, start_time from race").fetchdf()
    st_['t'] = pd.to_datetime(st_.meeting_date.astype(str) + ' ' + st_.start_time.astype(str), format='%Y-%m-%d %I:%M%p', errors='coerce')
    Wq = W[W.state == 'QLD'].merge(st_[['q_race_id', 't']], on='q_race_id', how='inner').sort_values(['jkey', 'meeting_id', 't'])
    Wq['mins_since'] = Wq.groupby(['jkey', 'meeting_id']).t.diff().dt.total_seconds() / 60
    f = Wq[Wq.mins_since.between(15, 240)].copy(); f['gap_c'] = pd.cut(f.mins_since, [14, 35, 50, 80, 240]).astype(str)
    m3 = cfit('inn_wj ~ C(gap_c) + I(dist_before/1000) + C(race_no_c) + C(rband) + C(band) + field', f)
    wk['Qld: scheduled minutes since previous ride (vs 15-35 min)'] = {k: (round(m3.params[k], 3), round(m3.conf_int().loc[k, 0], 3), round(m3.conf_int().loc[k, 1], 3)) for k in m3.params.index if 'gap_c' in k}
    wk['Qld: rides with a previous ride at the meeting'] = len(f)
except Exception as ex: wk['Qld intervals'] = 'failed: ' + str(ex)[:120]
OUT['s12 workload (kg, within-jockey)'] = wk; print(json.dumps(wk, default=str), flush=True)
json.dump(OUT, open('/home/claude/racing-intelligence/research/batch14/out_jockey.json', 'w'), indent=1, default=str)
