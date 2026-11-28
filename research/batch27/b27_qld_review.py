"""Batch 27 P2: Queensland - production v2.1.3 vs the common national framework; where any difference comes from (research only).
Queensland engine structure exactly as production (Qld v1 inputs incl. sectionals, race shape, barrier x style, track/distance/going
group + v2.1.3 terms incl. Age & sex) scored on Queensland races; windows A (fit before 2024, judge 2024) and B (fit before 2025, judge
2025-26), all refitted inside each window so frozen-coefficient advantages do not count. Paired per-race log-likelihood, race bootstrap.
 R1 rating mechanism: the same Qld structure on four national rating frames - v3 (production: learning speed), v2 (no learning speed),
    v2.3 (weight credit), consolidated (cap + experience responsiveness + completeness + certainty-weighted reference)
 R2 learning speed after Age & sex: v3 vs v2 with and without the Age & sex family
 R3 Qld-specific inputs: leave-one-family-out (sectionals; race shape + barrier; track/distance/going group; horse records; Age & sex)
 R4 common framework (research harness Q26 = config 2 on v2.3 ratings; QK27 = on consolidated ratings) vs the Qld structure, same races
Output batch27/out_b27_qld_review.json"""
import json, numpy as np, pandas as pd, os, sys, gc
os.chdir('/home/claude/racing-intelligence/research'); sys.path.insert(0, '.')
src = open('engine/v2.py').read().split('def run(')[0].replace("U = pd.read_parquet('engine/frames/national.parquet')", "U = None"); exec(src)
rng = np.random.default_rng(271)
M = json.load(open('benchmarks/engine_v2_1_3/manifest.json')); Q3 = M['families']['QLD']; NEW = list(Q3['coef_per_term_sd_dev_fit']); TAU = Q3.get('penalty_tau', 100)
COLS = list(E.QCOEF)
SEC = ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec']
SHAPE = ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone']
TGRP = ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing']
REC = ['c_rec', 'g_rec', 'd_rec']; AGE = ['age_n', 'young', 'old', 'female']
WIN = {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}
FRAMES = {'v3 (production)': 'engine/frames/national_v3.parquet', 'v2 (no learning speed)': 'engine/frames/national.parquet',
          'v2.3 (weight credit)': 'engine/frames/national_c2.parquet', 'consolidated': 'engine/frames/national_consolidated.parquet'}
LP = {}          # (label, window) -> per-race lp Series (index = Qld race_id)
def run(x, cols, new, lab):
    for w, (fe, lo, hi) in WIN.items():
        fm = (x.meeting_date < fe) & x.period.notna(); em = (x.meeting_date >= lo) & (x.meeting_date < hi)
        b1 = E.fit(x, cols, fm, 1e-6); off = E.eta(x, cols, b1)
        e = off + (x[['t::' + t for t in new]].values @ fitd(x, new, fm, off, TAU) if new else 0)
        LP[(lab, w)] = E.metrics(x, e, em).lp
    print(lab, {w: round(float(LP[(lab, w)].mean()), 5) for w in WIN}, flush=True)
QMAP = None
for name, f in FRAMES.items():
    U = pd.read_parquet(f); x = E.qld_frame(U)
    if name == 'v2.3 (weight credit)': QMAP = U[U.state == 'QLD'][['race_id', 'q_race_id']].dropna().drop_duplicates('race_id').set_index('race_id').q_race_id
    del U; gc.collect()
    x = E.zcols(x, COLS); x = build_terms(x, NEW)
    if name == 'v3 (production)':                                   # production exactly as it runs (frozen coefficients) for reference
        PV = json.load(open('benchmarks/candidates_b4_national_v3/manifest.json'))['coefficients_per_dev_sd']
        e0 = x[[c + '_z' for c in COLS]].values @ np.array([PV[c] for c in COLS]) + x[['t::' + t for t in NEW]].fillna(0.0).values @ np.array([Q3['coef_per_term_sd_dev_fit'][t] for t in NEW])
        for w, (fe, lo, hi) in WIN.items(): LP[('production frozen', w)] = E.metrics(x, e0, (x.meeting_date >= lo) & (x.meeting_date < hi)).lp
        run(x, COLS, NEW, 'v3 (production)')
        run(x, COLS, [t for t in NEW if t not in AGE], 'v3 without Age & sex')
        run(x, [c for c in COLS if c not in SEC], NEW, 'v3 without sectionals')
        run(x, [c for c in COLS if c not in SHAPE], NEW, 'v3 without race shape + barrier')
        run(x, [c for c in COLS if c not in SEC + SHAPE], NEW, 'v3 without sectionals, shape, barrier')
        run(x, [c for c in COLS if c not in TGRP], NEW, 'v3 without track/distance/going group')
        run(x, COLS, [t for t in NEW if t not in REC], 'v3 without horse records')
    elif name == 'v2 (no learning speed)':
        run(x, COLS, NEW, name); run(x, COLS, [t for t in NEW if t not in AGE], 'v2 without Age & sex')
    else:
        run(x, COLS, NEW, name)
    del x; gc.collect()
def paired(a, b, w):
    j = pd.concat([LP[(a, w)].rename('a'), LP[(b, w)].rename('b')], axis=1, join='inner').dropna(); d = (j.b - j.a).values
    bs = d[rng.integers(0, len(d), (1000, len(d)))].mean(1)
    return {'races': int(len(d)), 'gain': round(float(d.mean()), 5), 'ci95': [round(float(np.percentile(bs, 2.5)), 5), round(float(np.percentile(bs, 97.5)), 5)]}
# common framework research runs, mapped to Queensland race ids
for tag, lab in [('Q26', 'common framework on v2.3 ratings (config 2 research)'), ('QK27', 'common framework on consolidated ratings')]:
    fp = f'/tmp/cand/res_{tag}_R.parquet'
    if not os.path.exists(fp): continue
    r = pd.read_parquet(fp); r['qid'] = r.race_id.map(QMAP)
    for w in WIN: LP[(lab, w)] = r[(r.window == w) & r.qid.notna()].drop_duplicates('qid').set_index('qid').lp
out = {'note': 'gain = variant minus reference, mean log-likelihood of the winner per race; refitted inside each window', 'mean_lp': {f'{k[0]} | {k[1]}': round(float(v.mean()), 5) for k, v in LP.items()}}
COMP = [('production frozen', 'v3 (production)'), ('v3 (production)', 'v2 (no learning speed)'), ('v3 (production)', 'v2.3 (weight credit)'), ('v3 (production)', 'consolidated'),
        ('v3 without Age & sex', 'v2 without Age & sex'), ('v3 (production)', 'v3 without Age & sex'),
        ('v3 (production)', 'v3 without sectionals'), ('v3 (production)', 'v3 without race shape + barrier'), ('v3 (production)', 'v3 without sectionals, shape, barrier'),
        ('v3 (production)', 'v3 without track/distance/going group'), ('v3 (production)', 'v3 without horse records'),
        ('v3 (production)', 'common framework on v2.3 ratings (config 2 research)'), ('v3 (production)', 'common framework on consolidated ratings'),
        ('production frozen', 'common framework on v2.3 ratings (config 2 research)'), ('consolidated', 'common framework on consolidated ratings'),
        ('common framework on v2.3 ratings (config 2 research)', 'common framework on consolidated ratings')]
out['comparisons'] = {}
for a, b in COMP:
    if all((k, w) in LP for k in (a, b) for w in WIN):
        out['comparisons'][f'{b}  vs  {a}'] = {w: paired(a, b, w) for w in WIN}; print(b, 'vs', a, out['comparisons'][f'{b}  vs  {a}'], flush=True)
json.dump(out, open('batch27/out_b27_qld_review.json', 'w'), indent=1)
