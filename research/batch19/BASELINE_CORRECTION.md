# Research harness baseline correction (identified 27 Nov 2026, Batch 18; recorded Batch 19 G24)

Earlier reports are left as written. This note is the record of what was wrong and the corrected values. Numbers in
`out_b19_baseline_correction.json` (gain = mean per-race log-likelihood difference, race bootstrap 95%; A = judge 2024, B = judge 2025-26).

## Definitions
- **Original baseline** (Batches 16-18 harness tables): `res_C2_R`, the Engine v2.3 frame as released (`/tmp/cand/frames/C2_national.parquet`).
  Its history file uses the Engine v2.3 weight credit (0.25 kg per kg) in both the rating and the weight-adjusted speed figures.
- **Corrected baseline**: `res_OFF_R`, Engine v2.3 rebuilt by the same sandbox path as every variant (`/tmp/cand/research`, `build_hook.py`,
  `WCREDIT=0.25`, every hook off). It differs from the original only in the speed-figure columns below.

## Cause (speed-figure table difference)
The sandbox history file `/tmp/cand/research/national_runs.parquet` (built 25 Nov 21:29) carried the Engine v2.2 weight credit
(1.0 kg per kg) in the weight-adjusted speed figures: `fig_w`, `fig_n` and the form-figure inputs built from them (`a_rec`, `a_best3`,
`fs`, `a_fs3`, `prev_fig`). Pars, track variants, raw speeds, margins and weights are identical to production. The rating itself
(`dyn_nat`) used 0.25 in both (environment `WCREDIT`), so ratings are identical (max difference 0.0). Every sandbox variant therefore
combined Engine v2.3 ratings with Engine v2.2-credit form figures, while the original baseline used v2.3 for both.
Size of the mismatch: corrected vs original baseline -0.0009 (-0.0016 to -0.0002) in 2024, -0.0002 (-0.0008 to +0.0003) in 2025-26.

## Affected comparisons (sandbox variants vs the original baseline)
All rows of `out_b19_baseline_correction.json` "affected": U1 (cap only), U4, U5 (update rule), U6, U7, U1B, U5B, U5PW, U5E, U5EA, U5EC,
RF, RO, PW, STD, STD2, LN, LN2, LNSA. Every one was understated by about the size of the mismatch. Materially relevant corrections:
- **PW (race level weighted by rating certainty):** +0.0006 (n.s.) / +0.0011 becomes +0.0014 / +0.0014 (+0.0011 to +0.0017): now clear in
  both periods. It is a candidate refinement, not a released or shadowed mechanism.
- **STD (state-standardised margins):** -0.0012 / -0.0006 becomes -0.0003 / -0.0004 (-0.0005 to -0.0003): still worse; rejection stands.
- **RF (Batch 17 race-reference-only cap):** -0.0006 / -0.0034 becomes +0.0003 / -0.0032: conclusion unchanged.
- **Lane candidates:** small losses become small gains (Batch 18 report already corrected).

## Not affected
Variants built on the released frame (C2+wt_x_hcp, C2S+suit, C2X+xstate, C2J, C2D, C2-bm_change, C2~..., C2T+tr_debut); the release-chain
built checks in `/tmp/u5` and `/tmp/c2` (history file identical to production, speed figures max difference 0.0); every live shadow
(built each morning from production files).

## Release decisions
None affected. Engine v2.3 was released on its own built evaluation; the update-rule and cap-only shadows were approved on the
release-chain built check (+0.0059 / +0.0043), which used production-identical history. Engine v2.4 (handicap weight slope) is a C2-frame
variant. No production setting was ever taken from a sandbox comparison.

## Rule from now on
A variant is compared only with a baseline built by the same path from the same history file, race population and settings, unless the
difference is itself the experiment. The harness sandbox history file is checked against production (`fig_n`, `fig_w`, ratings) before a
batch of comparisons; release-chain builds record the parity check in their log (Batch 19: `/tmp/ua/parity.log`).
