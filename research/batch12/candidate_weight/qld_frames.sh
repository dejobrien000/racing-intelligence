#!/usr/bin/env bash
# after the national evaluation: Queensland v3 frames from the clean sandbox. B0 must reproduce production national_v3 exactly.
while ! grep -q "EVAL DONE" /tmp/cand/run_eval.log; do sleep 30; done
cd /tmp/cand/research; export PYTHONPATH=.
for V in B0 C2 W025; do
  unset WCREDIT; case $V in C2|W025) export WCREDIT=0.25;; esac
  cp /tmp/cand/frames/${V}_national.parquet engine/frames/national.parquet
  echo "[$(date +%T)] $V build_frame_v3"; python3 engine/build_frame_v3.py > /tmp/cand/v3_$V.log 2>&1 || { echo "$V v3 FAILED"; tail -3 /tmp/cand/v3_$V.log; continue; }
  cp engine/frames/national_v3.parquet /tmp/cand/frames/${V}_national_v3.parquet; echo "[$(date +%T)] $V v3 built"
done
echo "[$(date +%T)] QLD CHAIN DONE"
