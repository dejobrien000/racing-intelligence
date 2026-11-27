# Batch 19 ledger (27 Nov 2026): emergencies, age-aware and trainer debut shadows, age vs experience, barriers

Brief: /mnt/user-data/uploads/4fccd510-attachment.txt (4:11pm). Point in time, market-free. Harness = /tmp/cand (Engine v2.3 structure
refitted; A = judge 2024, B = judge 2025-26, both re-used: neither is untouched). Baseline for sandbox variants = OFF (hooks-off sandbox
frame), never the released frame (BASELINE_CORRECTION.md). Report: https://claude.ai/artifact/Ltm6Q4hqN29FCehH9YzaBa

| Item | Script / code | Output |
|---|---|---|
| A1 national emergency gained-start rule | collect/national/build_snapshot.py (EMRULE; switch ops/national_emergency_enabled; env NAT_EMERGENCY_RULE), prerace/score_national_prerace.py (records rule + admitted emergencies), ops/check_emergencies.py | outputs/emergency_check_<date>.json/.csv |
| A2 age-aware update rule shadow | release chain in /tmp/ua (sandbox guard relaxed for the taper); benchmarks/engine_age_aware_candidate; ops/run_update_shadow.sh UR_VARIANT=ageaware; ops/run_shadow.sh (from 29 Nov); ops/evaluate_prospective.py NSX | log_a2_parity.txt |
| A3 trainer debut record shadow | b19_trainer_debut_checks.py; harness EXTRA=tr_debut_g; release build in /tmp/td (third-layer parity 0.0); benchmarks/engine_trainer_debut_candidate; engine/v22.py trainer_debut() (only when a manifest lists the term); ops/run_trainer_debut_shadow.sh (from 29 Nov) | out_b19_trainer_debut_checks.json, out_b19_trainer_debut_built_check.json, log_a3_build.txt |
| A4 lane: extra ground and tempo; lane candidates | b19_lane_controls.py; b19_lane_candidate.py (writes /tmp/cand/lane_adj_b19.parquet); harness LN19 (national + Qld) | out_b19_lane_controls.json, out_b19_lane_candidate.json, out_b19_lane_harness.json |
| B5 sustainability extended | b19_sustainability_ext.py (exec's batch18/b18_sustainability.py unchanged) | out_b19_sustainability_ext.json |
| B6 age vs experience; threshold sensitivity; completeness floor | b19_age_vs_experience.py; dyn_rating_innov RATING_TAPER_AGEMIN (sensitivity only; default 5); harness U5EC4, U5EC6, U5EH (pre-stated prediction) | out_b19_age_vs_experience.json, out_b19_age_threshold.json, out_b19_career_starts_check.json |
| B8 individual vs race accuracy | b19_individual_accuracy.py (+ maiden breakdown inline) | out_b19_individual_accuracy.json, out_b19_individual_vs_race_maidens.json |
| C9 sire maturity out of cohort | b19_sire_maturity.py | out_b19_sire_maturity.json |
| C10 dam / siblings / damsire | b19_family.py | out_b19_family.json |
| C11 trainer development patterns | b19_trainer_development.py | out_b19_trainer_development.json |
| D13-D16 barrier hierarchy and stability | b19_barrier_hierarchy.py | out_b19_barrier_hierarchy.json |
| E17 spacing and preparation preferences | b19_spacing_preferences.py | out_b19_spacing_preferences.json |
| G24 baseline correction | BASELINE_CORRECTION.md | out_b19_baseline_correction.json |

All rating hooks remain off unless their environment variable is set; production paths unchanged (27 Nov national replay reproduces
production exactly with the new code; evaluation and export steps run cleanly on copies).
