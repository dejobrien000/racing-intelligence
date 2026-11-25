"""Genuine pre-race scoring of a Racing Queensland field snapshot with the FROZEN candidates (never refitted).
Input: a snapshot bundle from collectors/rq_prerace.js (fields, scratchings, conditions, rail as published at the time
of collection). Every feature is built only from runs before the race date; no result of the race exists when this runs.
Output (write-once; an existing file is never overwritten):
  prospective/prerace/<date>/<TRACK>/pred_<snapshot stamp>_<scored stamp>_runners.csv   one row per runner x candidate
  .../pred_<...>_races.csv                                                               one row per race x candidate
  .../pred_<...>_manifest.json   snapshot key + PDF sha256, model manifest hashes, inputs and their cut-off dates
  prospective/prerace/INDEX.csv  append-only log of every prediction file with its sha256
Usage (from research/):  python3 prerace/score_prerace.py <snapshot.jsonl.gz> ../history/history.duckdb [snapshot key]"""
import sys, os, re, json, gzip, shutil, subprocess, hashlib, numpy as np, pandas as pd
HERE = os.getcwd(); SNAP, DB = sys.argv[1], os.path.abspath(sys.argv[2]); WANT = sys.argv[3] if len(sys.argv) > 3 else None
REPLAY = os.environ.get('PRERACE_REPLAY') == '1'   # retrospective replay test: history cut at the race date, output to /tmp only
W = '/tmp/prerace_work' + ('_replay' if REPLAY else ''); os.makedirs(os.path.join(W, 'out'), exist_ok=True)
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
now = lambda: pd.Timestamp.now(tz='UTC')
norm = lambda n: re.sub(r'\s+', ' ', re.sub(r"['’]", '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(n).strip()))).upper()
nk = lambda n: re.sub(r'[^A-Z0-9]', '', norm(n))
# ---------- 1. snapshot ----------
snaps = {}
with gzip.open(SNAP, 'rt') as fh:
    for line in fh:
        if line.strip(): o = json.loads(line); snaps[o['key']] = o['value']
keys = sorted(k for k, v in snaps.items() if v.get('fields'))
if WANT: keys = [WANT]
latest = {}
for k in keys: latest[(snaps[k]['date'], snaps[k]['meeting_code'])] = k          # keys sort by stamp -> last = latest
scored_utc = now(); stamp = scored_utc.strftime('%Y%m%dT%H%M%SZ')
# ---------- 2. history tables (rebuilt from the database: identical development rows to the frozen fit) ----------
for f in ['build_runs.py', 'rating_v0.py', 'features.py', 'inv20_pace_figures.py', 'clogit_tools.py', 'dyn_rating.py']: shutil.copy(f, W)
run = lambda *a: subprocess.run([sys.executable, *a], cwd=W, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
run('build_runs.py', DB, 'runs_hist.parquet')
H = pd.read_parquet(os.path.join(W, 'runs_hist.parquet'))
D0 = pd.Timestamp(min(snaps[k]['date'] for k in latest.values()))
if REPLAY: H = H[pd.to_datetime(H.meeting_date) < D0].copy()
import duckdb
con = duckdb.connect(DB, read_only=True)
src_last = {'Qld tracked': H[['meeting_date', 'name_key']].assign(src='Qld tracked')}
src_last['Betfair (all states)'] = con.execute("select meeting_date, name_key from bf_runner where state <> 'NZ'").fetchdf().assign(src='Betfair (all states)')
src_last['Breednet NSW/Vic/ACT'] = con.execute("select u.meeting_date, u.name_key from bn_runner u join bn_race r using (meeting_date, slug, race_no) where not r.is_trial").fetchdf().assign(src='Breednet NSW/Vic/ACT')
src_last['Racing NSW form lines'] = con.execute("select run_date meeting_date, name_key from nsw_form_line where not trial").fetchdf().assign(src='Racing NSW form lines')
cutoff = {k: str(pd.to_datetime(v.meeting_date).max().date()) for k, v in src_last.items()}
allst = pd.concat(src_last.values()); allst['nk'] = allst.name_key.map(nk); allst['meeting_date'] = pd.to_datetime(allst.meeting_date)
src_build = open('build_runs.py').read()
exec(src_build[src_build.index('def cond(s):'):src_build.index("race[['cond_group','cond_num']]")])
exec(src_build[src_build.index('def cls(n):'):src_build.index("race[['class_group','class_num']]")])
# ---------- 3. pre-race rows ----------
fut, meta = [], []
last_id = H.sort_values('meeting_date').groupby('name_key').horse_id.last()
for (date, code), key in latest.items():
    s = snaps[key]; c = s['conditions']; track = s['track']
    scr = {(r['race_no'], h['saddlecloth']) for r in s['scratchings'] for h in r['horses']}
    # emergencies: before scratchings close they may or may not start (left out, listed); after close, an emergency
    # that has not been scratched has gained a start (Racing Queensland scratches the emergencies that miss out)
    closed = False; sc = (c.get('scratchings_close') or '')
    mm = re.search(r'(\d{2})/(\d{2})/(\d{2}) (\d{1,2}):(\d{2})([ap]m)', sc)
    if mm:
        hh = int(mm.group(4)) % 12 + (12 if mm.group(6) == 'pm' else 0)
        close_local = pd.Timestamp(2000 + int(mm.group(3)), int(mm.group(2)), int(mm.group(1)), hh, int(mm.group(5)), tz='Australia/Brisbane')
        closed = pd.Timestamp(s['retrieved_utc']) >= close_local.tz_convert('UTC')
    for f in s['fields']:
        status = 'scratched' if (f['race_no'], f['saddlecloth']) in scr else ('emergency (pending)' if (f['emergency'] and not closed) else 'runner')
        fut.append({**f, 'status': status, 'date': date, 'track': track, 'snapshot_key': key, 'cond_raw': c.get('track_condition'), 'rail': c.get('rail')})
    meta.append({'snapshot_key': key, 'date': date, 'meeting_code': code, 'track': track, 'retrieved_utc': s['retrieved_utc'], 'fields_pdf_sha256': s['fields_pdf_sha256'], 'after_scratchings_close': bool(closed),
                 'conditions': c, 'scratchings_listed': sum(len(r['horses']) for r in s['scratchings'])})
F = pd.DataFrame(fut)
F['meeting_date'] = pd.to_datetime(F.date).dt.date
F['race_id'] = F.date + '-' + F.track + '-R' + F.race_no.astype(str)
assert not F.race_id.isin(H.race_id).any(), 'pre-race race id already in history: refusing'
if not REPLAY: assert D0 > pd.Timestamp(max(v for v in cutoff.values())), 'a source already holds results on/after the race date: not a pre-race run'
F['name'] = F.horse; F['name_key'] = F.horse.map(norm)
F['horse_id'] = F.name_key.map(last_id); F['matched_history'] = F.horse_id.notna(); F['horse_id'] = F.horse_id.fillna('N:' + F.name_key)
R = F[F.status == 'runner'].copy()
R[['cond_group', 'cond_num']] = R.cond_raw.apply(cond); R['is_poly'] = R.track.str.contains('Poly') | (R.cond_group == 'Synthetic')
R[['class_group', 'class_num']] = R.race_name.apply(cls)
R['field'] = R.groupby('race_id').saddlecloth.transform('count')
R['eff_barrier'] = R.groupby('race_id').barrier.rank(method='first'); R['rel_barrier'] = np.where(R.field > 1, (R.eff_barrier - 1) / (R.field - 1), np.nan)
R['nk'] = R.name.map(nk); md = pd.to_datetime(R.meeting_date)
prev = allst.merge(R[['nk', 'meeting_date']].assign(md=md).drop_duplicates('nk')[['nk', 'md']], on='nk')
prev = prev[prev.meeting_date < prev.md].sort_values('meeting_date').groupby('nk').last()
R['prev_date'] = R.nk.map(prev.meeting_date); R['last_start_source'] = R.nk.map(prev.src)
R['days_since'] = (md - pd.to_datetime(R.prev_date)).dt.days
for col in H.columns:
    if col not in R.columns: R[col] = np.nan
R['scratched'] = False; R['result_state'] = 'PreRace'; R['finished'] = False; R['year'] = md.dt.year; R['split'] = 'prospective'
R['horse_code'] = None; R['race_time_s'] = np.nan
if str(H.meeting_date.dtype).startswith('datetime'): R['meeting_date'] = pd.to_datetime(R.meeting_date)
ALL = pd.concat([H, R[H.columns]], ignore_index=True)
ALL.to_parquet(os.path.join(W, 'runs.parquet'), index=False)
run('rating_v0.py', 'runs.parquet', 'runs_rated_dev.parquet', '--fit-until=2024-12-31')
run('features.py', 'runs_rated_dev.parquet', DB, 'features.parquet'); run('inv20_pace_figures.py', DB)
# ---------- 4. ratings ----------
sys.path.insert(0, W); os.chdir(W)
from clogit_tools import eligible, prep
import dyn_rating as DR
os.chdir(HERE)
man = json.load(open('benchmarks/candidates_b4/manifest.json')); man_n = json.load(open('benchmarks/candidates_b4_national/manifest.json'))
q = ALL; p = man['dynamic_rating_params']
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0
P = DR.prepare(d); P['dyn_mu'], P['dyn_sd'], _ = DR.run(P, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
# national rating: every state's results to their cut-off dates, then today's Qld fields (no result) appended
U = pd.read_parquet('national_runs.parquet')[['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'state', 'q_race_id', 'q_horse_id']]
if REPLAY: U = U[pd.to_datetime(U.date) < D0]
venue = {'Ipswich': 'ipswich', 'Doomben': 'doomben', 'Eagle_Farm': 'eagle-farm', 'Sunshine_Coast': 'sunshine-coast', 'Sunshine_Coast_Poly_Track': 'sunshine-coast',
         'Toowoomba': 'toowoomba', 'Townsville': 'townsville', 'Rockhampton': 'rockhampton', 'Mackay': 'mackay', 'Ladbrokes_Cannon_Park': 'cairns', 'TAB_Park_Gold_Coast': 'gold-coast'}
UR = pd.DataFrame({'race': 'QLD|' + R.track.map(venue).fillna(R.track) + '|' + md.dt.strftime('%Y-%m-%d') + '|' + R.race_no.astype(str), 'horse': R.nk, 'date': md,
                   'finish_pos': np.nan, 'margin_l': np.nan, 'weight_kg': R.weight_kg.astype(float), 'distance_m': R.distance_m.astype(float), 'race_id': R.race_id, 'horse_id': R.horse_id})
# v2.0.1 (25 Nov 2026): history rows keep their Qld ids, so the national rating has a development spread (v2.0 had none -> zero weight live)
UN = pd.concat([U.assign(race_id=U.q_race_id.where(U.state == 'QLD'), horse_id=U.q_horse_id.where(U.state == 'QLD')).drop(columns=['state', 'q_race_id', 'q_horse_id']), UR], ignore_index=True); UN['idx'] = np.arange(len(UN))
dn = pd.DataFrame({'race_key': UN.race, 'horse': UN.horse, 'date': pd.to_datetime(UN.date), 'finish_pos': UN.finish_pos, 'margin_l': UN.margin_l.where(UN.finish_pos != 1, 0.0),
                   'weight_kg': UN.weight_kg, 'distance_m': UN.distance_m, 'idx': UN.idx})
pn = man_n['dynamic_rating_params']; PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, sdv, _ = DR.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
UN['dyn_nat'] = pd.Series(mu, index=PN.idx.values).reindex(UN.idx).values; UN['dyn_nat_sd'] = pd.Series(sdv, index=PN.idx.values).reindex(UN.idx).values
nat = UN[UN.race_id.notna()][['race_id', 'horse_id', 'dyn_nat', 'dyn_nat_sd']]
# ---------- 5. features and frozen scores ----------
X = pd.read_parquet(os.path.join(W, 'features.parquet')).merge(P[['race_id', 'horse_id', 'dyn_mu', 'dyn_sd']], on=['race_id', 'horse_id'], how='left')
X = X.merge(pd.read_parquet(os.path.join(W, 'pace_figures.parquet'))[['race_id', 'horse_id', 'rec_rating_pa1']], on=['race_id', 'horse_id'], how='left')
X = X.merge(nat, on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna(),
             'misspa': has & X.rec_rating_pa1.isna()}.items(): X[k] = v.astype(float)
X['dyn_new'] = (X.dyn_sd >= 0.999 * p['sig0_kg']).astype(float)
cands = {**man['coefficients_per_dev_sd'], 'combined_v1 + national dynamic rating': man_n['coefficients_per_dev_sd']}
cols = sorted({c for m in cands.values() for c in m})
hist = eligible(X[X.period == 'development']); futx = X[X.race_id.isin(R.race_id)].copy(); futx['period'] = 'prospective'
x = prep(pd.concat([hist, futx], ignore_index=True), cols)
# check: development scaling identical to the frozen fit (features rebuilt from the same database rows)
ref = pd.read_parquet('features.parquet'); chk = {c: (float(x.loc[x.period == 'development', c].std()), float(prep(eligible(ref), [c]).loc[lambda t: t.period == 'development', c].std())) for c in ['a_avg3', 'p_relbar', 'f_avgfp3']}
dsd = float(x.loc[x.period == 'development', 'dyn_nat'].sub(x.loc[x.period == 'development'].groupby('race_id').dyn_nat.transform('mean')).std())
fro = json.load(open('benchmarks/engine_v2/manifest.json'))['families']['QLD']['base_feature_dev_sd']['dyn_nat']; chk['dyn_nat'] = (dsd, fro)
if not abs(dsd - fro) <= 0.02 * fro: raise SystemExit(f'national rating scaling check failed: development spread {dsd} vs frozen {fro}; nothing written')
xf = x[x.period == 'prospective'].copy()
G = {'Opposition-aware rating': ['dyn_mu', 'dyn_new', 'dyn_nat'], 'Recent ability figures': ['a_avg3', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig', 'rec_rating_pa1', 'misspa'],
     'Recent form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'], 'Closing sectionals': ['s_gap600_last', 's_gap600_avg3', 's_top3_last', 's_gap200_last', 's_fsp_last', 'misssec'],
     'Barrier and race shape': ['p_style', 'p_leader', 'p_relbar', 'missstyle', 'p_bar_x_style', 'p_lead_x_press', 'p_lone'],
     'Track, distance, going': ['t_trk_starts', 't_trk_win', 't_db_starts', 't_db_win', 't_td_starts', 't_td_win', 't_going', 't_dchange', 't_dchange_abs', 'missgoing'],
     'Fitness and spacing': ['r_debut', 'r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_prep', 'r_ldays']}
info = R.set_index(['race_id', 'horse_id'])
rows, races = [], []
for cname, coef in cands.items():
    z = xf[[c + '_z' for c in coef]].values; lp = z @ np.array(list(coef.values())); xf['_lp'] = lp
    xf['_score'] = xf._lp - xf.groupby('race_id')._lp.transform('mean')
    e = np.exp(xf._lp - xf.groupby('race_id')._lp.transform('max')); xf['_p'] = e / e.groupby(xf.race_id).transform('sum')
    xf['_rank'] = xf.groupby('race_id')._lp.rank(ascending=False, method='first').astype(int)
    for g_, cs in G.items(): xf['_g_' + g_] = sum(coef[c] * xf[c + '_z'] for c in cs if c in coef)
    for _, r in xf.iterrows():
        i = info.loc[(r.race_id, r.horse_id)]
        gs = {g_: r['_g_' + g_] for g_ in G}; pos = [k for k, v in sorted(gs.items(), key=lambda t: -t[1]) if v > 0.15][:2]; neg = [k for k, v in sorted(gs.items(), key=lambda t: t[1]) if v < -0.15][:1]
        rows.append({'candidate': cname, 'race_id': r.race_id, 'race_no': int(i.race_no), 'saddlecloth': int(i.saddlecloth), 'horse': i['name'], 'barrier': i.barrier, 'weight_kg': i.weight_kg,
                     'jockey': i.jockey, 'rank': int(r._rank), 'chance_pct': round(100 * r._p, 2), 'race_relative_score': round(r._score, 4),
                     'rating_kg_qld': round(r.dyn_mu, 2) if r.dyn_mu == r.dyn_mu else None, 'rating_sd_kg_qld': round(r.dyn_sd, 2) if r.dyn_sd == r.dyn_sd else None,
                     'rating_kg_national': round(r.dyn_nat, 2) if r.dyn_nat == r.dyn_nat else None, 'reasons_plus': '; '.join(pos), 'reasons_minus': '; '.join(neg),
                     'matched_history': bool(i.matched_history), 'has_prior_form': not bool(r.missform), 'has_figure': not bool(r.missfig) and not bool(r.missform),
                     'has_sectionals': not bool(r.misssec) and not bool(r.missform), 'has_running_style': not bool(r.missstyle) and not bool(r.missform),
                     'days_since': i.days_since if i.days_since == i.days_since else None, 'last_start_source': i.last_start_source, **{'grp_' + k: round(v, 4) for k, v in gs.items()}})
    for rid, g in xf.groupby('race_id'):
        pr = np.sort(g._p.values)[::-1]
        races.append({'candidate': cname, 'race_id': rid, 'runners': len(g), 'top_chance_pct': round(100 * pr[0], 2), 'second_chance_pct': round(100 * pr[1], 2) if len(pr) > 1 else None,
                      'top_two_gap_pts': round(100 * (pr[0] - (pr[1] if len(pr) > 1 else 0)), 2), 'runners_without_prior_form': int(g.missform.sum()),
                      'runners_new_to_tracked_qld': int((~R[R.race_id == rid].matched_history).sum())})
RW = pd.DataFrame(rows).sort_values(['candidate', 'race_no', 'rank']); RC = pd.DataFrame(races)
# ---------- 6. write once ----------
for (date, code), key in latest.items():
    track = snaps[key]['track']; od = os.path.join('/tmp/prerace_replay' if REPLAY else 'prospective', 'prerace', date, track); os.makedirs(od, exist_ok=True)
    base = os.path.join(od, f"pred_{key.split(':')[-1]}_{stamp}")
    sel = RW.race_id.str.startswith(f'{date}-{track}-')
    paths = {'runners': base + '_runners.csv', 'races': base + '_races.csv', 'manifest': base + '_manifest.json'}
    for kind, df in [('runners', RW[sel]), ('races', RC[RC.race_id.str.startswith(f'{date}-{track}-')])]:
        with open(paths[kind], 'x') as fh: df.to_csv(fh, index=False)
    excl = F[(F.snapshot_key == key) & (F.status != 'runner')][['race_no', 'saddlecloth', 'horse', 'status']].to_dict('records')
    mf = {'scored_utc': scored_utc.isoformat(), 'snapshot': next(m for m in meta if m['snapshot_key'] == key), 'snapshot_bundle': os.path.basename(SNAP), 'snapshot_bundle_sha256': sha(SNAP),
          'not_scored': excl, 'candidates': list(cands), 'model_manifests': {'benchmarks/candidates_b4/manifest.json': sha('benchmarks/candidates_b4/manifest.json'),
          'benchmarks/candidates_b4_national/manifest.json': sha('benchmarks/candidates_b4_national/manifest.json')},
          'code_sha256': {f: sha(f) for f in ['prerace/score_prerace.py', 'build_runs.py', 'rating_v0.py', 'features.py', 'inv20_pace_figures.py', 'dyn_rating.py', 'clogit_tools.py']},
          'history_cutoff_by_source': cutoff, 'national_runs_sha256': sha('national_runs.parquet'), 'scaling_check_dev_sd': chk,
          'notes': ['no result of these races existed when this file was written', 'days since last start uses every source held; Betfair lags about a month',
                    'emergencies and scratched runners at snapshot time are listed in not_scored', 'chance_pct is the frozen model probability; uncertainty: rating_sd_kg, evidence flags, top_two_gap_pts']}
    with open(paths['manifest'], 'x') as fh: json.dump(mf, fh, indent=1, default=str)
    if REPLAY: print('replay output (not a prediction):', base); continue
    new = not os.path.exists('prospective/prerace/INDEX.csv')
    with open('prospective/prerace/INDEX.csv', 'a') as fh:
        if new: fh.write('scored_utc,date,track,snapshot_key,file,sha256\n')
        for kind, pth in paths.items(): fh.write(f"{scored_utc.isoformat()},{date},{track},{key},{pth},{sha(pth)}\n")
    print('written', base, '| races', RC[RC.race_id.str.startswith(f'{date}-{track}-')].race_id.nunique(), '| runners', int(sel.sum()) // len(cands))
print('scaling check (dev sd rebuilt vs frozen):', chk)
print(RW[RW.candidate == 'combined_v1 + national dynamic rating'][['race_no', 'rank', 'saddlecloth', 'horse', 'chance_pct', 'reasons_plus', 'matched_history', 'has_sectionals']].groupby('race_no').head(3).to_string(index=False))
