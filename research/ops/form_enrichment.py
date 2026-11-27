"""What one day's TAB form records actually added (research measurement; never a rating input, never a release check).
Usage: python3 ops/form_enrichment.py <YYYYMMDD> [history.duckdb]
Reads prices/<D>/form_manifest.csv (ops/form_manifest.py), collect/national/<D>/form_runners.csv + form_past_starts.csv
(ops/parse_form.py), every EARLIER day's form files (what we had already captured) and the master database (what we already
hold). Writes collect/national/<D>/form_enrichment.csv (one row per past start with its classification) and appends one
summary row per day to outputs/form_enrichment_ledger.csv (re-running a day replaces that day's row).

Definitions
  race start      TAB startType LastStarts or WinRun (WinRun repeats a LastStarts entry when the last win is recent:
                  collapsed on horse + date + venue + distance). Trial = barrier trial / jump-out, kept separately.
  held            a race start on the same date by the same horse (name key) in our results: Breednet (all states),
                  Racing Queensland starters, Racing NSW form lines.
  new start       a race start we do not hold and had not captured on an earlier day (e.g. before Oct 2022, NZ or a
                  meeting missing from our results).
  enriched        a race start we hold, first captured today, carrying a stewards' comment and/or positions in running
                  (neither is in our results except Racing NSW form lines' 800m/400m positions).
  duplicate       already captured on an earlier day with the same comment and positions.
  barrier         TAB form records never give past-start barriers (0 or blank on every line), so barriers are counted as
                  UNAVAILABLE from this source, never as zero. Past-start barriers come only from Racing Queensland starters
                  and Racing NSW form lines.
  gear            today's blinkers flag per runner (the only gear field TAB publishes); change vs the same horse's
                  previous capture where we have one. A missing flag is 'unavailable', not 'no blinkers'.
  career          TAB career starts vs race starts we hold: first starter (TAB 0), complete, or incomplete history
                  (TAB shows more starts than we hold: older, interstate/overseas or missing meetings), never 'inexperienced'."""
import sys, os, glob, re, csv
import pandas as pd, duckdb
D = sys.argv[1]; DB = sys.argv[2] if len(sys.argv) > 2 else '../history/history.duckdb'
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper())) if isinstance(s, str) else None
blank = lambda s: s is None or (isinstance(s, float) and s != s) or str(s).strip() in ('', '-', 'null', 'None', 'nan')
base = f'collect/national/{D}'
man = pd.read_csv(f'prices/{D}/form_manifest.csv', dtype=str)
R = pd.read_csv(f'{base}/form_runners.csv', dtype=str); P = pd.read_csv(f'{base}/form_past_starts.csv', dtype=str)
R['name_key'] = R.name.map(nk); R['dam_key'] = R.dam.map(nk); R['horse_key'] = R.name_key + '|' + R.dam_key.fillna('')
P = P.merge(R[['ven', 'race', 'n', 'horse_key', 'name_key', 'blinkers']], on=['ven', 'race', 'n'], how='left')
P['is_race'] = P.start_type.isin(['LastStarts', 'WinRun']); P['start_date'] = pd.to_datetime(P.start_date, errors='coerce').dt.date
P['has_comment'] = ~P.stewards_comment.map(blank); P['has_pir'] = ~P.position_in_run.map(blank)
P['barrier_given'] = ~P.barrier.map(lambda b: blank(b) or str(b).strip() == '0')
P['k'] = P.horse_key + '|' + P.start_date.astype(str) + '|' + P.venue.fillna('') + '|' + P.distance.fillna('') + '|' + P.is_race.map({True: 'R', False: 'T'})
lines = len(P); P = P.sort_values('start_type').drop_duplicates('k', keep='first')   # LastStarts before WinRun
# what earlier days captured
prev = []
for f in sorted(glob.glob('collect/national/*/form_past_starts.csv')):
    d = f.split('/')[2]
    if d >= D: continue
    q = pd.read_csv(f, dtype=str); r = pd.read_csv(f.replace('form_past_starts', 'form_runners'), dtype=str)
    r['horse_key'] = r.name.map(nk) + '|' + r.dam.map(nk).fillna(''); q = q.merge(r[['ven', 'race', 'n', 'horse_key']], on=['ven', 'race', 'n'], how='left')
    q['is_race'] = q.start_type.isin(['LastStarts', 'WinRun']); q['start_date'] = pd.to_datetime(q.start_date, errors='coerce').dt.date
    q['k'] = q.horse_key + '|' + q.start_date.astype(str) + '|' + q.venue.fillna('') + '|' + q.distance.fillna('') + '|' + q.is_race.map({True: 'R', False: 'T'})
    q['sig'] = q.stewards_comment.fillna('-') + '#' + q.position_in_run.fillna('-'); q['day'] = d; prev.append(q[['k', 'sig', 'day']])
    r['day'] = d; prev.append(r.assign(k='RUNNER|' + r.horse_key, sig=r.blinkers.fillna('-'))[['k', 'sig', 'day']])
PV = pd.concat(prev).sort_values('day').drop_duplicates('k', keep='last').set_index('k') if prev else pd.DataFrame(columns=['sig', 'day'])
# what we hold
con = duckdb.connect(DB, read_only=True)
keys = tuple(set(P.name_key.dropna()))
held = con.execute(f"""select distinct name_key, meeting_date d from (
    select regexp_replace(upper(u.name_key), '[^A-Z0-9]', '', 'g') name_key, u.meeting_date from bn_runner u join bn_race r using (meeting_date, slug, race_no)
           where not coalesce(r.is_trial, false)
    union all select regexp_replace(upper(name_key), '[^A-Z0-9]', '', 'g'), meeting_date from starter where not coalesce(scratched, false)   -- Batch 20 A1 fix: Racing Queensland scratchings are not starts
    union all select regexp_replace(upper(name_key), '[^A-Z0-9]', '', 'g'), run_date from nsw_form_line where not coalesce(trial, false))
    where name_key in (select unnest(?))""", [list(keys)]).fetchdf()   # our tables keep spaces in name_key; compared letters/digits only
con.close()
H = set(zip(held.name_key, pd.to_datetime(held.d).dt.date))
P['held'] = [(a, b) in H for a, b in zip(P.name_key, P.start_date)]
P['sig'] = P.stewards_comment.fillna('-') + '#' + P.position_in_run.fillna('-')
P['seen_before'] = P.k.isin(PV.index); P['same_as_before'] = [s == PV.sig.get(k) for k, s in zip(P.k, P.sig)]
def cls(x):
    if x.seen_before and x.same_as_before: return 'duplicate'
    if not x.is_race: return 'trial (new)' if not x.seen_before else 'trial (updated)'
    if not x.held: return 'new start' if not x.seen_before else 'new start (updated)'
    return 'enriched' if (x.has_comment or x.has_pir) else 'held, nothing added'
P['enrich_class'] = P.apply(cls, axis=1)   # was 'class', which overwrote TAB's race class (fixed 26 Nov)
P.drop(columns=['sig']).to_csv(f'{base}/form_enrichment.csv', index=False)
# gear
R['blinkers_state'] = R.blinkers.map(lambda b: 'unavailable' if blank(b) else ('on' if str(b).lower() == 'true' else 'off'))
prevb = [PV.sig.get('RUNNER|' + h) for h in R.horse_key]
R['blinkers_change'] = ['no earlier capture' if p is None else ('unchanged' if str(p).lower() == str(b).lower() else f'{p}->{b}') for p, b in zip(prevb, R.blinkers)]
# career (held race starts per horse, any date)
cnt = held.groupby('name_key').size()
R['tab_starts'] = pd.to_numeric(R.career_starts, errors='coerce'); R['held_starts'] = R.name_key.map(cnt).fillna(0).astype(int)
LIGHT = 3   # 1-3 career starts = lightly raced (kept apart from first starters and from horses whose history we only partly hold)
def career(t, h):
    if t != t: return 'unknown'
    if t == 0: return 'first starter'
    full = h >= t
    if t <= LIGHT: return 'lightly raced, complete' if full else 'lightly raced, incomplete history'
    return 'complete' if full else 'incomplete history'
R['career'] = [career(t, h) for t, h in zip(R.tab_starts, R.held_starts)]
R[['ven', 'race', 'n', 'name', 'horse_key', 'tab_starts', 'held_starts', 'career', 'blinkers_state', 'blinkers_change']].to_csv(f'{base}/form_runner_status.csv', index=False)
races = P[P.is_race]; c = P['enrich_class'].value_counts()
row = {'day': D, 'runners_expected': len(man), 'runners_retrieved': int((man.status == 'retrieved').sum()),
       'runners_malformed': int((man.status == 'malformed').sum()), 'runners_missing': int((man.status == 'missing').sum()),
       'past_start_lines': lines, 'unique_past_starts': len(P), 'race_starts': len(races), 'trials': int((~P.is_race).sum()),
       'new_starts': int(c.get('new start', 0) + c.get('new start (updated)', 0)), 'enriched_held_starts': int(c.get('enriched', 0)),
       'held_nothing_added': int(c.get('held, nothing added', 0)), 'duplicates_unchanged': int(c.get('duplicate', 0)),
       'trials_new': int(c.get('trial (new)', 0)), 'new_stewards_comments': int((P.has_comment & ~(P.seen_before & P.same_as_before)).sum()),
       'new_running_positions': int((races.has_pir & ~(races.seen_before & races.same_as_before)).sum()),
       'race_starts_missing_positions': int((~races.has_pir).sum()), 'race_starts_missing_venue': int(races.venue.map(blank).sum()),
       'past_start_barriers_given': int(P.barrier_given.sum()),
       'blinkers_on': int((R.blinkers_state == 'on').sum()), 'blinkers_off': int((R.blinkers_state == 'off').sum()),
       'blinkers_unavailable': int((R.blinkers_state == 'unavailable').sum()),
       'blinkers_changed_vs_earlier_capture': int(R.blinkers_change.str.contains('->').sum()),
       'career_first_starters': int((R.career == 'first starter').sum()),
       'career_lightly_raced_complete': int((R.career == 'lightly raced, complete').sum()),
       'career_lightly_raced_incomplete': int((R.career == 'lightly raced, incomplete history').sum()),
       'career_complete': int((R.career == 'complete').sum()), 'career_incomplete_history': int((R.career == 'incomplete history').sum())}
# reconciliation: every race start falls in exactly one class; every line is a race start or a trial (or a collapsed duplicate)
row['check_race_starts'] = row['race_starts'] == row['new_starts'] + row['enriched_held_starts'] + row['held_nothing_added'] + int(c.get('duplicate', 0) - (P[~P.is_race]['enrich_class'] == 'duplicate').sum())
row['check_lines'] = row['past_start_lines'] == row['race_starts'] + row['trials'] + (lines - len(P))
L = 'outputs/form_enrichment_ledger.csv'; old = pd.read_csv(L, dtype=str) if os.path.exists(L) else pd.DataFrame()
if len(old): old = old[old.day != D]
pd.concat([old, pd.DataFrame([row]).astype(str)]).to_csv(L, index=False)
for k, v in row.items(): print(f'{k}: {v}')
