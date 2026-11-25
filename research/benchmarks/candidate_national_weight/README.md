# National weight release candidate — NOT LIVE

Built 25 Nov 2026 (Batch 12 s3). Research record only: no production script reads this folder. Any release is a separate decision.

## What it is
- C2: the national dynamic rating rebuilt with a weight credit of 0.25 kg per kg for each past run (production: 1.0), and figures
  using 0.170 s per length (production: about 0.143). Every rating-derived input (figures, v2.2 inputs, jockey/trainer features,
  head-to-head, venue levels) rebuilt from that rating; every layer refitted (v1 conditional logit, v2 terms, v2.2 terms).
- C2 + handicap weight: the same plus one preregistered term, today's weight vs field in handicaps
  (preregistered/2026-11-25_b12_weight_handicap.md).
- Coefficients: fitted on races before 2025 (the convention of the production dev-fit manifests): coef_C2.json, coef_C2_hcp.json.

## Evidence (per-race log-likelihood gain, 95% race-bootstrap interval; research/batch12/candidate_weight/out_compare.csv)
| Comparison | 2024 (fit before 2024) | 2025-26 (fit before 2025) |
|---|---|---|
| C2 vs production v2.2 as it runs (dev-fit coefficients) | +0.0029 (+0.0002 to +0.0054)* | +0.0107 (+0.0089 to +0.0124), top pick +0.56 pts |
| C2 vs the same engine refitted on the production rating | +0.0105 (+0.0084 to +0.0127) | +0.0084 (+0.0068 to +0.0101) |
| credit only (W025) vs refitted production | +0.0097 | +0.0079 |
| 0.170 s/L only (S1) vs refitted production | +0.0004 (+0.0001 to +0.0007) | +0.0003 (+0.0000 to +0.0005) |
| handicap term on top of C2 (preregistered primary = 2024) | +0.0012 (+0.0008 to +0.0017) | +0.0014 (+0.0011 to +0.0018)** |
| C2 + handicap term vs production v2.2 as it runs | +0.0042 (+0.0015 to +0.0069)* | +0.0121 (+0.0103 to +0.0140) |

\* production's dev-fit coefficients were fitted on data that includes 2024, so 2024 flatters production.
\** 2025-26 had already been looked at for the handicap residual: not independent evidence.

## Known limits
- Raw chances are over-confident like production's raw chances (top picks win 0.93 of expected): the calibration layer must be refitted
  before shadow scoring (same method as production).
- The handicap term removes only part of the handicap residual (3 kg+ under the field: 1.61 -> 1.36 of expected).
- 2025-26 has been examined repeatedly; the first untouched evidence will be shadow scoring from its start date.
- Queensland is unaffected (separate engine, allocated weight; carried weight was rejected there).

## Reproducibility
Clean sandbox = repository code + production database (/tmp/cand, scripts in research/batch12/candidate_weight). Baseline B0 reproduces
the production national frame and the production Queensland frame exactly (682,430 rows, all 105 columns identical); reruns reproduce
every figure above exactly.

## Before any shadow scoring
1. Move the two sandbox hooks into production code as configuration, default off (SPL_FIXED in national.py, WCREDIT in dyn_rating.py).
2. Weekly job builds the candidate frame alongside production (never replacing it); failure is non-fatal.
3. Daily: score the candidate after publishing into prospective/shadow/national_weight/ (write-once, own INDEX), as for Qld v2.1.2.
4. Refit the calibration layer; replay a past day and confirm the production output is byte-identical with the candidate switched on.
