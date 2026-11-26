# Batch 14 ledger (26-27 Nov 2026 night): physical performance, momentum, course geometry, rider specialisation

Damo's brief calls this "Research Batch 13"; the folder is batch14 because research/batch13 already holds the 26 Nov consolidation tests.
Research only: nothing here changes production (Engine v2.3 six states, Engine v2.1.3 Qld from 27 Nov). No market data anywhere.

Data: Queensland RQ tracking (81,116 finishers in 8,510 races where every finisher has complete 200 m splits, Oct 2022 - Nov 2026),
South Australia tracking (17,027 finishers, 1,591 races, Jan 2024 - Nov 2026), national v3 frame for ratings and jockeys (all states).
Measured splits only: deficits to the leader are from each runner's own cumulative times; nothing is estimated or filled.
Main outcome: next-run rating surprise (kg; how much better or worse the horse ran than its rating said). The rating has already absorbed
this run's margin, so anything that predicts it is information the rating missed. Prospective by construction.
Periods: Qld 2022-24 = discovery; Qld 2025-26 = re-used (Batch 12 looked at similar Qld sectional measures, so not untouched);
SA 2024-26 = independent check (SA tracking had never been used to develop a sectional feature; it has now been used for the tests below).
About 45 tests were run; results quoted as findings clear their 95% intervals by a wide margin, the rest are reported as uncertain.

| Script | Brief | Output | Result in one line |
|---|---|---|---|
| b14_build.py | data | /home/claude/b14/runs_*.parquet (not committed) | per-run deficits at 1000/800/600/400/200/line, segment speeds, tempo z, rail; checks: Qld deficit at the line vs margin x 0.17 median diff 0.006 s |
| b14_finish.py | s2, s3 | out_finish_features.csv, out_finish_leaders.json | weakest last-600 section (holding the average) -0.57/-0.50/-0.77 kg per sd; leaders table below |
| b14_dip.py | s2, s5 | out_dip.json | an UNEVEN last 600 precedes a better next run: +0.26 (0.18-0.33) Qld 22-24, +0.22 Qld 25-26, +0.31 (0.20-0.42) SA |
| b14_qld_engine.py | s2 vs production | out_qld_engine_dip.json | on top of Qld Engine v2.1.3: 2024 +0.0049 (0.0009-0.0094), 2025-26 +0.0011 (-0.0021 to +0.0040) |
| b14_accel.py | s4, s7 | out_accel.json | timing is a horse trait (split-half r 0.41 Qld, 0.32 SA) and a rider trait within the same horse (0.46, 0.52); no course interaction; early movers hold on less |
| b14_deter.py | s8, s9 | out_deter.json | flat kick / faded / slow-cruise runs vs own norm do not predict worse next runs and rarely recur; owner's contexts not supported statistically |
| b14_jockey.py, b14_jspec2.py, b14_jspec_feat.py | s11 | out_jockey.json, out_jspec2.json | jockey distance form real but small (+0.26 kg per kg beyond j_surp and trainer); Engine v2.3 test +0.00007 / +0.00014: negligible |
| b14_jockey.py, b14_workload2.py | s12 | out_jockey.json, out_workload2.json | no fatigue: the apparent improvement through a meeting is shared by trainers (artifact); rating-free check -0.4 to -1.0% of the field |
| b14_ground.py | s6 | out_ground.json | width slightly under-credited (+0.06 to +0.08 kg per sd, Qld); timing of width and accelerating-while-wide no effect; cover not measurable |
| b14_opp.py | s10 | out_opp.json | no interaction between physical profile and easier opposition next time |

Engine test (s11) used the Batch 12 harness (/tmp/cand, mode R, every layer refitted, Engine v2.3 frame): EXTRA=j_spec,t_spec.

Case study, Pride Of Jenni (measured runs held): Doomben 24 May 2025 R8 2000 m (tempo z +1.96; led by 0.43 s at 800 m to go and 0.04 s at the
400; final 200 at 14.53 m/s, 10th-fastest of 12; finished 10th by 10.9 L); Doomben 23 May 2026 R8 2000 m (tempo z +1.35; 1.84 s clear at 800 m to go, 1.24 s at the 400, 0.35 s at
the 200; last 200 15.63 m/s vs the winner's 16.54; caught, 2nd by 0.45 s); Caulfield 27 Sep 2026 R5 1600 m (Vic tracking: led at every mark, 0.40 s clear at
800 m from the start, lead 0.26 s at the line; final 200 16.92 m/s, third-fastest of six). Her other 32 races are held without sectionals.

Moonee Valley: held 21 Oct 2022 - 25 Oct 2025 (73 meetings, old layout only; no tracking held). Redeveloped course (published plans):
1,702 m circuit, 317 m straight (old 1,805 m and 173 m), realigned 90 degrees, planned return 2027. Rule: the new layout gets its own
configuration key; no old-layout tendency transfers to it.
