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
| 25 Nov 2026 | National rating rebuilt with weight credit 0.25 kg per kg (history) and 0.170 s per length (figures), full v2.2 rebuild | Full engine rebuilt and refitted: +0.0107 log-lik per race vs production as it runs (2025-26, +0.0089 to +0.0124), top pick +0.56 pts; +0.0105 / +0.0084 vs refitted production (2024 / 2025-26); credit carries almost all of it. Reproducible. Next: calibration refit and shadow scoring | benchmarks/candidate_national_weight/, batch12/candidate_weight/ |
| 25 Nov 2026 | Today's weight vs field in handicaps (own slope) on top of the weight candidate | Preregistered; 2024 +0.0012 (+0.0008 to +0.0017), negative coefficient both windows; residual 3 kg+ under field 1.50 -> 1.36 (part only) | preregistered/2026-11-25_b12_weight_handicap.md, batch12/candidate_weight/ |
| 25 Nov 2026 | Qld v2.1.2: drop last-start finish and track/distance/going history | Shadow-scored from 26 Nov; decide on prospective races only (2024 window weak, top-pick rate not better) | benchmarks/candidate_qld_v2_1_2/, batch11/ |

## Open hypotheses (judged only on races from 26 Nov 2026)
| Raised | Hypothesis | Evidence so far (2025-26, re-used period) | Ledger |
|---|---|---|---|
| 25 Nov 2026 | A late fade (weak final-200 retention vs own norm) after finishing within 1 L precedes a worse next run | -0.56 kg (-1.14 to -0.10), 358 runs; 2022-24 -0.66, 2025-26 -0.44 (interval includes 0). A fade in general precedes a +0.5 kg bounce (stable) | batch12/out_s5_late.csv |
| 25 Nov 2026 | Holding speed with shorter, quicker strides (vs own norm) precedes a worse next run (Qld tracking) | -0.43 kg (-0.73 to -0.11), 926 runs; both periods negative. One of six stride patterns tested; nothing about injury or fatigue inferred | batch12/out_s6_stride.csv |
| 25 Nov 2026 | A spread-aware chance calculation (the engine overrates consistent horses, underrates erratic ones) | actual/expected 0.95 most consistent third vs 1.05 least; not a bonus for inconsistency | batch12/out_s12_consistency.csv |
| 25 Nov 2026 | Ground covered built into the Qld rating itself (not as an added input) | Added input: discovery +0.0028 (+0.0011 to +0.0048), validation +0.0002 (-0.0019 to +0.0021); integrated rebuild not yet run | batch12/out_s4_qld_physical_terms.csv |
| 25 Nov 2026 | Horses after an ordinary debut (within 3 kg of expected) are overrated | actual/expected 0.75-0.80 under v2.2 | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | First starters the engine ranks 1st-3rd are underrated | 1.21-1.27 | batch11/out_lightly_raced.csv |
| 25 Nov 2026 | Lightly raced (1-3 runs) last-start winners rating in the top third are underrated | 1.19 (1.07-1.33), 699 runners | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | Vic horses on a first Tasmanian start beat their rating (rating connection, not a bonus) | 1.85 first start, 1.00 repeat; Tas->Vic 0.63 | batch11/out_vic_tas.csv |
| 25 Nov 2026 | Light weights in handicaps beat their rating (weight credit / today's weight under-used) | 1.32 (1.22-1.43) after v2.2 | batch11/out_light_weight_v22.csv |
| 25 Nov 2026 | Today's weight vs field is under-used (light weights in handicaps beat their rating) | Corrected 25 Nov (Batch 12): the weight credit does NOT remove it (1.61 -> 1.50); a handicap-specific slope removes part (1.36). See the handicap candidate | batch11/followup/out_weight_vs_field.csv |
| 25 Nov 2026 | Interstate pools are mis-connected (Tas ratings ~2.3 kg high vs Vic; SA ~0.9; Qld ~0.5-1.2) | Every-runner surprises, selection-adjusted; fix = pool levels inside the rating | batch11/followup/out_connections.csv |

## Rejected
| Date | Hypothesis | Why rejected | Ledger |
|---|---|---|---|
| 25 Nov 2026 | Continuous per-horse distance profile (surprises smoothed across distance) | Hurts on top of v2.2: validation -0.0026 (-0.0037 to -0.0014); past over-performance at a distance regresses; band record already in the engine | batch12/out_s8_distance.csv |
| 25 Nov 2026 | Peak vs typical, time/runs since best, career best, peak frequency (ceiling and decline) | Validation -0.0078 to +0.0005 on top of v2.2; variability and below-best-3 terms already carry it | batch12/out_s11_peaks.csv |
| 25 Nov 2026 | Perennial placegetters / under-converting horses | Next-start actual/expected 1.00 (most under-converting fifth) vs 1.01; placegetter profile 0.99 on 9,565 runs; as inputs -0.0003 | batch12/out_s13_conversion.csv, out_s13_bands.csv |
| 25 Nov 2026 | Opposition composition counts (rivals rated 2 kg+ above, and x own standing) | Validation -0.0003 / +0.00007 with discovery negative; field spread and top-two gap are constant within a race | batch12/out_s14_opposition.csv |
| 25 Nov 2026 | Improvement on the same run of last preparation, as an input | Real but modest persistence (r 0.19); validation -0.00002 on top of v2.2; kept as a description only | batch12/out_s10_prep_rel.csv |
| 25 Nov 2026 | Last-start late retention / final-200 speed as added Qld inputs | Discovery intervals include 0; validation -0.0020 / -0.0016 | batch12/out_s4_qld_physical_terms.csv |
| 25 Nov 2026 | Weight carried (claim deducted) in the Queensland model's history | Like-for-like rebuild: 2025-26 +0.0002 (-0.0035 to +0.0039), 2024 -0.0048 (-0.0100 to +0.0011): no gain; Qld keeps allocated weight in history and production (consistent) | batch11/followup/qld_carried_vs_allocated.csv |
| 25 Nov 2026 | No weight credit at all (0 kg per kg) | Not better than 0.5 (+0.0000) and worse than 0.25 | batch11/followup/out_prereg_spl_weight.csv |
| 25 Nov 2026 | Trainer-specific quick-backup bonuses (each trainer's backups vs that trainer's ordinary runners) | 557 trainers: shrunken trainer edges barely persist between 2022-24 and 2025-26 (correlation 0.06, p 0.09); the general quick-backup term already absorbs the average effect (1.01 after v2.2). Re-test only with materially different evidence. | batch11/out_trainer_quick.csv |
| 25 Nov 2026 | Exceptional lightly raced horses are broadly undervalued | Top-third, last start 3 kg+ better than expected: 0.98 (0.94-1.03) | batch11/out_lightly_raced2.csv |
| 25 Nov 2026 | Generic interstate bonus for Vic->Tas runners | Not added by rule: a winning-frequency gap is not a mechanism; address rating connections instead | batch11/ |
| 25 Nov 2026 | Trainer decisions (distance/class/jockey changes as trainer signals), dynamic trainer form, jockey tail rates | Failed discovery or validation | batch10/README.md |
| 25 Nov 2026 | Racing-style vs opposition (Qld), preparation shape, isolated peak, schedules B/C, acceleration trend | Failed discovery or validation | batch10/README.md |
