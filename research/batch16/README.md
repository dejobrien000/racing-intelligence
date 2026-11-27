# Batch 16 ledger (27 Nov 2026): rating foundations, national comparability, individual horse intelligence

Brief: /mnt/user-data/uploads/c626a212-attachment.txt (10:06am). Report: https://claude.ai/artifact/86wkTBtGJXB6Sx1Fpj416x.
All research is point in time and market-free. Engine tests: /tmp/cand harness (Engine v2.3 structure refitted; A = fit < 2024,
judge 2024; B = fit < 2025, judge 2025-26, re-used). Results: out_engine_tests.json unless named.

| Item | Script | Output | Result |
|---|---|---|---|
| A2 settings record + correction | a2_verify_settings.py | prospective/prerace/20261127/settings_verification_20261127.json | fixed; replay 561 scores |
| A2 first-layer history fingerprint | (scorer fix) | prospective/prerace/20261127/v1_history_file_correction_20261127.json | fixed; replay identical |
| B7 v2.4 checks | b7_v24_checks.py | out_b7_v24_checks.json | class parity waits for Monday |
| B8 train/serve audit | b8_train_serve.py | out_b8_train_serve.json | age/sex for first starters served missing |
| B8 bm_change | harness SERVE_MISSING / DROP | out_engine_tests.json | keep as a training-only control |
| B9 rule checks | b9_update_checks.py | out_b9_update_checks.json | rule halves known biases; no prop-up of decliners |
| B9 built check | b9_built_check.py | out_b9_built_check*.json | +0.0059 (rule), +0.0043 (cap only) vs v2.3 as built |
| B10 s per length | b10_margins.py | out_b10_margins.json | Qld 0.170, SA 0.1595, Vic 0.162 (empirical) |
| B10 interstate | b10_interstate.py | out_b10_interstate.json | offsets not a margin-unit effect |
| B10 standardised margins / state-pair term | harness STD, C2X | out_engine_tests.json | worse / no gain: no state corrections |
| B11 Qld configurations | b11_build_v3.py, b11_qld_configs.py, b11_qld_compare.py | out_b11_qld_configs.json | common + rule +0.0314 / +0.0204 vs v2.1.3 |
| C13/C14/C16 | c13_14_16.py | out_c13_14_16.json, out_c13_14_16_update_rule.json | heavy defeat flatters field -0.58 (rule: -0.25) |
| C13 race reference | harness PW, U5PW | out_engine_tests.json | +0.0005 / +0.0004 on top of the rule |
| C15 distance | c15_distance.py + harness C2S+suit | out_c15_distance.json | real, redundant in the engine |
| C17 trainer change | c17_trainer_change.py | out_c17_trainer_change.json | trainer-specific uplift persists (r 0.58) |
| C18 geometry | c18_geometry.py, course_geometry.csv | out_c18_geometry.json | rejected (sign flips) |

Shadows wired (not live, from the 28 Nov run): ops/run_update_shadow.sh (update rule; UR_VARIANT=caponly for the comparator), files in
benchmarks/engine_update_rule_candidate and benchmarks/engine_cap_only_candidate. Sandbox-only change for the build: the
inv30_horse_suitability.py equality guard skipped when RATING_GOOD_X is set (repo unchanged). New research hooks, off by default and
verified identical when off: RATING_CAP_L / RATING_CAP_SCOPE / RATING_GOOD_X (dyn_rating, dyn_rating_innov, engine/dyn_v3), RATING_REF.
