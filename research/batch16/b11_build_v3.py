"""Batch 16 B11: v3-structure rating frame from a given national frame (same code as engine/build_frame_v3.py, paths as arguments).
Rating hooks (RATING_CAP_L / RATING_CAP_SCOPE / RATING_GOOD_X) apply when set in the environment. Usage: python3 batch16/b11_build_v3.py <in national frame> <out>"""
import sys, json, pandas as pd
from engine import lab, dyn_v3
PRM = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))['rating_settings']
U0 = pd.read_parquet(sys.argv[1])
base = U0[[c for c in U0.columns if not c.startswith(('dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'surprise', 'dyn_traj', 'j_', 't_surp', 't_n', 'jt_', 'h2h'))]].copy()
F = lab.add_rating(base.copy(), 'dyn_nat', runner=dyn_v3.run, **PRM); F = lab.add_derived(F); F = lab.add_people(F); F = lab.add_h2h(F)
F.to_parquet(sys.argv[2]); print('written', sys.argv[2], len(F))
