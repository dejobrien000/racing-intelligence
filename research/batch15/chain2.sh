#!/usr/bin/env bash
for spec in "U1 12 1.0" "U4 25 1.3" "U6 15 1.5" "U7 10 1.3"; do
  set -- $spec; V=$1; export CAP=$2 GOOD=$3
  cd /tmp/cand/research; export PYTHONPATH=. WCREDIT=0.25 LAB_IN=/tmp/cand/frames/C2_national_runs.parquet LAB_OUT=/tmp/cand/frames/${V}_national.parquet
  echo "[$(date +%T)] $V frame CAP=$CAP GOOD=$GOOD"; python3 /tmp/cand/u5/build_u5.py > /tmp/cand/u5/lab_$V.log 2>&1 || { echo "$V FRAME FAILED"; continue; }
  D=/tmp/cand/f_$V; rm -rf $D; mkdir -p $D/engine/frames $D/b10/out; ln -s /tmp/cand/frames/${V}_national.parquet $D/engine/frames/national.parquet
  (cd $D && python3 /home/claude/racing-intelligence/research/batch10/scripts/feat10.py > /tmp/cand/u5/feat_$V.log 2>&1) || { echo "$V FEAT FAILED"; continue; }
  bash /tmp/cand/ev.sh $V R; tail -2 /tmp/cand/ev_${V}_R.log | head -1
done
echo "[$(date +%T)] CHAIN2 DONE"
