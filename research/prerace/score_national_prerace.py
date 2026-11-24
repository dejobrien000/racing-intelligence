"""Genuine pre-race scoring of Racing NSW field snapshots (NSW/ACT; Victorian fields will use the same scorer) with the
FROZEN common-data candidates (benchmarks/candidates_national_common): nat_v1 = form + national figure ability +
fitness + national dynamic rating; nat_v2 = nat_v1 + horse course/going/distance records. No sectionals are used or
invented outside Queensland. Every feature comes from runs before the race date. Write-once outputs as score_prerace.py.
Usage (from research/): python3 prerace/score_national_prerace.py <nsw snapshot.jsonl.gz> ../history/history.duckdb"""
import sys, os, re, json, gzip, hashlib, duckdb, numpy as np, pandas as pd
import dyn_rating as DR, dyn_rating_innov as DI
SNAP, DB = sys.argv[1], sys.argv[2]
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
slug = lambda t: re.sub(r'[^a-z0-9]+', '-', str(t).lower().replace('&', 'and')).strip('-')
man = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = man['dev_sd_after_race_centring']; CANDS = man['candidates']; pn = man['dynamic_rating_params']
scored = pd.Timestamp.now(tz='UTC'); stamp = scored.strftime('%Y%m%dT%H%M%SZ')
snaps = {}
with gzip.open(SNAP, 'rt') as fh:
    for line in fh:
        if line.strip(): o = json.loads(line); snaps[o['key']] = o['value']
latest = {}
for k in sorted(snaps): latest[(snaps[k]['date'], snaps[k]['venue'])] = k
# ---------- history ----------
U = pd.read_parquet('national_runs.parquet')
con = duckdb.connect(DB, read_only=True)
bm = con.execute("select meeting_date, bf_track_slug venue, slug from bn_meeting").fetchdf(); bm['date'] = pd.to_datetime(bm.meeting_date)
NAMEVAR = {'royal-randwick': 'randwick', 'canterbury-park': 'canterbury', 'the-valley': 'moonee-valley', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill', 'beaumont-newcastle': 'beaumont', 'newcastle-beaumont': 'beaumont'}
bm = bm.drop_duplicates(['date', 'venue']); bm['config'] = bm.slug.map(lambda s: NAMEVAR.get(s, s))
U = U.merge(bm[['date', 'venue', 'config']], on=['date', 'venue'], how='left')
qt = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'track']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'})
U = U.merge(qt, on=['q_race_id', 'q_horse_id'], how='left'); U.loc[U.state == 'QLD', 'config'] = U.track; U['config'] = U.config.fillna(U.venue)
cut = {'national results (Qld tracked + Breednet)': str(pd.to_datetime(U.date).max().date())}
D0 = pd.Timestamp(min(snaps[k]['date'] for k in latest.values() if not (len(sys.argv) > 3) or str(snaps[k]['date']).replace('-', '') == sys.argv[3]))
assert pd.to_datetime(U.date).max() < D0, 'history already holds results on/after the race date: not a pre-race run'
# ---------- pre-race rows ----------
METRO = {'randwick', 'rosehill', 'warwick-farm', 'canterbury', 'flemington', 'caulfield', 'moonee-valley', 'sandown'}
PROV = {'newcastle', 'kembla-grange', 'hawkesbury', 'wyong', 'gosford', 'canberra', 'pakenham', 'ballarat', 'geelong', 'cranbourne', 'bendigo', 'mornington', 'kilmore', 'seymour', 'sale', 'werribee', 'yarra-valley', 'moe', 'warrnambool', 'illawarra-grange'}
rows, meta = [], []
ONLY = sys.argv[3] if len(sys.argv) > 3 else None          # optional: score one race date only (YYYYMMDD)
for (date, venue), key in latest.items():
    if ONLY and str(date).replace('-', '') != ONLY: continue
    s = snaps[key]; c = s['conditions']; scr = {(r['race_no'], h['saddlecloth']) for r in s['scratchings'] for h in r['horses']}
    v = slug(venue); md = pd.Timestamp(date)
    for f in s['fields']:
        st = 'scratched' if (f['race_no'], f['saddlecloth']) in scr else ('unnumbered (emergency or late entry; not counted until confirmed)' if f.get('saddlecloth') in (None, '') or f.get('emergency') else 'runner')
        rows.append({**f, 'status': st, 'date': md, 'state': s['state'], 'venue': v, 'config': NAMEVAR.get(v, v), 'snapshot_key': key, 'going_text': c.get('track_condition'), 'rail': c.get('rail')})
    meta.append({'snapshot_key': key, 'date': date, 'venue': venue, 'retrieved_utc': s['retrieved_utc'], 'acceptances_sha256': s['acceptances_sha256'], 'conditions': c,
                 'scratchings_listed': sum(len(r['horses']) for r in s['scratchings'])})
F = pd.DataFrame(rows); R = F[F.status == 'runner'].copy()
R['race'] = R.state + '|' + R.venue + '|' + R.date.dt.strftime('%Y-%m-%d') + '|' + R.race_no.astype(str); R['race_id'] = R.race
R['horse_name'] = R.horse; R['horse'] = R.horse.map(nk); R['field'] = R.groupby('race').saddlecloth.transform('count')
R['tier'] = np.where(R.venue.isin(METRO), 'metro', np.where(R.venue.isin(PROV), 'provincial', 'country'))
gw = R.going_text.fillna('').str.lower(); R['gband'] = np.select([gw.str.contains('heavy'), gw.str.contains('soft'), gw.str.contains('synth|poly')], ['heavy', 'soft', 'synthetic'], 'good')
R['dband'] = pd.cut(R.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
R['period'] = 'prospective'; R['win'] = np.nan; R['finish_pos'] = np.nan; R['margin_l'] = np.nan
# ---------- features for pre-race rows from earlier runs only ----------
H = U[U.horse.isin(R.horse)].copy()
gwh = H.going.fillna('').astype(str).str.lower(); H['gband'] = np.select([gwh.str.contains('heavy'), gwh.str.contains('soft'), gwh.str.contains('synth|poly|awt')], ['heavy', 'soft', 'synthetic'], 'good')
H['dband'] = pd.cut(H.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
wts = np.array([1, 0.7, 0.5, 0.35, 0.25, 0.18])
out = []
for _, r in R.iterrows():
    h = H[(H.horse == r.horse) & (pd.to_datetime(H.date) < r.date)].sort_values(['date', 'race_no'])
    for c_ in ['fpct', 'margin_l', 'fig_n', 'fs', 'finish_pos']: h[c_] = pd.to_numeric(h[c_], errors='coerce').astype(float)
    o = {'race_id': r.race_id, 'horse': r.horse, 'n_prior': len(h)}
    if len(h):
        fp = h.fpct.values; o['f_avgfp3'] = -np.nanmean(fp[-3:]) if np.isfinite(fp[-3:]).any() else np.nan; o['f_lastfp'] = -fp[-1]
        lm = h.margin_l.values[-1]; lm = 0.0 if not np.isfinite(lm) else lm
        o['f_lastlm'] = -np.log(np.clip(lm, 0, 30) + 0.5) if np.isfinite(fp[-1]) else np.nan
        o['f_cwin'] = float((h.finish_pos == 1).sum()) / len(h); o['f_lstarts'] = np.log1p(len(h))
        fg = h.fig_n.values[-6:][::-1]; ok = np.isfinite(fg); o['a_rec'] = float(np.dot(fg[ok], wts[:len(fg)][ok]) / wts[:len(fg)][ok].sum()) if ok.any() else np.nan
        b3 = h.fig_n.values[-3:]; o['a_best3'] = np.nanmax(b3) if np.isfinite(b3).any() else np.nan
        f3 = h.fs.values[-3:]; o['a_fs3'] = np.nanmean(f3) if np.isfinite(f3).any() else np.nan
    out.append(o)
Fe = pd.DataFrame(out); R = R.merge(Fe, on=['race_id', 'horse'], how='left')
R['a_wt_rel'] = R.weight_kg - R.groupby('race_id').weight_kg.transform('mean')
src = [U[['date', 'horse']].assign(src='national results')]
for q_, lab in [("select meeting_date date, name_key from bf_runner where state <> 'NZ'", 'Betfair'), ("select run_date date, name_key from nsw_form_line where not trial", 'Racing NSW form lines')]:
    t = con.execute(q_).fetchdf(); t['horse'] = t.name_key.map(nk); src.append(t[['date', 'horse']].assign(src=lab))
A = pd.concat(src); A['date'] = pd.to_datetime(A.date); A = A[A.horse.isin(R.horse)]
prev = A.merge(R[['horse', 'date']].drop_duplicates().rename(columns={'date': 'rd'}), on='horse'); prev = prev[prev.date < prev.rd].sort_values('date').groupby(['horse', 'rd']).last().reset_index()
R = R.merge(prev.rename(columns={'date': 'prev_date', 'src': 'last_start_source', 'rd': 'date'}), on=['horse', 'date'], how='left')
days = (R.date - R.prev_date).dt.days
R['r_firstup'] = (days >= 60).astype(float); R['r_7_13'] = days.between(7, 13).astype(float); R['r_28_59'] = days.between(28, 59).astype(float)
R['r_quick'] = (days <= 10).astype(float); R['r_ldays'] = np.log(days.clip(7, 365)); R['days_since'] = days
has = R.f_avgfp3.notna(); R['missform'] = (~has).astype(float); R['missfig'] = (has & R.a_rec.isna()).astype(float)
# ---------- national rating and horse records (history + today's fields appended, no result) ----------
UR = pd.DataFrame({'race': R.race, 'horse': R.horse, 'date': R.date, 'finish_pos': np.nan, 'margin_l': np.nan, 'weight_kg': R.weight_kg.astype(float), 'distance_m': R.distance_m.astype(float),
                   'config': R.config, 'gband': R.gband, 'dband': R.dband, 'rid': R.race_id})
UH = U[['race', 'horse', 'date', 'finish_pos', 'margin_l', 'weight_kg', 'distance_m', 'config', 'going']].copy()
gu = UH.going.fillna('').astype(str).str.lower(); UH['gband'] = np.select([gu.str.contains('heavy'), gu.str.contains('soft'), gu.str.contains('synth|poly|awt')], ['heavy', 'soft', 'synthetic'], 'good')
UH['dband'] = pd.cut(UH.distance_m, [0, 1150, 1450, 1750, 9999], labels=['s', 'm', 'mi', 'l']).astype(str)
UN = pd.concat([UH.drop(columns=['going']).assign(rid=None), UR], ignore_index=True); UN['idx'] = np.arange(len(UN)); UN['date'] = pd.to_datetime(UN.date)
dn = pd.DataFrame({'race_key': UN.race, 'horse': UN.horse, 'date': UN.date, 'finish_pos': UN.finish_pos, 'margin_l': UN.margin_l.where(UN.finish_pos != 1, 0.0), 'weight_kg': UN.weight_kg, 'distance_m': UN.distance_m, 'idx': UN.idx})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last')
mu, sdv, inn = DI.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])
UN['dyn_nat'] = pd.Series(mu, index=PN.idx.values).reindex(UN.idx).values; UN['dyn_sd'] = pd.Series(sdv, index=PN.idx.values).reindex(UN.idx).values
UN['innov'] = pd.Series(inn, index=PN.idx.values).reindex(UN.idx).values
UN = UN.sort_values(['horse', 'date', 'race']).reset_index(drop=True)
for key, nm in [('config', 'c_rec'), ('gband', 'g_rec'), ('dband', 'd_rec')]:
    v = UN.innov.fillna(0.0); c = UN.innov.notna().astype(int); grp = [UN.horse, UN[key]]
    UN[nm] = (v.groupby(grp).cumsum() - v) / ((c.groupby(grp).cumsum() - c) + man['records_k']); UN[nm + '_n'] = c.groupby(grp).cumsum() - c
R = R.merge(UN[UN.rid.notna()][['rid', 'horse', 'dyn_nat', 'dyn_sd', 'c_rec', 'g_rec', 'd_rec', 'c_rec_n']].rename(columns={'rid': 'race_id'}), on=['race_id', 'horse'], how='left')
if os.environ.get('DUMP_FEATURES'):                       # engine v2 needs today's raw features; dump them and stop (writes no predictions)
    R.to_parquet(os.environ['DUMP_FEATURES']); print('features dumped', len(R)); sys.exit(0)
# ---------- frozen scores ----------
G = {'Opposition-aware rating': ['dyn_nat'], 'Ability figures': ['a_rec', 'a_best3', 'a_fs3', 'a_wt_rel', 'missfig'], 'Recent form': ['f_avgfp3', 'f_lastfp', 'f_lastlm', 'f_cwin', 'f_lstarts', 'missform'],
     'Fitness and spacing': ['r_firstup', 'r_7_13', 'r_28_59', 'r_quick', 'r_ldays'], 'Horse suits course/going/distance': ['c_rec', 'g_rec', 'd_rec']}
for c in SD: R[c + '_z'] = ((R[c].astype(float) - R.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0)
RW, RC = [], []
for cname, coef in CANDS.items():
    R['_lp'] = sum(coef[c] * R[c + '_z'] for c in coef); R['_score'] = R._lp - R.groupby('race_id')._lp.transform('mean')
    e = np.exp(R._lp - R.groupby('race_id')._lp.transform('max')); R['_p'] = e / e.groupby(R.race_id).transform('sum'); R['_rank'] = R.groupby('race_id')._lp.rank(ascending=False, method='first').astype(int)
    for g_, cs in G.items(): R['_g_' + g_] = sum(coef[c] * R[c + '_z'] for c in cs if c in coef)
    for _, r in R.iterrows():
        gs = {g_: r['_g_' + g_] for g_ in G}; pos = [k for k, v in sorted(gs.items(), key=lambda t: -t[1]) if v > 0.15][:2]; neg = [k for k, v in sorted(gs.items(), key=lambda t: t[1]) if v < -0.15][:1]
        RW.append({'candidate': cname, 'race_id': r.race_id, 'race_no': int(r.race_no), 'saddlecloth': int(r.saddlecloth), 'horse': r.horse_name,
                   'barrier': r.barrier, 'weight_kg': r.weight_kg, 'jockey': r.jockey, 'rank': int(r._rank), 'chance_pct': round(100 * r._p, 2), 'race_relative_score': round(r._score, 4),
                   'rating_kg_national': round(r.dyn_nat, 2) if r.dyn_nat == r.dyn_nat else None, 'rating_sd_kg_national': round(r.dyn_sd, 2) if r.dyn_sd == r.dyn_sd else None,
                   'course_record_kg': round(r.c_rec, 2) if r.c_rec == r.c_rec else None, 'runs_at_course_before': int(r.c_rec_n) if r.c_rec_n == r.c_rec_n else 0,
                   'reasons_plus': '; '.join(pos), 'reasons_minus': '; '.join(neg), 'n_prior_runs_held': int(r.n_prior) if r.n_prior == r.n_prior else 0,
                   'has_prior_form': not bool(r.missform), 'has_figure': not bool(r.missfig) and not bool(r.missform), 'has_sectionals': False, 'has_running_style': False,
                   'days_since': r.days_since if r.days_since == r.days_since else None, 'last_start_source': r.last_start_source, **{'grp_' + k: round(v, 4) for k, v in gs.items()}})
    for rid, g in R.groupby('race_id'):
        pr = np.sort(g._p.values)[::-1]
        RC.append({'candidate': cname, 'race_id': rid, 'runners': len(g), 'top_chance_pct': round(100 * pr[0], 2), 'second_chance_pct': round(100 * pr[1], 2) if len(pr) > 1 else None,
                   'top_two_gap_pts': round(100 * (pr[0] - (pr[1] if len(pr) > 1 else 0)), 2), 'runners_without_prior_form': int(g.missform.sum()), 'going': g.going_text.iloc[0], 'rail': g.rail.iloc[0]})
RW = pd.DataFrame(RW).sort_values(['candidate', 'race_id', 'rank']); RC = pd.DataFrame(RC)
for (date, venue), key in latest.items():
    if ONLY and str(date).replace('-', '') != ONLY: continue
    v = slug(venue); od = os.path.join('prospective', 'prerace', date, venue.replace(' ', '_')); os.makedirs(od, exist_ok=True)
    base = os.path.join(od, f"pred_{key.split(':')[-1]}_{stamp}"); pre = f"{snaps[key]['state']}|{v}|{pd.Timestamp(date).strftime('%Y-%m-%d')}|"
    paths = {'runners': base + '_runners.csv', 'races': base + '_races.csv', 'manifest': base + '_manifest.json'}
    with open(paths['runners'], 'x') as fh: RW[RW.race_id.str.startswith(pre)].to_csv(fh, index=False)
    with open(paths['races'], 'x') as fh: RC[RC.race_id.str.startswith(pre)].to_csv(fh, index=False)
    mf = {'scored_utc': scored.isoformat(), 'snapshot': next(m for m in meta if m['snapshot_key'] == key), 'snapshot_bundle': os.path.basename(SNAP), 'snapshot_bundle_sha256': sha(SNAP),
          'not_scored': F[(F.snapshot_key == key) & (F.status != 'runner')][['race_no', 'saddlecloth', 'horse', 'status']].to_dict('records'), 'candidates': list(CANDS),
          'model_manifest_sha256': sha('benchmarks/candidates_national_common/manifest.json'), 'code_sha256': {f: sha(f) for f in ['prerace/score_national_prerace.py', 'dyn_rating.py', 'dyn_rating_innov.py']},
          'history_cutoff': cut, 'national_runs_sha256': sha('national_runs.parquet'),
          'notes': ['no result of these races existed when this file was written', 'no sectionals or running positions are used outside Queensland',
                    'acceptors with no saddlecloth number (emergencies or late entries) are listed in not_scored and excluded from the field until confirmed']}
    with open(paths['manifest'], 'x') as fh: json.dump(mf, fh, indent=1, default=str)
    new = not os.path.exists('prospective/prerace/INDEX.csv')
    with open('prospective/prerace/INDEX.csv', 'a') as fh:
        if new: fh.write('scored_utc,date,track,snapshot_key,file,sha256\n')
        for kind, pth in paths.items(): fh.write(f"{scored.isoformat()},{date},{venue},{key},{pth},{sha(pth)}\n")
    print('written', base)
print(RW[RW.candidate.str.startswith('nat_v1')].groupby('race_id').head(2)[['race_id', 'rank', 'horse', 'chance_pct', 'reasons_plus', 'n_prior_runs_held', 'rating_kg_national']].to_string(index=False))
