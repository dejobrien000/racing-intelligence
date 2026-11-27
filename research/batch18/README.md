# Batch 18 ledger (27 Nov 2026): corrections, scratchings, experience, sustainability, lane bias, trainer debuts

Brief: /mnt/user-data/uploads/40957522-attachment.txt (2:23pm). Point in time, market-free. Harness = /tmp/cand (Engine v2.3 structure
refitted; A = judge 2024, B = judge 2025-26, both re-used: neither is an untouched validation sample). Qld harness = batch16/b11_qld_configs.py.
Report: https://claude.ai/artifact/UHk9gNXhht3HV3DVa8roVf

| Item | Script / code | Output |
|---|---|---|
| A1-A3 production corrections (effective 28 Nov 7:30am) | engine/score_v2.py corr_on (AGESEX_TAB, METRO_FROM_TIER, QLD_COURSE_MAP), prerace/qld_courses.py, prerace/score_prerace.py, ops/first_starter_todo.py, DAILY_RUN step 3b; switch files ops/agesex_tab_enabled, ops/metro_tier_enabled, ops/qld_course_map_enabled | benchmarks/engine_v2/RELEASES.md (replays, rollback) |
| A4 dashboard common scale | engine/export_ui.py (PROFILE, SCALE), ui/index.html profBox | dashboard version 1795755049-00a9 |
| B scratchings / emergencies | engine/export_ui.py mkt(), collect/tab_prices.py; ops/evaluate_prospective.py (starters_actual, field_complete), engine/engine_performance.py _paired | ops/logs/20261127.md |
| C Qld shadow integrity | ops/qld_common_adapter.py (Qld production emergency rule); scratch re-run /tmp/qcs_test | out_b18_qld_shadow_integrity_20261127_after_fix.json |
| D3 sustainability | b18_sustainability.py | out_b18_sustainability.json |
| D2 experience split | b18_experience_split.py [VA VB] | out_b18_experience_split.json, _U5EA_vs_U5.json, _U5EC_vs_U5.json |
| D2/D4 age floor (U5EA, pre-stated prediction), decomposition (U5EC, diagnostic) | dyn_rating.py / dyn_rating_innov.py RATING_TAPER_AGEFLOOR (off) | out_b18_harness.json |
| D5 race-level-only cap (RO) | dyn_rating_innov RATING_CAP_SCOPE=reference_others (off) | out_b18_harness.json |
| A5 lane candidate (LN share 0.167 pre-2024; LN2 share 0.383 on 2024) and SA replication | b18_lane_candidate.py (LANE_CAL), dyn_rating RATING_PERF_ADJ (off), b18_sa_lane.py | out_b18_lane_candidate*.json, out_b18_lane_qld_harness.json, out_b18_lane_qld_same_day_by_period.json, out_b18_sa_lane.json |
| A5 SA lane candidate (share 0.51 set on 2024 SA meetings; 2025-26 judged cleanly) | b18_sa_lane.py (SA_LANE_OUT) | out_b18_sa_lane_candidate.json, out_b18_sa_lane_harness.json |
| Harness baseline check (hooks-off sandbox frame OFF vs production frame C2) | /tmp/qcfg/chain22.sh | out_b18_harness.json (baseline_note, OFF_vs_C2, vs_hooks_off) |
| E6 trainer debut record; selectivity proxy; E4 maturity with continuation | b18_debut_selectivity.py, b18_trainer_debut_feature.py (harness EXTRA=tr_debut) | out_b18_debut_selectivity.json, out_b18_harness.json |

All rating hooks are off unless their environment variable is set; production code paths unchanged (verified identical when off).

Baseline: hook variants share the sandbox's speed-figure tables, which differ slightly from production; compare them with OFF (hooks-off sandbox), not C2. OFF vs C2 = -0.0009 (2024) / -0.0002 (2025-26).
