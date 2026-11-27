#!/usr/bin/env bash
# RATING UPDATE RULE CANDIDATE SHADOW (NOT LIVE; Batch 16 B9, approved by Damo 27 Nov 2026: "Approve building the new rating update
# mechanism as a shadow candidate."). Engine v2.3 rebuilt in full with the candidate rule: a defeat counts at most 12 lengths in the
# performance figure (the recorded margin is never changed) and a run better than expected moves the rating 1.3 times as far. All three
# layers are its own (benchmarks/engine_update_rule_candidate/). Scored on the same morning snapshot after publishing. Writes only to
# prospective/shadow/update_rule/ (own INDEX.csv). Never the dashboard, the ranking or the settlement. A failure is a warning, never a
# failed run. Usage (from research/): ops/run_update_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; R=${UR_ROOT:-prospective/shadow/update_rule}; B=collect/national/$D/bundles; CD=benchmarks/engine_update_rule_candidate
FR=engine/frames/national_update_rule.parquet
[ -f $CD/engine_v2.json ] && [ -f $CD/engine_v2_2.json ] && [ -f $CD/candidates_national_common.json ] || { echo "update-rule shadow: no candidate files"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f national_runs_c2.parquet ] || { echo "update-rule shadow: needs Engine v2.3 history (switch and national_runs_c2)"; exit 0; }
NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1); [ -n "$NB" ] || { echo "update-rule shadow: no national bundle"; exit 0; }
export ENGINE_C2=1 WCREDIT=0.25 RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_X=1.3 ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR \
       ENGINE_CAND_LABEL="Update-rule candidate (not live)" SHADOW_LABEL="shadow candidate: rating update rule (12 L cap, 1.3x good runs), not live"
# its own rating frame, rebuilt (about a minute) whenever the Engine v2.3 history file is newer; same code as production plus the rule
if [ ! -f $FR ] || [ $FR -ot national_runs_c2.parquet ]; then
  LAB_IN=national_runs_c2.parquet LAB_OUT=$FR python3 engine/lab.py > /tmp/ur_lab.txt 2>&1 \
    && echo "update-rule shadow: frame rebuilt" || { echo "WARNING update-rule shadow: frame failed (production unaffected): $(tail -1 /tmp/ur_lab.txt)"; rm -f $FR; exit 0; }
fi
mkdir -p $R
PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/ur_v1.txt 2>&1 \
  || { echo "WARNING update-rule shadow v1 failed (production unaffected): $(tail -1 /tmp/ur_v1.txt)"; exit 0; }
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
[ -n "$ONLY" ] || { echo "update-rule shadow: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/ur_v2.txt 2>&1 \
  && echo "update-rule shadow scored (not live): $(grep -c '^written' /tmp/ur_v2.txt) meetings" \
  || echo "WARNING update-rule shadow v2 failed (production unaffected): $(tail -1 /tmp/ur_v2.txt)"
exit 0
