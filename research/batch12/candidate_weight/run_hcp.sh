#!/usr/bin/env bash
/tmp/cand/ev.sh B0 P; grep -E "^B0 |peak|exit" /tmp/cand/ev_B0_P.log
for V in B0 C2; do for X in wt_x_hcp wt_x_nonmaiden; do
  export EXTRA=$X; /tmp/cand/ev.sh $V R; cp /tmp/cand/ev_${V}_R.log /tmp/cand/ev_${V}_R+$X.log; grep -E "^(coef )?$V|peak|exit" /tmp/cand/ev_${V}_R+$X.log
done; done; unset EXTRA
echo HCP DONE
