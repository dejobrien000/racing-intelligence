"""Batch 23 C6: package the consolidated candidate's release-chain files into benchmarks/engine_consolidated_candidate/ with a
candidate_record (settings, rule, fingerprints, build provenance) in each file, as the age-aware candidate was packaged.
Usage (from research/): python3 batch23/b23_package_candidate.py /tmp/cc/out"""
import sys, os, json, hashlib, pandas as pd
SRC = sys.argv[1]; DST = 'benchmarks/engine_consolidated_candidate'; os.makedirs(DST, exist_ok=True)
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
rec = {'candidate': 'Consolidated rating candidate (NOT LIVE, shadow only)', 'built_utc': pd.Timestamp.now(tz='UTC').isoformat(timespec='seconds'),
       'approved': 'Damo 27 Nov 2026 (Batch 23 s6): build through the actual release chain; independent prospective clock from 28 Nov if safe; never replaces production',
       'built_from': 'Engine v2.3 release chain (production national_runs_c2 history, weight credit 0.25 and 0.170 s/L -> engine/lab.py -> freeze_b5_national_common.py -> engine/release_v2.py -> batch10 feat10 -> venue class -> batch10/scripts/build_v22.py) in a sandbox (/tmp/cc/research) with the rule switched on',
       'rating_update_settings': {'WCREDIT': '0.25', 'RATING_CAP_L': '12', 'RATING_CAP_SCOPE': 'all', 'RATING_GOOD_TAPER': '0.8,6', 'RATING_REF': 'precision',
                                  'RATING_TAPER_NEFF': 'engine/frames/experience_at_run.parquet (batch23/b23_experience_file.py v4 from the production Engine v2.3 frame: verified TAB as-at starts where held, else observed starts, plus inferred starts for probably-incomplete careers limited by the approved cap)'},
       'rule_in_words': 'a defeat counts at most 12 lengths in the performance figure (recorded margins never changed); a run better than expected moves the rating m times as far, m = 1 + 0.8 exp(-n/6), n = the horse experience (verified, observed or capped inferred starts); the race reference each run is measured against weights runners by the certainty of their ratings; runs worse than expected move the rating as in Engine v2.3',
       'research_evidence': 'Batch 21-23 (re-used periods, not untouched): individual error 26.48 -> 24.64 kg2, rank correlation 0.344 -> 0.406, race gain +0.0116 (2024) / +0.0166 (2025-26) vs Engine v2.3; weaker in inexperienced fields',
       'source_files_sha256': {f: h(os.path.join(SRC, f)) for f in ['candidates_national_common.json', 'engine_v2.json', 'engine_v2_2.json']},
       'code_sha256': {f: h(f) for f in ['dyn_rating.py', 'dyn_rating_innov.py', 'engine/lab.py', 'batch23/b23_experience_file.py']}}
for f in ['candidates_national_common.json', 'engine_v2.json', 'engine_v2_2.json']:
    d = json.load(open(os.path.join(SRC, f))); d['candidate_record'] = rec; json.dump(d, open(os.path.join(DST, f), 'w'), indent=1)
open(os.path.join(DST, 'README.md'), 'w').write(f"""# Consolidated rating candidate (NOT LIVE - shadow only)

Engine v2.3 rebuilt in full through its own release chain with the strongest historical individual-rating configuration:
- heavy-defeat cap: a defeat counts at most 12 lengths in the performance figure (recorded margins are never changed);
- stronger experience-dependent response: a run better than expected moves the rating m = 1 + 0.8 exp(-n/6) times as far;
- n = history-completeness experience (batch23/b23_experience_file.py v4): verified TAB as-at career starts where held, else observed
  starts (Betfair runner-list dates and our history), plus inferred starts for probably-incomplete careers, limited by the approved cap
  (75th percentile of starts by age among complete-history horses: 2, 6, 13, 21, 27, 33 at 2-7yo+); observed and verified never reduced;
- certainty-weighted race reference (RATING_REF=precision), applied inside the update rule (verified 27 Nov).

All three layers are its own: candidates_national_common.json, engine_v2.json (NSW/VIC/ACT/SA/WA/TAS family), engine_v2_2.json.
Scored every morning from the 28 Nov 2026 run by `UR_VARIANT=consolidated ops/run_update_shadow.sh` into prospective/shadow/consolidated/
(own index, own prospective clock), after publishing. Never the dashboard, the ranking or the settlement. Promotion is a separate decision.
Built {rec['built_utc']}. Fingerprints in each file's candidate_record.
""")
print('packaged', DST, rec['source_files_sha256'])
