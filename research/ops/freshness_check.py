"""Data freshness audit (Batch 23 A2): which of today's runners have run since the rating history cutoff, so their latest run is NOT in
today's assessment? Uses TAB's morning form records (days since last run, career starts) and the rating frame. Collection only: nothing
here changes any rating or forecast. Writes collect/national/<D>/freshness.csv and prints one summary line for the log.
Usage (from research/): python3 ops/freshness_check.py <YYYYMMDD> [frame=engine/frames/national_c2.parquet]"""
import sys, re, json, glob, numpy as np, pandas as pd
D = sys.argv[1]; FR = sys.argv[2] if len(sys.argv) > 2 else 'engine/frames/national_c2.parquet'
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
day = pd.Timestamp(f'{D[:4]}-{D[4:6]}-{D[6:]}')
f = f'collect/national/{D}/form_runners.csv'
try: T = pd.read_csv(f)
except FileNotFoundError: print(f'freshness: no form records for {D}'); sys.exit(0)
H = pd.read_parquet(FR, columns=['horse', 'date']); cutoff = H.date.max()
last = H.groupby('horse').date.agg(['max', 'size']).rename(columns={'max': 'last_held', 'size': 'runs_held'})
T['horse'] = T.name.map(nk); T = T.join(last, on='horse')
T['days_since_last_run'] = T.days_since_last_run.where(T.days_since_last_run > 0)   # TAB shows 0 for first starters and unknowns: unknown, not 'ran today'
import gzip
scr = set()
for b in glob.glob(f'collect/national/{D}/bundles/*pre_{D}_snap*.jsonl.gz'):
    for l in gzip.open(b, 'rt'):
        for s_ in (json.loads(l)['value'].get('scratchings') or []): scr |= {nk(h['horse']) for h in s_['horses']}
T['listed_scratched'] = T.horse.isin(scr)
T['tab_last_start'] = day - pd.to_timedelta(T.days_since_last_run, unit='D')
T['recent_run_missing'] = T.tab_last_start.notna() & (T.tab_last_start > cutoff) & ~T.listed_scratched
T['backing_up_within_7d'] = (T.days_since_last_run <= 7) & ~T.listed_scratched
T['tab_minus_held'] = T.career_starts - T.runs_held.fillna(0)
P = sorted(glob.glob(f'collect/national/{D}/form_past_starts.csv'))
if P:
    ps = pd.read_csv(P[0]); ps['d'] = pd.to_datetime(ps.start_date, errors='coerce')
    after = ps[(ps.d > cutoff) & (ps.start_type.astype(str).str.lower() != 'trial')].groupby(['ven', 'race', 'n']).size().rename('form_lines_after_cutoff')
    T = T.join(after, on=['ven', 'race', 'n'])
out = T[['ven', 'race', 'n', 'name', 'days_since_last_run', 'tab_last_start', 'last_held', 'runs_held', 'career_starts', 'tab_minus_held', 'listed_scratched', 'recent_run_missing', 'backing_up_within_7d'] + (['form_lines_after_cutoff'] if P else [])]
out.to_csv(f'collect/national/{D}/freshness.csv', index=False)
print(f"freshness {D}: history cutoff {cutoff.date()}; {int(T.recent_run_missing.sum())} of {len(T)} runners have run since it (latest run not in ratings); "
      f"{int(T.backing_up_within_7d.sum())} backing up within 7 days; {int(((T.tab_minus_held > 0) & ~T.listed_scratched).sum())} with more TAB starts than runs held (listed scratchings excluded)")
