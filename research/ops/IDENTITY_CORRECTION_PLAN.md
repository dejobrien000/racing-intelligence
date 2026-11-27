# Horse identity correction: Monday 30 Nov 2026 plan (approved by Damo 27 Nov, Batches 21-22; subject to checks)

Nothing here is live until every check below passes and the release note is written. Rollback = delete the switch file.

## What changes
- Rating history key for 56 names only: 51 different-country names and 5 same-suffix names with a different sire and dam are split
  into separate horses (research/batch21/identity_correction_monday.csv, column proposed_rating_key). Every other horse keeps its key.
- 20 names kept as one horse (dam or sire spelt two ways); 3 kept together but flagged "identity uncertain" (Awol, Airclash,
  Infinite Rose): live fallback applies to them.
- BEREZKA 7 Nov 2026 Eagle Farm R5 record (RQ "Disqualified", no weight, placeholder finish; she ran R9) excluded from the rating
  history; the source row stays in the master database.
- Live identity rule (research/batch22/b22_identity_replay.py, resolve()): name + sire + dam (normalised), one match only, foaling
  season within one of TAB's age; otherwise no history / "history missing" / "identity uncertain" (scored with no usable history,
  labelled). Trainer, owner, partnership, state, gelding and source naming never form part of identity.

## Switch and versioning
- Switch: research/ops/identity_correction_enabled (absent = current behaviour). Rollback = delete it; the next run rebuilds frames.
- History release label recorded beside the existing national_runs_sha256 in every forecast manifest ("identity-corrected
  2026-11-30" vs previous). Previous history file and frames kept as *_pre_identity.parquet.
- Frozen candidates keep their coefficients; no new prospective clocks. Each comparison adds a sensitivity check without races that
  include a corrected horse; a separate clock starts only if that check disagrees (original comparison kept).

## Checks before the switch goes on (all must pass)
1. Replay tests (batch22/b22_identity_replay.py) on the final code: 7,254/7,255 or better; the only allowed miss is a malformed
   source pedigree that falls back.
2. Rebuild national_runs_c2 and the Engine v2.3 frame with the switch on in a sandbox: unaffected horses' ratings within 0.1 kg for
   97%+ of Sep-Nov 2026 runs (27 Nov sandbox: 97.3%); split horses' runs all present (no run lost: row count = before + 0 - 1 BEREZKA).
3. Replay Saturday's and Monday's national scoring with the switch on and off: identical for every runner whose name is not on the
   list; differences listed for any that is.
4. Shadow paths (update-rule, cap-only, age-aware, trainer debut, v2.4, Qld configs) run end to end with the switch on.
5. Dashboard export and settlement run on the corrected day files.

## Order on Monday
weekly master update (GitHub job) -> verify fingerprints -> sandbox rebuild with the switch -> checks 1-5 -> release note in
benchmarks/engine_v2/RELEASES.md with UTC time ("effective from the 1 Dec 2026 7:30am run") -> create the switch -> commit, push.
If any check fails: leave the switch off, keep the current history, report the blocker.
