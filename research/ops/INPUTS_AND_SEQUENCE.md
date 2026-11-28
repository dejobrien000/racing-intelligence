# Daily inputs: collection sequence and what each engine needs (Batch 27, 28 Nov 2026)

Essential = changes a forecast if missing. Supplementary = never needed before scoring. Missing information is never "scratched" and a
horse with no runs held is never called a debutant unless TAB's own record (held before scoring) shows 0 career starts.

## Sequence (DAILY_RUN step in brackets)
1. Core fields [1-2]: calendar, racecards - runners, barriers, weights and claims, jockeys, trainers, distance, class, track condition,
   TAB status. Essential.
2. Essential identity and scoring inputs [3b, straight after 2]: TAB form record (age, sex, career starts) for every runner production
   would otherwise serve without age or sex - no runs held, or held runs whose latest row has no age - in race-start order, rated
   states only, until 8:05am. Identity = name key against the held history (identity list corrections from Monday 30 Nov).
3. Scratchings and eligibility [2, 4]: TAB status at capture; national emergencies rule (gain a start only when the card shows it).
4. Production assessment [4]: Qld Engine v2.1.3, national Engine v2.3, export, publish. Runs in the background with an allowance of
   6 min + 10 s per race; ops/resume_daily.sh continues safely after "Engine v2 scored".
5. Independent research assessment [5a/5c]: the ten frozen shadows. Never block or alter step 4.
6. Supplementary enrichment [5b, 5d, 5e]: all other TAB form records (stewards, gear, past starts), rail ingest from the optional task,
   preflight, freshness and the essential-input record (ops/essential_inputs.py -> prospective/prerace/<D>/essential_inputs.csv).

## What each engine reads on the day (beyond the held history)
| Engine | Today's essential inputs | From history | Fallback when missing |
|---|---|---|---|
| National Engine v2.3 (six states) | distance, venue, going, class/benchmark, weight carried (claim deducted once), jockey, trainer, age and sex if no history age | opposition-aware rating, time figures, recent form, spacing, course/going/distance records, jockey/trainer records, career shape | missing-form and missing-figure indicators; age/sex missing indicators (never guessed); population average for the horse's experience |
| Qld Engine v2.1.3 | as above + barrier, field size | Qld v3 rating, RQ tracking (closing sectionals, race shape, settling), barrier x style, records, jockey/trainer, age and sex | Qld missing-style/missing-sectional indicators; "Queensland form inputs missing" label for horses held only outside Qld tracking |
| Shadows (frozen) | same as their base engine; v2.4 adds handicap class x weight; consolidated adds the experience file; trainer/sire debut add trainer/sire records | as their base | as their base |

Supplementary only (never awaited before scoring): stewards comments, gear, TAB past starts, pedigree (production does not read it),
rail and track information (collected, never served).
