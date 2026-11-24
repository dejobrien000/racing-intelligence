# Queensland history load (24 Nov 2026)

Rebuild in about 10 seconds:

1. Put the 12 bundles (racing_rq_2022.zip ... racing_rq_2026.zip, racing_betfair_2020.zip ... racing_betfair_2026.zip) in one folder.
   They are in your Downloads folder.
2. `pip install duckdb`
3. `python3 load_history.py <that folder>`  ->  history.duckdb and out/*.csv

`browser_bundle.js` is the script that built the bundles in Chrome (RQ tracking ZIPs + Race Fields PDFs for every tracked
Queensland meeting, and Betfair's national files with every price column removed). Each RQ bundle keeps the raw files
under raw/ and a per-file log (URL, HTTP status, size, SHA-256, time taken) in parsed/log.psv.

Coverage: 1,263 Queensland meetings (29 Oct 2022 - 22 Nov 2026), 9,758 races, 93,134 starters, 635,831 timing segments;
Betfair 2020 - Oct 2026, 1,303,266 runner rows across all states and NZ. Checks: out/checks.csv.

## Added 24 Nov 2026
- `load_breednet.py <folder> <db>`: Breednet results -> `bn_meeting`, `bn_race`, `bn_runner` (state from the Betfair venue
  map). Checks B0-B7 to `out/checks_breednet.csv`: race and runner counts and winners against Betfair, plausible times,
  margins, and agreement with Racing NSW results where they overlap. Refuses any record with price text.
  Note on B3: Betfair files sometimes hold a race twice, and include late scratchings, so a few runner counts differ.
- `load_nsw_allform.py <folder> <db>`: Racing NSW career form lines -> `nsw_form_line` (one row per past run, de-duplicated
  across pages), `nsw_form_horse`. Barrier on every race line; positions at 800/400m on most; race last 600m on ~85%.
  Track codes are RISA abbreviations (RAND, RHIL, W FM, ...); map to venues by joining on date + horse with Breednet.
