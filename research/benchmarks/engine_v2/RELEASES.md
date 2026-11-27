# Engine v2 releases

## v2.1 - 25 Nov 2026, 12:17pm Brisbane (Queensland: v3 rating)
- Queensland's national rating is the v3 rating (engine/dyn_v3.py; settings a_q=1, n0=4, g_imp=1 chosen on pre-2025 runs only):
  lightly raced horses are expected to improve after each run, and their ratings move a little more. Queensland v1 coefficients
  refit on development races (benchmarks/candidates_b4_national_v3), v2 terms refit as in v2.0 (benchmarks/engine_v2_1).
- Gate (research/batch9): Queensland v2.1 vs v2.0 on identical 2025-26 races +0.0052 log-lik per race (0.0028 to 0.0076),
  2026 alone +0.0067 (0.0028 to 0.0104); top pick +0.25 / +0.44 points (not significant). Re-used data: not untouched evidence.
- NSW/Vic/ACT unchanged (the v3 rating hurt there: -0.003 per race, it double-counts starts and age).
- Approved by Damo in chat 12:09pm (after advice to track it first). Ipswich re-issued before race 1; earlier sets kept.
- Operations: engine/frames/national_v3.parquet must exist (engine/build_frame_v3.py builds it); ENGINE_V21=0 restores v2.0.x.

## v2.0.2 - 25 Nov 2026, 12:06pm Brisbane (display calibration; ratings unchanged)
- Shown win chances use the bent-line runner calibration (benchmarks/engine_v2/runner_calibration_v2.json, built by
  engine/runner_calibration_v2.py on the same 2025-26 out-of-sample predictions as v2.0). Validation: fitted on 2025, judged
  on 2026 (research/batch9/out/e_calib.csv): 50%+ chances shown 47.5% / 43.5% vs won 43.7% / 43.0% (NSW-Vic / Qld), previously
  52.3% / 52.7%; overall log loss unchanged or better; 0% of races reordered.
- Approved by Damo in chat 12:05pm, applied before any race on 25 Nov. Selection-strength thresholds recomputed to match.

## v2.0.1 - 25 Nov 2026, 11:11am Brisbane (scorer fix; no coefficient changes)
- Fault: the Queensland pre-race scorer (prerace/score_prerace.py) never attached the national dynamic rating to history rows,
  so its development spread was blank and every live value was set to 0. Live Queensland ratings from 24 Nov to 25 Nov 11:11am
  therefore gave the strongest Queensland feature (dyn_nat, 0.347 per dev sd) zero weight. Research results were unaffected.
- Fix: history rows keep their Queensland ids; a guard now stops the scorer if the rebuilt spread differs from the frozen
  value (2.9392 kg) by more than 2%. Rebuilt spread after the fix: 2.9392.
- Evidence: dropping the national rating costs 0.025 log-likelihood per race on 2025-26 (95% 0.018 to 0.033), about one
  top-pick point (engine/out/ablation_qld.csv). The fix restores the validated model; it adds nothing new.
- Applied: Ipswich 25 Nov re-issued on the same 7:51am fields (top pick changed in 5 of 7 races); the 7:56am set is kept.
  Approved by Damo in chat, 25 Nov ~11:10am, to replace from now on.

## v2.0 - 24 Nov 2026 (benchmarks/engine_v2/manifest.json)

## Database release master-2026-11-23-sa-wa-tas (25 Nov 2026, approved by Damo 2:15pm Brisbane; live from the 26 Nov 7:30am run)
- What changed: SA, WA and Tas Breednet results Oct 2022 - 23 Nov 2026 (2,170 meetings) added to the master database and
  to the national rating. SA/WA/Tas meetings are rated from 26 Nov instead of shown as fields only. No coefficient changed.
- Evidence (copy of the database, 2025-26 races): NSW top pick 28.45% -> 28.43%, Vic 27.63% -> 27.61% (unchanged);
  on SA/WA/Tas races the model never saw: WA 28.1%, Tas 30.8%, SA 25.0%. 95.3% of SA/WA/Tas runners have a measured
  prior run; horses with none still get no rating. NSW/Vic/ACT ratings moved 0.24 kg on average (horses that also raced
  in SA/WA/Tas). Queensland scale check 2.992 vs frozen 2.987 (limit 2%); today's Ipswich chances moved 0.05 points,
  same top picks. Dry run on today's Strathalbyn, Albany and Launceston fields rated them (not published).
- Previous version kept on branch db-prev (master-2026-11-23). Roll back: ops/db_config.json states NSW, VIC, ACT and
  restore db from db-prev. Today's (25 Nov) published tips and settlement use the previous version and are not changed.
- Open: one meeting not collected (Ascot 12 Apr 2025, server error 500) - one-off retry after the Queensland backfill
  (the weekly update only re-reads the last 10 days). Local working copy (this chat) switches to this version after
  the 25 Nov settlement tonight, so tonight's settlement uses the same database as this morning's tips.

## Engine v2.2 (approved by Damo 25 Nov 2026 ~3:25pm "Replace from tomorrow"; live from the 26 Nov 7:30am run)
- Applies to NSW, VIC, ACT, SA, WA and TAS meetings. Queensland stays on Engine v2.1.
- What: Engine v2 NSW/Vic family score + 14 Batch 10 terms (benchmarks/engine_v2_2/manifest.json): below its best three runs, vs its
  longer-run level, last 5 vs longer-run level, long-run trend, run of below-par runs, unusually variable lately, own consistency x
  favourite/outsider, hot start to the preparation, quick backup, step in measured venue class, recent form x established horse, light
  weight (54 kg or less), runs on file, rating certainty. Display calibration refitted on v2.2 chances (runner_calibration_v22.json).
- Evidence (research/batch10, research period only): fit to 2023 judged on 2024 +0.0058 log-lik per race (0.0032 to 0.0083), top pick
  +0.25 pts; fit to 2024 judged on 2025-26 +0.0125 (0.0105 to 0.0145), NSW/Vic/ACT +0.0103, SA/WA/Tas +0.0174 (SA +0.024), top pick +0.02 pts.
  2025-26 had been examined before, so the first untouched evidence is races from 26 Nov 2026 (compare with the v2.0 score, kept in v1/v2 files).
- Checks: production features equal the research features for 1,313 runners on 3 dates (batch10/scripts/test_v22_parity.py, PASS);
  sandbox replay of 25 Nov Strathalbyn, Albany, Launceston through scoring, ranking and dashboard export: reconciles (not published).
  Top picks unchanged at Albany (7/7) and Launceston (8/8), 3 of 7 changed at Strathalbyn.
- Coefficients: all races to 23 Nov 2026 on top of the production v2 score (same rule as v2); dev-fit coefficients recorded in the manifest.
- Roll back: set ENGINE_V22=0 for engine/score_v2.py and engine/export_ui.py (or revert this commit). Days before 26 Nov always export with their own engine.
- Also from Batch 10 (approved): each venue's measured class (average rating of the fields it attracts) is shown as a meeting note.
  Frozen v2 terms keep their original metro flag (their coefficients were fitted with it). SA calibration left unchanged (Damo: no).

## Engine v2.1.1 (Queensland) + database master-2026-11-23-sa-wa-tas-qld (approved by Damo 25 Nov 2026 ~4:25pm "Refit tonight, live tomorrow"; live from the 26 Nov 7:30am run)
- Data: Breednet Queensland results Oct 2022 - 23 Nov 2026 (2,159 meetings). 1,244 are RQ-tracked meetings already held (used only for
  ages); 915 untracked meetings (54,301 runs: country tracks and pre-tracking gaps) join the national rating. No duplicates (0 Breednet
  meetings shared most horses with an RQ meeting under another name). Queensland ages known for 98.9% of 2025-26 runners (was 0%).
- Why a refit: the Queensland rating's development spread moved from 2.987 to 3.076 kg (+3%), outside the v2.1 scorer's 2% guard.
  Same model as v2.1, refitted on the new database (batch10/v211/build_v211.py): v1 coefficients on development races, v2 terms penalty 100.
- Gate vs current v2.1 on identical 2025-26 Queensland races: +0.0121 log-lik per race (0.0063 to 0.0175), top pick +0.8 pts
  (0.06 to 1.54), winner in top 3 +1.0 pts; 2026 alone +0.0073 (-0.0012 to 0.0145). Research-period evidence (re-used 2025-26).
- NSW/Vic/SA/WA/Tas (national family, frozen coefficients, before -> after): NSW fit 12.67 -> 12.77%, Vic 12.16 -> 12.19%, SA/WA/Tas
  unchanged within 0.06; top picks within +/-0.2 pts. Engine v2.2 terms unchanged (their venue classes do not include Qld country tracks:
  a step from one of those is treated as no information).
- Checks: sandbox replay of 25 Nov Ipswich through the Qld scorer (scale guard 3.0761 = frozen), Engine v2, ranking and export: reconciles;
  6 of 7 top picks unchanged vs the published v2.1 set (not published). Published database re-downloaded and every checksum verified.
- Weekly job: Breednet collection now includes QLD; national rating uses Queensland Breednet meetings (ops/db_config.json).
- Roll back: ops/db_config.json qld_breednet_in_national_rating false, restore db from db-prev (master-2026-11-23-sa-wa-tas) and the
  previous benchmarks/candidates_b4_national_v3 + engine_v2_1 manifests from git (commit before this one).

## Dashboard display: experience labels and race data confidence (from the 26 Nov 2026 run) — display only
- Batch 11 s5 (requested by Damo). Ratings, chances, rankings and labels like "Strong selection" are unchanged; this only adds wording.
- Runner line: "First starter · no demonstrated race rating" (no rated runs and no previous start known to our sources),
  "Has raced, but no rated runs held · no demonstrated race rating", "Runs held only outside Queensland tracking · Queensland form
  inputs missing" (Qld model only), or "Lightly raced · 1-2 rated runs". These runners keep a chance: it is a prior estimate
  (jockey and trainer records, weight, barrier, age and sex, average for its experience), not measured ability.
- Race line: Data confidence High / Medium / Low. Low = top pick has no demonstrated rating, or unrated runners hold 30%+ of the
  model's win chance; Medium = 10%+ or a 1-2 run horse in the top three. Shows how many runners are unrated and their share of chance.
- Checked: sandbox export of 25 Nov Albany, Launceston and Strathalbyn on the final database (v2.2); dashboard script syntax-checked.

## Weight correction: national model uses weight carried (from the 26 Nov 2026 run) — correction, approved by Damo 25 Nov 2026
- Why: the history the national model learned on (Breednet results) holds the weight CARRIED after the apprentice claim (matches the
  NSW form line's carried figure on 99.8% of 19,010 checked starts). TAB fields give the ALLOCATED weight (handicapWeight) with the
  claim separate (claimAmount; -1 = none). Checked live on the 26 Nov racecards: Mornington R1, 3yo maiden at set weights 58 kg,
  Zaac 58 kg with a 2 kg claim -> TAB weight is before the claim. Queensland is not changed: its history (RQ) is allocated weight too.
- Change: prerace/score_national_prerace.py computes weight_carried_kg = allocated - claim (claim read once, 0-4 kg, asserted) and
  uses it for weight-vs-field and today's rating row; engine/score_v2.py uses that column (no second deduction) for weight change
  and the v2.2 light-weight term, then restores the allocated weight for output. Files and dashboard keep showing the allocated
  weight with the claim beside it. New output columns: claim_used_kg, weight_carried_kg, weight_basis.
- Gate: WEIGHT_CARRIED (default 1) and WEIGHT_CARRIED_FROM (default 2026-11-26). Earlier days are scored exactly as before.
- Checks (sandbox, final database, v2.2): replay of 25 Nov Albany, Launceston, Strathalbyn, Geelong, Wyong (37 races, 52 claimed
  runners): 1 top pick changes (Geelong R5 Sixty Grand over Mickio), largest chance move 1.1 pts; code output identical to a
  hand-made carried-weight replay; export recompute check passes; dashboard shows allocated weight + claim; 25 Nov rescored
  with the default gate = identical to the pre-correction run (claims not used). Coefficients unchanged (they were fitted on carried weight).
- Roll back: WEIGHT_CARRIED=0 in the run environment, or revert this commit.

## Engine v2.3 (six states) and Engine v2.1.3 (Queensland) - APPROVED by Damo 26 Nov 2026 9:07pm ("Approve both"); live from the 27 Nov 7:30am run
- Switches ON: research/ops/engine_c2_enabled and research/ops/engine_qld213_enabled (each file records the approval).
- Kept for rollback and prospective comparison: Engine v2.2 (benchmarks/engine_v2_2, engine_v2_1 NSW family, candidates_national_common)
  and Engine v2.1.1 (benchmarks/engine_v2_1, candidates_b4_national_v3) are unchanged on disk and are scored every day after publishing
  as the PREVIOUS-ENGINE SHADOW (ops/run_prev_shadow.sh, called by ops/run_shadow.sh in step 5a): prospective/shadow/prev_engines/,
  own INDEX.csv, never on the dashboard, never ranked or settled; the evaluation ledger records it as prediction 'previous_engine'.
- kg scale (display): the six-state kg-equivalent scale changes from 0.226 to 0.269 model units per kg, so the same performance reads
  about 16% smaller in kg under v2.3. A change of units, not of ability: compare kg ratings within one engine only. The dashboard's
  scale note and release note say so; Queensland's scale is unchanged (0.2243).
- Ability ratings vs time figures stay distinct: the weight credit (0.25 kg per kg) changes how the opposition-aware ABILITY rating reads
  past runs; 0.170 s per length changes how margins become TIME FIGURES (estimates, never shown or stored as measured times).
- Re-exports and meeting refreshes follow the engine that scored the day (export reads the day's saved engine_release; refresh_meeting.sh
  reads the switch files); a failed v2.3 frame build sets ENGINE_C2=0 for that day.
- Default: neither switch file exists, so the 27 Nov run is the 26 Nov configuration. Parity replay of the 26 Nov run with both
  switches off, on the final code: every number identical in all 8 prediction files and all 260 dashboard runners.
- Engine v2.3 (research/ops/engine_c2_enabled): national history rating credits 0.25 kg per kg of weight carried (was 1 kg) and turns
  margins into time at 0.170 s per length (was race speed); then the same release chain as production on that rating: nat_v2 v1 frozen
  (benchmarks/engine_v2_3/candidates_national_common.json), Engine v2 family (engine_v2.json; penalty re-chosen 1e-6, was 1000), the
  14 v2.2 terms and venue class (engine_v2_2.json), display calibration (runner_calibration.json). kg scale 0.269 (was 0.226).
  Evidence: built release vs production as it runs, 2025-26, 23,729 races: +0.0095 log-lik per race (0.0076 to 0.0113), top pick
  28.51% vs 27.91% (+0.60 pts, 0.31 to 0.93); every state positive (SA +0.0023, smallest); 2025 +0.0115, 2026 +0.0072. 2024 (Batch 12,
  both refitted): +0.0105, but 2024 helped choose 0.25 from five preregistered settings. SA was in the fitting data: not independent.
  Run cost: the daily run builds national_runs_c2.parquet and engine/frames/national_c2.parquet (3.5 min, identical to the sandbox
  frames the release was fitted on); any failure falls back to v2.2 for that day.
- Engine v2.1.3 (research/ops/engine_qld213_enabled): Queensland v2.1.1 + the national Age & sex family (age, 3yo and under, 7yo and
  over, filly/mare), possible because Qld ages are now held for 98.9% of runners. v1 frozen at the v2.1.1 values; v2 family refitted
  (penalty 100, as v2.1.1) on development and on all races (batch13/build_qld_v213.py -> benchmarks/engine_v2_1_3/manifest.json);
  Qld display calibration refitted on v2.1.3 out-of-sample chances (it was still the v2.0 fit). kg scale held at 0.2243 (refit
  0.2423 recorded) so Qld kg figures stay comparable. Evidence: 2024 +0.0190 (0.0128 to 0.0253); 2025-26 +0.0166 (0.0116 to 0.0215),
  2026 +0.0238; top pick +0.15 pts (not significant), winner in top three +1.6 pts. NSW/Vic/ACT/SA/WA/Tas untouched by this switch.
- Replay of 26 Nov with both switches on (sandbox, not published): 4 of 29 top picks change (Geraldton R2, Hawkesbury R2, Rockhampton
  R1 and R5); every meeting labelled with its engine; dashboard breakdowns reconcile with each engine's own kg scale (exporter fix
  26 Nov night: v2.3 meetings divide by v2.3's kg scale).
- Roll back: delete the switch file(s). Days already published keep their own engine. The morning run pulls from GitHub first
  (ops/DAILY_RUN.md step 0), so a switch created or deleted on GitHub takes effect at the next run.
- Not in this release (deliberately): the handicap weight slope (next candidate, builds on v2.3), the common national framework for
  Queensland (shadow next), anything from the 30 Nov database update, any sectional/stride/gear/stewards coefficient.

## Dashboard housekeeping (27 Nov 2026, Damo 9:38am) - display only; ratings, chances, rankings and selections unchanged
- Tab "Engine v1 vs v2" renamed "Engine Performance" (same tab, same route). It showed today's production engine against its own first
  layer (the "v1" score inside it: for v2.3 meetings that layer runs on the v2.3 rating), plus the 24 Nov v1-vs-v2.0 backtest. It now shows:
  production engines vs their immediate predecessors (Engine v2.2 / v2.1.1, scored daily as shadows), prospective record since release,
  shadow candidates (scoring, built-but-waiting and approved-but-not-built), production record by engine, and the release evidence chain
  with its evidence status. Sources: benchmarks/engine_lineage.json (update at every release) and outputs/prospective_eval.csv, via
  engine/engine_performance.py. The 24 Nov backtest is kept as a collapsed archive; days exported before 27 Nov keep the old view.
- The daily run refreshes the tab after the evaluation ledger (ops/run_daily.sh, non-fatal), so it includes yesterday's races.
- Sectional message: it was hard-coded by model family ("Not published for NSW/Vic history" for every non-Qld meeting and runner); it read
  no tracking table. Now each meeting says whether the model uses sectionals there and how many runners have tracked runs held (Qld, SA,
  Vic), and each runner's drawer lists its latest 5 tracked runs (date, course, distance, finish, time, last 600, last 200; measured vs
  derived labelled) from the master database tracking tables (engine/tracking_view.py). Victorian runs appear by themselves once the
  30 Nov weekly update loads vic_race/vic_starter/vic_sectional. Display only: no tracking reaches a rating outside Queensland.
- Fixes found on the way: (1) meeting links for names with spaces (Sunshine Coast, Mount Gambier) did not open from the meeting chips
  (the router only accepted one-word ids); fixed. (2) a re-export after settlement dropped the running returns history that settlement
  writes into the day file; the exporter now keeps it, and writes the day file atomically.
- Checks: re-export of 27 Nov identical to the published file in every rating, chance, rank, price and selection (only wording and the
  new keys differ); headless render of every view and of 4 drawers per meeting on 27 Nov and 26 Nov data: no script errors.

## Record-keeping fixes (27 Nov 2026, Batch 16 A1/A2/A5) - no rating, chance, rank or selection changed
- Settings fingerprint (A2): engine/score_v2.py recorded engine_manifest_sha256 from the base file it loads first; under Engine v2.3 the
  national family is replaced in memory by benchmarks/engine_v2_3/engine_v2.json, so the 27 Nov national files named the wrong file.
  From the 28 Nov run each Engine v2 manifest has a 'settings' record: engine version, production or shadow, a fingerprint of the
  settings held in memory, every settings file loaded with its sha256, the v1-layer settings, the rating frame and its sha256, kg scale,
  history cutoff, generation time and fallback (run_daily.sh / refresh_meeting.sh pass ENGINE_FALLBACK when v2.3 frames are missing).
  engine_manifest_sha256 now fingerprints the file that supplied the family. The record step can never stop scoring.
- 27 Nov correction: prospective/prerace/20261127/settings_verification_20261127.json (originals unchanged). Replay of all 8
  meetings from saved inputs under v2.3/v2.1.3 reproduced all 561 scores (max difference 4.4e-16); under the earlier settings the
  national replays stop at the rating guard and Queensland differs by up to 0.51. The dashboard shows it as "verified afterwards".
- Race list (A1): the run keeps TAB's race list (RACES lines) so a listed race that is not read shows as missing on the dashboard;
  "SSC R8" of 27 Nov was a calendar misread (TAB lists 7 races). RACE lines gain TAB's raceClassConditions (collection only).
- Tracking display (A5): runs shown are cut at the forecast's own history cutoff, with the database release that supplied them; a
  later re-export says when tracking was added after the forecast; a read error is shown as an error, not as "no tracked runs".
- First-layer history file (A2 follow-up, 27 Nov 11:15): prerace/score_national_prerace.py recorded the fingerprint of
  national_runs.parquet while Engine v2.3 reads national_runs_c2.parquet. From the 28 Nov run it records the file it actually reads
  (national_runs_file + national_runs_sha256) and any rating-update settings. 27 Nov correction:
  prospective/prerace/20261127/v1_history_file_correction_20261127.json (6 national files; originals unchanged; the v2.3 history file was
  built 36 s before scoring and has not changed since). Replay of the 6 national meetings on the new code: every number identical
  (v1 and v2, 2,175 runner rows).
- Shadow-only engine overrides (Batch 16 B9): ENGINE_CAND_DIR / ENGINE_CAND_FRAME / ENGINE_CAND_LABEL point the three layers at a
  candidate's own files; unset in production (verified by the replay above). Used only by ops/run_update_shadow.sh.

## Production corrections effective from the 28 Nov 2026 7:30am run (approved by Damo 27 Nov 2026, Batch 18 A1-A3)
Each is a serving correction with its own switch file (rollback = delete the file); no coefficient changed; every shadow uses the same
corrected inputs, so production-vs-shadow comparisons stay like-for-like from 28 Nov. Replays use this morning's saved inputs (scratch only).
- Queensland course names (ops/qld_course_map_enabled; prerace/qld_courses.py): today's Racing Queensland names are mapped onto the
  course keys in Queensland history (sponsor names for Cairns, Gold Coast, Warwick; spaces vs underscores everywhere; Polytrack kept
  separate). Before: no Queensland runner had any track history in the first layer (0% vs 67% of history rows) and no Cairns runner had a
  course record in the second layer. After (27 Nov replay): track history found for 73% of runners, Cairns course records 88%. Replay with
  the switch off reproduces production exactly; with it on: Cairns mean change 1.1 points (max 7.2; top pick changed in 1 of 7 races),
  Sunshine Coast 0.3 (max 2.1; no top pick changed). History keys themselves are unchanged (tracked and untracked rows of one course
  still carry different keys - a refit question, not a serving fix).
- Metro flag (ops/metro_tier_enabled): live metro = the venue's tier in the training history (adds SA Morphettville and Morphettville
  Parks, WA Ascot and Belmont; course variants mapped first). 27 Nov replay: identical (no SA/WA metro meeting). Harness on SA/WA metro
  races: 2024 -0.0021 (-0.0046 to +0.0002), 2025-26 +0.0002 (-0.0013 to +0.0017): no measurable accuracy effect; made for consistency.
- First-starter age and sex (ops/agesex_tab_enabled; DAILY_RUN step 3b): runners with no history take age and sex from TAB's form record
  fetched before scoring; unknown stays missing. Harness +0.0005 (2024) / +0.0009 (2025-26); 27 Nov replay: 49 runners filled, first
  starters -1.1 to +2.0 points, no top pick changed. If the morning fetch fails, scoring falls back to the old treatment and logs it.
