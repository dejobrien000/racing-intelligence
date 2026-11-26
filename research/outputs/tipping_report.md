# Tipping report card (observational; notional flat units; percentages and counts only)

Updated with 2026-11-26. Ledger: outputs/tipping_ledger.csv. OPEN = TAB fixed win at the 7:30am run; CLOSE = final TAB fixed win in the completed racecard; each ROI uses only selections with that price. Scratched = void; abandoned or unpublished races = void; dead heats divide the price; TAB late-scratching deductions are not published and not applied. No tote, SP or Betfair substitutes. Not an optimisation target.

## Calibration: every settled runner, by published calibrated chance

| band     |   runners |   mean_predicted_pct |   won_pct |
|:---------|----------:|---------------------:|----------:|
| under 5% |        80 |                  2.5 |       3.8 |
| 5-10%    |        69 |                  6.9 |       2.9 |
| 10-20%   |        69 |                 14.5 |      15.9 |
| 20-30%   |        21 |                 23.9 |      19   |
| 30%+     |        19 |                 35.2 |      47.4 |

| group                                |   selections |   settled |   void_scratched |   void_no_result |   winners |   strike_rate_% |   expected_winners |   actual_over_expected |   mean_predicted_% |   open_eligible |   open_price_missing |   roi_open_% |   close_eligible |   close_price_missing |   roi_close_% |   dead_heat_wins |   winners_in_races_with_late_scratchings |
|:-------------------------------------|-------------:|----------:|-----------------:|-----------------:|----------:|----------------:|-------------------:|-----------------------:|-------------------:|----------------:|---------------------:|-------------:|-----------------:|----------------------:|--------------:|-----------------:|-----------------------------------------:|
| All top picks                        |           29 |        29 |                0 |                0 |        10 |            34.5 |                8.8 |                   1.13 |               30.4 |              29 |                    0 |         -8.8 |               29 |                     0 |         -15.5 |                0 |                                        1 |
| Contender                            |           56 |        55 |                1 |                0 |        10 |            18.2 |                9.9 |                   1.01 |               17.9 |              55 |                    0 |        -32.2 |               55 |                     0 |         -27.4 |                0 |                                        1 |
| Insufficient evidence (not top pick) |           20 |        20 |                0 |                0 |         1 |             5   |                1.3 |                   0.75 |                6.7 |              20 |                    0 |        -86.5 |               20 |                     0 |         -87.5 |                0 |                                        0 |
| Outsider                             |          155 |       154 |                1 |                0 |         8 |             5.2 |                8.5 |                   0.94 |                5.5 |             154 |                    0 |        -43.2 |              154 |                     0 |         -40.6 |                0 |                                        0 |
| Top pick: Insufficient evidence      |            1 |         1 |                0 |                0 |         1 |           100   |                0.3 |                   2.88 |               34.7 |               1 |                    0 |         75   |                1 |                     0 |          50   |                0 |                                        0 |
| Top pick: Leading contender          |            7 |         7 |                0 |                0 |         2 |            28.6 |                1.9 |                   1.07 |               26.6 |               7 |                    0 |        -22.9 |                7 |                     0 |         -28.6 |                0 |                                        0 |
| Top pick: No clear selection         |            6 |         6 |                0 |                0 |         2 |            33.3 |                1.2 |                   1.62 |               20.6 |               6 |                    0 |         75   |                6 |                     0 |          56.7 |                0 |                                        0 |
| Top pick: Strong selection           |           15 |        15 |                0 |                0 |         5 |            33.3 |                5.4 |                   0.93 |               35.8 |              15 |                    0 |        -41.3 |               15 |                     0 |         -42.7 |                0 |                                        1 |

## All top picks by day (cumulative)

| date       |   settled |   winners |   cum_selections |   cum_winners |   cum_strike_% |   open_eligible |   cum_roi_open_% |
|:-----------|----------:|----------:|-----------------:|--------------:|---------------:|----------------:|-----------------:|
| 2026-11-26 |        29 |        10 |               29 |            10 |           34.5 |              29 |             -8.8 |
