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

Interim daily run: if the 7:33 scheduled run logs "ATTENTION: TAB fetch needs approval", run DAILY_RUN.md in the build
conversation (session_01TcfAeuNwdADDxa3cwHWiRz) when its 7:35 reminder arrives; the leftover 7:45/7:50/8:20 reminders
there are superseded (old PC-based cycle) and are ignored.
25 Nov 10:21: Damo approved the TAB read in the build chat. 10:40 test (new URL, Damo asked not to approve anything):
dates/2026-11-26/meetings returned data (HAW, MOR, ROC, GER) -> the approval now holds in this chat with nobody answering.
Whether it also covers fresh scheduled sessions is shown by the 26 Nov 7:33 daily run (log research/ops/logs/2026-11-26.md).
TAB's info-service lists only today and future dates (25 Nov 10:20: dates = 25, 26, 28, 29 Nov, 4 Dec; 24 Nov meetings = []).
So CLOSE (final fixed price with the results) may not be readable at 7:30 next morning: checked tonight + 26 Nov 7:30.

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
- Prepared, not released: Breednet Queensland country meetings (switch NAT_QLD_BN in national.py, off). Needs the Qld
  backfill (running on GitHub) and an evaluation shown to Damo first.
