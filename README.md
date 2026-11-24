# National data pilot: local DuckDB demo (rerun on exact files)

Small, reproducible proof of concept for the Racing Intelligence platform. Pilot Saturday: **3 Oct 2026** (Randwick, Flemington, Eagle Farm). No cloud services, no paid data, no market prices.

## What's here

| Path | What it is |
| --- | --- |
| `schema.sql` | Common national schema (venue, meeting, race, horse, horse_alias, starter, sectional, position_in_run, outcome_flag, source, retrieval, field_provenance, data_gap, integrity_check) |
| `load_pilot.py` | Loads the files into the schema and runs 127 join and integrity checks |
| `exact/manifest.psv` | One line per file: source URL, size and SHA-256 of the file as served, when it was taken, and the hash of what was kept |
| `exact/rq/20261003_Eagle_Farm_T.csv` | Racing Queensland sectional CSV, byte-identical to the server copy |
| `exact/rq/rq_xml_*.psv` | Extracts from RQ's per-meeting ZIP (10 race XML files): results, margins, times, ground covered, positions, stride |
| `exact/rq/rq_racefields_pdf.psv` | Barrier, weight, jockey and trainer read from RQ's Race Fields PDF |
| `exact/betfair/bf_20261003_*.psv` | The three meetings from Betfair's October 2026 file, price columns removed |
| `exact/rq/notes_from_pages.txt` | Short factual notes from RQ pages (stewards rating, race page values, form guide inspection, April run) |
| `raw_transcribed/`, `out_transcribed/` | The first run's transcriptions and outputs, kept only to show they were reproduced |
| `pilot.duckdb` | The built database |
| `out/*.csv` | Every table exported, including `integrity_check.csv` and `coverage_by_state.csv` |

## How to rerun

1. Install Python 3 and run `pip install duckdb`.
2. In this folder, run `python3 load_pilot.py`.
3. Open `out/integrity_check.csv` in Excel or Google Sheets.

The script first re-hashes every file in `exact/` and stops trusting anything that doesn't match (checks M1).

## How the files were taken

Each source file was fetched through the built-in browser on 23–24 Nov 2026 (Brisbane). The CSV was copied byte for byte; for ZIP, PDF and the large Betfair CSV the browser parsed the file and the extract was copied out. Every copy was hash-checked against the browser's own hash. Price, odds and volume columns were dropped before anything left the browser.

## Licensing — keep this folder private

- **RQ Race Fields PDF** (barrier, weight, jockey, trainer): the PDF's notice requires RQ's prior written permission. RQ gave Damo permission on 24 Nov 2026; a written confirmation has been requested. Raw files still aren't redistributed.
- **RQ sectional CSV / ZIP**: listed as open licence in RQ's catalogue; no notice in the files. Still to be confirmed by RQ.
- **Betfair**: published for download with a no-warranty disclaimer; no licence stated.
- **Form guide PDF**: inspected only, not stored.
- Nothing from racing.com, Racing Australia, Punter's Intel or commercial form sites is included.
