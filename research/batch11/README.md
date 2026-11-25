# Batch 11 ledger (25 Nov 2026): model integrity, national data depth, targeted discovery

Research only. No production rating changed. Production change tonight: dashboard display labels (see benchmarks/engine_v2/RELEASES.md).
Run from the research copy with the Batch 10 harness (batch10/scripts/lib10.py); "v2.2 out of sample" = build_v22hist.py (dev-fit
coefficients, fitted on races before 2025), judged on 2025-26. 2025-26 has been examined repeatedly: every lead here is a hypothesis,
first untouched evidence = races from 26 Nov 2026. No market data in any script.

| Script | Question (brief section) | Output | Result in one line |
|---|---|---|---|
| s11_interstate.py | s10 Vic->Tas and other moves (Engine v2) | out_vic_tas.csv, out_moves.csv | Vic->Tas 1.66 (1.35-2.01), 420 horses; first Tas start 1.85, repeat 1.00; Tas->Vic 0.63 |
| s11_spl.py | s7 seconds per length on Qld tracking | out_spl.csv | 0.1705 s per official length, flat by distance/going/speed; engine figures use ~0.143 |
| s11_weight.py | s8 light weights, NSW starts with allocated and carried weight | out_weight_ae.csv, out_weight_models.csv | effect in handicaps and claimed-under-54 kg; no weight description adds on 478 validation races |
| build_v22hist.py | out-of-sample v2.2 chances for history | b11/v22hist.parquet (not committed) | |
| s11_resid22.py | s5 lightly raced, s8 light weight after v2.2, s9 trainer quick backups, s10 moves under v2.2 | out_lightly_raced.csv, out_light_weight_v22.csv, out_moves_v22.csv, out_trainer_quick.csv | first starters 1.08; 1 run 0.92; light weight 1.12; trainer quick-backup split-half r 0.06 |
| s11_lightly2.py | s5 lightly raced by last-start surprise, rating level, opposition | out_lightly_raced2.csv | ordinary debut then 0.75-0.80; 1-3 runs top third + won last 1.19 (1.07-1.33) |
| s11_simplify.py | s12 joint refits with/without inputs | out_simplify.csv, simplify.log | national: last-start finish, strike rate, first-up redundant, a_rec earns; Qld proxy: track history and last-start finish hurting |
| s11_races.py | s3 three races traced | (printed; in the doc) | Cairns 22 Nov R3, Cranbourne 21 Nov R5, Morphettville 21 Nov R7 |
| s11_common.py | helpers (actual/expected with horse-clustered bootstrap) | | |

Integrity checks (no script file; commands in the session):
- Market audit: no price/odds columns in the 29 DB tables or the frames; prices/ read only by export (display) and settle_yesterday (paper returns).
- Weight definition: Breednet weight = weight carried after claim (99.8% of 19,010 NSW form-line matches); RQ starter weight = allocated;
  TAB racecard weight = allocated with claim separate. Replay of 25 Nov Geelong + Wyong under v2.2, allocated vs carried: 1 of 15 top picks changes.
- Individual data proof (s2): TAB form records for GOODNESS (5/5 starts held) and ELEGANT VENUS (7 of 11 held in the final database).
