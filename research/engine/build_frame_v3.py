"""Builds engine/frames/national_v3.parquet (Engine v2.1 Queensland history frame) from engine/frames/national.parquet:
the v3 rating replaces dyn_nat and every rating-derived feature is rebuilt from it. About 5 minutes."""
import json, pandas as pd
from engine import lab, dyn_v3
PRM = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))['rating_settings']
U0 = pd.read_parquet('engine/frames/national.parquet')
base = U0[[c for c in U0.columns if not c.startswith(('dyn_nat', 'c_rec', 'g_rec', 'd_rec', 'surprise', 'dyn_traj', 'j_', 't_surp', 't_n', 'jt_', 'h2h'))]].copy()
F = lab.add_rating(base.copy(), 'dyn_nat', runner=dyn_v3.run, **PRM); F = lab.add_derived(F); F = lab.add_people(F); F = lab.add_h2h(F)
F.to_parquet('engine/frames/national_v3.parquet'); print('written engine/frames/national_v3.parquet', len(F))
