#!/bin/bash
# Usage: bash after_backfill.sh <staged full bundle path>
set -e
cd /home/claude/pilot
cp "$1" breednet/bundles/
cp history/history.duckdb history/history_backup_20261124_prebackfill.duckdb
python3 history/load_breednet.py breednet/bundles history/history.duckdb 2>&1 | grep -v Warn | tail -25
cd research
python3 coverage_matrix.py ../history/history.duckdb out/coverage_matrix.csv 2>&1 | grep -v Warn | tail -30
