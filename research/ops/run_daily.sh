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
# Engine v2.3 (candidate C2: history weight credit 0.25 kg per kg, 0.170 s per length; NSW/VIC/ACT/SA/WA/TAS only; Qld untouched).
# OFF unless ops/engine_c2_enabled exists (a release decision by Damo). Builds its frames beside production (~3 min); if anything fails
# the run falls back to Engine v2.2 for that day and says so.
if [ -f ops/engine_c2_enabled ]; then
  export ENGINE_C2=1
  if [ ! -f engine/frames/national_c2.parquet ] || [ ! -f national_runs_c2.parquet ] || [ national_runs_c2.parquet -ot ../history/history.duckdb ]; then   # rebuilt whenever the master database is newer
    NS=$(python3 -c "import json;print(','.join(json.load(open('ops/db_config.json'))['national_states']))")
    QB=$(python3 -c "import json;print('1' if json.load(open('ops/db_config.json')).get('qld_breednet_in_national_rating') else '0')")
    ( export NAT_STATES=$NS NAT_QLD_BN=$QB WCREDIT=0.25 SPL_FIXED=0.170
      NAT_RUNS_ONLY=1 NAT_RUNS_OUT=national_runs_c2.parquet python3 national.py ../history/history.duckdb > /tmp/c2_nat.txt 2>&1 \
      && LAB_IN=national_runs_c2.parquet LAB_OUT=engine/frames/national_c2.parquet python3 engine/lab.py > /tmp/c2_lab.txt 2>&1 ) \
      && log "Engine v2.3 frames built" || { log "WARNING Engine v2.3 frames failed: national meetings scored with Engine v2.2 today"; export ENGINE_C2=0 ENGINE_FALLBACK="Engine v2.3 rating frames failed to build; national meetings scored with Engine v2.2"; rm -f engine/frames/national_c2.parquet national_runs_c2.parquet; }
  fi
fi
# Engine v2.5 (national consolidated rating; approved by Damo 28 Nov 2026 2:38pm, Batch 28 amendment, from the 29 Nov run): NSW/VIC/ACT/SA/
# WA/TAS only, Queensland untouched. OFF unless ops/engine_v25_enabled exists and Engine v2.3 history is on. benchmarks/engine_v2_5 holds
# byte-identical copies of the frozen consolidated candidate's files; same code, rating settings and frame as the consolidated shadow.
# Rebuilds its experience file and rating frame when the v2.3 history is newer (~4 min). Any failure -> Engine v2.3 for the day, logged.
# Rollback: delete ops/engine_v25_enabled (Engine v2.3 is also scored every morning as the fallback shadow).
if [ -f ops/engine_v25_enabled ] && [ "${ENGINE_C2:-0}" = 1 ] && [ -f benchmarks/engine_v2_5/engine_v2.json ]; then
  V25ENV="WCREDIT=0.25 RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_X=1 RATING_GOOD_TAPER=0.8,6 RATING_TAPER_NEFF=engine/frames/experience_at_run.parquet RATING_REF=precision"
  FR25=engine/frames/national_consolidated.parquet; OK25=1
  if [ ! -f $FR25 ] || [ $FR25 -ot national_runs_c2.parquet ] || [ ! -f engine/frames/experience_at_run.parquet ]; then
    ( export $V25ENV
      EXP_INFO_JSON=/tmp/exp_info_v25.json python3 batch23/b23_experience_file.py engine/frames/national_c2.parquet engine/frames/experience_at_run.parquet > /tmp/v25_exp.txt 2>&1 \
      && LAB_IN=national_runs_c2.parquet LAB_OUT=$FR25 python3 engine/lab.py > /tmp/v25_lab.txt 2>&1 ) && log "Engine v2.5 experience file and rating frame rebuilt" || OK25=0
  fi
  if [ $OK25 = 1 ]; then export $V25ENV ENGINE_CAND_DIR=benchmarks/engine_v2_5 ENGINE_CAND_FRAME=$FR25 ENGINE_CAND_LABEL="Engine v2.5"; log "Engine v2.5 switch ON (national)"
  else log "WARNING Engine v2.5 frames failed: national meetings scored with Engine v2.3 today"; export ENGINE_FALLBACK="Engine v2.5 rating frames failed to build; national meetings scored with Engine v2.3"; fi
fi
# Engine v2.1.3 (Queensland candidate: v2.1.1 + Age & sex family; benchmarks/engine_v2_1_3). OFF unless ops/engine_qld213_enabled exists
# (a release decision by Damo). No frames to build: same v3 history frame as v2.1.1. NSW/VIC/ACT/SA/WA/TAS untouched by this switch.
if [ -f ops/engine_qld213_enabled ] && [ -f benchmarks/engine_v2_1_3/manifest.json ]; then export ENGINE_QLD213=1; log "Queensland: Engine v2.1.3 switch ON"; fi
NB=$(ls collect/national/$D/bundles/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
[ -n "$NAT" ] && [ -n "$NB" ] && { python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/score_nat.txt 2>&1 && log "national meetings scored" || log "FAILED national scoring: $(tail -1 /tmp/score_nat.txt)"; }
# Engine v2.1: Queensland history frame on the v3 rating (built once from the restored master database, ~5 min)
[ -f engine/frames/national_v3.parquet ] || PYTHONPATH=. python3 engine/build_frame_v3.py
SNAPDIR=collect/national/$D/bundles python3 engine/score_v2.py "$D" > /tmp/score_v2.txt 2>&1 && log "Engine v2 scored" || log "FAILED Engine v2: $(tail -1 /tmp/score_v2.txt)"
python3 engine/daily_ranking_v2.py "$D" > /tmp/rank.txt 2>&1 || log "WARNING ranking: $(tail -1 /tmp/rank.txt)"
python3 engine/export_ui.py "$D" > /tmp/export.txt 2>&1 || { log "FAILED export: $(tail -3 /tmp/export.txt)"; exit 3; }
python3 collect/tab_prices.py "$D" "tab_${STAMP}" > /tmp/prices.txt 2>&1 && log "open prices matched: $(head -1 /tmp/prices.txt)" || log "WARNING prices: $(tail -1 /tmp/prices.txt)"
python3 engine/export_ui.py "$D" > /tmp/export.txt 2>&1; sed -n 1p /tmp/export.txt
if [ -n "$Y" ] && [ -f "$YRAW" ] && [ -f "ui/data/racing_${Y:0:4}-${Y:4:2}-${Y:6:2}.json" ]; then python3 ops/settle_yesterday.py "$Y" "$YRAW" "$D" && log "yesterday settled"
  python3 ops/evaluate_prospective.py "$Y" > /tmp/eval.txt 2>&1 && log "evaluation ledger: $(tail -1 /tmp/eval.txt)" || log "WARNING evaluation ledger (observational only): $(tail -1 /tmp/eval.txt)"
  python3 ops/tipping_report.py "$Y" > /tmp/tip.txt 2>&1 && log "$(tail -1 /tmp/tip.txt)" || log "WARNING tipping report (observational only): $(tail -1 /tmp/tip.txt)"; fi
# Engine Performance tab: refresh after the evaluation ledger so it includes yesterday (display only; never fails the run; 27 Nov 2026)
python3 engine/engine_performance.py "$D" > /tmp/engperf.txt 2>&1 && log "$(tail -1 /tmp/engperf.txt)" || log "WARNING engine performance (display only): $(tail -1 /tmp/engperf.txt)"
python3 ui/build_standalone.py "$DATE" >/dev/null && log "done"
