# Batch 7: Rating engine v2

Written 25 Nov 2026, 12:30–1:30am, before any 25 Nov race. Prices are not used anywhere. Everything earlier is kept: the 49-hypothesis register (now R1–R68), the frozen benchmarks and v1, which is still scored every day alongside v2.

## 1. Operations: what is and isn't working

| Piece | Status | Detail |
| --- | --- | --- |
| Qld morning fields | **Working** | Ipswich 25 Nov captured 9:34pm and scored by v1. Engine v2 re-scored it at 12:27am. |
| NSW morning fields | **Working** | Wyong 25 Nov captured and scored by v1 and v2. Hawkesbury 26 Nov fields are also captured. |
| Vic morning fields | **Not built** | Three routes tried tonight: racing.com needs Chrome (not connected); Racing Australia blocks automated fetching (robots.txt); the Racing NSW mirror lists NSW only. Next: read racing.com's rendered pages through Chrome. |
| Engine v2 scoring + daily ranking | **Working (new)** | Both meetings scored before racing, with v1 kept alongside. |
| Your PC at 12:30am | **Offline** | The desktop app and the Chrome extension weren't connected. The 6:31am collection and the 8:05am post-scratchings re-score both need the PC on with Chrome open. If it's off they fail, and the failure is reported, never back-filled. |
| Results, then evaluation | Scheduled 26 Nov | Evaluates v1 and v2 side by side; the first prospective result. |
| Second Breednet crawl, venue aliases | Unknown tonight | Unknown because the PC is offline. |
| Vic historical sectionals, NSW sectional sources, track geometry, gear, trials | Not started | Jockey, trainer, age and sex were investigated tonight (section 4). |

## 2. How the final rating is calculated (engine v2)

1. **Ability.** The national opposition-aware rating is rebuilt from every earlier race: margins, weights, and the ratings of the horses actually met. It is strictly point-in-time.
2. **Established features (v1).** Every runner gets the existing features: 41 for Qld (form, figures, sectionals, race shape, track history, fitness, rating) and 20 for NSW/Vic. Each feature is centred on the race and standardised. The v1 score is the sum of coefficient × feature. The coefficients were learned on development races by a within-race model.
3. **New information (v2).** v2 adds new terms on top of v1:
   - **Qld (7 terms):** horse course/going/distance records, and jockey & trainer.
   - **NSW/Vic (80 terms):** jockey & trainer, age & sex, form changes & head-to-head, and 65 interactions. The interactions were chosen on discovery data only.

   **v2 score = v1 score + Σ (coefficient × term).**
   - All new terms are estimated **together**, so overlapping terms share credit rather than double-count.
   - v1 is held fixed while they are estimated, so a new term only earns credit for what v1 doesn't already know.
   - A ridge penalty is chosen on an inner split of development races (Qld τ = 100; NSW/Vic τ = 1000). The terms are then refitted on all races to 23 Nov.
4. **Chances.** Within-race win chances come from the v2 scores (softmax).
5. **Final rating (kg-equivalent).** The v2 score is divided by the score that 1 kg of rating difference is worth on average: 0.224 for Qld, 0.226 for NSW/Vic. This is a common currency for every factor, **not** a claim that each factor is a physical kilogram. Each contribution is divided by the same number, and the breakdown adds up exactly to the final rating (checked in code on every run).
6. **Selection strength (cross-race).**
   - A calibration layer turns the model's top chance and the field size into how often such top picks actually won. It is fitted on 2025–26 v2 predictions the model wasn't fitted on.
   - The 80% band comes from 300 meeting bootstraps.
   - The labels are thirds of that history: strong, moderate, weak – no clear selection. Insufficient information applies when the top pick, or most of the field, has no prior form.
7. **Missing inputs.** A missing input gets the race-average value, so it contributes 0, and it is flagged in "evidence gaps". Nothing is invented.
8. **Course-specific.** Horse-at-course records are in. Course-level coefficients failed in Batches 4–6, so they stay pooled. Partial pooling of the new v2 terms by course is the next test.

## 3. Feature audit: the 39 operational features

Each feature and family was refit-tested on identical 2025–26 races: drop it, or use it alone. Full results are in the sheet, tab "Feature audit".

- **Strongest:**
  - **Qld:** the opposition-aware rating (+0.025 per race), then recent form (+0.008) and ability figures (+0.004).
  - **NSW/Vic:** recent form (+0.058, driven by career starts and average finishing position), the rating (+0.024) and ability figures (+0.017).
- **Redundant (useful alone, adds nothing once the rest is in):**
  - Qld closing sectionals: +0.052 alone, ≈0 in the model.
  - Weight vs field (both states).
  - Qld barrier & race shape: +0.002, interval spans 0.
  - NSW/Vic fitness.
  - NSW/Vic recency-weighted figure (a_rec): duplicated by best-of-3 and the rating.
- **Harmful (removing it improves 2025–26):**
  - The Qld track/distance/going history family (−0.003; its interval only just reaches 0). Horse records do this job better.
  - Six single Qld features: last-start finish, average of last 3 figures, average last-600m, and the missing-form, missing-figure and missing-style flags.
- **Reading:** the 41-feature Qld model, fitted on 4,819 races, overfits. v3 will refit it with a penalty and prune these terms.

## 4. Expanded discovery (screen 2: NSW/Vic, plus the faster-learning rating)

**Design**

- 225 investigations, covering:
  - new single features, including the untested jockey, trainer, age and sex families;
  - nonlinear shapes;
  - time drift;
  - feature × context;
  - pairs;
  - replications of the Qld findings.
- Each one is a single term on top of the frozen NSW/Vic model:
  - **Discovery:** 20,406 races, Oct 2022–Dec 2024, with BH at 10% and the same sign in both halves.
  - **Confirmation:** 16,489 races in 2025–26, coefficient fixed, meeting bootstrap.
- **Results:**
  - 111 passed discovery.
  - **66 passed both stages.**
  - 88 were positive in confirmation, against about 6 expected by chance.

| # | Investigation | Effect per sd (se) | Out-of-sample gain per race (95%) | Top pick | Verdict |
| --- | --- | --- | --- | --- | --- |
| 1 | Trainer's earlier runners beat their ratings | +0.245 (0.008) | +0.0214 (0.0180 to 0.0246) | +0.75 | **Passed** → v2 |
| 2 | Jockey's earlier mounts beat their ratings | +0.202 (0.007) | +0.0163 (0.0130 to 0.0195) | +0.53 | **Passed** → v2 |
| 3 | Jockey–trainer combination | +0.155 (0.007) | +0.0156 (0.0127 to 0.0187) | +0.70 | Passed, overlaps 1–2 |
| 4 | Jockey upgrade vs last start | +0.103 (0.007) | +0.0047 (0.0031 to 0.0064) | +0.12 | Passed → v2 |
| 5 | Age: older horses run below their rating | −0.243 (0.009) | +0.0129 (0.0099 to 0.0165) | +0.61 | **Passed** → v2 |
| 6 | 3-year-olds and younger run above it | +0.153 (0.007) | +0.0062 (0.0038 to 0.0085) | +0.01 | Passed → v2 |
| 7 | Mares and fillies | +0.053 (0.007) | +0.0022 (0.0015 to 0.0031) | +0.16 | Passed, small |
| 8 | Head-to-head vs today's actual rivals | +0.056 (0.007) | +0.0016 (0.0006 to 0.0026) | +0.21 | Passed (replicates the Qld watch list) |
| 9 | Size of the distance change | −0.048 (0.008) | +0.0014 (0.0008 to 0.0020) | +0.03 | Passed, small |
| 10 | Ability separates horses less in strong fields | −0.036 (0.008) | +0.0012 (0.0004 to 0.0020) | +0.10 | Passed (replicates Qld #12) |
| 11 | Lightly raced horses that have met strong fields | +0.044 (0.007) | +0.0027 (0.0019 to 0.0035) | +0.20 | Passed |
| 12 | Jockey/trainer edge larger in Vic, wet, 1400m+, big fields | +0.12 to +0.19 | +0.005 to +0.010 each | +0.1 to +0.5 | Passed (context; shares credit with 1–2) |
| 13 | Recent-form weight rising year by year | +0.033 (0.008) | +0.0016 (0.0010 to 0.0023) | +0.02 | Passed: a stability warning |
| 14 | Last-start surprise (the Qld improvement theme) | −0.020 (0.008) | −0.0005 (−0.0008 to −0.0002) | +0.05 | **Failed**: opposite sign nationally |
| 15 | Benchmark (class) step beyond ratings | −0.051 (0.007) | −0.0010 (−0.0018 to −0.0002) | −0.04 | **Failed** confirmation |
| 16 | Faster-learning rating (corroborated improvement) | λ 0.25 (dev-tuned) | Qld +0.0022 (0.0010 to 0.0033); NSW/Vic −0.0004 (−0.0009 to +0.0001) | Qld +0.17 | **Mixed**: not released |
| 17 | Course record × wet going (Qld #7) | +0.008 (0.008) | +0.0001 (−0.0001 to +0.0002) | +0.07 | Not replicated |

- **Leakage guard:** the jockey and trainer measures use only earlier days. Rebuilt from rides at least 28 days old, the trainer effect barely moves (+0.0214 → +0.0208), so it isn't leaking same-week information.
- **Real-world reading:**
  - The rating can't see who trains or rides a horse, or how old it is.
  - Stables whose horses are improving or well placed beat their ratings repeatedly.
  - Older horses decline faster than the rating learns.
- **Faster-learning rating, answered:** the Batch 6 "corroborated improvement" signal is better captured by features than by a revised rating. The revised rating helps Qld (where pace figures corroborate) but not NSW/Vic, so the frozen rating stays.

## 5. Cumulative improvement on identical races (2025–26)

**Queensland (4,730 races)**

| Version | Fit | Top pick wins | Winner in top 3 | Ordering | Step gain per race (95%) |
| --- | --- | --- | --- | --- | --- |
| Original combined model | 6.40% | 22.6% | 53.6% | 0.312 | – |
| + opposition-aware rating (v1) | 7.51% | 23.6% | 54.8% | 0.335 | +0.025 (0.018 to 0.033) |
| + horse course/going/distance records | 7.72% | 23.8% | 55.0% | 0.342 | +0.0046 (0.0020 to 0.0070) |
| + jockey & trainer (= **v2**) | **9.37%** | **25.4%** | **57.8%** | **0.373** | +0.037 (0.028 to 0.046) |

**NSW / Vic / ACT (16,489 races)**

| Version | Fit | Top pick wins | Winner in top 3 | Ordering | Step gain per race (95%) |
| --- | --- | --- | --- | --- | --- |
| Common features only | 8.96% | 24.9% | 56.2% | 0.335 | – |
| + opposition-aware rating | 10.07% | 25.5% | – | – | – |
| + horse records (v1) | 10.27% | 25.9% | 57.2% | 0.356 | +0.0043 (0.0030 to 0.0056) |
| + jockey & trainer | 11.70% | 27.0% | 59.7% | 0.384 | +0.032 (0.028 to 0.036) |
| + age & sex | 11.99% | 27.5% | 60.0% | 0.386 | +0.0067 (0.0044 to 0.0091) |
| + form changes & head-to-head | 12.02% | 27.5% | 60.0% | 0.388 | +0.0007 (−0.0009 to +0.0024) |
| + interactions (= **v2**) | **12.30%** | **28.1%** | **60.6%** | **0.398** | +0.0063 (0.0035 to 0.0092) |

- **Not additive:**
  - NSW/Vic: each family alone on top of v1 adds +0.032, +0.015, +0.003 and +0.032. Those sum to +0.083 per race, but **together they add +0.046**, because they overlap.
  - Qld: +0.045 summed vs +0.041 together.
  - The joint fit prevents the double counting.
- **Rolling-origin backtest.** Old features and new terms are re-estimated from scratch each window:

| Test year | Qld gain per race (95%) | Qld top pick | NSW/Vic gain per race (95%) | NSW/Vic top pick |
| --- | --- | --- | --- | --- |
| 2024 | +0.053 (0.042 to 0.064) | +2.4 pts | +0.071 (0.063 to 0.078) | +2.7 pts |
| 2025 | +0.057 (0.045 to 0.069) | +2.0 pts | +0.061 (0.053 to 0.068) | +2.3 pts |
| 2026 | +0.047 (0.034 to 0.060) | +1.9 pts | +0.052 (0.043 to 0.060) | +2.9 pts |

- **Honest limits:**
  - 2025–26 has been examined by earlier batches.
  - The Qld "form changes" family was dropped from the release *after* seeing it hurt on 2025–26. That was a choice made on that period.
  - Raw v2 chances are over-confident at the top: NSW/Vic's top tenth predicted 33.1% vs 29.3% actual; Qld 30.9% vs 26.7%. Selection strength uses the calibration layer that corrects this.
  - Prospective monitoring of v1 and v2 starts today.

## 6. Dynamic re-scoring: Wyong R7, one input at a time

Each scenario re-scores the race end-to-end with the learned models. Nothing is adjusted by hand.

| Change | Top pick HY: final rating (chance) | What moved and why |
| --- | --- | --- |
| As published (Good 4, Wyong) | +6.8 (27.4%) | – |
| Track to Soft 6 | +6.8 (28.4%) | Each horse's soft-track record replaces its good-track record. Very Sirius −0.7, Absolutist +1.4. |
| Track to Heavy 8 | +6.8 (28.0%) | Heavy-track records: The Pacific +0.5, Very Sirius −0.6. |
| Same race at Newcastle | +6.8 (28.3%) | Newcastle records: Waveton +1.2, Stellaa Lass −0.7. |
| HY ridden by the strongest-record NSW jockey (A Bullock) | **+8.6 (37.8%)** | v2 jockey terms. v1 has no jockey term and wouldn't move. |
| HY ridden by the weakest-record NSW jockey (E Hennessy) | +6.4 (25.1%) | v2 jockey terms. |
| HY barrier 1 → 12 | +6.8 (27.4%), **no change** | There's no barrier history for NSW/Vic, so no barrier effect has been learned. |
| Rail out 6 m | **No change** | No rail effect has been validated. |
| HY carries 3 kg more | +6.2 (24.0%) | The model has learned that weight moves results less than a literal 3 kg. |
| Zourrific (2nd pick) scratched | +7.5 (34.9%) | Everyone is re-scored against the smaller field. |

- The scale is race-relative: when one horse goes up, the others dip slightly.
- The full per-horse tables are in engine/out/demo_rescore.md in the code bundle.

## 7. Today's ranked selections (engine v2)

| # | Meeting | R | Top pick | Final rating | Clear of 2nd | Selection strength | Label | v1 top pick |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Wyong | 2 | Ligularia | +6.1 | +3.5 | 32.1% | strong | same |
| 2 | Wyong | 5 | Siragusa | +6.6 | +2.5 | 28.7% | moderate | same |
| 3 | Wyong | 3 | Appin Opal | +6.2 | +1.2 | 25.0% | moderate | same |
| 4 | Wyong | 7 | HY | +6.8 | +0.9 | 24.9% | moderate | same |
| 5 | Ipswich | 4 | Cellphone | +5.0 | +0.4 | 23.7% | moderate | Castello Grande |
| 6 | Wyong | 1 | Freddie Bassett | +3.5 | +1.3 | 23.2% | weak – no clear selection | same |
| 7 | Wyong | 4 | Acknowledge Me | +5.7 | +0.2 | 21.8% | weak – no clear selection | Captain Peacock |
| 8 | Ipswich | 3 | Clouded Thoughts | +5.6 | +2.3 | 21.6% | weak – no clear selection | Hard Miss |
| 9 | Wyong | 6 | Gravel Road | +4.1 | +0.2 | 21.0% | weak – no clear selection | same |
| 10 | Ipswich | 5 | Ancestral | +4.7 | +1.1 | 19.7% | weak – no clear selection | Switchblade |
| 11 | Ipswich | 7 | Tasman Bay | +3.8 | +1.1 | 17.0% | weak – no clear selection | same |
| 12 | Ipswich | 6 | Barrelling | +3.9 | +0.5 | 16.6% | weak – no clear selection | Rolling Home |
| – | Ipswich | 2 | Flavourofthemonth | +4.7 | +2.5 | – | insufficient information | Plan of Attack |
| – | Ipswich | 1 | Brother | +5.3 | +1.0 | – | insufficient information | Two Minds |

- **Ipswich:** v2 changes the top pick in 6 of 7 races, mostly through trainer and jockey records. Brother (R1) and Flavourofthemonth (R2) have no prior form, so they are labelled insufficient information rather than ranked.
- **Wyong:** no sectionals or barrier history exist for NSW, and every runner says so.
- **Per-horse breakdowns** (for, against, horse-specific records, jockey/trainer, rating change, evidence gaps) are in the v2 ranking report.

## 8. Development programme from here

**Operations**

1. Keep the PC on with Chrome open overnight.
2. 26 Nov morning:
   - results;
   - the first prospective evaluation of v1 and v2;
   - the next day's fields and the v2 ranking.
3. Victorian collector on racing.com's rendered pages.
4. Load the second Breednet crawl, venue aliases and course configurations.
5. Track-geometry table.
6. Vic sectional history; NSW sectional sources.

**Research**

1. **v3:** a penalised joint refit of all families, pruning what the audit flagged.
2. Partial pooling by course for the v2 terms. For example, does a trainer's edge depend on the track?
3. An age source for Qld (Racing Queensland fields PDFs).
4. A daily surprise review in the morning cycle:
   - who beat or missed their rating, and by how much;
   - repeated errors by factor;
   - candidate hypotheses for the register.

   Coefficients are never changed from single races.
5. Gear, trials and apprentice claims.
6. A flexible challenger (boosted trees or a GAM) on top of v2, compared on identical races.
