# Weekly master-database update

- Run (Brisbane): 2026-11-26; previous Breednet history to 2026-11-23; collecting 2026-11-14 to 2026-11-25 (re-fetching recent days picks up corrections)

- Breednet: 96 meetings collected, 0 empty, 0 errors, CAPTCHA stop: False
- Venues on Breednet with no state in venue_states.json (not collected): none
- Breednet retry list (1 meetings): 0 collected, 0 empty, 1 errors

```
bn_meeting rows before 9461 after 9484 | replaced or added 96
bn_race rows before 73364 after 73522 | replaced or added 763
bn_runner rows before 697341 after 698496 | replaced or added 6669
check                                                                                 what            expected                    got status
   B8                          jump-outs / barrier trials flagged (excluded from analysis)            reported    2720 of 73522 races   INFO
   B0                                                     meetings / states / races loaded                   -       9484 / 7 / 73522   INFO
  B0b                                                                       runners loaded                   -                 698496   INFO
   B1                                   meetings whose venue has no state (not in Betfair) few (picnic venues)                      0   PASS
   B2                                            meetings also in Betfair: same race count                 all           8368 of 8454   FLAG
   B3                                          meetings also in Betfair: same runner count          nearly all           7030 of 8454   FLAG
   B4                                        winners that match Betfair (meetings in both)              >= 99%         65926 of 66261   PASS
   B5                                              races with a plausible time / last 600m          nearly all 72928 / 58622 of 73083   PASS
   B6                placed-behind runners with no margin (races only, jump-outs excluded)                 few          235 of 612353   PASS
   B7 NSW overlap with Racing NSW results: same horse at same place, weight carried agrees                 all         17431 of 17434   PASS
state    y  meetings  races
  ACT 2022         6   50.0
  ACT 2023        19  154.0
  ACT 2024        19  148.0
  ACT 2025        18  135.0
  ACT 2026        14  110.0
  NSW 2022       181 1344.0
  NSW 2023       697 5183.0
  NSW 2024       660 4932.0
  NSW 2025       660 4912.0
  NSW 2026       605 4484.0
  QLD 2022       153 1122.0
  QLD 2023       521 3852.0
  QLD 2024       501 3673.0
  QLD 2025       520 3771.0
  QLD 2026       470 3451.0
   SA 2022        46  378.0
   SA 2023       171 1366.0
   SA 2024       173 1377.0
   SA 2025       170 1370.0
   SA 2026       190 1562.0
  TAS 2022        22  170.0
  TAS 2023        71  566.0
  TAS 2024        71  568.0
  TAS 2025        70  564.0
  TAS 2026        56  457.0
  VIC 2022       130 1085.0
  VIC 2023       501 4068.0
  VIC 2024       499 4101.0
  VIC 2025       497 4013.0
  VIC 2026       639 5878.0
   WA 2022        71  562.0
   WA 2023       280 2149.0
   WA 2024       273 2082.0
   WA 2025       271 2061.0
   WA 2026       239 1824.0
```

- Racing Queensland: {'races': 89, 'runners': 1229, 'secs': 5772, 'fields': 861, 'log': 22} -> /home/runner/work/racing-intelligence/racing-intelligence/rq_weekly/racing_rq_weekly_20261114_20261125.zip

```
bundles: ['racing_rq_weekly_20261114_20261125.zip']
incremental: {'x_race': (9758, 9765), 'x_runner': (126121, 126222), 'x_sec': (635831, 636340), 'x_field': (94344, 94416)}
checks:
   B1 | Betfair rows with a readable date and time | 1303266 | 1303266 dates, 1303266 times; 16057 rows in day-first format (Apr 2025 file) | PASS
   K1 | Meetings with a tracking ZIP fetched | 1267 | 1264 | FLAG
   K2 | Meetings with a Race Fields PDF fetched | 1267 | 1266 | FLAG
   K3 | Files that failed to parse | 0 | 0 | PASS
   K4 | Races where tracking starters = Race Fields runners (same saddlecloths) | 9673 | 9616 | FLAG
   K5 | Starters whose segment times add to the official time (±0.05s) | 93206 | 92233 | FLAG
   K6 | Tracked Qld races found in Betfair | 9757 | 9587 | FLAG
   K7 | Matched races: Betfair runners = tracking starters | 9587 | 9543 | FLAG
   K8 | Matched races: Betfair winner = tracking rank 1 | 9587 | 9554 | FLAG
   K9 | Matched races: Betfair distance = Race Fields distance | 9587 | 9460 | FLAG
   K10 | Barrier differs from saddlecloth (tracking draw field not used) | 92282 | 84655 differ, 7627 equal | PASS
   H1 | Names carrying more than one numeric RQ horse code (different horses sharing a name) | 0 | 5 | FLAG
   H2 | Meetings using the AUS- horse code instead of the numeric code | 0 | 62 meetings, 2026-02-18 to 2026-06-06 | FLAG
   H3 | Horses keeping the same numeric code either side of the AUS- period | 2559 | 2558 | PASS
   K8b | Winner mismatches explained by dead heats | 45 | 28 | FLAG
   D1 | Qld meetings in Betfair 2025 at venues with no RQ tracking (country/picnic history comes from Betfair only) | - | 108 of 463 | FLAG
tables: {'race': 9765, 'starter': 126224, 'sectional': 636340, 'bf_runner': 1303266}
```

- South Australian tracking: 10 SA meetings in the window; 24 races staged, 21 passed every check and were loaded; sa_race 1775 -> 1775, sa_starter 18822 -> 18822, sa_sectional 133905 -> 133905

- TAB form staging (research only): form staging: no form files yet
- rebuilt: build_runs.py /home/runner/work/racing-intelligence/racing-intelligence/history/history.duckdb runs.parquet (4s)
- rebuilt: rating_v0.py runs.parquet runs_rated_dev.parquet --fit-until=2024-12-31 (6s)
- rebuilt: rating_v0.py runs.parquet runs_rated.parquet (6s)
- rebuilt: features.py runs_rated_dev.parquet /home/runner/work/racing-intelligence/racing-intelligence/history/history.duckdb features.parquet (105s)
- rebuilt: inv20_pace_figures.py /home/runner/work/racing-intelligence/racing-intelligence/history/history.duckdb (159s)
- rebuilt: national.py /home/runner/work/racing-intelligence/racing-intelligence/history/history.duckdb (803s)
- rebuilt: ops/build_dyn_nat_qld.py (7s)
- rebuilt: engine/lab.py (34s)
- rebuilt: engine/build_frame_v3.py (34s)

| Check | Result |
| --- | --- |
| no table lost rows | PASS |
| frame did not shrink | PASS |
| every old run still present | PASS |
| old ratings barely moved (95th pct < 0.5 kg) | PASS |
| history advanced or held | PASS |
| Queensland runs did not shrink | PASS |
| no Queensland file failed to parse | PASS |

- Rows before -> after: bn_meeting 9461 -> 9484, bn_race 73364 -> 73522, bn_runner 697341 -> 698496, race 9758 -> 9765, starter 126123 -> 126224, sa_race 1775 -> 1775, sa_starter 18822 -> 18822, sa_sectional 133905 -> 133905
- National frame rows 682430 -> 683346; Queensland runs 93134 -> 93206; history to 2026-11-25
- Rating change on existing runs: mean 0.000 kg, 95th pct 0.000 kg, max 3.40 kg
