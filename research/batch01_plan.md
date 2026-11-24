# Batch 1 plan (written 24 Nov 2026, before any of these analyses were run)

No market prices, odds or market-derived inputs are used anywhere. All "pre-race" measures come from runs before the race.

## Periods
- Development: Queensland races before 1 Jan 2025 (Oct 2022 - Dec 2024). Models, pars and cut-offs are fitted here only.
- Internal evaluation: Queensland races 1 Jan 2025 - 23 Nov 2026. Out-of-sample for the fitted models, but NOT independent of
  the researcher: these races were already looked at for R1-R16. Results here are labelled "internal out-of-sample".
- Independent: Racing NSW career form lines, non-Queensland races (B3, B4). Forward: Queensland races from 25 Nov 2026,
  scored later with the definitions frozen in this file.
- Multiple testing: the six primary tests below are adjusted together (Benjamini-Hochberg, 10% false discovery rate).
  Everything else is secondary and reported as descriptive.

## B1. Rating v0 against simple baselines (R15, R17)
Question: does the pre-race figure pick winners better than simple form, class and weight measures, and does it add
information beyond all of them together?
Ratings refitted with pars and class allowances from the development period only (`rating_v0.py --fit-until 2024-12-31`).
Population: evaluation races, fields of 6+, where every runner has at least one earlier figure.
Pre-race measures: best of last 3 figures (R15), last figure, average of last 3 (R17); baselines: last-start finishing position
(relative to field), last-start margin, average finishing position of last 3, career win % before the race, class level
of the last race, weight carried today (handicaps only: the handicapper's assessment).
Metrics: top-pick win %, A/E against field size, and conditional-logit log-likelihood per race (fitted on development,
scored on evaluation).
Primary test 1: adding the best-of-3 figure to a model holding all baselines improves evaluation log-likelihood
(bootstrap 95% CI over meetings excludes zero).

## B2. R9 interaction profile (R9, R14, R22, R25, IP1)
Question: do combinations of closing sectional with distance change, early tempo, class move, figure and race strength add
predictive information beyond the same factors used separately?
Population: beaten finishers, fields 6+, true next start 7-60 days later (as `frames.py`).
M1 main effects: gap to the race's best last 600m (s), distance-change band, tempo band, class change (kg), run figure,
best pre-race figure, field strength, settling position, log days to next run, log margin, log next field, venue tier,
distance band. M2 = M1 + interactions of the last-600m gap with: step up, tempo, class change, field strength, figure.
Trees: gradient-boosted trees limited to depth 1 (no interactions possible) vs depth 3 (interactions allowed), same inputs,
tuned on 2024 inside the development period.
Primary test 2: M2 improves evaluation log-loss over M1 (bootstrap CI over meetings).
Primary test 3: the depth-3 trees improve evaluation log-loss over the depth-1 trees.
Secondary: interaction block Wald test on development data (horse-clustered); same blocks with next figure change as outcome (R25).

## B3. R13 outside Queensland
Question: do ordinary beaten runners stepping up 200m+ underperform next start in NSW and other non-Queensland races?
Data: Racing NSW form lines, non-Queensland tracks, race (not trial) runs Oct 2022 - Nov 2026, next race run 7-60 days later
(the form lines list every run, so consecutive race lines are true consecutive starts; trials in between are allowed).
Population: beaten finishers, fields 6+, next field 6+.
Primary test 4: logit next win ~ step up 200m+ + log margin + log next field, horse-clustered; Queensland found 0.84-0.90.
Limitation: only horses racing in NSW since July 2026 (survivor bias); no individual sectionals, so R9 itself can't be tested.

## B4. Weight change (R41)
Question: does a weight drop of 2kg+ from last start improve the next run once class change, margin, field and figure are
allowed for, and does it depend on the class move?
Queensland: all finishers with a true next start 7-60 days later; weight change = next weight - this weight; bands
drop 2kg+, within 1.5kg, rise 2kg+. Outcome next win (figures already credit weight, so they are not used as outcome).
Primary test 5 (Queensland): odds for drop 2kg+ vs within 1.5kg, adjusted, horse-clustered, development + evaluation pooled
(this question was not examined before).
Primary test 6 (NSW form lines, independent): same model, carried weight (claim deducted where shown).
Secondary: weight band x class move interaction; handicaps only.
