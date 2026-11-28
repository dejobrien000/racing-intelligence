# Engine v2.5 (national: NSW, VIC, ACT, SA, WA, TAS) - PRODUCTION from the 29 Nov 2026 morning run

Approved by Damo 28 Nov 2026 2:38pm Brisbane (Batch 28 amendment). Queensland stays on Engine v2.1.3.

What it is: the frozen consolidated rating candidate, released unchanged. candidates_national_common.json, engine_v2.json and
engine_v2_2.json are byte-identical copies of benchmarks/engine_consolidated_candidate/ (built 27 Nov through the Engine v2.3 release
chain). runner_calibration.json is new (display calibration only). manifest.json holds the release record: settings, file and history
fingerprints, the release checks on 28 Nov fields, fallback, rollback and known concerns.

Switch: ops/engine_v25_enabled (with ops/engine_c2_enabled). Serving: ops/run_daily.sh exports the same settings the consolidated shadow
uses; frames rebuild when the Engine v2.3 history is newer; any failure falls back to Engine v2.3 for the day.
Fallback scored daily: ops/run_v23_fallback_shadow.sh -> prospective/shadow/v2_3_fallback/.
Rollback: delete ops/engine_v25_enabled.
