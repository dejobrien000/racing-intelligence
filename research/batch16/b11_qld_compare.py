"""Batch 16 B11: Queensland configurations compared on identical races (meeting bootstrap, engine/evaltools.diff).
Config 1 = v2.1.3 structure (v2.1.1 + age & sex) on the current v3 rating; 2 = common national framework on the current rating;
3 = v2.1.3 structure on the v3 rating with the update rule; 4 = common framework + update rule; 5 = state-standardised margins
(v2.1.3 structure and common framework). All refitted on the same harness (fit < 2024 judge 2024 = A; fit < 2025 judge 2025-26 = B)."""
import json, pandas as pd
from engine import evaltools as E
R = lambda tag, v, w: pd.read_parquet(f'/tmp/qcfg/res_{tag}_{v}_{w}.parquet')
CFG = {'1 v2.1.3 (current rating)': ('v3', '3'), '2 common framework (current rating)': ('v3', '7'), '3 v2.1.3 + update rule': ('v3U', '3'),
       '4 common framework + update rule': ('v3U', '7'), '5a v2.1.3 + standardised margins': ('v3S', '3'), '5b common framework + standardised margins': ('v3S', '7'),
       '0 v2.1.1 (previous production structure)': ('v3', '1')}
OUT = {}
for w in ['A', 'B']:
    base = R('v3', '3', w)
    for name, (t, v) in CFG.items():
        r = R(t, v, w); OUT[f'{w} | {name}'] = {**{k: (float(x) if hasattr(x, 'item') else x) for k, x in E.summary(r).items()}, **({'vs_config_1': E.diff(base, r)} if name[0] != '1' else {})}
    OUT[f'{w} | 4 vs 2 (update rule on top of the common framework)'] = E.diff(R('v3', '7', w), R('v3U', '7', w))
json.dump(OUT, open('batch16/out_b11_qld_configs.json', 'w'), indent=1, default=float)
for k, v in OUT.items():
    d = v.get('vs_config_1', v if 'lp' in v and 'fit_%' not in v else None)
    print(k, '| fit', v.get('fit_%'), 'top', v.get('top_pick_%'), '| vs 1:' if d else '', (d['lp'], d['lp_lo'], d['lp_hi'], 'tp', d['hit']) if d else '')
