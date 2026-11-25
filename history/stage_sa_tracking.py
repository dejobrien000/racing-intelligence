"""Stage Racing SA tracking (tripleSdata sectional reports) into a SEPARATE DuckDB with the Queensland tracking tables' shape.
Never touches the master database (read-only, for checks) and is never read by production.
Usage: python3 stage_sa_tracking.py <raw dir with files.csv + texts.jsonl.gz> <master history.duckdb> <out staging.duckdb> <report.md>
Tables (columns of the Qld tables first, SA extras after):
  sa_race      = race      (+ slug, venue_pdf, weather, sectional_m, report_created, source_url, sha256)
  sa_starter   = starter   (+ ground_rel_winner_m, top_speed_ms, fastest_section_s, first400_s, bn_*: Breednet cross-check)
  sa_sectional = sectional (+ seg_len_m, col)
  sa_files, sa_race_checks, sa_problems
Conventions as in parse_sectional.py. weight_kg is left empty (Queensland holds allocated weight; Breednet's SA weight is carried
after claims, so it is kept separately as bn_weight_carried_kg rather than mixing definitions). ground_m (absolute ground) is not
published for SA; only ground relative to the winner is."""
import csv, gzip, json, os, re, sys, statistics
import duckdb, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'collect', 'racingsa')); import parse_sectional as PS
RAW, MASTER, OUTDB, REPORT = sys.argv[1:5]
files = pd.read_csv(os.path.join(RAW, 'files.csv'), dtype=str).drop_duplicates('url', keep='last')
texts = {}
with gzip.open(os.path.join(RAW, 'texts.jsonl.gz'), 'rt') as fh:
    for line in fh:
        try: j = json.loads(line)
        except json.JSONDecodeError: continue          # a line cut by the time limit
        texts[j['url']] = j
M = duckdb.connect(MASTER, read_only=True)
bn = M.execute("""select r.meeting_date::varchar d, r.slug, r.race_no, r.saddlecloth, r.name_key, r.finish_pos, r.margin_l, r.weight_kg, r.horse, r.pos_raw
                  from bn_runner r join bn_meeting m using (meeting_date, slug) where m.state='SA' and r.meeting_date >= '2023-12-01'""").fetchdf()
bnr = M.execute("select meeting_date::varchar d, slug, race_no, distance_m from bn_race r join bn_meeting m using (meeting_date, slug) where m.state='SA'").fetchdf()
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\((?:[A-Z]{2,3})\)\s*$', '', str(s).upper()))
def track_of(venue, slug):
    v = (venue or '').lower()
    if 'parks' in v: return 'Morphettville_Parks', 'morphettville-parks'
    if 'morphettville' in v: return 'Morphettville', 'morphettville'
    if 'murray bridge' in v: return 'Murray_Bridge', 'murray-bridge-gh'
    if 'gawler' in v: return 'Gawler', 'gawler'
    return re.sub(r'\W+', '_', venue or slug).strip('_'), slug
RACE, ST, SEC, CHK, PROB = [], [], [], [], []
ok_files = files[files.status == '200']
for _, f in ok_files.iterrows():
    t = texts.get(f.url)
    if not t: PROB.append({'url': f.url, 'problem': 'no text kept'}); continue
    race, runners, segs, probs = PS.parse(t['pages'])
    for p in probs: PROB.append({'url': f.url, 'problem': p})
    if not race.get('date_text') or not runners: continue
    dd = pd.to_datetime(race['date_text'], format='%d %b %Y').date()
    if str(dd) != f.meeting_date: PROB.append({'url': f.url, 'problem': f'date in report {dd} != requested {f.meeting_date}'}); continue
    trk, slug = track_of(race.get('venue'), f.slug)
    rid = f"{dd.strftime('%Y%m%d')}-{trk}-R{race['race_no']}"
    RACE.append({'meeting_date': dd, 'track': trk, 'race_no': race['race_no'], 'race_id': rid, 'race_name': race.get('race_name'), 'distance_m': race.get('distance_m'),
                 'start_time': race.get('start_time'), 'track_rating_tracking': race.get('track_rating'), 'rail': race.get('rail'), 'meeting_code': None, 'race_code': None,
                 'race_time_s': race.get('race_time_s'), 'slug': slug, 'venue_pdf': race.get('venue'), 'weather': race.get('weather'), 'sectional_m': race.get('sectional_m'),
                 'report_created': race.get('report_created'), 'source_url': f.url, 'sha256': f.sha256})
    b = bn[(bn.d == f.meeting_date) & (bn.slug == slug) & (bn.race_no == race['race_no'])].set_index('saddlecloth')
    bd = bnr[(bnr.d == f.meeting_date) & (bnr.slug == slug) & (bnr.race_no == race['race_no'])].distance_m
    sg = pd.DataFrame(segs)
    nmatch = npos = 0; split_ok = []; pos_disagree = 0
    for r in runners:
        sc = r['saddlecloth']; br = b.loc[sc] if sc in b.index else None
        if isinstance(br, pd.DataFrame): br = br.iloc[0]
        mt = br is not None and nk(br.horse) == nk(r['horse'])
        fp = int(r['finish_pos_text']) if str(r.get('finish_pos_text', '')).isdigit() else None
        nmatch += mt
        if mt and fp is not None and br.finish_pos == fp: npos += 1
        elif mt and fp is not None: pos_disagree += 1
        rs = sg[sg.saddlecloth == sc] if len(sg) else sg
        if len(rs) and r.get('finish_time_s') and rs.split_s.notna().all(): split_ok.append(abs(rs.split_s.sum() - r['finish_time_s']) <= 0.06)
        ST.append({'meeting_date': dd, 'track': trk, 'race_no': race['race_no'], 'race_id': rid, 'saddlecloth': sc, 'name': r['horse'].title(), 'name_key': nk(r['horse']),
                   'horse_code': None, 'scratched': False, 'finish_pos': fp, 'margin_l': r.get('margin_l'), 'finish_time_s': r.get('finish_time_s'), 'ground_m': None,
                   'result_state': r.get('race_state') or ('Finished' if fp else None), 'result_substate': None if fp else r.get('finish_pos_text'), 'barrier': r.get('barrier'),
                   'weight_kg': None, 'jockey': r.get('jockey'), 'trainer': br.trainer if mt and 'trainer' in br else None, 'emergency': None, 'name_fields': r['horse'],
                   'ground_rel_winner_m': r.get('ground_rel_winner_m'), 'top_speed_ms': round(r['top_speed_kmh'] / 3.6, 3) if r.get('top_speed_kmh') else None,
                   'fastest_section_s': r.get('fastest_section_s'), 'first400_s': r.get('first400_s'), 'bn_match': bool(mt),
                   'bn_finish_pos': int(br.finish_pos) if mt and pd.notna(br.finish_pos) else None, 'bn_margin_l': float(br.margin_l) if mt and pd.notna(br.margin_l) else None,
                   'bn_weight_carried_kg': float(br.weight_kg) if mt and pd.notna(br.weight_kg) else None})
    for s in segs:
        SEC.append({'race_id': rid, 'saddlecloth': s['saddlecloth'], 'segment_end_m': s['segment_end_m'], 'ground_m': None, 'position': s['position'], 'inter_s': s['inter_s'],
                    'split_s': s['split_s'], 'avg_speed_ms': s['avg_speed_ms'], 'top_speed_ms': s['top_speed_ms'], 'stride_freq_hz': s['stride_freq_hz'],
                    'stride_len_m': s['stride_len_m'], 'dist_to_rail_m': s['dist_to_rail_m'], 'seg_len_m': s['seg_len_m'], 'col': s['col']})
    # checks
    perm_ok = True
    if len(sg):
        for col, g in sg.groupby('col'):
            p = sorted(x for x in g.position if pd.notna(x))
            if p and p != list(range(1, len(p) + 1)): perm_ok = False
        st = sg.dropna(subset=['avg_speed_ms', 'stride_freq_hz', 'stride_len_m']); st = st[(st.seg_len_m >= 200) & (st.avg_speed_ms > 0)]
        stride_err = float((abs(st.stride_freq_hz * st.stride_len_m - st.avg_speed_ms) / st.avg_speed_ms).median()) if len(st) else None
    else: stride_err = None
    win = next((r for r in runners if r.get('finish_pos_text') == '1'), None)
    CHK.append({'race_id': rid, 'url': f.url, 'runners': len(runners), 'runners_with_segments': sg.saddlecloth.nunique() if len(sg) else 0,
                'bn_runners': len(b), 'bn_name_matched': nmatch, 'bn_finish_agree': npos, 'bn_finish_disagree': pos_disagree,
                'distance_pdf': race.get('distance_m'), 'distance_bn': int(bd.iloc[0]) if len(bd) else None,
                'split_sum_ok_share': round(sum(split_ok) / len(split_ok), 3) if split_ok else None, 'positions_ok': perm_ok,
                'stride_median_rel_err': round(stride_err, 4) if stride_err is not None else None,
                'winner_time_eq_race_time': (abs(win['finish_time_s'] - race['race_time_s']) < 0.011) if (win and win.get('finish_time_s') and race.get('race_time_s')) else None,
                'parse_problems': sum(1 for p in PROB if p['url'] == f.url)})
C = pd.DataFrame(CHK)
if len(C):
    C['pass'] = ((C.bn_name_matched == C.runners) & (C.bn_finish_disagree == 0) & (C.distance_pdf == C.distance_bn) & C.positions_ok.astype(bool)
                 & (C.split_sum_ok_share.fillna(0) >= 0.9) & (C.parse_problems == 0) & (C.runners_with_segments == C.runners))
os.makedirs(os.path.dirname(OUTDB) or '.', exist_ok=True)
if os.path.exists(OUTDB): os.remove(OUTDB)
D = duckdb.connect(OUTDB)
for name, rows in [('sa_race', RACE), ('sa_starter', ST), ('sa_sectional', SEC), ('sa_race_checks', CHK and C.to_dict('records')), ('sa_problems', PROB)]:
    df = pd.DataFrame(rows or [])
    if len(df): D.register('df', df); D.execute(f'create table {name} as select * from df'); D.unregister('df')
D.register('df', files); D.execute('create table sa_files as select * from df'); D.unregister('df')
# drop races that appear twice (same race_id from two files) keeping the first, and flag
dups = D.execute('select race_id, count(*) n from sa_race group by 1 having n > 1').fetchdf() if RACE else pd.DataFrame()
D.close()
# report
F = files; cal = pd.read_csv(os.path.join(os.path.dirname(__file__), '..', 'collect', 'racingsa', 'sa_meetings.csv'))
lines = ['# Racing SA tracking staging report', '', f'Built {pd.Timestamp.utcnow():%Y-%m-%d %H:%M}Z from {RAW}. Staging only: not in the master database, not read by production.', '']
lines += [f'- Files requested {len(F)}; found (200) {int((F.status == "200").sum())}; not found {int(F.status.isin(["403", "404"]).sum())}; other {int((~F.status.isin(["200", "403", "404"])).sum())}']
if len(C):
    lines += [f'- Races staged {len(C)}; runners {len(ST)}; 200 m segments {len(SEC)}',
              f'- Races passing every check {int(C["pass"].sum())} ({100 * C["pass"].mean():.1f}%)',
              f'- Breednet name match {int(C.bn_name_matched.sum())}/{int(C.runners.sum())} runners; finishing position agrees {int(C.bn_finish_agree.sum())}, disagrees {int(C.bn_finish_disagree.sum())}',
              f'- Distance agrees with Breednet in {int((C.distance_pdf == C.distance_bn).sum())}/{len(C)} races',
              f'- Splits add up to the runner\'s time (within 0.06 s) for {C.split_sum_ok_share.mean() * 100:.1f}% of runners (race average)',
              f'- Positions form 1..n at every section in {int(C.positions_ok.sum())}/{len(C)} races',
              f'- Stride frequency x length vs average speed: median relative error {C.stride_median_rel_err.median():.3f} (Qld: 0.013)',
              f'- Duplicate race ids: {len(dups)}', '']
    R = pd.DataFrame(RACE); R['month'] = pd.to_datetime(R.meeting_date).dt.to_period('M').astype(str)
    cov = R.groupby(['track', 'month']).size().unstack(0).fillna(0).astype(int)
    lines += ['## Coverage (races staged by month and track)', '', cov.to_markdown(), '']
    ff = F[F.race_no == '1'].copy(); ff['found'] = ff.status == '200'
    m1 = ff.groupby('slug').agg(meetings_asked=('found', 'size'), meetings_found=('found', 'sum'))
    lines += ['## Meetings found per club (race 1 asked)', '', m1.to_markdown(), '']
    lines += ['## Clubs not collected (report folder unknown)', '', ', '.join(sorted(set(cal.slug) - set(m1.index))), '']
    bad = C[~C['pass']].head(40)
    lines += ['## Races failing a check (first 40)', '', bad[['race_id', 'runners', 'runners_with_segments', 'bn_name_matched', 'bn_finish_disagree', 'distance_pdf', 'distance_bn',
                                                              'split_sum_ok_share', 'positions_ok', 'parse_problems']].to_markdown(index=False) if len(bad) else 'none', '']
    if PROB: lines += ['## Parse problems (first 30)', ''] + [f"- {p['url'].split('/')[-2]}/{p['url'].split('/')[-1]}: {p['problem']}" for p in PROB[:30]]
open(REPORT, 'w').write('\n'.join(lines) + '\n'); print('\n'.join(lines[:14]))
