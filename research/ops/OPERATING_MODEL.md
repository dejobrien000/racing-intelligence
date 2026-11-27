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
| Horse identity correction (Batch 21 A1-A4) | APPROVED for the Monday 30 Nov master update, subject to checks | List: batch21/identity_correction_monday.csv (51 suffix + 5 sire/dam splits; 20 name variants kept as one horse; 3 flagged uncertain: Awol, Airclash, Infinite Rose; BEREZKA 7 Nov R5 record excluded). Live TAB matching by name + sire + dam: 1,030/1,068 unique, 38 genuine first starters, 0 ambiguous. Fallback: "identity uncertain" = no usable history, labelled. Versioned history release; no new prospective clocks (immaterial: 2.7% of recent runners move > 0.1 kg) |
| Seven-way responsiveness comparison (Batch 21 B6) | research | Stronger rule + history-completeness (7) best individually (24.72 kg2) and overall (+0.0102 / +0.0149) but -0.0026 vs rule 5 in inexperienced fields and -0.0005 in 2024; rule 5 freeze Monday |
| Certainty-weighting combined (Batch 21 B8) | candidate | Research code fixed (switch ignored inside the update-rule hook before 27 Nov; first combined runs invalid). Adds +0.0017 to rule 5 and +0.0016 to rule 7, both periods |
| Trainer-change and unfamiliar-distance breakthroughs (Batch 21 C9-C10) | research | Next-run under-reaction with controls: first run for new trainer +0.50 kg, runs 2-5 +0.23, unfamiliar distance +0.21; step-up breakthroughs carry at the new trip (+0.30), not back at the old (-0.01) |
| Pre-race rail (Batch 21 D11) | data access | TAB railPosition empty in all 163 captured races; RQ/SA rail recorded with results. Breednet race-page check pending site approval; no collector built |
| Barrier follow-ups (Batch 21 D12) | research | National bent shape +0.010 kg2/run (+0.002 to +0.017); absolute number, going and field-size factors rejected; 1301-1500 m course flips described |
| Sire debut record (Batch 21 E13) | candidate recommendation (decision) | Debut error 0.38 kg2 (sire) / 0.63 (sire + trainer); race +0.0006 / +0.0013 alone, +0.0008 / +0.0021 with trainer; 3yo clear, 2yo not; general inherited-ability prior, genuine first starters only |
| Name-key collisions merge different horses (Batch 20 A2) | data issue (master history) -> correction plan, Monday | 82 keys, 1,569 runs: 51 different countries + 5 different sire and dam = two horses; 26 dam-name variants probably one horse (check by hand). Sandbox split of 51: affected ratings mean 1.02 kg (max 16.7), others 0.01 kg. No production change until consequences presented; TAB names carry no suffix (serving needs dam/sire) |
| History-completeness experience rule (Batch 20 B4) | candidate (research form) -> freeze Monday, shadow after 29 Nov shadows run cleanly | Betfair start-list dates + held runs, labelled verified / complete / older beginner / probably incomplete; vs age-aware +0.0010 (2024) / +0.0008 (2025-26), both CIs above 0; older genuine beginners helped most |
| Race-layer refinement (Batch 20 C7) | research -> rejected (simplest forms) | rating x field inexperience -0.0005/race; x own or field uncertainty 0.0000. Inexperienced fields already calibrated (0.99); overconfidence is in established fields (0.90) |
| Certainty-weighted race reference (Batch 20 C8) | candidate | Production figures: +0.0014 (+0.0012 to +0.0016), both periods; no penalty for meeting inexperienced rivals; additivity with update rules untested |
| Pooled barrier expectation (Batch 20 D9) | candidate (Qld replace; SA add) | Qld replace +0.0022 / +0.0018 (CIs above 0), add worse; rail-free Qld 2025-26 +0.0009 (not clear); SA 2025-26 +0.0010. No pre-race rail in TAB capture; 1301-1500 m band negative |
| Trainer early improvement (Batch 20 F13) | research (no candidate) | 0.17 kg per kg after controls (0.26 in 2025-26, 3rd start, first prep); harness 0.0000 |
| Family after trainer controls (Batch 20 F14-F15) | research (no breeding input approved) | Sire's earlier debutants 0.33 kg2, maternal 0.09, damsire 0.07, full siblings 0.01; breeding x trainer interactions not clear |
| First-up own record (Batch 20 G16) | research | 0.14 (0.09 to 0.19) beyond fitness terms, 50,505 first-up runs; harness +0.0003 / +0.0001 (not clear) |
| Age-aware update rule shadow (Batch 19 A2) | SHADOW from the 29 Nov run (approved 27 Nov) | Release chain, parity 0.0 with research, fingerprints in candidate_record; benchmarks/engine_age_aware_candidate; UR_VARIANT=ageaware; own clock. Known limitation: by Nov 2026 most 5yo+ with few runs held are genuinely lightly raced (TAB form 28 of 30) |
| Trainer debut record shadow (Batch 19 A3) | SHADOW from the 29 Nov run (approved 27 Nov; no promotion) | Genuine debutants only. Checks passed (debut identification 68/70, trainer parity 70/70, no age/sex interaction). Harness +0.0004 / +0.0015; built check +0.0014 (+0.0009 to +0.0020), +0.0077 in debut races; debut error -0.19 / -0.24 kg2. benchmarks/engine_trainer_debut_candidate; ops/run_trainer_debut_shadow.sh (production frame read-only) |
| Lane-adjusted ratings, Qld and SA (Batch 19 A4) | BUILT (research form); shadow when operations allow | Lane bias not explained by extra ground (-0.08 kg/m) or tempo x position; cleaner help (after ground and pace). Shares: Qld 0.34 (pre-2024), SA 0.63 (2024). Gains: SA 2025-26 +0.0013 (+0.0003 to +0.0023); Qld 2024 +0.0009 (common) / +0.0008; Qld 2025-26 n.s. positive |
| History-completeness version of the experience rule (Batch 19 B6) | research -> DECISION (new versioned candidate) | Age floor works as an incomplete-history proxy: completeness floor vs age rule +0.0000 / +0.0008 (+0.0003 to +0.0012), pre-stated prediction met; thresholds: age 4 +0.0007 / +0.0003, age 6 -0.0007 / -0.0006. Complete-history horses: experience dominates, age adds a modest drop from 5. Prospective completeness from TAB as-at career starts |
| Individual vs race accuracy (Batch 19 B8) | research -> DECISION (race-layer test) | Strongest individual accuracy: 1.8x taper + age floor (MSE 25.03 / 24.65 vs v2.3 26.30 / 26.58). Race forecasts disagree only in maidens 2024: wider rating spread (3.36 vs 3.11 kg) over-read by one race-layer rating weight. Next: race layer reading ratings by field experience |
| Sustainability extended (Batch 19 B5) | research | One-offs keep 32% (6-11 starts) down to 9% (20+) over five starts; complete-history horses keep far more than pre-2022 careers; non-returners kept less (five-start figures describe survivors) |
| Barrier hierarchy (Batch 19 D13-D16) | research -> DECISION (pre-race input test) | Qld+SA, fit < 2025, judge 2025-26: pooled course x distance x rail beats national +0.041 kg2/run (+0.014 to +0.068); unpooled local worse (-0.033); course x distance slopes stable (0.54 vs random halves 0.59); recency weighting no help. National history holds no barriers (form records hold recent ones for current runners) |
| Family signals for debutants (Batch 19 C10) | research (no breeding input approved) | Maternal siblings +0.089 kg2, damsire +0.063, all three +0.131 (+0.038 to +0.231) on 2025-26 debut error; dams that raced in our data: 376 (unusable); full siblings no help |
| Sire maturity out of cohort (Batch 19 C9) | research (not supported as an input) | Cohort A -> B coefficient +0.24 (-0.12 to +0.60); sire means corr 0.11 between cohorts; Per Incanto +0.66 then +0.37 kg vs average; population 3->4 +1.4 to +1.8 kg |
| Trainer development patterns (Batch 19 C11) | research -> candidate idea | Early improvement at starts 2-3 persists (r 0.54 vs random 0.57); ready-on-debut stables improve less afterwards (-0.37); more 2yo debuts, less early improvement (-0.42) |
| Spacing and preparation preferences (Batch 19 E17) | research | Fresh preference repeats weakly (odd/even preps 0.033 vs chance p95 0.013; own record 0.14 per kg); progression and short-vs-longer spacing not distinguishable from chance; population fresh effect falls with age (+0.28 at 4 to -0.93 at 8) |
| Queensland runs held exceed TAB career starts (Batch 19 B6) | RESOLVED 27 Nov (Batch 20 A1): measurement bug, not history | ops/form_enrichment.py counted 32,989 Racing Queensland scratchings as starts; fixed (55.2% -> 0.0%, others 3% -> 0.1%); rating frames never contained scratchings; originals kept (*_before_b20_fix) |
| Fields-only meetings: non-Open TAB status shown as "scratched (TAB)" (Batch 19) | FIXED 27 Nov (display) | Same explicit-scratch rule as Batch 18 B, second code path in engine/export_ui.py; 27 Nov re-export unchanged |
| Research harness baseline: sandbox figure tables drifted (Batch 18; recorded Batch 19 G24) | RECORDED | batch19/BASELINE_CORRECTION.md + out_b19_baseline_correction.json: sandbox history file carried the v2.2 weight credit in speed figures; OFF = -0.0009 / -0.0002 vs released frame; PW now clear (+0.0014 / +0.0014); STD still worse; no release decision affected; parity checks recorded in every build |
| National emergencies that gain a start (Batch 18 B -> Batch 19 A1) | production fix (approved 27 Nov) -> VERIFY TONIGHT | Gained-start count rule in collect/national/build_snapshot.py behind ops/national_emergency_enabled (rollback = delete). 26 Nov: 11/11 correct (Queensland rule would have counted 8 that never ran: WA capture before its deadline). 27 Nov replay: 45 added, off = production exactly. Switch on only if 27 Nov results confirm; else keep the complete-field safeguard |
| "Scratched per TAB" shown for non-scratch TAB statuses (Batch 18 B) | FIXED 27 Nov (display) | Root cause: every non-Open status shown as scratched (41 Cairns "Reserve" runners). Now only LateScratched/Scratched; other statuses "No fixed odds shown by TAB; not a scratching". Forecasts never affected; originals preserved |
| Qld common framework shadows: emergency handling (Batch 18 C) | FIXED 27 Nov (shadow) | ops/qld_common_adapter.py uses Qld production rule. 27 Nov re-run: 126/126 runners, 14/14 races, 0 unmatched (was 117, 9 missing); sums 100; corr 0.88; same top pick 7/14. batch18/out_b18_qld_shadow_integrity_20261127_after_fix.json |
| Dashboard common national scale (Batch 18 A4) | DONE 27 Nov (display) | Fixed reference group (2025 BM64-72 runners), offset and spread per engine family; engine figures kept in brackets; engine calculations untouched; desktop and mobile checked |
| Age-aware experience update rule (Batch 18 D2/D4) | research -> DECISION (new shadow?) | Age floor (5yo+ counted as exposed) on the experience taper: vs taper +0.0018 (+0.0005 to +0.0031) 2024, +0.0025 (+0.0016 to +0.0034) 2025-26 (pre-stated mechanism test; helped both, more than predicted). Limiting the lightly raced boost to 1.3x (diagnostic, designed after both periods): vs uniform 1.3x +0.0017 (+0.0010 to +0.0025) / +0.0046 (+0.0039 to +0.0054); vs v2.3 (hooks-off) +0.0097 / +0.0104. Neither period untouched: only a frozen prospective shadow can validate it. Frozen uniform-1.3x and cap-only shadows unchanged. batch18/out_b18_harness.json |
| Why 2024 and 2025-26 disagreed on experience (Batch 18 D2) | research | Maidens worse both periods; exposed-horse race types flip; WA worse both. Incomplete-history share 26.5% vs 11.1%; clean-history 2024 races are mostly maidens, so that test was inconclusive. Age floor shows truncated run counts are part of it. batch18/out_b18_experience_split*.json |
| Sustainability of exceptional runs, 1/3/5 starts (Batch 18 D3) | research | Emerging keep ~61% of the gain (next run +0.99 kg above the revised rating); progressive/return-to-level 38% -> 28-29%; unprecedented one-offs 33% -> 27% (repeat 38%). Emerging 2-3yo 64% vs "emerging" 6yo+ 45%. 10 kg+ peaks: rating 6.2 kg below career best before (3.7 for 6-10 kg). 96-98% raced again. batch18/out_b18_sustainability.json |
| Heavy defeats: race-level-only cap (Batch 18 D5) | research (closed for now) | vs hooks-off: race level only, beaten horse own comparison unchanged +0.0022 (+0.0007 to +0.0036) / -0.0016 (-0.0028 to -0.0004); own-only +0.0051 / +0.0015; both +0.0073 / +0.0042. Race-level part pays only alongside the own part. Design caveat: race no longer balances |
| Lane bias: Qld retrospective candidate + SA replication (Batch 18 A5) | research -> DECISION (candidate for a frozen shadow; no release) | Same-day lane bias real: Qld +0.35 per kg (pre-2024 0.18, 2024+ 0.40), SA +0.59 (233 meetings); next run -0.13 Qld, -0.26 SA. Removing it from the rating figure (vs hooks-off): SA races 2025-26 +0.0013 (+0.0004 to +0.0022, share 0.51 set on 2024 = clean); Qld races +0.0002 to +0.0008 in all 8 comparisons (2 clear of zero). Small but consistent. batch18/out_b18_lane_*.json, out_b18_sa_lane*.json |
| Trainer debut record as a first-starter input (Batch 18 E6) | research -> DECISION (not authorised) | Shrunk point-in-time record of a trainer's earlier debutants: +0.0010 (+0.0001 to +0.0019) / +0.0020 (+0.0013 to +0.0026); first-starter races +0.0036 / +0.0086. Persistent r 0.38 (151 trainers). "Rarely debuts twos" proxy: their 2yo debutants -0.62 kg (opposite of selectivity); denominator limitation (unraced horses unseen). batch18/out_b18_debut_selectivity.json, b18_trainer_debut_feature.py |
| Maturity with continuation (Batch 18 E4) | research | 78% of 3yo seen at 4; +1.14 kg with 3+ runs each age. Per Incanto 86% continue, +2.36 kg (not a survivor effect); Justify +2.69 but 72% continue. Dam/siblings/damsire, debut-age cohorts, breeding x trainer carried to Batch 19 |
| Course-specific intelligence, hierarchical (Batch 18 F) | research (plan) | Layers course > distance > rail > meeting, shrunk; pre-race tendency vs post-race assistance kept apart; replaces, not adds to, generic barrier input; first test = barrier hierarchy as a pre-race input |
| Common national framework for Qld (Qld coefficients; keep Qld physical inputs as a variant) | research build -> shadow | Approved to build as a SHADOW (Damo 26 Nov 9:07pm). Not for promotion without an evidence review |
| Handicap weight slope on top of v2.3 (wt_x_hcp) | next release candidate | Approved to prepare for the following release; preregistered 2024 +0.0012 (0.0008-0.0017); needs build_v22 with the term + live term definition + parity |
| Batch 14: uneven-last-600 input for Qld (dip_last, dip_prior) | research -> prospective check | Open hypothesis, judged on races from 27 Nov; not a candidate until confirmed. Follow-up: +0.0040 (-0.0006 to +0.0095) 2024 on v2.1.3 - uncertain-small |
| Batch 14 follow-up (27 Nov): profiles, own-normal decline, riders, distance form, small-improvement bundle | research | Done; research/batch14/followup/README.md. No candidate except the weight slope (already queued). Rider tendencies uncertain-small (Qld +0.0008 / +0.0013) |
| QRIC and SA stewards reports parsed (staging/stewards/stewards_events.csv.gz) | research data | Done 27 Nov (supplementary evidence only; never a rating input). Next: horse-level clear-running repeatability; wide with vs without cover |
| Jockey workload | research | CLOSED 27 Nov: no effect; artifact rule recorded (race-relative rating controls only). Reopen only with a substantive new reason |
| Handicap weight slope (Engine v2.4 candidate = v2.3 + wt_x_hcp) | release prep | Candidate built 27 Nov (benchmarks/engine_v2_4_candidate, not live). Needs: race class at race time (add TAB raceClassConditions to the step-2 RACE line + parser), switch file (off), parity, then Damo's release decision. Keep bm_change unserved |
| Rating update rule (cap heavy defeats 12 L in the figure, good runs 1.3x) | SHADOW from 28 Nov (Damo 27 Nov) | Built by the v2.3 release chain (benchmarks/engine_update_rule_candidate; ops/run_update_shadow.sh -> prospective/shadow/update_rule). Built check 2025-26: +0.0059 (0.0043-0.0076) vs v2.3 as built, every state positive, top pick unchanged. kg scale 0.315 (v2.3 0.269). Promotion = separate decision on prospective races at the agreed checkpoints |
| bm_change train/serve gap | KEPT AS TRAINING-ONLY CONTROL (Damo 27 Nov, Batch 17 s4) | Documented in benchmarks/engine_v2_3/FEATURE_NOTES.md and in each candidate manifest. Serving it: -0.0012 / -0.0007; retraining without it: -0.0008 / -0.0005. No other unserved input may be kept without the same test |
| v2.3 frame build rewrites out/out_nat_r20*.csv and out_nat_venue_offsets.csv | operational fix | Side effect seen 27 Nov (restored from git); make the frame build write to a scratch path (with the next release wiring) |
| State seconds-per-length (Qld 0.170, SA 0.1595, Vic 0.162) | research (national comparability) | Batch 16: empirical clock-margin relationships (no official rule verified); Qld fixed at 0.170 since 2025, SA/Vic vary by distance (sprints lower). Standardising margins: engine -0.0012 (2024) / -0.0006 (2025-26) nationally; Qld +0.0005 / +0.0007. Interstate offsets unchanged by it. NOT adopted; no state corrections |
| Common national framework for Qld (shadow) | SHADOW from 28 Nov (Damo 27 Nov, Batch 17 s2) | Configs 2 (national v2.3 rating) and 4 (update-rule rating) built by the national release chain refitted on Qld races (benchmarks/engine_qld_common_candidate, engine_qld_common_update_candidate); ops/run_qld_common_shadow.sh via ops/qld_common_adapter.py. Built 2025-26 out of sample vs the v2.1.3 structure (harness): +0.031 / +0.035. Qld physical inputs add +0.002 (not clear): not in the shadows. Emergencies are not rated by the national scorer (Qld production rates them) |
| Engine Performance tab and tracking inspection (dashboard) | done 27 Nov | Display only. Update benchmarks/engine_lineage.json at every release and when a shadow starts or stops |
| Provenance: v2.3 manifests record the base manifest hash; first-layer files record the v2.2 history file | FIXED 27 Nov | Settings record from the 28 Nov run; first-layer history fingerprint fixed 27 Nov 11:15 (correction record prospective/prerace/20261127/v1_history_file_correction_20261127.json); replay identical |
| Kept open (untested, not rejected): course geometry and momentum retention; acceleration x course configuration; extra ground vs optimal distance; cross-jurisdiction inference; dynamic distance suitability | research | Open. An empirical leader-hold rate by track is not geometry |
| Race reference weighted by rating certainty (Batch 16 C13) | research | On v2.3: +0.0006 (n.s.) 2024, +0.0011 (0.0004-0.0018) 2025-26. One heavy defeat costs the other runners 0.58 kg next time under v2.3. Tested on top of the update rule (see Batch 16 ledger) |
| Receiving-trainer uplift on transfer (Batch 16 C17) | research -> decision | Persistent by trainer (r 0.58 across periods, 57 trainers); no generic stable-change effect (-0.38 kg first run). Candidate term inside the trainer family if Damo wants it |
| Age & sex for first starters at race time | PRODUCTION from 28 Nov 7:30am (Damo 27 Nov, Batch 18 A1) | Switch ops/agesex_tab_enabled; DAILY_RUN step 3b fetches the TAB form subset before scoring (reused later; no duplicate requests); unknown stays missing; fetch failure falls back and is logged. 27 Nov replay: 49 filled, first starters -1.1 to +2.0 points, no top pick changed. Harness +0.0005 / +0.0009. Release note: benchmarks/engine_v2/RELEASES.md |
| Distance suitability (kernel), ability ceiling, course geometry (Batch 16 C14/C15/C18) | research | Suitability and ceiling: real at rating level, redundant in the engine (gain 0.0000; Batch 12 peaks). Geometry x momentum: rejected (sign flips) |
| Prospective checkpoints | APPROVED (Damo 27 Nov, Batch 17 s1) | 300 / 1,000 / 2,000 settled, eligible, paired races per comparison; review points, not release thresholds (benchmarks/engine_lineage.json) |
| Metro flag at race time (SA, WA metros) | FIXED from 28 Nov 7:30am (Damo 27 Nov, Batch 18 A2) | Switch ops/metro_tier_enabled: live metro = training venue tier (all states audited; only SA Morphettville/Parks and WA Ascot/Belmont were wrong; Qld family has no metro terms). 27 Nov replay identical; harness on SA/WA metro races -0.0021 (-0.0046 to +0.0002) / +0.0002 |
| Qld production course names (sponsor names, spaces) | FIXED from 28 Nov 7:30am (Damo 27 Nov, Batch 18 A3) | Switch ops/qld_course_map_enabled; prerace/qld_courses.py (all Qld courses audited; Polytrack separate; configs not merged). First-layer track history 0% -> 73% of runners; Cairns course records 0% -> 88%. 27 Nov replay: Cairns mean change 1.1 points (max 7.2; 1 of 7 top picks), Sunshine Coast 0.3 |
| Heavy-defeat cap: which mechanism helps (Batch 17 s10) | research | Own-update-only cap +0.0042 / +0.0012; race-reference-only cap -0.0006 / -0.0034 (it deepens the beaten horse's own drop); both (figure capped) +0.0064 / +0.0040. The gain is mainly the beaten horse's own update, with the race-level part adding about a third when combined |
| Exceptional positive runs (Batch 17 s11) | research | Bigger surprises are more under-believed overall (v2.3: +0.17 kg next after a 2-4 kg run, +1.91 after 10+); lightly raced most (+0.57 to +2.47); experienced horses' unprecedented isolated peaks slightly over-believed (-0.56 to -0.75 at 6-10 kg) and 1.3x makes that a little worse. Experience-tapered response: rating-level residuals flatter but engine 2024 -0.0025, 2025-26 +0.0050 vs uniform 1.3x: inconsistent, not a candidate |
| Track bias, Qld tracking (Batch 17 s13-14) | research | Outside barrier costs ~1 kg (2.7-3.3 kg in some rail-out sprints); configuration slopes real but only partly stable across years. Race-day lane bias persists within a meeting (first vs second half r 0.23) and ~1/3 of it is credited to ability: next run -0.13 kg per kg of lane help (-0.18 to -0.09). Candidate direction: a retrospective lane-bias allowance in the Qld figure |
| Breeding priors (Batch 17 s19-20) | research | Pedigree held for 99.8% of runs (1,205 sires). Sire distance/going records do not help as a simple prior (slightly negative, likely placement selection). Sire 3-to-4yo improvement is modestly repeatable across cohorts (r 0.30, 138 sires); Per Incanto +2.6 kg vs +1.0 average (67 horses; selection not removed) |
| Stable presentation scale (Batch 17 s6) | demonstration | Offset-and-spread mapping on 2025 BM64-72 runners: v3 vs v2.3 raw gap 8.0 kg -> 0.5 kg; update rule 3.7 -> 0.03 kg; Qld horses v3 vs v2.3 7.8 -> 0.2 kg. Not implemented |
| Moonee Valley new layout (planned 2027) | data rule | New configuration key when racing resumes; no transfer of old-layout tendencies |
| Measured race times vs margins x 0.170 s/L (Qld, SA, Vic) | research | Open |
| Interstate connections (pool levels inside the rating) | research | Batch 16: SA ~0.5 kg high vs Vic, Qld ~0.4 high vs NSW, Tas ~1.5 high vs Vic (movers both ways); a state-pair engine term adds nothing (+0.0004 n.s. / +0.0001): the engine already prices it. No correction |
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
