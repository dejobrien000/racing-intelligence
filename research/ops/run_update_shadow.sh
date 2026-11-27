#!/usr/bin/env bash
# RATING UPDATE RULE CANDIDATE SHADOW (NOT LIVE; Batch 16 B9, approved by Damo 27 Nov 2026: "Approve building the new rating update
# mechanism as a shadow candidate."). Engine v2.3 rebuilt in full with the candidate rule: a defeat counts at most 12 lengths in the
# performance figure (the recorded margin is never changed) and a run better than expected moves the rating 1.3 times as far. All three
# layers are its own (benchmarks/engine_update_rule_candidate/). Scored on the same morning snapshot after publishing. Writes only to
# prospective/shadow/update_rule/ (own INDEX.csv). Never the dashboard, the ranking or the settlement. A failure is a warning, never a
# failed run. Usage (from research/): ops/run_update_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; B=collect/national/$D/bundles
# UR_VARIANT=caponly: the simpler heavy-defeat-cap-only comparator (12 L cap, good runs NOT moved further), kept for comparison (brief s9)
if [ "${UR_VARIANT:-}" = caponly ]; then
  R=${UR_ROOT:-prospective/shadow/cap_only}; CD=benchmarks/engine_cap_only_candidate; FR=engine/frames/national_cap_only.parquet; GX=1
  LBL="Cap-only candidate (not live)"; SLBL="shadow candidate: heavy-defeat cap only (12 L), not live"; N="cap-only shadow"
elif [ "${UR_VARIANT:-}" = ageaware ]; then
  # Batch 19 A2 (approved by Damo 27 Nov 2026): age-aware update rule, its own frozen candidate and prospective clock (from the 29 Nov run)
  R=${UR_ROOT:-prospective/shadow/age_aware}; CD=benchmarks/engine_age_aware_candidate; FR=engine/frames/national_age_aware.parquet; GX=1
  LBL="Age-aware update rule (not live)"; SLBL="shadow candidate: age-aware update rule (12 L cap; good runs 1+0.3exp(-n/6) times, 5yo+ counted as exposed), not live"; N="age-aware shadow"
  export RATING_GOOD_TAPER=0.3,6 RATING_TAPER_AGEFLOOR=engine/frames/age_at_run.parquet
else
  R=${UR_ROOT:-prospective/shadow/update_rule}; CD=benchmarks/engine_update_rule_candidate; FR=engine/frames/national_update_rule.parquet; GX=1.3
  LBL="Update-rule candidate (not live)"; SLBL="shadow candidate: rating update rule (12 L cap, 1.3x good runs), not live"; N="update-rule shadow"
fi
[ -f $CD/engine_v2.json ] && [ -f $CD/engine_v2_2.json ] && [ -f $CD/candidates_national_common.json ] || { echo "$N: no candidate files"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f national_runs_c2.parquet ] || { echo "$N: needs Engine v2.3 history (switch and national_runs_c2)"; exit 0; }
NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1); [ -n "$NB" ] || { echo "$N: no national bundle"; exit 0; }
export ENGINE_C2=1 WCREDIT=0.25 RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_X=$GX ENGINE_CAND_DIR=$CD ENGINE_CAND_FRAME=$FR \
       ENGINE_CAND_LABEL="$LBL" SHADOW_LABEL="$SLBL"
# its own rating frame, rebuilt (about a minute) whenever the Engine v2.3 history file is newer; same code as production plus the rule
T=${UR_VARIANT:-ur}_${GX}   # log tag (keeps each shadow's logs apart)
if [ ! -f $FR ] || [ $FR -ot national_runs_c2.parquet ]; then
  if [ "${UR_VARIANT:-}" = ageaware ]; then   # age at each completed run, from the production frame (fixed history; point in time)
    python3 -c "import pandas as pd;f=pd.read_parquet('engine/frames/national_c2.parquet',columns=['race','horse','age_n']).rename(columns={'race':'race_key','age_n':'age'}).dropna();f.to_parquet('$RATING_TAPER_AGEFLOOR')" \
      || { echo "WARNING $N: age file failed (production unaffected)"; exit 0; }
  fi
  LAB_IN=national_runs_c2.parquet LAB_OUT=$FR python3 engine/lab.py > /tmp/ur_lab_${T}.txt 2>&1 \
    && echo "$N: frame rebuilt" || { echo "WARNING $N: frame failed (production unaffected): $(tail -1 /tmp/ur_lab_${T}.txt)"; rm -f $FR; exit 0; }
fi
mkdir -p $R
PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/ur_v1_${T}.txt 2>&1 \
  || { echo "WARNING $N v1 failed (production unaffected): $(tail -1 /tmp/ur_v1_${T}.txt)"; exit 0; }
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
[ -n "$ONLY" ] || { echo "$N: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/ur_v2_${T}.txt 2>&1 \
  && echo "$N scored (not live): $(grep -c '^written' /tmp/ur_v2_${T}.txt) meetings" \
  || echo "WARNING $N v2 failed (production unaffected): $(tail -1 /tmp/ur_v2_${T}.txt)"
exit 0
