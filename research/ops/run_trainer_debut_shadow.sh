#!/usr/bin/env bash
# TRAINER DEBUT RECORD CANDIDATE SHADOW (NOT LIVE; Batch 19 A3, approved by Damo 27 Nov 2026: "Approve preparing the trainer debut record
# as a candidate input and frozen shadow."). Engine v2.3 + one third-layer term (tr_debut_g) for genuine debutants; all three layers from
# benchmarks/engine_trainer_debut_candidate/. Uses the PRODUCTION Engine v2.3 rating frame read-only: this script never builds a frame.
# Scored on the same morning snapshot after publishing; writes only to prospective/shadow/trainer_debut/ (own INDEX.csv). Never the
# dashboard, the ranking or the settlement. A failure is a warning, never a failed run. Usage (from research/): ops/run_trainer_debut_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; B=collect/national/$D/bundles
R=${TD_ROOT:-prospective/shadow/trainer_debut}; CD=benchmarks/engine_trainer_debut_candidate; FR=engine/frames/national_c2.parquet; N="trainer-debut shadow"
LBL="Trainer debut record (not live)"; SLBL="shadow candidate: Engine v2.3 + trainer debut record for genuine debutants, not live"
[ -f $CD/engine_v2.json ] && [ -f $CD/engine_v2_2.json ] && [ -f $CD/candidates_national_common.json ] || { echo "$N: no candidate files"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f $FR ] || { echo "$N: needs the Engine v2.3 switch and frame"; exit 0; }
NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1); [ -n "$NB" ] || { echo "$N: no national bundle"; exit 0; }
export ENGINE_C2=1 ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR ENGINE_CAND_LABEL="$LBL" SHADOW_LABEL="$SLBL"
mkdir -p $R
PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/td_v1.txt 2>&1 \
  || { echo "WARNING $N v1 failed (production unaffected): $(tail -1 /tmp/td_v1.txt)"; exit 0; }
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
[ -n "$ONLY" ] || { echo "$N: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/td_v2.txt 2>&1 \
  && echo "$N scored (not live): $(grep -c '^written' /tmp/td_v2.txt) meetings" \
  || echo "WARNING $N v2 failed (production unaffected): $(tail -1 /tmp/td_v2.txt)"
exit 0
