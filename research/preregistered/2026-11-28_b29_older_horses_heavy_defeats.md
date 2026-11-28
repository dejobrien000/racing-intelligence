# Preregistration: older-horse terms (prospective) and heavy-defeat responsiveness (Batch 29, 28 Nov 2026)

Written 28 Nov 2026 before any of the tests below were run. Approved in principle by Damo (Batch 29 s3).
Not to be edited after the first result exists; amendments are added as dated notes at the end.

## Part A. Older-horse terms: prospective test only

**Background.** In Batch 28, two terms reduced the consolidated rating's overrating of established older horses:
+0.0005 per race (2024) and +0.0013 per race (2025-26). They were designed after looking at 2025-26 breakdowns. Neither
period is therefore independent evidence, and both are treated as development data.

**Definitions** (unchanged from Batch 28; computed from the horse's earlier held runs only):

- **Established** = 15 or more held runs before today, and aged 5 or over.
- **est_below_peak** = (highest pre-race rating the horse carried into any earlier held run) minus (pre-race rating today).
  Applies to established horses only; 0 otherwise.
- **est_trend6** = (pre-race rating today) minus (pre-race rating carried into the run 6 held runs earlier).
  Applies to established horses only; 0 otherwise.

**Candidate.** Engine v2.5 with both terms added to its third layer and nothing else changed:

- Ratings, layers 1-2 and the 14 existing third-layer terms are as released.
- Coefficients are fitted on all races to the release history cutoff.
- It is built through the release chain and scored as a shadow (not live).

**Prospective record.** Races run from the shadow's first morning (30 Nov 2026), scored before the start and settled afterwards:

- **Primary.** Gain in log-likelihood per race vs Engine v2.5, on the same races, with a 95% bootstrap interval.
  It is reviewed at 300, 1,000 and 2,000 paired races.
- **Secondary** (reported, not used to decide):
    - actual/expected wins for established 5yo+ horses, split by the Batch 28 groups: near own peak, rising trend, top quarter of the field
    - top pick won
    - winner in top 3
- **Decision rule.** Recommend release only if the 95% interval is entirely above 0 at 1,000 or more paired races. Below 1,000
  races, no recommendation either way. A checkpoint is a review, never an automatic promotion.
- **Excluded.** No re-use of 2024 or 2025-26 as confirmation. No change to the definitions after the first prospective result.
  No blanket age deduction.

## Part B. Heavy-defeat responsiveness (historical, staged)

**Observation that prompted it** (Batch 28; seen on 2025-26, so not usable as confirmation). After defeats of more than
12 lengths, established older horses are overrated at their next run:

- by 0.51 kg under Engine v2.5
- by 0.07 kg under v2.3

The 12-length cap in v2.5 may protect some declining horses too generously.

**Staging** (fixed now):

1. **Development (races to 31 Dec 2023).** All description and mechanism design. Only this period may be used to choose groups,
   thresholds or any rule.
2. **Confirmation (2024).** One pre-stated comparison per hypothesis below, with no re-tuning.
3. **2025-26.** Reported for completeness, labelled as previously seen. It is never called independent confirmation.

**Target.** The next-run surprise (innovation against the rating carried in) for runs that follow a defeat of more than 12 lengths.
Ratings are Engine v2.5's. The reference group is next runs after a defeat of 6-12 lengths.

**Hypotheses** (each split stated in advance):

- **H1. Isolated vs repeated.** A >12 L defeat that follows another >12 L defeat within the horse's previous 3 runs is followed by
  a larger overrating than an isolated one.
- **H2. Trajectory.** Overrating is larger when the 6-run rating trend before the defeat was falling (≤ -0.5 kg) than when it was
  flat or rising.
- **H3. Experience.** Overrating is larger for horses with 30+ held runs than with 15-29.
- **H4. Previous recovery.** Horses whose earlier poor runs (surprise ≤ -3 kg) were followed by recovery (next surprise ≥ 0) at
  least half the time are less overrated than horses that recovered less than half the time. Only earlier pairs count.
- **H5. Time since last strong run.** Overrating is larger when the horse's last run within 1 kg of its own peak was 8 or more runs
  ago than 1-3 runs ago.
- **H6. Preparation and absence.** A >12 L defeat first-up after 120+ days is followed by less overrating than one deeper in a
  preparation. The comparison is third-up or later vs first-up.
- **H7. Distance.** A >12 L defeat at a distance where the horse's distance-specific suitability was ≤ -1 kg is followed by less
  overrating than one at a suitable distance. Here the defeat is partly explained by the trip, not decline.
- **H8. Physical deterioration.** Only where tracking exists (Qld; SA from 2024), the latest closing-sectional figure is compared
  with the horse's own earlier median. This is descriptive only, because coverage is too thin for a rule.

**Mechanism candidates.** These are built only if H1, H2 or H5 holds in development AND confirms in 2024:

- **(a)** Apply the 12 L cap to an isolated heavy defeat. Count a second heavy defeat within 3 runs uncapped (or capped at 20 L).
- **(b)** Make the heavy-defeat credit depend on the falling trend from H2.

Each candidate is a rating-level change, rebuilt through the full release chain. It is judged on 2024 races not used to fit any
layer, and then, if it passes, as a prospective shadow. Removal tests are not proof of no interaction.

**Not allowed:**

- a blanket age deduction
- generic excuses for poor runs
- inferring injury or fitness from time between races
- fitting a rule to the 2025-26 weakness and describing 2025-26 as confirmation
