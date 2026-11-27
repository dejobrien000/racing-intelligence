"""Batch 16 A2: verify which settings actually produced a day's saved Engine v2 predictions, by replaying them from the saved
inputs (v1 file, snapshot, history frame) under a stated configuration and comparing with the saved scores. Read-only on the
predictions; prints one JSON line per meeting. Usage (from research/): ENGINE_C2=0|1 ENGINE_QLD213=0|1 PYTHONPATH=. python3 batch16/a2_verify_settings.py 20261127"""
import sys, os, json, glob, hashlib, pandas as pd, numpy as np
from engine import score_v2 as S
D = sys.argv[1]; IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[IX.date.astype(str) == D]
for f in sorted(glob.glob(f'prospective/prerace/{D}/*/v2_pred_*_runners.csv')):
    m2 = json.load(open(f.replace('_runners.csv', '_manifest.json'))); W = pd.read_csv(f)
    ixv1 = IX[IX.file == m2['base_v1_file']].iloc[0]
    T, fam, _, _ = S.meeting_table(ixv1); T = S.new_raw(T, S.history(D, fam), fam); T, _ = S.apply(T, fam)
    a = pd.Series(T.v2_score.values, index=list(zip(T.race_no, T.saddlecloth))); b = pd.Series(W.v2_score.values, index=list(zip(W.race_no, W.saddlecloth))).reindex(a.index)
    live = {'family': S.MAN['families'][fam], 'v22_terms': S.v22.M if (S.V22 and fam != 'QLD') else None}
    print(json.dumps({'file': f, 'family': fam, 'recorded_release': m2['engine_release'], 'recorded_engine_manifest_sha256': m2['engine_manifest_sha256'],
                      'replay_config': {'ENGINE_C2': S.C2, 'ENGINE_QLD213': S.Q213, 'family_file': S.FAMILY_FILE[fam], 'v22_file': os.path.relpath(S.v22.MPATH) if fam != 'QLD' else None},
                      'family_file_sha256': hashlib.sha256(open(S.FAMILY_FILE[fam], 'rb').read()).hexdigest(),
                      'settings_fingerprint': hashlib.sha256(json.dumps(live, sort_keys=True, default=str).encode()).hexdigest(),
                      'runners': int(len(a)), 'max_abs_score_diff': float((a - b).abs().max()), 'top_picks_same': bool((T.sort_values('v2_rank').groupby('race_no').head(1).set_index('race_no').saddlecloth == W.sort_values('v2_rank').groupby('race_no').head(1).set_index('race_no').saddlecloth).all())}))
