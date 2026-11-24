"""Build one row per Queensland starter with research features.
Usage: python3 build_runs.py ../history/history.duckdb runs.parquet
Everything derived from history.duckdb (RQ tracking + Race Fields + Betfair runners, no prices)."""
import sys, re, duckdb, pandas as pd, numpy as np
db, out = sys.argv[1], sys.argv[2]
c = duckdb.connect(db, read_only=True)

race = c.execute("select race_id, meeting_date, track, race_no, race_name, distance_m, track_rating_tracking cond_raw, rail, race_time_s from race").fetchdf()
def cond(s):
    s = s.lower() if isinstance(s, str) else ''
    m = re.search(r'(good|soft|heavy|firm|synthetic|awt)\s*\(?\s*(\d+)?', s)
    if not m: return pd.Series([None, None])
    g = m.group(1); n = int(m.group(2)) if m.group(2) else None
    if g in ('synthetic','awt'): return pd.Series(['Synthetic', None])
    return pd.Series([g.title(), n])
race[['cond_group','cond_num']] = race['cond_raw'].apply(cond)
race['is_poly'] = race['track'].str.contains('Poly') | (race['cond_group'] == 'Synthetic')
# class from race name (descriptive only)
def cls(n):
    n = n.upper() if isinstance(n, str) else ''
    for pat, lab in [(r'MAIDEN', 'Maiden'), (r'CLASS\s*(\d)', 'Class'), (r'BENCHMARK\s*(\d+)|BM\s*(\d+)', 'BM'), (r'GROUP\s*([123])|\bG([123])\b', 'Group'), (r'LISTED', 'Listed'), (r'RESTRICTED|RST', 'Restricted'), (r'OPEN|QUALITY|HANDICAP', 'Open/Hcp')]:
        m = re.search(pat, n)
        if m:
            num = next((g for g in m.groups() if g), None) if m.groups() else None
            return pd.Series([lab, int(num) if num else None])
    return pd.Series(['Other', None])
race[['class_group','class_num']] = race['race_name'].apply(cls)

st = c.execute("""select race_id, saddlecloth, name, name_key, horse_code, scratched, finish_pos, margin_l, finish_time_s,
                  ground_m, result_state, barrier, weight_kg, jockey, trainer from starter""").fetchdf()
st = st[~st['scratched'].fillna(False) & st['result_state'].isin(['Finished','DidNotFinish','DidNotTrack','Disqualified'])].copy()
# horse identity: numeric code; AUS- codes mapped to the numeric code used by the same name elsewhere (H3 check: 2553/2554 stable)
num = st[st['horse_code'].str.fullmatch(r'\d+', na=False)].groupby('name_key')['horse_code'].agg(lambda s: s.value_counts().index[0])
nunique = st[st['horse_code'].str.fullmatch(r'\d+', na=False)].groupby('name_key')['horse_code'].nunique()
st['horse_id'] = np.where(st['horse_code'].str.fullmatch(r'\d+', na=False), st['horse_code'],
                          st['name_key'].map(num.where(nunique == 1)))
st['horse_id'] = st['horse_id'].fillna('N:' + st['name_key'])

df = st.merge(race, on='race_id', how='left')
df['field'] = df.groupby('race_id')['saddlecloth'].transform('count')
df['finished'] = df['result_state'].eq('Finished')
df['win'] = (df['finish_pos'] == 1).astype(int)
df['top3'] = (df['finish_pos'] <= 3).astype(int)
df['finish_pct'] = np.where(df['field'] > 1, (df['finish_pos'] - 1) / (df['field'] - 1), np.nan)
df.loc[~df['finished'], 'finish_pct'] = np.nan
# effective barrier: rank of drawn barrier among actual starters (handles scratchings)
df['eff_barrier'] = df.groupby('race_id')['barrier'].rank(method='first')
df['rel_barrier'] = np.where(df['field'] > 1, (df['eff_barrier'] - 1) / (df['field'] - 1), np.nan)

# sectionals: L600, positions at 800/400 to go, ground covered
sec = c.execute("select race_id, saddlecloth, segment_end_m, ground_m seg_ground, position, inter_s, split_s from sectional").fetchdf()
sec = sec.merge(race[['race_id','distance_m']], on='race_id')
sec['to_go'] = sec['distance_m'] - sec['segment_end_m']
fin = sec[sec['to_go'] == 0][['race_id','saddlecloth','inter_s']].rename(columns={'inter_s':'t_fin'})
def at(togo, col, name):
    x = sec[sec['to_go'] == togo][['race_id','saddlecloth',col]].rename(columns={col:name}); return x
f = fin.merge(at(600,'inter_s','t600'), on=['race_id','saddlecloth'], how='left') \
       .merge(at(800,'position','pos800'), on=['race_id','saddlecloth'], how='left') \
       .merge(at(400,'position','pos400'), on=['race_id','saddlecloth'], how='left')
# settling position: position ~400m after the start (first segment ending at >=400m)
early = sec[sec['segment_end_m'] >= 400].sort_values('segment_end_m').groupby(['race_id','saddlecloth']).head(1)[['race_id','saddlecloth','position']].rename(columns={'position':'pos_settle'})
f = f.merge(early, on=['race_id','saddlecloth'], how='left')
f['l600'] = f['t_fin'] - f['t600']
df = df.merge(f[['race_id','saddlecloth','l600','pos800','pos400','pos_settle']], on=['race_id','saddlecloth'], how='left')
ok = df['finished'] & df['l600'].between(30, 50)
df.loc[~ok, 'l600'] = np.nan
df['l600_rank'] = df.groupby('race_id')['l600'].rank(method='min')
df['l600_vs_best'] = df['l600'] - df.groupby('race_id')['l600'].transform('min')
df['l600_vs_winner'] = df['l600'] - df['race_id'].map(df[df['win'] == 1].groupby('race_id')['l600'].first())
df['ground_extra'] = df['ground_m'] - df.groupby('race_id')['ground_m'].transform('min')
df.loc[~df['finished'] | (df['ground_m'] < df['distance_m'] * 0.95), 'ground_extra'] = np.nan
df['settle_rel'] = np.where(df['field'] > 1, (df['pos_settle'] - 1) / (df['field'] - 1), np.nan)
df['leader_settle'] = (df['pos_settle'] == 1).astype(float).where(df['pos_settle'].notna())
df['leader_800'] = (df['pos800'] == 1).astype(float).where(df['pos800'].notna())

# days since previous start, using every Australian TAB start in Betfair (all states) plus these Qld starts
bf = c.execute("select meeting_date, name_key from bf_runner where state <> 'NZ'").fetchdf()
allstarts = pd.concat([bf, df[['meeting_date','name_key']]]).drop_duplicates()
allstarts = allstarts.sort_values(['name_key','meeting_date'])
allstarts['prev_date'] = allstarts.groupby('name_key')['meeting_date'].shift()
df = df.merge(allstarts, on=['meeting_date','name_key'], how='left')
df['days_since'] = (pd.to_datetime(df['meeting_date']) - pd.to_datetime(df['prev_date'])).dt.days
bf_first = bf['meeting_date'].min()
df.loc[pd.to_datetime(df['prev_date']).isna() & (pd.to_datetime(df['meeting_date']) < pd.Timestamp(bf_first) + pd.Timedelta(days=400)), 'days_since'] = np.nan

# next Queensland start for the same horse
df = df.sort_values(['horse_id','meeting_date','race_no'])
for col in ['race_id','meeting_date','win','finish_pct','field','distance_m','track','class_group','class_num','days_since','finished','margin_l']:
    df['next_' + col] = df.groupby('horse_id')[col].shift(-1)
df['gap_to_next'] = (pd.to_datetime(df['next_meeting_date']) - pd.to_datetime(df['meeting_date'])).dt.days
df['year'] = pd.to_datetime(df['meeting_date']).dt.year
df['split'] = np.where(df['year'] >= 2026, 'holdout_2026', 'explore_2022_2025')
df.to_parquet(out, index=False)
print(len(df), 'rows;', df['race_id'].nunique(), 'races;', df['horse_id'].nunique(), 'horses')
print(df[['l600','pos800','pos_settle','ground_extra','days_since','next_win']].notna().mean().round(3).to_dict())
print(df.groupby('split').size().to_dict())
