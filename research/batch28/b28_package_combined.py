"""Batch 28 item 3: package the COMBINED NATIONAL CANDIDATE (built through the release chain in the sandbox) into
benchmarks/engine_combined_candidate/ (NOT LIVE, shadow only). Usage (from research/): python3 batch28/b28_package_combined.py /tmp/cmb/research"""
import sys, os, json, hashlib, pandas as pd
SB = sys.argv[1]; DST = 'benchmarks/engine_combined_candidate'; os.makedirs(DST, exist_ok=True)
h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
SRC = {'candidates_national_common.json': 'benchmarks/candidates_national_common/manifest.json', 'engine_v2.json': 'benchmarks/engine_v2/manifest.json', 'engine_v2_2.json': 'out_combined/engine_v2_2.json'}
chk = json.load(open(os.path.join(SB, 'out_combined/built_check.json')))
rec = {'candidate': 'Combined national candidate (NOT LIVE, shadow only)', 'built_utc': pd.Timestamp.now(tz='UTC').isoformat(timespec='seconds'),
       'components': ['Engine v2.5 consolidated rating (unchanged settings)', 'distance-specific suitability REPLACING the distance record in layers 1-2 (kernel h = 0.12 on log distance, k = 3; preregistered Batch 26-27)',
                      'handicap weight slope wt_x_hcp (third layer; preregistered Batch 12)', 'trainer debut record tr_debut_g and sire debut record sire_debut_x (third layer; genuine debutants aged 2-3 only)'],
       'built_from': 'the national release chain in a sandbox copy of the Engine v2.5 build (/tmp/cc): consolidated frame with the distance slot replaced (batch27/b27_dspec.py) -> freeze_b5_national_common.py with DREC_SOURCE=dspec -> engine/release_v2.py -> batch28/b28_build_combined.py (third layer; debut terms from batch28/b28_debut_terms.py)',
       'rating_update_settings': {'WCREDIT': '0.25', 'RATING_CAP_L': '12', 'RATING_CAP_SCOPE': 'all', 'RATING_GOOD_X': '1', 'RATING_GOOD_TAPER': '0.8,6', 'RATING_TAPER_NEFF': 'engine/frames/experience_at_run.parquet', 'RATING_REF': 'precision'},
       'approved': 'Damo 28 Nov 2026 (Batch 28 s3 and amendment): build the combined national candidate through the release chain and start the shadow once dependencies are satisfied; promotion a separate decision',
       'built_check_2025_26_vs_engine_v2_5_built': chk['combined_vs_v25_built'], 'ladder_2025_26': {k: v.get('vs_previous_step') for k, v in chk['ladder_2025_26'].items()},
       'by_state_2025_26': chk.get('combined_vs_v25_by_state'),
       'serving': {'distance': 'prerace/score_national_prerace.py when d_rec_source = dspec (serving vs offline max diff 3e-5, 28 Nov, 695 runners)',
                   'trainer_debut': 'engine/v22.py trainer_debut (parity with historical values exact on 6 sample dates)',
                   'sire_debut': "engine/v22.py sire_debut: sire from TAB's pre-race form record (as held at production scoring), else the pedigree held; parity exact on 6 sample dates",
                   'handicap': "engine/v22.py wt_x_hcp from TAB's race class field (BMnn -> Benchmark)"},
       'open_dependency': "class parity (TAB race class at scoring vs the historical class label) is checked on Monday's master refresh BEFORE any release decision; the shadow runs meanwhile",
       'caveats': ['2025-26 has been examined repeatedly in research; the built check confirms the harness rather than giving a fresh test', 'window 2024 is not a clean test of the layer-1/2 change (their dev fit includes 2024)', 'Queensland not in scope (national family only)'],
       'source_files_sha256': {f: h(os.path.join(SB, p)) for f, p in SRC.items()}}
for f, p in SRC.items():
    d = json.load(open(os.path.join(SB, p))); d['candidate_record'] = rec
    json.dump(d, open(os.path.join(DST, f), 'w'), indent=1)
c = chk['combined_vs_v25_built']
open(os.path.join(DST, 'README.md'), 'w').write(f"""# Combined national candidate (NOT LIVE - shadow only)

Engine v2.5 plus three preregistered improvements, built through the release chain:
- distance suitability replacing the distance record (layers 1-2)
- handicap weight slope (third layer)
- trainer and sire debut records for genuine debutants (third layer)

Built check, 2025-26 (dev-fit chances; races not used to fit): vs Engine v2.5 as built {c['gain']:+.4f} ({c['lo95']:+.4f} to {c['hi95']:+.4f}) per race
on {c['races']:,} races. Ladder: distance {rec['ladder_2025_26']['L1 distance replacement (14 terms)']['gain']:+.4f}, handicap slope
{rec['ladder_2025_26']['L2 + handicap weight slope']['gain']:+.4f}, debut records {rec['ladder_2025_26']['L3 + trainer and sire debut']['gain']:+.4f}.
Open dependency: class parity on Monday's master refresh before any release decision. Approved to build and shadow by Damo 28 Nov 2026.
Scored every morning by ops/run_combined_shadow.sh into prospective/shadow/combined_national/ (own index and clock), after publishing.
Never the dashboard, the ranking or the settlement. Built {rec['built_utc']}.
""")
print('packaged', DST)
