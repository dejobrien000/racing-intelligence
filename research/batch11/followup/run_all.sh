#!/usr/bin/env bash
cd /tmp/exp/research; export PYTHONPATH=. NAT_STATES=NSW,VIC,ACT,SA,WA,TAS NAT_QLD_BN=1
for V in S0 S1 W050 W075; do
  unset SPL_FIXED WCREDIT
  case $V in S1) export SPL_FIXED=0.170;; W050) export WCREDIT=0.5;; W075) export WCREDIT=0.75;; esac
  echo "[$(date +%T)] $V national.py"; python3 national.py ../history/history.duckdb > /tmp/exp/nat_$V.log 2>&1 || { echo "$V national FAILED"; tail -3 /tmp/exp/nat_$V.log; continue; }
  echo "[$(date +%T)] $V lab.py"; python3 engine/lab.py > /tmp/exp/lab_$V.log 2>&1 || { echo "$V lab FAILED"; tail -3 /tmp/exp/lab_$V.log; continue; }
  cp engine/frames/national.parquet /tmp/exp/frame_$V.parquet
  echo "[$(date +%T)] $V eval"; python3 b11eval.py $V 2>&1 | grep -v Warn
done
echo "[$(date +%T)] ALL DONE"
