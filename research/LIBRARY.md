# Research library (permanent)

One line per hypothesis, newest first within each section. Evidence lives in the batch ledgers named. "Rejected" items stay
here so they are not re-tested without materially different evidence. Market data never enters any rating input.

## Reconciliation, 27 Nov 2026 night (Batch 23; supersedes the 26 Nov reconciliation below as the status of record)
Checked against the code that runs, the manifests in benchmarks/, ops/run_shadow.sh and the switch files. Statuses: PRODUCTION; APPROVED
CORRECTION (live from a stated run); FROZEN SHADOW; BUILT CANDIDATE (awaiting deployment); PROMISING RESEARCH; DESCRIPTIVE; REJECTED/REDUNDANT;
AWAITING DATA; NOT YET INVESTIGATED. "Pred." = tested as a forecast input; "Desc." = describes horses, not tested as an input.
Engine inputs, coefficients and served influence: batch23/engine_inventory.csv and batch23/out_b23_family_influence.json.

| Finding (first batch) | Data / states | Main result | Type | Status | Where it lives / supersedes | Next action |
|---|---|---|---|---|---|---|
| Opposition-aware margin rating (B4) | all | strongest single input | Pred. | PRODUCTION (v2.3 national, v3 rating in Qld) | layer 1 dyn_nat | - |
| Time figures, recent form, fitness/spacing (B1-B3) | all | core inputs | Pred. | PRODUCTION | layer 1 | - |
| Closing sectionals, race shape, relative barrier, barrier x style (B2-B6) | Qld | ~2% of Qld score | Pred. | PRODUCTION (Qld only) | Qld v1 groups | pooled barrier would REPLACE relative barrier + barrier x style (B20-B22) |
| Horse course/going/distance records (B5) | all | | Pred. | PRODUCTION | layer 1 nat_v2 / Qld v2 family | Qld duplicates with its T group (v2.1.2 shadow tests dropping it) |
| Jockey & trainer, jockey change (B7) | all | | Pred. | PRODUCTION | layer 2 | trainer names need normalising before transfer work (B22 D) |
| Age & sex (B7; Qld B13) | all | national +0.0129; Qld +0.0190/+0.0166 | Pred. | PRODUCTION (Qld v2.1.3 from 27 Nov) | layer 2 | first-starter age/sex from TAB: APPROVED CORRECTION from 28 Nov |
| Form changes & head-to-head, interactions (B7) | national | | Pred. | PRODUCTION (national only; hurt Qld) | layer 2 | - |
| 14 v2.2 terms: career shape, light weight, quick backup, venue class (B10) | national | +0.0125 | Pred. | PRODUCTION (national); never on Qld production | layer 3 | Qld gets them only via the common-framework shadows |
| Weight credit 0.25 kg/kg + 0.170 s per length (B11-B13) | six states | +0.0095 | Pred. | PRODUCTION (Engine v2.3 from 27 Nov) | history figures | - |
| Weight carried (claim deducted once) (B11) | national | definition match | Pred. | PRODUCTION (national); Qld keeps allocated (consistent) | serving | verify claim deducted once each morning (B23 A1) |
| bm_change class change (B16) | national | serving it costs 0.0012/0.0007 | Pred. | PRODUCTION as a documented TRAINING-ONLY control | engine_v2_3/FEATURE_NOTES.md | only intentional train-not-serve input |
| Learning-speed rating (B9; v3) | Qld | Qld +0.0052; national -0.0026 | Pred. | PRODUCTION in Qld via the v3 rating | Qld v2.1.x | FORGOTTEN: B13 said re-test once Age & sex was live in Qld (live since 27 Nov) - not yet re-tested |
| Display calibration, experience labels, data confidence (B9-B11) | all | | display | PRODUCTION | dashboard | - |
| Metro from tier, Qld course-name map (B18) | SA/WA, Qld | Qld track history 0% -> 73% | correction | APPROVED CORRECTION from 28 Nov (switches) | serving | verify in the 28 Nov run |
| National emergencies that gain a start (B18-B19) | national | 26 Nov 11/11; 27 Nov 52 admitted and ran, 2 admitted then late-scratched, original rule missed 53 | correction | PRODUCTION from the 28 Nov run (switched on 27 Nov 11:10pm) | ops/national_emergency_enabled; benchmarks/engine_v2/RELEASES.md | keep checking daily |
| Handicap weight slope = Engine v2.4 (B11-B15) | national | +0.0005 / +0.0015 built | Pred. | FROZEN SHADOW (from 27 Nov) | benchmarks/engine_v2_4_candidate | final recommendation Monday after TAB/Breednet class parity |
| Heavy-defeat cap 12 L (B15-B16) | national | +0.0043 | Pred. | FROZEN SHADOW (cap-only) | benchmarks/engine_cap_only_candidate | superseded by the consolidated candidate if it wins prospectively |
| Uniform 1.3x good-run response (B15-B16) | national | +0.0059 | Pred. | FROZEN SHADOW (update-rule) | benchmarks/engine_update_rule_candidate | as above |
| Age-aware taper (B18-B19) | national | +0.0098 / +0.0104 vs v2.3 | Pred. | FROZEN SHADOW (brought forward to 28 Nov) | benchmarks/engine_age_aware_candidate | - |
| History-completeness experience (B19-B23) | national | +0.0010 / +0.0008 over age-aware | Pred. | BUILT CANDIDATE (research form); folded into the consolidated candidate; gentle-rule freeze Monday | batch23/b23_experience_file.py (v4, with cap) | - |
| Inferred-start cap (B22-B23) | national | cuts implausible inferred starts | data rule | APPROVED (in experience v4) | batch23/b23_experience_file.py | replace inferred by verified TAB counts as they accrue |
| Stronger experience response 1+0.8exp(-n/6) (B18-B21) | national | best individual error | Pred. | in the CONSOLIDATED CANDIDATE | - | - |
| Certainty-weighted race reference (B16-B21) | national | +0.0014 alone; +0.0016-0.0017 on top of the update rules | Pred. | in the CONSOLIDATED CANDIDATE | dyn_rating_innov RATING_REF (fixed inside the hook 27 Nov) | - |
| Consolidated rating candidate (B23) | national | research: 24.64 kg2; +0.0116 / +0.0166 | Pred. | BUILT through the release chain tonight if parity passes -> FROZEN SHADOW from 28 Nov | benchmarks/engine_consolidated_candidate | prospective clock |
| Common national framework for Qld, configs 2 and 4 (B13-B17) | Qld | +0.0424 / +0.0326 (research) | Pred. | FROZEN SHADOWS (from 28 Nov) | benchmarks/engine_qld_common_* | - |
| Qld v2.1.2: drop last-start finish and T group (B11) | Qld | weak 2024 | Pred. | FROZEN SHADOW (since 26 Nov) | benchmarks/candidate_qld_v2_1_2 | decide on prospective races |
| Trainer debut record (B18-B19) | national | +0.0004 / +0.0015 | Pred. | FROZEN SHADOW (brought forward to 28 Nov) | benchmarks/engine_trainer_debut_candidate | - |
| Sire debut record (B21-B22) | national | debut error 0.38 kg2; race +0.0006 / +0.0013; with trainer +0.0008 / +0.0021 | Pred. | APPROVED, NOT BUILT (frozen shadow after current shadows settle) | batch21/b21_sire_debut.py | build after the 28-29 Nov shadows run clean |
| Maternal siblings, damsire (B19-B21) | national | debut error 0.15 / 0.07 kg2 | Pred. (individual only) | PROMISING RESEARCH | batch21 | race-level test on top of sire + trainer |
| Lane-adjusted ratings, Qld and SA (B18-B19) | Qld, SA | SA +0.0013; Qld +0.0008 | Pred. | BUILT CANDIDATE (research form), no shadow yet | batch19/b19_lane_candidate.py | shadow once the 28-29 Nov shadows are settled; test with the barrier term |
| Pooled course x distance x rail barrier (B19-B22) | Qld, SA | Qld replacement +0.0022 / +0.0018; SA +0.0010 | Pred. | PROMISING RESEARCH (rail-dependent version provisional) | batch20/b20_barrier_feature.py | collect rail (from 28 Nov, Qld); morning-vs-results parity |
| National bent barrier shape (B21) | Qld, SA | +0.010 kg2/run | Pred. | PROMISING RESEARCH | batch21 | include in the barrier candidate |
| Absolute barrier number, going and field-size barrier factors (B21) | Qld, SA | worse out of sample | Pred. | REJECTED | batch21 | - |
| Course-specific barrier effects, course_v1 (B4) | Qld | frozen 25 Nov, scored once | Pred. | REDUNDANT (superseded by the pooled barrier work) | benchmarks/course_v1 | - |
| Race-layer x field inexperience / uncertainty (B20) | national | -0.0005 / 0.0000 | Pred. | REJECTED | - | do not reopen |
| Field-experience brake on the update (B22) | national | good runs in inexperienced fields under-moved | Pred. | REJECTED | batch22 | study how unknown rivals' levels are set (B23 C8) |
| Trainer change: under-reaction after transfer (B16, B20-B21) | national | +0.50 kg first run (controls) | Desc. -> Pred. next | PROMISING RESEARCH | batch21/b21_breakthroughs.py | normalise trainer names; test on top of the update rules |
| Trainer-specific transfer record (B16, B21) | national | +0.13 (n.s.) beyond general trainer record | Pred. | REJECTED as tested | - | - |
| Unfamiliar-distance breakthroughs (B20-B21) | national | step-up: +0.30 at new trip, -0.01 back | Desc. | PROMISING RESEARCH (distance-suitability framework) | batch21 | framework after Monday |
| Continuous per-horse distance profile (B12), own-runs distance suitability (B16) | national | -0.0026; engine gain 0.0000 | Pred. | REJECTED / REDUNDANT as built | - | the new framework is a different method (ability vs suitability), not a retest |
| Trainer early improvement 2nd-3rd start (B19-B20) | national | 0.17 kg/kg; harness 0.0000 | Pred. | DESCRIPTIVE | batch20 | - |
| First-up own record (B19-B20) | national | 0.14; harness n.s. | Pred. | DESCRIPTIVE | batch20 | - |
| Spacing preferences (B19) | national | chance level | Desc. | REJECTED | - | closed |
| Supported vs unsupported big runs; sustainability (B18-B20) | national | descriptive | Desc. | DESCRIPTIVE | batch18-20 | - |
| Sire maturity (B18-B19) | national | not replicated | Pred. | REJECTED as a general input | - | - |
| Uneven last 600 precedes a better next run (B14) | Qld, SA | +0.26 kg per sd, replicated in SA | Desc. | PROMISING RESEARCH | batch14 | FORGOTTEN: bundle test +0.0034 / +0.0021 (n.s.) never followed up as its own Qld input |
| Late fade within 1 L; stride shortening (B12) | Qld | -0.56 / -0.43 kg | Desc. | AWAITING DATA (prospective check) | batch12 | FORGOTTEN: the prospective check was never run; due once 28 Nov+ results are in the master |
| Ordinary debut overrated; top-3 first starters underrated; lightly raced winners underrated (B11) | national | 0.75-0.80; 1.21-1.27; 1.19 | Desc. | AWAITING re-check | batch11 | FORGOTTEN: re-check under the update-rule and debut shadows (they may already explain it) |
| Spread-aware chances (consistency) (B12) | national | 0.95 vs 1.05 | Desc. | PROMISING RESEARCH | batch12 | partly addressed by the update rule (erratic horses' big runs); re-check |
| Ground covered inside the Qld rating (B12) | Qld | added input n.s. | Pred. | SUPERSEDED by the lane candidate (ground controlled there) | - | - |
| Interstate connections / state offsets (B11, B16) | all | already priced in the engine | Pred. | REDUNDANT | - | - |
| State seconds per length (B15-B16) | all | -0.0012 / -0.0006 | Pred. | REJECTED | - | - |
| Jockey distance specialisation, rider momentum, jockey workload (B14-B15) | Qld, SA | engine +0.0001; workload artifact | Pred./Desc. | REDUNDANT / DESCRIPTIVE | batch14-15 | frozen rider tables' prospective check not run |
| Horse identity: suffix/sire/dam splits (B20-B22) | all | 56 splits | data | APPROVED CORRECTION (Monday 30 Nov, subject to checks) | ops/IDENTITY_CORRECTION_PLAN.md | Monday |
| Qld start-count discrepancy (B19-B20) | Qld | measurement bug | data | FIXED (research script) | ops/form_enrichment.py | - |
| Pre-race rail and track information (B21-B23) | Qld now | RQ publishes before the cutoff | data | COLLECTED from 28 Nov (not served) | ops/parse_rail.py; DAILY_RUN 5d | other states need a source that permits collection (RaceHub's robots file blocks Claude's crawlers: not used) |
| Leaders vs tactical leaders; stable racing styles; competition for position; cost of position; sit-and-sprint; tempo x position x bias (B23 G) | Qld, SA tracking | - | - | NOT YET INVESTIGATED (added to the physical/tactical family) | - | after the physical queue starts |
| Economical cruising; acceleration and adjacent distances; cumulative demands; going tolerance; education and habits (B20-B23) | Qld, SA | - | - | NOT YET INVESTIGATED | - | after Monday |

## Batch 24 (27 Nov 2026 night): findings and newly registered research families
Findings (research only; nothing served):
- Consolidated scale: not a constant offset. Production rating mean drifts down ~0.8 kg/yr (-3.21 in 2022 to -6.31 in 2026), the
  consolidated candidate up ~0.8 kg/yr (-2.64 to +0.66). Uniform shifts cancel exactly (every term is centred within its race).
  Drift reaches: within-horse lagged inputs (below_top3, gap_long_z, short_vs_long, slope15, last_race_strength; stable offsets
  2024-26, within-race correlation 0.91-0.94 between builds), the 'ability x field strength' interaction (absolute field level moves
  ~0.3 sd by 2026, ~2% of the rating's weight), and venue class. No defect; candidate stays frozen. Next: period re-anchoring test,
  both engines. batch24/out_b24_scale_*.json.
- First-starter starting level (consolidated rule): 1.5 kg instead of 2.0 removes most debut bias (+0.46 -> +0.12 kg), debut error
  31.95 -> 31.72 kg2, less drag on established rivals (-0.61 -> -0.40), but race accuracy is a wash (2024 -0.0007, 2025-26 +0.0005);
  1.0 kg overshoots. Missing-career first runs (n 621) move the other way: they need their own start from inferred experience.
  DESCRIPTIVE / PROMISING (no candidate). batch24/out_b24_starting_level.json.
- Meeting speed (Part C8, preliminary): the meeting effect is real (other races predict a left-out race's time deviation, r 0.81);
  stronger fields run 0.063 s/km faster per kg of field strength; a leave-one-race-out, field-strength-adjusted variant raises figure
  repeatability (next figure within 60 days, later period, 198,934 pairs) from 0.349 (existing daily variant) to 0.361. Holds in
  NSW/VIC/QLD/WA/ACT; TAS slightly worse; SA anomalous (no adjustment best). UPDATE 28 Nov 00:45: repeatability is confounded
  (consecutive runs share a season's surface speed; that was the SA 'anomaly'). Cleaner test - previous figures ranking today's
  field, 24,025 later-period races: none 0.181, existing variant 0.232, LORO 0.225, LORO + field strength 0.231, existing-style
  (race included) + field strength 0.238 (top-figure winner 18.4% vs 18.1%; better in every state). Inside the engines (full
  research frames, only figure inputs changed): Engine v2.3 -0.0008 / +0.0002, consolidated -0.0006 / +0.0001 -> no engine gain
  (the rating already carries field strength). DESCRIPTIVE: a better standalone time figure for meeting/tempo/sectional research,
  not an engine candidate. batch24/b24_meeting_speed.py, b24_ms_runs.py.
- Scale drift causes (28 Nov 00:45): mechanical, not population change - time figures flat by year (88.7-89.3; metro 93.6-94.1).
  Entrants start ~1.25 kg below their field in both engines; continuing horses rise +0.06 to +0.13 kg/run in production (deflation
  wins) and +0.21 to +0.35 kg/run under the consolidated rule (inflation wins). PRIORITY RESEARCH (Damo 28 Nov): point-in-time
  re-anchoring on established horses, effects on peaks, decline, spell returns, venue class, interstate. batch24/out_b24_drift_causes.json.
- Rail data foundation: retrospective rail already held for Qld (9,758 races from Oct 2022), SA (1,775 races from Jan 2024),
  NSW/ACT (331 meetings from Jul 2026); pre-race from 28 Nov for Qld (RQ) and NSW/ACT (Racing NSW FreeFields). See
  ops/foundation/field_register.csv (national rail row). MANDATORY data workstream; model use evidence-dependent.
Newly registered families (NOT YET INVESTIGATED unless stated; tracking-based ones use Qld/SA/Vic data as each actually supplies it):
performance against race shape (tempo x position x lane x ground x sectional speed; Part B5); tempo and the meaning of margins (B6);
historical course-distance benchmarks by age/class/going/season (C7, audit done: production uses venue x distance par + daily variant);
meeting-specific benchmarks (C8, begun); meeting speed + lane bias + race shape integration (C9); whole-field underestimation and
connected form lines (D10); stewards' observations as context (D11, existing programme); response to racing pressure (E12);
conditional consistency, ceiling and range (F13); familiar/home-track performance (F14, reconcile with redundant course records);
development before rating change (G15); turn of foot and speed development (G16); settling and racing education (G17);
deterioration before rating decline (G18). Rediscovered: Qld learning speed retest, uneven last 600 as its own Qld test, late-fade
prospective check, debut/lightly raced findings under the new rules (B24 s27).

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

## Batch 14 (26-27 Nov 2026 night; Damo's "Research Batch 13"): physical performance, momentum, course geometry, rider specialisation
Ledger and scripts: research/batch14/README.md. Outcome: next-run rating surprise (kg) unless stated. Qld 2022-24 discovery, Qld 2025-26
re-used, SA 2024-26 independent (now used for these hypotheses: no longer untouched for them). Nothing changes production.

| Finding | Evidence | Status |
|---|---|---|
| An uneven last 600 (one 200 m section given up, at the same average speed) precedes a better next run than the rating expects | +0.26 kg per sd (0.18-0.33) Qld 22-24; +0.22 (0.14-0.30) Qld 25-26; +0.31 (0.20-0.42) SA. Horse's habitual unevenness +0.57 to +0.81 per sd. On top of Qld Engine v2.1.3: 2024 +0.0049 (0.0009-0.0094), 2025-26 +0.0011 (n.s.) | MEANINGFUL (rating level); engine value unconfirmed: open hypothesis, judge on races from 27 Nov. Extends Batch 12 s5 (weak retention bounce) |
| Sustained finishing (no section given up) is NOT, by itself, a sign of a better next run | weakest-section term -0.57 / -0.50 / -0.77 kg per sd holding the average; top-quarter sustained among 5th-or-worse finishers +0.09 / -0.02 / +0.15 (n.s.) | Rejected as a future signal |
| Acceleration timing (gaining on the field 800-400 out vs last 400) is a repeatable trait of horses and of riders | horse split-half r 0.41 (3,218 horses) Qld, 0.32 SA; rider within the same horse 0.46 (137 riders) Qld, 0.52 SA; circumstances explain 4-5% | MEANINGFUL (descriptive); no prospective value found yet |
| Earlier momentum helps more at courses where leaders hold (empirical 'hold' index by track) | interaction +0.02 (-0.04 to +0.08) Qld; +0.16 (-0.03 to +0.34) SA | Not supported (Qld); SA hint only. Tested with an EMPIRICAL leader-hold index only, which is not course geometry: the geometry hypothesis stays OPEN (follow-up s10) |
| Leaders at the 200 who built momentum earlier hold on less, for the same lead and speed | odds ratio 0.32 (0.22-0.46) per 1 m/s Qld, 0.23 (0.10-0.56) SA | Descriptive (energy cost), same-race |
| Riders differ consistently in late speed retention on the same horse | within-horse split-half r sprint 0.49 (137 riders), middle 0.45 (118), staying 0.02 (41, small) | MEANINGFUL (descriptive). Follow-up: validated in SA overall (within-horse r 0.60, 38 riders; trainer removed 0.595); distance split NOT established at finer bands; no value beyond j_surp; Qld engine +0.0008 / +0.0013 (uncertain-small) |
| Jockey distance specialisation | persistence r 0.34 raw, 0.17 after trainer; +0.26 kg per kg (0.20-0.32) beyond j_surp and trainer distance form; trainer distance form +0.40; Engine v2.3 test +0.00007 (2024) / +0.00014 (2025-26) | Real but too small for the engine: no candidate. Follow-up: persistent year to year (r 0.27-0.38); optimal shrinkage 734 rides; no specialist subgroup; Engine v2.3 -0.0003 to +0.0001 alone or inside j_surp: genuine, redundant/too small |
| Jockey workload (fatigue) across a meeting | within jockey x meeting apparent +0.16 to +0.40 kg is shared by trainers (placebo +0.13 to +0.21) = measurement artifact; rating-free check -0.4 to -1.0% of the field on later rides; scheduled gaps (Qld) no effect; busier days +0.1 to +0.36 kg = booking selection | CLOSED (follow-up s7): no workload or order effect; artifact mechanism identified; owner's observations preserved in batch14/followup/README.md |
| Within-meeting comparisons of rating surprise carry an order artifact | trainer placebo above | Method rule (follow-up s7): with race-relative outcomes, control race-relative ratings (rating minus field mean) or none; never absolute ratings across races of different class |
| Leader that surrenders a big lead ('fell in' from 1.5 L+ at the 400) runs worse next time than one that held | -0.62 kg (-1.50 to +0.26) Qld, -0.70 (-2.68 to +1.29) SA; reversed for narrow leads | Interesting, uncertain |
| Leading a slow early tempo flatters the rating | slow vs fast early -0.73 kg (-1.13 to -0.33) Qld; SA +0.71 (n.s.) | Uncertain (does not replicate) |
| Physical deterioration (flat kick, faded, slow cruise vs own norm), repeats, and the owner's contexts | next-run effects ~0 (flat +0.18, faded -0.15, slow -0.01 Qld); recurrence 12.6% vs 11.8% base (flat); contexts n.s. (Qld first-up flat +0.42 borderline); 'concerning case' -0.24 (-1.08 to +0.60, 140 runs) | Rejected as a sign of FURTHER decline. Follow-up: an abnormal decline vs the horse's own normal is followed by a better-than-rated next run (+0.31 Qld, +0.77 SA kg; rating over-reacts); redundant in the Qld engine |
| Extra ground / width | +0.06 to +0.08 kg per sd at every phase (Qld); SA early +0.12, turn 0, straight +0.13; accelerating-while-wide no interaction | Small under-credit; timing of width not supported |
| Racing wide without cover | proxy (no runner within 0.30 s ahead and 1.5 m laterally at 600 and 400) agrees with itself only 69-72% between marks; effect n.s. | Cannot be measured from segment-average tracking; needs stewards text. Follow-up: stewards text now tagged (wide without cover 0.6-3.8% of Qld runs); effect n.s. (too few); stays OPEN |
| Physical improvement shows more against weaker opposition next time | interactions -0.00 / +0.02 Qld; -0.07 / -0.08 SA (n.s.) | Rejected |
| Uneven run vs stewards' interference comments (TAB past starts) | dip 0.24 vs 0.19 on 18 Qld runs with an interference comment | Follow-up s3: dip survives stewards controls (0.25 / 0.18 / 0.31 per sd) |

Awaiting data or not attempted: clear-running repeatability by horse and wide-without-cover (stewards reports now parsed in the follow-up;
horse-level repeatability still to test); Moonee Valley (no tracking held; old layout only, 2022-25; new layout = new configuration key from 2027);
extra ground x optimal distance; richer-to-poorer inference (s14); Jimmysstar (conceptual only). Pride Of Jenni: three measured runs
(Doomben 2025 and 2026, Caulfield 27 Sep 2026); full profiles in batch14/followup/README.md.


## Batch 14 follow-up (27 Nov 2026, 00:23-01:30): physical profiles, momentum, rider characteristics
Ledger, scripts, full numbers: research/batch14/followup/README.md. Research only; no production change. Outcome: next-run rating surprise
(kg) unless stated. Qld 2022-24 discovery, Qld 2025-26 re-used, SA 2024-26 check.

| Finding | Evidence | Status |
|---|---|---|
| Seven finishing profiles; Progressive fade and Late fade precede better-than-rated next runs | Progressive fade vs Steady +0.55 (0.32-0.78) / +0.39 (0.15-0.63) / +0.79 (0.44-1.14); next five +0.23 / +0.24 / +0.35; Late fade +0.20 / +0.21 / +0.28. Dip and recover does not replicate (SA -0.01). Early fade ~0 | MEANINGFUL against the rating; redundant in the Qld engine (+0.000) |
| Abnormal decline vs the horse's own normal finish | next run +0.31 (0.05-0.57) Qld, +0.77 (0.18-1.37) SA; rating drops 2.0 kg then is still 0.6 kg down after five starts; returns to normal 68% vs 76%; recurs 8.3% vs 5.8%; dropout 6.5% vs 2.8%; contexts n.s. | MEANINGFUL against the rating (rating over-reacts); no causes inferred; redundant in the Qld engine |
| Abnormal improvement vs own normal | -0.07 / +0.02 (n.s.) | No signal |
| Stewards reports parsed (QRIC 2,827; SA 384 PDFs) | research/staging/stewards/stewards_events.csv.gz, 18 tags, subject vs mentioned, negation kept; Qld coverage 98-99% of meetings, 68-71% of runs with a paragraph; SA 30% | Supplementary evidence only; absent comment is not 'no event' |
| Horse and rider momentum profiles | horse timing r 0.27 / 0.25, retention 0.36 / 0.39; riders (same horse, trainer removed) timing 0.56 / 0.73, retention 0.59 / 0.60; 45% of relative gains made while slowing | Descriptive (research reference: horse_momentum_profiles.csv, rider_momentum_profiles.csv) |
| Horse early-timing x rider late-retention | -0.07 (-0.11 to -0.02) Qld, -0.23 (-0.37 to -0.08) SA kg per sd squared | Consistent, small; descriptive |
| Small improvements bundle | weight slope +0.0012 / +0.0014 on Engine v2.3; adding distance form makes it worse; Qld dip + profiles + riders together +0.0034 / +0.0021 (intervals include 0) | Only the weight slope is a candidate (already queued) |
| Pride Of Jenni, Doomben 2025 vs 2026 | near-identical times 122.74 / 122.68 s; 2025 first 1000 m 1.2 s faster; 2026 lead made by the field going slower; rating surprise -4.9 vs -0.2 kg | Different effort distribution, not different capability; being caught in 2026 was a run to her rating |

Small-improvement categories (keep using): genuine positive incremental (engine-measured); genuine against the rating but redundant in
the engine; uncertain-small; descriptive only; noise or rejected. Combined candidates are tested together against the production engine;
additivity is never assumed; top-pick strike rate is a downstream diagnostic only.
Kept OPEN (not rejected): course geometry and momentum retention; acceleration x course configuration; extra ground vs optimal distance;
wide with vs without cover; clear running and interruption sensitivity; cross-jurisdiction inference; measured times vs estimated figures;
interstate connections; dynamic distance suitability; one experience-dependent learning mechanism nationally. An empirical leader-hold
rate by track is not course geometry.


## Batch 21 (27 Nov 2026, first part): horse identity, responsiveness, trainer changes, distances, sire debut
Ledger: research/batch21/README.md. Report: https://claude.ai/artifact/E5PUAWm112r7pc68faiXc6.

| Finding | Evidence | Status |
|---|---|---|
| Durable identity = name + suffix + sire + dam | 59,246 identities; foaling season consistent in all but 1; TAB matching 1,030/1,068 unique, 0 ambiguous | Monday correction approved |
| Stronger rule + history-completeness | 24.72 kg2; +0.0102 / +0.0149; weaker in inexperienced fields | Research |
| Certainty-weighting adds to update rules | +0.0017 / +0.0016 on top (corrected run) | Candidate |
| Typical-starts inference | right on average; 34% over by 5+ for early-list careers | Cap at freeze |
| Trainer-change under-reaction | +0.50 kg first run, controls; largest for declining horses; trainer-specific record adds nothing | Research |
| Unfamiliar-distance breakthroughs | step-up: +0.30 at new trip, -0.01 back at old | Research (distance suitability) |
| Bent barrier shape | +0.010 kg2/run; going and field-size factors fail | Research |
| Sire debut record | 0.38 kg2 debut error; race +0.0013 (2025-26) | Candidate recommendation |

## Batch 20 (27 Nov 2026): Queensland integrity, race layer, history completeness, barriers, trainer and family
Ledger: research/batch20/README.md. Report: https://claude.ai/artifact/P4agrYWSvsCaJZViC3kv47. Harness now on production speed figures.

| Finding | Evidence | Status |
|---|---|---|
| Qld 55% start-count excess | form-enrichment counted RQ scratchings; 55.2% -> 0.0% after fix; frames clean | Resolved (measurement bug) |
| Name-key collisions | 82 keys / 1,569 runs; 56 clear two-horse cases; sandbox mean 1.02 kg on affected | Correction plan (Monday, consequences first) |
| History-completeness experience rule | +0.0010 / +0.0008 over age-aware | Candidate; freeze Monday |
| Race layer x inexperience / uncertainty | -0.0005 / 0.0000 per race | Rejected (simplest forms) |
| Overconfidence location | race calibration 0.90 established vs 0.99 inexperienced | Meaningful, descriptive |
| Certainty-weighted reference | +0.0014 both periods on production figures | Candidate |
| Pooled barrier expectation | Qld replace +0.0022 / +0.0018; SA +0.0010 | Candidate; needs pre-race rail |
| Trainer early improvement | 0.17 kg/kg after controls; harness 0.0000 | Research only |
| Sire's earlier debutants | 0.33 kg2 debut error after trainer readiness | Research (no breeding input approved) |
| First-up own record | 0.14 beyond fitness terms; harness not clear | Research trait |

## Batch 19 (27 Nov 2026): emergencies, age-aware and trainer debut shadows, age vs experience, barriers, family
Ledger: research/batch19/README.md. Report: https://claude.ai/artifact/Ltm6Q4hqN29FCehH9YzaBa. Baseline record: research/batch19/BASELINE_CORRECTION.md.

| Finding | Evidence | Status |
|---|---|---|
| National emergency gained-start count rule | 26 Nov 11/11; 27 Nov replay 45 added, off = production | Approved; switch on if 27 Nov verifies |
| Age-aware update rule (frozen) | release chain parity 0.0; dry run 435 runners | SHADOW from 29 Nov |
| Trainer debut record, genuine debutants (frozen) | built check +0.0014; debut races +0.0077; debut error -0.24 kg2 | SHADOW from 29 Nov |
| Experience over age | completeness floor +0.0008 over age rule (pre-stated); TAB: 28 of 30 lightly-held 5yo+ truly lightly raced | DECISION: completeness version |
| Individual vs race accuracy | 1.8x taper best individually; maiden rating spread over-read | DECISION: race-layer test |
| Established one-offs fade | 9% kept over 5 starts at 20+ starts held | MEANINGFUL, descriptive |
| Barrier hierarchy | pooled course x distance x rail +0.041 kg2/run over national; stable | DECISION: pre-race input test |
| Lane bias vs ground and tempo | unchanged by controls; candidates SA +0.0013, Qld +0.0009 | BUILT; shadow later |
| Family signals | +0.131 kg2 combined on debut error | Research (no breeding input approved) |
| Sire maturity out of cohort | +0.24 (-0.12 to +0.60) | Not supported as an input |
| Trainer development patterns | persistence r 0.54; ready-on-debut vs improvers -0.37 | Candidate idea |
| Fresh-horse trait | repeat corr 0.033 (chance p95 0.013) | Small; spacing preferences noise |

## Batch 18 (27 Nov 2026): production corrections, scratchings, experience, sustainability, lane bias, trainer debuts
Ledger: research/batch18/README.md. Report: https://claude.ai/artifact/UHk9gNXhht3HV3DVa8roVf. Production corrections A1-A3 effective
28 Nov 7:30am (approved); dashboard common scale A4 (display). Batch 17 ledger: research/batch17/README.md.

| Finding | Evidence | Status |
|---|---|---|
| First-starter age/sex, metro definition, Qld course names | replays: 49 filled; SA/WA metro identical; Qld track history 0% -> 73%, Cairns course records 0% -> 88% | PRODUCTION from 28 Nov (switch files) |
| Non-scratch TAB statuses shown as scratched | 41 Cairns "Reserve" runners (display only) | FIXED at root |
| National emergencies that gain a start not scored | 26 Nov 3 incomplete races; 27 Nov 47 unscored | DECISION |
| Qld shadows' emergency rule | 126/126 runners after fix (was 117) | FIXED |
| Age floor on the experience taper (5yo+ exposed) | vs taper +0.0018 / +0.0025 (pre-stated test) | MEANINGFUL |
| Age-aware taper limited to 1.3x | vs uniform 1.3x +0.0017 / +0.0046 (diagnostic; both periods seen) | DECISION: new frozen shadow |
| Research harness baseline | hooks-off sandbox -0.0009 / -0.0002 vs production frame (figure tables) | Use hooks-off baseline; earlier "vs v2.3" gains slightly understated |
| Sustainability of exceptional runs | emerging keep ~61%; exposed 38% -> 28%; one-offs 33% -> 27% | MEANINGFUL, descriptive |
| Race-level-only heavy-defeat cap | +0.0022 / -0.0016 (vs hooks-off) | Not useful alone |
| Same-day lane bias, Qld and SA | Qld +0.35, SA +0.59 per kg; next run -0.13 / -0.26; removing it: SA 2025-26 +0.0013 (clean), Qld +0.0002 to +0.0008 | SMALL GENUINE GAIN; DECISION (shadow candidate) |
| Trainer debut record | +0.0010 / +0.0020; first-starter races +0.0036 / +0.0086; persistence r 0.38 | DECISION (not authorised) |
| "Rarely debuts twos" selectivity proxy | their 2yo debutants -0.62 kg | Opposite of hypothesis |
| Sire maturity with continuation | Per Incanto 86% continue, +2.36 kg vs 78%, +1.14 | MEANINGFUL, descriptive |

## Batch 16 (27 Nov 2026): rating foundations, national comparability, individual horse intelligence
Ledger: research/batch16/README.md. Two shadows added (update rule, cap only); no production change.

| Finding | Evidence | Status |
|---|---|---|
| Update rule as built by the release chain | 2025-26 +0.0059 (0.0043-0.0076) vs v2.3 as built, every state positive, top pick unchanged; cap only +0.0043; 1.3x adds +0.0016 | SHADOW from 28 Nov (with cap-only comparator); promotion on prospective races |
| The rule halves each known learning bias without propping up decliners | moderate poor run -0.61 -> -0.28; good run +1.20 -> +0.89; third poor run -0.25 -> -0.13 (cap only -0.40) | MEANINGFUL |
| One heavy defeat flatters the rest of the field | others next run -0.58 kg (-0.62 to -0.53), 15% of races; -0.25 under the rule | MEANINGFUL; addressed by the rule |
| Race level weighted by rating certainty | alone +0.0006 n.s. / +0.0011; on top of the rule +0.0005 / +0.0004 (both clear) | CANDIDATE for the rule's next refit |
| Races of unexposed horses share their error | shared sd 0.45 kg (established fields) vs 1.19 (least certain); maidens 0.98 | MEANINGFUL, descriptive |
| Erratic horses' big runs under-believed | +0.73 kg after controls under v2.3; gone under the rule (+0.01) | Explained by the rule |
| Repeated best vs one-off peak | 0.11-0.13 vs 0.04-0.05 kg per kg | Redundant (engine already carries it) |
| Distance suitability from the horse's own runs | +0.19-0.21 kg per kg at rating level; engine gain 0.0000 | Redundant |
| Trainer change | first run -0.38 kg; receiving-trainer uplift persists (r 0.58, 57 trainers) | Decision: trainer-specific transfer term |
| State seconds per length | Qld 0.170, SA 0.1595, Vic 0.162; standardising -0.0012 / -0.0006 | REJECTED (no state corrections) |
| Interstate rating offsets | SA ~0.5 kg high vs Vic, Qld ~0.4 vs NSW, Tas ~1.5 vs Vic; engine term +0.0004 n.s. | Already priced; no correction |
| Qld configurations vs v2.1.3 structure | common +0.0235 / +0.0160; + rule +0.0314 / +0.0204; rule alone +0.0096 / +0.0081; standardised +0.0005 / +0.0007 | Daily shadow to build (configs 4 and 2) |
| bm_change | serving it -0.0012 / -0.0007; retraining without it -0.0008 / -0.0005 | Keep as training-only control (reverses B15 plan) |
| Age & sex for first starters | missing live 9.2% vs 0.5% in training | Decision: serve from TAB's field |
| Course geometry x late speed | -0.04 then +0.01 per 100 m | REJECTED |

## Batch 15 (27 Nov 2026): rating foundations, physical profiles, small improvements
Ledger: research/batch15/README.md. Research only; no production change.

| Finding | Evidence | Status |
|---|---|---|
| Rating update rule: cap heavy defeats at 10-12 L and let good runs move the rating 1.3x | Engine v2.3 refitted: +0.0071 (0.0051-0.0092) 2024, +0.0055 (0.0038-0.0072) 2025-26; cap alone +0.0064/+0.0040; plateau 10-12 L; rating accuracy +0.0104/+0.0096 per run, stability unchanged | CANDIDATE for a shadow (chosen with sight of both periods: prospective evidence needed). Decision: Damo |
| The rating learns unevenly | good runs: next +0.6 to +2.3 kg above the raised rating; narrow defeats under-weighted (1.2-1.6x), 10-25 L over-weighted (0.79x), one-off poor run after a good run 0.64x | MEANINGFUL (drives the candidate above) |
| Beating a lowered rating is not recovery | after 10+ kg-worse runs: next +0.66 vs revised but -4.3 vs pre-run rating over 5 starts | MEANINGFUL, descriptive |
| Heavy defeats with an abnormal late decline are partly temporary | +0.95 next vs -0.54 for normal-shape heavy defeats; +0.36 (0.11-0.62) holding defeat size; Qld progressive fade + vet finding +1.64 (1.25-2.03) | MEANINGFUL against the rating; physical data only in Qld/SA |
| Official margins are clock-derived; states convert differently | within-race r 1.000 (Qld, SA), 0.9997 (Vic); 0.170 / 0.159 / 0.162 s per length | MEANINGFUL; national comparability lead (OPEN: state-specific conversion) |
| Handicap weight slope (Benchmark races) in release-build form | +0.0005 (0.0003-0.0007) 2024 clean; +0.0015 (0.0011-0.0018) 2025-26 | CANDIDATE built (benchmarks/engine_v2_4_candidate); needs race class at race time (TAB raceClassConditions) |
| bm_change never served at race time | 0 of 67 runners today; serving it would cost -0.0008 (0.0004-0.0013) | Train/serve gap; keep unserved; drop from training at next release (decision) |
| Rider momentum tables | 120 riders; trainer-half r 0.57 / 0.61; no rider with 60+ rides in both states | Descriptive; frozen table for the prospective check |
| Workload artifact audit | corrected control changes nothing material | Closed |
