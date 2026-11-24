# Batch 2 plan (written 24 Nov 2026, before any batch 2 analysis ran)

No prices, odds or market-derived inputs. Every pre-race input comes from runs before the race, or from what is
published before the race (today's distance, track, going, barrier, weight, field).

## Validity labels used in every study
- Exploratory: patterns found or examined on the data being described.
- Chronological out-of-sample: model fitted on races before 1 Jan 2025, scored on 1 Jan 2025 - 23 Nov 2026. Those races
  have informed earlier research, so this is NOT independent validation.
- Independent interstate replication: NSW/Vic data not used to form the hypothesis (form lines are survivor-biased).
- Prospective: Queensland races from 25 Nov 2026 onward, scored later with definitions frozen here.

## Common methods
- Unit: a runner in a race; model: conditional logit within race (each race's runners compete for one win), so
  correlated runners within a race are handled by design. Same horse across races: bootstrap by meeting for differences;
  horse-clustered errors where a runner-level regression is used.
- Population: Queensland TAB races (RQ tracking), fields 6+, one winner. All eligible races, not only complete-figure
  races: a missing input is set to the race average and flagged (missing indicator) so selection is not forced.
- Fit on development races (before 2025); score on the out-of-sample period. Figures from `runs_rated_dev.parquet`
  (pars and class allowances from pre-2025 races only).
- Fit measure: out-of-sample log-likelihood per race vs equal chances ("fit %"); top-pick win %; 95% bootstrap intervals
  over meetings (1,000 resamples) for differences.
- Multiple testing: primary tests P1-P9 adjusted together (Benjamini-Hochberg, 10%). Secondary results are descriptive.

## Study 1. Rating variants (why the figure trails simple form)
Variants (all pre-race, each the horse's previous Queensland figures): V1 best of last 3; V2 last; V3 average of last 3
(current best); V4 recency-weighted (weights 1, 0.7, 0.5, 0.35, 0.25, 0.18 over the last 6); V5 shrunk towards the class
of each past race (class level + 0.5 x (figure - class level)), then averaged over 3; V6 opposition-adjusted (figure +
0.5 x (field strength - class level)), averaged over 3; V7 weight-for-age: figures from 2YO/3YO-restricted races
adjusted by the median gap to open-age races in the same month of the season (fitted on development races; age is not
otherwise known for Queensland runners, a stated limitation); V8 = V3 plus today's weight relative to the field
(handicaps; fitted combination). Baseline: average finishing position over the last 3 (B).
Primary test P1: does the best pre-specified variant (chosen on development fit, not on the scoring period) match or beat
B on out-of-sample fit and top-pick %, on matched races (the same races for both)? Report the difference with its interval.
Secondary: diagnostics of where the figure loses ground (distance, going, venue tier, margin size, first-up); the
complete-figure selection (why only ~26% of races qualify and how those races differ).

## Study 2. Evidence groups (independent predictive information)
Groups (pre-race):
- F simple form: average finishing position last 3, last finishing position, last margin, career win %, number of starts.
- A ability and opposition: average figure last 3 (V3), best figure, average field strength faced last 3 (R18), today's
  class level minus the horse's average figure, weight today relative to field.
- S sectional: last-start gap to the race's best last 600m, average of that over 3 starts, last-start top-3 last 600m,
  last-start gap to the best last 200m (R23), last-start finishing speed relative to the race.
- P predicted race shape: usual settling position (last 3), number of habitual leaders among the other runners (R28), lone
  habitual leader (R29), relative barrier, barrier x usual position, leader x pace pressure.
- T track and distance: starts and win rate at the track, at today's distance band, at the track and distance (shrunk);
  figure on today's going group minus the horse's average figure (R31); distance change from last start.
- R fitness and recency: days since last run (bands), first-up, run number in the preparation, quick back-up (10 days or less).
Primary tests (each: out-of-sample fit gain, interval excludes 0):
- P2-P6: each group adds information beyond F and all other groups (full model vs full model without that group), for A, S, P, T, R.
- P7: one combined model vs separate group profiles combined afterwards (stacked: each group's own score, weighted on
  development data). Two-sided: which fits better out-of-sample.
- P8: race-shape interactions (barrier x usual position, leader x pace pressure, lone leader) add beyond race-shape main effects.
- P9: a tree model (gradient-boosted, race-relative inputs) beats the combined conditional-logit model out-of-sample.
Secondary: each group alone and each group added to F; agreement (win % when 1, 2, 3+ groups' own top picks coincide);
R23 last-200m term inside S; R40 (field-strength change vs class-label change for next-start results); metro-only results.
Deferred to batch 3: R20 (needs the finished NSW/Vic backfill), R24, R26, R27.
