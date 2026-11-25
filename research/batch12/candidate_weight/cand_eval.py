"""Weight release candidate (Batch 12 s3): evaluate a national frame variant with the COMPLETE Engine v2.2 structure.
Modes:
  P  production: frozen v1 coefficients, Engine v2 dev-fit term coefficients, v2.2 dev-fit coefficients and venue levels from the manifests
     (= the actual production v2.2, as dev-fit; meaningful for the baseline frame B0)
  R  refit: every layer refitted on the fitting races (v1 inputs by conditional logit; v2 terms with the production penalty on top of v1;
     v2.2 terms ridge 30 on top), venue levels recomputed on the variant's own rating
  R-noW  as R but every input carrying TODAY's weight removed (a_wt_rel and its interactions, wt_change, light_weight)
Windows: A = fit before 2024, judge 2024; B = fit before 2025, judge 2025-26. Writes per-race results to /tmp/cand/res_<V>_<mode>.parquet.
Usage: cd /tmp/cand/research && PYTHONPATH=. python3 /tmp/cand/cand_eval.py <V> <frame.parquet> <feat.parquet> <modes comma>"""
import sys, json, numpy as np, pandas as pd
sys.path.insert(0, '/home/claude/racing-intelligence/research/batch10/scripts'); import lib10 as L
V, FRAME, FEAT, MODES = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(',')
src = open('engine/v2.py').read().split('def run(')[0].replace("pd.read_parquet('engine/frames/national.parquet')", f"pd.read_parquet('{FRAME}')"); g = {}; exec(src, g)
U0, E, NFAM2, build_terms, offset_v1, fitd = g['U'], g['E'], g['NFAM2'], g['build_terms'], g['offset_v1'], g['fitd']
MAN = json.load(open('benchmarks/engine_v2/manifest.json'))['families']['NSW_VIC_ACT']; M22 = json.load(open('benchmarks/engine_v2_2/manifest.json'))
C2 = json.load(open('benchmarks/candidates_national_common/manifest.json'))['candidates']['nat_v2 (+ horse records)']
allt = sum(NFAM2.values(), []); T22 = M22['terms']; TAU = json.load(open('benchmarks/engine_v2/manifest.json'))['families']['NSW_VIC_ACT'].get('penalty_tau')
x = E.nat_frame(U0); x = build_terms(x, allt); x['meeting_date'] = pd.to_datetime(x.meeting_date)
off_frozen, Tm = (offset_v1(x, 'nat'), x[['t::' + a for a in allt]].fillna(0.0).values) if 'P' in MODES else (None, None)
F = pd.read_parquet(FEAT).drop(columns=['date', 'state'], errors='ignore'); x = x.merge(F, on=['race_id', 'horse'], how='left', suffixes=('', '_f'))
# memory (8 GB workspace): keep only the columns any layer uses, floats as float32; results are compared like-for-like across variants
_keep = set(C2) | {'t::' + a for a in allt} | set(T22) | set(F.columns) | {'race_id', 'horse', 'meeting_date', 'state', 'win', 'weight_kg', 'a_wt_rel', 'class_label',
         'dyn_nat', 'dyn_nat_sd', 'n_prior', 'h_sd', 'f_avgfp3', 'finish_pos', 'field_size'}
_rows_keep = np.ones(len(x), bool)
x = x[[c for c in x.columns if c in _keep or x[c].dtype.kind not in 'f']].copy()
for _c in x.columns:
    if x[_c].dtype == 'float64': x[_c] = x[_c].astype('float32')
del F; import gc; gc.collect()
# v2.2 raw terms (same definitions as build_v22.py), venue level from the variant's own rating (dev period) or the manifest (mode P)
Uv = U0[['race_id', 'horse', 'date', 'venue', 'f_avgfp3', 'weight_kg', 'dyn_nat_sd', 'dyn_nat']].copy(); Uv['date'] = pd.to_datetime(Uv.date)
del U0, g; gc.collect()
fm_ = Uv.groupby('race_id').dyn_nat.transform('mean'); VLown = fm_[Uv.date < '2025-01-01'].groupby(Uv.venue[Uv.date < '2025-01-01']).mean()
VLman = pd.Series(M22['venue_level_kg']); alias = M22['venue_alias']
def v22raw(x, VL):
    u = Uv.sort_values(['horse', 'date']).copy(); va = u.venue.map(lambda v: alias.get(v, v)); u['vl'] = va.map(VL); u['venue_step'] = u.vl - u.groupby('horse').vl.shift()
    y = x.drop(columns=[c for c in ['venue_step', 'weight_kg_v', 'dyn_nat_sd_v'] if c in x]).merge(u[['race_id', 'horse', 'venue_step']], on=['race_id', 'horse'], how='left')
    y['hsd_x_rel'] = y.h_sd * (y.dyn_nat - y.groupby('race_id').dyn_nat.transform('mean')); y['recentform_x_established'] = y.f_avgfp3 * (y.n_prior >= 15)
    y['light_weight'] = (y.weight_kg <= 54).astype(float).where(y.weight_kg.notna()); y['log_runs_held'] = np.log1p(y.n_prior); y['rating_uncertainty'] = y.dyn_nat_sd
    hcp_ = y.class_label.isin(['Benchmark', 'BM', 'Open/Hcp']).astype(float); y['wt_x_hcp'] = y.a_wt_rel * hcp_
    y['wt_x_nonmaiden'] = y.a_wt_rel * (y.class_label != 'Maiden').astype(float)
    return y
import os; EXTRA = [t for t in os.environ.get('EXTRA', '').split(',') if t]; TAG = ('+' + '+'.join(EXTRA)) if EXTRA else ''
WT = ['a_wt_rel']; WTT = [a for a in allt if 'a_wt_rel' in a or 'wt_change' in a]; WT22 = ['light_weight']
out = []
for mode in MODES:
    y = v22raw(x, VLman if mode == 'P' else VLown)
    for win, (fe, lo, hi) in {'A': ('2024-01-01', '2024-01-01', '2025-01-01'), 'B': ('2025-01-01', '2025-01-01', '2027-01-01')}.items():
        fm = pd.Series((y.meeting_date < fe).values, index=y.index); em = pd.Series(((y.meeting_date >= lo) & (y.meeting_date < hi)).values, index=y.index)
        if mode == 'P':
            e = off_frozen + Tm @ np.array([MAN['coef_per_term_sd_dev_fit'][t] for t in allt])
            z = np.column_stack([((pd.to_numeric(y[c], errors='coerce') - pd.to_numeric(y[c], errors='coerce').groupby(y.race_id).transform('mean')).fillna(0.0) / M22['term_sd_dev_fit'][c]).values for c in T22])
            e = e + z @ np.array([M22['coef_per_sd_dev_fit'][c] for c in T22])
        else:
            c1 = [c for c in C2 if not (mode == 'R-noW' and c in WT)]; tt = [t for t in allt if not (mode == 'R-noW' and t in WTT)]; t22 = [t for t in T22 if not (mode == 'R-noW' and t in WT22)] + EXTRA
            z = L.prep_z(y.copy(), c1, fm); b1 = L.clogit_fit(z, c1, fm, np.zeros(len(z)), ridge=1e-3); off = z[[c + '_z' for c in c1]].values @ b1; [print('v1coef', V + TAG, mode, win, c, round(float(b1[i]), 4), 'sd', round(float(z[c].std()), 3), 'per unit', round(float(b1[i] / z[c].std()), 4), flush=True) for i, c in enumerate(c1) if c in ('dyn_nat', 'a_wt_rel', 'wt_change') or 'wt' in c]
            b2 = fitd(y, tt, fm, off, TAU if TAU else 100); e = off + y[['t::' + t for t in tt]].fillna(0.0).values @ b2
            z2 = L.prep_z(y.copy(), t22, fm); b3 = L.clogit_fit(z2, t22, fm, e, ridge=30.0); [print('coef', V + TAG, mode, win, t, round(float(b3[t22.index(t)]), 4), 'per sd', round(float(z2[t].std()), 3) if t in z2 else '', flush=True) for t in EXTRA + ['a_wt_rel', 'light_weight'] + [u for u in t22 if 'wt' in u] if t in t22]; e = e + z2[[c + '_z' for c in t22]].values @ b3
        if mode != 'P' and win == 'B':   # freeze the fitted candidate (fit before 2025, same convention as the production dev-fit manifests)
            _sd = lambda cols: {c: float(((pd.to_numeric(y[c], errors='coerce') - pd.to_numeric(y[c], errors='coerce').groupby(y.race_id).transform('mean')).fillna(0.0))[fm].std() or 1.0) for c in cols}
            json.dump({'variant': V + TAG, 'mode': mode, 'fit': 'races before 2025-01-01', 'v1_inputs': c1, 'v1_coef_per_sd': dict(zip(c1, map(float, b1))), 'v1_sd': _sd(c1),
                       'v2_terms': tt, 'v2_coef': dict(zip(tt, map(float, b2))), 'v2_penalty_tau': TAU if TAU else 100, 'v22_terms': t22, 'v22_coef_per_sd': dict(zip(t22, map(float, b3))),
                       'v22_sd': _sd(t22), 'venue_level_kg': {k: float(v) for k, v in VLown.items()}, 'weight_credit': os.environ.get('WCREDIT_NOTE'), 'spl': os.environ.get('SPL_NOTE')},
                      open(f'/tmp/cand/coef_{V}{TAG}_{mode}.json', 'w'), indent=1)
        y['e'] = e; r = L.race_lp(y, e, em); r['window'] = win; r['mode'] = mode; r['variant'] = V + TAG; out.append(r.reset_index())
        mx = y.loc[em].groupby('race_id').e.transform('max'); p = np.exp(y.loc[em].e - mx); p = p / p.groupby(y.loc[em, 'race_id']).transform('sum')
        y.loc[em, 'p_' + win] = p.values
        print(V + TAG, mode, win, 'races', len(r), 'mean lp', round(r.lp.mean(), 5), 'top pick %', round(100 * r.hit.mean(), 2), flush=True)
    y[['race_id', 'horse', 'meeting_date', 'state', 'win', 'weight_kg', 'a_wt_rel', 'class_label', 'dyn_nat', 'p_B']].to_parquet(f'/tmp/cand/runners_{V}{TAG}_{mode}.parquet')
pd.concat(out).to_parquet(f'/tmp/cand/res_{V}{TAG}_{"_".join(MODES)}.parquet')
