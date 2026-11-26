# Racing Intelligence operating model (Damo's definitive instructions, 25 Nov 2026 07:45 Brisbane)
- ONE daily automated run at 7:30am Brisbane: all AU thoroughbred meetings; full fields (runners, barriers, jockeys,
  trainers, weights, track, rail, scratchings); TAB fixed win/place = OPEN price; match to master DB; score with the
  approved engine (Engine v2); ONE final morning set (date, model version, collection timestamp); publish dashboard;
  retrieve YESTERDAY's results + CLOSE prices; evaluate yesterday's selections, movement, paper returns.
- NO hourly collection, NO intraday price snapshots, NO intraday re-rating, NO extra jobs without a clear need.
- Prices: OPEN = TAB fixed win (and place) at the 7:30am run. CLOSE = final TAB fixed price published with / obtainable
  from the completed results. If missing, mark missing; never substitute tote, Betfair or SP. Prices never enter the model.
- ONE authoritative master historical DB, read-only between WEEKLY incremental refreshes (rich fields: margins, times,
  sectionals, running positions, ground covered, weights, jockeys, trainers, barriers, track, rail, class). No daily
  ability recomputation, no secondary form DB. Weekly refresh updates dynamic ratings/opposition histories; coefficients
  change only on deliberate model releases. Versioned DB with recoverable previous version.
- Preferred host: private GitHub repo + Actions (daily 7:30 + weekly), DB outside git history if needed; identify real
  limits before recommending a paid server. Retire competing Claude tasks once proven.
- Priority data gap: SA, WA, Tas history (Morphettville, Strathalbyn, Ascot, Belmont, Albany, Launceston, Hobart) + Qld/Vic gaps.
- Then STOP infrastructure; return to modelling (feature/family tests, jockey/trainer, course interactions, horse-course
  compatibility, penalised/flexible models, Engine v3).
Status 25 Nov 07:57: hourly minder trig_01N5Vf53vtCMTkfm36r7jMAq DISABLED. Disabling 12:15 waves / 9:30pm / 9:45pm
send_laters was refused by the permission check (user interrupted) - when they fire, treat as superseded except the 9:30pm
one may be used for the one-off CLOSE-price investigation (what TAB's post-race racecard shows). The PC-bound 26 Nov
7:35am reminder serves as the interim daily run until the GitHub workflow exists (needs Damo to create a private repo).

## TAB access status (25 Nov 10:15 Brisbane) - the one open blocker for a hands-off 7:30am run
| Route | Result | Evidence |
|---|---|---|
| GitHub Actions runner (US Azure, 172.190.124.68) | TAB returns a 3,987-byte "TAB.com.au" web page, not JSON | probe/results.txt, run 2026-11-24T23:21:05Z |
| Fresh scheduled Claude session, fetch agent | PROVENANCE_REQUIRED: "permission request ... not answered in time" | branch tab-fetch-test, research/ops/logs/TAB-FETCH-TEST.md |
| Fresh scheduled Claude session, direct WebFetch | no direct WebFetch tool in scheduled sessions (only the fetch agent) | branch tab-fetch-test-2, research/ops/logs/TAB-FETCH-TEST-2.md |
| This build conversation, Damo away | PROVENANCE_REQUIRED: "Nobody answered this permission request" | 25 Nov 00:13Z, dates/2026-11-24/meetings |
Racing Queensland, Racing NSW FreeFields, Breednet and racing.com all answer the GitHub runner (200 HTML), so the weekly
database update can run fully on GitHub. TAB prices need Damo's approval of api.beta.tab.com.au (asked 25 Nov 10:15).
Not done, by rule: no browser-header impersonation, no proxies, no other price sources.

26 Nov 8:27am (Damo): the daily run now wakes this build conversation at 7:30am, plus an 11:20pm evening capture, as chained
one-shot reminders (DAILY_RUN.md "WHERE IT RUNS"); the fresh-session task trig_011FEpTKDVAUA5SMkv9EBkQS is switched off.
Interim daily run: if the 7:33 scheduled run logs "ATTENTION: TAB fetch needs approval", run DAILY_RUN.md in the build
conversation (session_01TcfAeuNwdADDxa3cwHWiRz) when its 7:35 reminder arrives; the leftover 7:45/7:50/8:20 reminders
there are superseded (old PC-based cycle) and are ignored.
25 Nov 10:21: Damo approved the TAB read in the build chat. 10:40 test (new URL, Damo asked not to approve anything):
dates/2026-11-26/meetings returned data (HAW, MOR, ROC, GER) -> the approval now holds in this chat with nobody answering.
Whether it also covers fresh scheduled sessions is shown by the 26 Nov 7:33 daily run (log research/ops/logs/2026-11-26.md).
TAB's info-service lists only today and future dates (25 Nov 10:20: dates = 25, 26, 28, 29 Nov, 4 Dec; 24 Nov meetings = []).
So CLOSE (final fixed price with the results) may not be readable at 7:30 next morning: checked tonight + 26 Nov 7:30.
25 Nov 23:14 Brisbane (13:14Z, about 2h after the last race; already 26 Nov in Sydney/Melbourne): every 25 Nov racecard still
answered (44/44 races). After racing TAB shows: fixedOdds.returnWin = final TAB fixed price; bettingStatus = Winner / Placing /
Loser / LateScratched; race.results = finishing order of the FIRST FOUR only; dividends (tote, not used); returnWinOpen = TAB's own
opening price (NOT our 7:30 OPEN). Runners 5th or worse have no position: settle_yesterday.py now marks them 'unplaced' (fixed 25 Nov;
before the fix they counted as no result, field sizes shrank to 4 and place terms were wrong).
26 Nov 8:15am test: dates/2026-11-25/meetings returned 2 meetings and no Australian thoroughbred meeting, so yesterday is not
readable next morning: the evening capture is required (decision confirmed). 26 Nov 7:34am: the fresh scheduled run stopped at
step 1 (PROVENANCE_REQUIRED), so the approval given in the build chat does not carry to scheduled sessions; the interim run in
the build chat produced the day (log ops/logs/20261126.md).
DECISION: results + CLOSE need an EVENING capture (after the last race, before Brisbane midnight) until a morning run proves the
previous day is still listed: on 25 Nov 10:20 Brisbane the 24 Nov meetings list was empty. The 26 Nov 7:30 run's step 3 is the test.
Evening file: research/collect/national/<date>/results_<stamp>.raw.txt (copy in prices/<date>/). If step 3 finds TAB empty, the
morning run uses the evening file. A standing evening capture needs a scheduled task that can read TAB unattended: not created yet
(depends on the same TAB-approval question as the 7:30 run).

## Weekly master-database update (built 25 Nov 2026 afternoon) - workflow weekly-master-db
- Schedule: Monday 3:00am Brisbane (cron Sunday 17:00 UTC). Runs entirely on GitHub; laptop can be off.
- Steps (research/ops/weekly_update.py): Breednet results for the last 10+ days (all six states held) -> incremental merge
  (history/load_breednet.py --incremental) -> Racing Queensland tracking ZIPs + Race Fields PDFs for the same days
  (collect/weekly/rq.py) -> incremental merge (history/load_history.py --incremental) -> rebuild every derived table
  (Qld runs, Qld ratings/features/pace figures, national runs with the states in ops/db_config.json, v2 and v3 frames)
  -> checks -> report (branch ci-results, weekly-db/weekly_report.md).
- Publishing: the new version goes to branch db and the old one to db-prev ONLY if every check passes AND the switch
  file research/ops/weekly_publish_enabled exists. The switch is added after one dry run passes on GitHub.
- Proven locally 25 Nov: RQ collector parse = browser parse on every saved 2022-26 file (9.8k races, 126k runners, 636k
  sections, 94k field rows); live GitHub fetch of 20-22 Nov matches the master DB exactly; incremental merge of an
  already-held bundle leaves every table identical; full rebuild reproduces all production tables exactly. Full job ~20 min,
  peak memory about 2.5 GB (GitHub runners have 7 GB or more). Sandbox run of the whole script with saved bundles: all checks PASS.
- Only one collector job runs at a time (concurrency group breednet-collect, shared with the backfills). A new queued run
  replaces a waiting one, so dry runs are started only when no backfill is waiting.
- SA, WA and Tas join the national rating only by a deliberate database release (ops/db_config.json), after Damo sees
  the evaluation.

## Database releases
- 25 Nov 2026 2:20pm: master-2026-11-23-sa-wa-tas on branch db (previous master-2026-11-23 on db-prev). SA, WA and Tas
  history in the national rating; SA/WA/Tas meetings rated from the 26 Nov 7:30am run (ops/db_config.json). Approved by
  Damo 2:15pm. Evidence and roll-back: research/benchmarks/engine_v2/RELEASES.md. This chat's local copy switches after
  tonight's 25 Nov settlement (reminder 11:30pm).
- 25 Nov 2026 ~3:30pm: Engine v2.2 (NSW/VIC/ACT/SA/WA/TAS; Qld stays v2.1), live from the 26 Nov 7:30am run; approved by Damo
  ("Replace from tomorrow"). Code engine/v22.py, manifest benchmarks/engine_v2_2/; roll back ENGINE_V22=0. Pre-registered check:
  research/preregistered/2026-11-25_batch10_v22.md. Each meeting shows its measured venue class (approved). SA calibration unchanged.
- 25 Nov 2026 ~5:10pm: database master-2026-11-23-sa-wa-tas-qld (Breednet Queensland meetings: 915 untracked meetings in the national
  rating, Qld ages) + Engine v2.1.1 (Qld model refitted; scale moved 3%). Approved by Damo ("refit tonight, live tomorrow"). db-prev =
  master-2026-11-23-sa-wa-tas. Weekly job: publishing ON (first GitHub dry run passed every check); collects QLD too.
- Local working copy (this chat): switches to the final database at 11:30pm and syncs code at 11:35pm, after the 25 Nov settlement.

## Production configuration register (single source; updated 26 Nov 2026 9:30pm after Damo's approval)
| Item | Production from the 27 Nov 7:30am run | Switch | Roll back to | Kept as |
|---|---|---|---|---|
| NSW/Vic/ACT/SA/WA/Tas | Engine v2.3 (benchmarks/engine_v2_3; ratings built each morning: national_runs_c2.parquet, engine/frames/national_c2.parquet) | ops/engine_c2_enabled (approved 26 Nov 9:07pm) | Engine v2.2: delete the file; a failed v2.3 build falls back for that day by itself | previous-engine shadow, daily |
| Qld | Engine v2.1.3 (v3 rating; benchmarks/engine_v2_1_3) | ops/engine_qld213_enabled (approved 26 Nov 9:07pm) | Engine v2.1.1: delete the file | previous-engine shadow, daily |
| Qld candidate shadow | v2.1.2 (ops/run_shadow.sh), never published | - | - | - |
| Weight | national = carried (allocated minus claim); Qld = allocated (its history is allocated) | - | WEIGHT_CARRIED=0 | - |
| Display calibration | v2.3 bent line (six states); v2.1.3 bent line (Qld) | follows the engine switch | follows the switch | - |
| kg display scale | six states 0.269 per kg (v2.2 was 0.226: kg figures ~16% smaller, units not ability); Qld 0.2243 unchanged | follows the switch | follows the switch | - |
| Master database | master-2026-11-23-sa-wa-tas-qld (branch db; previous on db-prev) | Monday 30 Nov weekly update adds TAB daily tables, TAB venue map, TAB results check, Vic tracking, racing.com archive (approved 26 Nov; none feeds ratings) | db-prev | - |
Each meeting's day-file record names the engine that scored it; days already published are never rescored. The morning run pulls
GitHub first (DAILY_RUN step 0), so a switch file created or deleted on GitHub takes effect at the next run.
Checks 26 Nov night: replay of the 26 Nov run with switches off = identical to production (8 prediction files, 260 dashboard runners);
with switches on = runs end to end (frames identical to the fitted ones, labels per meeting, breakdowns reconcile, ranking, shadow).

### Open work register (operations and research; one list, newest first)
| Item | Type | Status |
|---|---|---|
| Common national framework for Qld (Qld coefficients; keep Qld physical inputs as a variant) | research build -> shadow | Approved to build as a SHADOW (Damo 26 Nov 9:07pm). Not for promotion without an evidence review |
| Handicap weight slope on top of v2.3 (wt_x_hcp) | next release candidate | Approved to prepare for the following release; preregistered 2024 +0.0012 (0.0008-0.0017); needs build_v22 with the term + live term definition + parity |
| Batch 14: uneven-last-600 input for Qld (dip_last, dip_prior) | research -> prospective check | Open hypothesis, judged on races from 27 Nov; not a candidate until confirmed. Follow-up: +0.0040 (-0.0006 to +0.0095) 2024 on v2.1.3 - uncertain-small |
| Batch 14 follow-up (27 Nov): profiles, own-normal decline, riders, distance form, small-improvement bundle | research | Done; research/batch14/followup/README.md. No candidate except the weight slope (already queued). Rider tendencies uncertain-small (Qld +0.0008 / +0.0013) |
| QRIC and SA stewards reports parsed (staging/stewards/stewards_events.csv.gz) | research data | Done 27 Nov (supplementary evidence only; never a rating input). Next: horse-level clear-running repeatability; wide with vs without cover |
| Jockey workload | research | CLOSED 27 Nov: no effect; artifact rule recorded (race-relative rating controls only). Reopen only with a substantive new reason |
| Handicap weight slope (Engine v2.4 candidate = v2.3 + wt_x_hcp) | release prep | Candidate built 27 Nov (benchmarks/engine_v2_4_candidate, not live). Needs: race class at race time (add TAB raceClassConditions to the step-2 RACE line + parser), switch file (off), parity, then Damo's release decision. Keep bm_change unserved |
| Rating update rule (cap heavy defeats 10-12 L, good runs 1.3x) | research -> shadow (decision) | Engine +0.0055 to +0.0073 per race; needs Damo's approval to build as a shadow (full rating + engine rebuild, kg scale changes) |
| bm_change train/serve gap | release clean-up | Never served; serving would cost 0.0008; drop from training at the next release (decision) |
| v2.3 frame build rewrites out/out_nat_r20*.csv and out_nat_venue_offsets.csv | operational fix | Side effect seen 27 Nov (restored from git); make the frame build write to a scratch path (with the next release wiring) |
| State seconds-per-length (Qld 0.170, SA 0.159, Vic 0.162) | research (national comparability) | Open: test state-specific conversion on horses moving between states |
| Common national framework for Qld (shadow) | build | Approved 26 Nov; not yet wired. Recommended 27 Nov: build together with the update-rule shadow (one rebuild); Damo's call |
| Kept open (untested, not rejected): course geometry and momentum retention; acceleration x course configuration; extra ground vs optimal distance; cross-jurisdiction inference; dynamic distance suitability | research | Open. An empirical leader-hold rate by track is not geometry |
| Moonee Valley new layout (planned 2027) | data rule | New configuration key when racing resumes; no transfer of old-layout tendencies |
| Measured race times vs margins x 0.170 s/L (Qld, SA, Vic) | research | Open |
| Interstate connections (pool levels inside the rating) | research | Open |
| One experience-shaped learning mechanism for all states | research | Open (Batch 13: shape supported, v3 setting not) |
| Qld duplicated track/distance/going history (simplification) | research | v2.1.2 shadow continues |
| Monday 30 Nov weekly update: first live run of the five foundation steps | operations | Scheduled; passed on a database copy only |
| PC collector install | operations (Damo) | Pending |
| SA gear history run; NSW notifications parser (other post styles); QRIC backfill check | operations | Pending |
| Ascot 12 Apr 2025 re-collection | operations | Queued for 30 Nov |

## Production from the 26 Nov 2026 run (recorded 25 Nov evening)
- NSW/Vic/ACT/SA/WA/Tas: Engine v2.2, weight carried (allocated minus apprentice claim, claim taken off once). Qld: Engine v2.1.1, allocated
  weight (its history is allocated too). Database master-2026-11-23-sa-wa-tas-qld. Each meeting's record in the day file names its engine release.
- Dashboard: first-starter / no-demonstrated-rating labels and a race Data confidence line (display only).
- Shadow (NOT LIVE): Qld Engine v2.1.2-candidate scored after publishing (DAILY_RUN step 5a, ops/run_shadow.sh) into prospective/shadow/qld_v2_1_2
  with its own index; never on the dashboard, never settled or ranked. A shadow failure is a warning, never a failed run.
- Prospective evaluation ledger (observational): outputs/prospective_eval.csv, one row per race per prediction set (production, shadow) after
  settlement (ops/evaluate_prospective.py, run by run_daily.sh). Reads saved predictions and results only; races from 26 Nov flagged untouched.
- Weekly job: TAB form records staged into the master database (history/load_form_staging.py: stg_form_runner, stg_form_start, stg_career,
  stg_form_check). Research only; never a release check; never a rating input.
- Tipping report card (observational, Batch 12 s2): ops/tipping_report.py after settlement, from the 26 Nov published predictions on.
  outputs/tipping_ledger.csv (one row per runner, never rewritten) and outputs/tipping_report.csv/.md (rebuilt daily): by dashboard
  classification (Strong selection, Leading contender, No clear selection, Insufficient evidence for top picks; Contender, Outsider,
  Insufficient evidence for the rest) and all top picks: selections, winners, strike rate, expected vs actual, calibration, notional
  flat-unit ROI % at OPEN and separately at CLOSE on their own eligible samples, price coverage, voids, dead heats; cumulative by day.
  No tote/SP/Betfair substitutes; late-scratching deductions not published by TAB and not applied (disclosed). Never read by any model.

## Staged data (not in the master database; 26 Nov 2026)
- South Australian tracking (tripleSdata reports, Morphettville/Parks, Murray Bridge, Gawler; Jan 2024 - Nov 2026): branch
  staging-sa-tracking, Queensland table shape, 93.6% of races pass every check. Collector: workflow racingsa-tracking (orphan
  branch raw-racingsa-tracking). Details and gaps: research/ops/DATA_ACCESS_tracking.md, research/staging/sa_tracking_report.md.
  Loading into the master database and adding SA to the weekly job await Damo's release decision.
- 26 Nov 2026 7:06am: LIVE in the master database (release master-2026-11-23-sa-wa-tas-qld-satrk, approved by Damo 7:01am "set this live"):
  sa_race 1,775 / sa_starter 18,822 / sa_sectional 133,905 (races passing every check; 53 races with duplicate rows excluded),
  sa_race_checks 1,954. Previous version on db-prev. Existing tables, parquets and engine frames byte-identical, so production
  ratings are unchanged; no model uses SA tracking yet (research first). Weekly incremental SA step: to be added to weekly_update.py
  and tested by a dry run after the 26 Nov daily run.

## Collection processes register and data foundation (26 Nov 2026, Damo 7:03pm)
The register of every collection process is research/ops/foundation/collection_processes.csv; the field-by-field source map
(primary/secondary source, history, forward process, database destination, matching rules, ratings vs research) is
research/ops/foundation/field_register.csv, explained in research/ops/foundation/DATA_FOUNDATION.md.
- ESTABLISHED EXTERNAL PROCESS: ChatGPT + Damo run a weekly, manually started Work session collecting Victorian TripleS
  sectional CSVs from Racing.com. Accepted start 1 July 2026; no resources on earlier coverage for now. Output: a ZIP of
  original files -> Claude validates and stages (history/stage_vic_triples.py -> research/staging/vic_triples).
  First ZIP (817 races, 1 Jul - 25 Nov 2026, 13 track configurations): validated, awaiting the integration decision.
- Direction: consolidation, not expansion. No new collectors; WA/Tas gear and stewards searches paused.

## Unattended runs: options and exact blockers (26 Nov 2026, Damo's brief section 7)
In place now (fallback, not permanent): wake-ups into the build conversation kept two days ahead (07:30 and 23:20), idempotent
runs, and workflow run-watchdog (08:50 and 00:45) that fails, so GitHub emails Damo, when a run did not reach the repository.
Known limits seen 26 Nov: an unanswered approval stopped the form helper at 293/317 and blocked NSW reads at 2pm; disabling
reminders was refused by the safety check; the conversation itself grows and is compacted.
| Option | Status | Exact blocker |
|---|---|---|
| Fresh scheduled Claude session doing everything | tried 26 Nov 7:30 | every new session needs Damo's approval for TAB reads (PROVENANCE_REQUIRED); no supported way found to pre-approve a site for scheduled sessions |
| GitHub Actions scripted collector | tried 24 + 26 Nov | TAB returns its website shell (HTML, 3,987 bytes) to GitHub's servers, also with Accept: application/json and for robots.txt; we do not impersonate browsers |
| Scripted collector in the cloud workspace | tried 26 Nov | workspace network allowlist refuses api.beta.tab.com.au (CONNECT 403). Team/Enterprise owners can change network access in Admin settings; plan type and whether TAB serves Anthropic's cloud addresses are unknown |
| Script on Damo's PC (Windows Task Scheduler) at 07:15 and 23:15, pushing raw files to the repository; fresh scheduled Claude session at 07:30 then needs no TAB reads | RECOMMENDED, not built | PC must be on and online at those times; one-time setup by Damo (Python, a GitHub token stored only on the PC, two scheduled tasks); TAB's terms for scripted personal use not confirmed (no developer API or terms found) |
The PC route also replaces the ~600-step form-record helper with an ordinary script (~10 minutes of paced requests), cached
and de-duplicated (only today's runner record plus past starts not already captured are processed).
