# Batch 17 ledger (27 Nov 2026): sustainability, breeding, track bias, development

Brief: /mnt/user-data/uploads/75ddca15-attachment.txt (1:16pm). Point in time, market-free. Harness = /tmp/cand (Engine v2.3 structure
refitted; A = judge 2024, B = judge 2025-26, re-used).

| Item | Script / code | Output |
|---|---|---|
| Qld common framework shadows (configs 2, 4) | ops/qld_common_adapter.py, ops/run_qld_common_shadow.sh, sandbox release chain (QCF=1) | out_b17_qld_built_check.json, out_b17_qld_shadow_integrity_20261127.json, batch16/out_b11_qld_configs.json (national_rating_variants, physical_inputs_interaction) |
| First-starter age/sex | engine/score_v2.py AGESEX_TAB (off); harness SERVE_MISSING_FIRST | out_b17_first_starter_agesex.json |
| Heavy-defeat mechanism | dyn_rating RATING_CAP_SCOPE=reference (off); harness RF vs U1B vs U1 | register row |
| Exceptional positive runs | b17_positive_outliers.py; dyn_rating_innov RATING_GOOD_TAPER (off); harness U5E | out_b17_positive_outliers.json, _tapered.json |
| Track bias (Qld) | b17_track_bias.py, b17_bias_next_run.py | out_b17_track_bias.json, out_b17_bias_next_run.json, out_b17_data_coverage.json |
| Breeding | b17_breeding.py | out_b17_breeding.json |
| Presentation scale | b17_presentation_scale.py | out_b17_presentation_scale.json |
| Race uncertainty vs confidence | (inline) | out_b17_race_uncertainty_confidence.json |
| Dashboard | engine/export_ui.py (profile), ui/index.html (profBox, vSim) | artifact version 1795751544-7179 |
