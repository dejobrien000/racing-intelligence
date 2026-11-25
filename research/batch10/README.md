# Batch 10 (25 Nov 2026): national depth, ability vs expression, discovery
Write-up: research doc, tab "Batch 10: national depth and discovery". Nothing here is in production.
Run from research/ with the six-state frame (database master-2026-11-23-sa-wa-tas), PYTHONPATH=.:batch10/scripts (scripts expect b10/out paths: adjust or symlink).
- scripts/lib10.py      harness: Engine v2 score held fixed as an offset; discovery = fit Oct22-Dec23 judge 2024; validation = fit <2025 judge 2025-26;
                         meeting bootstrap 95% CIs; east (NSW/VIC/ACT) vs west (SA/WA/TAS) split; Benjamini-Hochberg q<0.10 on discovery.
- scripts/feat10.py     pre-race features: career shape & own variability (s5), preparations (s6), workload (s7), dynamic jockey/trainer (s9), trainer decisions (s8)
- scripts/t10_run.py    national tests -> out/t10_discovery.csv, t10_validation.csv, t10_joint.csv
- scripts/t10b_bundle.py residual-scan items + v2.2 research candidate bundle -> out/t10b.csv, t10b_bundle_coefs.csv
- scripts/q10.py        Queensland tracked races: style vs opposition (s3), trip x class by finishing profile (s4), composition (s7) -> out/q10_*.csv
- scripts/s10_resid.py  actual/expected wins by ~150 pre-race groups (2023-24 discovery, 2025-26 check) -> out/s10_resid.csv
- scripts/s1_six_state.py Engine v2 by state / tier / SA-WA-Tas venue -> out/s1_*.csv; out/s11_shippers.csv interstate travellers; out/venue_strength.csv measured venue class
Evidence status: research period only. 2025-26 has been examined repeatedly (and some residual patterns were first noticed there), so it is not an
untouched test; prospective evidence starts with races from 26 Nov 2026. Negative results are kept in the same tables.
Known issue: the discovery BH filter used two-sided p-values, so a few terms with significantly NEGATIVE discovery gains were carried to validation; all of them
failed validation (see t10_validation.csv) and none is in the candidate bundle.
