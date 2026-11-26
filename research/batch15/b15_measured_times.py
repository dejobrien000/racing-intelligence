"""Batch 15 (brief s6): measured individual times vs official margins (Qld tracking Oct 2022-Nov 2026, SA tracking Jan 2024-Nov 2026,
Victorian TripleS sections where held). Research only.
1. Dependence: are the official margins themselves derived from the measured times? Per race, official margin (lengths) regressed on the
   measured time behind the winner (s). If R2 ~ 1 the two are the same measurement, not independent confirmation.
2. Independent information: D = official margin - measured gap in lengths (gap s / 0.170 s per length, the Engine v2.3 conversion), in kg
   (x kg per length). D > 0: the official margin says the horse was beaten further than the clock does.
3. Does D predict the next run better than the rating (production rating surprise next start)? If the clock carries information the
   margins miss, horses the margin under-credited (D > 0) should beat their rating next time. Controls: this run's surprise, field size,
   distance band, margin size; cluster-robust by horse.
4. Where the two disagree: by margin size (close finishes, 3-10 L, 10 L+ where margins are coarse and capped at 25 L in the rating).
Rating used: the national rating each state is rated on in production (Qld v3 frame for Qld rows as used by Engine v2.1.3; SA from the
Engine v2.3 frame). Measured gaps are never filled in where a time is missing."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
OUT = {}
C2 = pd.read_parquet('/home/claude/b14/b15_resp.parquet', columns=['race_id', 'horse', 'dyn_nat_inn', 'inn1', 'next5_inn'])
def load(st):
    R = pd.read_parquet(f'/home/claude/b14/runs_{st}.parquet', columns=['race_id', 'nat_race', 'horse', 'fp', 'm', 't', 'margin_l', 'distance_m', 'dyn_nat_inn', 'inn_n1', 'next3', 'meeting_date', 'field_x'])
    R = R.rename(columns={'field_x': 'field'})
    R = R[R.t.notna() & (R.t > 0)].copy()
    R['t_win'] = R.groupby('race_id').t.transform(lambda s: s[R.loc[s.index, 'fp'] == 1].min() if (R.loc[s.index, 'fp'] == 1).any() else np.nan)
    R['gap_s'] = R.t - R.t_win
    R = R[R.gap_s.notna() & (R.gap_s >= -0.05)]
    if st == 'SA':   # production SA rating = Engine v2.3 frame
        R = R.drop(columns=['dyn_nat_inn', 'inn_n1']).merge(C2.rename(columns={'race_id': 'nat_race', 'inn1': 'inn_n1'})[['nat_race', 'horse', 'dyn_nat_inn', 'inn_n1']], on=['nat_race', 'horse'], how='left')
    R['kgpl'] = 1.5 * (1200 / R.distance_m) ** 0.8; R['gapL'] = R.gap_s / 0.170
    R['D_L'] = R.margin_l - R.gapL; R['D_kg'] = R.D_L * R.kgpl
    R['state'] = st; R['yr'] = pd.to_datetime(R.meeting_date).dt.year
    return R
A = pd.concat([load('QLD'), load('SA')], ignore_index=True)
for st, R in A.groupby('state'):
    r = {}
    nw = R[R.fp > 1]
    # 1 dependence, pooled and within race
    m = smf.ols('margin_l ~ gap_s', nw).fit(); r['official margin vs measured gap: R2, lengths per second'] = [round(m.rsquared, 4), round(m.params['gap_s'], 2)]
    w = nw.groupby('race_id').apply(lambda g: np.corrcoef(g.margin_l, g.gap_s)[0, 1] if len(g) >= 4 and g.gap_s.std() > 0 else np.nan)
    r['within-race correlation of margin and measured gap: median, 5th percentile'] = [round(float(w.median()), 4), round(float(w.quantile(0.05)), 4)]
    implied = (nw.gap_s / nw.margin_l.replace(0, np.nan)).where(nw.margin_l >= 1)
    r['implied seconds per length (official margins 1 L+): median, IQR'] = [round(float(implied.median()), 3), round(float(implied.quantile(0.25)), 3), round(float(implied.quantile(0.75)), 3)]
    r['share of runs where margin and clock disagree by more than 0.5 L (after the 0.170 s/L conversion)'] = round(float((nw.D_L.abs() > 0.5).mean() * 100), 1)
    r['sd of disagreement D (kg) vs sd of margin-based performance (kg)'] = [round(float(nw.D_kg.std()), 2), round(float((nw.margin_l.clip(upper=25) * nw.kgpl).std()), 2)]
    # by margin size
    nw = nw.assign(mb=pd.cut(nw.margin_l, [0, 3, 10, 25, 99], labels=['<3 L', '3-10 L', '10-25 L', '25 L+']))
    r['disagreement by margin size: mean D (L), mean |D| (L), runs'] = {str(k): [round(float(g.D_L.mean()), 2), round(float(g.D_L.abs().mean()), 2), int(len(g))] for k, g in nw.groupby('mb', observed=True)}
    # 3 predictive value
    d = nw.copy(); d['D_kg_c'] = d.D_kg.clip(-15, 15); d['dband'] = pd.cut(d.distance_m, [0, 1150, 1450, 1750, 9999]).astype(str)
    d = d.dropna(subset=['inn_n1', 'dyn_nat_inn', 'D_kg_c', 'field', 'mb'])
    for per, dd in [('all', d), ('2022-24', d[d.yr <= 2024]), ('2025-26', d[d.yr >= 2025])]:
        if len(dd) < 2000: continue
        mm = smf.ols('inn_n1 ~ D_kg_c + dyn_nat_inn + C(mb) + field + C(dband)', dd).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(dd.horse)[0]})
        r[f'next-run surprise per kg of D (+ = clock says better than the margin), {per}'] = [round(mm.params['D_kg_c'], 3), round(mm.conf_int().loc['D_kg_c', 0], 3), round(mm.conf_int().loc['D_kg_c', 1], 3), int(mm.nobs)]
    for lab, dd in d.groupby('mb', observed=True):
        if len(dd) < 1500: continue
        mm = smf.ols('inn_n1 ~ D_kg_c + dyn_nat_inn + field', dd).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(dd.horse)[0]})
        r[f'... within margin band {lab}'] = [round(mm.params['D_kg_c'], 3), round(mm.conf_int().loc['D_kg_c', 0], 3), round(mm.conf_int().loc['D_kg_c', 1], 3), int(mm.nobs)]
    OUT[st] = r; print(st, json.dumps(r, default=str), flush=True)
# Victoria: TripleS sections (user-supplied files) vs the national (Breednet) margins where both exist
try:
    S = pd.read_csv('staging/vic_triples/sections.csv.gz'); fin = S.sort_values('section_end_m').groupby(['meeting_id', 'race_no', 'horse']).cum_time_s.last().reset_index()
    fin['t_win'] = fin.groupby(['meeting_id', 'race_no']).cum_time_s.transform('min'); fin['gap_s'] = fin.cum_time_s - fin.t_win
    OUT['VIC'] = {'races with TripleS finishing times': int(fin.groupby(['meeting_id', 'race_no']).ngroups), 'runners': int(len(fin)),
                  'note': 'too few races for the predictive test; linked to official margins in a later step if the national rows can be matched'}
except Exception as e: OUT['VIC'] = str(e)[:200]
json.dump(OUT, open('batch15/out_measured_times.json', 'w'), indent=1, default=str)
A.to_parquet('/home/claude/b14/b15_measured.parquet')
