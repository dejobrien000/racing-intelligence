# Batch 14 follow-up ledger (27 Nov 2026, 00:23-01:30): physical profiles, momentum, rider characteristics

Brief: "Horse Intel - Targeted Research Follow-up: Physical Profiles, Momentum and Rider Characteristics" (Damo, 00:23 27 Nov).
Follows Batch 14 (Damo's "Research Batch 13"; see ../README.md for the naming).
Report (Docs): "Horse Intel - Batch 14 follow-up: physical profiles, momentum and riders" (artifact 9c88b391-1ae1-4275-a6e1-c6d21cdd0eeb).
The Batch 14 report (artifact fe361e22-4a0f-48ed-b364-102f50e78c52) now carries the naming note and a link to the follow-up. Research only: no production change, no new collector,
no new system, no market data anywhere. Existing database, staging and evaluation harness only. Production stays Engine v2.3 (six
states) and Engine v2.1.3 (Qld) from the 27 Nov run.

Data: Qld tracking (Oct 2022 - Nov 2026) and SA tracking (Jan 2024 - Nov 2026) per-run tables from Batch 14 (b14_build.py);
QRIC stewards reports (2,827 reports, raw branch raw-rqstewards) and SA stewards PDFs (384, Oct 2022 - Nov 2024, raw branch raw-sagear),
parsed here; national v3 frame (all states) for ratings and jockeys; the Engine v2.3 candidate harness (/tmp/cand, Batch 12).
Outcome unless stated: next-run rating surprise (kg; race-centred, so the race mean is exactly 0; sd 5.5 kg).
Periods: Qld 2022-24 discovery; Qld 2025-26 re-used; SA 2024-26 check (already used in Batch 14, so not untouched).
About 60 further tests. Results are called findings only where the 95% interval clears zero in two or more periods.

| Script | Brief | Output | Result in one line |
|---|---|---|---|
| parse_stewards.py | s3 | research/staging/stewards/stewards_events.csv.gz (180,370 rows) | 18 tags; subject vs mentioned horse; negation kept separately; first distance mark; phase flags; text kept verbatim |
| b14f_profiles.py | s1, s3 | out_profiles.json | seven finishing profiles; Progressive fade and Late fade precede better-than-rated next runs in all three periods; dip survives stewards controls |
| b14f_norms.py | s2, s8 | out_norms.json | own-normal finishing shape; an abnormal decline precedes a better-than-rated next run (rating over-reacts); recovery, recurrence, dropout |
| b14f_artifact.py | s7 | out_artifact.json | workload 'later rides better' is an estimator artifact (absolute rating control on a race-relative outcome); no order effect |
| b14f_riders.py | s4, s5 | out_riders.json, horse_momentum_profiles.csv, rider_momentum_profiles.csv | momentum profiles; rider tendencies persistent in Qld and SA; no prospective value beyond j_surp; small horse x rider interaction |
| b14f_riders_band.py | s5 | out_riders_band.json | rider late retention by distance: not established at finer distance bands in either state |
| b14f_qld_engine_riders.py, b14f_qld_joint.py | s5, s11 | out_qld_engine_riders.json, out_qld_engine_joint.json | on top of Qld Engine v2.1.3: profile flags +0.000, rider +0.001, all together +0.003 / +0.002 (intervals include 0) |
| b14f_jdist.py | s6 | out_jdist.json | distance specialisation persistent year to year (r 0.27-0.38); optimal shrinkage 734 rides; no specialist subgroup; feeds the engine tests |
| /tmp/cand/fu_compare.py | s6, s11 | out_engine_small_improvements.csv | Engine v2.3 harness: distance form adds nothing (-0.0003 to +0.0001); weight slope +0.0012 / +0.0014; together worse than weight slope alone |
| b14f_poj.py | s9 | out_poj.json, poj_*.csv | Pride Of Jenni: full measured profiles, three races, ratings, figures, stewards text |

## s1 Physical performance profiles (last 600 m: 600-400, 400-200, final 200, field-relative speed)
Profiles (dead zone 0.5 sd of a step, about 0.16 m/s Qld, 0.15 SA): Building 30%, Steady 24%, Late fade 12.5%, Progressive fade 12%,
Early fade 10%, Surge then fade 6%, Dip and recover 5-6%. Continuous measures kept alongside: level, slope (final 200 minus 600-400),
bend, recovery (final 200 minus 400-200), dip (average minus weakest section).
Next run vs Steady (kg, 95%): Progressive fade +0.55 (0.32-0.78) Qld 22-24, +0.39 (0.15-0.63) Qld 25-26, +0.79 (0.44-1.14) SA;
mean of next five +0.23 / +0.24 / +0.35; rating change over five starts +0.49 / +0.44 / +0.32. Late fade +0.20 / +0.21 / +0.28.
Dip and recover +0.17 / +0.23 (n.s.) / -0.01 SA. Building +0.08 / +0.05 (n.s.) / +0.27 (0.04-0.50) SA.
Controls in every model: average last-600 speed, early position, deficit at 800, tempo, distance band, course, field strength, prep stage, field size.
Continuous: finishing weaker (slope per sd) -0.24 / -0.14 / -0.14 kg -> runs better next time; recovery +0.12 (Qld 22-24 only).
The value shows in the fading profiles (Progressive fade, Late fade), not in Dip and recover, the 'textbook' uneven profile, which does
not replicate in SA. The continuous dip still stands with the shape terms in (0.25 / 0.21 / 0.31 per sd).
Location matters: a late or progressive fade is followed by better next runs; an early fade (weak 600-400, then holding) is not
(+0.01 / +0.03 / +0.01). No universal unevenness bonus.

## s2 / s8 Individual normal profiles and longer-term change
Usual finishing slope from earlier runs only (shrunk 3 runs). Within-horse sd 0.466 m/s vs population 0.513 (Qld), 0.413 vs 0.459 (SA):
horses have a usual shape, but it explains little of the spread. Established style (strong finisher / in between / habitual fader) does
not change the effect of a run's shape. Continuous departure from own normal predicts no better than the raw shape (-0.10 / -0.26 kg per sd).
Abnormal decline (more than 1.5 own-sd weaker finish; 7.0% of runs Qld, 6.6% SA): next run +0.31 (0.05-0.57) Qld, +0.77 (0.18-1.37) SA;
next five +0.31 (0.15-0.47) / +0.38; repeated decline (two in a row) extra +0.82 (0.07-1.56) Qld, SA n.s.
The rating over-reacts: after a decline it drops 2.01 kg at once and is still 0.62 kg down after five starts (normal runs +0.22 / +0.66).
Abnormal improvement (4.1% / 4.7%): next run -0.07 / +0.02 (n.s.).
Return to profile: next tracked run back within the normal range 67.7% after a decline vs 75.5% overall (SA 69.7% vs 74.1%);
decline repeats 8.3% vs 5.8% base (SA 8.0% vs 5.1%).
Dropout: races again within 180 days 93.5% after a decline vs 97.2% (SA 93.5% vs 97.1%). Worst-case bound (stopped horses given a
bottom-decile next five) keeps the decline effect: +0.31 (0.15-0.47) Qld, +0.38 (0.01-0.75) SA.
Context (early prep, distance up 200 m+, fast tempo): no context changes the decline effect (all interactions n.s.).
No causes inferred. The finding is that a weak finish against the horse's own normal is, on average, a run the horse comes back from,
and the rating marks it down too far. In the Qld engine it adds nothing (s11), so the engine's own physical inputs already allow for it.

## s3 Stewards reports (supplementary evidence only)
Parsed QRIC (2,827 reports) and SA (384 PDFs) already held. 180,370 rows: 137,661 where the horse is the subject, 42,709 where it is only
mentioned (e.g. the horse that caused the interference). Tags: held up, checked, restrained, bumped, wide, wide without cover, wide with
cover, unable to improve, disappointed for a run, weakened, rider concern, performance concern, vet finding, vet clear, slow to begin,
over-raced, laid in / hung, shifted. Negated phrases kept in their own column, never counted as events. Text kept verbatim.
Coverage: Qld runs at a meeting with a report 98-99%; a paragraph about the horse 68-71%. SA 30% (PDFs end Nov 2024).
An absent comment is not 'no event': rates below are lower bounds.
Profiles x reports (Qld 22-24): Building and Dip and recover carry the most 'held up' (9.5%, 6.9%); Progressive fade the most performance
concerns (4.7% Qld 22-24, 5.1% Qld 25-26, 11.1% SA) and wide without cover (2.4 / 3.8 / 7.5%). Reported wide runners are measurably
wider at the 400 (2.67 vs 1.81 m Qld; 3.81 vs 3.12 SA): reports and tracking agree.
The dip effect survives the stewards controls (0.25 / 0.18 / 0.31 per sd), so it is not simply interference.
Reported performance concern -> next run +0.28 (n.s.) / +0.52 (0.03-1.00) / +0.36 (n.s.).

## s4 Horse and rider momentum profiles (descriptive, research only)
Measures (200 m sections; no instantaneous acceleration; nothing about when a rider asked): timing (gain on the field 800-400 out vs the
last 400), late retention (final 200 vs 400-200), prolonged build (two or more consecutive rising sections, 12.9% of runs), rapid single
surge (15.5%), sustained high speed (3+ of the last four sections 0.2 m/s above the field, 6.8%).
Actual vs relative: 44.9% of relative gains 600-400 -> 400-200 were made while the horse's own speed was falling (others slowed more);
correlation of actual and relative change 0.50. Relative gains are not acceleration.
Persistence (split-half r, circumstances removed): horse timing 0.27 Qld / 0.25 SA; horse retention 0.36 / 0.39; sustained 0.28 / 0.30;
prolonged build 0.09 / 0.08 (not a trait). Same horse at two courses r 0.13 / 0.13; on pace vs back r 0.19 / 0.26: horse timing is
only partly stable across courses and styles.
Riders (same horse, different riders; trainer average removed): timing 0.56 Qld (137 riders) / 0.73 SA (38); retention 0.59 / 0.60;
sustained 0.56 / 0.33; across two different sets of trainers 0.58 / 0.71. Rider tendencies are real and stable.
Size: spread between riders 0.026 m/s (about 0.1 length per 200 m). Timing and retention share sections (riders: r -0.59).
Profiles written: 2,798 horses (10+ tracked runs), 121 riders (200+ rides), shrunk, with standard errors. Research reference only.

## s5 Rider late retention ('finishing strength') - SA validation
Validated as a persistent tendency in SA: within-horse split-half 0.60 (38 riders), trainer removed 0.595 (Qld 0.60, 137 riders).
By distance (40+ rides per band, trainer removed): Qld 0.11-0.35, SA 0.03-0.36, all intervals wide: the Batch 14 sprint/middle vs
staying split is NOT established at finer bands. Prospective value beyond the dynamic jockey assessment (j_surp): rider prior retention
-0.04 (-0.15 to +0.08) kg per sd Qld, +0.05 (-0.14 to +0.24) SA: none. Horse momentum x rider: horses that habitually gain early do
slightly worse with riders whose horses keep their speed late (interaction -0.07 (-0.11 to -0.02) Qld, -0.23 (-0.37 to -0.08) SA kg per sd²):
consistent in both states, small. Horse early timing itself -0.15 / -0.13 kg per sd. Not attributed to strength, fitness or technique.
On top of Qld Engine v2.1.3: +0.0008 (-0.0005 to +0.0021) 2024, +0.0013 (+0.0001 to +0.0026) 2025-26; top pick -0.1 / -0.2 points.
Status: descriptive; uncertain-small for the engine; no candidate.

## s6 Jockey distance specialisation
Persistence (staying minus sprint form, before the year vs the year): r 0.27 (2024), 0.32 (2025), 0.38 (2026): genuine.
Optimal shrinkage from split-half covariance: true sd 0.20 kg vs ride noise 5.5 kg -> prior weight 734 rides (Batch 14 used 60).
Beyond j_surp and trainer distance form (2023-26): 1.14 kg per kg (0.98-1.30) = 0.25 kg per sd at optimal shrinkage; six finer distance
groups 0.28 per sd, no better than three bands. Pre-specified specialists (top 10% on pre-2025 data, 22 of 220 riders): no extra effect
in 2025-26 (+0.005, -0.39 to +0.40). Related to rider timing (r 0.28: riders whose horses move earlier do relatively better over
staying trips), not to retention (r -0.01).
Engine v2.3 harness (every layer refitted): as a separate term -0.00034 (-0.00069 to -0.00002) 2024, -0.00015 (-0.00029 to -0.00001)
2025-26; inside the existing jockey assessment (j_surp + j_spec, same family) -0.00025 (n.s.) / +0.00005 (n.s.). Batch 14's 60-ride
version +0.00007 / +0.00014. Status: genuine but too small; incorporating it into j_surp is the right form if ever revisited, but
there is no measurable gain now. No distance bonus.

## s7 Jockey workload (closed)
Results preserved: no workload or order effect. The Batch 14 'later rides go better' (+0.15 to +0.37 kg) appears only when the absolute
pre-race rating difference between a rider's rides is controlled; with no rating control later rides show -0.02 to -0.05 kg; random
orders show nothing; reversing the order flips the sign; prize money does not explain it. Mechanism: the outcome is race-relative but the
control is absolute, across races of different class. Rule: with race-relative outcomes, control race-relative ratings (rating minus
field mean) or none. Owner's observations kept on record as context, not contradicted by any test: leading riders are professional
athletes conditioned for multiple rides; recovery time between races is built into the program; leading riders are allocated better
horses (booking selection explains the 'busier days' difference). Not reopened without a substantive new reason.

## s9 Pride Of Jenni (full tables: poj_*.csv; everything in out_poj.json)
Doomben Cup 2000 m, 24 May 2025 (Group 1, Good 4, rail +2 m, 12 runners): rated 16.85 kg pre-race, 7th of 12 (top 20.9, Antino, the
winner). Fast early pace (tempo z +1.96). She led by 0.16-0.43 s; first 1000 m 59.86 s vs field median 61.10 (1.24 s faster); fastest
section 17.9 m/s at 1600 m to go. From 800 m out she was the slowest in the field for three successive 200 m sections (-0.31, -0.64,
-0.64 m/s vs the median), headed before the 200, 10th by 10.9 L. Stride length fell from 7.9 m mid-race to 6.9 m in the last 200
(field median 7.0). Ground 1,998 m (winner 2,005). Time 122.74 s. Time figure 102.5. Rating surprise -4.9 kg (a below-rating run).
Stewards (reported, not observed): rider said he had to use her early to lead, she raced only fairly in the middle stages and came back
from the 500 m; no concern with her action; post-race vet: slow recovery.
Doomben Cup 2000 m, 23 May 2026 (Good 4, rail +2 m, 7 runners): rated 20.17 kg, 2nd of 7 (Birdman 21.19, the winner). She ran the first
1000 m in 61.08 s - 1.2 s SLOWER than she ran it in 2025 - but the field went 63.23, so her lead grew to 1.98 s at 1000 m to go (fastest
in each of the first five sections). From 800 m out she was slowest of seven for three sections (-0.25, -0.96, -0.79 m/s), then 5th
fastest in the last 200; caught late, 2nd by 0.45 s (2.66 L). Stride 7.4-7.5 m late vs field 7.6. Ground 2,013 m (winner 2,005).
Time 122.68 s. Time figure 105.7. Rating surprise -0.2 kg (ran to her rating). No stewards comment about her (absent comment, not 'no event').
Caulfield 1600 m, 27 Sep 2026 (Good, 6 runners): rated 20.12, top of six. Led throughout by 0.14-0.43 s; first 800 m 0.72 s faster than the
field median, second 800 m 0.20 s slower; third-fastest last 200; won by 0.26 s. Time figure 111.4. Rating surprise +1.0 kg.
(Victorian files: times and speeds only; no stride, width or ground.)
Reading: her two Doomben times are almost identical (122.74 and 122.68 s). The difference is distribution, not capability: in 2025 she went
1.2 s faster early under pressure and paid it back late; in 2026 she ran a more even race herself and the 2 s lead was made by the others
going slower. Being caught in 2026 was NOT an inferior performance: she ran exactly to her rating against a stronger, smaller field and
was beaten by the top-rated runner. Caulfield differs by course (2,080 m circuit, 367 m straight, left-handed, sweeping turns; Doomben
1,715 m, about 350 m, right-handed, tight) and by 400 m of distance; her best figures are at 1600-1800 m (Caulfield 1600 May 2025 121.4;
Gold Coast 1800 May 2026 113.7), and she has run to her rating at 2000 m elsewhere (Flemington Mar 2026, 2nd by 0.1 L, +4.8 kg).
Course, distance and pace cannot be separated with three tracked runs. Course facts are from public track guides, not measured here.

## s10 Kept open (untested or not yet adequately tested; not rejected)
Course geometry and momentum retention (Batch 14 used an empirical leader-hold index by track; that is not geometry); horse acceleration
x course configuration; extra ground vs optimal distance; wide with vs without cover (now tagged in stewards text, Qld 0.6-3.8% of runs:
next-run +0.41 / +0.14 / +0.52, all n.s. - too few); clear running and interruption sensitivity (stewards tags now available; horse-level
repeatability not yet tested); cross-jurisdiction inference; measured times vs estimated figures; interstate connections; dynamic distance
suitability; one experience-dependent learning mechanism nationally.

## s11 Small improvements (categories; tested against the actual production engines; additivity not assumed)
| Category | Items |
|---|---|
| Genuine positive incremental (engine-measured) | Handicap weight slope on Engine v2.3: +0.00124 (0.00078-0.00171) 2024, +0.00144 (0.00109-0.00181) 2025-26. Already queued for the next release |
| Genuine against the rating, redundant in the engine | Fade profiles and abnormal decline (Qld engine +0.000); jockey distance form (Engine v2.3 -0.0003 to +0.0001) |
| Uncertain, small | Dip on Qld engine +0.0040 (-0.0006 to +0.0095) / +0.0009; rider tendencies +0.0008 / +0.0013; all Qld items together +0.0034 (-0.0021 to +0.0091) / +0.0021 (-0.0011 to +0.0054) |
| Descriptive only | Horse and rider momentum profiles; horse x rider interaction; stewards tags; Pride Of Jenni |
| Noise or rejected | Workload/order; specialist subgroup; finer distance bands; physical decline as a sign of further decline |
Not additive: weight slope + distance form (-0.00034 / -0.00016 vs weight slope alone); Qld all-together below the sum of its parts.
Winning frequency (top pick) moved -0.2 to +0.15 points in every test: downstream only, never the deciding measure.
