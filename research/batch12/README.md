# Batch 12 ledger (25 Nov 2026): physical performance, early change, weight release candidate

Research only. Production for 26 Nov is as approved in Batch 11 (v2.2 national with weight carried, v2.1.1 Qld, v2.1.2 shadow).
No market data in any script. 2025-26 has been examined repeatedly: every lead is a hypothesis; first untouched evidence =
races from 26 Nov 2026. Additive tests use the Batch 10 harness on top of Engine v2.2 (discovery: fit before 2024, judged on
2024; validation: fit before 2025, judged on 2025-26). Queensland tests sit on top of the Queensland engine.

| Script | Brief section | Output | Result in one line |
|---|---|---|---|
| sect_build.py | s5/s6 data | sect_runs.parquet (not committed) | 91,179 Qld tracked runs; 200 m splits, speed, stride, ground, all relative to the race median |
| s5_late.py | s5 early deterioration | out_s5_late.csv, out_s5_late_periods.csv | weak late retention -> +0.52 kg bounce next start (stable both periods); within 1.0 L -> -0.56 (2025-26 interval includes 0) |
| s6_stride.py | s6 stride | out_s6_stride.csv | stride is a horse trait (r 0.51-0.53); same speed with shorter, quicker strides -> -0.43 kg next start; 2026 stride-length shift looks like measurement |
| (in s5_late.py) | s4 physical inputs (Qld) | out_s4_qld_physical_terms.csv | ground covered: discovery +0.0028, validation +0.0002; retention / final-200 speed rejected as added inputs |
| s8_distance.py | s8 distance suitability, s9 preparation stage | out_s8_distance.csv, out_s9_prep_surprise.csv | continuous profile hurts (-0.0026); preparation stage doesn't explain it |
| s10_prep_rel.py | s10 preparation-relative improvement | out_s10_prep_rel.csv | persistence r 0.19; no gain as an input |
| s11_peaks.py | s11 ceiling/decline, s12 peak vs typical | out_s11_peaks.csv, out_s12_consistency.csv | no feature improves v2.2; consistent horses A/E 0.95 vs erratic 1.05 |
| s13_conversion.py | s13 perennial placegetters | out_s13_conversion.csv, out_s13_bands.csv | no persistence (1.00 vs 1.01); rejected |
| s14_opposition.py | s14 opposition composition | out_s14_opposition.csv | nothing beyond the race-relative calculation; rejected |

Measured time vs margins in Queensland (s4, command in the session on sect_runs.parquet): beaten runners whose official margin x 0.17 s
matches their measured gap to within 0.1 s: 2023 85%, 2024 86%, 2025 96%, 2026 99.6%. From 2025 the Qld margin rating is a
measured-time rating.

Evidence shares (s4, how the Batch 11 percentages were calculated): batch11/followup/s11_decomp_nat.py and decomp_qld.py.
Share = cov(family contribution, total score) / var(total), each contribution taken relative to its race mean, 2025-26 races,
dev-fit coefficients. Shares of the score, not of accuracy.

## s3 weight release candidate: candidate_weight/
Clean sandbox (/tmp/cand) = repository code + the production database. Baseline B0 reproduces the production national frame.
Sandbox-only hooks (diffs here): SPL_FIXED in national.py (figures' seconds per length), WCREDIT in dyn_rating.py (history weight credit).
- build.sh: national.py + engine/lab.py per variant: B0 (production), C2 (0.25 credit + 0.170 s/L), W025 (credit only), S1 (s/L only).
- run_eval.sh: Batch 10 feat10 (v2.2 inputs) per variant, then cand_eval.py.
- cand_eval.py modes: P = actual production v2.2 coefficients (B0 only); R = every layer refitted; R-noW = refitted without today's weight inputs.
- ev.sh / rest.sh / run_hcp.sh: one variant and mode per process (8 GB workspace; float32, unused columns dropped; like-for-like).
- compare.py -> out_compare.csv, out_levels.csv; hcp_resid.py -> out_hcp_resid.csv; calibration table -> out_calibration.csv.
- qld_frames.sh: Queensland v3 frames from the clean sandbox; B0 reproduces production national_v3 exactly (682,430 rows, 105 columns).

Results (per-race log-likelihood gain; full table out_compare.csv):
- C2 vs production v2.2 as it runs: 2025-26 +0.0107 (+0.0089 to +0.0124), top pick +0.56 pts.
- C2 vs refitted production: 2024 +0.0105, 2025-26 +0.0084. Credit alone +0.0097 / +0.0079; 0.170 s/L alone +0.0004 / +0.0003.
- Today's weight inputs: add +0.0018 / +0.0027 on the production rating, nothing on C2 (-0.0010 / -0.0001).
- Handicap residual (2025-26, 3 kg+ under the field in benchmark handicaps): 1.61 production, 1.50 C2, 1.36 C2 + handicap term.
- Handicap term (preregistered): 2024 +0.0012 (+0.0008 to +0.0017), coefficient negative in both windows: primary test passed.
- Frozen record: benchmarks/candidate_national_weight/ (NOT LIVE).
