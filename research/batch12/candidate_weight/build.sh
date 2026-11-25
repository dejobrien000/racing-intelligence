#!/usr/bin/env bash
cd /tmp/cand/research; export PYTHONPATH=. NAT_STATES=NSW,VIC,ACT,SA,WA,TAS NAT_QLD_BN=1
for V in "$@"; do
  unset SPL_FIXED WCREDIT
  case $V in C2) export SPL_FIXED=0.170 WCREDIT=0.25;; W025) export WCREDIT=0.25;; S1) export SPL_FIXED=0.170;; B0) ;; esac
  echo "[$(date +%T)] $V national.py"; python3 national.py ../history/history.duckdb > /tmp/cand/nat_$V.log 2>&1 || { echo "$V national FAILED"; tail -3 /tmp/cand/nat_$V.log; continue; }
  echo "[$(date +%T)] $V lab.py"; python3 engine/lab.py > /tmp/cand/lab_$V.log 2>&1 || { echo "$V lab FAILED"; tail -3 /tmp/cand/lab_$V.log; continue; }
  cp engine/frames/national.parquet /tmp/cand/frames/${V}_national.parquet; cp national_runs.parquet /tmp/cand/frames/${V}_national_runs.parquet
  echo "[$(date +%T)] $V built"
done
echo "[$(date +%T)] BUILD DONE $*"
