# Victorian TripleS: reconciliation before the 30 Nov integration (Batch 16 A5, 27 Nov 2026)

Method: history/load_vic_tracking.py run on a throwaway copy of the master database (master-2026-11-23-sa-wa-tas-qld-satrk),
exactly as the weekly update's step 4 will run it. Nothing was written to the live database. Originals stay on branch
raw-vic-triples (817 files, every sha256 verified at staging).

| Stage | Races | Runner rows | Notes |
|---|---|---|---|
| Original files acquired | 817 | | 97 meetings, 1 Jul - 25 Nov 2026, 13 track configurations |
| Parsed | 817 | 10,831 | two layouts (724 three-field, 93 five-field headers); 0 checksum mismatches |
| Complete tracked runs (all sections timed) | | 8,234 | measured sections 61,153 |
| Kept with a reason (not measurements) | | 2,597 | 2,129 scratched (all times zero, not in the official field); 440 all-zero in 1-25 Nov races (not yet checkable: scratched or untracked); 13 all-zero in races outside our lists; 12 ran without tracking (in the official field, all zero); 3 partial (tracking stops part-way) |
| Matched to our historical result lists (Betfair-sourced, to 31 Oct) | 666 of 671 | 6,777 of 6,827 tracked | 5 races not in those lists (Ballarat synthetic 6 Aug R4-R7, Pakenham synthetic 2 Oct R2); they do match Breednet results |
| Not checkable against those lists (1-25 Nov) | 146 | | checked internally only |
| Course configuration from the matching Breednet meeting (same horses, same date) | 809 | 8,155 complete runs, every one with its Breednet finishing position | turf/synthetic and course variants kept apart (e.g. Sandown Hillside vs Lakeside, Caulfield vs Caulfield Heath, Ballarat vs Ballarat Synthetic) |
| Course from the file's meeting label only ('label only') | 8 | 79 complete runs, no Breednet finish yet | all eight are Geelong 25 Nov R1-R8: the master database's Breednet Victorian results end 22 Nov, so no Breednet meeting exists yet. Geelong has one configuration, so the label is not ambiguous, but the races stay marked 'label only' |
| Duplicates | 0 | 0 starters, 0 sections | |
| Package-flagged files | 4 | | "timing check incomplete or mismatched; original retained" (kept, flagged) |
| Fastest complete run = official winner | 665 of 666 | | one exception (Mr Natural, 0.01 s tracked gap); 3 dead heats |

The eight-race difference (817 loaded vs 809 course-matched) is entirely Geelong 25 Nov. Monday's weekly update collects
Breednet results before the foundation steps run, so those eight should match on Monday. If they do not, they stay 'label
only' and keep no Breednet finishing position; nothing is attached to a guessed course configuration or horse.

Not in these files and left NULL (never estimated): ground covered, top speed, stride frequency and length, distance from the
rail. Measured: section times, speed at each mark. Derived (labelled): cumulative time, section average speed, position by
cumulative time, finish time.
