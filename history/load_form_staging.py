"""TAB form-record STAGING inside the master database (Batch 11 follow-up, approved by Damo 25 Nov 2026). Research data only:
nothing here feeds a rating, and it is not a second database. Idempotent: every run rebuilds the staging tables from all
saved daily form files (collect/national/<D>/form_runners.csv + form_past_starts.csv, written by ops/parse_form.py).

Tables
  stg_form_runner   one row per runner form record captured (date captured, meeting, race, number): TAB career starts/wins/places,
                    runs since spell, days since last run, blinkers, class level, sire, dam, trainer (when captured), provenance.
  stg_form_start    one row per past start (race or trial) listed by TAB, de-duplicated across capture days: date, venue, distance,
                    class, finish, starters, margin, positions in running, track condition, time as published, rider, raw stewards'
                    comment, provenance. TAB lists a SHORTENED history: these are never a complete career.
  stg_career        per horse (latest capture): TAB career starts vs race starts we hold since Oct 2022, and a completeness flag.
  stg_form_check    agreement between TAB's listed race starts and our own results (same horse, same date): finish position match.
Horse key: name key + dam key when TAB gave the dam (pedigree identifies a horse better than its name), else name key only.
Survivor bias: form records exist only for horses still racing; use them for counts, labels and raw text, not to re-rate past races.
Usage: python3 history/load_form_staging.py <history.duckdb> <collect/national dir>"""
import sys, os, re, glob, hashlib, datetime as dt
import duckdb, pandas as pd
DB, BASE = sys.argv[1], sys.argv[2]
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper())) if isinstance(s, str) else None
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()[:16]
R, P = [], []
for f in sorted(glob.glob(os.path.join(BASE, '*', 'form_runners.csv'))):
    d = os.path.basename(os.path.dirname(f)); pf = f.replace('form_runners.csv', 'form_past_starts.csv')
    r = pd.read_csv(f, dtype=str); r['capture_day'] = d; r['source_file'] = f; r['file_sha256'] = sha(f); R.append(r)
    if os.path.exists(pf):
        p = pd.read_csv(pf, dtype=str); p['capture_day'] = d; p['source_file'] = pf; p['file_sha256'] = sha(pf); P.append(p)
if not R: print('form staging: no form files yet'); sys.exit(0)
R = pd.concat(R, ignore_index=True); P = pd.concat(P, ignore_index=True) if P else pd.DataFrame()
for c in ['sire', 'dam', 'trainer']:
    if c not in R: R[c] = None
R['name_key'] = R.name.map(nk); R['dam_key'] = R.dam.map(nk); R['horse_key'] = R.name_key + '|' + R.dam_key.fillna('')
R = R.drop_duplicates(['capture_day', 'ven', 'race', 'n'], keep='last')
for c in ['career_starts', 'career_wins', 'career_places', 'runs_since_spell', 'days_since_last_run']: R[c] = pd.to_numeric(R[c], errors='coerce')
if len(P):
    P = P.merge(R[['capture_day', 'ven', 'race', 'n', 'horse_key', 'name_key']], on=['capture_day', 'ven', 'race', 'n'], how='left')
    P['start_date'] = pd.to_datetime(P.start_date, errors='coerce').dt.date
    P['is_race'] = P.start_type.isin(['LastStarts', 'WinRun'])   # TAB types: LastStarts, WinRun (repeats a recent win), Trial
    # TAB never publishes past-start barriers (0 or blank on every line, 26 Nov 2026 check of 2,934 lines): unavailable, not zero
    P['barrier'] = None; P['barrier_note'] = 'not published by TAB form records'
    P = P.sort_values(['capture_day', 'start_type']).drop_duplicates(['horse_key', 'start_date', 'venue', 'distance', 'is_race'], keep='last')
con = duckdb.connect(DB)
con.register('R_', R); con.execute('create or replace table stg_form_runner as select * from R_')
if len(P): con.register('P_', P); con.execute('create or replace table stg_form_start as select * from P_')
latest = R.sort_values('capture_day').groupby('horse_key').tail(1)
# race starts we hold (trials and jump-outs excluded; Breednet runs matched on name + dam when TAB gave the dam; RQ starts on name)
B = con.execute("""select u.name_key, u.dam, u.meeting_date from bn_runner u join bn_race r using (meeting_date, slug, race_no)
                    where u.finish_pos is not null and not coalesce(r.is_trial, false)""").fetchdf(); B['dam_key'] = B.dam.map(nk)
Q = con.execute("select name_key, meeting_date from starter where finish_pos is not null").fetchdf()
B['name_key'] = B.name_key.map(nk); Q['name_key'] = Q.name_key.map(nk)   # our tables keep spaces in name_key (fix 26 Nov 2026)
B = B[B.name_key.isin(latest.name_key)]; Q = Q[Q.name_key.isin(latest.name_key)]
rows = []
for hk, nmk, dk in latest[['horse_key', 'name_key', 'dam_key']].itertuples(index=False):
    b = B[(B.name_key == nmk) & ((B.dam_key == dk) if isinstance(dk, str) and dk else True)]
    dates = set(b.meeting_date) | set(Q[Q.name_key == nmk].meeting_date)
    rows.append({'horse_key': hk, 'runs_held': len(dates), 'first_held': min(dates) if dates else None})
C = latest[['horse_key', 'name_key', 'name', 'capture_day', 'career_starts']].merge(pd.DataFrame(rows), on='horse_key', how='left'); C['runs_held'] = C.runs_held.fillna(0).astype(int)
C['completeness'] = [('first starter (TAB: 0 starts)' if cs == 0 else 'complete' if h >= cs else f'incomplete: {h} of {int(cs)} starts held') if cs == cs else 'unknown'
                     for cs, h in zip(C.career_starts, C.runs_held)]
con.register('C_', C); con.execute('create or replace table stg_career as select * from C_')
if len(P):
    races = P[P.is_race].copy()
    ours = con.execute("""select u.name_key, u.meeting_date start_date, u.finish_pos from bn_runner u join bn_race r using (meeting_date, slug, race_no) where not coalesce(r.is_trial, false)
                          union all select name_key, meeting_date, finish_pos from starter""").fetchdf()
    ours['start_date'] = pd.to_datetime(ours.start_date).dt.date; ours['name_key'] = ours.name_key.map(nk)
    ours = ours.drop_duplicates(['name_key', 'start_date'])   # Qld runs appear in both Breednet and RQ
    K = races.merge(ours, on=['name_key', 'start_date'], how='left'); K['finish_tab'] = pd.to_numeric(K.finish, errors='coerce')
    K['status'] = ['not held by us' if pd.isna(o) else ('agree' if t == o else 'disagree') for t, o in zip(K.finish_tab, K.finish_pos)]
    con.register('K_', K[['horse_key', 'name_key', 'start_date', 'venue', 'finish_tab', 'finish_pos', 'status']]); con.execute('create or replace table stg_form_check as select * from K_')
    agree = K.status.value_counts().to_dict()
else: agree = {}
con.close()
print(f'form staging: {len(R)} runner records, {len(P)} past starts, {C.horse_key.nunique()} horses; completeness '
      f'{C.completeness.str.startswith("complete").sum()} complete / {C.completeness.str.startswith("incomplete").sum()} incomplete / '
      f'{C.completeness.str.startswith("first").sum()} first starters; TAB race starts vs our results {agree}')
