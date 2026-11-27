# Tipping report card (observational; notional flat units; percentages and counts only)

Updated with 2026-11-27. Ledger: outputs/tipping_ledger.csv. OPEN = TAB fixed win at the 7:30am run; CLOSE = final TAB fixed win in the completed racecard; each ROI uses only selections with that price. Scratched = void; abandoned or unpublished races = void; dead heats divide the price; TAB late-scratching deductions are not published and not applied. No tote, SP or Betfair substitutes. Not an optimisation target.

## Calibration: every settled runner, by published calibrated chance

| band     |   runners |   mean_predicted_pct |   won_pct |
|:---------|----------:|---------------------:|----------:|
| under 5% |       229 |                  2.7 |       2.2 |
| 5-10%    |       223 |                  7.1 |       5.4 |
| 10-20%   |       214 |                 14.1 |      17.8 |
| 20-30%   |        66 |                 24.3 |      22.7 |
| 30%+     |        49 |                 35.7 |      36.7 |

| group                                |   selections |   settled |   void_scratched |   void_no_result |   winners |   strike_rate_% |   expected_winners |   actual_over_expected |   mean_predicted_% |   open_eligible |   open_price_missing |   roi_open_% |   close_eligible |   close_price_missing |   roi_close_% |   dead_heat_wins |   winners_in_races_with_late_scratchings |
|:-------------------------------------|-------------:|----------:|-----------------:|-----------------:|----------:|----------------:|-------------------:|-----------------------:|-------------------:|----------------:|---------------------:|-------------:|-----------------:|----------------------:|--------------:|-----------------:|-----------------------------------------:|
| All top picks                        |           90 |        88 |                1 |                1 |        23 |            26.1 |               26.3 |                   0.87 |               29.9 |              81 |                    7 |        -28.8 |               88 |                     0 |         -34.4 |                0 |                                        3 |
| Contender                            |          173 |       163 |                7 |                3 |        37 |            22.7 |               27.8 |                   1.33 |               17   |             151 |                   12 |         21.4 |              163 |                     0 |          11.6 |                0 |                                        5 |
| Insufficient evidence (not top pick) |           74 |        70 |                1 |                3 |         6 |             8.6 |                5.1 |                   1.19 |                7.2 |              67 |                    3 |        -55.5 |               70 |                     0 |         -46.3 |                0 |                                        2 |
| Outsider                             |          484 |       460 |               13 |               11 |        22 |             4.8 |               26.7 |                   0.82 |                5.8 |             441 |                   19 |        -53.2 |              460 |                     0 |         -51   |                0 |                                        5 |
| Top pick: Insufficient evidence      |            4 |         4 |                0 |                0 |         1 |            25   |                1.1 |                   0.91 |               27.5 |               4 |                    0 |        -56.2 |                4 |                     0 |         -62.5 |                0 |                                        0 |
| Top pick: Leading contender          |           22 |        22 |                0 |                0 |         3 |            13.6 |                5.9 |                   0.51 |               26.7 |              21 |                    1 |        -59.5 |               22 |                     0 |         -64.1 |                0 |                                        0 |
| Top pick: No clear selection         |           20 |        19 |                0 |                1 |         5 |            26.3 |                3.9 |                   1.28 |               20.6 |              19 |                    0 |         28.9 |               19 |                     0 |          13.2 |                0 |                                        1 |
| Top pick: Strong selection           |           44 |        43 |                1 |                0 |        14 |            32.6 |               15.5 |                   0.91 |               35.9 |              37 |                    6 |        -38   |               43 |                     0 |         -37.7 |                0 |                                        2 |

## All top picks by day (cumulative)

| date       |   settled |   winners |   cum_selections |   cum_winners |   cum_strike_% |   open_eligible |   cum_roi_open_% |
|:-----------|----------:|----------:|-----------------:|--------------:|---------------:|----------------:|-----------------:|
| 2026-11-26 |        29 |        10 |               29 |            10 |           34.5 |              29 |             -8.8 |
| 2026-11-27 |        59 |        13 |               88 |            23 |           26.1 |              52 |            -28.8 |
