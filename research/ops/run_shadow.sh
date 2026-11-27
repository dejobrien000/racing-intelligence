#!/usr/bin/env bash
# SHADOW scoring (NOT LIVE), daily run step 5c: Queensland Engine v2.1.2-candidate beside production v2.1.1 (approved for shadow
# scoring by Damo 25 Nov 2026). Writes only to prospective/shadow/qld_v2_1_2/ (own index). Never touches the dashboard, the
# production predictions, the ranking or the settlement. A failure here never affects production. Usage (from research/): ops/run_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.
# previous production engines kept for rollback and prospective comparison (Damo 26 Nov 2026); independent of the Qld v2.1.2 shadow below
bash ops/run_prev_shadow.sh "$D" || echo "WARNING prev-engine shadow (production unaffected)"
# Engine v2.4 candidate (v2.3 + handicap weight slope), shadow only (Batch 16 B7, 27 Nov 2026)
bash ops/run_v24_shadow.sh "$D" || echo "WARNING v2.4 shadow (production unaffected)"
# rating update rule candidate (12 L cap on the performance figure, good runs 1.3x), all three layers its own, shadow only (Batch 16 B9, 27 Nov 2026)
bash ops/run_update_shadow.sh "$D" || echo "WARNING update-rule shadow (production unaffected)"
RQB=$(ls collect/national/$D/bundles/rqpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
[ -n "$RQB" ] || { echo "shadow: no Queensland bundle for $D (no Qld meetings?)"; exit 0; }
SHADOW_QLD_CANDIDATES=benchmarks/candidate_qld_v2_1_2/candidates_manifest.json python3 prerace/score_prerace.py "$RQB" ../history/history.duckdb > /tmp/shadow_v1.txt 2>&1 \
  || { echo "WARNING shadow v1 failed (production unaffected): $(tail -1 /tmp/shadow_v1.txt)"; exit 0; }
SNAPDIR=collect/national/$D/bundles python3 ops/shadow_qld.py "$D" > /tmp/shadow_v2.txt 2>&1 \
  && { grep '^shadow written' /tmp/shadow_v2.txt; echo "shadow Qld v2.1.2 scored (not live)"; } \
  || echo "WARNING shadow v2 failed (production unaffected): $(tail -1 /tmp/shadow_v2.txt)"
