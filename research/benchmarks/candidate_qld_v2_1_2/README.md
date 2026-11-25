# Engine v2.1.2-candidate (Queensland) — NOT LIVE

Approved for testing by Damo 25 Nov 2026 ("prepare a release candidate and document the evidence and limitations"). Production
stays Engine v2.1.1. Going live needs Damo's decision.

What it is: Engine v2.1.1 refitted without (a) last-start finish and (b) the 10 track/distance/going history inputs (track starts and
wins, distance-band starts and wins, track-and-distance starts and wins, going, distance change, absolute distance change, missing going).
Same fitting rule as v2.1.1. Removed inputs carry coefficient 0 so the existing Queensland scorers run it unchanged.
Files: candidates_manifest.json (replaces benchmarks/candidates_b4_national_v3/manifest.json), engine_manifest.json (replaces
benchmarks/engine_v2_1/manifest.json). Built by batch11/build_qld_candidate.py; tested by batch11/qld_simplify_v211.py.

Evidence (actual Queensland tracked races; log-likelihood per race vs v2.1.1, meeting-bootstrap 95% interval):
| Window | Races | Log-lik gain | Top pick (pts) | Winner in top 3 (pts) |
|---|---|---|---|---|
| B: fit before 2025, judge 2025-26 | 4,730 | +0.0061 (+0.0025 to +0.0096) | -0.34 (-1.00 to +0.30) | +0.61 |
| B, 2026 only | | +0.0039 (-0.0011 to +0.0084) | | |
| A: fit before 2024, judge 2024 | 2,409 | +0.0012 (-0.0038 to +0.0060) | -0.58 (-1.45 to +0.33) | -0.71 |
Single removals in window B: track history +0.0047 (+0.0014 to +0.0080); last-start finish +0.0014 (+0.0002 to +0.0024);
closing sectionals +0.0003 (-0.0016 to +0.0025, redundant - kept in the candidate).

Limitations: window B (2025-26) has been examined many times; the earlier window does not confirm it clearly; top-pick accuracy does
not improve (slightly lower in both windows, within noise); gains are in probability calibration, not picking winners. Recommended:
score it in shadow from the 26 Nov run alongside v2.1.1 and decide on prospective races only.
