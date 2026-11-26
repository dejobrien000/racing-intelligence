# Batch 15 ledger (27 Nov 2026, from 07:39): rating foundations, physical profiles, small improvements

Brief: "Horse Intel - Rating Foundations, Physical Profiles and Incremental Improvements" (Damo, 07:39 27 Nov). Research only; no
production change; the 27 Nov 7:30am run was verified before any work started. Report (Docs): "Horse Intel - Batch 15: rating
foundations, physical profiles and small improvements" (artifact aec1cba8-306d-4b19-9f55-aa6252a79f0b).

| Script | Brief | Output | Result |
|---|---|---|---|
| build_v24c.py (run in the v2.3 build sandbox /tmp/c2/research) | s1 | benchmarks/engine_v2_4_candidate/engine_v2_2.json | weight slope in release-build form: fit<=2023 judge 2024 +0.0005 (0.0003-0.0007); fit<=2024 judge 2025-26 +0.0015 (0.0011-0.0018); 3.9% of chance per kg vs field in Benchmark races |
| (inline checks, report s4) | s1 | report | class at race time needs TAB raceClassConditions (one racecard checked: 'TAB HANDICAP' = '3YO+ BM72'); bm_change never served (0/67 runners today; 24% non-missing in training); serving it would cost -0.0008 (0.0004-0.0013) per race on 2025-26; history weights are carried weights (NSW 4,136 claiming rides: 100%); claimers 197 wins vs 217 / 220 expected (n.s.) |
| b15_responsiveness.py | s2 | out_responsiveness.json | after 10+ kg-worse runs: next +0.66 vs revised, -4.3 vs pre-run rating over 5 starts; moderate poor runs under-reacted; good runs under-reacted; heavy defeats with abnormal late decline +0.95 next (normal shape -0.54); decline adds +0.36 (0.11-0.62) holding defeat size |
| b15_learning.py | s7 | out_learning.json | implied best move: poor runs 0.80x, good runs 1.84x (2025-26); narrow defeats 1.2-1.6x, 10-25 L 0.79x; poor run after a good run 0.64x; good after good 1.93x; experience/uncertainty/completeness matter little |
| b15_update_proto.py | s2/s7 | out_update_proto.json | rating-level accuracy per run: cap 12 L +0.0046/+0.0058; good 1.3x +0.0045/+0.0024; cap 12 + good 1.3x +0.0104/+0.0096 (2024/2025-26), stability unchanged |
| build_u5.py, chain.sh, chain2.sh, cmp.py (harness /tmp/cand) | s2/s7 | /tmp/cand/res_U*_R.parquet | Engine v2.3 refitted on the new rating: cap 12 +0.0064/+0.0040; good 1.3x alone -0.0009/-0.0008 (n.s.); cap 12 + 1.3x +0.0071 (0.0051-0.0092) / +0.0055 (0.0038-0.0072); cap 10 + 1.3x +0.0073/+0.0055; cap 15 + 1.5x +0.0035/+0.0018 |
| b15_measured_times.py (+ Vic inline) | s6 | out_measured_times.json | official margins are clock-derived (within-race r 1.000 Qld/SA, 0.9997 Vic); seconds per length Qld 0.170, SA 0.159, Vic 0.162; clock adds +0.065 kg per kg of disagreement (Qld) |
| b15_profiles_stewards.py | s3 | out_profiles_stewards.json | Qld: progressive fade + vet finding +1.64 (1.25-2.03); + performance concern +0.96; + interference +0.50; meaning differs by profile for vet findings (p<0.001) |
| b15_rider_tables.py | s4 | rider_tables.csv, out_rider_tables.json, prospective/research/rider_momentum_frozen_20261126.csv | 120 riders profiled; trainer-half agreement r 0.57 (timing), 0.61 (hold); 19 of 20 strongest hold riders are late-ground riders (r -0.59); no rider has 60+ rides in both states |
| b15_artifact_audit.py | s9 | out_artifact_audit.json | corrected within-race control changes nothing material (dip 0.27->0.26; progressive fade 0.59->0.55; j_spec 1.14->1.09) |

2024 status: clean only for the weight slope (found on 2025-26, preregistered on 2024). Physical, rider, distance-form, update-rule and
stewards items all used 2024 or both periods: first clean evidence is prospective. Correction made in the Batch 14 follow-up report.
