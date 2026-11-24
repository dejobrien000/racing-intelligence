# Research library

One line per study. Columns: id, batch, title, hypotheses, validity, data, runners_races, compared, result, after_other_factors, next, script, outputs.
Query it with pandas, e.g. `pd.read_csv("library/studies.csv").query("hypotheses.str.contains('R18')", engine="python")`.

## B1-1 Rating v0 vs simple baselines
- Validity: chronological out-of-sample
- Question/hypotheses: R15,R17
- Data: Qld tracked races; fit <2025, score 2025-26 (1,257 complete-figure races (sensitivity 4,730))
- Compared: figure versions vs form, margin, win %, class, weight
- Result: figure alone weaker than avg finishing position last 3 (19.6% vs 21.6% top picks); adds 0.015/race beyond all baselines (0.006-0.024)
- After other factors: yes, adds beyond baselines
- Next: improve the figure
- Script: `inv13_b1_rating_baselines.py` -> `out_b1_*.csv`

## B1-2 R9 interaction profile
- Validity: chronological out-of-sample
- Question/hypotheses: R9,R14,R22,R25
- Data: Qld beaten runners, true next start 7-60 days (16,639 fit / 17,285 scored runs)
- Compared: main effects vs pre-set interactions; additive vs depth-3 trees
- Result: interactions add nothing out-of-sample (0.00005/run, -0.0003 to 0.0004); trees no better
- After other factors: no
- Next: IP1 stays exploratory
- Script: `inv14_b2_r9_interactions.py` -> `out_b2_*.csv`

## B1-3 Step-up penalty outside Queensland
- Validity: independent interstate replication (survivor-biased form lines)
- Question/hypotheses: R13
- Data: Racing NSW form lines, non-Qld races Oct 2022-Nov 2026 (60,965 runs, 5,877 horses)
- Compared: step up 200m+ vs same trip
- Result: odds 0.93 (0.87-0.99); 0.89 with NSW rating move
- After other factors: yes
- Next: re-check on full Breednet results
- Script: `inv15_b3b4_nsw_tests.py` -> `out_b3_*.csv`

## B1-4 Weight change
- Validity: exploratory (Qld) + interstate replication (NSW)
- Question/hypotheses: R41,R49
- Data: Qld finishers with true next start; NSW form lines (49,824 Qld runs; 69,882 NSW runs)
- Compared: 2kg+ drop vs within 1.5kg
- Result: drop goes with worse next start: Qld 0.78 (0.72-0.85), NSW 0.86 (0.80-0.93); association, not cause
- After other factors: yes (class, figure, margin)
- Next: weight as handicapper information (R49)
- Script: `inv16_b4_weight_qld.py; inv15_b3b4_nsw_tests.py` -> `out_b4_*.csv`

## B2-1 Rating variants
- Validity: chronological out-of-sample
- Question/hypotheses: R15,R17
- Data: Qld tracked races; pars fit <2025 (4,730 scored races (1,260 complete))
- Compared: 8 figure versions vs avg finishing position last 3, matched races
- Result: recency-weighted best: 20.7% vs 19.8% top picks (+1.0, -0.5 to +2.4); fit -0.009/race (-0.021 to +0.004); losses in 1500m+ races
- After other factors: recency version adds 0.005/race inside full model
- Next: pace-correct staying figures; real ages for weight-for-age
- Script: `inv17_rating_variants.py` -> `out_s1_*.csv`

## B2-2 Complete-figure sample
- Validity: descriptive
- Question/hypotheses: -
- Data: as B2-1 (4,730 races)
- Compared: complete vs incomplete races
- Result: 26% complete is arithmetic (87.4% of runners have a figure); complete races are smaller, rarely maidens, more country
- After other factors: rankings unchanged
- Next: use all races with missing flags
- Script: `inv17_rating_variants.py` -> `out_s1_complete_selection.csv`

## B2-3 Evidence groups: independent contributions
- Validity: chronological out-of-sample
- Question/hypotheses: R18,R23,R28,R29,R30,R31
- Data: Qld tracked races; fit <2025, score 2025-26 (91,223 runners; 4,652 fit / 4,730 scored races)
- Compared: each group alone, added to form, dropped from full model
- Result: ability +0.031 beyond all; fitness +0.003; race shape +0.003 (borderline, metro +0.007); sectional 0; track/distance -0.003
- After other factors: as stated
- Next: replicate in NSW/Vic; rebuild track/distance
- Script: `inv18_evidence_groups.py` -> `out_s2_*.csv`

## B2-4 Combined model vs profiles vs trees; agreement
- Validity: chronological out-of-sample
- Question/hypotheses: -
- Data: as B2-3 (as B2-3)
- Compared: combined vs stacked profiles vs boosted trees; agreement counts
- Result: combined beats stacked +0.005/race (0.001-0.010); trees no better; agreement strong descriptively (3 groups: 26.5% win) but adds nothing to combined model
- After other factors: agreement no
- Next: one combined model built in blocks
- Script: `inv18_evidence_groups.py; inv19_secondary.py` -> `out_s2_*.csv, out_s2b_secondary.csv`

## B2-5 Opposition, class labels, weight level
- Validity: chronological out-of-sample
- Question/hypotheses: R18,R40,R49
- Data: as B2-3; R40 next-start frame (R40: 21,461 fit / 22,088 scored runs)
- Compared: with/without each input
- Result: opposition strength +0.004 (0.003-0.006); weight vs field +0.007 (0.004-0.011); R40 field-strength move beats label move (log loss 0.32412 vs 0.32507)
- After other factors: yes
- Next: R20 after the backfill
- Script: `inv19_secondary.py` -> `out_s2b_*.csv`
## B3-6 Pace-adjusted figures (sectionals)
- Validity: chronological out-of-sample (Qld only)
- Data: Qld tracked races; slopes and pars fit <2025, score 2025-26 (4,730 races, 45,305 runners, 8,436 horses (metro 1,289; 1400m+ 1,703))
- Compared: PA1 tempo-corrected figure, late-section figure, run profile vs v0 figure; inside frozen benchmark combined_v1
- Result: PA1 beats v0 alone: 1400m+ +0.014/race (0.004-0.025), all +0.007; inside benchmark +0.005 1400m+ (not clear); late section +0.002 (passes); run profile +0.003
- After other factors: partly: late section and run profile add; PA1 swap not clear
- Next: distance-specific pace correction; benchmark v2 scored prospectively
- Script: `inv20_pace_figures.py; inv20b_pa1_vs_form.py` -> `out_s6_*.csv`

