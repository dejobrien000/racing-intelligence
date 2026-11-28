"""Batch 28 item 2: package the Queensland common framework on the consolidated rating (config 5) into
benchmarks/engine_qld_common_cons_candidate/ (NOT LIVE, shadow only), as configs 2 and 4 were packaged.
Usage (from research/): python3 batch28/b28_package_qld5.py /tmp/q5/research"""
import sys, os, json, hashlib, pandas as pd
SB = sys.argv[1]; DST = 'benchmarks/engine_qld_common_cons_candidate'; os.makedirs(DST, exist_ok=True)
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
SRC = {'candidates_national_common.json': 'benchmarks/candidates_national_common/manifest.json', 'engine_v2.json': 'benchmarks/engine_v2/manifest.json', 'engine_v2_2.json': 'benchmarks/engine_v2_2/manifest.json'}
chk = json.load(open('batch28/out_b28_qld_built_check.json'))
rec = {'candidate': 'Queensland common national framework on the consolidated rating, configuration 5 (NOT LIVE, shadow only)', 'built_utc': pd.Timestamp.now(tz='UTC').isoformat(timespec='seconds'),
       'built_from': 'the national release chain (freeze_b5_national_common.py -> engine/release_v2.py -> b10/scripts/build_v22.py) in a sandbox copy of the consolidated build (/tmp/cc), refitted on Queensland races only (QCF=1); the NSW_VIC_ACT family structure carries Queensland coefficients',
       'rating': 'consolidated rating (= Engine v2.5 national rating): 12 L cap, 1 + 0.8 exp(-n/6) good-run response with history-completeness experience, certainty-weighted reference; weight credit 0.25',
       'rating_update_settings': {'WCREDIT': '0.25', 'RATING_CAP_L': '12', 'RATING_CAP_SCOPE': 'all', 'RATING_GOOD_X': '1', 'RATING_GOOD_TAPER': '0.8,6', 'RATING_TAPER_NEFF': 'engine/frames/experience_at_run.parquet', 'RATING_REF': 'precision'},
       'approved': 'Damo 28 Nov 2026 (Batch 28 s2): build the Queensland common framework on the consolidated foundation; start independent prospective assessment once ready; promotion a separate decision',
       'built_check_2025_26': {k: v for k, v in chk.items() if k != 'mean lp'},
       'barrier': 'rail-free pooled barrier NOT included in this build (the release chain has no barrier term yet); planned as a separate variant',
       'qld_physical_inputs': 'not used (Batch 26: no established gain); Queensland tracking stays in the data', 'training_only_inputs': {'bm_change': 'training-only control, served missing (as config 2)'},
       'source_files_sha256': {f: h(os.path.join(SB, p)) for f, p in SRC.items()}}
for f, p in SRC.items():
    d = json.load(open(os.path.join(SB, p))); d['candidate_record'] = rec
    if f == 'engine_v2.json': d['scope_note'] = 'NSW_VIC_ACT family holds QUEENSLAND coefficients (QCF build); scored only on Queensland meetings restated in the national format (ops/qld_common_adapter.py)'
    json.dump(d, open(os.path.join(DST, f), 'w'), indent=1)
open(os.path.join(DST, 'README.md'), 'w').write(f"""# Queensland common framework on the consolidated rating - configuration 5 (NOT LIVE - shadow only)

The national engine's three-layer structure with Queensland's own coefficients (fitted on Queensland races only), on the consolidated
rating that Engine v2.5 uses nationally. Approved to build and shadow by Damo 28 Nov 2026 (Batch 28 s2). Production promotion is a separate decision.
Built check, 2025-26 (dev-fit chances, races not used to fit): vs Queensland production v2.1.3 +0.040 (+0.029 to +0.052) per race on 4,730
races; vs config 2 rebuilt the same way +0.011 (+0.007 to +0.016) on 6,804 races. Barrier: not in this build (separate variant to follow).
Scored every morning by ops/run_qld_common_shadow.sh (config 5) into prospective/shadow/qld_common_cons/ (own index and clock), after
publishing, on the consolidated frame and the same rating settings as Engine v2.5. Never the dashboard, the ranking or the settlement.
Built {rec['built_utc']}.
""")
print('packaged', DST)
