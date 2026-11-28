# Preregistration - Batch 27 distance candidate and compatible combinations (written 28 Nov 2026 ~2:40pm Brisbane, before any run below)

Status of the evidence: windows A (fit before 2024, judged 2024) and B (fit before 2025, judged 2025-26) have both been examined in
earlier batches, including Batch 26's exploratory distance tests (replacement +0.0005 / +0.0002). They are research evidence, not
untouched validation. Only races from 26 Nov 2026 onward are prospective. Nothing below is tuned after seeing its own result.

## 1. Distance measure (fixed, from batch26/b26_distance.py; not re-tuned)
dspec = kernel-weighted (Gaussian on log distance, h = 0.12) shrunk mean (k = 3) of the horse's earlier surprises near today's trip,
minus the horse's general shrunk mean surprise scaled by the same evidence. Computed from each engine's OWN rating surprises
(v2.3 frame for v2.3, consolidated frame for consolidated). Point in time (earlier runs only).

Neighbourhood: decided on runs BEFORE 2024 only (no outcome window): estimate, separately for sprints (<=1200 m), middle (1201-1800 m)
and staying (1801 m+), how fast the within-horse correlation of surprises falls with the log-distance gap. Rule fixed now: if the
distance gap at which the correlation halves differs by more than 50% between ranges, use range-specific bandwidths equal to
h x (range half-gap / pooled half-gap); otherwise keep h = 0.12. Whichever results is run ONCE.

## 2. Primary comparisons (national harness, refit mode R; paired per-race log-likelihood, 95% bootstrap; windows A and B)
D1 Engine v2.3: distance record d_rec REPLACED by dspec            vs v2.3 unchanged
D2 Consolidated: d_rec replaced by dspec (consolidated surprises)  vs consolidated unchanged
D3 Qld common framework (config 2 research harness): d_rec replaced vs config 2 unchanged
Secondary (individual accuracy, reported separately): mean squared error of field-relative performance (Batch 20-21 common target)
predicted by field-relative rating + b x dspec (b fitted on 2023 runs), judged on 2024 and 2025-26, vs rating alone.
Secondary (physical, Qld/SA tracked runners only; untracked = 0, no missing penalty): add speed-retention prior x step-up indicator and
x step-down indicator to D2; report the incremental gain overall and in races with half or more tracked runners.

## 3. Compatible combinations (sequential ladder, each step vs the previous step AND vs the unchanged Engine v2.3 baseline)
L0 Engine v2.3 (unchanged baseline, harness P26)
L1 + consolidated rating (K26)
L2 + handicap weight slope (wt_x_hcp, the frozen Engine v2.4 term)
L3 + distance replacement (D2's change)
L4 + trainer debut term, + sire debut term (if their pre-race features can be served identically; otherwise reported as not tested)
L5 + 365-day+ returner term (designed in Batch 27 P4 on runs before 2024 only)
Controlled ablations from the full ladder: remove each component one at a time.

## Decision rules (fixed now)
- A component goes forward only if its gain is >= 0 in BOTH windows and its lower 95% bound is above -0.0005 in both.
- A combined candidate is called "ready for production consideration" only if every component passes, the full combination beats
  L1 in both windows, and the serving definitions can be reproduced from morning data; otherwise "ready for prospective research"
  or "promising but incomplete".
- No component is chosen because of 28 Nov results.
