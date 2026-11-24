#!/usr/bin/env bash
# Daily 7:30am run, computing part (after the TAB racecards for TODAY and YESTERDAY have been saved by the run).
# Usage (from research/): ops/run_daily.sh <today YYYYMMDD> <today raw> [<yesterday YYYYMMDD> <yesterday results raw>]
set -uo pipefail
D=$1; RAW=$2; Y=${3:-}; YRAW=${4:-}; DATE="${D:0:4}-${D:4:2}-${D:6:2}"; export PYTHONPATH=.
log() { echo "[$(date -u +%H:%M:%SZ)] $*"; }
OUT=$(python3 ops/daily_build.py "$D" "$RAW") || { log "FAILED daily_build"; exit 2; }; echo "$OUT"
STAMP=$(echo "$OUT" | sed -n 's/^stamp //p'); RETR="${STAMP:0:4}-${STAMP:4:2}-${STAMP:6:2}T${STAMP:9:2}:${STAMP:11:2}:${STAMP:13:2}Z"
NAT=$(cat collect/national/$D/nat_venues.txt)
python3 collect/national/build_snapshot.py "$D" "$RETR" "$NAT" || log "WARNING build_snapshot failed (fields-only meetings may be missing)"
RQB=collect/national/$D/bundles/rqpre_${D}_snap${STAMP}.jsonl.gz
[ -f "$RQB" ] && { python3 prerace/score_prerace.py "$RQB" ../history/history.duckdb > /tmp/score_qld.txt 2>&1 && log "Queensland scored" || log "FAILED Queensland scoring: $(tail -1 /tmp/score_qld.txt)"; }
NB=$(ls collect/national/$D/bundles/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
[ -n "$NAT" ] && [ -n "$NB" ] && { python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/score_nat.txt 2>&1 && log "national meetings scored" || log "FAILED national scoring: $(tail -1 /tmp/score_nat.txt)"; }
SNAPDIR=collect/national/$D/bundles python3 engine/score_v2.py "$D" > /tmp/score_v2.txt 2>&1 && log "Engine v2 scored" || log "FAILED Engine v2: $(tail -1 /tmp/score_v2.txt)"
python3 engine/daily_ranking_v2.py "$D" > /tmp/rank.txt 2>&1 || log "WARNING ranking: $(tail -1 /tmp/rank.txt)"
python3 engine/export_ui.py "$D" > /tmp/export.txt 2>&1 || { log "FAILED export: $(tail -3 /tmp/export.txt)"; exit 3; }
python3 collect/tab_prices.py "$D" "tab_${STAMP}" > /tmp/prices.txt 2>&1 && log "open prices matched: $(head -1 /tmp/prices.txt)" || log "WARNING prices: $(tail -1 /tmp/prices.txt)"
python3 engine/export_ui.py "$D" > /tmp/export.txt 2>&1; sed -n 1p /tmp/export.txt
if [ -n "$Y" ] && [ -f "$YRAW" ] && [ -f "ui/data/racing_${Y:0:4}-${Y:4:2}-${Y:6:2}.json" ]; then python3 ops/settle_yesterday.py "$Y" "$YRAW" "$D" && log "yesterday settled"; fi
python3 ui/build_standalone.py "$DATE" >/dev/null && log "done"
