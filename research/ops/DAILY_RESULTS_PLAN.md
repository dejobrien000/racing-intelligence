# Daily rating freshness - staged incremental results (Batch 27 design; NOT in use; no daily history process before it passes)

Why: ratings use history to the last weekly master (28 Nov: cutoff 23 Nov; 2 of 1,270 runners had run since, 73 backing up within 7 days).
TAB settlement is not enough: it lacks complete margins and every runner's result.

Source: the same Breednet results pages the weekly master already uses (collect/weekly/breednet.py, all states, re-fetch window of
10+ days so corrections are picked up). No new site, no paid source. Same access rules (stop on CAPTCHA; never circumvent).

## Stages (each writes new files; the authoritative history.duckdb is only ever changed by the weekly master step)
1. Collect yesterday +/- 2 days into breednet/daily/<date>.jsonl.gz (staging only).
2. Validate each race - all must pass or the race is held back (never a partial race in opposition-based ratings):
   complete field (starters = TAB final field minus scratchings); every finisher has a position; margins present for all but the
   winner and monotone with position; dead heats share a position and margin 0; non-finishers (fell, lost rider, DNF) flagged, never
   given a margin; race time present and within 15% of the venue-distance par; horse identity resolves through the identity list
   (unresolved names -> race held back); no duplicate race key; no race already in the master.
3. Build a staged history version (history_staged_<date>.duckdb = master + validated races) and a staged rating frame with a version
   fingerprint (master hash + staged race list). Production keeps reading the master.
4. Reconcile every Monday: the weekly master must reproduce every staged race exactly (positions, margins, times, identity); any
   difference is logged and the staged race is replaced by the master's.

## Test before any use (from Monday 30 Nov)
Run stages 1-3 for 24-29 Nov, then compare with Monday's master: race-level agreement (fields, positions, margins, times, identity)
and rating agreement (staged frame vs master-built frame, max difference per horse). Pass = 100% of validated races identical and
rating differences only from races the master corrected. Only then propose to Damo: score each morning from the staged frame, with
the master still the authority. Not before; Monday is not a reason to start it.
