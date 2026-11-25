#!/usr/bin/env bash
# one variant, one mode per process (memory); peak RSS logged
cd /tmp/cand/research; export PYTHONPATH=.
V=$1; M=$2
python3 - "$V" "$M" <<'PY' > /tmp/cand/ev_${V}_${M}.log 2>&1
import sys, runpy, resource, threading, time
V, M = sys.argv[1], sys.argv[2]
sys.argv = ['cand_eval.py', V, f'/tmp/cand/frames/{V}_national.parquet', f'/tmp/cand/f_{V}/b10/out/feat.parquet', M]
try: runpy.run_path('/tmp/cand/cand_eval.py', run_name='__main__')
finally: print('peak RSS GB', round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 2), flush=True)
PY
echo "exit $?" >> /tmp/cand/ev_${V}_${M}.log
