# Batch 4 plan: first course-specific research (written 24 Nov 2026 ~19:20, before any batch 4 analysis ran)

No prices, odds or market-derived inputs (checked: no price fields or price text in any table on 24 Nov).
Everything pre-race comes from earlier runs or the published field. combined_v1 stays frozen and is the baseline.

## Labels
Descriptive / exploratory / chronological out-of-sample (Qld 2025-26, already examined, NOT untouched) /
independent replication (NSW/Vic, not used to form these ideas) / prospective (races from 25 Nov 2026, scored later
with the frozen definitions below; predictions saved with a timestamp before results are known).

## Study 10. Course-specific barrier x expected running style (Queensland, all tracked courses)
Baseline offset: the combined_v1 score for each runner (fitted on development races), so every local effect is
measured after horse ability, form, opposition, fitness and the pooled race-shape terms.
Local terms, per course configuration (Eagle Farm, Doomben, Sunshine Coast turf, Sunshine Coast Polytrack, Ipswich,
Toowoomba, and every other tracked course): (i) relative barrier (inside = +), (ii) relative barrier x usual running
position (from the horse's previous 3 runs).
Candidates (fitted on races before 2025, scored on 2025-26):
- A pooled: combined_v1 alone (already contains the pooled barrier and barrier x style terms).
- C independent course models: course deviations fitted with no pooling (courses with 150+ development races; others 0).
- D hierarchical partial pooling: the same deviations with a Gaussian prior centred on the pooled value
  (penalised likelihood; the prior spread tau chosen by fitting on Oct 2022-Dec 2023 and scoring on 2024, inside the
  development period only), so a course departs from the pool only as far as its own evidence supports.
- E: D plus course x distance-band deviations (<=1150, 1200-1450, 1500-1750, 1800+), nested and partially pooled.
- Rail: D plus a course-specific slope of barrier x rail distance out (metres from the true position).
Primary tests (fit gain per race, intervals over meetings and calendar months, both must agree):
P1 D beats A on all Queensland tracked races. P2 D beats C. P3 D beats A on Eagle Farm + Doomben races.
P4 E beats D. P5 Rail beats D.
Secondary: course-by-course estimates with uncertainty and shrinkage; stability (Oct 2022-Dec 2023 vs 2024 fits);
fit gain by course and race type; whether any course departs clearly (95% interval) from the pool.

## Study 11 (secondary, descriptive in this batch). Does the last-start closing sectional mean the same at every course?
Course of the LAST start x last-start closing-sectional gap, hierarchical as in D, same baseline. Reported only.

## Study 12 (prototype). Point-in-time dynamic opposition rating
Race-by-race in date order: each horse has a current ability estimate and uncertainty. After each race, every
runner's estimate moves towards its observed performance relative to the field (margins converted to kg, weight
allowed for), judged against the current estimates of the horses it actually met. Uncertainty grows with time off.
Only information up to the day before the race is ever used. Compared, within race, with the recency-weighted v0 and
PA1 figures and inside combined_v1 (chronological out-of-sample; national version after the backfill).

## Prospective protection
The candidates fitted here are frozen with hashes; predictions for races from 25 Nov 2026 are written to
`prospective/` with a timestamp before results exist and are never refitted on those races.
