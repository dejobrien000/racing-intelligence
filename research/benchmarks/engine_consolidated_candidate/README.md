# Consolidated rating candidate (NOT LIVE - shadow only)

Engine v2.3 rebuilt in full through its own release chain with the strongest historical individual-rating configuration:
- heavy-defeat cap: a defeat counts at most 12 lengths in the performance figure (recorded margins are never changed);
- stronger experience-dependent response: a run better than expected moves the rating m = 1 + 0.8 exp(-n/6) times as far;
- n = history-completeness experience (batch23/b23_experience_file.py v4): verified TAB as-at career starts where held, else observed
  starts (Betfair runner-list dates and our history), plus inferred starts for probably-incomplete careers, limited by the approved cap
  (75th percentile of starts by age among complete-history horses: 2, 6, 13, 21, 27, 33 at 2-7yo+); observed and verified never reduced;
- certainty-weighted race reference (RATING_REF=precision), applied inside the update rule (verified 27 Nov).

All three layers are its own: candidates_national_common.json, engine_v2.json (NSW/VIC/ACT/SA/WA/TAS family), engine_v2_2.json.
Scored every morning from the 28 Nov 2026 run by `UR_VARIANT=consolidated ops/run_update_shadow.sh` into prospective/shadow/consolidated/
(own index, own prospective clock), after publishing. Never the dashboard, the ranking or the settlement. Promotion is a separate decision.
Built 2026-11-27T12:34:44+00:00. Fingerprints in each file's candidate_record.
