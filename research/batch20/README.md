# Batch 20 ledger (27 Nov 2026): Queensland integrity, race layer, history completeness, barriers, trainer and family

Brief: /mnt/user-data/uploads/4a8fdd1e-attachment.txt (6:17pm). Point in time, market-free. No experimental production change.
Harness = /tmp/cand, now on production speed figures: the sandbox history file is production's national_runs_c2 (OFF2 and OFF3 vs the
released Engine v2.3 frame: max difference 0.0; Engine v2.3 harness rerun reproduces its earlier result exactly). The v2.2-credit sandbox
file is kept as /tmp/cand/national_runs_sandbox_v22credit_backup.parquet. Windows: A = judge 2024, B = judge 2025-26; both re-used.
Report: https://claude.ai/artifact/P4agrYWSvsCaJZViC3kv47

| Item | Script / code | Output |
|---|---|---|
| A1 Qld start-count discrepancy: cause and fix | ops/form_enrichment.py (scratched RQ rows no longer counted as starts); originals kept as collect/national/2026112[67]/*_before_b20_fix.csv, outputs/form_enrichment_ledger_before_b20_fix.csv | Qld held > TAB 55.2% -> 0.0%; others 3% -> 0.1%; rating frames never exceed TAB (0.0%) |
| A1 traced horses | inline (OSCAR, FACTNOT FICTION, PAPARACHA) | out_b20_qld_trace.json |
| A2 integrity audits, all jurisdictions | inline (bn_runner duplicates 567, scratched rows 0, RQ duplicate race ids 0, starter dups 2, BEREZKA frame dup 1) | report section A |
| A2-A3 name-key collisions | b20_name_collisions.py (review list); sandbox split of 51 country suffixes in /tmp/nk (national.py _nk2, never production) | out_b20_name_collisions.json, name_collision_review.csv, out_b20_name_collision_sandbox.json |
| B4 history-completeness candidate (research form) | b20_experience_file.py (v2: Betfair runner list dates + held runs; labels verified / complete / late_maiden / probable_incomplete); dyn_rating hook RATING_TAPER_NEFF (off by default); harness U5EH2 vs U5EC2 (parity: NEFF all-missing = U5EC2, 0.0) | out_b20_experience_file.json; report section B |
| B5 supported vs unsupported big runs | b20_supported.py (exec's batch18/b18_sustainability.py unchanged) | out_b20_supported.json |
| C6-C8 race layer vs individual accuracy (six measures); PW on production figures | b20_race_layer_feats.py (rel_x_light, rel_x_osd, rel_x_fsd), harness C2RL / U5EA2RL, b20_race_layer_eval.py; PW2; b20 PW inexperienced-field check (inline) | out_b20_race_layer_eval.json, out_b20_pw_inexperienced_check.json |
| D9 pooled barrier expectation | b20_barrier_feature.py (point in time; NORAIL=1 rail-free); b20_qld_barrier.py (Qld: replace 3R / add 3A); harness C2B, C2BN (SA) | out_b20_barrier_feature*.json, out_b20_barrier_tests.json, out_b20_barrier_breakdown.json |
| D11 form-record barrier coverage | inline (TAB past starts 0.2% usable; NSW form lines survivor-only) | report section D |
| E12 SA ground fields | inline (sa_starter.ground_rel_winner_m supplied; sa_sectional.ground_m empty; 2026 files absolute ground_m) | report section E |
| F13 trainer early improvement | b20_trainer_early.py; harness C2TE (tr_early_x) | out_b20_trainer_early.json, out_b20_trainer_firstup_harness.json |
| F14-F15 family after trainer controls; breeding x trainer | b20_family_trainer.py (exec's batch19/b19_family.py set-up) | out_b20_family_trainer.json |
| G16 first-up evidence | b20_firstup.py; harness C2FU (fu_own) | out_b20_firstup.json, out_b20_trainer_firstup_harness.json |
| H17 emergency reconciliation | ops/check_emergencies.py (morning eligibility vs eventual participation; races with pre-cutoff vs later scratchings); dashboard lists emergencies included by inference, labelled not official (engine/export_ui.py, ui/index.html) | outputs/emergency_check_<D>.json |

Production paths unchanged: all rating hooks off unless their environment variable is set; dashboard export with the new field verified on
27 Nov (only the new, empty field differs); the national emergency rule switch stays off until tonight's checks.
