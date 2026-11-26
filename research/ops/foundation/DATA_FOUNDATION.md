# Data foundation: how the sources fit together (26 Nov 2026)

The field-by-field register is `field_register.csv` (50 fields). Collection processes are in `collection_processes.csv`.
Evidence for the TAB form numbers is `tab_form_overlap.csv`, made by `tab_form_overlap.py` from the 26 Nov form records.
Consolidation only: no new collectors were built for this stocktake.

## One national core, state layers beside it
- **National core (every state, Oct 2022 on): Breednet results.** This is the result of record for:
  - meeting, race, distance, class, going and race time;
  - finishing position, margin, weight carried, jockey and trainer;
  - age, sex and breeding.
  Fill rate is 99.5-100% in every state. The exception is race last 600m, at 58% (SA) to 99% (ACT).
- **Today's fields (every state, from 25 Nov 2026): TAB racecards at 7:30am.** These give runners, barriers, allocated weight and claim, riders, trainers, scratchings and the morning track condition.
- **TAB form records (every runner, daily, from 25 Nov 2026).** These give each runner's last 8-9 race starts and about 3 trials, plus its true career record.
- **State layers, kept alongside the core and never replacing it:**
  - **Qld:** RQ tracking, 1,263 meetings from Oct 2022. Used by the Qld rating.
  - **SA:** tracking, 233 meetings from Jan 2024. Research.
  - **Vic:** TripleS files, metro and major provincial, from 1 Jul 2026 (the accepted start). Staging.
  - **NSW:** Racing NSW form lines, a static snapshot from Jun 2018 to 16 Nov 2026. Research.
  - **Gear and stewards:** QRIC reports (Qld), SA gear and stewards documents, NSW stewards notifications. All staging.

## Precedence and matching rules (all sources)
1. **Same horse** = name with letters and digits only, plus the race date. The race number breaks ties for dual acceptors, and sire/dam where two horses share a name. There is no national horse id.
2. **Results:** Breednet is the record. Inside Queensland, RQ tracking is the record for tracked meetings. Breednet fills Queensland meetings that RQ doesn't track.
   - TAB nightly results settle the dashboard only.
   - TAB form copies of results are checks only. On 26 Nov they agreed with Breednet as follows:
     - finishes: 1,953 of 1,954;
     - margins within 0.1 length: 1,644 of 1,664;
     - distances: 1,954 of 1,954.
3. **Weight conventions differ, and are never mixed silently.**
   - Breednet gives carried weight. Checked: 4,937 of 4,940 NSW rides where allocated and carried differ.
   - RQ race fields and TAB racecards give allocated weight, with the claim separate.
   - The national rating uses carried weight (today's = TAB allocated minus claim).
   - Open item: the national history frame takes Queensland rows from RQ (allocated weight). The effect is small (apprentice rides only). It is flagged for the next release and not changed now.
4. **Missing is not zero.**
   - A missing barrier, comment, report or gear document is "unknown".
   - TAB form gives barrier 0 for every past start, so TAB form is never a barrier source.
5. **Timing.** Post-race material (stewards' reports, comments) is usable only for later races.
   - Pre-race documents count from their own published time:
     - SA gear documents: "Date Printed";
     - NSW notices: last-edited time.
6. **Market information** (TAB prices, SP, Betfair prices) is kept out of every model input. Prices live only in `prices/`.
7. **Duplicate representations are not separate sources.**
   - The `x_*` tables are the raw parse of the same RQ files as `race`, `starter` and `sectional`.
   - The `bf` and `bf_runner` tables (Betfair) are for validation only.

## What TAB daily form enrichment adds
26 Nov fields had 2,025 race starts across every state: Vic 557, WA 738, NSW 355, Qld 289, others 86.

| Field | TAB form | Held elsewhere | What it means |
|---|---|---|---|
| Position in running | 1,976 / 2,025 (97.6%) | 256 (NSW 800/400m, Qld tracking) | The only running-position source for Vic, WA and Tas (Vic: 557/557 from TAB, 11 held elsewhere). |
| Stewards' comment | 766 (38%) | Qld/SA reports (staging) | The only per-horse stewards remarks for Vic, NSW, WA, Tas. Retrospective. |
| Starts we don't hold | 71 (Yarra Glen, Yea picnics, NZ, older) | none | Fills history gaps. A venue-code map is needed before use. |
| True career record | every runner | our own counts | Separates first starters (20) from lightly raced (52) and part-held histories (66, 2 of them lightly raced). |
| Blinkers today | every runner (on/off) | SA gear documents (SA) | Gear flag nationally. On/off only. |
| Finish, margin, distance, class, going, time, rider | duplicates | Breednet | Checks only (agreement above). |
| Barrier at past starts | not given (always 0) | Qld, SA, NSW (static) | Not a source. |

TAB form is a rolling window (the last 8-9 starts of today's runners). Because it is taken every day, running positions and comments build up for every active horse in every state from 25 Nov 2026. Horses that have stopped racing are never back-filled.

## Collection processes register
See `collection_processes.csv`.

**Established external process (26 Nov 2026).** ChatGPT and Damo run a weekly, manually started Work session that collects Victorian TripleS sectional CSVs from Racing.com. Accepted start: 1 July 2026. No effort goes into earlier coverage for now.
- The output is a ZIP of original files.
- Claude checks it with `history/stage_vic_triples.py` and stages it under `research/staging/vic_triples`.
- The first ZIP (817 races, 1 Jul - 25 Nov 2026, 13 track configurations) is validated:
  - runners: 6,777 / 6,777 matched;
  - saddlecloths: all agree;
  - fastest = official winner in 663 of 666 races.
- It is awaiting the integration decision.
- Proposed home: `vic_race`, `vic_starter` and `vic_sectional`, the same shape as the SA tracking tables, loaded at the weekly update once approved.

## Genuine remaining gaps (after reconciling every source above)
1. **Past barriers for Vic, WA and Tas before 25 Nov 2026** (also NSW after 16 Nov, SA before 2024).
   - No existing source: Breednet doesn't publish barriers and TAB form gives none.
   - Forward is covered by the daily TAB racecards once they are loaded into the database.
   - Barriers are not used by the national rating today (Queensland only).
2. **Per-runner sectionals:**
   - NSW, WA, Tas and country Victoria: none.
   - Vic metro and provincial: from 1 Jul 2026 only (accepted).
3. **Pre-race gear changes:** Vic, Qld, WA and Tas have none beyond TAB's blinkers on/off. Held only for SA (full gear) and NSW (late changes).
4. **Full stewards' reports:** Vic, NSW (report index blocked by robots rules), WA and Tas. TAB per-horse comments cover part of this.
5. **Running positions before 25 Nov 2026 for Vic, WA and Tas.** Filled only for horses still racing, through TAB form.

## Consolidation steps (no new collectors)
1. **Load the daily TAB racecards and results into the master database at the weekly update** (two staging tables). Barriers, claims, scratchings and nightly results from 25 Nov are then kept with the history.
2. **Build a TAB venue-code table** from the daily TAB files. This lets TAB form's 4-letter venue codes and new starts be placed.
3. **Add a weekly reconciliation check:** TAB nightly results vs Breednet (winners, finishes, scratchings). This takes over Betfair's checking role. No Betfair collection is needed.
4. **Integrate the Vic TripleS files** as `vic_*` tables (decision pending).
5. **Remove the racing.com tables** (`rc_*`, `vic_speed_*`) at the next weekly update. They are superseded.
6. **Weight-convention note (Qld rows in the national frame)** goes to the next engine release. It does not change production now.
7. **Paused:** WA and Tas gear and stewards source searches, and earlier Victorian history.
