# Prospective evaluation (protected)
Frozen candidates: benchmarks/candidates_b4/manifest.json (frozen 2026-11-24T09:28:58.462686+00:00 UTC) and benchmarks/course_v1/manifest.json.
Rule: only races dated 25 Nov 2026 or later count. Models are never refitted on these races. Each scoring run writes
prospective/scores_YYYYMMDD.csv with a UTC timestamp and the manifest hash it used.
Limitation today: we collect results, not acceptances, so scores are computed after the race from features built only
from earlier runs (point-in-time by construction). Saving true pre-race predictions needs a Qld acceptances collector
(next-sequence item), which also guards against late data revisions.
