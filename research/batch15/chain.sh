#!/usr/bin/env bash
cd /tmp/cand/research; export PYTHONPATH=. WCREDIT=0.25 LAB_IN=/tmp/cand/frames/C2_national_runs.parquet LAB_OUT=/tmp/cand/frames/U5_national.parquet
echo "[$(date +%T)] U5 frame"; python3 /tmp/cand/u5/build_u5.py > /tmp/cand/u5/lab.log 2>&1 || { echo FRAME FAILED; tail -3 /tmp/cand/u5/lab.log; exit 1; }
D=/tmp/cand/f_U5; rm -rf $D; mkdir -p $D/engine/frames $D/b10/out; ln -s /tmp/cand/frames/U5_national.parquet $D/engine/frames/national.parquet
echo "[$(date +%T)] U5 feat10"; (cd $D && python3 /home/claude/racing-intelligence/research/batch10/scripts/feat10.py > /tmp/cand/u5/feat.log 2>&1) || { echo FEAT FAILED; tail -3 /tmp/cand/u5/feat.log; exit 1; }
echo "[$(date +%T)] U5 eval"; bash /tmp/cand/ev.sh U5 R; tail -3 /tmp/cand/ev_U5_R.log
echo "[$(date +%T)] U5 CHAIN DONE"
