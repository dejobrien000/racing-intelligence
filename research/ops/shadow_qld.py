"""SHADOW scoring (NOT LIVE): Queensland Engine v2.1.2-candidate, approved for shadow scoring by Damo 25 Nov 2026.
Reads the shadow v1 files written by `SHADOW_QLD_CANDIDATES=... prerace/score_prerace.py` (prospective/shadow/qld_v2_1_2/INDEX.csv),
applies the candidate's Engine v2 terms with the same code as production (engine/score_v2.py, manifest swapped), and writes
write-once v2 files beside them. Nothing here is read by the dashboard, the ranking, the settlement or any rating script.
Usage (from research/): SNAPDIR=collect/national/<D>/bundles PYTHONPATH=. python3 ops/shadow_qld.py <YYYYMMDD>"""
import sys, os, json, hashlib, pandas as pd
sys.path.insert(0, '.')
import engine.score_v2 as S
D = sys.argv[1]; ROOT = 'prospective/shadow/qld_v2_1_2'; IDX = os.path.join(ROOT, 'INDEX.csv'); MANP = 'benchmarks/candidate_qld_v2_1_2/engine_manifest.json'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
S.MAN = json.load(open(MANP)); S.V22 = False                      # candidate's Queensland family coefficients; v2.2 terms never apply to Qld
stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%SZ')
IX = pd.read_csv(IDX); IX = IX[(IX.date.astype(str) == D) & IX.file.str.endswith('_runners.csv') & ~IX.file.str.contains('/v2_')]
if IX.empty: sys.exit(f'shadow: no shadow v1 files for {D}')
for _, ix in IX.sort_values('scored_utc').groupby('track').tail(1).iterrows():
    W, fam, cond, mf = S.meeting_table(ix); assert fam == 'QLD'
    T = S.new_raw(W, S.history(D, fam), fam); T, contrib = S.apply(T, fam)
    base = os.path.join(os.path.dirname(ix.file), f"v2_{os.path.basename(ix.file).replace('_runners.csv', '')}_{stamp}")
    out = T[['race_id', 'race_no', 'saddlecloth', 'horse_name', 'v2_rank', 'v2_chance_pct', 'v2_score', 'final_rating_kg_eq', 'v1_score', 'rank', 'chance_pct']].rename(
        columns={'rank': 'v1_rank', 'chance_pct': 'v1_chance_pct', 'horse_name': 'horse'}).sort_values(['race_no', 'v2_rank'])
    out.insert(0, 'candidate', 'qld_v2_1_2_shadow')
    paths = {'runners': base + '_runners.csv', 'manifest': base + '_manifest.json'}
    with open(paths['runners'], 'x') as fh: out.to_csv(fh, index=False)
    m2 = {'scored_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'engine_release': 'Engine v2.1.2-candidate (Queensland) - SHADOW, NOT LIVE', 'family': fam,
          'base_v1_file': ix.file, 'base_v1_sha256': sha(ix.file), 'snapshot_key': ix.snapshot_key, 'engine_manifest': MANP, 'engine_manifest_sha256': sha(MANP),
          'production_engine': 'Engine v2.1.1 (prospective/prerace)', 'notes': ['no result of these races existed when this file was written', 'shadow only: not on the dashboard, not settled, not ranked']}
    with open(paths['manifest'], 'x') as fh: json.dump(m2, fh, indent=1)
    with open(IDX, 'a') as fh:
        for kind, pth in paths.items(): fh.write(f"{m2['scored_utc']},{D},{ix.track},{ix.snapshot_key},{pth},{sha(pth)}\n")
    print('shadow written', base, '| races', out.race_no.nunique())
