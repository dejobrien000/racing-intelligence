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
