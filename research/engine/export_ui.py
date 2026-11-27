"""Export one racing day to the dashboard's data contract  (racing-intelligence.daily v1.0).
The dashboard (ui/) only reads this JSON; the prediction engine only writes it. Any later engine version that fills the same
contract feeds the same interface. Everything here is read from saved, write-once prediction files and frozen manifests;
nothing is re-predicted. (v2 term-level detail is recomputed from the same inputs and must equal the saved v2 score.)
Usage: PYTHONPATH=. python3 engine/export_ui.py 20261125  -> ui/data/racing_<YYYY-MM-DD>.json (+ ui/data/index.json)"""
import sys, os, re, json, gzip, hashlib, numpy as np, pandas as pd
# The engine that scored the day decides how the day is exported (predictions are write-once), so a re-export (ops/rebuild_dashboard.sh)
# needs no run environment: a day scored by Engine v2.3 / v2.1.3 exports with them, any other day without them (26 Nov 2026 night).
def _day_releases(day):
    import csv
    rel = set()
    try:
        for r_ in csv.DictReader(open('prospective/prerace/INDEX.csv')):
            if str(r_['date']) == day and '/v2_' in r_['file'] and r_['file'].endswith('_manifest.json'): rel.add(str(json.load(open(r_['file'])).get('engine_release', '')))
    except Exception: pass
    return rel
_REL = _day_releases(sys.argv[1]) if len(sys.argv) > 1 else set()
if _REL:
    os.environ['ENGINE_C2'] = '1' if 'Engine v2.3' in _REL else '0'
    os.environ['ENGINE_QLD213'] = '1' if any(x.startswith('Engine v2.1.3') for x in _REL) else '0'
from engine import score_v2 as S
D = sys.argv[1]; DATE = f'{D[:4]}-{D[4:6]}-{D[6:]}'; NOW = pd.Timestamp.now(tz='UTC')
ENGINE_VERSION = 'Engine v2.1'; RELEASE_NOTE = 'v2.1 (25 Nov 2026, 12:17pm): Queensland ratings use the v3 rating, which expects lightly raced horses to improve (research/batch9 A; approved by Damo). NSW/Vic/ACT unchanged. v2.0.2 (12:06pm): win chances use the bent-line calibration. v2.0.1 (11:11am): Queensland scorer fix.'
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); RC = json.load(open('benchmarks/engine_v2/runner_calibration_v2.json' if os.path.exists('benchmarks/engine_v2/runner_calibration_v2.json') else 'benchmarks/engine_v2/runner_calibration.json'))
RC_OLD = RC; RC22 = json.load(open('benchmarks/engine_v2_2/runner_calibration_v22.json'))   # v2.2: NSW/Vic family recalibrated on v2.2 chances; QLD family unchanged
M22 = json.load(open('benchmarks/engine_v2_2/manifest.json'))
RC23 = json.load(open('benchmarks/engine_v2_3/runner_calibration.json')) if os.path.exists('benchmarks/engine_v2_3/runner_calibration.json') else None
# Engine v2.1.3 (Queensland candidate, v2.1.1 + Age & sex): its own Queensland family and display calibration, chosen per meeting from the saved engine_release
_q213 = 'benchmarks/engine_v2_1_3/manifest.json'; Q213F = json.load(open(_q213))['families']['QLD'] if os.path.exists(_q213) else None
RC213 = json.load(open('benchmarks/engine_v2_1_3/runner_calibration.json')) if os.path.exists('benchmarks/engine_v2_1_3/runner_calibration.json') else None
Q211F = json.load(open('benchmarks/engine_v2_1/manifest.json'))['families']['QLD']
_c23 = 'benchmarks/engine_v2_3/engine_v2.json'; KG23 = json.load(open(_c23))['families']['NSW_VIC_ACT']['score_per_kg_total'] if os.path.exists(_c23) else None   # v2.3 ratings are on its own kg scale
KG_USED = {}; CAL_USED = {}
V22_DAY = os.environ.get('ENGINE_V22', '1') == '1' and str(sys.argv[1]) >= os.environ.get('ENGINE_V22_FROM', '20261126')   # v2.2 predictions exist from the 26 Nov 2026 run; earlier days keep their own engine
if V22_DAY:
    RC = RC22; ENGINE_VERSION = 'Engine v2.3' if os.environ.get('ENGINE_C2', '0') == '1' else 'Engine v2.2'
    RELEASE_NOTE = 'v2.2 (26 Nov 2026 run on; approved by Damo 25 Nov): NSW, Vic, ACT, SA, WA and Tas add 14 Batch 10 terms (horses below their own proven level, own consistency, hot start to a preparation, quick backups, light weights, runs on file, rating certainty, measured venue class) and a recalibrated chance curve. Queensland: Engine v2.1.1, the v2.1 model refitted with Queensland country history (915 more meetings) and ages. ' + RELEASE_NOTE   # v2 = bent line (25 Nov 2026)
    _N23 = []
    if os.environ.get('ENGINE_C2', '0') == '1': _N23.append('v2.3 (27 Nov 2026 run on; approved by Damo 26 Nov): NSW, Vic, ACT, SA, WA and Tas ratings read past runs with 0.25 kg of credit for each extra kg carried (was 1 kg), and past margins become time figures at a fixed 0.170 s per length (was from each race speed); every layer refitted, display calibration refitted. The kg scale for these states changes from 0.226 to 0.269 per kg, so kg ratings read about 16% smaller: a change of units, not of any horse ability. Compare kg ratings within one engine only.')
    if os.environ.get('ENGINE_QLD213', '0') == '1': _N23.append('v2.1.3 (27 Nov 2026 run on; approved by Damo 26 Nov): Queensland adds age and sex (age, 3yo and under, 7yo and over, filly or mare); Queensland display calibration refitted; Queensland kg scale unchanged.')
    if _N23: RELEASE_NOTE = ' '.join(_N23) + ' Ability ratings (opposition-aware, kg-equivalent) and time figures (margins converted to time; estimates, not measured times) remain separate inputs. Previously: ' + RELEASE_NOTE
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
OPS = {'QLD': 'combined_v1 + national dynamic rating', 'NSW_VIC_ACT': 'nat_v2 (+ horse records)'}
GROUP = {'Opposition-aware rating': ('ability', 'Ability: opposition-aware rating'), 'Recent ability figures': ('figures', 'Form figures and opposition faced'),
         'Ability figures': ('figures', 'Form figures and opposition faced'), 'Recent form': ('form', 'Recent form'), 'Closing sectionals': ('sectionals', 'Closing sectionals'),
         'Barrier and race shape': ('shape', 'Barrier and race shape'), 'Track, distance, going': ('trackhist', 'Track, distance and going starts'),
         'Fitness and spacing': ('fitness', 'Fitness and spacing'), 'Horse suits course/going/distance': ('suit', 'Course, going and distance suitability'),
         'Horse course/going/distance records': ('suit', 'Course, going and distance suitability'), 'Jockey & trainer': ('people', 'Jockey and trainer'),
         'Age & sex': ('age', 'Age and sex'), 'Form changes & head-to-head': ('changes', 'Form changes and head-to-head'), 'Interactions (chosen on discovery data only)': ('inter', 'Combined effects (interactions)'),
         'Career shape and consistency': ('career', 'Career shape and consistency (v2.2)'), 'Weight, spacing and venue class': ('load', 'Weight, spacing and venue class (v2.2)')}
V2FAM = {'Horse course/going/distance records', 'Jockey & trainer', 'Age & sex', 'Form changes & head-to-head', 'Interactions (chosen on discovery data only)', 'Career shape and consistency', 'Weight, spacing and venue class'}
TERMNAME = {'j_surp': 'jockey record', 't_surp': 'trainer record', 'jt_surp': 'jockey-trainer combination', 'j_change': 'jockey change vs last start', 'age_n': 'age', 'young': '3yo or younger', 'old': '7yo or older',
            'female': 'mare or filly', 'h2h': 'head-to-head vs these rivals', 'abs_dist_change': 'size of distance change', 'dist_change': 'distance change', 'dyn_traj': 'rating trend', 'surprise_last': 'last start vs rating',
            'bm_change': 'class change', 'wt_change': 'weight change', 'c_rec': 'course record', 'g_rec': 'going record', 'd_rec': 'distance record', 'dyn_nat': 'ability rating', 'f_avgfp3': 'average finish',
            'f_lstarts': 'career starts', 'a_fs3': 'opposition faced', 'a_best3': 'best figure', 'a_wt_rel': 'weight vs field', 'r_ldays': 'days since run', 'route': '1400m+', 'metro': 'metro', 'wet': 'wet track',
            'big_field': 'big field', 'vic': 'Victoria', 'year': 'trend over time', 'ability': 'ability', 'field strength': 'field strength', 'f_lastfp': 'last finish', 'a_rec': 'recent figures',
            'below_top3': 'below its best three runs', 'gap_long_z': 'vs its longer-run level', 'short_vs_long': 'last 5 vs longer-run level', 'slope15': 'long-run trend', 'neg_run': 'run of below-par runs',
            'recent_var_ratio': 'unusually variable lately', 'hsd_x_rel': 'own consistency x favourite/outsider', 'early_prep_vs_usual': 'hot start to this preparation', 'quick_today': 'quick backup',
            'venue_step': 'step in measured venue class', 'recentform_x_established': 'recent form (established horse)', 'light_weight': 'light weight (54 kg or less)', 'log_runs_held': 'runs on file', 'rating_uncertainty': 'rating certainty'}
def tname(t):
    if t.endswith(' squared'): return TERMNAME.get(t.split(' ')[0], t.split(' ')[0]) + ' (curved)'
    return ' × '.join(TERMNAME.get(p, p) for p in t.split(' x '))
def cal(p, n, fam):
    F = RC['families'][fam]; l_ = np.log(p / (1 - p))
    if 'knots_logit' in F: b = np.array(F['coef_const_logitp_bends_logfield']); z = np.array([1, l_] + [max(l_ - k_, 0.0) for k_ in F['knots_logit']] + [np.log(n)])
    else: b = np.array(F['coef_const_logitp_logfield']); z = np.array([1, l_, np.log(n)])
    B = np.array(F['bootstrap_coefs'])
    c = 1 / (1 + np.exp(-z @ b)); lo, hi = np.percentile(1 / (1 + np.exp(-(B @ z))), [10, 90]); return float(c), float(lo), float(hi)
def race_class(name):
    n = name.upper(); out = []
    if 'MAIDEN' in n: out.append('Maiden')
    m = re.search(r'BENCHMARK\s*(\d+)|\bBM\s?(\d+)', n); out += [f'Benchmark {m.group(1) or m.group(2)}'] if m else []
    m = re.search(r'CLASS\s*(\d)', n); out += [f'Class {m.group(1)}'] if m else []
    m = re.search(r'RATINGS BAND\s*([\d\s\-]+)', n); out += [f'Ratings band {m.group(1).strip()}'] if m else []
    if 'QTIS' in n: out.append('QTIS')
    m = re.search(r'(\d)YO', n.replace('THREE-YEAR-OLD', '3YO')); out += [f'{m.group(1)}yo' + ('+' if '&UP' in n or '& UP' in n else '')] if m else []
    if 'HANDICAP' in n: out.append('Handicap')
    elif 'PLATE' in n: out.append('Set weights')
    return ' · '.join(dict.fromkeys(out)) or None
def tm(s, tz):
    m = re.match(r'0?(\d{1,2}):(\d{2})\s*([AP]M)', str(s).upper())
    if not m: return None, None
    h, mi = int(m.group(1)), int(m.group(2)); h24 = h % 12 + (12 if m.group(3) == 'PM' else 0); bris = h24 * 60 + mi + {'AEDT': -60, 'ACDT': -30, 'AWST': 120}.get(tz, 0)
    return f"{h}:{mi:02d}{m.group(3).lower()}", bris
def clean_name(n): return re.sub(r'\s+', ' ', n).strip()
def nice(n):
    n = clean_name(str(n))
    if not n.isupper() or len(re.sub(r'[^A-Z]', '', n)) <= 3: return n
    def w(x):
        if x.strip('()') in ('NZ', 'GB', 'IRE', 'USA', 'FR', 'GER', 'JPN', 'AUS', 'TAB', 'QTIS', 'BM', 'FC'): return x
        x = x.lower(); x = x[:1].upper() + x[1:]
        if len(x) > 2 and x[1] == "'": x = x[:2] + x[2].upper() + x[3:]
        return x
    return ' '.join('-'.join(w(y) for y in t.split('-')) for t in n.split(' '))

SHORT = {'ability': 'Ability rating', 'figures': 'Form figures', 'form': 'Recent form', 'sectionals': 'Closing sectionals', 'shape': 'Barrier and race shape',
         'trackhist': 'Track and distance starts', 'fitness': 'Fitness and spacing', 'suit': 'Suits course, going or distance', 'people': 'Jockey and trainer',
         'age': 'Age and sex', 'changes': 'Form changes and head-to-head', 'inter': 'Combined effects', 'career': 'Career shape and consistency', 'load': 'Weight, spacing and venue class'}
# ---- market prices: a DISPLAY layer only. Never read by any model. Files: prices/<date>/*.jsonl, one quote per line:
# {"meeting","race_no","saddlecloth","source","kind","price","captured_utc"}  kind in fixed_win | fixed_place | exchange_back | exchange_lay | exchange_ltp
MKT, QUOTES = {}, []
if os.path.isdir(f'prices/{D}'):
    for f_ in sorted(os.listdir(f'prices/{D}')):
        if f_.endswith('.jsonl'): QUOTES += [json.loads(l) for l in open(f'prices/{D}/{f_}') if l.strip()]
import glob, csv
TABR, TABS = {}, {}
for f_ in sorted(glob.glob(f'prices/{D}/tab_*_races.json')):
    j_ = json.load(open(f_))
    for r_ in j_['races']: TABR[(r_['meeting'], r_['race_no'])] = {**r_, 'captured_utc': j_['captured_utc']}
for f_ in sorted(glob.glob(f'prices/{D}/tab_*_match.csv')):
    for r_ in csv.DictReader(open(f_)): TABS[(r_['meeting'], int(r_['race']), int(r_['n']))] = r_['tab_status']   # latest snapshot wins
def mkt(meeting, rn, n):
    """display-only market cell: TAB fixed odds if matched and open; otherwise an honest note"""
    st = TABS.get((meeting, rn, n)); rr = TABR.get((meeting, rn)); q = MKT.get((meeting, rn, n))
    if st and st != 'Open': return {'note': 'Scratched per TAB', 'captured_utc': rr and rr['captured_utc']}
    if q: return q
    if rr and not rr['has_fixed_odds']: return {'note': 'Not offered yet (TAB)', 'captured_utc': rr['captured_utc']}
    return None
for q_ in sorted(QUOTES, key=lambda q: q['captured_utc']):
    k_ = (q_['meeting'], int(q_['race_no']), int(q_['saddlecloth'])); e_ = MKT.setdefault(k_, {'quotes': 0})
    e_[q_['kind']] = {'price': q_['price'], 'source': q_['source'], 'captured_utc': q_['captured_utc']}; e_['quotes'] += 1
IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[(IX.date.astype(str) == D) & IX.file.str.endswith('_runners.csv')]
v2rows = IX[IX.file.str.contains('/v2_')].sort_values('scored_utc'); H_ = S.history(D)
U = pd.read_parquet('engine/frames/national.parquet', columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn'])
runs = U[U.dyn_nat_inn.notna()].groupby('horse').size(); lastd = U.groupby('horse').date.max()
meetings = []; all_runners = []
for track, grp in v2rows.groupby('track', sort=False):
    snaps = []
    for _, ix in grp.iterrows():
        m2 = json.load(open(ix.file.replace('_runners.csv', '_manifest.json'))); m1 = json.load(open(m2['base_v1_file'].replace('_runners.csv', '_manifest.json')))
        snaps.append((ix, m2, m1))
    ix, m2, m1 = snaps[-1]                                   # latest valid snapshot is the default; earlier ones are listed
    fam = m2['family']; tz = 'AEST' if fam == 'QLD' else 'AEDT'; kg = MAN['families'][fam]['score_per_kg_total']
    W = pd.read_csv(ix.file); V1 = pd.read_csv(m2['base_v1_file']); V1o = V1[V1.candidate == OPS[fam]]
    snap = None
    with gzip.open(S.find_bundle(m1['snapshot_bundle']), 'rt') as fh:
        for line in fh:
            o = json.loads(line); v = o['value']; v = json.loads(v) if isinstance(v, str) else v
            if o['key'] == m1['snapshot']['snapshot_key']: snap = v
    F = pd.DataFrame(snap['fields']); cond = m1['snapshot'].get('conditions', {})
    st = snap.get('state') or ('QLD' if fam == 'QLD' else 'NSW'); tz = snap.get('tz') or tz; notes = []
    is22 = V22_DAY and fam != 'QLD' and m2.get('engine_release') in ('Engine v2.2', 'Engine v2.3'); S.V22 = is22
    RC = RC23 if (is22 and m2.get('engine_release') == 'Engine v2.3') else (RC22 if is22 else RC_OLD)   # v2.3 = candidate C2 with its own calibration
    is213 = fam == 'QLD' and str(m2.get('engine_release') or '').startswith('Engine v2.1.3')
    if fam == 'QLD' and S.V21: S.MAN['families']['QLD'] = Q213F if is213 else Q211F    # term detail recomputed with the family that scored this meeting
    if is213: RC = RC213
    if is22 and m2.get('engine_release') == 'Engine v2.3': kg = KG23              # the divisor score_v2 used for this meeting's final_rating_kg_eq
    if is213: kg = Q213F['score_per_kg_total']
    KG_USED['QLD' if fam == 'QLD' else 'NAT'] = kg
    CAL_USED['QLD' if fam == 'QLD' else 'NSW_VIC_ACT'] = RC['families']['QLD' if fam == 'QLD' else 'NSW_VIC_ACT']   # the calibration each family was shown with
    vk = re.sub(r'[^a-z0-9]+', '-', str(track).lower()).strip('-'); vk = M22['venue_alias'].get(vk, vk); vl = M22['venue_level_kg'].get(vk)
    if vl is not None: notes.append('Measured class of this course: ' + ('metro level' if vl >= -2.9 else 'provincial level' if vl >= -6.85 else 'country level') + f' (average field rating {vl:+.1f} kg vs metro about 0, provincial about -6, country about -8).')
    if fam != 'QLD' and not cond.get('track_condition'): notes.append('Track condition was not available from the field source; the Good going band is assumed for going records until an official rating is collected.')
    if snap.get('source'): notes.append('Fields source: ' + snap['source'] + '.')
    # term-level v2 detail, recomputed from the same saved inputs; must equal the saved v2 score
    ixv1 = IX[IX.file == m2['base_v1_file']].iloc[0]
    T, _, _, _ = S.meeting_table(ixv1); T = S.new_raw(T, S.history(D, fam), fam); T, contrib = S.apply(T, fam)
    chk = pd.Series(T.v2_score.values, index=list(zip(T.race_no, T.saddlecloth))) - pd.Series(W.v2_score.values, index=list(zip(W.race_no, W.saddlecloth))).reindex(list(zip(T.race_no, T.saddlecloth))).values
    assert chk.abs().max() < 1e-6, f'recomputed v2 detail does not match the saved prediction ({chk.abs().max()})'
    contrib.index = list(zip(T.race_no, T.saddlecloth))
    W = W.merge(V1o[[c for c in ['race_no', 'saddlecloth', 'has_prior_form', 'has_figure', 'has_sectionals', 'has_running_style', 'days_since', 'rating_sd_kg_national', 'rating_sd_kg_qld', 'n_prior_runs_held'] if c in V1o]], on=['race_no', 'saddlecloth'], how='left')
    W = W.merge(F[[c for c in ['race_no', 'saddlecloth', 'last10', 'claim_kg', 'emergency'] if c in F]], on=['race_no', 'saddlecloth'], how='left')
    gcols = [c for c in W.columns if c.startswith('grp_') or c.startswith('v2+ ')]
    for c in gcols: W[c] = W[c] - W.groupby('race_id')[c].transform('mean')        # race-centred so the parts add up exactly
    races = []; not_scored = pd.DataFrame(m1.get('not_scored') or [])
    scr = {(s_['race_no'], h['saddlecloth']): h for s_ in (snap.get('scratchings') or []) for h in s_['horses']}
    for rn, g in W.groupby('race_no'):
        g = g.sort_values('v2_rank'); fr = F[F.race_no == rn].iloc[0]; n = len(g); t_local, t_bris = tm(fr.start_time, tz)
        rr = []
        for _, r in g.iterrows():
            parts = []
            for c in gcols:
                name = c.replace('grp_', '').replace('v2+ ', ''); key, label = GROUP[name]
                parts.append({'key': key, 'label': label, 'kg': round(float(r[c]) / kg, 3), 'new_in_v2': name in V2FAM})
            agg = {}
            for p in parts:
                a = agg.setdefault(p['key'], {**p, 'kg': 0.0}); a['kg'] = round(a['kg'] + p['kg'], 3)
            groups = sorted(agg.values(), key=lambda p: -abs(p['kg']))
            final = round(float(sum(p['kg'] for p in groups)), 2)
            assert abs(final - r.final_rating_kg_eq) < 0.05, f'breakdown does not reconcile {final} {r.final_rating_kg_eq}'
            terms = contrib.loc[[(rn, r.saddlecloth)]].iloc[0] / kg
            terms = terms[terms.abs() > 0.005].sort_values(key=abs, ascending=False)
            p_ = r.v2_chance_pct / 100; c_, lo, hi = cal(min(max(p_, 1e-4), 0.999), n, fam)
            gaps = []
            if not r.has_prior_form: gaps.append('No prior form in our database')
            elif fam == 'QLD' and not r.has_sectionals: gaps.append('No sectional history')
            if fam != 'QLD': gaps.append('The model uses no sectionals or barrier history in this state (tracked runs held, if any, are shown for inspection only)')
            if pd.isna(r.jockey): gaps.append('Jockey not named in the fields (treated as average)')
            elif not (r.j_n >= 30): gaps.append('Jockey has little history with us')
            if not (r.t_n >= 30): gaps.append('Trainer has little history with us')
            if r.c_rec_n == 0 and r.has_prior_form: gaps.append('No previous run at this course')
            if fam != 'QLD' and pd.isna(r.age_n): gaps.append('Age unknown')
            checks = [bool(r.has_prior_form), bool(r.get('has_figure', r.has_prior_form)), (fam != 'QLD') or bool(r.has_sectionals), bool(r.j_n >= 30), bool(r.t_n >= 30), bool(r.c_rec_n > 0)]
            hk = S.nk(r.horse); sd = r.get('rating_sd_kg_national') if fam != 'QLD' else r.get('rating_sd_kg_qld')
            ro = {'n': int(r.saddlecloth), 'horse': nice(r.horse), 'barrier': None if pd.isna(r.barrier) else int(r.barrier), 'weight': None if pd.isna(r.weight_kg) else float(r.weight_kg),
                  'claim': None if 'claim_kg' not in r or pd.isna(r.claim_kg) else float(r.claim_kg), 'jockey': None if pd.isna(r.jockey) else str(r.jockey), 'trainer': None if pd.isna(r.trainer) else str(r.trainer),
                  'last10': None if 'last10' not in r or pd.isna(r.last10) else str(r.last10), 'rank': int(r.v2_rank), 'rating': round(float(r.final_rating_kg_eq), 2), 'chance': round(float(r.v2_chance_pct), 2),
                  'cal': round(100 * c_, 1), 'cal_lo': round(100 * lo, 1), 'cal_hi': round(100 * hi, 1), 'groups': groups,
                  'terms': [{'term': tname(k), 'kg': round(float(v), 3)} for k, v in terms.items()][:40],
                  'ability': {'rating_kg': round(float(r.rating_kg_national), 2), 'sd_kg': None if sd is None or pd.isna(sd) else round(float(sd), 2), 'sd_source': 'national' if fam != 'QLD' else 'Queensland rating model',
                              'change_after_last_run_kg': None, 'rated_runs': int(runs.get(hk, 0)), 'last_run': None if hk not in lastd else str(lastd[hk].date()), 'days_since': None if pd.isna(r.days_since) else int(r.days_since)},
                  'records': {'course': {'kg': round(float(r.c_rec), 2), 'runs': int(r.c_rec_n)}, 'going': {'kg': round(float(r.g_rec), 2), 'runs': int(r.g_rec_n)}, 'distance': {'kg': round(float(r.d_rec), 2), 'runs': int(r.d_rec_n)}},
                  'people': {'jockey_kg': None if pd.isna(r.j_surp) else round(float(r.j_surp), 2), 'jockey_rides': None if pd.isna(r.j_n) else int(r.j_n), 'trainer_kg': None if pd.isna(r.t_surp) else round(float(r.t_surp), 2),
                             'trainer_runners': None if pd.isna(r.t_n) else int(r.t_n), 'combo_kg': None if pd.isna(r.jt_surp) else round(float(r.jt_surp), 2)},
                  'age': None if pd.isna(r.age_n) else int(r.age_n), 'female': None if pd.isna(r.female) else bool(r.female),
                  'v1': {'rank': int(r.v1_rank), 'chance': round(float(r.v1_chance_pct), 2)},
                  'evidence': {'score': int(sum(checks)), 'max': len(checks), 'gaps': gaps}}
            ro['reasons'] = [SHORT[g['key']] for g in groups if g['kg'] > 0.25][:3]; ro['against'] = [SHORT[g['key']] for g in sorted(groups, key=lambda g: g['kg']) if g['kg'] < -0.25][:2]
            ro['market'] = mkt(track, int(rn), int(r.saddlecloth))
            # Batch 11 (display only): say plainly when a runner has no demonstrated race rating. Its chance is a prior estimate
            # (jockey/trainer, weight, barrier, age/sex, population average for its experience), not measured ability.
            nr_ = ro['ability']['rated_runs']; prev_ = ro['ability']['last_run'] is not None or ro['ability']['days_since'] is not None
            if nr_ == 0 and not prev_: exp_ = 'First starter · no demonstrated race rating'
            elif nr_ == 0: exp_ = 'Has raced, but no rated runs held · no demonstrated race rating'
            elif fam == 'QLD' and not bool(r.has_prior_form): exp_ = 'Runs held only outside Queensland tracking · Queensland form inputs missing'
            elif nr_ <= 2: exp_ = f'Lightly raced · {nr_} rated run' + ('s' if nr_ > 1 else '')
            else: exp_ = None
            ro['experience'] = exp_; ro['demonstrated'] = bool(nr_ > 0)
            rr.append(ro)
        # change in rating after last run (from the ranking file of this same prediction)
        top = rr[0]; second = rr[1] if n > 1 else None
        for i, ro in enumerate(rr): ro['gap'] = round(ro['rating'] - (second['rating'] if i == 0 and second else top['rating']), 2)
        tcal = top['cal'] / 100; terc = RC['families'][fam]['top_pick_terciles']
        insufficient = (not g.iloc[0].has_prior_form) or (1 - g.has_prior_form.mean()) > 0.5
        label = 'Insufficient evidence' if insufficient else ('Strong selection' if tcal >= terc[1] else 'Leading contender' if tcal >= terc[0] else 'No clear selection')
        for i, ro in enumerate(rr):
            if not g.iloc[i].has_prior_form: ro['class'] = 'Insufficient evidence'
            elif i == 0: ro['class'] = label if not insufficient else 'Insufficient evidence'
            elif i < 3: ro['class'] = 'Contender'
            else: ro['class'] = 'Outsider'
            ro['qualified'] = bool(g.iloc[i].has_prior_form) and not insufficient
        ns = [{'n': int(x_['saddlecloth']), 'horse': nice(x_['horse']), 'status': x_['status'],
               'when': scr.get((rn, x_['saddlecloth']), {}).get('when')} for _, x_ in not_scored[not_scored.race_no == rn].iterrows()] if len(not_scored) else []
        unr_ = [x_ for x_ in rr if not x_['demonstrated']]; lt_ = [x_ for x_ in rr if 0 < x_['ability']['rated_runs'] <= 2]
        tot_ = sum(x_['chance'] for x_ in rr) or 1.0; sh_ = sum(x_['chance'] for x_ in unr_) / tot_
        lvl_ = 'Low' if (not rr[0]['demonstrated']) or sh_ >= 0.30 else ('Medium' if sh_ >= 0.10 or any(x_ in lt_ for x_ in rr[:3]) else 'High')
        conf_ = {'level': lvl_, 'no_demonstrated_rating': len(unr_), 'lightly_raced': len(lt_), 'chance_on_unrated_pct': round(100 * sh_, 1),
                 'note': (f"{len(unr_)} of {n} runners have no demonstrated race rating and hold {round(100 * sh_)}% of the model's win chance" if unr_ else 'Every runner has at least one rated run')
                         + (f"; {len(lt_)} lightly raced (1-2 rated runs)" if lt_ else '')}
        races.append({'no': int(rn), 'name': nice(fr.race_name), 'confidence': conf_, 'class': race_class(str(fr.race_name)), 'distance_m': int(fr.distance_m),
                      'time': t_local, 'tz': tz, 'time_brisbane_min': t_bris, 'field': n, 'label': label, 'top_cal': top['cal'], 'runners': rr, 'not_scored': ns,
                      'v1_top': next(x for x in rr if x['v1']['rank'] == 1)['horse']})
        for ro in rr: all_runners.append({'meeting': track, 'race': int(rn), **{k: ro[k] for k in ['n', 'horse', 'rank', 'rating', 'chance', 'cal', 'cal_lo', 'cal_hi', 'gap', 'class', 'qualified', 'reasons', 'market']}, 'evidence': ro['evidence']['score'], 'evidence_max': ro['evidence']['max'], 'time': t_local, 'tz': tz, 'tmin': t_bris, 'race_label': label})
    # rating change after last run: from the v2 daily ranking file built from this same prediction set
    RK = sorted([f for f in os.listdir(f'prospective/daily/{D}') if f.startswith('ranking_v2_') and f.endswith('_runners.csv')])
    if RK:
        rk = pd.read_csv(f'prospective/daily/{D}/{RK[-1]}'); rk = rk[rk.meeting == track].set_index(['race_no', 'saddlecloth']).rating_change_kg
        for race in races:
            for ro in race['runners']:
                v = rk.get((race['no'], ro['n'])); ro['ability']['change_after_last_run_kg'] = None if v is None or pd.isna(v) else round(float(v), 2)
    def snap_kind(s1):
        cap = pd.Timestamp(s1['snapshot']['retrieved_utc']).tz_convert('Australia/Brisbane'); rd = pd.Timestamp(DATE).date()   # Brisbane clock for every state; a night-before capture after midnight in Sydney is still the night before
        if cap.date() < rd: return 'Night-before fields (before final scratchings)', 'pre-final-scratchings'
        if s1['snapshot'].get('conditions', {}).get('after_final_scratchings'): return 'After final scratchings', 'post-final-scratchings'
        close = re.search(r'(\d{1,2}):(\d{2})\s*([ap]m)', str(s1['snapshot'].get('conditions', {}).get('scratchings_close') or ''), re.I)
        if close:
            h = int(close.group(1)) % 12 + (12 if close.group(3).lower() == 'pm' else 0)
            if (cap.hour, cap.minute) >= (h, int(close.group(2))): return 'After final scratchings', 'post-final-scratchings'
        return 'Race-morning fields (scratchings as published at capture)', 'race-morning'
    snap_list = [{'id': s2['snapshot_key'].split(':')[-1], 'label': snap_kind(s1)[0], 'kind': snap_kind(s1)[1],
                  'fields_captured_utc': s1['snapshot']['retrieved_utc'], 'v1_scored_utc': s1['scored_utc'], 'v2_scored_utc': s2['scored_utc']} for s0, s2, s1 in snaps]
    for i_, s_ in enumerate(snap_list):   # same fields scored again (a re-issue): unique id, labelled with the re-issue time
        if any(t_['id'] == s_['id'] for t_ in snap_list[:i_]):
            s_['id'] += '-reissue' + s_['v2_scored_utc'][11:16].replace(':', ''); tl = pd.Timestamp(s_['v2_scored_utc']).tz_convert('Australia/Brisbane')
            s_['label'] += f" - re-issued {tl.strftime('%-I:%M%p').lower()} Brisbane"; notes.append(f"Ratings re-issued at {tl.strftime('%-I:%M%p').lower()} Brisbane on the same fields; the earlier set is kept on file.")
    meetings.append({'id': track.lower(), 'name': track, 'state': st, 'tz': tz, 'model_family': fam, 'engine_release': m2.get('engine_release') or ENGINE_VERSION, 'rated': True, 'status': 'rated', 'notes': notes,
                     'conditions': {k_: (re.sub(r'Riders$', '', v_).strip() if isinstance(v_, str) else v_) for k_, v_ in {'going': cond.get('track_condition'), 'rail': cond.get('rail'), 'weather': cond.get('weather_text') or cond.get('weather'), 'rainfall': cond.get('rainfall'),
                                    'penetrometer': cond.get('penetrometer') or None, 'updated': cond.get('conditions_updated') or cond.get('track_information'), 'scratchings_close': cond.get('scratchings_close'),
                                    'scratchings_published': cond.get('scratchings_last_published')}.items()},
                     'sectionals': fam == 'QLD', 'snapshots': snap_list, 'default_snapshot': snap_list[-1]['id'], 'races': races,
                     'provenance': {'engine_release': m2.get('engine_release'), 'v2_prediction_file': ix.file, 'v2_prediction_sha256': sha(ix.file)[:16], 'v1_prediction_sha256': m2['base_v1_sha256'][:16], 'engine_manifest_sha256': m2['engine_manifest_sha256'][:16], 'history_to': m2['history_max_date']}})
# ---- meetings whose fields were collected but whose horses lack enough history to rate: shown as fields only ----
import glob
CAL = json.load(open(f'collect/national/{D}/calendar.json')) if os.path.exists(f'collect/national/{D}/calendar.json') else {'meetings': []}
FO = sorted(glob.glob(f'collect/national/{D}/fields_*.json')); rated_names = {m['name'] for m in meetings}
REASON = {'NT': 'We hold no Northern Territory results history yet'}   # SA, WA, TAS history added 25 Nov 2026 (database master-2026-11-23-sa-wa-tas); unrated meetings there fall back to the general reason
if FO:
    for name, s_ in json.load(open(FO[-1])).items():
        if name in rated_names: continue
        F_ = pd.DataFrame(s_['fields']); scr_ = {(x['race_no'], h['saddlecloth']) for x in s_['scratchings'] for h in x['horses']}; tz_ = s_.get('tz', 'AEDT'); races_ = []
        for rn, g in F_.groupby('race_no'):
            fr = g.iloc[0]; t_local, t_bris = tm(fr.start_time, tz_); rr = []
            for _, h in g.sort_values('saddlecloth').iterrows():
                hk = S.nk(h.horse); stt = 'scratched' if (rn, h.saddlecloth) in scr_ else ('scratched (TAB)' if TABS.get((name, int(rn), int(h.saddlecloth)), 'Open') != 'Open' else ('probable emergency' if h.emergency else 'runner'))
                rr.append({'n': int(h.saddlecloth), 'horse': nice(h.horse), 'barrier': int(h.barrier), 'weight': float(h.weight_kg), 'claim': None if pd.isna(h.claim_kg) else float(h.claim_kg),
                           'jockey': h.jockey if isinstance(h.jockey, str) else None, 'trainer': h.trainer, 'age_sex': h.age_sex if isinstance(h.age_sex, str) else None, 'status': stt, 'history_runs': int(runs.get(hk, 0)),
                           'market': mkt(name, int(rn), int(h.saddlecloth))})
            act = [x for x in rr if x['status'] == 'runner']; cov = sum(1 for x in act if x['history_runs'] > 0)
            races_.append({'no': int(rn), 'name': clean_name(fr.race_name), 'class': fr.get('class_text'), 'distance_m': int(fr.distance_m), 'time': t_local, 'tz': tz_, 'time_brisbane_min': t_bris,
                           'field': len(act), 'label': 'Not rated', 'coverage': {'runners': len(act), 'with_history': cov}, 'runners': rr})
        meetings.append({'id': name.lower(), 'name': name, 'state': s_['state'], 'tz': tz_, 'rated': False, 'status': 'fields only',
                         'reason': REASON.get(s_['state'], 'Too few of these horses have runs in our history') + ". The races are shown with full fields but are not rated. Each race shows how many runners have any history with us.",
                         'notes': ['Fields source: ' + s_['source'] + '.', 'Emergencies are not labelled by this source: runners listed after the weight-ordered field are shown as probable emergencies.'],
                         'conditions': {'going': None}, 'races': races_,
                         'snapshots': [{'id': s_['retrieved_utc'], 'label': 'Fields only (not rated)', 'kind': 'fields-only', 'fields_captured_utc': s_['retrieved_utc']}], 'default_snapshot': s_['retrieved_utc']})
for m_ in meetings: m_['tab_code'] = next((c.get('tab_code') for c in CAL['meetings'] if c['name'] == m_['name']), None)
order = {m['name']: i for i, m in enumerate(CAL['meetings'])}; meetings.sort(key=lambda m: (min(r['time_brisbane_min'] or 9999 for r in m['races']), order.get(m['name'], 99)))
# ---- completeness against the national calendar ----
comp = []
for c_ in CAL['meetings']:
    m_ = next((m for m in meetings if m['name'] == c_['name']), None); rs = m_['races'] if m_ else []
    nr = sum(len([x for x in r['runners'] if x.get('status', 'runner') == 'runner']) for r in rs) if m_ else 0
    pr = sum(1 for r in rs for x in r['runners'] if (x.get('market') or {}).get('fixed_win'))
    miss = []
    if not m_: miss.append('fields not collected')
    elif len(rs) < c_['races']: miss.append(f"{c_['races'] - len(rs)} race(s) without fields")
    if c_.get('races_not_read'): miss.append('listed by TAB but racecard not read (not rated): R' + ', R'.join(map(str, c_['races_not_read'])))   # from the run's RACES lines (27 Nov 2026)
    if m_ and not m_['rated']: miss.append('not rated (no ' + c_['state'] + ' results history yet)')
    nof = [r['no'] for r in rs if not TABR.get((c_['name'], r['no']), {}).get('has_fixed_odds', True)]
    if nof: miss.append('TAB fixed odds not offered at last check: R' + ', R'.join(map(str, nof)))
    if not pr and not nof: miss.append('no TAB prices matched')
    comp.append({'meeting': c_['name'], 'state': c_['state'], 'races_expected': len(c_['races_listed']) if c_.get('races_listed') else c_['races'], 'races_collected': len(rs), 'runners': nr, 'fields_source': c_['fields_source'],
                 'fields': bool(m_), 'prices': pr, 'races_rated': len(rs) if (m_ and m_['rated']) else 0, 'issues': miss})
# leaderboard: every qualified runner ordered by calibrated win chance (comparable across races)
lb = sorted([r for r in all_runners if r['qualified']], key=lambda r: -r['cal'])
for i, r in enumerate(lb): r['day_rank'] = i + 1
# ---- measured tracking history of today's runners, for inspection (display only; Damo 27 Nov 2026). Never fatal. ----
TRACKING = {'note': 'Tracked runs are shown for inspection. Only Queensland tracking feeds a model (the Queensland engine\'s closing-sectional and race-shape inputs); SA and Victorian tracking are not model inputs. Horses are matched by name, as the ratings are.'}
try:
    from engine import tracking_view as TV
    TRK, TRACKING['tables_present'] = TV.history('../history/history.duckdb', [h['horse'] for m in meetings for r in m.get('races', []) for h in r.get('runners', [])], DATE)
    for m in meetings:
        held, nrun, tot = {}, 0, 0
        for r in m.get('races', []):
            for h in r.get('runners', []):
                tot += 1; t_ = TRK.get(TV.nk(h['horse'])); h['tracking'] = t_ or {'held': {}, 'runs': []}
                if t_:
                    nrun += 1
                    for s__ in t_['held']: held[s__] = held.get(s__, 0) + 1
        m['tracking'] = {'runners': tot, 'with_tracked_runs': nrun, 'by_state': held, 'model_uses_sectionals': m.get('model_family') == 'QLD'}
except Exception as ex_:
    TRACKING['error'] = str(ex_)[:200]; print('WARNING tracking view skipped (display only):', str(ex_)[:200])
# ---- Engine Performance tab (display only; reuses the release lineage and the prospective evaluation ledger). Never fatal. ----
try:
    from engine import engine_performance as EP
    ENGINE_PERF = EP.build(D)
except Exception as ex_:
    ENGINE_PERF = {'error': str(ex_)[:200]}; print('WARNING engine performance skipped (display only):', str(ex_)[:200])
V = lambda f: pd.read_csv(f'engine/out/{f}')
q, n_ = V('v2_qld.csv'), V('v2_nat.csv'); qr, nr = V('v2_qld_rolling.csv'), V('v2_nat_rolling.csv'); ad = V('additivity.csv')
def chain(T, first_label, first):
    rows = [first] + [{'version': r.model.replace('+ ', '+ '), 'fit': r['fit_%'], 'top_pick': r['top_pick_%'], 'top3': r['winner_in_top3_%'], 'step_gain': r.step_lp, 'step_lo': r.step_lp_lo, 'step_hi': r.step_lp_hi} for _, r in T[T.kind == 'cumulative'].iterrows()]
    return rows
ab = V('ablation_qld.csv'); base_q = ab[ab.set == 'Ability & opposition rating'].iloc[0]; full_q = ab[ab.kind == 'full'].iloc[0]
OPSF = f'ops/status_{D}.json'; OPS_STATUS = json.load(open(OPSF))['items'] if os.path.exists(OPSF) else []
MARKETS = json.load(open(OPSF)).get('markets') if os.path.exists(OPSF) else None
MARKETS = {**(MARKETS or {}), 'quotes': len(QUOTES), 'runners_priced': len(MKT)}
upd = [x for m in meetings for s_ in m['snapshots'] for x in [s_.get('fields_captured_utc'), s_.get('v2_scored_utc')] if x]
FRESH = {'latest_update_utc': max(upd) if upd else None, 'exported_utc': NOW.isoformat(), 'stale_after_min': 90,
         'per_meeting': [{'meeting': m['name'], 'fields_captured_utc': next(s_ for s_ in m['snapshots'] if s_['id'] == m['default_snapshot'])['fields_captured_utc'],
                          'kind': next(s_ for s_ in m['snapshots'] if s_['id'] == m['default_snapshot'])['label']} for m in meetings]}
sel = []
for m in meetings:
    if not m['rated']: continue
    for r in m['races']:
        h = r['runners'][0]
        cut_ = pd.Timestamp(DATE + 'T00:00:00+10:00') + pd.Timedelta(minutes=(r['time_brisbane_min'] or 0) - 5)
        qs_ = [q for q in QUOTES if q['kind'] == 'fixed_win' and (q['meeting'], q['race_no'], q['saddlecloth']) == (m['name'], r['no'], h['n']) and pd.Timestamp(q['captured_utc']) <= cut_]
        qq_ = max(qs_, key=lambda q: q['captured_utc']) if qs_ else None
        sel.append({'meeting': m['name'], 'state': m['state'], 'race': r['no'], 'time': r['time'], 'tz': r['tz'], 'horse': h['horse'], 'n': h['n'], 'model_version': m.get('engine_release') or ENGINE_VERSION,   # per meeting (26 Nov fix: Qld meetings were labelled v2.2)
                    'rank': 1, 'win_chance': h['cal'], 'classification': r['label'], 'price': qq_ and qq_['price'], 'price_source': qq_ and 'TAB fixed win', 'price_time_utc': qq_ and qq_['captured_utc'], 'result': None, 'settlement': 'pending'})
ROI = {'status': 'waiting', 'selections': sel,
       'rules': ['A selection is the top-rated runner in the latest prediction saved before the race starts. It is frozen at that point and never re-created after the race.',
                 'The quoted price is the last price captured from a named source at or before 5 minutes before the scheduled start, stored with its source and time. TAB fixed odds and Betfair exchange prices are kept separate and never mixed.',
                 'Paper return: 1 unit to win at the quoted price. Selections with no quoted price are listed but excluded from paper returns (and counted).',
                 'Scratchings: a scratched selection is void (stake returned). Late-scratching deductions on fixed-odds winners are applied as published by the bookmaker; on Betfair, the exchange reduction factor is applied.',
                 'Betfair returns are shown after commission on net winnings, at the rate recorded with the quote.',
                 'Realised returns are only bets you actually placed and record yourself. They are never mixed with paper returns. Nothing here places bets.'],
       'paper': {'selections': len(sel), 'priced': sum(1 for x in sel if x['price']), 'settled': 0}, 'realised': {'bets': 0}, 'groups': []}
data = {'contract': {'name': 'racing-intelligence.daily', 'version': '1.0'}, 'date': DATE, 'weekday': pd.Timestamp(DATE).strftime('%A'), 'exported_utc': NOW.isoformat(),
        'snapshot_note': 'Read-only snapshot, republished after each successful refresh. Built only from predictions saved before racing.',
        'engine': {'operational': ENGINE_VERSION + ('; Queensland: ' + sorted({m['engine_release'] for m in meetings if m.get('rated') and m.get('model_family') == 'QLD'})[0] if any(m.get('rated') and m.get('model_family') == 'QLD' for m in meetings) else ''), 'release_note': RELEASE_NOTE, 'released_utc': MAN['released_utc'], 'previous': 'Previous engines (Engine v2.2 six states, Engine v2.1.1 Queensland) are scored every day as shadows from 27 Nov 2026; Engine v1 remains the first layer of every engine',
                   'scale': 'Ratings are kg-equivalent: model score divided by the score that 1 kg of opposition-aware rating is worth on average (Qld {:.3f}, NSW/Vic {:.3f} per kg). They are relative to the average runner in the race. Contributions use the same divisor and add up to the rating.'.format(KG_USED.get('QLD', MAN['families']['QLD']['score_per_kg_total']), KG_USED.get('NAT', MAN['families']['NSW_VIC_ACT']['score_per_kg_total'])) + ((' From 27 Nov 2026 (Engine v2.3) the NSW/Vic/ACT/SA/WA/Tas scale is {:.3f} per kg (Engine v2.2: {:.3f}), so the same performance reads about {:.0f}% smaller in kg: a change of units, not of ability. Compare kg ratings within one engine only.'.format(KG_USED['NAT'], MAN['families']['NSW_VIC_ACT']['score_per_kg_total'], 100 * (1 - MAN['families']['NSW_VIC_ACT']['score_per_kg_total'] / KG_USED['NAT']))) if KG_USED.get('NAT') and abs(KG_USED['NAT'] - MAN['families']['NSW_VIC_ACT']['score_per_kg_total']) > 1e-9 else ''),
                   'calibration': {k: {'races': v['races'], 'runners': v['runners'], 'top_pick_tiers': v['top_pick_tiers_2025_26'], 'terciles': v['top_pick_terciles'], 'deciles': v['deciles']} for k, v in {k_: CAL_USED.get(k_, v_) for k_, v_ in RC['families'].items()}.items()}},
        'meetings': meetings, 'leaderboard': lb,
        'validation': {'qld_chain': [{'version': 'Original combined model', 'fit': base_q['fit_%'], 'top_pick': base_q['top_pick_%'], 'top3': base_q['winner_in_top3_%']}] + [
                           {'version': 'Engine v1 (+ opposition-aware rating)', 'fit': full_q['fit_%'], 'top_pick': full_q['top_pick_%'], 'top3': full_q['winner_in_top3_%']}] + [
                           {'version': r.model, 'fit': r['fit_%'], 'top_pick': r['top_pick_%'], 'top3': r['winner_in_top3_%'], 'step_gain': r.step_lp, 'step_lo': r.step_lp_lo, 'step_hi': r.step_lp_hi} for _, r in q[q.kind == 'cumulative'].head(2).iterrows()],
                       'nat_chain': [{'version': 'Engine v1 (nat_v2)', 'fit': n_[n_.kind == 'version'].iloc[0]['fit_%'], 'top_pick': n_[n_.kind == 'version'].iloc[0]['top_pick_%'], 'top3': n_[n_.kind == 'version'].iloc[0]['winner_in_top3_%']}] + [
                           {'version': r.model, 'fit': r['fit_%'], 'top_pick': r['top_pick_%'], 'top3': r['winner_in_top3_%'], 'step_gain': r.step_lp, 'step_lo': r.step_lp_lo, 'step_hi': r.step_lp_hi} for _, r in n_[n_.kind == 'cumulative'].iterrows()],
                       'rolling': {'qld': qr[['test_year', 'v1 top_pick_%', 'v2 top_pick_%', 'gain_lp', 'gain_lp_lo', 'gain_lp_hi']].to_dict('records'), 'nat': nr[['test_year', 'v1 top_pick_%', 'v2 top_pick_%', 'gain_lp', 'gain_lp_lo', 'gain_lp_hi']].to_dict('records')},
                       'additivity': ad[['model', 'family alone on top of v1', 'gain_lp']].dropna().to_dict('records'),
                       'races': {'qld': 4730, 'nat': 16489}, 'period': '2025-01-01 to 2026-11-23 (out-of-sample for the fitted coefficients)',
                       'caveats': ['Historical research results, not live performance.', '2025-26 races were examined by earlier research batches, so they are not an untouched holdout.',
                                   'One Qld feature family was dropped after seeing it hurt on 2025-26.', 'Raw model chances are over-confident at the top; the calibrated win chance corrects this.']},
        'markets': MARKETS, 'completeness': {'calendar_source': CAL.get('source'), 'excluded': CAL.get('excluded'), 'act_nt': CAL.get('act_nt'), 'rows': comp},
        'freshness': FRESH, 'roi': ROI,
        'results': {'status': 'waiting', 'message': 'No results have been evaluated yet. These races are run on ' + pd.Timestamp(DATE).strftime('%a %d %b') + '; the evaluation of the saved predictions (production, previous engines and shadow candidates on the same races) is scheduled for the next morning.'},
        'operations': OPS_STATUS, 'engine_performance': ENGINE_PERF, 'tracking': TRACKING}
def _clean(o):
    if isinstance(o, dict): return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, list): return [_clean(v) for v in o]
    if isinstance(o, float) and o != o: return None
    return o
data = _clean(data)
os.makedirs('ui/data', exist_ok=True); out = f'ui/data/racing_{DATE}.json'
if os.path.exists(out):
    try:
        _prev = json.load(open(out))
        if 'history' in _prev and 'history' not in data: data['history'] = _prev['history']   # written by ops/settle_yesterday.py; a re-export keeps it (27 Nov 2026 fix)
    except Exception: pass
json.dump(data, open(out + '.tmp', 'w'), separators=(',', ':'), allow_nan=False, default=lambda o: None if isinstance(o, float) and o != o else (int(o) if isinstance(o, (np.integer,)) else float(o) if isinstance(o, np.floating) else str(o)))
os.replace(out + '.tmp', out)                                                  # atomic: a failed export never leaves a half-written day file
idx = {'contract': data['contract'], 'days': sorted({*([d['date'] for d in json.load(open('ui/data/index.json'))['days']] if os.path.exists('ui/data/index.json') else []), DATE}, reverse=True)}
idx['days'] = [{'date': d, 'file': f'racing_{d}.json'} for d in idx['days']]; json.dump(idx, open('ui/data/index.json', 'w'), indent=1)
print('written', out, os.path.getsize(out), 'bytes |', sum(len(m['races']) for m in meetings), 'races |', len(all_runners), 'runners |', len(lb), 'qualified')
for r in lb[:12]: print(r['day_rank'], r['meeting'], r['race'], r['horse'], r['cal'], r['class'], r['rank'])
