# Batch 3 plan (written 24 Nov 2026, before any batch 3 analysis ran)

No prices, odds or market-derived inputs. Pre-race inputs come only from earlier runs (including their sectionals)
or from the published field. The 49-hypothesis register and its revision log stay as they are.

## Labels
- Chronological out-of-sample (Qld): fit before 2025, score 2025-26. Not independent: that period informed earlier work.
- Independent interstate replication: NSW/ACT/Vic Breednet results (never used to form any hypothesis), fit before 2025,
  score 2025-26. NSW form lines, where used, are survivor-biased and labelled so.
- Prospective: Queensland races from 25 Nov 2026, scored later with these definitions.

## Uncertainty (applies to every comparison)
Per-race differences in fit (log-likelihood of the winner) and top-pick hits. Intervals by bootstrap over meetings
(1,000) and, as a check for time dependence and the same horses racing within weeks, over calendar months (1,000).
A result counts only if both intervals agree on the sign. Runner-level regressions use horse-clustered errors.

## Benchmark
The batch 2 combined model is frozen as `benchmarks/combined_v1` (feature list, definitions, development coefficients,
code hashes). Every new idea is scored against it on the same races.

## Study 6. Pace-adjusted figures (Queensland, where individual sectionals exist)
Race early tempo: the leader's elapsed time at 600m to go, against the development-period par for that track and
distance, less the day's track variant (seconds per km of the early section; + = slower than usual).
- PA1 tempo-corrected figure: each runner's time is corrected for the part of the early-tempo effect on final time that
  is not made up late: corrected time = run time - c x early excess, where c is the slope of winners' time residual
  (after par, variant, class) on early excess, fitted on development races. Then the figure is recomputed as in v0.
- PA2 late-section figure: each runner's last 600m against the par last 600m for that track and distance, adjusted for
  the race's early tempo (slope fitted on development races), converted to kg with the v0 length scale; the blended
  figure = 0.5 x v0 figure + 0.5 x late-section figure.
- Run profile (fast-early vs fast-late): for the last start, the early component (time to 600m to go vs par, own run)
  and the late component (last 600m vs tempo-expected), entered separately.
Pre-race measures use the batch 2 recency weights (1, .7, .5, .35, .25, .18) over the last 6 runs.
Primary tests (chronological out-of-sample, within-race models, all eligible races, missing flagged):
- P1: recency-weighted PA1 alone beats recency-weighted v0 alone in races of 1400m+.
- P2: the same in all races.
- P3: in the frozen benchmark, PA1 in place of the v0 figure improves fit in 1400m+ races.
- P4: in the frozen benchmark, PA1 in place of v0 improves fit in metro races.
- P5: the late-section figure (PA2 component) adds beyond the v0 figure in the benchmark, 1400m+.
Secondary: blended PA2 alone; run-profile components; fast-early vs fast-late figure comparison; sprints.

## Study 7. R20 and a national rating scale (after the backfill)
Within-venue figures for every state from race time and margins (pars per track and distance, daily variant, no class
allowance). Venue offsets estimated from horses that run at two venues within 60 days (least squares on the change in
figure, Eagle Farm = 0). National figure = within-venue figure + venue offset.
Primary P6: winners of the same benchmark band (58, 64, 72, 78, 84+) run different national figures across Qld, NSW,
Vic (state differences estimated with track tier, distance band and going held steady; interval excludes 0 for any band).
Secondary: by venue tier; check that offsets are stable when estimated from 2022-24 vs 2025-26 shippers.

## Study 8. National replication of the evidence groups (after the backfill)
Common-feature model (identical definitions in every state): simple form F; ability A (recency-weighted national
figure, strength of fields met, weight vs field); fitness R (days since, first-up, quick back-up). Race shape needs
prior settling positions and barriers, which Breednet lacks: tested only where Racing NSW form lines provide them,
reported separately as an enhanced subset.
Primary P7: A adds beyond F and R in NSW/Vic metro races; P8: R adds beyond F and A in NSW/Vic metro races.
Secondary: provincial and country; the same common-feature model in Queensland for a like-for-like comparison;
missing-data rates per feature per state.

## Study 9. Cross-state transfer (after the backfill)
Horses with consecutive starts in different states within 60 days. Does the national figure from the first state predict
the run in the second state as well as within-state consecutive runs predict each other (correlation of consecutive
figures; and the conditional-logit coefficient of the pre-race national figure for shippers vs non-shippers)?
Primary P9: the national figure's coefficient for interstate shippers is not lower than for horses staying in state
(interval for the ratio includes 1 or above).

## Multiple testing
P1-P9 adjusted together (Benjamini-Hochberg, 10%). Studies 7-9 run only if the backfill completes; if a study cannot
run, its tests are dropped from the family and that is reported.
