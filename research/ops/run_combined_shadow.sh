#!/usr/bin/env bash
# COMBINED NATIONAL CANDIDATE SHADOW (NOT LIVE; Batch 28 item 3 + amendment, Damo 28 Nov 2026: "build the combined national candidate ...
# start the shadow once dependencies are satisfied"). Engine v2.5 + distance-specific suitability replacing the distance record (layers 1-2)
# + handicap weight slope + trainer and sire debut records (third layer); all three layers from benchmarks/engine_combined_candidate/.
# Rating = Engine v2.5's (same settings). Uses the production consolidated frame read-only: this script never builds a frame.
# Scored on the same morning snapshot after publishing; writes only to prospective/shadow/combined_national/ (own INDEX.csv). Never the
# dashboard, the ranking or the settlement. A failure is a warning, never a failed run. Usage (from research/): ops/run_combined_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; B=collect/national/$D/bundles
R=${CMB_ROOT:-prospective/shadow/combined_national}; CD=benchmarks/engine_combined_candidate; FR=engine/frames/national_consolidated.parquet; N="combined national shadow"
LBL="Combined national candidate (not live)"; SLBL="shadow candidate: Engine v2.5 + distance suitability + handicap slope + trainer/sire debut, not live"
[ -f $CD/engine_v2.json ] && [ -f $CD/engine_v2_2.json ] && [ -f $CD/candidates_national_common.json ] || { echo "$N: no candidate files"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f $FR ] && [ -f engine/frames/experience_at_run.parquet ] || { echo "$N: needs the Engine v2.5 frame and experience file"; exit 0; }
NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1); [ -n "$NB" ] || { echo "$N: no national bundle"; exit 0; }
unset ENGINE_V24
export ENGINE_C2=1 WCREDIT=0.25 RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_X=1 RATING_GOOD_TAPER=0.8,6 RATING_TAPER_NEFF=engine/frames/experience_at_run.parquet RATING_REF=precision
export ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR ENGINE_CAND_LABEL="$LBL" SHADOW_LABEL="$SLBL"
mkdir -p $R
PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/cmb_v1.txt 2>&1 \
  || { echo "WARNING $N v1 failed (production unaffected): $(tail -1 /tmp/cmb_v1.txt)"; exit 0; }
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
[ -n "$ONLY" ] || { echo "$N: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/cmb_v2.txt 2>&1 \
  && echo "$N scored (not live): $(grep -c '^written' /tmp/cmb_v2.txt) meetings" \
  || echo "WARNING $N v2 failed (production unaffected): $(tail -1 /tmp/cmb_v2.txt)"
exit 0
