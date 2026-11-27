#!/usr/bin/env bash
# ENGINE v2.4 CANDIDATE SHADOW (NOT LIVE; Batch 16 B7, approved by Damo 27 Nov 2026 "prepare the v2.4 candidate with the switch off ...
# prospective comparisons"). Engine v2.3 + handicap weight slope, scored on the same production v1 files (the candidate changes only the
# third layer) and the same morning snapshot, after publishing. Race class comes from TAB's own class field (races.csv race_class or a
# race_class_*.txt file); a race with no class gets no handicap term. Writes only to prospective/shadow/v2_4_candidate/ (own INDEX.csv).
# Never the dashboard, the ranking or the settlement. A failure is a warning, never a failed run. Usage (from research/): ops/run_v24_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; R=prospective/shadow/v2_4_candidate; B=collect/national/$D/bundles
[ -f benchmarks/engine_v2_4_candidate/engine_v2_2.json ] || { echo "v2.4 shadow: no candidate file"; exit 0; }
[ -f ops/engine_c2_enabled ] && [ -f engine/frames/national_c2.parquet ] || { echo "v2.4 shadow: needs Engine v2.3 frames (switch and frames)"; exit 0; }
[ -f ops/engine_v24_enabled ] && { echo "v2.4 shadow: v2.4 is production; nothing to shadow"; exit 0; }
mkdir -p $R; [ -f $R/INDEX.csv ] || echo 'scored_utc,date,track,snapshot_key,file,sha256' > $R/INDEX.csv
python3 - "$D" "$R" <<'PY' || { echo "WARNING v2.4 shadow: listing failed"; exit 0; }
import sys, pandas as pd
D, R = sys.argv[1], sys.argv[2]
P = pd.read_csv('prospective/prerace/INDEX.csv'); S = pd.read_csv(f'{R}/INDEX.csv')
q = P[(P.date.astype(str) == D) & ~P.snapshot_key.str.startswith('rq') & ~P.file.str.contains('/v2_')]   # national production v1 files (listed, not copied)
q = q[~q.file.isin(S.file)]; q.to_csv(f'{R}/INDEX.csv', mode='a', header=False, index=False); print('v2.4 shadow: national v1 files listed', len(q))
PY
ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');S=S[(S.date.astype(str)=='$D')&~S.snapshot_key.str.startswith('rq')];print(','.join(sorted(set(S.track))))")
[ -n "$ONLY" ] || { echo "v2.4 shadow: no national meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B ENGINE_C2=1 ENGINE_V24=1 SHADOW_LABEL="shadow candidate: Engine v2.4 (handicap weight slope), not live" \
  python3 engine/score_v2.py "$D" > /tmp/v24_shadow.txt 2>&1 \
  && echo "v2.4 shadow scored (not live): $(grep -c '^written' /tmp/v24_shadow.txt) meetings" \
  || echo "WARNING v2.4 shadow failed (production unaffected): $(tail -1 /tmp/v24_shadow.txt)"
exit 0
