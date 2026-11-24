#!/usr/bin/env bash
# After any refresh: cross-race ranking, dashboard export, self-contained copy. Usage: ops/rebuild_dashboard.sh 20261125
set -euo pipefail
D=$1; DATE="${D:0:4}-${D:4:2}-${D:6:2}"
PYTHONPATH=. python3 engine/daily_ranking_v2.py "$D" > /tmp/rank.txt 2>&1; tail -1 /tmp/rank.txt
PYTHONPATH=. python3 engine/export_ui.py "$D" > /tmp/export.txt 2>&1; sed -n 1p /tmp/export.txt
python3 ui/build_standalone.py "$DATE"
