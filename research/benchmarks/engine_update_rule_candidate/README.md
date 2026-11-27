# Rating update rule candidate (NOT LIVE — shadow only)

Engine v2.3 rebuilt in full with one change to how a run moves a horse's rating:
- a defeat counts at most **12 lengths** in the performance figure (the margin in the data is never changed);
- a run **better than expected** moves the rating **1.3 times** as far.

All three layers are its own: `candidates_national_common.json` (first layer), `engine_v2.json` (second layer, NSW/VIC/ACT/SA/WA/TAS
family; penalty chosen by the release script = 10), `engine_v2_2.json` (third layer). kg scale 0.315 model units per kg (Engine v2.3:
0.269) — a different scale, not a change in any horse's ability.

Scored every morning by `ops/run_update_shadow.sh` into `prospective/shadow/update_rule/` (own index), after publishing. Never the
dashboard, the ranking or the settlement. Approved as a shadow by Damo, 27 Nov 2026 (Batch 16 brief s9). Promotion is a separate decision
after final checks and prospective evidence.
