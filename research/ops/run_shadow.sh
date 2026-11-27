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
[ -d benchmarks/engine_cap_only_candidate ] && { UR_VARIANT=caponly bash ops/run_update_shadow.sh "$D" || echo "WARNING cap-only shadow (production unaffected)"; }
# age-aware update rule (Batch 19 A2, approved 27 Nov 2026): own frozen candidate and clock, starting with the 29 Nov run (not the first corrected run)
[ -d benchmarks/engine_age_aware_candidate ] && [ "$D" -ge 20261129 ] && { UR_VARIANT=ageaware bash ops/run_update_shadow.sh "$D" || echo "WARNING age-aware shadow (production unaffected)"; }
# trainer debut record (Batch 19 A3, approved 27 Nov 2026): Engine v2.3 + one term for genuine debutants; production frame read-only; from the 29 Nov run
[ -d benchmarks/engine_trainer_debut_candidate ] && [ "$D" -ge 20261129 ] && { bash ops/run_trainer_debut_shadow.sh "$D" || echo "WARNING trainer-debut shadow (production unaffected)"; }
# Queensland common national framework, configs 2 and 4 (Batch 17 B2, approved 27 Nov 2026); after the update-rule shadow, whose rating frame config 4 uses
bash ops/run_qld_common_shadow.sh "$D" || echo "WARNING Qld common shadow (production unaffected)"
RQB=$(ls collect/national/$D/bundles/rqpre_${D}_snap*.jsonl.gz 2>/dev/null | tail -1)
[ -n "$RQB" ] || { echo "shadow: no Queensland bundle for $D (no Qld meetings?)"; exit 0; }
SHADOW_QLD_CANDIDATES=benchmarks/candidate_qld_v2_1_2/candidates_manifest.json python3 prerace/score_prerace.py "$RQB" ../history/history.duckdb > /tmp/shadow_v1.txt 2>&1 \
  || { echo "WARNING shadow v1 failed (production unaffected): $(tail -1 /tmp/shadow_v1.txt)"; exit 0; }
SNAPDIR=collect/national/$D/bundles python3 ops/shadow_qld.py "$D" > /tmp/shadow_v2.txt 2>&1 \
  && { grep '^shadow written' /tmp/shadow_v2.txt; echo "shadow Qld v2.1.2 scored (not live)"; } \
  || echo "WARNING shadow v2 failed (production unaffected): $(tail -1 /tmp/shadow_v2.txt)"
