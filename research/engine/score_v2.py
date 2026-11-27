"""Pre-race scoring with ENGINE v2 (benchmarks/engine_v2). For each meeting on a date, takes the latest write-once v1
prediction file (its operational score is v2's fixed base), the same field snapshot, and the history before the race
date, computes v2's new terms for every runner, and writes NEW write-once files (candidate 'engine_v2').
v2 score = v1 score + sum(coef x term). Terms are race-centred and scaled with the release's development constants.
Also usable as a library: rescore(meeting_table, overrides) re-computes everything after changing an input (demo).
Usage (from research/): PYTHONPATH=. python3 engine/score_v2.py 20261125"""
import sys, os, re, json, gzip, hashlib, subprocess, numpy as np, pandas as pd
from engine.lab import person_key, nk
V21 = os.environ.get('ENGINE_V21', '1') == '1'   # Engine v2.1 (25 Nov 2026): Queensland on the v3 rating; NSW/Vic/ACT unchanged
V22 = os.environ.get('ENGINE_V22', '1') == '1'   # Engine v2.2 (26 Nov 2026 run on): 14 Batch 10 terms for NSW/VIC/ACT/SA/WA/TAS (approved by Damo 25 Nov); Qld stays v2.1
from engine import v22
BASE_MANP = 'benchmarks/engine_v2_1/manifest.json' if V21 else 'benchmarks/engine_v2/manifest.json'
MAN = json.load(open(BASE_MANP))
C2 = os.environ.get('ENGINE_C2', '0') == '1'   # Engine v2.3 candidate for NSW/VIC/ACT/SA/WA/TAS only (benchmarks/engine_v2_3); Qld untouched; default off
Q213 = os.environ.get('ENGINE_QLD213', '0') == '1' and V21   # Engine v2.1.3 candidate for Queensland only: v2.1.1 + Age & sex family (benchmarks/engine_v2_1_3); default off
# the file each family's settings were actually loaded from (fingerprints are taken from these, 27 Nov 2026 fix)
FAMILY_FILE = {'NSW_VIC_ACT': 'benchmarks/engine_v2_3/engine_v2.json' if C2 else BASE_MANP, 'QLD': 'benchmarks/engine_v2_1_3/manifest.json' if Q213 else BASE_MANP}
if C2: MAN['families']['NSW_VIC_ACT'] = json.load(open(FAMILY_FILE['NSW_VIC_ACT']))['families']['NSW_VIC_ACT']
if Q213: MAN['families']['QLD'] = json.load(open(FAMILY_FILE['QLD']))['families']['QLD']
SNAPDIR = os.environ.get('SNAPDIR', '/mnt/user-data/uploads/Downloads')   # override for cloud-collected bundles
def find_bundle(name):
    """snapshot bundles live in the PC download folder (staged) or, for cloud-collected fields, collect/national/<date>/bundles"""
    import glob
    for d in [SNAPDIR, '/mnt/user-data/uploads/Downloads'] + sorted(glob.glob('collect/national/*/bundles')):
        if os.path.exists(os.path.join(d, name)): return os.path.join(d, name)
    raise FileNotFoundError(name)
OPS = {'QLD': 'combined_v1 + national dynamic rating', 'NSW_VIC_ACT': 'nat_v2 (+ horse records)'}
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
gband = lambda g: 'heavy' if 'heavy' in str(g).lower() else 'soft' if 'soft' in str(g).lower() else 'synthetic' if re.search('synth|poly', str(g).lower()) else 'good'
dband = lambda m: 's' if m <= 1150 else 'm' if m <= 1450 else 'mi' if m <= 1750 else 'l'
METRO = {'randwick', 'rosehill', 'warwick-farm', 'canterbury', 'flemington', 'caulfield', 'moonee-valley', 'sandown'}
_U = {}
def frame_path(fam):
    return 'engine/frames/national_v3.parquet' if (V21 and fam == 'QLD') else ('engine/frames/national_c2.parquet' if C2 else 'engine/frames/national.parquet')
def history(D, fam='NSW_VIC_ACT'):
    key = 'U3' if (V21 and fam == 'QLD') else 'U'
    if key not in _U: _U[key] = pd.read_parquet(frame_path(fam))
    U = _U[key]; H_ = U[U.date < pd.Timestamp(D)]
    assert len(H_) == len(U), 'history holds results on/after the race date: not a pre-race run'
    return H_

def new_raw(T, H_, fam, records=False):
    """T: today's runners (one meeting) with horse key, jockey, trainer, distance_m, weight_kg, config, gband, dband, date, race_id, dyn_nat (today's
    pre-race rating) and benchmark. Returns T with the raw new features (same definitions as engine/lab.py)."""
    T = T.copy(); D = T.date.iloc[0]
    # weight the model sees = weight carried (the v1 file's weight_carried_kg, claim already taken off ONCE there); the allocated weight is restored for output
    alloc_ = T.weight_kg.copy(); carried_ = fam != 'QLD' and 'weight_carried_kg' in T and T.weight_carried_kg.notna().all()
    if carried_: T['weight_kg'] = T.weight_carried_kg.astype(float)
    inn = H_.dyn_nat_inn
    def shrunk(keycol, keys, k):
        g = pd.DataFrame({'k': keycol, 'v': inn.fillna(0.0), 'c': inn.notna().astype(float)}).dropna(subset=['k']).groupby('k')[['v', 'c']].sum()
        s = g.reindex(keys); return (s.v.fillna(0) / (s.c.fillna(0) + k)).values, s.c.fillna(0).values
    T['jkey'] = T.jockey.map(person_key); T['tkey'] = T.trainer.map(person_key)
    T['j_surp'], T['j_n'] = shrunk(H_.jkey, T.jkey, 50); T['t_surp'], T['t_n'] = shrunk(H_.tkey, T.tkey, 50)
    T['jt_surp'], _ = shrunk(H_.jkey + '|' + H_.tkey, T.jkey + '|' + T.tkey, 50)
    T.loc[T.jkey.isna(), 'j_surp'] = np.nan; T.loc[T.tkey.isna(), 't_surp'] = np.nan
    hh = H_[H_.horse.isin(T.horse)].sort_values(['horse', 'date', 'race'])
    last = hh.groupby('horse').tail(1).set_index('horse'); prev2 = hh.groupby('horse').nth(-2).set_index('horse') if len(hh) else hh
    T['j_change'] = T.j_surp - T.horse.map(last.j_surp)
    T['surprise_last'] = T.horse.map(last.dyn_nat_inn); T['dyn_traj'] = T.dyn_nat - T.horse.map(prev2.dyn_nat)
    T['wt_change'] = T.weight_kg - T.horse.map(last.weight_kg); T['dist_change'] = np.log(T.distance_m / T.horse.map(last.distance_m))
    bm_today = pd.to_numeric(T.get('benchmark', pd.Series(np.nan, index=T.index)).astype(str).str.extract(r'(\d+)')[0], errors='coerce')
    T['bm_change'] = bm_today - pd.to_numeric(T.horse.map(last.bm), errors='coerce')
    la = T.horse.map(last.age_n); ld = T.horse.map(last.date)
    seasons = [sum(1 for y in range(d0.year, D.year + 1) if d0 < pd.Timestamp(y, 8, 1) <= D) if d0 == d0 and d0 is not None else np.nan for d0 in ld]
    T['age_n'] = la + np.array(seasons, dtype=float); T['female'] = T.horse.map(last.sex).isin(['m', 'f']).astype(float).where(T.horse.map(last.sex).notna())
    T['young'] = (T.age_n <= 3).astype(float).where(T.age_n.notna()); T['old'] = (T.age_n >= 7).astype(float).where(T.age_n.notna())
    # horse records for today's configuration / going band / distance band (k = 1)
    for key, nm in [('config', 'c_rec'), ('gband', 'g_rec'), ('dband', 'd_rec')]:
        g = hh.assign(v=hh.dyn_nat_inn.fillna(0), c=hh.dyn_nat_inn.notna().astype(float)).groupby(['horse', key])[['v', 'c']].sum()
        idx = pd.MultiIndex.from_arrays([T.horse, T[key]]); s = g.reindex(idx)
        T[nm] = (s.v.fillna(0) / (s.c.fillna(0) + 1)).values if (fam == 'QLD' or records or nm + '_v1' not in T) else T[nm]
        T[nm + '_n'] = s.c.fillna(0).values
    # head-to-head among today's runners (earlier shared races)
    P = H_[H_.finish_pos.notna() & (H_.finish_pos <= H_.field) & H_.horse.isin(T.horse)][['race', 'horse', 'finish_pos']]
    pp = P.merge(P, on='race', suffixes=('', '_o')); pp = pp[pp.horse != pp.horse_o]
    vals = []
    for _, r in T.iterrows():
        riv = set(T[(T.race_id == r.race_id) & (T.horse != r.horse)].horse); q = pp[(pp.horse == r.horse) & pp.horse_o.isin(riv)]
        if len(q) == 0: vals.append(np.nan); continue
        per = q.assign(b=np.sign(q.finish_pos_o - q.finish_pos)).groupby('horse_o').b.agg(['sum', 'count']); vals.append(float((per['sum'] / (per['count'] + 1)).sum() / max(len(riv), 1)))   # training averaged over ALL rivals (unmet = 0)
    T['h2h'] = vals
    if V22 and fam != 'QLD': T = v22.raw(T, H_)                 # Engine v2.2: career shape, consistency, weight, spacing, measured venue class
    T['weight_kg'] = alloc_.values; T['weight_basis'] = 'carried' if carried_ else 'as given'
    return T

def terms(T, fam):
    F = MAN['families'][fam]; allt = list(F['coef_per_term_sd_all_races']); bsd = F['base_feature_dev_sd']; tsd = F['term_dev_sd']; ctx = F['context']
    T = T.copy(); T['yr'] = float(T.date.iloc[0].year - 2024); T['vic'] = (T.state == 'VIC').astype(float); T['big_field'] = (T.field >= 12).astype(float)
    T['route'] = (T.distance_m >= 1400).astype(float); T['metro'] = T.venue.isin(METRO).astype(float) if fam != 'QLD' else 0.0; T['wet'] = T.gband.isin(['soft', 'heavy']).astype(float)
    T['abs_dist_change'] = T.dist_change.abs(); T['field_dyn'] = T.groupby('race_id').dyn_nat.transform('mean')
    def z(c):
        v = T[c].astype(float); return ((v - v.groupby(T.race_id).transform('mean')) / bsd.get(c, 1.0)).fillna(0.0)
    fd = (T.field_dyn - ctx['field_dyn_mean']) / ctx['field_dyn_sd']
    out = {}
    for n in allt:
        if n == 'ability x field strength': t = z('dyn_nat') * fd
        elif n.endswith(' squared'): t = z(n.split(' ')[0]) ** 2
        elif ' x ' in n:
            t = 1.0
            for p in n.split(' x '): t = t * (z(p) if p in bsd else (T.yr if p == 'year' else T[p]))
        else: t = z(n) if n in bsd else T[n]
        t = pd.Series(np.nan_to_num(np.asarray(t, dtype=float)), index=T.index); t = t - t.groupby(T.race_id).transform('mean'); out[n] = t / tsd[n]
    return pd.DataFrame(out, index=T.index)

def apply(T, fam, base_col='v1_score'):
    F = MAN['families'][fam]; C = F['coef_per_term_sd_all_races']; TT = terms(T, fam)
    contrib = TT * pd.Series(C); T = T.copy(); tf = dict(F['term_families'])
    if V22 and fam != 'QLD':
        contrib = pd.concat([contrib, v22.terms(T)], axis=1); tf.update(v22.M['term_families'])
    fam_of = {t: f for f, ts in tf.items() for t in ts}
    for f in tf: T['v2+ ' + f] = contrib[[t for t in contrib.columns if fam_of[t] == f]].sum(axis=1)
    T['v2_score'] = T[base_col] + contrib.sum(axis=1); T['v2_score'] -= T.groupby('race_id').v2_score.transform('mean')
    e = np.exp(T.v2_score - T.groupby('race_id').v2_score.transform('max')); T['v2_chance_pct'] = 100 * e / e.groupby(T.race_id).transform('sum')
    T['v2_rank'] = T.groupby('race_id').v2_score.rank(ascending=False, method='first').astype(int)
    T['final_rating_kg_eq'] = T.v2_score / F['score_per_kg_total']
    return T, contrib

def meeting_table(ix):
    """build today's runner table for one meeting from its v1 prediction file + snapshot (+ national feature dump)."""
    W = pd.read_csv(ix.file); fam = 'QLD' if ix.snapshot_key.startswith('rq') else 'NSW_VIC_ACT'; W = W[W.candidate == OPS[fam]].copy()
    mf = json.load(open(ix.file.replace('_runners.csv', '_manifest.json'))); bundle = find_bundle(mf['snapshot_bundle']); key = ix.snapshot_key
    snap = None
    with gzip.open(bundle, 'rt') as fh:
        for line in fh:
            o = json.loads(line); v = o['value']; v = json.loads(v) if isinstance(v, str) else v
            if o['key'] == key: snap = v
    cond = snap.get('conditions', {}); D = pd.Timestamp(str(snap['date']))
    f = pd.DataFrame(snap['fields'])[['race_no', 'saddlecloth', 'trainer', 'distance_m'] + [c for c in ['benchmark'] if c in snap['fields'][0]]]
    W = W.merge(f, on=['race_no', 'saddlecloth'], how='left')
    W['horse_name'] = W.horse; W['horse'] = W.horse.map(nk); W['date'] = D; W['field'] = W.groupby('race_id').saddlecloth.transform('count')
    W['gband'] = gband(cond.get('track_condition')); W['dband'] = W.distance_m.map(dband); W['state'] = 'QLD' if fam == 'QLD' else ('VIC' if key.startswith('vic') else 'NSW')
    venue = snap.get('track') or snap.get('venue'); W['venue'] = re.sub(r'[^a-z0-9]+', '-', str(venue).lower()).strip('-')
    W['config'] = str(venue).replace(' ', '_') if fam == 'QLD' else W.venue
    W['dyn_nat'] = W.rating_kg_national; W['v1_score'] = W.race_relative_score
    if fam != 'QLD':
        dump = f'/tmp/v2_features_{ix.track}_{D:%Y%m%d}.parquet'
        subprocess.run(['python3', 'prerace/score_national_prerace.py', bundle, '../history/history.duckdb', D.strftime('%Y%m%d')], env={**os.environ, 'DUMP_FEATURES': dump, 'PYTHONPATH': '.'}, check=True, capture_output=True)
        R = pd.read_parquet(dump); R = R[R.venue == W.venue.iloc[0]] if 'venue' in R else R
        core = ['dyn_nat', 'f_avgfp3', 'f_lstarts', 'a_fs3', 'a_best3', 'a_wt_rel', 'r_ldays', 'c_rec', 'g_rec', 'd_rec', 'a_rec', 'f_lastfp', 'f_lastlm', 'f_cwin']
        W = W.drop(columns=['dyn_nat']).merge(R[['race_no', 'saddlecloth'] + [c for c in core if c in R]].rename(columns={c: c for c in core}), on=['race_no', 'saddlecloth'], how='left')
        for c in ['c_rec', 'g_rec', 'd_rec']: W[c + '_v1'] = W[c]
        assert np.allclose(W.dyn_nat.round(2), W.rating_kg_national.round(2), equal_nan=True), 'feature dump does not match the v1 prediction file'
    return W, fam, cond, mf

_FSHA = {}
def provenance(fam, ix, H_, m2, fallback):
    """What actually produced this file (27 Nov 2026 fix): fingerprints come from the files and in-memory settings used, not a label."""
    def fsha(p):
        if p not in _FSHA: _FSHA[p] = sha(p)
        return _FSHA[p]
    F = MAN['families'][fam]; used22 = bool(V22 and fam != 'QLD')
    files = {BASE_MANP: fsha(BASE_MANP), FAMILY_FILE[fam]: fsha(FAMILY_FILE[fam])}
    if used22: files[os.path.relpath(v22.MPATH)] = fsha(v22.MPATH)
    try:
        m1 = json.load(open(ix.file.replace('_runners.csv', '_manifest.json')))
        v1set = m1.get('model_manifest_sha256') or m1.get('model_manifests'); v1runs = m1.get('national_runs_sha256')
    except Exception: v1set, v1runs = None, None
    live = {'family': F, 'v22_terms': v22.M if used22 else None}
    fp = hashlib.sha256(json.dumps(live, sort_keys=True, default=str).encode()).hexdigest()
    return {'engine_version': m2['engine_release'], 'output': (os.environ.get('SHADOW_LABEL') or 'shadow: previous production engine (not live)') if SHADOW_PREV else 'production',
            'settings_fingerprint': fp, 'settings_fingerprint_of': 'sha256 of the family settings and v2.2-term settings held in memory when this file was scored',
            'settings_files_loaded': files, 'v1_layer_settings': v1set,
            'rating_build': {'history_frame': frame_path(fam), 'history_frame_sha256': fsha(frame_path(fam)), 'history_rows': int(len(_U['U3' if (V21 and fam == 'QLD') else 'U'])), 'v1_national_runs_sha256': v1runs},
            'rating_scale_model_units_per_kg': F['score_per_kg_total'], 'history_cutoff': str(H_.date.max().date()), 'generated_utc': m2['scored_utc'],
            'fallback': fallback or False}

if __name__ == '__main__':
    D = sys.argv[1]; stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%SZ')
    PRED_ROOT = os.environ.get('PRED_ROOT', 'prospective/prerace'); SHADOW_PREV = PRED_ROOT != 'prospective/prerace'   # shadow root: ops/run_prev_shadow.sh only
    IX = pd.read_csv(os.path.join(PRED_ROOT, 'INDEX.csv')); IX = IX[(IX.date.astype(str) == D) & IX.file.str.endswith('_runners.csv') & ~IX.file.str.contains('/v2_')]
    latest = IX.sort_values('scored_utc').groupby('track').tail(1)
    if os.environ.get('ONLY_TRACKS'): latest = latest[latest.track.isin(os.environ['ONLY_TRACKS'].split(','))]   # score only these meetings
    V22_ON = V22
    for _, ix in latest.iterrows():
        V22 = V22_ON                                              # each meeting starts on the release setting (a fallback applies to one meeting only)
        W, fam, cond, mf = meeting_table(ix); H_ = history(D, fam); fallback = os.environ.get('ENGINE_FALLBACK') or None if fam != 'QLD' else None
        try:
            T = new_raw(W, H_, fam); T, contrib = apply(T, fam)
        except Exception as ex:                                   # safety net: never lose a meeting's ratings to a v2.2 fault
            if not (V22 and fam != 'QLD'): raise
            print(f'WARNING Engine v2.2 failed for {ix.track} ({str(ex)[:120]}); scored with Engine v2.0 instead', file=sys.stderr)
            V22 = False; T = new_raw(W, H_, fam); T, contrib = apply(T, fam); fallback = f'v2.2 terms failed ({str(ex)[:80]}); scored without them (Engine v2.0 terms only)'
        od = os.path.dirname(ix.file) if not SHADOW_PREV else os.path.join(PRED_ROOT, D, str(ix.track).replace(' ', '_')); os.makedirs(od, exist_ok=True); base = os.path.join(od, f"v2_{os.path.basename(ix.file).replace('_runners.csv', '')}_{stamp}")
        fams = [c for c in T.columns if c.startswith('v2+ ')]
        keep = ['race_id', 'race_no', 'saddlecloth', 'horse_name', 'barrier', 'weight_kg', 'claim_used_kg', 'weight_carried_kg', 'weight_basis', 'jockey', 'trainer', 'v2_rank', 'v2_chance_pct', 'v2_score', 'final_rating_kg_eq', 'v1_score', 'rank', 'chance_pct'] + \
               [c for c in T.columns if c.startswith('grp_')] + fams + ['j_surp', 'j_n', 't_surp', 't_n', 'jt_surp', 'j_change', 'age_n', 'female', 'h2h', 'surprise_last', 'dyn_traj', 'dist_change', 'wt_change', 'bm_change', 'c_rec', 'c_rec_n', 'g_rec', 'g_rec_n', 'd_rec', 'd_rec_n', 'rating_kg_national']
        out = T[[c for c in keep if c in T]].rename(columns={'rank': 'v1_rank', 'chance_pct': 'v1_chance_pct', 'horse_name': 'horse'}).sort_values(['race_no', 'v2_rank'])
        out.insert(0, 'candidate', 'engine_v2'); out.insert(1, 'family', fam)
        paths = {'runners': base + '_runners.csv', 'manifest': base + '_manifest.json'}
        with open(paths['runners'], 'x') as fh: out.to_csv(fh, index=False)
        m2 = {'scored_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'engine': 'v2', 'family': fam, 'base_v1_file': ix.file, 'base_v1_sha256': sha(ix.file), 'snapshot_key': ix.snapshot_key,
              'engine_manifest_sha256': sha(FAMILY_FILE[fam]), 'engine_release': ((('Engine v2.1.3' if Q213 else MAN.get('version', 'Engine v2.1').split(' (')[0]) + ' (v3 rating)') if (V21 and fam == 'QLD') else ((('Engine v2.4-candidate (not live)' if v22.V24 else 'Engine v2.3') if C2 else 'Engine v2.2') if V22 else 'Engine v2.0.x')), 'v22_manifest_sha256': (sha(v22.MPATH) if (V22 and fam != 'QLD') else None), 'engine_c2': bool(C2 and fam != 'QLD'), 'code_sha256': {p: sha(p) for p in ['engine/score_v2.py', 'engine/lab.py', 'prerace/score_national_prerace.py']},
              'history_max_date': str(H_.date.max().date()), 'notes': ['no result of these races existed when this file was written', 'v2 = v1 operational score + new terms; v1 file unchanged']}
        if SHADOW_PREV: m2['shadow'] = 'NOT LIVE: previous production engine, scored after publishing for rollback and prospective comparison; never on the dashboard, never ranked or settled'
        try: m2['settings'] = provenance(fam, ix, H_, m2, fallback)      # record only: a failure here never stops scoring
        except Exception as ex_: m2['settings'] = {'error': f'provenance not recorded: {str(ex_)[:120]}', 'fallback': fallback or False}
        with open(paths['manifest'], 'x') as fh: json.dump(m2, fh, indent=1)
        with open(os.path.join(PRED_ROOT, 'INDEX.csv'), 'a') as fh:
            for kind, pth in paths.items(): fh.write(f"{m2['scored_utc']},{D},{ix.track},{ix.snapshot_key},{pth},{sha(pth)}\n")
        print('written', base); print(out.groupby('race_no').head(1)[['race_no', 'horse', 'v2_chance_pct', 'v1_rank', 'v1_chance_pct', 'final_rating_kg_eq'] + fams].to_string(index=False))
