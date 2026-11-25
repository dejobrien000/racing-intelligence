#!/usr/bin/env bash
# SHADOW scoring (NOT LIVE), daily run step 5c: Queensland Engine v2.1.2-candidate beside production v2.1.1 (approved for shadow
# scoring by Damo 25 Nov 2026). Writes only to prospective/shadow/qld_v2_1_2/ (own index). Never touches the dashboard, the
# production predictions, the ranking or the settlement. A failure here never affects production. Usage (from research/): ops/run_shadow.sh <YYYYMMDD>
set -uo pipefail
D=$1; export PYTHONPATH=.
RQB=$(ls collect/national/$D/bundles/rqpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
[ -n "$RQB" ] || { echo "shadow: no Queensland bundle for $D (no Qld meetings?)"; exit 0; }
SHADOW_QLD_CANDIDATES=benchmarks/candidate_qld_v2_1_2/candidates_manifest.json python3 prerace/score_prerace.py "$RQB" ../history/history.duckdb > /tmp/shadow_v1.txt 2>&1 \
  || { echo "WARNING shadow v1 failed (production unaffected): $(tail -1 /tmp/shadow_v1.txt)"; exit 0; }
SNAPDIR=collect/national/$D/bundles python3 ops/shadow_qld.py "$D" > /tmp/shadow_v2.txt 2>&1 \
  && { grep '^shadow written' /tmp/shadow_v2.txt; echo "shadow Qld v2.1.2 scored (not live)"; } \
  || echo "WARNING shadow v2 failed (production unaffected): $(tail -1 /tmp/shadow_v2.txt)"
