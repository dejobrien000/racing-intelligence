#!/usr/bin/env bash
# Safe continuation of the daily computing part (Batch 26, 28 Nov 2026) - use ONLY when ops/run_daily.sh stopped AFTER scoring
# (its log shows "Engine v2 scored") but before "done". It never scores anything: it runs, in order and exactly as written in
# run_daily.sh, the steps that follow scoring (ranking only if missing, export, OPEN prices, export, settle yesterday, evaluation
# ledger, tipping report, engine performance, standalone build).
# Guards (any failure -> exit without doing anything):
#   - today's forecasts must already be stored (Queensland and/or national pre-race store for today, and Engine v2 runner files)
#   - at most one dashboard ranking file for today (never makes a second one: forecasts are immutable once stored)
# Usage (from research/): ops/resume_daily.sh <today YYYYMMDD> <today raw> [<yesterday YYYYMMDD> <yesterday results raw>]
# DRYRUN=1 prints the checks and the steps it would run, and runs nothing.
set -uo pipefail
D=$1; RAW=$2; Y=${3:-}; YRAW=${4:-}; DATE="${D:0:4}-${D:4:2}-${D:6:2}"; export PYTHONPATH=.
log() { echo "[$(date -u +%H:%M:%SZ)] $*"; }
STAMP=$(basename "$RAW" | sed -n 's/^tab_\([0-9TZ]*\)\.raw\.txt$/\1/p')
[ -n "$STAMP" ] || { log "STOP: cannot read the snapshot stamp from $RAW"; exit 2; }
NPRE=$(ls -d prospective/prerace/$D/*/ 2>/dev/null | wc -l)
NV2=$(ls prospective/prerace/$D/*/v2_pred_*_runners.csv 2>/dev/null | wc -l)
NRANK=$(ls prospective/daily/$D/ranking_v2_*_races.csv 2>/dev/null | wc -l)
log "checks: pre-race venues stored $NPRE | Engine v2 runner files $NV2 | dashboard ranking files $NRANK | snapshot $STAMP"
[ "$NPRE" -gt 0 ] && [ "$NV2" -gt 0 ] || { log "STOP: today's forecasts are not stored - this is not a post-scoring stop; rerun ops/run_daily.sh instead"; exit 2; }
[ "$NRANK" -le 1 ] || { log "STOP: more than one ranking file for today - investigate, do not continue"; exit 2; }
run() { if [ "${DRYRUN:-0}" = "1" ]; then echo "  would run: $*"; else "$@"; fi; }
if [ "$NRANK" -eq 0 ]; then run sh -c "python3 engine/daily_ranking_v2.py $D > /tmp/rank.txt 2>&1" || log "WARNING ranking: $(tail -1 /tmp/rank.txt)"
else log "ranking already stored: not rebuilt"; fi
run sh -c "python3 engine/export_ui.py $D > /tmp/export.txt 2>&1" || { log "FAILED export: $(tail -3 /tmp/export.txt)"; exit 3; }
run sh -c "python3 collect/tab_prices.py $D tab_${STAMP} > /tmp/prices.txt 2>&1" && log "open prices matched: $(head -1 /tmp/prices.txt 2>/dev/null)" || log "WARNING prices: $(tail -1 /tmp/prices.txt)"
run sh -c "python3 engine/export_ui.py $D > /tmp/export.txt 2>&1"; [ "${DRYRUN:-0}" = "1" ] || sed -n 1p /tmp/export.txt
if [ -n "$Y" ] && [ -f "$YRAW" ] && [ -f "ui/data/racing_${Y:0:4}-${Y:4:2}-${Y:6:2}.json" ]; then run python3 ops/settle_yesterday.py "$Y" "$YRAW" "$D" && log "yesterday settled"
  run sh -c "python3 ops/evaluate_prospective.py $Y > /tmp/eval.txt 2>&1" && log "evaluation ledger: $(tail -1 /tmp/eval.txt 2>/dev/null)" || log "WARNING evaluation ledger (observational only): $(tail -1 /tmp/eval.txt)"
  run sh -c "python3 ops/tipping_report.py $Y > /tmp/tip.txt 2>&1" && log "$(tail -1 /tmp/tip.txt 2>/dev/null)" || log "WARNING tipping report (observational only): $(tail -1 /tmp/tip.txt)"; fi
run sh -c "python3 engine/engine_performance.py $D > /tmp/engperf.txt 2>&1" && log "$(tail -1 /tmp/engperf.txt 2>/dev/null)" || log "WARNING engine performance (display only): $(tail -1 /tmp/engperf.txt)"
run sh -c "python3 ui/build_standalone.py $DATE >/dev/null" && log "done (continued)"
