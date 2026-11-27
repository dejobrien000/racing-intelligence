#!/usr/bin/env bash
# QUEENSLAND COMMON NATIONAL FRAMEWORK SHADOWS (NOT LIVE; Batch 17 B2, approved by Damo 27 Nov 2026: "Approve building Configuration 2 ...
# Configuration 4 ... Score both beside current Queensland production."). The national engine's structure with Queensland's own
# coefficients, scored on the same Racing Queensland morning fields (restated in the national format by ops/qld_common_adapter.py):
#   config 2: common framework on the national Engine v2.3 rating  -> prospective/shadow/qld_common/
#   config 4: common framework on the update-rule candidate rating -> prospective/shadow/qld_common_update/
# Runs after the update-rule shadow (it shares that shadow's rating frame). Never the dashboard, the ranking or the settlement. A failure
# is a warning, never a failed run. Usage (from research/): ops/run_qld_common_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; BD=prospective/shadow/qld_common/bundles
[ -f ops/engine_c2_enabled ] && [ -f national_runs_c2.parquet ] && [ -f engine/frames/national_c2.parquet ] || { echo "Qld common shadow: needs Engine v2.3 history and frames"; exit 0; }
QB=$(python3 ops/qld_common_adapter.py "$D" "$BD" 2>/tmp/qcf_adapt.txt) || { echo "WARNING Qld common shadow: adapter failed (production unaffected): $(tail -1 /tmp/qcf_adapt.txt)"; exit 0; }
[ -f "$QB" ] || { echo "Qld common shadow: no Queensland meetings"; exit 0; }
for spec in "2 benchmarks/engine_qld_common_candidate engine/frames/national_c2.parquet prospective/shadow/qld_common" \
            "4 benchmarks/engine_qld_common_update_candidate engine/frames/national_update_rule.parquet prospective/shadow/qld_common_update"; do
  set -- $spec; C=$1; CD=$2; FR=$3; R=$4; N="Qld common shadow config $C"
  [ -f $CD/engine_v2.json ] && [ -f $CD/engine_v2_2.json ] && [ -f $CD/candidates_national_common.json ] || { echo "$N: no candidate files"; continue; }
  [ -f $FR ] || { echo "$N: rating frame $FR missing (the update-rule shadow builds it)"; continue; }
  if [ $C = 4 ]; then HOOKS="RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_X=1.3"; LBL="Qld common framework + update rule (not live)"; else HOOKS=""; LBL="Qld common framework (not live)"; fi
  mkdir -p $R
  env ENGINE_C2=1 WCREDIT=0.25 $HOOKS ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR ENGINE_CAND_LABEL="$LBL" METRO_FROM_TIER=1 SHADOW_LABEL="shadow candidate: $LBL" \
    PRED_ROOT=$R python3 prerace/score_national_prerace.py "$QB" ../history/history.duckdb "$D" > /tmp/qcf_v1_$C.txt 2>&1 \
    || { echo "WARNING $N v1 failed (production unaffected): $(tail -1 /tmp/qcf_v1_$C.txt)"; continue; }
  ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');S=S[(S.date.astype(str)=='$D')&S.snapshot_key.str.startswith('qcf')];print(','.join(sorted(set(S.track))))")
  [ -n "$ONLY" ] || { echo "$N: no meetings"; continue; }
  env ENGINE_C2=1 WCREDIT=0.25 $HOOKS ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR ENGINE_CAND_LABEL="$LBL" METRO_FROM_TIER=1 SHADOW_LABEL="shadow candidate: $LBL" \
    PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$BD python3 engine/score_v2.py "$D" > /tmp/qcf_v2_$C.txt 2>&1 \
    && echo "$N scored (not live): $(grep -c '^written' /tmp/qcf_v2_$C.txt) meetings" \
    || echo "WARNING $N v2 failed (production unaffected): $(tail -1 /tmp/qcf_v2_$C.txt)"
done
exit 0
