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
