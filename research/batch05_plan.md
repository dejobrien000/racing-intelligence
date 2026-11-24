# Batch 5 plan: course conditions and horse-course compatibility (fixed 24 Nov 2026, before any Batch 5 analysis)

Question: once a horse's opposition-aware ability is known, do local conditions change outcomes, and do particular
horses suit particular courses, goings or distances? A local effect is not required to exist; "no effect beyond the
pool" is an acceptable answer.

## Baselines (frozen, never refitted here)
- Queensland tracked races: frozen candidate "combined_v1 + national dynamic rating"
  (benchmarks/candidates_b4_national/manifest.json) as a fixed offset for every runner.
- NSW/Vic/ACT (Breednet full fields, jump-outs excluded): common-feature model F + A + R + national dynamic rating,
  fitted on development races, used as a fixed offset.
- Development = races before 1 Jan 2025; scoring = 1 Jan 2025 to 23 Nov 2026 (chronological out-of-sample).
- Local terms are estimated by penalised within-race logit (Gaussian prior on each course deviation, centred on the
  pooled value). This is the most likely value of a hierarchical model with uncertainty from the curvature (Laplace),
  an approximation, not a full Bayesian posterior. The prior spread is chosen by fitting Oct 2022-Dec 2023 and scoring
  2024. Course configurations are kept separate (Sunshine Coast turf vs Polytrack; Sandown Hillside vs Lakeside etc.).

## Studies
- Study 13, course x going (Qld): (a) course deviations of the horse's going-suitability term (t_going);
  (b) course x going band (good / soft / heavy) deviations of the usual-running-position term.
- Study 14, course x early pace and running style (Qld): (a) course deviations of usual running position (p_style);
  (b) course deviations of the leader x other-leaders (pace pressure) term.
- Study 15, horse late speed x course (Qld): (a) course deviations of the horse's recent closing-sectional term
  (s_gap600_avg3). (b) Secondary, only once a course geometry table (straight length, circumference) is compiled from
  published sources: is the late-speed effect larger at longer-straight courses?
- Study 16, horse performance relative to its rating at particular courses: each run's "surprise" is the dynamic
  rating's own innovation (performance relative to the field minus what the pre-race ratings expected). A horse's
  course record = its earlier surprises at today's course, shrunk towards zero by n / (n + k), k chosen on the inner
  split. Point-in-time: only runs before the race date. Qld (offset baseline) and NSW/Vic (common model).
- Study 17, suitability beyond the national rating: the same shrunk surprise records for today's going band and
  today's distance band, plus "home track" (the course where the horse has raced most, to date).

## Primary tests (fit gain per race, intervals over meetings and calendar months, both must agree; BH 10%)
- P1 13a course x going-suitability beats pooled (Qld).
- P2 14a course x running position beats pooled (Qld).
- P3 14b course x pace pressure beats pooled (Qld).
- P4 15a course x late speed beats pooled (Qld).
- P5 16 horse-course record adds beyond the baseline (Qld).
- P6 16 horse-course record adds beyond the baseline (NSW/Vic).
- P7 17 going-band and distance-band records add beyond the baseline (Qld).
- P8 17 going-band and distance-band records add beyond the baseline (NSW/Vic).

## Secondary (reported, not tested)
Eagle Farm + Doomben subsets; course tables with estimate, uncertainty and share kept after pooling; stability between
the two development halves; home track; 13b; 15b.

## Protection
No race on or after 25 Nov 2026 is used. Anything that passes is frozen and must also pass on the timestamped pre-race
predictions before it can enter rankings.
