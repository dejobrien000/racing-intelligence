# Engine v2.3 feature notes (sidecar; the settings files themselves are unchanged so their fingerprints stay valid)

## Training-only control: `bm_change` (class change since the last start)

Agreed by Damo 27 Nov 2026 (Batch 17 brief s4): keep `bm_change` as a documented training-only control.

- **Definition (training, engine/lab.py):** today's race benchmark number minus the benchmark number of the horse's previous race, both
  from the race conditions (Breednet). Both are known when the field is published: no result or later information is used.
- **Serving (engine/score_v2.py):** computed from the snapshot's `benchmark` field, which TAB's field format leaves empty, so it is
  missing for every live runner; after race-centring it contributes exactly zero. This is intended.
- **Evidence (Batch 16 B8, research/batch16/out_engine_tests.json, `B8_class_change_input_bm_change`):** fitted with it and served
  with it present would cost 0.0012 (2024) / 0.0007 (2025-26) log-likelihood per race; retraining without it costs 0.0008 / 0.0005
  against today's arrangement (both intervals clear of zero). Read: in training it absorbs class moves that would otherwise bleed into
  other inputs' weights; as a live input it does not help.
- **Do not start serving it** now that TAB's class field is collected (race_class): the tests say serving it makes chances worse.
- **No other unserved input** is kept this way (Batch 16 audit: bm_change was the only input never served). Any other unserved input
  needs its own equivalent test before it can be kept.
