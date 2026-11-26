# Research library (permanent)

One line per hypothesis, newest first within each section. Evidence lives in the batch ledgers named. "Rejected" items stay
here so they are not re-tested without materially different evidence. Market data never enters any rating input.

## In production
| Since | What | Evidence | Ledger |
|---|---|---|---|
| 27 Nov 2026 | Engine v2.3 (six states): history weight credit 0.25 kg per kg + 0.170 s per length, full refit (approved 26 Nov 9:07pm) | 2025-26 +0.0095 (0.0076-0.0113) vs v2.2 as run; top pick +0.6 pts; v2.2 kept as daily previous-engine shadow | batch13/, benchmarks/engine_v2_3/ |
| 27 Nov 2026 | Engine v2.1.3 (Qld): v2.1.1 + Age & sex (approved 26 Nov 9:07pm) | 2024 +0.0190, 2025-26 +0.0166; v2.1.1 kept as daily previous-engine shadow | batch13/, benchmarks/engine_v2_1_3/ |
| 26 Nov 2026 | Weight carried (allocated minus apprentice claim) for the national model; Qld unchanged (consistent allocated) | Definition match with history; replay 1 top pick in 37 races | benchmarks/engine_v2/RELEASES.md |
| 26 Nov 2026 | Engine v2.2: 14 terms (career shape and consistency, light weight, quick backup, measured venue class) | Validation +0.0125 log-lik per race (0.0105-0.0145) | batch10/ |
| 26 Nov 2026 | Engine v2.1.1 (Qld): v2.1 refitted on the database with Breednet Qld country meetings | +0.0121 vs v2.1 on 2025-26 | batch10/v211/ |

## Candidates (not live)
| Since | What | Status | Ledger |
|---|---|---|---|
| 26 Nov 2026 | Common national framework with Qld coefficients (one methodology, regional coefficients; a variant keeps Qld physical inputs) | Research: 2024 +0.0424, 2025-26 +0.0326 vs v2.1.1. Damo 26 Nov: build as a SHADOW; no promotion without an evidence review | batch13/qld_align.py |
| 26 Nov 2026 | Handicap weight slope (wt_x_hcp) on top of Engine v2.3 | Damo 26 Nov: prepare for the following release. Preregistered 2024 +0.0012 (0.0008-0.0017); +0.0014 over C2 on 2025-26 (not independent) | /tmp/cand evidence -> batch13 build |
| 25 Nov 2026 | National rating rebuilt with weight credit 0.25 kg per kg (history) and 0.170 s per length (figures), full v2.2 rebuild | Released as Engine v2.3 from 27 Nov 2026 (see In production); kept here for its Batch 11-12 history | benchmarks/candidate_national_weight/, batch12/candidate_weight/ |
| 25 Nov 2026 | Today's weight vs field in handicaps (own slope) on top of the weight candidate | Preregistered; 2024 +0.0012 (+0.0008 to +0.0017), negative coefficient both windows; residual 3 kg+ under field 1.50 -> 1.36 (part only) Damo 26 Nov: prepare for the release after v2.3 | preregistered/2026-11-25_b12_weight_handicap.md, batch12/candidate_weight/ |
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

## Reconciliation, 26 Nov 2026 (checked against production code and manifests, not reports)
Production as it runs: Qld = Engine v2.1.1 (prerace/score_prerace.py combined_v1 + national v3 rating, benchmarks/candidates_b4_national_v3;
engine/score_v2.py QLD family from benchmarks/engine_v2_1). Other states = Engine v2.2 (prerace/score_national_prerace.py nat_v2 from
benchmarks/candidates_national_common; engine/score_v2.py NSW_VIC_ACT family; engine/v22.py 14 terms from benchmarks/engine_v2_2).
Verified 26 Nov: Rockhampton was scored by v2.1.1 (its manifest says so; family QLD, no v2.2 terms); only the dashboard label said v2.2 (fixed).

| Finding | Evidence | Qld | National | Status / why not further |
|---|---|---|---|---|
| Simple form (avg finish last 3, last finish/margin, win %, starts) | Batch 2-3 | yes | yes | Production. Simplification found last-start finish redundant nationally and hurting in Qld (B11) -> Qld v2.1.2 shadow |
| Time figures in kg (best/avg/form of last 3, weight vs field) | B1-B3 | yes | yes | Production |
| Closing sectionals (last 600 gap, top-3 L600, last 200, finishing speed) | B2-B6 (R8 supported) | yes | no data | Production in Qld only. Measured sectionals carry ~2% of the Qld score (B11 shares) |
| Race shape: settling position, leader, relative barrier, barrier x style, lone leader | R7 validated, B2 | yes | no data | Production in Qld only (needs positions and barriers) |
| Track / distance / going history | B2, B5 records | yes (two sets) | yes (records) | Qld duplicates them (T group + records): v2.1.2 shadow drops the T group |
| Fitness and spacing | B2 | yes | yes | Production |
| Margin-based dynamic rating (opposition-aware) | B4 Study 12 | yes | yes | Production: the strongest single input (dropping it costs 0.025/race in Qld) |
| Learning-speed rating (lightly raced expected to improve) | B9: Qld +0.0052 (0.0028-0.0076); NSW/Vic replacement -0.0026 (-0.0037 to -0.0016) | yes (v2.1, 25 Nov) | no | Not tested on identical common inputs. NSW/Vic test pre-dates SA/WA/Tas/Qld-country data and national ages. OPEN (brief s5) |
| Jockey and trainer strike rates, jockey change | B7 R50-R68 | yes | yes | Production |
| Age and sex | B7 +0.0129/race | NO | yes | Excluded in Qld only because Qld history had no ages; ages now 98.9% (26 Nov database). Ready to test in Qld |
| Form changes and head-to-head (h2h, distance change, trajectory, last surprise, class change, weight change) | B7 | NO (hurt in 2025-26) | yes | Qld dropped by evidence (B7 release note) |
| Engine v2 interactions (chosen on discovery data) | B7 | no | yes | Production national only |
| v2.2: 14 career-shape / consistency / weight / spacing / venue-class terms | B10 +0.0125 (0.0105-0.0145) | NO | yes | Never tested on Qld. OPEN (brief s5) |
| Weight carried today (claim deducted) | B11 definition check | no (allocated, consistent) | yes | Production 26 Nov. Qld carried tested: no gain (B11) |
| Display calibration (bent line) | B9 E | yes | yes (refit for v2.2) | Production |
| Qld scorer fix (rating was zero-weighted 24-25 Nov) | v2.0.1 | yes | - | Production |
| Measured venue class (meeting note; v2.2 venue step) | B10 | note only | yes | Production |
| Experience labels and race data confidence | B11 s5 | yes | yes | Production (display only) |
| C2: weight credit 0.25 kg per kg + 0.170 s per length | B11/B12: +0.0107 (0.0089-0.0124) vs production as it runs, 2025-26; +0.0105 / +0.0084 vs refitted production | no | NOT YET | Built and reproducible; calibration refit and shadow never started (no approval recorded). Completed for a release decision 26 Nov night (see benchmarks/candidate_national_weight) |
| Handicap weight slope on top of C2 | preregistered: 2024 +0.0012 (0.0008-0.0017) | no | no | Primary test passed; 2025-26 not independent. Release option with C2 |
| Qld v2.1.2 (drop last-start finish and track/distance/going history) | B11: 2024 weak, top pick not better | shadow | - | Shadow from 26 Nov (1 day so far). Decide on prospective races only |
| Course-specific barrier effects (Eagle Farm 1800-2100, Sunshine Coast 1200-1400, sprint leaders) | B4 Study 10 frozen (course_v1) | no | no | Frozen for a future-race test; scored once (25 Nov), not daily. Watch |
| Late fade within 1 L, stride shortening, ground covered in the Qld rating | B12 open | no | no data | Open hypotheses (prospective only) |
| Ordinary debut overrated; top-3 first starters underrated; lightly raced last-start winners underrated | B11 A/E 0.75-0.80, 1.21-1.27, 1.19 | no | no | Open: residual patterns, need a mechanism (rating certainty) not a bonus |
| Interstate connections (Tas ~2.3 kg high vs Vic; SA ~0.9; Qld 0.5-1.2) | B11 selection-adjusted | no | no | Open: fix belongs inside the rating (pool levels), never a travel bonus |
| Rejected list above | | | | Kept so they are not re-tested without new evidence |

Previously approved and NOT implemented: none found in production code. Two approved items still pending outside the engine:
the one-off Ascot 12 Apr 2025 re-collection (in collect/weekly/retry_queue.json, runs at the next weekly update) and the
national weight candidate's next steps (calibration + shadow), which were planned but never approved or started until 26 Nov.
Two registers existed for hypotheses (this file and batch8/out/hypothesis_register_R1_R68.csv). This file is the single
research register from 26 Nov; R1-R68 stays as its numbered appendix (its open/watch items are folded into the rows above).

## Batch 13 (26 Nov 2026 night): consolidation tests behind the 27 Nov release proposal
Scripts and outputs: research/batch13 (qld_align.py, learning_speed.py, weight_qld_rows.py, build_qld_v213.py, calib_qld_v213.py; out/*.csv).
Measure: log-likelihood gain per race with a 95% meeting-bootstrap interval. Window A = fit before 2024, judged on 2024 (independent of
every choice below). Window B = fit before 2025, judged on 2025-26 (RE-USED: earlier batches looked at it, so it is not independent).
The first untouched evidence for anything released on 27 Nov is races from 27 Nov onward.

| Test | A (2024) | B (2025-26) | Reading |
|---|---|---|---|
| Qld v2.1.2 (shadow) vs v2.1.1 | +0.0012 (n.s.) | +0.0061 (0.0025-0.0096) | weak; stays shadow, judged on prospective races |
| Qld v2.1.1 + Age & sex (= v2.1.3 candidate) | +0.0190 (0.0128-0.0253) | +0.0166 (0.0116-0.0215); 2026 +0.0238 | clear in both windows; small, pre-specified change |
| Qld v2.1.1 + the 14 v2.2 terms | +0.0068 (n.s.) | +0.0108 (0.0043-0.0170) | not clear in 2024; v2.2 inputs only 39-100% present on Qld rows |
| Qld v2.1.1 + Age & sex + v2.2 terms | +0.0240 (0.0126-0.0354) | +0.0232 (0.0151-0.0309) | adds ~0.005-0.007 over Age & sex alone; needs Qld-coefficient v2.2 build |
| Qld v2.1.2 + Age & sex + v2.2 terms | +0.0250 | +0.0293 | |
| Common national framework, Qld coefficients | +0.0424 (0.0262-0.0587), top pick +1.66 | +0.0326 (0.0208-0.0435), top pick +0.66 | strongest; larger build; next step = shadow |
| Common framework + Qld physical inputs (sectionals, barrier, race shape) | +0.0442, top pick +2.24 | +0.0343, top pick +1.14 | physical inputs add only ~+0.002 on top |
| Learning speed (v3) on common inputs | national -0.0020; Qld rows +0.0005 | | same experience shape in both: helps 4-10 runs held (+0.015/+0.016), hurts 0-3, 11+ and truncated histories |
| Qld rows on carried instead of allocated weight (21,297 of 147,433 Qld rows differ) | | Qld races +0.0015 (-0.0002 to +0.0028); other states +0.0002 (0.0001-0.0003) | no material gain; keep allocated, carried and claim as separate fields |
| Engine v2.3 (C2) as BUILT by the release chain vs production as it runs | (B12 refit: C2 vs B0 +0.0105 on 2024) | +0.0095 (0.0076-0.0113), top pick +0.6 pts; NSW/Vic/ACT +0.0093, SA +0.0023, WA +0.0145, Tas +0.0113; 2025 +0.0115, 2026 +0.0072 | built release reproduces Batch 12 (refit +0.0107) within 0.0012 |
| Handicap weight slope on top of C2 | preregistered +0.0012 (0.0008-0.0017) | +0.0014 over C2 | NOT in the 27 Nov build (one change at a time); next release candidate |

Findings that change earlier conclusions: (1) Qld's missing Age & sex was a data gap, not a Qld effect: with ages now held it is the
largest single Qld improvement available. (2) The Qld v3 learning-speed gain looks like a stand-in for the age information Qld lacked
(it persists without physical inputs and is neutral on common inputs); keep v3 in production until Age & sex is live, then re-test.
(3) A common national framework with Qld's own coefficients beats every Qld-specific variant; Qld's physical measurements add little on
top at present. This supports one national methodology with regional coefficients. SA note: SA rows were inside the six-state fitting
data for C2 (weight credit and seconds per length), so SA is NOT an independent check of C2; SA stays independent for v2.1.3 (Qld only).
