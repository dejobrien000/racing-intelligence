#!/usr/bin/env bash
while ! grep -q "FIX DONE\|FAILED" /tmp/exp/run_fix.log; do sleep 20; done
cd /tmp/exp/research; export PYTHONPATH=. NAT_STATES=NSW,VIC,ACT,SA,WA,TAS NAT_QLD_BN=1 SPL_FIXED=0.170 WCREDIT=0.25
echo "[$(date +%T)] C2 rebuild"; python3 national.py ../history/history.duckdb > /tmp/exp/nat_C2.log 2>&1 && python3 engine/lab.py > /tmp/exp/lab_C2.log 2>&1 && cp engine/frames/national.parquet /tmp/exp/frame_C2.parquet && cp national_runs.parquet /tmp/exp/national_runs_C2.parquet && python3 b11eval.py C2 2>&1 | grep -v "Warn\|sd = t"
echo "[$(date +%T)] C2 DONE"
