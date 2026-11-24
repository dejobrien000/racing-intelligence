"""Run rating v0: a time-based performance figure for every finisher, in kg-equivalent units (100 = par).

How it works (racing terms):
  1. Each runner's time = winner's time + beaten margin converted to seconds (1 length = 2.4 m at the winner's speed).
  2. Par time for every track x distance = typical winning time after removing the day's track speed and race class.
  3. Daily track variant = how fast the track ran that meeting (average of that day's winners against par and class),
     shrunk towards zero when the meeting has few races. This absorbs going, rail and wind.
  4. Lengths ahead of par are converted to kg with a distance scale (about 1.5 kg per length at 1200 m, less over further),
     and weight carried above 57 kg is added (a horse that carries more weight to the same time ran better).
  rating = 100 + kg_per_length x lengths_ahead_of_par + (weight - 57)

Leakage note: the figure for a run uses only that meeting's results (par/class effects use all years, which is fine for
describing past runs; models that predict must use ratings from runs before the race being predicted, as done below).
Usage: python3 rating_v0.py runs.parquet runs_rated.parquet
"""
import sys, numpy as np, pandas as pd

args = [a for a in sys.argv[1:] if not a.startswith('--fit-until=')]
fit_until = next((a.split('=', 1)[1] for a in sys.argv[1:] if a.startswith('--fit-until=')), None)
src, out = (args[0], args[1]) if len(args) > 1 else ('runs.parquet', 'runs_rated.parquet')
df = pd.read_parquet(src)
for c in ['margin_l', 'distance_m', 'race_time_s', 'weight_kg', 'class_num', 'finish_pos', 'field', 'l600']:
    df[c] = pd.to_numeric(df[c], errors='coerce').astype(float)

def class_bucket(g, n):
    if g == 'Maiden': return 'Maiden'
    if g == 'Class' and n == n: return f'C{int(n)}'
    if g == 'BM' and n == n: return f'BM{int(min(max(n, 45), 90) // 5 * 5)}'
    if g in ('Group', 'Listed'): return 'Stakes'
    return g or 'Other'
df['class_bucket'] = [class_bucket(g, n) for g, n in zip(df['class_group'], df['class_num'])]
df['meeting_id'] = df['meeting_date'].astype(str) + '|' + df['track']

# race-level table: winner's time
race = df[df['win'] == 1][['race_id', 'meeting_id', 'track', 'distance_m', 'race_time_s', 'class_bucket', 'cond_group', 'l600', 'year']].drop_duplicates('race_id').copy()
race['speed'] = race['distance_m'] / race['race_time_s']
race = race[race['speed'].between(14.0, 19.0)].copy()
race['td'] = race['track'] + '|' + race['distance_m'].astype(int).astype(str)
race['km'] = race['distance_m'] / 1000
race['variant'] = 0.0; race['cls'] = 0.0
race['dev'] = True if fit_until is None else (pd.to_datetime(race['meeting_id'].str.split('|').str[0]) <= pd.Timestamp(fit_until))
for it in range(8):
    dv = race[race['dev']]
    race['par'] = race['td'].map(dv.groupby('td')['race_time_s'].median()) if it == 0 else \
        race['td'].map((dv['race_time_s'] - dv['km'] * (dv['variant'] + dv['cls'])).groupby(dv['td']).median())
    resid = (race['race_time_s'] - race['par']) / race['km']            # seconds per km slower than par
    cls = (resid - race['variant'])[race['dev']].groupby(race.loc[race['dev'], 'class_bucket']).median()
    cls = cls - cls.get('BM65', cls.median())                            # BM65 class = 0 reference
    race['cls'] = race['class_bucket'].map(cls)
    g = (resid - race['cls']).groupby(race['meeting_id'])
    race['variant'] = race['meeting_id'].map(g.sum() / (g.count() + 2))  # shrink small meetings towards 0
race['n_td'] = race['td'].map(race[race['dev']].groupby('td')['race_id'].count()).fillna(0)
print('class effects, seconds per km vs BM65 (negative = faster):'); print(cls.sort_values().round(3).to_string())
print('variant sd (s/km):', round(race['variant'].std(), 3), ' track-distance combos:', race['td'].nunique())

d = df.merge(race[['race_id', 'par', 'variant', 'km', 'n_td', 'speed']], on='race_id', how='left')
sec_per_l = 2.4 / d['speed']
d['run_time'] = d['race_time_s'] + d['margin_l'].clip(upper=30) * sec_per_l
d['lengths_vs_par'] = ((d['par'] + d['km'] * d['variant']) - d['run_time']) / sec_per_l
d['kg_per_l'] = 1.5 * (1200 / d['distance_m']) ** 0.8
d['rating'] = 100 + d['kg_per_l'] * d['lengths_vs_par'] + (d['weight_kg'] - 57)
ok = d['finished'] & d['par'].notna() & (d['n_td'] >= 10) & d['margin_l'].notna() & d['weight_kg'].notna()
d.loc[~ok, 'rating'] = np.nan

# early tempo: winner's time to the 600 m mark vs par for that track/distance, after the day's track speed (s per km of the early part)
race['first_part'] = race['race_time_s'] - race['l600']
race['early_km'] = (race['distance_m'] - 600) / 1000
race['fp_par'] = race['td'].map(race[race['dev']].groupby('td')['first_part'].median())
race['tempo'] = ((race['first_part'] - race['fp_par']) / race['early_km']) - race['variant']   # + = slower than usual early
race.loc[race['distance_m'] < 1000, 'tempo'] = np.nan
d = d.merge(race[['race_id', 'tempo']], on='race_id', how='left')
d['tempo_band'] = pd.cut(d['tempo'], [-np.inf, -0.35, 0.35, np.inf], labels=['fast early', 'average early', 'slow early'])
# finishing speed: horse's average speed over the last 600 vs its average speed over the whole race (>100 = finished faster than it travelled)
d['fsp'] = 100 * (600 / d['l600']) / (d['distance_m'] / d['run_time'])

# pre-race ratings (no leakage): every horse's previous ratings in date order
d = d.sort_values(['horse_id', 'meeting_date', 'race_no'])
grp = d.groupby('horse_id')['rating']
d['prev_rating'] = grp.shift()
d['best_last3'] = grp.transform(lambda s: s.shift().rolling(3, min_periods=1).max())
d['avg_last3'] = grp.transform(lambda s: s.shift().rolling(3, min_periods=1).mean())
# field strength = average of the best-of-last-3 pre-race figures of the top half of the field's pre-race figures
def strength(s):
    s = s.dropna().sort_values(ascending=False)
    return s.head(max(3, len(s) // 2)).mean() if len(s) >= 3 else np.nan
fs = d.groupby('race_id')['best_last3'].apply(strength).rename('field_strength')
d = d.merge(fs, on='race_id', how='left')
# next run's rating (for "did the horse improve")
nx = d[['race_id', 'horse_id', 'rating', 'field_strength', 'class_bucket', 'tempo']].rename(columns={'race_id': 'next_race_id', 'rating': 'next_rating', 'field_strength': 'next_field_strength', 'class_bucket': 'next_class_bucket', 'tempo': 'next_tempo'})
d = d.merge(nx, on=['next_race_id', 'horse_id'], how='left')
d.to_parquet(out)
print('rated runs:', int(d['rating'].notna().sum()), 'of', len(d))
