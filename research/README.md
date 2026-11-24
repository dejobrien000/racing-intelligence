# Research lab (Queensland first findings, 24 Nov 2026)

Rebuild the research table, then run each investigation:

    python3 build_runs.py ../history/history.duckdb runs.parquet
    python3 inv1_barriers.py          # barriers, Doomben 1200 example
    python3 inv3b_interaction.py      # metro barriers by exact distance; last-600 x step-up
    python3 inv2_pace.py              # settling position, run-style persistence
    python3 inv3_l600.py              # last 600m and next start
    python3 inv45_ground_fitness.py   # ground covered; days between starts; preparation pattern

Outputs land in out/ as CSV. Exploration period: Oct 2022 - Dec 2025. Hold-out: 2026.
Baseline everywhere: expected wins = 1 / field size. No prices or market data are used.

## Added 24 Nov 2026
Run in this order after `build_runs.py`:
1. `python3 rating_v0.py runs.parquet runs_rated.parquet` - run rating v0 (time figure in kg, 100 = par), early tempo,
   finishing speed, pre-race figures, field strength. `python3 rating_v0_check.py` - repeatability and predictive checks.
2. `python3 inv9_r9_deep.py` - R9 deep dive (class move, race strength, tempo, venue, distance, margin, figure).
3. `python3 inv10_barriers_context.py` - barriers by rail, field size, distance, running style, pace pressure (BH q-values).
4. `python3 inv11_preparation.py` - figures through a preparation, horse fixed effects.
5. `python3 lab.py --when "<filter>" --vs "<filter>" --by <columns> [--since YYYY-MM-DD]` - answer a next-start question
   in racing language with A/E, CIs and a horse-clustered adjusted odds ratio. Shared frame in `frames.py`.
   Example: `python3 lab.py --when "top_l600==1 and step_up==1" --vs "top_l600==0 and step_up==1" --by class_move tempo_band`
Everything on Queensland Oct 2022 - Nov 2026 is now exploratory (the 2026 hold-out has been used). Fresh tests:
Queensland races from 25 Nov 2026 (`--since 2026-11-25`), and NSW/Vic from Breednet and Racing NSW form lines.

## Batch 1 (24 Nov 2026) - plan in batch01_plan.md (fixed before running; sha256 47db1aca...)
- `python3 rating_v0.py runs.parquet runs_rated_dev.parquet --fit-until=2024-12-31` (pars from pre-2025 races only)
- `inv13_b1_rating_baselines.py` (B1), `inv14_b2_r9_interactions.py` (B2), `inv15_b3b4_nsw_tests.py ../history/history.duckdb` (B3, B4 NSW),
  `inv16_b4_weight_qld.py` (B4 Qld), multiple-testing table `out/out_batch01_primary_fdr.csv`.
- `inv12_nsw_barriers.py ../history/history.duckdb` - independent NSW check of R1/R16.

## Batch 2 (24 Nov 2026) - plan in batch02_plan.md (fixed 15:39 before running; sha256 6a3370ec...)
`features.py runs_rated_dev.parquet ../history/history.duckdb features.parquet` -> `inv17_rating_variants.py`, `inv18_evidence_groups.py`,
`inv19_secondary.py`; `coverage_matrix.py ../history/history.duckdb out/coverage_matrix.csv`. Shared within-race tools: `clogit_tools.py`.
Study index: `library/studies.csv` and `library/README.md` (one card per study).

## Batch 3 (24 Nov 2026) - plan in batch03_plan.md (fixed 16:17 before running; sha256 b6b5442b...)
- Frozen benchmark: `benchmarks/combined_v1/` (manifest with file hashes, development coefficients, code copies).
- Study 6: `inv20_pace_figures.py ../history/history.duckdb`, `inv20b_pa1_vs_form.py` (pace-adjusted figures; writes pace_figures.parquet).
- Studies 7-9: `national.py <history.duckdb> [split]` (national run table, venue offsets, R20, common-feature replication, transfer;
  writes national_runs.parquet and out/out_nat_*.csv). Run after the Breednet backfill is loaded.
- Coverage: `coverage_matrix.py <db> out/coverage_matrix.csv` (completeness against all known races and starters from Oct 2022).
- Uncertainty: `clogit_tools.boot_diff(..., by='month')` adds calendar-month block intervals beside meeting intervals.

## Batch 4 (24 Nov 2026) - plan in batch04_plan.md (fixed 19:13 before running; sha256 b3ee70bd...)
- `hier_tools.py` - penalised within-race logit with an offset (partial pooling engine; Gaussian prior = L2 penalty).
- Study 10: `inv22_course_barriers.py` (P1-P5, freezes benchmarks/course_v1), `inv22b_course_barriers_checks.py` (exploratory checks),
  NSW replication `inv26_nsw_course_barriers.py ../history/history.duckdb`. Study 11: `inv24_lastcourse_sectional.py`.
- Study 12: `dyn_rating.py` (the rating), `inv23_dynamic_rating.py` (Qld), `inv27_fullorder_dyn.py` (top-3 check),
  `inv25_national_dynamic.py` (after `national.py`; national version).
- `freeze_b4_candidates.py` -> benchmarks/candidates_b4/manifest.json; `prospective/score_frozen.py ../history/history.duckdb`
  scores races from 25 Nov 2026 with the frozen candidates (never refits). `demo_ranked_reasons.py` - ranked runners with reasons (illustration).
- Breednet jump-outs (Vic, from May 2026) are flagged `bn_race.is_trial` and excluded everywhere.

## Batch 5 (24 Nov 2026) - plan in batch05_plan.md (sha256 2337c96d...)
- Pre-race: `../collectors/rq_pdf_helpers.js` + `../collectors/rq_prerace.js` (Racing Queensland fields, scratchings,
  conditions, rail; immutable snapshots), `prerace/score_prerace.py <snapshot> ../history/history.duckdb` (write-once
  predictions + append-only INDEX), `prerace/evaluate_prerace.py ../history/history.duckdb <runners files>` (append-only).
  `PRERACE_REPLAY=1` runs a retrospective replay with history cut at the race date (output to /tmp only).
- `freeze_b4_national.py` (candidates_b4_national), `freeze_b5_records.py` (candidates_b5).
- `inv28_dyn_verify.py` leak tests + identical races; `reconcile_breednet.py` Betfair vs Breednet causes;
  `inv29_course_conditions.py` Studies 13-15; `inv30_horse_suitability.py` Studies 16-17 (uses `dyn_rating_innov.py`);
  `inv31_selection_strength.py`.

## Batch 7 (25 Nov 2026): rating engine v2
- engine/lab.py builds the shared point-in-time national frame (rating, records, surprises, head-to-head, jockey/trainer, age/sex).
- engine/evaltools.py identical-race fitting/metrics; engine/ablation.py feature audit; engine/fast_rating.py + dyn_fast.py faster-learning rating test;
  engine/screen_nat.py discovery screen 2; engine/check_people_lag.py leakage guard; engine/v2.py cumulative / leave-one-out / rolling origin;
  engine/additivity.py non-additivity; engine/release_v2.py -> benchmarks/engine_v2/manifest.json (released model);
  engine/score_v2.py pre-race v2 scoring; engine/daily_ranking_v2.py daily report; engine/demo_rescore.py dynamic re-scoring demo.
- Outputs in engine/out/. Doc tab "Batch 7: rating engine v2"; register R50-R68.
