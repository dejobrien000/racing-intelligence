# Batch 6: Operations and discovery

Written 24 Nov 2026, before any 25 Nov race. Prices are not used anywhere. The 49-hypothesis register, the frozen benchmarks and the earlier studies are unchanged.

## 1. Daily operations: where things stand

| Piece | Status | Evidence |
| --- | --- | --- |
| Qld morning fields (Racing Queensland) | **Working** | Ipswich 25 Nov captured 9:34pm 24 Nov, with going, rail and scratchings. Scored and saved write-once. |
| NSW morning fields (Racing NSW) | **Working (new)** | Wyong 25 Nov: 66 acceptors captured 11:03pm 24 Nov, and 62 runners scored. Hawkesbury 26 Nov fields are also captured. Entries with no saddlecloth number (emergencies) are held out until confirmed. |
| Vic morning fields (racing.com) | **Not built** | Its pages are drawn by script. The plan is to read the rendered page in Damo's Chrome. No API keys are extracted. |
| Scoring with frozen models | **Working** | Qld uses combined_v1 + national rating, with sectionals and race shape. NSW and Vic use nat_v2 (form, ability, fitness, national rating, horse records), with no sectionals. |
| Daily ranking | **Working (new)** | First report: 25 Nov, 2 meetings, 14 races (section 2). |
| Post-scratchings re-score | Scheduled 8:05am 25 Nov | Ipswich, now with Wyong added. These are new files; the 9:34pm and 11:03pm sets are never overwritten. |
| Results, then evaluation | Scheduled 26 Nov, 7:35am | Append-only (evaluate_prerace.py). This is the first prospective test. |
| Unattended 6:31am collection | **Not yet verified** | The first unattended run is 25 Nov. It gets checked at 7:15am. |
| Second Breednet crawl | Running | Fixes missing non-finishers, venue identities and coverage. It gets loaded when finished. |

- **Constraint:** every collector reads public pages through Damo's Chrome. If the PC is off, or Chrome isn't running with the extension, that morning's run fails and the failure is reported. It is never filled in afterwards as if it had been pre-race.
- **Sectionals:** only Queensland publishes them historically. NSW and Vic ratings state "no sectionals or running style" on every runner. Nothing is estimated in their place.

## 2. First daily ranking: Wed 25 Nov

| # | Meeting | R | Top pick | Final rating | Clear of 2nd | Selection strength | Label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Wyong | 7 | HY | +8.6 kg | +4.1 | 36.3% | strong |
| 2 | Wyong | 5 | Siragusa | +7.6 | +3.0 | 34.2% | strong |
| 3 | Wyong | 2 | Ligularia | +5.5 | +2.3 | 29.2% | strong |
| 4 | Wyong | 4 | Captain Peacock | +6.2 | +2.2 | 25.8% | moderate |
| 5 | Wyong | 3 | Appin Opal | +5.6 | +0.2 | 23.7% | moderate |
| 6 | Wyong | 6 | Gravel Road | +4.1 | +1.3 | 21.9% | moderate |
| 7 | Wyong | 1 | Freddie Bassett | +3.0 | +1.0 | 21.0% | weak – no clear selection |
| 8 | Ipswich | 4 | Castello Grande | +3.5 | +0.8 | 20.0% | weak – no clear selection |
| 9 | Ipswich | 7 | Tasman Bay | +4.6 | +3.2 | 18.4% | weak – no clear selection |
| 10 | Ipswich | 2 | Plan of Attack | +2.7 | +1.2 | 17.1% | weak – no clear selection |
| 11 | Ipswich | 5 | Switchblade | +3.5 | +0.3 | 17.1% | weak – no clear selection |
| 12 | Ipswich | 3 | Hard Miss | +3.0 | +0.1 | 15.8% | weak – no clear selection |
| 13 | Ipswich | 1 | Two Minds | +3.3 | +1.5 | 15.4% | weak – no clear selection |
| – | Ipswich | 6 | Rolling Home | +2.4 | +0.6 | 14.0% | insufficient information |

How each number is built:

- **Final rating.** There is one number per horse. All of that horse's factors are combined and expressed as kg better (+) or worse (−) than the average runner in its race. 1 kg of final rating equals 1 kg of rating difference on average. The model score per kg was measured on development races: 0.19 log-odds in both state groups.
- **Selection strength.** This is how often top picks like this one actually won in 2025–26 races that the frozen models never saw. It is calibrated separately for Qld (4,730 races; top picks won 23.7%) and for NSW/Vic/ACT (16,489 races; 25.8%). The calibration accounts for the model's own top chance and for field size. Above 30%, the raw top chance was overstated, and calibration pulls it back. Separation, agreement and uncertainty added nothing beyond this (Batch 5), so they are shown but not counted.
- **Labels.** These are descriptive thirds of each state group's own 2025–26 races. They are not betting thresholds. "Insufficient information" means the top pick has no prior form in our data, or more than half the field has none.
- **Per-horse breakdown.** The report (Downloads\racing_predictions\20261125\daily\) lists, for every runner:
  - the factors for and against it, in kg;
  - the course-specific record applied, for example "Course record +3.5 kg over 1 earlier run here";
  - its evidence gaps;
  - how its rating moved after its last run.
- **Why Ipswich is all weak.** The track is Soft 5, and there are many lightly raced or Qld-new runners: 4 of 12 in R1 have no prior form. Wyong's fields are smaller, and its horses are well exposed.
- **Nothing is refitted from results.** The calibration layer is frozen at benchmarks/selection_strength_v1. Coefficients change only through a versioned, controlled comparison.

## 3. Data gaps and what is being done

| Gap | Action |
| --- | --- |
| Vic morning fields | Build a reader for racing.com's rendered fields page, next in operations. |
| Vic historical sectionals and speed data | Find out how far back the racing.com sectional files go and how to retrieve them. Until then, Vic has no sectionals in history. |
| Non-finishers missing from Breednet | They come back from Betfair and the second crawl. All 24 checked cases were omissions, not scratchings. |
| Venue identities (Newcastle = beaumont, Royal Randwick, canberra-acton, yarra-glen) | Aliases go in after pass 2. The coverage matrix and national pars are then rerun with course configurations. |
| Course configurations in the national pars | national.py still uses the venue. It is rerun with configurations after pass 2. |
| Qld records in the pre-race scorer | The candidates_b5 records are frozen but not yet in the Qld pre-race scorer. They go in as a versioned Qld v2. |
| Course geometry (straight, circumference, turns) | There is no table yet. Investigations 13 and 15 wait on it. |
| Jockey and trainer form, gear, trials, apprentice claims | Untested. The claims are already collected in the NSW fields. |

## 4. Feature inventory

The full library is in the sheet [Racing Intelligence – Feature library](https://claude.ai/artifact/Wzqhm6sMpDesyvJjWn6tdX) (tab "Feature library"). It has one row per feature, with these columns:

- definition and racing meaning;
- data needed and jurisdictions;
- status;
- effect and uncertainty;
- course dependence;
- contribution beyond existing features;
- stability;
- validation;
- source study.

| Status | Count |
| --- | --- |
| Implemented, in an operational model | 39 (36 core + 3 horse records) |
| Tested, frozen but not operational | 1 (PA1 pace-corrected figure) |
| Experimental, new single features screened today | 9 |
| Experimental, interactions that passed discovery and confirmation | 7 |
| Untested | 10 |

- **Honest gap:** for the core features the evidence is at group level (Batch 2/3). A one-feature-at-a-time drop test has not been run yet.

## 5. Discovery screen 1 (Queensland, richest data)

**Design**

- Every candidate is a single term added on top of the frozen combined_v1 + national rating, inside a within-race model.
- **Discovery** uses races before 2025:
  - Benjamini–Hochberg at 10%;
  - the same sign in 2022–23 and in 2024;
  - at least 300 races where the term varies.
- **Confirmation** uses 2025–26 races, with the coefficient fixed. The fit gain needs a meeting-bootstrap 95% interval above zero.
- **Course-specificity** is checked by fitting per-track coefficients across 9 tracks and testing their spread (Q, I²).

**Results**

- **Overall:**
  - 593 candidates were tested: the 15 named investigations, 9 new single features, 406 pairs, 116 feature × context terms and 45 three-factor terms. The three-factor terms were chosen on discovery data only.
  - 72 passed discovery.
  - **7 passed both stages.** Each is worth about +0.001 to +0.002 log-likelihood per race. None moves top-pick accuracy by more than 0.3 points.
- **One theme runs through all 7: corroborated improvement.** Some horses have both:
  - just beaten their own rating, or improved their figures;
  - a strong pace-corrected figure.

  Those horses are under-rated by the current dynamic rating. The rating appears to learn too slowly when improvement is backed by a second source. A real-world reading: the horse is genuinely on the up, and the rating is still catching up.
- **None of the 7 is course-specific.** I² is 0–45% and no Q test is significant, so course versions are not justified.
- **More real signal than chance.** 51 terms were positive in confirmation; about 15 would be expected by chance. The baseline is missing real structure, mostly in:
  - improvement;
  - weight interactions;
  - trip (route) interactions.
- **Promoted terms are frozen** (benchmarks/discovery_screen1) for testing on races from 25 Nov. A high historical win rate was not used to promote anything.

**The 15 named investigations**

| # | Investigation | Discovery | Confirmation | Verdict |
| --- | --- | --- | --- | --- |
| 1 | Opposition strength × class change | not significant | nil | Not supported |
| 2 | Course record × running style | not significant | nil | Not supported |
| 3 | Pace-corrected figure × distance change | p 0.05, fails BH | negative | Not supported |
| 4 | Barrier × settling position (course version: Batch 4) | nil | nil | Not supported |
| 5 | Weight change × opposition strength | nil | nil | Not supported |
| 6 | Prep stage × recent improvement | nil | nil | Not supported |
| 7 | Course record × wet going today | **passes** (q 0.04) | +0.0013 (−0.0004 to +0.0028) | Passed discovery, not confirmed: watch |
| 8 | Late sectional × last-start tempo × trip | nil | nil | Not supported |
| 9 | Ground covered × finishing speed | nil | nil | Not supported |
| 10 | Head-to-head × changed distance | not significant | +0.0009 (CI spans 0) | Not supported |
| 10b | Head-to-head record (main effect) | fails BH (q 0.15) | **+0.0012 (+0.0001 to +0.0024)** | Watch list |
| 11 | Rating trajectory × days between runs | not significant | +0.0006 (CI spans 0) | Not supported |
| 12 | Ability × field strength | fails BH | **+0.0012 (+0.0002 to +0.0022)** | Watch list |
| 13 | Leader × pace pressure × metro (course: Batch 5) | nil | nil | Not supported; geometry pending |
| 14 | Class advantage × weight carried | fails BH (q 0.18) | **+0.0014 (+0.0004 to +0.0024)** | Watch list |
| 15 | Late speed × course (proxy: × trip) | nil | nil | Not supported; geometry pending |

New single features:

- **Rating trajectory** and **last-start surprise** are each positive out-of-sample, but they fail the discovery screen. Both point at the same improvement theme.
- **Class change, weight change, last-race tempo and ground covered** add nothing.
- Full results for all 97 shown terms are in the sheet, tab "Discovery screen 1".

## 6. What changes when a supported feature is added

**NSW/Vic/ACT:** adding horse records (course configuration, going band and distance band) to the national model, compared on identical races (16,489):

| | nat_v1 | nat_v2 (+ records) |
| --- | --- | --- |
| Fit beyond random | 10.07% | 10.27% |
| Top pick wins | 25.5% | 25.8% |
| Gain per race | – | +0.0043 (0.0030 to 0.0056) |

- **On 25 Nov at Wyong** no top pick changed.
- The biggest moves:
  - **Southport** +3.8 points: course record +2.9 kg, from 1 earlier run.
  - **Freddie Bassett** −2.6 points: course record −1.0 kg.
- **Qld (Batch 4):** adding the national rating to combined_v1 gave +0.019 per race and +0.8 points of top-pick accuracy.

## 7. Next steps

**Operations**

1. 8:05am 25 Nov: post-scratchings re-score for Ipswich and Wyong, then rebuild the daily ranking.
2. 26 Nov morning:
   - results;
   - the first prospective evaluation;
   - fields for Rockhampton (Qld) and Hawkesbury (NSW);
   - the daily ranking.
3. Build the Vic morning collector.
4. Load pass 2, then apply venue aliases and configurations, and rerun the coverage and national pars.
5. Qld operational v2 (adds horse records): a versioned switch after the identical-race comparison.

**Discovery**

1. Turn the improvement theme into one controlled rating revision rather than 7 interaction terms. Candidate: a dynamic rating that learns faster when a surprise is corroborated by a second source. Compare it with the current rating on identical races.
2. Rerun the screen on NSW/Vic common features. Last-start surprise, trajectory and head-to-head are all computable there.
3. Fit a flexible layer (boosted trees on top of the frozen model) to capture the excess signal, with the same split.
4. Build a course geometry table, then run investigations 13 and 15 properly.
5. Add the 7 promoted terms to the hypothesis register as H50–H56, with status "frozen for future test".
