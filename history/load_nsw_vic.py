"""Load NSW (Racing NSW results pages) and racing.com (NSW + Victoria results) bundles into DuckDB,
then cross-check them against Betfair and each other.

Usage: python3 load_nsw_vic.py <folder with *.jsonl.gz bundles> <history.duckdb>

Bundles are written by the browser collectors:
  racing_nsw_freefields_*.jsonl.gz  one JSON object per Racing NSW meeting page (Results.aspx)
  racing_rc_*.jsonl.gz              one JSON object per racing.com meeting (all races' results pages)
Prices (SP, tote) are never captured by the collectors.
"""
import sys, os, re, gzip, json, glob, duckdb, pandas as pd

folder, dbpath = sys.argv[1], sys.argv[2]

def secs(s):
    if not s: return None
    s = s.strip()
    m = re.fullmatch(r'(?:(\d+):)?(\d+(?:\.\d+)?)', s)
    if not m: return None
    return (int(m.group(1)) * 60 if m.group(1) else 0) + float(m.group(2))

def grab(pat, txt):
    m = re.search(pat, txt or '')
    return m.group(1).strip() if m else None

SHORT = {'NOSE': 0.05, 'SHD': 0.1, 'SHORT HEAD': 0.1, 'HD': 0.2, 'HEAD': 0.2, 'LSHD': 0.15, 'NK': 0.3, 'SNK': 0.25, 'LNK': 0.4, '1/2HD': 0.15, 'DH': 0.0}
def margin_l(s, is_winner):
    if is_winner: return 0.0
    if not s: return None
    s = s.strip().upper()
    if s in SHORT: return SHORT[s]
    m = re.fullmatch(r'([\d.]+)L?', s)
    return float(m.group(1)) if m else None

def ordinal(s):
    m = re.fullmatch(r'(\d+)(ST|ND|RD|TH)?', (s or '').strip().upper())
    return int(m.group(1)) if m else None

def norm_name(s):
    s = re.sub(r'\s*\((NZ|GB|IRE|FR|USA|JPN|GER|AUS|ARG|CHI|BRZ|SAF|ITY|HK)\)\s*$', '', (s or '').upper())
    return re.sub(r'[^A-Z0-9 ]', '', s).strip()

def read_jsonl(pattern):
    """All records from matching bundles; when a key appears in several bundles the latest retrieval wins."""
    best = {}
    for f in sorted(glob.glob(os.path.join(folder, pattern))):
        with gzip.open(f, 'rt', encoding='utf-8') as fh:
            for line in fh:
                if line.strip():
                    o = json.loads(line); o['_bundle'] = os.path.basename(f)
                    v = o.get('value', o)
                    stamp = v.get('retrieved_utc') or max([r.get('retrieved_utc') or '' for r in v.get('races', [])] or ['']) or os.path.basename(f)
                    k = o.get('key') or json.dumps(v.get('key'))
                    if k not in best or stamp >= best[k][0]:
                        best[k] = (stamp, o)
    return [o for _, o in best.values()]

# ---------- Racing NSW results pages ----------
nm, nr, nu = [], [], []
for o in read_jsonl('racing_nsw_freefields_*.jsonl.gz'):
    v = o.get('value', o); key = v['key']
    parts = key.split(',')
    d = pd.to_datetime(parts[0], format='%Y%b%d').date()
    vi = v.get('venue_info', '')
    nm.append({'key': key, 'meeting_date': d, 'state': parts[1], 'venue': parts[2], 'meeting_kind': parts[3] if len(parts) > 3 else 'Professional',
               'meeting_type': grab(r'Meeting Type:\s*(.+?)\s*(?:Snapshot|XML|$)', v.get('page_title', '')),
               'rail': grab(r'Rail Position:\s*(.+?)\s*Dual Track', vi), 'track_condition': grab(r'Track Condition:\s*(.+?)\s*Weather', vi),
               'weather': grab(r'Weather:\s*(.+?)\s*Penetrometer', vi), 'penetrometer': grab(r'Penetrometer:\s*([\d.]+)', vi),
               'results_last_published': grab(r'Results Last Published:\s*(.+?(?:AEDT|AEST))', vi), 'interim': '(interim)' in vi.lower() or v.get('interim', False),
               'n_races': len(v.get('races', [])), 'url': v.get('url'), 'sha256': v.get('sha256'), 'bytes': v.get('bytes'), 'retrieved_utc': v.get('retrieved_utc'), 'bundle': o['_bundle']})
    for r in v.get('races', []):
        t = r.get('title', ''); info = r.get('info', '')
        m = re.match(r'Race (\d+) - (\d{1,2}:\d{2}[AP]M)\s+(.*?)\s*\((\d+) METRES\)', t)
        if not m: continue
        rno = int(m.group(1))
        nr.append({'key': key, 'race_no': rno, 'start_time': m.group(2), 'race_name': m.group(3), 'distance_m': int(m.group(4)),
                   'conditions': grab(r'^(.*?)Track Name:', info), 'track_name': grab(r'Track Name:\s*(.+?)\s*Track Type', info),
                   'track_type': grab(r'Track Type:\s*(.+?)\s*Track Condition', info), 'track_condition': grab(r'Track Condition:\s*(.+?)\s*Time:', info),
                   'race_time_s': secs(grab(r'Time:\s*([\d:.]+)', info)), 'last600_s': secs(grab(r'Last 600m:\s*([\d:.]+)', info)),
                   'timing_method': grab(r'Timing Method:\s*([A-Za-z]+?)(?:Official|$)', info), 'official_comments': grab(r'Official Comments:\s*(.*)$', info)})
        for u in r.get('runners', []):
            fin = u.get('finish', '')
            w = u.get('weight', '')
            wm = re.match(r'([\d.]+)(?:\s*\(cd\s*([\d.]+)\))?', w or '')
            sd = (u.get('sire_dam') or '').split(' / ')
            nu.append({'key': key, 'race_no': rno, 'finish_raw': fin, 'finish_pos': ordinal(fin), 'scratched': 'Scratched' in (u.get('row_class') or ''),
                       'saddlecloth': int(re.match(r'\d+', u['tab']).group()) if re.match(r'\d+', u.get('tab') or '') else None, 'emergency': (u.get('tab') or '').endswith('e'), 'horse': u.get('horse'), 'name_key': norm_name(u.get('horse')),
                       'trainer': u.get('trainer'), 'jockey': u.get('jockey'), 'margin_l': margin_l(u.get('margin'), ordinal(fin) == 1),
                       'barrier': int(u['barrier']) if (u.get('barrier') or '').isdigit() else None,
                       'weight_kg': float(wm.group(1)) if wm else None, 'weight_carried_kg': float(wm.group(2)) if wm and wm.group(2) else (float(wm.group(1)) if wm else None),
                       'penalty_kg': u.get('penalty') or None, 'benchmark': int(u['bmark']) if (u.get('bmark') or '').isdigit() else None,
                       'sire': sd[0] if sd and sd[0] else None, 'dam': sd[1] if len(sd) > 1 else None})

# ---------- racing.com ----------
rm, rr, ru = [], [], []
for o in read_jsonl('racing_rc_*.jsonl.gz'):
    v = o.get('value', o)
    if 'races' not in v: continue
    mk = f"{v['state']}:{v['date']}:{v['slug']}"
    sl = v['slug']
    bft = 'Sandown' if sl.startswith('sandown') else 'Randwick' if sl == 'randwick-kensington' else 'Newcastle' if sl == 'beaumont-newcastle' else \
          ' '.join(w.capitalize() for w in sl.replace('-synthetic', '').split('-'))
    rm.append({'rc_key': mk, 'state': v['state'], 'meeting_date': pd.to_datetime(v['date']).date(), 'slug': v['slug'], 'bf_track': bft, 'n_races': v.get('n_races'),
               'meet_code': v.get('meet_code'), 'bundle': o['_bundle']})
    for r in v['races']:
        h = r.get('head', {})
        rr.append({'rc_key': mk, 'race_no': r['race_no'], 'ok': r.get('ok'), 'race_time_s': secs(h.get('race_time')), 'track_condition': h.get('track_cond'),
                   'rail': h.get('rail'), 'conditions': h.get('conditions'), 'prize': h.get('prize'), 'start_time': h.get('start'),
                   'distance_m': int(h['distance']) if h.get('distance') else None, 'url': r.get('url'), 'text_sha256': r.get('text_sha256'), 'retrieved_utc': r.get('retrieved_utc')})
        for u in r.get('runners', []):
            p = ordinal(u.get('pos'))
            pp = re.match(r'(\d+)\w*/(\d+)\w*', u.get('pos800_400') or '')
            ru.append({'rc_key': mk, 'race_no': r['race_no'], 'pos_raw': u.get('pos'), 'finish_pos': p, 'scratched': (u.get('pos') or '').upper() in ('SCR', 'LSCR'),
                       'saddlecloth': int(u['tab']), 'horse': u.get('horse'), 'name_key': norm_name(u.get('horse')), 'barrier': int(u['barrier']) if u.get('barrier') else None,
                       'trainer': u.get('trainer'), 'jockey': u.get('jockey'), 'weight_kg': float(u['weight'][:-2]) if u.get('weight') else None,
                       'pos800': int(pp.group(1)) if pp else None, 'pos400': int(pp.group(2)) if pp else None, 'margin_l': margin_l(u.get('margin'), p == 1)})

c = duckdb.connect(dbpath)
for name, rows in [('nsw_meeting', nm), ('nsw_race', nr), ('nsw_runner', nu), ('rc_meeting', rm), ('rc_race', rr), ('rc_runner', ru)]:
    df = pd.DataFrame(rows)
    c.execute(f'drop table if exists {name}')
    if len(df):
        c.register('tmp', df); c.execute(f'create table {name} as select * from tmp'); c.unregister('tmp')
    print(f'{name}: {len(df)} rows')


# ---------- racing.com speed data (Victoria) ----------
def kmh(s):
    m = re.match(r'([\d.]+)\s*km/h', s or ''); return float(m.group(1)) if m else None
def tpos(s):
    m = re.match(r'((?:\d+:)?\d+\.\d+)\s+(\d+)\w*', s or ''); return (secs(m.group(1)), int(m.group(2))) if m else (None, None)
vs_run, vs_pt, vs_sp = [], [], []
for o in read_jsonl('racing_rcspeed_*.jsonl.gz'):
    v = o.get('value', o)
    for r in v.get('races', []):
        d = r.get('data')
        if not d: continue
        for i, h in enumerate(d['horses']):
            if 'tab' not in h: continue
            ov = d['overview'][i] if i < len(d['overview']) else []
            dm = re.match(r'(\d+)', ov[0]) if ov else None
            base = {'state': v['state'], 'meeting_date': pd.to_datetime(v['date']).date(), 'slug': v['slug'], 'meet_code': v.get('meet_code'), 'race_no': r['race_no'], 'saddlecloth': int(h['tab'])}
            vs_run.append({**base, 'pos_raw': h['pos'], 'finish_pos': ordinal(h['pos']), 'horse': h['horse'], 'name_key': norm_name(h['horse']), 'barrier': int(h['barrier']),
                           'trainer': h['trainer'], 'jockey': h['jockey'], 'dist_run_m': int(dm.group(1)) if dm else None,
                           'early_kmh': kmh(ov[1]) if len(ov) > 1 else None, 'mid_kmh': kmh(ov[2]) if len(ov) > 2 else None, 'late_kmh': kmh(ov[3]) if len(ov) > 3 else None,
                           'peak_kmh': kmh(ov[4]) if len(ov) > 4 else None, 'avg_kmh': kmh(ov[5]) if len(ov) > 5 else None})
            cum = d['cum'][i] if i < len(d['cum']) else []
            for lab, val in zip(d['cum_head'], cum):
                t, p = tpos(val)
                togo = 0 if lab == 'Overall' else (int(lab[:-1]) if lab.endswith('m') and lab[:-1].isdigit() else None)
                vs_pt.append({**base, 'to_go_m': togo, 'label': lab, 'time_to_finish_s': t, 'position': p})
            spl = d['splits'][i] if i < len(d['splits']) else []
            for lab, val in zip(d['split_head'], spl):
                t, p = tpos(val)
                vs_sp.append({**base, 'segment': lab, 'split_s': t, 'split_rank': p})
for name, rows in [('vic_speed_runner', vs_run), ('vic_speed_point', vs_pt), ('vic_speed_split', vs_sp)]:
    df = pd.DataFrame(rows); c.execute(f'drop table if exists {name}')
    if len(df):
        c.register('tmp', df); c.execute(f'create table {name} as select * from tmp'); c.unregister('tmp')
    print(f'{name}: {len(df)} rows')

checks = []
def chk(cid, desc, expected, actual, ok):
    checks.append({'check': cid, 'description': desc, 'expected': str(expected), 'actual': str(actual), 'status': 'PASS' if ok else 'FLAG'})

if nm:
    # Betfair track names vs Racing NSW venue names
    c.execute("""create or replace temp view nsw_bfmap as
      select n.key, n.meeting_date, n.venue, n.state,
             case n.venue when 'Royal Randwick' then 'Randwick' when 'Rosehill Gardens' then 'Rosehill' when 'Canterbury Park' then 'Canterbury'
                          when 'Beaumont Newcastle' then 'Newcastle' when 'Randwick Kensington' then 'Randwick' else n.venue end as bf_track
      from nsw_meeting n where n.meeting_kind = 'Professional'""")
    tot = c.execute("select count(*) from nsw_bfmap").fetchone()[0]
    inbf = c.execute("select count(*) from nsw_bfmap m where exists (select 1 from bf_runner b where b.meeting_date = m.meeting_date and b.bf_track = m.bf_track)").fetchone()[0]
    chk('N1', 'Racing NSW professional meetings also in Betfair (TAB meetings)', tot, inbf, True)
    w = c.execute("""with nw as (select m.meeting_date, m.bf_track, u.race_no, u.saddlecloth from nsw_runner u join nsw_bfmap m using(key) where u.finish_pos = 1),
                         bw as (select meeting_date, bf_track, race_no, saddlecloth from bf_runner where win_flag)
                    select count(*) total, count(*) filter (where exists (select 1 from bw where bw.meeting_date = nw.meeting_date and bw.bf_track = nw.bf_track and bw.race_no = nw.race_no and bw.saddlecloth = nw.saddlecloth)) agree,
                           count(*) filter (where exists (select 1 from bf_runner b where b.meeting_date = nw.meeting_date and b.bf_track = nw.bf_track and b.race_no = nw.race_no)) in_bf
                    from nw""").fetchone()
    chk('N2', 'NSW winners that Betfair also marks as the winner (races present in both)', w[2], w[1], w[1] >= 0.98 * w[2] if w[2] else False)
    cnt = c.execute("""with nc as (select m.meeting_date, m.bf_track, u.race_no, count(*) filter (where not u.scratched) n from nsw_runner u join nsw_bfmap m using(key) group by all),
                           bc as (select meeting_date, bf_track, race_no, count(*) n from bf_runner group by all)
                      select count(*), count(*) filter (where nc.n = bc.n) from nc join bc using(meeting_date, bf_track, race_no)""").fetchone()
    chk('N3', 'NSW races where starters match Betfair runner count', cnt[0], cnt[1], cnt[1] >= 0.9 * cnt[0] if cnt[0] else False)
    miss = c.execute("select count(*) from nsw_runner u join nsw_meeting m using(key) where m.meeting_kind <> 'Trial' and not u.scratched and (u.barrier is null or u.weight_kg is null)").fetchone()[0]
    chk('N4', 'NSW race starters (not trials) missing barrier or weight', 0, miss, miss == 0)
    pub = c.execute("select count(*) filter (where results_last_published is null), count(*) from nsw_meeting where n_races > 0").fetchone()
    chk('N5', 'NSW meetings with a "results last published" timestamp', pub[1], pub[1] - pub[0], pub[0] == 0)

if rm:
    c.execute("""create or replace temp view rc_bfmap as
      select r.rc_key, r.state, r.meeting_date, r.slug, r.bf_track from rc_meeting r""")
    w = c.execute("""with rw as (select m.meeting_date, m.bf_track, u.race_no, u.saddlecloth from rc_runner u join rc_bfmap m using(rc_key) where u.finish_pos = 1)
                    select count(*), count(*) filter (where exists (select 1 from bf_runner b where b.win_flag and b.meeting_date = rw.meeting_date and b.bf_track = rw.bf_track and b.race_no = rw.race_no and b.saddlecloth = rw.saddlecloth)),
                           count(*) filter (where exists (select 1 from bf_runner b where b.meeting_date = rw.meeting_date and b.bf_track = rw.bf_track and b.race_no = rw.race_no))
                    from rw""").fetchone()
    chk('R1', 'racing.com winners that Betfair also marks as the winner (races present in both)', w[2], w[1], w[1] >= 0.98 * w[2] if w[2] else False)
    cnt = c.execute("""with rc as (select m.meeting_date, m.bf_track, u.race_no, count(*) filter (where not u.scratched and u.finish_pos is not null) n from rc_runner u join rc_bfmap m using(rc_key) group by all),
                           bc as (select meeting_date, bf_track, race_no, count(*) n from bf_runner group by all)
                      select count(*), count(*) filter (where rc.n = bc.n) from rc join bc using(meeting_date, bf_track, race_no)""").fetchone()
    chk('R2', 'racing.com races where finishers match Betfair runner count', cnt[0], cnt[1], cnt[1] >= 0.9 * cnt[0] if cnt[0] else False)
    nob = c.execute("select count(*) from rc_runner where finish_pos is not null and (barrier is null or weight_kg is null)").fetchone()[0]
    chk('R3', 'racing.com finishers missing barrier or weight', 0, nob, nob == 0)
    vic = c.execute("select count(*), count(meet_code) from rc_meeting where state = 'VIC'").fetchone()
    chk('R4', 'Victorian meetings with a speed-data meeting code', vic[0], vic[1], vic[1] == vic[0])
    if nm:
        x = c.execute("""with n as (select *, rank() over (partition by key, race_no order by barrier) eff from nsw_runner where not scratched and finish_pos is not null),
                              r as (select *, rank() over (partition by rc_key, race_no order by barrier) eff from rc_runner where not scratched and finish_pos is not null)
                         select count(*), count(*) filter (where n.finish_pos = r.finish_pos), count(*) filter (where n.eff = r.eff), count(*) filter (where n.weight_kg = r.weight_kg),
                                count(*) filter (where n.barrier = r.barrier)
                         from n join nsw_bfmap nm using(key) join rc_bfmap rm on rm.meeting_date = nm.meeting_date and rm.bf_track = nm.bf_track and rm.state = nm.state
                         join r on r.rc_key = rm.rc_key and r.race_no = n.race_no and r.saddlecloth = n.saddlecloth""").fetchone()
        chk('X1', 'NSW runners in both sources: finish position agrees', x[0], x[1], x[1] >= 0.99 * x[0] if x[0] else False)
        chk('X2', 'NSW runners in both sources: barrier rank among starters agrees (raw barrier agrees for ' + str(x[4]) + ')', x[0], x[2], x[2] >= 0.99 * x[0] if x[0] else False)
        chk('X3', 'NSW runners in both sources: weight agrees', x[0], x[3], x[3] >= 0.95 * x[0] if x[0] else False)


if vs_run:
    w = c.execute("""select count(*), count(*) filter (where exists (select 1 from bf_runner b where b.win_flag and b.meeting_date = v.meeting_date and b.bf_track = initcap_slug and b.race_no = v.race_no and b.saddlecloth = v.saddlecloth))
                     from (select *, upper(substr(slug,1,1)) || substr(replace(slug,'-',' '),2) initcap_slug from vic_speed_runner where finish_pos = 1) v""").fetchone()
    chk('V1', 'Victorian speed-data winners that Betfair also marks as the winner', w[0], w[1], w[1] == w[0])
    s6 = c.execute("""select count(*), count(*) filter (where abs((o.time_to_finish_s - p.time_to_finish_s) - 0) >= 0) ,
                             count(*) filter (where p.time_to_finish_s between 30 and 45)
                      from vic_speed_point p join vic_speed_point o using(meeting_date, slug, race_no, saddlecloth) where p.to_go_m = 600 and o.to_go_m = 0""").fetchone()
    chk('V2', 'Victorian runners with a plausible last-600m time (30-45s)', s6[0], s6[2], s6[2] >= 0.97 * s6[0] if s6[0] else False)

ck = pd.DataFrame(checks)
os.makedirs('out', exist_ok=True); ck.to_csv('out/checks_nsw_vic.csv', index=False)
print(ck.to_string(index=False))
