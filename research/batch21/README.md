# Batch 21 ledger (27 Nov 2026): horse identity, sustainable ability, physical performance (first part)

Brief: /mnt/user-data/uploads/0c1043df-attachment.txt (7:49pm). Point in time, market-free, no experimental production change.
Harness = /tmp/cand on production speed figures (sandbox history identical to production). Windows: A = judge 2024, B = judge 2025-26.
Report: https://claude.ai/artifact/E5PUAWm112r7pc68faiXc6

| Item | Script / code | Output |
|---|---|---|
| A1 Monday identity correction list (51 suffix splits, 5 sire/dam splits, 20 name variants kept as one horse, 3 flagged uncertain, BEREZKA R5 record) | b21_identity.py, inline list builder | identity_correction_monday.csv |
| A2 permanent identity: name + suffix + sire + dam, foaling season as a check; crosswalk keeps all source names and codes | b21_identity.py | identity_crosswalk_proposal.csv, out_b21_identity.json |
| A3 live identity resolution (TAB name + sire + dam, 26-27 Nov fields) and fallback | b21_identity.py | live_identity_check.csv, out_b21_identity.json |
| A4 materiality of the correction (rating moves, unaffected horses; Batch 20 race-level consequences) | inline | out_b21_identity_materiality.json |
| B5 experience file v3 (scratched-only Betfair rows dropped using RQ and NSW scratchings; parts kept: observed / inferred / verified / label) | b21_experience_file.py | /tmp/cand/experience_b21.parquet, out_b21_experience_file.json |
| B5 verification against TAB career starts (validation only) and NSW form-line careers | b21_experience_check.py, inline | out_b21_experience_check.json, out_b21_experience_check_nswform.json |
| B6 seven rating mechanisms (C2, CAP2, UR2, U5EC2, U5EH3, U5EA2, U5EH8) | harness chain34; b21_responsiveness_eval.py | out_b21_responsiveness_eval.json |
| B8 certainty weighting combined with the update-rule hook | dyn_rating_innov.py: RATING_REF now also applies inside the hook (before: plain mean, so the first PWH3/PWH8 runs did NOT combine; parity: REF off = U5EH3, 0.0); harness PWH3B, PWH8B | out_b21_responsiveness_eval_pw.json |
| C9-C10 trainer change and unfamiliar-distance breakthroughs | b21_breakthroughs.py | out_b21_breakthroughs.json |
| D11 pre-race rail sources | inline (TAB railPosition empty in 163 captured races; RQ/SA rail recorded with results); one Breednet check pending site approval | report section D |
| D12 barrier follow-ups (four pre-stated tests) | b21_barrier_followups.py | out_b21_barrier_followups.json |
| E13 sire debut record for first starters | b21_sire_debut.py; harness C2SD (sire_debut_x, tr_debut_x) | out_b21_sire_debut.json, out_b21_sire_debut_harness.json |

Production paths unchanged: every rating hook is off unless its environment variable is set; the frozen shadows run the hook without
RATING_REF, which is byte-for-byte the previous path (parity 0.0).
