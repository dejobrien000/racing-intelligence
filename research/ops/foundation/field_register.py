"""Data-foundation field register (26 Nov 2026). One row per data field: where it comes from, how far back, how it keeps
coming, where it lands, how duplicates and disagreements are settled, and whether the ratings use it.
Writes research/ops/foundation/field_register.csv and collection_processes.csv. Evidence for the numbers quoted:
ops/foundation/tab_form_overlap.csv (TAB form vs Breednet etc., 26 Nov fields) and the queries noted in DATA_FOUNDATION.md.

Ratings in force: Engine v2.2 (NSW, Vic, ACT, SA, WA, Tas) and Engine v2.1.1 (Qld). 'Ratings' below means read by one of
them today; 'Research' means stored and studied but not read by a production rating; 'Display' means shown, not rated;
'Excluded' means kept out of every model input by rule (market information)."""
import csv, os
H = ['layer', 'group', 'field', 'level', 'primary_source', 'secondary_source', 'history', 'forward_process', 'db_destination',
     'dedupe_and_reconciliation', 'use', 'notes_and_gaps']
BN = 'Breednet results (all states)'; RQ = 'Racing Queensland tracking + race fields (TripleS)'; SAT = 'Racing SA tracking reports (TripleS PDFs)'
TABC = 'TAB racecard (7:30am daily)'; TABR = 'TAB results (11:20pm capture)'; TABF = 'TAB form records (daily, every runner)'
WK = 'Weekly master update (GitHub Actions)'; DAILY = 'Daily 7:30am run (this chat now; PC collector once proven)'
KEY = 'Same horse = name with letters/digits only + race date (+ race no. for dual acceptors).'
R = []
def add(*a): R.append(dict(zip(H, a)))
# ---------------------------------------------------------------- national core: identity and race
add('Core', 'Identity', 'Meeting date', 'meeting', BN, 'RQ (Qld), Racing SA (SA), TAB calendar (forward)', 'Oct 2022 on, all states',
    WK + ': Breednet last 10+ days re-read each week', 'bn_meeting.meeting_date (race.meeting_date Qld; sa_race SA)',
    'Date + venue is the meeting key in every source.', 'Ratings', '')
add('Core', 'Identity', 'Venue / track', 'meeting', BN + ' (venue slug)', 'RQ track names via venue_map; TAB meeting name and venue code (daily)',
    'Oct 2022 on', WK, 'bn_meeting.bf_track_slug; venue_map (Qld names)', 'One alias list (national.py) folds course variants (e.g. Sandown Lakeside/Hillside -> Sandown).',
    'Ratings', 'GAP (small): TAB form records give past-start venues as 4-letter TAB codes (CANT, YGLN...). No code-to-venue table yet, so new starts from TAB form cannot be placed at a venue automatically.')
add('Core', 'Identity', 'State', 'meeting', BN + ' (state from the Betfair venue map)', 'TAB meeting location (daily)', 'Oct 2022 on', WK,
    'bn_meeting.state', 'Breednet venue map is authoritative; unknown venues are reported each week, not guessed.', 'Ratings', '')
add('Core', 'Identity', 'Race number', 'race', BN, 'RQ, Racing SA, TAB (daily)', 'Oct 2022 on', WK, 'bn_race.race_no', 'Meeting key + race no. = national race key.', 'Ratings', '')
add('Core', 'Identity', 'Horse name / identity', 'runner', BN, 'RQ horse_code (Qld only); TAB form sire+dam (daily); Racing NSW form horse table (NSW, static)',
    'Oct 2022 on', WK, 'bn_runner.name_key', KEY + ' Sire/dam break ties where two horses share a name.', 'Ratings',
    'No national horse id exists. 26 Nov TAB form: 1,954 of 2,025 race starts matched to Breednet by name + date (the other 71 are starts Breednet does not have); finishes agree in 1,953.')
add('Core', 'Identity', 'Saddlecloth number', 'runner', BN, 'RQ, Racing SA, TAB, Betfair (to Oct 2026)', 'Oct 2022 on', WK, 'bn_runner.saddlecloth',
    'Agrees with the Vic TripleS files 6,777/6,777.', 'Ratings (race-day matching only)', '')
add('Core', 'Race', 'Distance', 'race', BN, 'RQ; Racing SA; TAB form past starts (agrees 1,954/1,954); TAB racecard (today)', 'Oct 2022 on',
    WK + '; today from ' + TABC, 'bn_race.distance_m', 'Breednet wins for history; today from TAB.', 'Ratings', '')
add('Core', 'Race', 'Class / race conditions', 'race', BN + ' (class text)', 'TAB race name (today); TAB form class per past start; RQ class group (Qld)',
    'Oct 2022 on', WK + '; today from ' + TABC, 'bn_race.class', 'Breednet text parsed to class group and benchmark number.', 'Ratings (class group, benchmark change)', '')
add('Core', 'Race', 'Track condition (going)', 'race', BN, 'RQ track rating; TAB racecard (today); TAB form past starts', 'Oct 2022 on (100%)',
    WK + '; today from ' + TABC, 'bn_race.going / going_num', 'Breednet wins for history; banded good/soft/heavy/synthetic.', 'Ratings (going band, going record)', '')
add('Core', 'Race', 'Race time (winner)', 'race', BN, 'RQ; Racing SA; TAB form past starts', 'Oct 2022 on (99.8-100%)', WK, 'bn_race.race_time_s',
    'Breednet wins; RQ time used inside Qld.', 'Ratings (time figures)', '')
add('Core', 'Race', 'Race last 600m (leader)', 'race', BN, 'Racing NSW form lines (NSW, static); RQ tracking (Qld, per runner)', 'Oct 2022 on; 58% SA to 99% ACT',
    WK, 'bn_race.last600_s', 'Breednet race-level only.', 'Research', '')
add('Core', 'Race', 'Field size (starters)', 'race', 'Derived: count of Breednet finishers', 'TAB form starters per past start', 'Oct 2022 on', WK, 'derived from bn_runner',
    'Derived count; TAB figure is a check.', 'Research / checks', '')
add('Core', 'Race', 'Prize money', 'race', BN, 'Racing NSW results (NSW, Jul-Nov 2026)', 'Oct 2022 on', WK, 'bn_race.prize', '', 'Research', '')
add('Core', 'Race', 'Barrier trial / jump-out flag', 'race', BN + ' (flagged, excluded)', 'TAB form trials (about 3 per runner)', 'Oct 2022 on', WK + '; ' + TABF,
    'bn_race.is_trial; stg_form_start (trials)', 'Trials are never counted as starts.', 'Excluded from ratings (research only)', '')
# ---------------------------------------------------------------- national core: runner results
add('Core', 'Result', 'Finishing position', 'runner', BN, 'RQ (Qld model); Racing SA tracking; TAB results top 4 (nightly); TAB form (agrees 1,953/1,954)',
    'Oct 2022 on, all states', WK + '; nightly ' + TABR + ' for the dashboard', 'bn_runner.finish_pos (starter.finish_pos Qld)',
    'Breednet is the record for history. TAB nightly results settle the dashboard only; they are replaced by Breednet at the weekly update.', 'Ratings', '')
add('Core', 'Result', 'Margin', 'runner', BN, 'RQ official margin; TAB form (98.8% within 0.1 length)', 'Oct 2022 on', WK, 'bn_runner.margin_l', 'Breednet wins.', 'Ratings', '')
add('Core', 'Result', 'Weight carried', 'runner', BN + ' (carried weight: checked 4,937/4,940 against NSW)', 'RQ race fields (ALLOCATED weight); Racing NSW (both)',
    'Oct 2022 on', WK, 'bn_runner.weight_kg (starter.weight_kg Qld = allocated)',
    'Different conventions: Breednet carried; RQ and TAB racecards allocated with the claim separate. National rating uses carried (today = TAB allocated - claim).',
    'Ratings', 'RECONCILE: the national history frame takes Qld rows from RQ (allocated) and other states from Breednet (carried). Small effect (apprentice rides only); flag for the next release, do not change now.')
add('Core', 'Result', 'Jockey', 'runner', BN, 'RQ; TAB racecard (today); TAB form rider per past start', 'Oct 2022 on', WK + '; today ' + TABC, 'bn_runner.jockey',
    'Names compared as written; no jockey id.', 'Ratings (jockey strike rates, change of jockey)', '')
add('Core', 'Result', 'Trainer', 'runner', BN, 'RQ; TAB racecard; TAB form', 'Oct 2022 on', WK + '; today ' + TABC, 'bn_runner.trainer', '', 'Ratings (trainer strike rates)', '')
add('Core', 'Horse', 'Age and sex', 'runner', BN + ' (99.5%)', 'TAB form (today, 100%)', 'Oct 2022 on', WK + '; ' + TABF, 'bn_runner.age, sex; stg_form_runner',
    'Breednet for history. TAB has every runner today, including first starters; held in staging, not read by the ratings.', 'Ratings (age & sex terms, from Breednet)', '')
add('Core', 'Horse', 'Sire, dam, dam sire', 'runner', BN, 'TAB form (sire, dam); Racing NSW form horse table', 'Oct 2022 on', WK, 'bn_runner.sire, dam, damsire',
    '', 'Research (and name disambiguation)', '')
add('Core', 'Horse', 'True career record (starts, wins, places)', 'runner', TABF, 'Count of runs we hold (Breednet + RQ + NSW form)', 'Rolling: from 25 Nov 2026',
    DAILY + ': form step', 'stg_form_runner, stg_career (research staging in the master database)',
    'TAB count vs our count: equal = complete history; TAB 0 = first starter; TAB more = part of history not held. Never assumed.',
    'Research', 'This is what separates genuine first starters (20 on 26 Nov) from lightly raced (52) and incomplete histories (66).')
add('Core', 'Horse', 'Runs since spell, days since last run', 'runner', 'Derived from our run history', TABF + ' (covers starts we do not hold)', 'Oct 2022 on (derived)',
    WK + ' (derived); ' + TABF, 'derived in frames; stg_form_runner', 'Our derivation is used; TAB value is a check where history is incomplete.', 'Ratings (fitness/spacing, derived)', '')
# ---------------------------------------------------------------- today's field (pre-race)
add('Pre-race', 'Today', 'Today\'s runners and scratchings', 'runner', TABC, 'TAB results (late scratchings); PC collector (same source, from install)',
    'From 25 Nov 2026 (files)', DAILY, 'Files: collect/national/<date>/ (not in the master database)',
    'Morning file is the official snapshot; never rebuilt after racing starts.', 'Ratings (who runs)',
    'CONSOLIDATE: load the daily TAB racecards into the master database at the weekly update (one table), so barriers, claims and scratchings from 25 Nov are kept with the history.')
add('Pre-race', 'Today', 'Barrier', 'runner', TABC + ' (every runner, every state)', 'RQ race fields (Qld); Racing SA tracking (SA); Racing NSW form/results (NSW, static)',
    'Qld Oct 2022 on (99%); SA Jan 2024 on; NSW form lines 2018 - 16 Nov 2026; Vic/WA/Tas: none before 25 Nov 2026', DAILY + '; ' + WK + ' (Qld, SA)',
    'starter.barrier (Qld); sa_starter.barrier (SA); nsw_form_line.barrier, nsw_runner.barrier (NSW); TAB files (all, from 25 Nov)',
    'Barrier at a past start is never taken from TAB form records (they give 0).', 'Ratings (Qld only); Display (national)',
    'GENUINE GAP: past barriers for Vic, WA and Tas before 25 Nov 2026. Breednet does not publish barriers; TAB form does not give them. Forward is covered once the daily TAB files are loaded (see above).')
add('Pre-race', 'Today', 'Allocated weight and apprentice claim', 'runner', TABC, 'RQ race fields (Qld)', 'From 25 Nov 2026 (files); Qld Oct 2022 on', DAILY,
    'TAB files; starter.weight_kg (Qld)', 'Carried = allocated - claim (0-4 kg check).', 'Ratings (carried weight)', '')
add('Pre-race', 'Today', 'Rider, trainer, emergency flag', 'runner', TABC, 'RQ race fields (Qld)', 'From 25 Nov 2026 (files)', DAILY, 'TAB files', '', 'Ratings (rider/trainer)', '')
add('Pre-race', 'Today', 'Track condition and rail (morning)', 'meeting', TABC, 'RQ (Qld); Racing NSW meeting page (NSW, static)', 'From 25 Nov 2026 (files)', DAILY, 'TAB files',
    'Morning value only; later upgrades are not chased (one daily run).', 'Ratings (going band); rail Display', 'TAB gives no rail at race level.')
add('Pre-race', 'Today', 'Start time', 'race', TABC, 'Betfair scheduled time (history, to Oct 2026)', 'From 25 Nov 2026', DAILY, 'TAB files', '', 'Display / operations', '')
add('Pre-race', 'Today', 'Blinkers on today', 'runner', TABF, 'SA gear documents (SA, full gear)', 'From 25 Nov 2026', DAILY + ': form step', 'stg_form_runner.blinkers',
    'TAB gives on/off only, not first time/removed.', 'Research', '')
# ---------------------------------------------------------------- TAB form records: what they add to past starts
add('TAB form fill', 'Past start', 'Position in running (e.g. 3-2-2-2)', 'past start', TABF + ' (97.6% of race starts, all states)',
    'RQ tracking (Qld, every segment); Racing SA tracking; Racing NSW form 800m/400m (NSW, static); Vic TripleS section times (metro, from Jul 2026)',
    'Rolling: each runner\'s last 8-9 race starts, gathered daily from 25 Nov 2026 (the 26 Nov set reaches back to 2022)', DAILY + ': form step',
    'stg_form_start.position_in_run (research staging)', KEY + ' Venue and distance confirm. RQ/SA tracking win where both exist.', 'Research',
    'Only national source of running positions for Vic, WA and Tas: 557/557 Vic starts on 26 Nov had it; 11 were held elsewhere.')
add('TAB form fill', 'Past start', 'Stewards\' comment per past start', 'past start', TABF + ' (38% of starts carry one)', 'QRIC full reports (Qld); Racing SA stewards PDFs (SA)',
    'Rolling, as above', DAILY + ': form step', 'stg_form_start.stewards_comment', 'A blank comment is "not recorded", never "no incident".', 'Research',
    'Only source for Vic, NSW, WA and Tas per-horse stewards remarks. Retrospective information: usable only for later races.')
add('TAB form fill', 'Past start', 'Starts we do not hold (picnic, NZ/overseas, pre-Oct 2022, last few days)', 'past start', TABF, 'none',
    'Rolling', DAILY + ': form step', 'stg_form_start (class "new start")', 'Added to staging only; Breednet replaces any it later publishes.', 'Research',
    '62-71 a day (e.g. Yarra Glen, Yea picnics; Ashburton NZ). Venue code map needed before use (see Venue).')
add('TAB form fill', 'Past start', 'Finish, margin, distance, class, going, time, rider (duplicates)', 'past start', BN, TABF, 'Oct 2022 on', WK,
    'bn_* (Breednet copy kept)', 'TAB copies are checks only: finish agrees 1,953/1,954, margin 1,644/1,664 within 0.1L, distance 1,954/1,954.', 'Ratings (Breednet copy)', '')
# ---------------------------------------------------------------- state layers
QT = ('Oct 2022 on, 1,263 tracked meetings, 635,831 segments', WK + ': RQ files for the same window')
XR = 'x_* tables are the raw parse of the same RQ files, not a second source; race/starter/sectional are the clean versions.'
add('Qld layer', 'Tracking', 'Section (split) times per runner: last 600m, last 200m, finishing speed', 'section', RQ, 'Breednet race last 600m (leader only)', *QT,
    'sectional.split_s, inter_s', XR, 'Ratings (Qld v2.1.1 sectional terms)', '')
add('Qld layer', 'Tracking', 'Position at each segment (settling position, leader)', 'section', RQ, 'TAB form position in running', *QT, 'sectional.position',
    XR + ' Tracking wins over TAB position in running.', 'Ratings (Qld v2.1.1 race-shape terms)', '')
add('Qld layer', 'Tracking', 'Average and top speed per segment', 'section', RQ, 'none', *QT, 'sectional.avg_speed_ms, top_speed_ms', XR, 'Research', '')
add('Qld layer', 'Tracking', 'Stride frequency and length', 'section', RQ, 'none', *QT, 'sectional.stride_freq_hz, stride_len_m', XR, 'Research', '')
add('Qld layer', 'Tracking', 'Distance from rail, ground covered', 'section', RQ, 'none', *QT, 'sectional.dist_to_rail_m, ground_m; starter.ground_m', XR, 'Research', '')
add('Qld layer', 'Tracking', 'Runner finish time, official margin, result state', 'runner', RQ, BN, 'Oct 2022 on', WK, 'starter', 'RQ wins inside Qld; Breednet fills Qld meetings RQ does not track (country).',
    'Ratings (Qld)', '')
add('SA layer', 'Tracking', 'Same measurements as Qld: section times, positions, speed, stride, distance from rail, ground covered', 'section', SAT, 'Breednet (results); TAB form position in running',
    'Jan 2024 on, 233 meetings, 133,905 segments', WK + ': new SA meetings', 'sa_sectional; sa_starter; sa_race; sa_race_checks',
    'Race enters only if every staging check passes; finishes checked against Breednet (bn_finish_agree).', 'Research (released 26 Nov; no rating reads it yet)', '')
add('Vic layer', 'Tracking', 'Per-runner section times (every 200m) and speed at each mark', 'section',
    'Vic TripleS CSVs via the weekly external Racing.com session (ChatGPT + Damo)', 'none', '1 Jul 2026 on (accepted start); 817 races, 13 track configurations, metro and major provincial',
    'Weekly, manually started external session -> ZIP -> history/stage_vic_triples.py', 'research/staging/vic_triples (awaiting integration; proposed vic_sectional / vic_starter / vic_race, same shape as SA)',
    'Validated: runners 6,777/6,777, saddlecloths agree, fastest = winner 663/666. Breednet stays the result of record.', 'Research (staging)',
    'No stride, rail distance or ground covered in these files. Country Vic uses a different provider (Daily Sectionals): not covered.')
add('NSW layer', 'Results and form', 'Barrier, 800m/400m positions, race last 600m, NSW rating, weight allocated and carried', 'past start',
    'Racing NSW form lines (static snapshot)', 'Racing NSW results pages (Jul-24 Nov 2026, static)', 'Form lines Jun 2018 - 16 Nov 2026 for 8,154 horses; results Jul-Nov 2026',
    'None (collected by browser before 25 Nov; not continued)', 'nsw_form_line, nsw_form_horse, nsw_meeting, nsw_race, nsw_runner', KEY + ' Breednet wins on results.',
    'Research', 'Forward replacement for barriers: daily TAB files. No forward source for 800m/400m positions except TAB position in running.')
# ---------------------------------------------------------------- gear and stewards
add('Gear & stewards', 'Gear', 'Declared gear list with state (on, first time, again, removed)', 'runner', 'Racing SA gear documents (Country Racing SA site)', 'none',
    'Oct 2022 on (history run in progress)', 'Twice daily (GitHub workflow sagear)', 'Branch raw-sagear (originals + gear_items.csv); staging only',
    '"Date Printed" = when known; a document printed after a race is never used for it.', 'Research', 'SA only.')
add('Gear & stewards', 'Gear', 'Late gear changes, trainer reports, surgery, gear clarifications', 'runner', 'Racing NSW Stewards Notifications posts', 'none',
    '2,100 posts held (2017 on)', '4 times daily (workflow nswstewards)', 'Branch raw-nswstewards (every version) ; staging only',
    'Known from the post\'s last-edited time.', 'Research', 'NSW only. Parser reads one post style so far; others stored for the next pass.')
add('Gear & stewards', 'Stewards', 'Full stewards\' reports (race by race, per horse)', 'runner', 'QRIC stewards reports (Qld)', 'Racing SA stewards PDFs (SA)',
    'Qld Oct 2022 on (backfill running); SA Oct 2022 on (running)', 'Weekly (rqstewards); twice daily (sagear)', 'Branches raw-rqstewards, raw-sagear; staging only',
    'Post-meeting, retrospective. Missing report = unknown.', 'Research', 'Vic, NSW, WA, Tas full reports: not held (TAB per-horse comments cover part of this).')
# ---------------------------------------------------------------- market and validation
add('Excluded', 'Market', 'TAB fixed odds win/place (OPEN 7:30am, CLOSE at results)', 'runner', TABC + ' / ' + TABR, 'none', 'From 25 Nov 2026', DAILY,
    'prices/<date>/ only', 'Never Betfair, tote or SP in place of a missing TAB price.', 'Excluded from models (display and returns only)', '')
add('Excluded', 'Market', 'Starting prices, Betfair prices', 'runner', 'Dropped at parse (Breednet, Betfair files)', 'none', '-', '-', 'not stored',
    'Loaders refuse records with price text.', 'Excluded', '')
add('Validation', 'Cross-check', 'Betfair race lists (names, saddlecloths, winners)', 'runner', 'Betfair historical files (prices removed)', 'none', '2020 - Oct 2026, all states + NZ',
    'None (browser bundle; not continued)', 'bf, bf_runner, coverage_betfair', 'Used only to check Breednet and new sources.', 'Validation only',
    'CONSOLIDATE: TAB nightly results can take over this checking role from Nov 2026; no new Betfair collection needed.')
add('Retire', 'racing.com', 'racing.com results and speed tables collected by browser (24 Nov)', 'runner', 'racing.com (collected by Claude in Chrome)', '-',
    '106 races (Oct-Nov 2026); speed for 3 Oct', 'None', 'rc_meeting, rc_race, rc_runner, vic_speed_*', 'Superseded by Breednet results and the Vic TripleS files.',
    'Not used', 'Recommended for removal at the next weekly update (collected outside the agreed method).')
os.makedirs('ops/foundation', exist_ok=True)
with open('ops/foundation/field_register.csv', 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=H); w.writeheader(); w.writerows(R)
P = [['process', 'what it collects', 'run by', 'when', 'lands in', 'status'],
     ['Daily 7:30am run', 'TAB racecards (fields, barriers, weights, claims, riders, scratchings, track), TAB prices (display only), ratings, dashboard', 'Claude (this chat) -> PC collector after proving week', 'Daily 7:30am Brisbane', 'collect/national/<date>/, prices/<date>/', 'Running'],
     ['Daily form records', 'TAB form records for every runner (past starts, career, gear flag)', 'Claude -> PC collector', 'Daily from 7:40am', 'prices/<date>/form_*.raw.txt -> collect/national/<date>/form_*.csv -> stg_form_* weekly', 'Running'],
     ['Evening results', 'TAB results (finishes, status) for the dashboard and returns', 'Claude (11:20pm) -> PC collector', 'Nightly; PC keeps trying to 3am', 'collect/national/<date>/results_*', 'Running'],
     ['Weekly master update', 'Breednet results (all states), RQ tracking + fields, SA tracking, TAB form staging; rebuilds frames; checks', 'GitHub Actions', 'Mondays 3:00am Brisbane', 'Master database (branch db, previous kept as db-prev)', 'Running'],
     ['QRIC stewards reports', 'Qld stewards reports', 'GitHub Actions (rqstewards)', 'Weekly; backfill running', 'Branch raw-rqstewards', 'Running (staging)'],
     ['SA gear and stewards documents', 'Gear Change Race Order PDFs, stewards PDFs', 'GitHub Actions (sagear)', 'Twice daily; history run in progress', 'Branch raw-sagear', 'Running (staging)'],
     ['NSW stewards notifications', 'Pre-race notices (late gear, surgery, trainer reports)', 'GitHub Actions (nswstewards)', '4 times daily', 'Branch raw-nswstewards', 'Running (staging)'],
     ['EXTERNAL: weekly Racing.com session', 'Victorian TripleS sectional CSVs (from 1 Jul 2026; 13 track configurations)', 'ChatGPT + Damo, manually started Work session (outside Claude)', 'Weekly', 'ZIP -> history/stage_vic_triples.py -> research/staging/vic_triples', 'Established 26 Nov 2026. First ZIP (817 races, 1 Jul-25 Nov) validated by Claude; awaiting integration decision'],
     ['Missed-run watchdog', 'Emails if the morning run, evening capture or (once enabled) PC deliveries are missing', 'GitHub Actions (run-watchdog)', '8:15am, 8:50am, 12:45am', 'Email to Damo', 'Running'],
     ['Retired', 'Browser collectors: Racing NSW results/form, racing.com, Betfair bundles, Breednet in Chrome', '-', '-', '-', 'Not continued; history kept (racing.com tables to be removed)']]
with open('ops/foundation/collection_processes.csv', 'w', newline='', encoding='utf-8') as fh: csv.writer(fh).writerows(P)
print(len(R), 'fields;', len(P) - 1, 'processes')
