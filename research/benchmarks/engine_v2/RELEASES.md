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
- Open: one meeting not collected (Ascot 12 Apr 2025, server error 500) - retried with the next weekly update.
