# Victorian TripleS sectionals, 1 Jul - 25 Nov 2026 (STAGING ONLY)

Supplied by Damo on 26 Nov 2026 as `VIC_TripleS_original_CSVs_2026-07-01_to_2026-11-25.zip` (817 original CSVs).
Per the package README the files are the exact bytes of TripleS race CSV exports downloaded from Racing.com's file host
(d3qmfyv6ad9vwv.cloudfront.net); file names are Racing.com meeting id + race number. Claude did not collect them.
The untouched zip is kept on branch `raw-vic-triples`. All 817 sha256 checksums verified.

Not in the master database, not in any rating. Integration is a separate decision after review.

## What is here
- `races.csv` one row per file: date (from the meeting label's ISO date), meeting id, race no, race name, layout, course code,
  distance (= last section mark), runners, tracked runners, fastest tracked runner and time, package flag.
- `runners.csv` one row per horse per race: row order, horse, saddlecloth, tracked (0 = every time zero), total tracked time.
- `sections.csv.gz` one row per horse per section: section end (m from start), length, time, cumulative time, the file's
  speed (speed AT the mark, m/s) and the section average (length / time).
- `validation.csv` each race against our Victorian race lists (Betfair-sourced names, saddlecloths and winners; no prices read).
- `checks.txt` the counts below. `coverage.csv`, `flagged_originals.csv`, `summary.json` are from the package, unchanged.

## How to read the files (learned while staging)
- Two layouts: 93 files with a 5-field first line (date; meeting; race; time; course code) and 724 with 3 fields.
- The first-field date is day/month in 84 files and month/day in 9; the meeting label's ISO date always agrees with the folder.
- The course code (e.g. SANL_1600m_TRACK) names the course; it is NOT the race distance (differs in 58 of 90 files).
- The 5-field time is NOT the winner's time (median 2.3 s slower than the fastest tracked runner). Not used.
- The speed column is the speed at each mark, not the section average.
- A runner with every time zero was scratched (2,142 of 2,154 such runners are absent from the official field) or, in 12
  cases, ran without tracking. Kept and flagged; never treated as a run.
- Row order is not documented as finishing order; finishing positions must come from official results, not from here.

## Validation (races to 31 Oct, where our lists exist)
- 666 of 671 races matched; the other 5 (Ballarat 6 Aug R4-R7, Pakenham 2 Oct R2) are missing from OUR lists, not the files.
- Tracked runners found in the official field: 6,777 / 6,777 in matched races; saddlecloths agree 6,777 / 6,777.
- No official starter is missing from a TripleS file.
- Fastest tracked runner = official winner in 663 / 666. The 3 others: two photo finishes (0.01 s apart, timing cannot split
  them) and one file the package already flagged (a runner's times are broken: 60 s gap).
- Distance agrees with our lists in 663 / 666 (12 Jul R4, R5: 1500 vs 1600; 9 Oct R1: 2648 vs 2600) - flagged for review.
- 146 races from 1-25 Nov checked internally only (our lists end 31 Oct).

## Coverage
TripleS files exist for metropolitan and major provincial tracks (Ballarat, Caulfield, Sandown, Pakenham, Bendigo, Geelong,
Flemington, Cranbourne, Mornington, The Valley). Country meetings (715 races) use a different provider, Daily Sectionals,
whose CSVs were not offered; 76 races had nothing. So this covers 817 of 1,608 Victorian races (51%).
