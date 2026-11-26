# Gear changes, stewards' reports and TAB form records: sources, access and status (started 26 Nov 2026)

Damo's brief (26 Nov 2026 1:28pm): collect gear changes (first time / removed / again / unchanged, all approved gear, not just
blinkers), pre-race notifications and retrospective stewards' comments from Oct 2022 where permitted, forward collection first;
keep originals, source references, identifiers, publication and collection times; keep pre-race and post-race information apart;
a missing report is never evidence that nothing happened; no new coefficients; staging only; production never blocked.

## Rules for every source
- Access: public pages only, honest User-Agent, robots.txt respected, paced, stop on CAPTCHA / refusals. No logins, no bypassing.
- Timing: every item carries `available_from`. A stewards' report is published AFTER the meeting, so everything in it (even an
  item about a pre-race event such as a late gear change or rider replacement) is post-race information for modelling.
  Pre-race inputs may only come from documents published before the race (gear-change lists, late gear notices with a time).
- Missing: no report / no gear list = 'unavailable', never 'none'. Confirmed absence only where a source says so explicitly.

## Status by state (26 Nov 2026)
| State | Gear changes (pre-race) | Stewards' reports (post-race) | Access status |
|---|---|---|---|
| QLD | Not in Racing Queensland's race-fields PDFs (checked rfd_IPSW_20260620). Official gear lists are on Racing Australia FreeFields (robots: Disallow for all agents) | QRIC report per meeting on racingqueensland.com.au: GENERAL (overweights, rider replacements, fines), per-race horse notes, summary (swabs, rider changes). Reports may be amended later | COLLECTING: workflow rqstewards (GitHub runner, Oct 2022 on, resumable; weekly re-read of 14 days for amendments) -> branch raw-rqstewards. robots.txt has no Disallow |
| NSW | Late gear changes: news posts on racingnsw.com.au. Full lists: Racing Australia FreeFields (robots Disallow) | Stewards' raceday rundown PDFs: www.racingnsw.com.au/wp-content/uploads/stewards_info/<DDMMYYYY><CODE>.pdf (200 from GitHub, www robots.txt 404 = no rules). The diary that lists them is on racing.racingnsw.com.au/FreeFields (robots: Disallow /) | BLOCKER for the index: cannot crawl the diary. PDFs themselves reachable; need the track-code list to build addresses (as for SA). WebFetch reads need Damo's approval (asked 26 Nov 2pm, unanswered) |
| VIC | Not found outside racing.com | Index is on dxp-static.racing.com (racing.com host) | BLOCKED for Claude's tools (racing.com refused). Route: Damo / his tripleSdata contact supplies files |
| SA | 'Gear Change Race Order' PDFs per meeting WITH 'Date Printed' timestamp (pre-race) on racingsa.com.au / countryracingsa.com.au /files/<id>_<name>.pdf: per horse e.g. 'Blinkers Off First Time', 'Tongue Tie On', 'Ear Muffs (Pre-Race Only) Again' | Stipendiary stewards' report PDFs, same /files/ host | BLOCKER: file ids are not predictable; the listing pages answer the GitHub runner with an empty 202 (bot protection) and WebFetch of countryracingsa.com.au needs approval |
| WA | Not yet found | RWWA stewards' report PDFs per meeting: static.p.racingwa.com.au/race-files/<meeting id>/0/steward/<name>.pdf | To investigate: meeting ids and robots |
| TAS | Not yet found (late gear changes appear in reports) | Tasracing Integrity Unit PDFs on tasracing.com.au/hubfs/... with dated names | To investigate: listing page and robots |
| ACT | (Canberra meetings run under Racing NSW) | as NSW | as NSW |

## TAB form records (DAILY_RUN step 5b) - what they hold
- Per runner today: age, sex, career starts/wins/places, runs since spell, days since last run, BLINKERS true/false (the only gear
  field TAB publishes), class level, sire, dam, trainer.
- Per past start (about 10 most recent plus trials and the last win): type (LastStarts / Trial / WinRun), date, venue, distance,
  class, finish, starters, margin, positions in running, track condition, time, rider, stewards' comment.
- BARRIER RECONCILIATION (Batch 11 said zero): TAB's `draw` is 0 or blank on every past start (26 Nov: 2,934 lines, none with a
  barrier). So TAB form records do NOT supply past-start barriers; the staging loader now stores them as NULL with a note. My
  25-26 Nov statement that they did was wrong. Past-start barriers come only from Racing Queensland starters and Racing NSW form lines.
- Measured on 26 Nov (ops/form_enrichment.py; outputs/form_enrichment_ledger.csv): 317/317 runners; 2,934 past starts = 2,025
  race starts + 909 trials; of the race starts 1,951 are races we hold that gain positions in running and/or a stewards' comment,
  62 are races we do not hold (older, interstate/overseas or missing meetings), 12 add nothing; 766 stewards' comments; 1,976
  races with positions in running; 107 runners in blinkers. Career: 20 first starters, 231 complete, 66 incomplete history
  (TAB shows more starts than we hold: 'incomplete history', never 'inexperienced').
- Fixes 26 Nov: name keys matched letters/digits only (our tables keep spaces); TAB start types (LastStarts/WinRun, not 'race');
  WinRun collapsed onto its LastStarts copy; parser combines several passes per day and never drops a malformed line.
- Collection cost: AI-step collection took ~97 minutes and ~600 tool calls for one day. No scripted alternative is available yet:
  TAB answers GitHub's servers with its website shell (24 and 26 Nov; also with Accept: application/json and for robots.txt),
  the workspace's network allowlist refuses api.beta.tab.com.au (CONNECT 403), and TAB publishes no developer API or terms for
  automated use that we have found. See OPERATING_MODEL.md 'Unattended runs'.
