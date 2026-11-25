#!/usr/bin/env bash
for VM in "B0 R-noW" "C2 R" "C2 R-noW" "W025 R" "S1 R" "W025 R-noW" "S1 R-noW"; do
  set -- $VM; echo "[$(date +%T)] eval $1 $2"; /tmp/cand/ev.sh $1 $2; grep -E "^$1 |peak|exit" /tmp/cand/ev_$1_$2.log
done
echo "[$(date +%T)] EVAL DONE"
cd /tmp/cand/research; export PYTHONPATH=.
for V in B0 C2 W025; do
  unset WCREDIT; case $V in C2|W025) export WCREDIT=0.25;; esac
  cp /tmp/cand/frames/${V}_national.parquet engine/frames/national.parquet
  echo "[$(date +%T)] $V build_frame_v3"; python3 engine/build_frame_v3.py > /tmp/cand/v3_$V.log 2>&1 || { echo "$V v3 FAILED"; tail -3 /tmp/cand/v3_$V.log; continue; }
  cp engine/frames/national_v3.parquet /tmp/cand/frames/${V}_national_v3.parquet; echo "[$(date +%T)] $V v3 built"
done
echo "[$(date +%T)] QLD CHAIN DONE"
