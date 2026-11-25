# Preregistration: today's weight in handicaps (Batch 12, s3 handicap residual) — written 25 Nov 2026 before running

Observation that prompted it (2025-26, already seen, so NOT valid evidence for this hypothesis):
under production v2.2 (dev-fit), benchmark-handicap runners carrying 3 kg+ less than the field mean win 1.61x expected
(1.47-1.75), 3 kg+ more 0.82x. The weight release candidate (C2: 0.25 credit + 0.170 s/L) barely changes it (1.50 / 0.83).
Maidens show nothing (0.96 / 1.01). The engine fits one slope for today's weight across all races; in set-weight races
weight differences come from claims and allowances, in handicaps from the handicapper's assessment.

Hypothesis: a separate slope for today's weight vs field in handicaps improves the engine.

Term (fixed now): wt_x_hcp = a_wt_rel x [class_label in {Benchmark, BM, Open/Hcp}], added to the v2.2 layer (ridge 30, as the
other v2.2 terms), every other layer as in cand_eval.py mode R. Secondary (reported, not decisive): wt_x_nonmaiden =
a_wt_rel x [class_label != Maiden].

Primary test: discovery window A (fit before 2024, judged on 2024), on both the production rating (B0) and the weight
candidate (C2): per-race log-likelihood gain over the same variant without the term, 95% race-bootstrap interval excluding 0,
and a negative coefficient (heavier = worse). 2025-26 (window B) is reported but is not independent evidence (seen).
Prospective evidence = races from 26 Nov 2026 only. Not a production change: any release is a separate decision.
No market data.
