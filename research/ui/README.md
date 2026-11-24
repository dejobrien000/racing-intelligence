# Racing Intelligence dashboard

The interface and the prediction engine are separate. The engine writes one JSON file per race day in a fixed contract;
the interface only reads that contract. Engine v3 or later just has to fill the same fields.

## Files
- `index.html`: the whole interface (HTML, CSS and JS in one file). It reads the data in one of two ways:
  1. data embedded in its `<script id="ri-data">` tag (the self-contained copy), or
  2. `data/index.json` and the day file it names, fetched from beside the page (the published artifact, or any static web server).
- `data/index.json`: the list of race days available.
- `data/racing_YYYY-MM-DD.json`: one race day (contract `racing-intelligence.daily` v1.0).
- `dist/racing_intelligence_YYYY-MM-DD.html`: the self-contained copy. It opens by double-click, with no server or internet needed (fonts fall back to system fonts offline).

## Daily refresh
Run these from `research/`:

1. `PYTHONPATH=. python3 engine/export_ui.py YYYYMMDD`. This reads the latest write-once v2 and v1 prediction files and their snapshots.
2. `python3 ui/build_standalone.py YYYY-MM-DD`.
3. Republish the day file to the artifact: publish_files, patch mode, with `data/racing_YYYY-MM-DD.json` and `data/index.json`.

## Contract essentials (v1.0)

**Day level**
- `date`, `exported_utc`, `snapshot_note`
- `engine`: `operational`, `released_utc`, `scale`, `calibration`

**Meetings:** `meetings[]` has:
- `conditions`
- `snapshots[]`: each with `label`, `kind`, `fields_captured_utc`, `v1_scored_utc` and `v2_scored_utc`
- `races[]`

**Races:** `races[]` has:
- `no`, `name`, `class`, `distance_m`, `time`, `tz`, `field`
- `label`: Strong selection / Leading contender / No clear selection / Insufficient evidence
- `runners[]`
- `not_scored[]`

**Runners:** `runners[]` has:
- `rating`: final race rating, kg-equivalent and race-relative
- `chance` (model %) and `cal`, `cal_lo`, `cal_hi` (calibrated win %, with its 80% band)
- `groups[]`: contribution families in kg-equivalent. They add up to `rating`.
- `terms[]`: v2 terms
- `ability`, `records`, `people`, `evidence`, `v1`, `class`

**Other day-level blocks**
- `leaderboard[]`: qualified runners ordered by calibrated win chance
- `validation`: the historical backtest
- `results`: `status` is waiting until the evaluation exists
- `operations`

## Rules
- The dashboard never re-predicts. The export may recompute v2 term detail from the same inputs, but it must equal the saved v2 score, or it stops.
- No local paths, keys or personal data go into the contract. Only public racing data (horses, jockeys, trainers) and file fingerprints do.
- No market prices.
