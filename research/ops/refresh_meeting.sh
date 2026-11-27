#!/usr/bin/env bash
# Race-morning refresh of ONE meeting from the cloud (no PC): apply published scratchings to the saved snapshot,
# then re-score v1 and Engine v2. All outputs are new write-once files. Usage (from research/):
#   ops/refresh_meeting.sh <qld|nat> <src bundle> <src key> <refresh.json> <Track>
set -euo pipefail
FAM=$1 SRC=$2 KEY=$3 REF=$4 TRACK=$5
# same engine as the morning run (release switches; v2.3 only if its ratings were built this morning)
if [ -f ops/engine_c2_enabled ] && [ -f engine/frames/national_c2.parquet ] && [ -f national_runs_c2.parquet ]; then export ENGINE_C2=1; else export ENGINE_C2=0; [ -f ops/engine_c2_enabled ] && export ENGINE_FALLBACK="Engine v2.3 rating frames missing at refresh; scored with Engine v2.2"; fi
if [ -f ops/engine_qld213_enabled ]; then export ENGINE_QLD213=1; else export ENGINE_QLD213=0; fi
OUT=$(python3 collect/rescratch.py "$SRC" "$KEY" "$REF")
echo "$OUT"
NB=$(echo "$OUT" | sed -n 1p); D=$(echo "$KEY" | cut -d: -f2)
if [ "$FAM" = qld ]; then PYTHONPATH=. python3 prerace/score_prerace.py "$NB" ../history/history.duckdb > /tmp/refresh_v1.txt 2>&1
else PYTHONPATH=. python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/refresh_v1.txt 2>&1; fi
tail -1 /tmp/refresh_v1.txt
SNAPDIR=$(dirname "$NB") ONLY_TRACKS="$TRACK" PYTHONPATH=. python3 engine/score_v2.py "$D" > /tmp/refresh_v2.txt 2>&1
tail -1 prospective/prerace/INDEX.csv | cut -d, -f3,5
