#!/usr/bin/env bash
cd /tmp/exp/research; export PYTHONPATH=. NAT_STATES=NSW,VIC,ACT,SA,WA,TAS NAT_QLD_BN=1
for V in C1 W025 W000; do
  unset SPL_FIXED WCREDIT
  case $V in C1) export SPL_FIXED=0.170 WCREDIT=0.5;; W025) export WCREDIT=0.25;; W000) export WCREDIT=0;; esac
  echo "[$(date +%T)] $V national.py"; python3 national.py ../history/history.duckdb > /tmp/exp/nat_$V.log 2>&1 || { echo "$V national FAILED"; continue; }
  echo "[$(date +%T)] $V lab.py"; python3 engine/lab.py > /tmp/exp/lab_$V.log 2>&1 || { echo "$V lab FAILED"; continue; }
  echo "[$(date +%T)] $V eval"; python3 b11eval.py $V 2>&1 | grep -v "Warn\|sd = t"
done
echo "[$(date +%T)] MORE DONE"
