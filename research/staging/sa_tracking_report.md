# Racing SA tracking staging report

Built 2026-11-25 16:21Z from /tmp/sa/rawfull. Staging only: not in the master database, not read by production.

- Report formats found: tripleSdata 1738, tripleSdata_2026 254, daily_sectionals 70
- tripleSdata tracking from 2024-01-01; older Daily Sectionals (race-level + late splits, kept as text, not staged) until 2023-12-30
- Files requested 2195; found (200) 2062; not found 133; other 0
- Races staged 1954; runners 20868; 200 m segments 147439
- Races passing every check 1829 (93.6%)
- Breednet name match 20866/20868 runners; finishing position agrees 20729, disagrees 137
- Distance agrees with Breednet in 1949/1954 races
- Splits add up to the runner's time (within 0.06 s) for 98.9% of runners (race average)
- Positions form 1..n at every section in 1888/1954 races
- Stride frequency x length vs average speed: median relative error 0.013 (Qld: 0.013)
- Duplicate race ids: 1

## Coverage (races staged by month and track)

| month   |   Gawler |   Morphettville |   Morphettville_Parks |   Murray_Bridge |
|:--------|---------:|----------------:|----------------------:|----------------:|
| 2024-01 |       18 |              10 |                     0 |              23 |
| 2024-02 |       14 |              10 |                    17 |               7 |
| 2024-03 |        0 |              17 |                    16 |              14 |
| 2024-04 |       12 |              16 |                     9 |               6 |
| 2024-05 |        8 |              18 |                     9 |              24 |
| 2024-06 |       16 |              18 |                    18 |               9 |
| 2024-07 |       25 |               9 |                     9 |              28 |
| 2024-08 |        7 |              18 |                    18 |              18 |
| 2024-09 |        0 |               9 |                    27 |              17 |
| 2024-10 |       14 |              27 |                     6 |              10 |
| 2024-11 |       14 |              27 |                    26 |               6 |
| 2024-12 |        9 |               8 |                    18 |               9 |
| 2025-01 |        0 |               9 |                     7 |              43 |
| 2025-02 |        0 |              18 |                    18 |               7 |
| 2025-03 |        0 |              17 |                    24 |              10 |
| 2025-04 |        0 |              17 |                     9 |              14 |
| 2025-05 |        7 |              27 |                     9 |              17 |
| 2025-06 |       16 |               9 |                    18 |              10 |
| 2025-07 |       16 |               9 |                     9 |              25 |
| 2025-08 |       14 |              18 |                    26 |              18 |
| 2025-09 |        0 |              16 |                    26 |               7 |
| 2025-10 |       14 |              22 |                     7 |              15 |
| 2025-11 |       14 |              28 |                    27 |               7 |
| 2025-12 |        9 |              17 |                    15 |              16 |
| 2026-01 |       16 |              11 |                     0 |              25 |
| 2026-02 |        7 |              19 |                    19 |               8 |
| 2026-03 |        0 |              18 |                    20 |              10 |
| 2026-04 |        7 |              19 |                    10 |              18 |
| 2026-05 |        7 |              27 |                     9 |              17 |
| 2026-06 |        0 |               9 |                    18 |               9 |
| 2026-07 |        0 |              17 |                    18 |              32 |
| 2026-08 |        0 |              18 |                    27 |              15 |
| 2026-09 |        6 |               9 |                    17 |              26 |
| 2026-10 |       15 |              36 |                     0 |              16 |
| 2026-11 |       14 |              19 |                    17 |               0 |

## Meetings found per club (race 1 asked)

| slug                |   meetings_asked |   meetings_found |
|:--------------------|-----------------:|-----------------:|
| balaklava           |                2 |                0 |
| bordertown          |                2 |                0 |
| clare               |                2 |                0 |
| gawler              |               51 |               41 |
| morphettville       |              101 |               72 |
| morphettville-parks |               70 |               62 |
| mt-gambier          |                6 |                0 |
| murray-bridge-gh    |              105 |               68 |
| naracoorte          |                2 |                0 |
| oakbank             |                4 |                0 |
| penola              |                2 |                0 |
| port-lincoln        |               10 |                0 |
| strathalbyn         |                6 |                0 |

## Clubs not collected (report folder unknown)

halidon, kingscote, port-augusta

## Races failing a check (first 40)

| race_id                         |   runners |   runners_with_segments |   bn_name_matched |   bn_finish_disagree |   distance_pdf |   distance_bn |   split_sum_ok_share | positions_ok   |   parse_problems |
|:--------------------------------|----------:|------------------------:|------------------:|---------------------:|---------------:|--------------:|---------------------:|:---------------|-----------------:|
| 20240113-Murray_Bridge-R2       |        14 |                       0 |                14 |                    0 |           1000 |          1000 |              nan     | True           |               14 |
| 20240217-Morphettville_Parks-R2 |        12 |                       0 |                12 |                    0 |           1000 |          1000 |              nan     | True           |               12 |
| 20240217-Morphettville_Parks-R8 |        11 |                       0 |                11 |                    0 |           1000 |          1000 |              nan     | True           |               11 |
| 20240224-Morphettville-R6       |        13 |                      13 |                13 |                    0 |           1050 |          1050 |                0.077 | True           |                0 |
| 20240302-Morphettville_Parks-R7 |        11 |                       0 |                11 |                    0 |           1000 |          1000 |              nan     | True           |               11 |
| 20240316-Morphettville_Parks-R1 |        11 |                       0 |                11 |                    0 |           1000 |          1000 |              nan     | True           |               11 |
| 20240316-Morphettville_Parks-R8 |        11 |                       0 |                11 |                    0 |           1000 |          1000 |              nan     | True           |               11 |
| 20240316-Morphettville_Parks-R9 |        14 |                      14 |                14 |                    0 |           1400 |          1400 |                1     | False          |                0 |
| 20240320-Murray_Bridge-R2       |        12 |                       0 |                12 |                    0 |           1000 |          1000 |              nan     | True           |               12 |
| 20240320-Murray_Bridge-R7       |        13 |                       0 |                13 |                    0 |           1000 |          1000 |              nan     | True           |               13 |
| 20240323-Morphettville-R9       |        15 |                      15 |                15 |                    0 |           1200 |          1200 |                0     | True           |                0 |
| 20240406-Morphettville_Parks-R1 |         4 |                       4 |                 4 |                    0 |           2250 |          2250 |                1     | False          |                0 |
| 20240410-Gawler-R5              |        10 |                      10 |                10 |                    0 |              0 |          1200 |                1     | True           |                0 |
| 20240511-Morphettville-R7       |        14 |                      14 |                14 |                    0 |           1600 |          1600 |                1     | False          |                0 |
| 20240608-Morphettville_Parks-R3 |        10 |                      10 |                10 |                    5 |           1250 |          1250 |                1     | True           |                0 |
| 20240626-Gawler-R3              |        11 |                      11 |                11 |                    0 |              0 |          1100 |                0     | True           |                0 |
| 20240626-Gawler-R7              |        11 |                      11 |                10 |                    1 |           1516 |          1516 |                1     | True           |                0 |
| 20240706-Gawler-R4              |         9 |                       9 |                 9 |                    2 |           1500 |          1500 |                1     | True           |                0 |
| 20240717-Gawler-R1              |        11 |                      11 |                11 |                   10 |           2112 |          2112 |                1     | True           |                0 |
| 20240803-Murray_Bridge-R9       |        15 |                      15 |                15 |                    1 |           1400 |          1400 |                1     | False          |                0 |
| 20240814-Murray_Bridge-R1       |        11 |                      11 |                11 |                    0 |            900 |           900 |                1     | False          |                0 |
| 20240814-Murray_Bridge-R8       |        15 |                      15 |                15 |                    2 |           1800 |          1800 |                1     | True           |                0 |
| 20240914-Morphettville-R5       |        11 |                      11 |                11 |                    0 |           1536 |          1536 |                1     | False          |                0 |
| 20241007-Gawler-R7              |        11 |                      11 |                11 |                    0 |           1516 |          1516 |                1     | False          |                0 |
| 20241025-Gawler-R1              |         7 |                       7 |                 7 |                    0 |           2100 |          2100 |                0     | True           |                0 |
| 20241105-Morphettville-R5       |         9 |                       9 |                 9 |                    5 |           1800 |          1800 |                1     | True           |                0 |
| 20241107-Gawler-R1              |        11 |                       0 |                11 |                    0 |           1000 |          1100 |              nan     | True           |               11 |
| 20241107-Gawler-R7              |        12 |                      12 |                12 |                    0 |           1200 |          1200 |                0     | True           |                0 |
| 20241113-Murray_Bridge-R3       |        13 |                      13 |                13 |                    0 |           1800 |          1800 |                1     | False          |                0 |
| 20241113-Murray_Bridge-R4       |         9 |                       9 |                 9 |                    0 |           2500 |          2500 |                1     | False          |                0 |
| 20241123-Morphettville-R7       |        11 |                      11 |                11 |                   10 |           1600 |          1600 |                1     | True           |                0 |
| 20241127-Gawler-R4              |         8 |                       8 |                 8 |                    0 |           1500 |          1500 |                0     | True           |                0 |
| 20241127-Gawler-R5              |        11 |                      11 |                11 |                    0 |           1200 |          1200 |                1     | False          |                0 |
| 20241127-Gawler-R6              |        10 |                      10 |                10 |                    0 |           1700 |          1700 |                0     | True           |                0 |
| 20241130-Morphettville_Parks-R3 |         9 |                       9 |                 9 |                    3 |           1950 |          1950 |                1     | True           |                0 |
| 20241221-Murray_Bridge-R4       |        11 |                      11 |                11 |                    7 |           2000 |          2000 |                1     | True           |                0 |
| 20250101-Murray_Bridge-R4       |         9 |                       9 |                 9 |                    0 |            900 |           900 |                1     | False          |                0 |
| 20250101-Murray_Bridge-R6       |        14 |                      14 |                13 |                    0 |           1200 |          1200 |                1     | True           |                0 |
| 20250124-Murray_Bridge-R3       |        13 |                      13 |                13 |                   12 |           1400 |          1400 |                1     | True           |                0 |
| 20250124-Murray_Bridge-R6       |        10 |                      10 |                10 |                    0 |            900 |           900 |                1     | False          |                0 |

## Parse problems (first 30)

- 30558/2024-01-13_race02_sectional.pdf: IN MY ROOM: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: BLANC VISAGE: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: KALBARRI: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: MAHI MAHI: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: POPSTAR PRINCESS: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: HER EXCELLENCY: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: THE LAST DANCE: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: SIOUX WARRIOR: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: PRODIGAL LAD: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: ESTICON: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: TAMERICA: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: MAGIC FIELD: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: RHINESTONE RORY: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30558/2024-01-13_race02_sectional.pdf: BARYNYA: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: ZANTHRON: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: ENDLESS FAITH: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: PURE BLISS: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: OAKLAND RAIDER: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: HISWAY: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: GOTTA GO GURU: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: TOI ET MOI: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: FLYIN' FOR US: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: CINCHONA: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: BLANC VISAGE: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: LITTLE RICH LADY: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race02_sectional.pdf: MIGHTY EDGY: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race08_sectional.pdf: EL SALTO: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race08_sectional.pdf: SECRET WAR: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race08_sectional.pdf: STORM VOYAGER: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
- 30072/2024-02-17_race08_sectional.pdf: KAIDO: unexpected column order ['Overall', 'L1000', 'L800', 'L600', 'L400']
