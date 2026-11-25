#!/usr/bin/env bash
# after the frames are built: v2.2 features per variant (feat10), then the evaluation. Sequential (memory).
while ! grep -q "BUILD DONE" /tmp/cand/build.log; do sleep 20; done
for V in B0 C2 W025 S1; do
  [ -f /tmp/cand/frames/${V}_national.parquet ] || { echo "no frame for $V"; continue; }
  D=/tmp/cand/f_$V; rm -rf $D; mkdir -p $D/engine/frames $D/b10/out; ln -s /tmp/cand/frames/${V}_national.parquet $D/engine/frames/national.parquet
  echo "[$(date +%T)] $V feat10"; (cd $D && python3 /home/claude/racing-intelligence/research/batch10/scripts/feat10.py > /tmp/cand/feat_$V.log 2>&1) || { echo "$V feat10 FAILED"; tail -3 /tmp/cand/feat_$V.log; continue; }
done
cd /tmp/cand/research; export PYTHONPATH=.
echo "[$(date +%T)] eval B0"; python3 /tmp/cand/cand_eval.py B0 /tmp/cand/frames/B0_national.parquet /tmp/cand/f_B0/b10/out/feat.parquet P,R,R-noW 2>&1 | grep -v "Warn\|sd = t\|t = t\["
for V in C2 W025 S1; do echo "[$(date +%T)] eval $V"; python3 /tmp/cand/cand_eval.py $V /tmp/cand/frames/${V}_national.parquet /tmp/cand/f_$V/b10/out/feat.parquet R,R-noW 2>&1 | grep -v "Warn\|sd = t\|t = t\["; done
echo "[$(date +%T)] EVAL DONE"
