# Batch 8 (25 Nov 2026): audit and quick tests
Write-up: research doc, tab "Batch 8: audit and research restart". Run from research/ with PYTHONPATH=.
1. scripts/events.py -> /tmp/exp/rt/events.parquet (run -> next run, point-in-time; outcome = next run's dyn_nat_inn)
2. scripts/tests_abc.py (tests 1-3), scripts/t4_sect.py (test 4, Qld 200m splits), scripts/incr.py (terms on top of v2),
   scripts/calib_light.py (calibration of high chances by starts; 2025-fit judged on 2026)
Outputs in out/. None of these are model inputs; no coefficients were changed.
