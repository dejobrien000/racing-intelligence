"""Batch 10 harness. Engine v2 score held fixed as an offset; candidate terms fitted on top.
Protocol for NEW hypotheses (Batch 10): discovery = fit Oct 2022-Dec 2023, judge on 2024 (inside the old development period);
validation = fit on everything before 2025, judge on 2025-26 (only for terms that pass discovery). Region split: EAST = NSW/VIC/ACT
(the data Engine v2 was built on), WEST = SA/WA/TAS (added 25 Nov 2026, never used to build or screen anything) = transfer check.
All features are pre-race (computed from earlier runs only). No market data anywhere."""
import os, json, numpy as np, pandas as pd
HERE = os.getcwd(); CACHE = 'b10/out'
def load_U():
    return pd.read_parquet('engine/frames/national.parquet')
def base(kind='nat', rebuild=False):
    f = f'{CACHE}/base_{kind}.parquet'
    if os.path.exists(f) and not rebuild: return pd.read_parquet(f)
    src = open('engine/v2.py').read().split('def run(')[0]; g = {}; exec(src, g)
    U, E, NFAM2, QFAM2, build_terms, offset_v1 = g['U'], g['E'], g['NFAM2'], g['QFAM2'], g['build_terms'], g['offset_v1']
    MAN = json.load(open('benchmarks/engine_v2/manifest.json'))
    if kind == 'nat':
        x = E.nat_frame(U); allt = sum(NFAM2.values(), []); fam = 'NSW_VIC_ACT'; o = 'nat'
    else:
        QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
        x = E.qld_frame(U); allt = sum(QREL.values(), []); fam = 'QLD'; o = 'qld'
    x = build_terms(x, allt); off = offset_v1(x, o)
    bd = np.array([MAN['families'][fam]['coef_per_term_sd_dev_fit'][t] for t in allt]); x['v2'] = off + x[['t::' + a for a in allt]].values @ bd
    keep = [c for c in ['race_id', 'horse', 'horse_id', 'date', 'meeting_date', 'state', 'venue', 'tier', 'meeting_id', 'period', 'win', 'fpos', 'field', 'v2', 'dyn_nat', 'trainer', 'jockey', 'tkey', 'jkey', 'distance_m'] if c in x]
    b = x[keep].copy(); b['meeting_date'] = pd.to_datetime(b.meeting_date); b.to_parquet(f); return b
def prep_z(x, cols, fit_mask):
    """race-centre each column, scale by its SD on the fitting rows; missing -> 0 after centring (= no information, not poor form)."""
    for c in cols:
        v = pd.to_numeric(x[c], errors='coerce'); m = v.groupby(x.race_id).transform('mean'); t = (v - m).fillna(0.0)
        sd = t[fit_mask].std() or 1.0; x[c + '_z'] = t / sd
    return x
def clogit_fit(x, cols, mask, offset, ridge=1e-4, iters=50):
    """conditional logit (one winner per race), Newton steps, coefficients per SD."""
    d = x[mask]; X = d[[c + '_z' for c in cols]].values; o = offset[mask.values]; w = d.win.values; r = pd.factorize(d.race_id.values)[0]
    b = np.zeros(X.shape[1])
    for _ in range(iters):
        e = o + X @ b; e = e - pd.Series(e).groupby(r).transform('max').values; p = np.exp(e); p = p / np.bincount(r, p)[r]
        g = X.T @ (w - p) - ridge * b
        xm = np.vstack([np.bincount(r, p * X[:, j]) for j in range(X.shape[1])]).T[r]; Xc = X - xm
        Hm = (Xc * p[:, None]).T @ Xc + ridge * np.eye(X.shape[1]); step = np.linalg.solve(Hm, g); b = b + step
        if np.abs(step).max() < 1e-7: break
    return b
def race_lp(x, e, mask):
    t = x.loc[mask, ['race_id', 'meeting_id', 'meeting_date', 'win', 'state']].copy(); t['e'] = e[mask.values]
    mx = t.groupby('race_id').e.transform('max'); t['lp'] = t.e - (np.log(np.exp(t.e - mx).groupby(t.race_id).transform('sum')) + mx)
    t['rk'] = t.groupby('race_id').e.rank(ascending=False, method='first'); w = t[t.win == 1].set_index('race_id')
    return pd.DataFrame({'meeting_id': w.meeting_id, 'date': w.meeting_date, 'state': w.state, 'lp': w.lp, 'hit': (w.rk == 1).astype(float)})
def boot(d, meets, reps=400, seed=10):
    rng = np.random.default_rng(seed); um, inv = np.unique(meets, return_inverse=True); s = np.bincount(inv, d); n = np.bincount(inv)
    bs = np.array([s[k].sum() / n[k].sum() for k in (rng.integers(0, len(um), len(um)) for _ in range(reps))])
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)), float(2 * min((bs <= 0).mean(), (bs >= 0).mean()))
WEST = {'SA', 'WA', 'TAS'}
def test(x, cols, label, stage='discovery', ridge=1e-4):
    """stage discovery: fit 2022-10..2023-12, judge 2024. validation: fit < 2025, judge 2025-26. Gains = log-likelihood per race vs Engine v2."""
    yr = x.meeting_date.dt.year
    fitm, evm = ((yr <= 2023), (yr == 2024)) if stage == 'discovery' else ((yr <= 2024), (yr >= 2025))
    fitm, evm = pd.Series(fitm.values, index=x.index), pd.Series(evm.values, index=x.index)
    x = prep_z(x.copy(), cols, fitm); off = x.v2.values
    b = clogit_fit(x, cols, fitm, off, ridge); e = off + x[[c + '_z' for c in cols]].values @ b
    a0, a1 = race_lp(x, off, evm), race_lp(x, e, evm); d = (a1.lp - a0.lp); h = (a1.hit - a0.hit) * 100
    out = {'label': label, 'stage': stage, 'terms': '+'.join(cols), 'coef_per_sd': ';'.join(f'{v:.4f}' for v in b), 'races': len(d), 'gain': round(d.mean(), 5)}
    lo, hi, p = boot(d.values, a1.meeting_id.values); out.update(lo95=round(lo, 5), hi95=round(hi, 5), p=round(p, 4), top_pick_pts=round(h.mean(), 2))
    for reg, sel in [('east', ~a1.state.isin(WEST)), ('west', a1.state.isin(WEST))]:
        if sel.sum() > 50:
            lo, hi, _ = boot(d[sel].values, a1.meeting_id[sel].values); out[f'gain_{reg}'] = round(d[sel].mean(), 5); out[f'{reg}_lo'] = round(lo, 5); out[f'{reg}_hi'] = round(hi, 5)
    cov = x.loc[evm, cols[0]].notna().mean(); out['coverage_%'] = round(100 * cov, 1)
    return out
def bh(p, q=0.10):
    p = np.asarray(p); o = np.argsort(p); n = len(p); thr = q * (np.arange(1, n + 1)) / n; ok = p[o] <= thr
    k = np.max(np.nonzero(ok)[0]) + 1 if ok.any() else 0; res = np.zeros(n, bool); res[o[:k]] = True; return res
