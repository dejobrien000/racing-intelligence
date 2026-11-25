# Research library (permanent)

One line per hypothesis, newest first within each section. Evidence lives in the batch ledgers named. "Rejected" items stay
here so they are not re-tested without materially different evidence. Market data never enters any rating input.

## In production
| Since | What | Evidence | Ledger |
|---|---|---|---|
| 26 Nov 2026 | Weight carried (allocated minus apprentice claim) for the national model; Qld unchanged (consistent allocated) | Definition match with history; replay 1 top pick in 37 races | benchmarks/engine_v2/RELEASES.md |
| 26 Nov 2026 | Engine v2.2: 14 terms (career shape and consistency, light weight, quick backup, measured venue class) | Validation +0.0125 log-lik per race (0.0105-0.0145) | batch10/ |
| 26 Nov 2026 | Engine v2.1.1 (Qld): v2.1 refitted on the database with Breednet Qld country meetings | +0.0121 vs v2.1 on 2025-26 | batch10/v211/ |

## Candidates (not live)
| Since | What | Status | Ledger |
|---|---|---|---|
| 25 Nov 2026 | National rating rebuilt with weight credit 0.25 kg per kg (history) and 0.170 s per length (figures) | Preregistered tests passed: +0.0079 log-lik per race on 2025-26 (0.0062-0.0094), +0.0089 on 2024, top pick +0.2 pts; needs v2.2 terms rebuilt, coefficients refitted and shadow scoring before any release | batch11/followup/, preregistered/2026-11-25_b11_spl_weight.md |
| 25 Nov 2026 | Qld v2.1.2: drop last-start finish and track/distance/going history | Shadow-scored from 26 Nov; decide on prospective races only (2024 window weak, top-pick rate not better) | benchmarks/candidate_qld_v2_1_2/, batch11/ |

## Open hypotheses (judged only on races from 26 Nov 2026)
| Raised | Hypothesis | Evidence so far (2025-26, re-used period) | Ledger |
|---|---|---|---|
| 25 Nov 2026 | Horses after an ordinary debut (within 3 kg of expected) are overrated | actual/expected 0.75-0.80 under v2.2 | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | First starters the engine ranks 1st-3rd are underrated | 1.21-1.27 | batch11/out_lightly_raced.csv |
| 25 Nov 2026 | Lightly raced (1-3 runs) last-start winners rating in the top third are underrated | 1.19 (1.07-1.33), 699 runners | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | Vic horses on a first Tasmanian start beat their rating (rating connection, not a bonus) | 1.85 first start, 1.00 repeat; Tas->Vic 0.63 | batch11/out_vic_tas.csv |
| 25 Nov 2026 | Light weights in handicaps beat their rating (weight credit / today's weight under-used) | 1.32 (1.22-1.43) after v2.2 | batch11/out_light_weight_v22.csv |
| 25 Nov 2026 | Today's weight vs field is under-used (light weights in handicaps beat their rating) | Explained by the weight mechanics: superseded by the weight-credit candidate above | batch11/followup/out_weight_vs_field.csv |
| 25 Nov 2026 | Interstate pools are mis-connected (Tas ratings ~2.3 kg high vs Vic; SA ~0.9; Qld ~0.5-1.2) | Every-runner surprises, selection-adjusted; fix = pool levels inside the rating | batch11/followup/out_connections.csv |

## Rejected
| Date | Hypothesis | Why rejected | Ledger |
|---|---|---|---|
| 25 Nov 2026 | Weight carried (claim deducted) in the Queensland model's history | Like-for-like rebuild: 2025-26 +0.0002 (-0.0035 to +0.0039), 2024 -0.0048 (-0.0100 to +0.0011): no gain; Qld keeps allocated weight in history and production (consistent) | batch11/followup/qld_carried_vs_allocated.csv |
| 25 Nov 2026 | No weight credit at all (0 kg per kg) | Not better than 0.5 (+0.0000) and worse than 0.25 | batch11/followup/out_prereg_spl_weight.csv |
| 25 Nov 2026 | Trainer-specific quick-backup bonuses (each trainer's backups vs that trainer's ordinary runners) | 557 trainers: shrunken trainer edges barely persist between 2022-24 and 2025-26 (correlation 0.06, p 0.09); the general quick-backup term already absorbs the average effect (1.01 after v2.2). Re-test only with materially different evidence. | batch11/out_trainer_quick.csv |
| 25 Nov 2026 | Exceptional lightly raced horses are broadly undervalued | Top-third, last start 3 kg+ better than expected: 0.98 (0.94-1.03) | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | Generic interstate bonus for Vic->Tas runners | Not added by rule: a winning-frequency gap is not a mechanism; address rating connections instead | batch11/ |
| 25 Nov 2026 | Trainer decisions (distance/class/jockey changes as trainer signals), dynamic trainer form, jockey tail rates | Failed discovery or validation | batch10/README.md |
| 25 Nov 2026 | Racing-style vs opposition (Qld), preparation shape, isolated peak, schedules B/C, acceleration trend | Failed discovery or validation | batch10/README.md |
