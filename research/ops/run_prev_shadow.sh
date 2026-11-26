#!/usr/bin/env bash
# PREVIOUS-ENGINE SHADOW (NOT LIVE), run inside daily step 5a (ops/run_shadow.sh) after publishing. Approved by Damo 26 Nov 2026 9:07pm:
# "Preserve the existing engines for rollback and prospective comparison". When a release switch is ON, the engine it replaced is scored
# on the same morning snapshot: Engine v2.2 for NSW/VIC/ACT/SA/WA/TAS (when ops/engine_c2_enabled) and Engine v2.1.1 for Qld (when
# ops/engine_qld213_enabled). Writes only to prospective/shadow/prev_engines/ (own INDEX.csv). Never the dashboard, the ranking or the
# settlement; the evaluation ledger reads it as prediction 'previous_engine'. A failure is a warning, never a failed run.
# Usage (from research/): ops/run_prev_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.; R=prospective/shadow/prev_engines; B=collect/national/$D/bundles
C2=0; Q=0; [ -f ops/engine_c2_enabled ] && C2=1; [ -f ops/engine_qld213_enabled ] && Q=1
[ $C2 = 1 ] || [ $Q = 1 ] || { echo "prev-engine shadow: no release switch on, production IS the previous engine; nothing to do"; exit 0; }
mkdir -p $R; [ -f $R/INDEX.csv ] || echo 'scored_utc,date,track,snapshot_key,file,sha256' > $R/INDEX.csv
unset ENGINE_C2 ENGINE_QLD213                       # the previous engines: v2.2 (six states) and v2.1.1 (Qld)
ONLY=""
if [ $Q = 1 ]; then
  # Qld v1 files are not changed by v2.1.3, so v2.1.1 is applied to the SAME production v1 file (listed in the shadow index, not copied)
  python3 - "$D" "$R" <<'PY' || echo "WARNING prev-engine shadow: Qld listing failed"
import sys, pandas as pd
D, R = sys.argv[1], sys.argv[2]
P = pd.read_csv('prospective/prerace/INDEX.csv'); S = pd.read_csv(f'{R}/INDEX.csv')
q = P[(P.date.astype(str) == D) & P.snapshot_key.str.startswith('rq') & ~P.file.str.contains('/v2_')]
q = q[~q.file.isin(S.file)]
q.to_csv(f'{R}/INDEX.csv', mode='a', header=False, index=False); print('prev-engine shadow: Qld v1 files listed', len(q))
PY
  ONLY=$(python3 -c "import pandas as pd;P=pd.read_csv('prospective/prerace/INDEX.csv');q=P[(P.date.astype(str)=='$D')&P.snapshot_key.str.startswith('rq')];print(','.join(sorted(set(q.track))))")
fi
if [ $C2 = 1 ]; then
  NB=$(ls $B/natpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
  if [ -n "$NB" ]; then
    PRED_ROOT=$R python3 prerace/score_national_prerace.py "$NB" ../history/history.duckdb "$D" > /tmp/prev_nat.txt 2>&1 \
      && echo "prev-engine shadow: national v1 (v2.2 rating) scored" || echo "WARNING prev-engine shadow: national v1 failed: $(tail -1 /tmp/prev_nat.txt)"
    ONLY=$(python3 -c "import pandas as pd;S=pd.read_csv('$R/INDEX.csv');print(','.join(sorted(set(S[S.date.astype(str)=='$D'].track))))")
  fi
fi
[ -n "$ONLY" ] || { echo "prev-engine shadow: no meetings"; exit 0; }
PRED_ROOT=$R ONLY_TRACKS="$ONLY" SNAPDIR=$B python3 engine/score_v2.py "$D" > /tmp/prev_v2.txt 2>&1 \
  && echo "prev-engine shadow scored (not live): $(grep -c '^written' /tmp/prev_v2.txt) meetings" \
  || echo "WARNING prev-engine shadow v2 failed (production unaffected): $(tail -1 /tmp/prev_v2.txt)"
exit 0
