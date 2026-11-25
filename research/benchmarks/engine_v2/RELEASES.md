# Engine v2 releases

## v2.0.1 - 25 Nov 2026, 11:11am Brisbane (scorer fix; no coefficient changes)
- Fault: the Queensland pre-race scorer (prerace/score_prerace.py) never attached the national dynamic rating to history rows,
  so its development spread was blank and every live value was set to 0. Live Queensland ratings from 24 Nov to 25 Nov 11:11am
  therefore gave the strongest Queensland feature (dyn_nat, 0.347 per dev sd) zero weight. Research results were unaffected.
- Fix: history rows keep their Queensland ids; a guard now stops the scorer if the rebuilt spread differs from the frozen
  value (2.9392 kg) by more than 2%. Rebuilt spread after the fix: 2.9392.
- Evidence: dropping the national rating costs 0.025 log-likelihood per race on 2025-26 (95% 0.018 to 0.033), about one
  top-pick point (engine/out/ablation_qld.csv). The fix restores the validated model; it adds nothing new.
- Applied: Ipswich 25 Nov re-issued on the same 7:51am fields (top pick changed in 5 of 7 races); the 7:56am set is kept.
  Approved by Damo in chat, 25 Nov ~11:10am, to replace from now on.

## v2.0 - 24 Nov 2026 (benchmarks/engine_v2/manifest.json)
