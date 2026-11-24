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
