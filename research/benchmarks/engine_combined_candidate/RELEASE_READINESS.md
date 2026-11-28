# Engine v2.6 (combined national candidate): release readiness

Damo approved the release (Batch 29 s1, 28 Nov 2026 9:12pm). It takes effect from the first appropriate morning run after every check
below passes. v2.5 stays as the independently scored immediate fallback. v2.3's historical and prospective records are kept
unchanged.

| Check | Status | Evidence |
| --- | --- | --- |
| Historical class parity | Passed after a serving fix (28 Nov) | 10,982 identical runs: 94.95% agreement before, 99.78% after counting TAB 'BM0-NN' (SA/Vic restricted benchmarks) as not Benchmark, which matches Breednet's 'Restricted' label. Remaining: 23 WA runs that Breednet labels 'Benchmark' (served 0 by the WA rule) and 1 Vic. batch29/out_b29_class_parity.json |
| Live class parity | Waiting for Monday's master | Pre-race TAB class for 27-28 Nov races (159 + 98) against Breednet's class for the same races. Those races are only in the master after Monday's refresh. |
| Release-chain validation | Passed | Built through freeze -> release_v2 -> third layer. 2025-26: +0.0043 (+0.0035 to +0.0051) vs v2.5 as built, 23,729 races. Matched tables in batch29/out_b29_perf_tables.json |
| Distance serving | Passed | Serving vs offline: max difference 3e-5 (28 Nov, 695 runners) |
| Trainer and sire serving | Passed | Historical vs serving: exact on 6 sample dates (batch28/b28_debut_terms.py) |
| Essential inputs | Passed (28 Nov) | TAB class held for 98 of 98 races; sire held for 1,270 of 1,270 form runners |
| Display calibration | Built | runner_calibration.json (bent line, from its own 2025-26 out-of-sample chances). Top-pick terciles 0.240 / 0.314 (v2.5: 0.240 / 0.313) |
| Operational shadow scoring | First live run 29 Nov 7:30am | Smoke test on 28 Nov fields: 695 runners, chances sum to 100. Needs clean shadow runs on Sunday and Monday. |
| Integrity and calibration defects | None found so far | Calibration error 0.29 pts (v2.5: 0.30) |
| Release wiring | To do on Sunday after the first v2.5 run | Switch file, run_daily block, export/ranking labels, v2.5 fallback shadow, release manifest. Same pattern as v2.5. |

**Earliest release:** the first morning run after the live class parity passes on Monday's refreshed master and the Sunday and
Monday shadows are clean. On the current schedule that is the Tuesday 1 Dec 7:30am run.

The release record will document two things separately:

- the engine files and settings
- the history version (Monday's refreshed master), recorded as its own update
