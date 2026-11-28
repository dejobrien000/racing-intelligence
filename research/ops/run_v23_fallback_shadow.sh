#!/usr/bin/env bash
# ENGINE v2.3 FALLBACK SHADOW (NOT LIVE; Batch 28 amendment, Damo 28 Nov 2026: "Retain Engine v2.3 as an independently scored comparison
# and immediate fallback"). Only while ops/engine_v25_enabled is on: scores Engine v2.3 exactly as production ran it until 28 Nov
# (benchmarks/engine_v2_3, frame engine/frames/national_c2.parquet) on the same morning snapshot, into prospective/shadow/v2_3_fallback/
# (own INDEX.csv). Never the dashboard, the ranking or the settlement; the evaluation ledger reads it as 'Engine v2.3 fallback (not live)'.
# A failure is a warning, never a failed run. Usage (from research/): ops/run_v23_fallback_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; R=prospective/shadow/v2_3_fallback; B=collect/national/$D/bundles; N="v2.3 fallback shadow"
[ -f ops/engine_v25_enabled ] || { echo "$N: Engine v2.5 not live (production is Engine v2.3); nothing to do"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f national_runs_c2.parquet ] && [ -f engine/frames/national_c2.parquet ] || { echo "$N: needs Engine v2.3 history and frame"; exit 0; }
NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1); [ -n "$NB" ] || { echo "$N: no national bundle"; exit 0; }
unset ENGINE_CAND_DIR ENGINE_CAND_FRAME ENGINE_CAND_LABEL RATING_CAP_L RATING_CAP_SCOPE RATING_GOOD_X RATING_GOOD_TAPER RATING_TAPER_NEFF RATING_REF ENGINE_V24
export ENGINE_C2=1 WCREDIT=0.25 SHADOW_LABEL="shadow: Engine v2.3 fallback (not live)"
mkdir -p $R
PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/v23f_v1.txt 2>&1 \
  || { echo "WARNING $N v1 failed (production unaffected): $(tail -1 /tmp/v23f_v1.txt)"; exit 0; }
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
[ -n "$ONLY" ] || { echo "$N: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/v23f_v2.txt 2>&1 \
  && echo "$N scored (not live): $(grep -c '^written' /tmp/v23f_v2.txt) meetings" \
  || echo "WARNING $N v2 failed (production unaffected): $(tail -1 /tmp/v23f_v2.txt)"
exit 0
