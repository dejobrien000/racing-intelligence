"""Rating-engine lab: one place that builds the point-in-time national frame every engine experiment uses.
- national runs (Qld tracked + Breednet NSW/Vic/ACT; jump-outs excluded upstream), course configuration, going band, distance band
- a dynamic opposition-aware rating (frozen params by default; any runner function/params can be swapped in)
- horse records (course config / going band / distance band, k = 1), last-start surprise, rating trajectory, head-to-head
- NEW families: jockey and trainer (point-in-time mean rating surprise of their earlier rides/runners, shrunk), jockey change,
  age, sex, weight change, class (benchmark) change, distance change
Everything at row i uses only races dated before row i's race (records/h2h/jockey use cumulative sums minus the current row;
same-day rows of other races are NOT used because they are grouped by date below where it matters)."""
import re, json, duckdb, numpy as np, pandas as pd
import dyn_rating as DR, dyn_rating_innov as DI
NAMEVAR = {'royal-randwick': 'randwick', 'canterbury-park': 'canterbury', 'the-valley': 'moonee-valley', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill', 'beaumont-newcastle': 'beaumont', 'newcastle-beaumont': 'beaumont'}
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
def person_key(s):
    """'Ms Angela Jones' / 'A Jones' / 'Angela Jones (a2)' -> 'a jones'. Partnerships keep the first named person's initial + last surname."""
    if s is None or (isinstance(s, float) and s != s): return None
    t = re.sub(r'\(.*?\)', ' ', str(s)); t = re.sub(r'\b(ms|mr|mrs|miss|dr)\b\.?', ' ', t, flags=re.I); t = re.sub(r'[^A-Za-z&\' -]', ' ', t).strip()
    w = [x for x in re.split(r'[\s&]+', t) if x]
    if not w: return None
    return (w[0][0] + ' ' + w[-1]).lower().replace("'", '')
PN_FROZEN = json.load(open('benchmarks/candidates_national_common/manifest.json'))['dynamic_rating_params']

def base_frame():
    U = pd.read_parquet('national_runs.parquet'); U['row_id'] = np.arange(len(U))
    con = duckdb.connect('../history/history.duckdb', read_only=True)
    bm = con.execute("select meeting_date, bf_track_slug venue, slug, state from bn_meeting").fetchdf(); bm['date'] = pd.to_datetime(bm.meeting_date)
    bm1 = bm.drop_duplicates(['date', 'venue']); bm1['config'] = bm1.slug.map(lambda s: NAMEVAR.get(s, s))
    U['date'] = pd.to_datetime(U.date)
    U = U.merge(bm1[['date', 'venue', 'config', 'slug']], on=['date', 'venue'], how='left')
    qt = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'track', 'cond_group', 'jockey', 'trainer', 'barrier', 'pos_settle', 'l600_vs_best', 'ground_extra']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id', 'barrier': 'q_barrier'})
    U = U.merge(qt, on=['q_race_id', 'q_horse_id'], how='left')
    U.loc[U.state == 'QLD', 'config'] = U.track; U['config'] = U.config.fillna(U.venue)
    # Breednet runner details (jockey, trainer, age, sex) for NSW/Vic/ACT rows by meeting slug + race + horse; Qld rows get age/sex by date + horse
    br = con.execute("select meeting_date, slug, race_no, name_key, jockey bj, trainer bt, age, sex from bn_runner").fetchdf()
    br['date'] = pd.to_datetime(br.meeting_date); br['horse'] = br.name_key.map(nk)
    nq = br.drop_duplicates(['date', 'slug', 'race_no', 'horse'])
    U = U.merge(nq[['date', 'slug', 'race_no', 'horse', 'bj', 'bt', 'age', 'sex']], on=['date', 'slug', 'race_no', 'horse'], how='left')
    qa = br.merge(bm[bm.state == 'QLD'][['date', 'slug']].drop_duplicates(), on=['date', 'slug']).drop_duplicates(['date', 'horse'])[['date', 'horse', 'age', 'sex']].rename(columns={'age': 'qage', 'sex': 'qsex'})
    U = U.merge(qa, on=['date', 'horse'], how='left')
    U['age'] = U.age.fillna(U.qage); U['sex'] = U.sex.fillna(U.qsex)
    U['jkey'] = np.where(U.state == 'QLD', U.jockey.map(person_key), U.bj.map(person_key)); U['tkey'] = np.where(U.state == 'QLD', U.trainer.map(person_key), U.bt.map(person_key))
    gw = U.going.fillna(U.cond_group).astype(str).str.lower()
    U['gband'] = np.select([gw.str.contains('heavy'), gw.str.contains('soft'), gw.str.contains('synth|poly|awt')], ['heavy', 'soft', 'synthetic'], 'good')
    U['dband'] = pd.cut(U.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
    U['wet'] = U.gband.isin(['soft', 'heavy']).astype(float); U['route'] = (U.distance_m >= 1400).astype(float); U['metro'] = (U.tier == 'metro').astype(float)
    U = U.drop_duplicates('row_id').sort_values('row_id').reset_index(drop=True)
    return U.drop(columns=['qage', 'qsex', 'jockey', 'trainer', 'bj', 'bt'])

def add_rating(U, name='dyn_nat', runner=None, params=None, **kw):
    p = params or PN_FROZEN; runner = runner or DI.run
    dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': U.date, 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0),
                       'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
    PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
    out = runner(PN, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'], **kw)
    ix = PN.idx.values; n = np.arange(len(U))
    U[name] = pd.Series(out[0], index=ix).reindex(n).values; U[name + '_sd'] = pd.Series(out[1], index=ix).reindex(n).values; U[name + '_inn'] = pd.Series(out[2], index=ix).reindex(n).values
    return U

def _prior_mean(U, keys, v, k):
    """point-in-time shrunk mean of v over EARLIER DATES within groups `keys` (same-day rows excluded)."""
    vv = v.fillna(0.0); c = v.notna().astype(float)
    d = pd.DataFrame({'g': pd.Series(list(zip(*[U[k_] for k_ in keys])) if len(keys) > 1 else U[keys[0]], index=U.index), 'date': U.date, 'v': vv, 'c': c})
    day = d.groupby(['g', 'date'], sort=False)[['v', 'c']].sum().reset_index().sort_values(['g', 'date'])
    day[['sv', 'sc']] = day.groupby('g')[['v', 'c']].cumsum().values - day[['v', 'c']].values
    m = d[['g', 'date']].merge(day[['g', 'date', 'sv', 'sc']], on=['g', 'date'], how='left')
    return (m.sv / (m.sc + k)).values, m.sc.values

def add_derived(U, rating='dyn_nat', pre=''):
    """records, surprise, trajectory for a given rating column (prefix pre for alternative ratings)."""
    U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse'); inn = U[rating + '_inn']
    v = inn.fillna(0.0); c = inn.notna().astype(int)
    for key, nm in [('config', 'c_rec'), ('gband', 'g_rec'), ('dband', 'd_rec')]:
        grp = [U.horse, U[key]]; U[pre + nm] = (v.groupby(grp).cumsum() - v) / ((c.groupby(grp).cumsum() - c) + 1); U[pre + nm + '_n'] = c.groupby(grp).cumsum() - c
    U[pre + 'surprise_last'] = g[rating + '_inn'].shift()
    U[pre + 'surprise_avg3'] = g[rating + '_inn'].transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
    U[pre + 'dyn_traj'] = U[rating] - g[rating].shift(2)
    return U

def add_people(U, rating='dyn_nat', kj=50, kt=50):
    """jockey / trainer: shrunk mean of the rating surprises of their EARLIER rides/runners (beyond the horse's own rating)."""
    U = U.sort_values(['date', 'race']).reset_index(drop=True); inn = U[rating + '_inn']
    U['j_surp'], U['j_n'] = _prior_mean(U, ['jkey'], inn, kj); U['t_surp'], U['t_n'] = _prior_mean(U, ['tkey'], inn, kt)
    U.loc[U.jkey.isna(), ['j_surp']] = np.nan; U.loc[U.tkey.isna(), ['t_surp']] = np.nan
    U['jt_surp'], U['jt_n'] = _prior_mean(U, ['jkey', 'tkey'], inn, kj)
    U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
    U['j_change'] = U.j_surp - g.j_surp.shift()                 # + = better-performing jockey than last start (by today's numbers for last-start jockey at that time)
    U['same_jockey'] = (U.jkey == g.jkey.shift()).astype(float)
    U['wt_change'] = U.weight_kg - g.weight_kg.shift(); U['dist_change'] = np.log(U.distance_m / g.distance_m.shift())
    bmv = pd.to_numeric(U.bm, errors='coerce'); U['bm_change'] = bmv - g.bm.shift().pipe(pd.to_numeric, errors='coerce')
    U['female'] = U.sex.isin(['m', 'f']).astype(float).where(U.sex.notna()); U['age_n'] = U.age
    U['first_at_course'] = (U.c_rec_n == 0).astype(float) if 'c_rec_n' in U else np.nan
    return U

def add_h2h(U):
    P = U[U.finish_pos.notna() & (U.finish_pos <= U.field)][['race', 'date', 'horse', 'finish_pos']]
    pp = P.merge(P, on=['race', 'date'], suffixes=('', '_o')); pp = pp[pp.horse != pp.horse_o]
    pp['beat'] = np.sign(pp.finish_pos_o - pp.finish_pos); pp = pp.sort_values(['horse', 'horse_o', 'date']); gg = pp.groupby(['horse', 'horse_o'])
    pp['n_prev'] = gg.cumcount(); pp['b_prev'] = gg.beat.cumsum() - pp.beat; pp['h2h'] = pp.b_prev / (pp.n_prev + 1); pp['has_prev'] = (pp.n_prev > 0).astype(int)
    hh = pp.groupby(['race', 'horse']).agg(h2h=('h2h', 'mean'), h2h_pairs=('has_prev', 'sum')).reset_index()
    U = U.drop(columns=[c for c in ['h2h', 'h2h_pairs'] if c in U]).merge(hh, on=['race', 'horse'], how='left'); U.loc[U.h2h_pairs.fillna(0) == 0, 'h2h'] = np.nan
    return U

def build(save='engine/frames/national.parquet'):
    U = base_frame(); U = add_rating(U); U = add_derived(U); U = add_people(U); U = add_h2h(U)
    import os; os.makedirs(os.path.dirname(save), exist_ok=True); U.to_parquet(save); return U

if __name__ == '__main__':
    U = build()
    print(len(U), 'rows'); print(U[['j_surp', 't_surp', 'age_n', 'female', 'h2h', 'surprise_last', 'dyn_traj', 'c_rec']].notna().mean().round(3).to_string())
    print('jockeys', U.jkey.nunique(), 'trainers', U.tkey.nunique())
