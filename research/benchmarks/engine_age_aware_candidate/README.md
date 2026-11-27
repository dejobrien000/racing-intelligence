# Age-aware update rule candidate (NOT LIVE — shadow only)

Engine v2.3 rebuilt in full with one change to how a run moves a horse's rating:
- a defeat counts at most **12 lengths** in the performance figure (the recorded margin is never changed), as in the update-rule shadow;
- a run **better than expected** moves the rating **m times** as far, with **m = 1 + 0.3 × exp(−n/6)**: 1.3 on a horse's first run held,
  1.15 after 4 runs, 1.04 after 12, about 1.0 after 20. **n** = runs held in our history before this run; a horse **aged 5 or more** at the
  run counts as n ≥ 24 (m ≈ 1.006).
- runs worse than expected move the rating exactly as in Engine v2.3.

Maths (dyn_rating_innov.py): u = (perf − race mean perf) − (μ − race mean μ); K = var/(var + s²); μ ← μ + K·m·u if u > 0, else μ + K·u.
Settings: WCREDIT=0.25 RATING_CAP_L=12 RATING_CAP_SCOPE=all RATING_GOOD_TAPER=0.3,6 RATING_TAPER_AGEFLOOR=engine/frames/age_at_run.parquet
(age at each completed run, taken from the production Engine v2.3 frame; RATING_TAPER_AGEMIN default 5).

All three layers are its own: `candidates_national_common.json`, `engine_v2.json` (NSW/VIC/ACT/SA/WA/TAS family), `engine_v2_2.json`.
kg scale 0.334 model units per kg (Engine v2.3 0.268; update rule 0.315) — a different scale, not a change in any horse's ability.
Built 27 Nov 2026 4:41pm Brisbane by the Engine v2.3 release chain in a sandbox; rating identical to the research implementation (U5EC,
max difference 0.0); speed figures identical to production (0.0). Fingerprints in each file's `candidate_record`.

Scored every morning from the **28 Nov 2026 run** (brought forward from 29 Nov by Damo, Batch 23 D10, 27 Nov 10:01pm) by `UR_VARIANT=ageaware ops/run_update_shadow.sh` into `prospective/shadow/age_aware/`
(own index, own prospective clock), after publishing. Never the dashboard, the ranking or the settlement; settled separately in the
evaluation ledger and shown in Engine Performance. Approved as a frozen shadow by Damo, 27 Nov 2026 (Batch 19 brief A2). Frozen: any
change needs a new version and a new clock.

Caveats: both historical periods influenced the design (not untouched validation). Runs held are not true career starts; by Nov 2026
most horses aged 5+ with few runs held are genuinely lightly raced (TAB form records 26–27 Nov: 28 of 30), so the age floor now treats
those late starters as exposed (Batch 19 B6). A career-start version would be a separate candidate.
