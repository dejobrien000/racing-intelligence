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
