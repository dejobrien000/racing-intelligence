# Individual tracking data outside Queensland: access investigation (25-26 Nov 2026)

## Permission reported by Damo (recorded 25 Nov 2026, 11:54pm Brisbane)
Damo reports that he personally spoke with the sales director at Racing.com / Racing Victoria and with Racing Australia, who
expressed comfort with collection and use of their data for this private, non-commercial research project (personal use, no
redistribution, no wagering product). Verbal; no written confirmation held yet. Recommended: an email confirming scope
(personal research, storage, automated retrieval, no redistribution) and naming a technical contact.
25 Nov 11:55pm: Damo reports Racing Australia said to "push forward through" the robots.txt block. Not acted on: the block is
enforced by Claude's fetch tool, and a relayed verbal comment does not change the site's published crawler policy. The fix is on
Racing Australia's side (below).

## What was tested (25 Nov 2026, about 11:55pm-12:10am Brisbane), and the result
| Route | Result |
|---|---|
| racing.com speed-data page (form/2026-07-10/ladbrokes-geelong/race/1/speed-data) via Claude's fetch tool | Refused by the tool: SITE_BLOCKED. Same as earlier tests. This is a restriction on Claude's side, not a racing.com control, so the permission does not change it. Not worked around (no browser, scripts, GitHub runner, caches or mirrors). |
| racing.zendesk.com help article "What's improved" | Readable. Says only that CSV download for sectionals was restored; no fields, coverage or access details. |
| Prism help article (speed data) | Readable. Racing.com speed data for races in the previous 2 weeks only; Overview (distance run, early/mid/late/peak/average speed), Sectionals (time from each marker to the finish, position at each point), Splits (each 200 m); "Download Race Sectional Data" as PDF or CSV, one race at a time; no bulk export or API mentioned. |
| racingaustralia.horse (robots.txt, FreeFields results calendar) | Not fetched: robots_disallowed for automated agents across the site. A robots.txt block is a technical access control; verbal comfort does not lift it. |

Conclusion: no automated route exists today that respects these controls. The web pages are designed for one race at a time by a
person. Collection therefore needs an approved machine route from the data owner (below), not page scraping.

## Who measures what (public sources)
- Victoria: Racing Victoria's tracking is tripleSdata (with Champion Data). From 2021: Flemington, Moonee Valley, Caulfield, Sandown;
  by April 2024 six venues (plus Pakenham and Cranbourne). Country/provincial Victoria: race-level sectionals (Daily Sectionals), not
  individual tracking. So Victorian individual data from Oct 2022 should cover metro + Pakenham/Cranbourne only; exact start dates
  per venue to be confirmed by RV.
- South Australia: tripleSdata SMART tracking from 1 Jan 2024 (individual timing, sectional splits, stride).
- Queensland (what we already hold): tripleSdata since late 2022; stride frequency and length added March 2024.
- NSW: different provider (Punters' Intelligence sectional data for Racing NSW). Not the same platform as racing.com.
- So one provider, tripleSdata, measures Vic, SA and Qld in the same 200 m format. Our Queensland schema should carry Vic and SA
  data with little change.

## Field comparison against our Queensland tracking tables (provisional: no racing.com CSV seen)
| Field we hold for Qld (sectional / starter tables) | Racing.com / Prism speed data (documented) |
|---|---|
| finish_time_s (individual time) | Derivable from splits / "time from each marker to the finish" |
| split_s per 200 m segment | Yes ("Splits", every 200 m) |
| position per segment | Yes (position at each marker) |
| avg_speed_ms per segment | Speed values (early/mid/late/peak/average); per-200 m speed not confirmed |
| ground_m (distance covered) | Yes ("distance run") |
| dist_to_rail_m | Lane mentioned by VRC; column not confirmed |
| stride_len_m | Mentioned by VRC (stride length); column not confirmed |
| stride_freq_hz | Not confirmed |
The real column list must come from one genuine CSV (see the request) before any loader is written.

## Precise request for Racing.com / Racing Victoria's technical team
Context line: "Following [sales director]'s conversation with Damo on [date], approving use of racing.com data for his private,
non-commercial research (no redistribution, no wagering product), we need a machine route rather than per-race page downloads."
1. Historical archive: the same per-runner file as the speed-data page's "Download Race Sectional Data" CSV, for every tracked
   Victorian thoroughbred race from 1 Oct 2022 to date, as one bulk archive (one CSV per race, or per meeting), plus the column
   dictionary (units, the timing point for splits, how ground covered and lane are measured).
2. Every row keyed by: meeting date, venue, race number, saddlecloth, horse name (and Racing Australia horse ID if you hold it),
   official finishing position; trials/jump-outs flagged.
3. Fields, in priority order: individual finish time; each 200 m: split time, position, speed, distance covered, lane or distance
   from the rail, stride length, stride frequency; race-level official time, distance, rail position and track rating.
4. Ongoing: a weekly incremental delivery (each Monday, the previous 7 days) by an authenticated programmatic route: either an
   API endpoint with a key and stated rate limits, or files dropped to a shared folder (Google Drive, S3 or SFTP). Any key or
   password goes into secure storage, never into chat, logs or the repository.
5. Coverage confirmation: which venues are tracked and from which dates; whether stride fields exist before a given date; whether
   South Australian (tripleSdata) or NSW races are available through the same feed.
6. Written confirmation (email is enough) of the permitted use, storage and automated retrieval, and a technical contact.
Note for Damo: permission to scrape the website does not help, because Claude's fetch tool refuses racing.com and it will not be
worked around. The route must be files or an API.
If Racing Victoria points to its supplier, the same request goes to tripleSdata (covers Vic, SA and Qld in one format).

## Racing Australia (results with every finishing position, official horse IDs)
robots.txt blocks automated agents across racingaustralia.horse. Simplest fix: their web team adds an Allow rule in robots.txt for
Anthropic's user-request fetch agent on /FreeFields/ (results, fields), at a stated request rate. Otherwise: written approval and an approved machine route (results
file or API: every runner's finishing position, margin, weight carried, official horse ID, gear changes, stewards' reports), or the
name of their authorised data agent (Mediality Racing describes itself as Racing Australia's authorised agent).
Meanwhile TAB remains the price source; TAB's completed racecards give only the first four places (settle_yesterday.py marks the
rest 'unplaced'), and Breednet supplies full results in the weekly database update.

## Staging and validation before anything enters the master database (when files arrive)
- Raw files kept as delivered (hash recorded) in collect/tracking/<source>/<date>/; never edited.
- Staging tables mirroring the Queensland schema: stg_trk_race, stg_trk_runner (finish time, ground covered), stg_trk_segment
  (200 m split, position, speed, rail distance, stride length, stride frequency), each row carrying source file + hash.
- Checks: segment times sum to the runner's time (within 0.05 s); winner's time matches the official race time; time gaps match
  official margins at a plausible seconds per length; speed x time = segment distance; stride length x frequency = speed (Qld median
  error 1.3%); positions are a permutation per segment; every runner matched to the Breednet history by date + venue + race +
  saddlecloth + name; no duplicates; coverage report by venue and month.
- Only after a clean staging report and Damo's release decision does a weekly database release add the data (versioned on branch db,
  previous version kept). Research tests on staged data first; no production input changes without a release.
- Weekly incremental: the Monday database job reads the week's delivered files, stages, validates and reports; loading stays a
  release step.

## Update 26 Nov 12:15am: South Australia has a readable route
- Racing SA publishes a per-race sectional report as a PDF on its file CDN, linked from each race on racingsa.com.au ("Sectional
  Times"): d26j0amf97rmny.cloudfront.net/30072/<YYYY-MM-DD>_race<NN>_sectional.pdf. Fetched and read 2025-05-03 race 2
  (Morphettville, tripleSdata format, report created 13:53 the same day).
- Fields per runner: finish rank, overall time; per 200 m (L1000 ... L200): time to the finish [rank] (split), average speed, top
  speed, average distance to rail, average stride frequency, average stride length; plus barrier, first 400 m, fastest section,
  top speed, margin, distance travelled relative to the winner. Same content as our Queensland tracking tables (plus top speed).
- Older reports (2016-2019, Equitime) are race splits only and carry "no reproduction without written permission of Thoroughbred
  Racing South Australia". The 2025 report shows no notice. Racing SA was not among the bodies Damo spoke to: add them.
- Not yet known: the exact file name for every venue and date (two guesses for 2024-01-06 and 2026-11-25 returned not found; the
  links are drawn by the page's scripts). Next: read the link targets from race pages, then coverage by venue from Jan 2024.
  No URL guessing at scale.
- Victoria: no equivalent public route found; racing.com content will not be fetched from another host either (that would be
  going around the block).

## South Australia collection (26 Nov 2026, overnight; staging only)
- Decision: Damo 26 Nov 12:02am "Do SA overnight. Happy to proceed... We don't have to implement for tomorrow but need it built";
  12:03am "whatever you need to do to get this done overnight in the same shape as qld". Racing SA's permission not yet sought
  (Damo's call to proceed for private research). Nothing enters the master database or production without a release decision.
- Route: GitHub runner (the same route as the weekly Breednet/RQ collection). Racing SA's website answers the runner with an empty
  202 (bot protection), so it is not used. Only the public report host is read: honest User-Agent, robots.txt (none published),
  ~1.5 s pacing, stop after repeated refusals.
- Report folders (one per club), confirmed from published links: Morphettville + Morphettville Parks 30072, Murray Bridge 30558,
  Gawler 30272. Other clubs (Strathalbyn, Balaklava, Port Lincoln, Mt Gambier, Port Augusta, Oakbank, Bordertown, Naracoorte,
  Penola, Clare, Kingscote, Halidon): folder unknown, not guessed. Next: read a link from one of their race pages (needs a
  one-off approval for countryracingsa.com.au, or Damo copying one 'Sectional Times' link).
- File names: <date>_race<NN>_sectional.pdf (tripleSdata reports, from Jan 2024); older Daily Sectionals reports use race<N>
  (race-level + last-800 m splits by runner; kept as text, not staged as tracking).
- Code: collect/racingsa/collect.py (+ parse_sectional.py, gz_tolerant.py), .github/workflows/racingsa-tracking.yml -> branch
  raw-racingsa-tracking (files.csv manifest with sha256, texts.jsonl.gz page text). history/stage_sa_tracking.py builds the staged
  DuckDB with the Queensland table shape (sa_race, sa_starter, sa_sectional) plus checks and a report.
- Differences from Queensland to remember: sections are counted back from the finish (first section is the odd length, e.g. 50 m
  of a 1050 m race; Queensland's first section starts at the start); absolute ground covered is not published (only metres
  relative to the winner); weight is not in the report (Breednet's carried weight is kept separately).
- Weekly incremental (after a release decision): the Monday job adds the SA meetings of the previous 7 days from the Breednet
  calendar for the known folders, re-runs staging checks, and reports; loading stays a release step.

## Result, 26 Nov 2026 ~2:45am (staging built; not released)
- Collected: 2,195 report requests for the 272 meetings at Morphettville / Morphettville Parks / Murray Bridge / Gawler (Dec 2023 to
  21 Nov 2026): 2,062 found (243 meetings), 133 not found. Layouts: tripleSdata (Jan 2024 to Jul 2026) 1,738, redesigned
  'TRIPLESDATA GPS SECTIONALS' (late Jul 2026 on) 254, older Daily Sectionals (Dec 2023) 70 (kept as text only).
- Staged (branch staging-sa-tracking, parquet + MANIFEST; local copy pilot/staging/sa_tracking.duckdb): 1,954 races, 20,868
  runners, 147,439 sections. 1,829 races (93.6%) pass every check. Breednet name match 20,866/20,868; finishing position agrees
  20,729, disagrees 137 (23 races, flagged); distance agrees 1,949/1,954; splits sum to the runner's time 98.9%; stride x frequency
  vs speed median error 0.013 (Qld 0.013). Medians vs Qld 2024+: stride 7.20 m (Qld 7.35), 2.3 Hz (2.3), speed 16.83 m/s (17.04).
- Not available: per-section speed, stride and rail for the redesigned layout (late Jul 2026 on: drawn as charts, not read);
  absolute ground covered before that layout (only metres vs the winner); the other 12 country clubs (folders unknown).
- Report: research/staging/sa_tracking_report.md. Next decision for Damo: whether to load passing races into the master database
  (as a versioned release with the Qld shape plus a state column) and add SA to the weekly job.
