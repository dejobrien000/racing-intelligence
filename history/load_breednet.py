"""Load Breednet results bundles (racing_breednet_*.jsonl.gz) into history.duckdb and run checks.
Usage: python3 load_breednet.py <bundle folder> <history.duckdb>
Tables: bn_meeting, bn_race, bn_runner (all states the crawl collected; state from the venue map below).
No prices are stored: any text after the weight is dropped, and the loader refuses a record that still has one.
Latest record per key wins (by retrieved_utc). Checks go to out/checks_breednet.csv."""
import sys, os, re, glob, gzip, json, duckdb, pandas as pd, numpy as np

folder, db = sys.argv[1], sys.argv[2]
best = {}
for f in sorted(glob.glob(os.path.join(folder, 'racing_breednet_*.jsonl.gz'))):
    with gzip.open(f, 'rt', encoding='utf-8') as fh:
        for line in fh:
            if not line.strip(): continue
            o = json.loads(line); k = o['key']; v = o['value']
            if not (k.startswith('bnm:') or k.startswith('bn:')): continue
            stamp = v.get('cleaned_utc') or v.get('retrieved_utc') or ''
            # normalise the early test keys bn:STATE:DATE:Track to date + slug
            date = v.get('date'); slug = v.get('slug')
            nk = f'{date}:{slug}'
            if nk not in best or stamp >= best[nk][0]: best[nk] = (stamp, v, os.path.basename(f))

con = duckdb.connect(db)
bf = con.execute("select distinct bf_track, state from bf_runner").fetchdf()
slug = lambda t: re.sub(r'[^a-z0-9]+', '-', t.lower().replace('&', 'and')).strip('-')
state_of = {slug(t): s for t, s in zip(bf.bf_track, bf.state)}
alias = {'caulfield-heath': 'caulfield', 'sandown-hillside': 'sandown', 'sandown-lakeside': 'sandown', 'randwick-kensington': 'randwick', 'kensington': 'randwick',
         'the-valley': 'moonee-valley', 'beaumont-newcastle': 'newcastle', 'newcastle-beaumont': 'newcastle', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill',
         'canterbury-park': 'canterbury', 'royal-randwick': 'randwick', 'pakenham-synthetic': 'pakenham', 'ballarat-synthetic': 'ballarat', 'geelong-synthetic': 'geelong'}
bf_slug = lambda s: alias.get(s, s[:-10] if s.endswith('-synthetic') else s)

def secs(t):
    m = re.match(r'^(?:(\d+):)?(\d+(?:\.\d+)?)$', (t or '').strip())
    return (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else None
M, R, U = [], [], []
for nk, (stamp, v, src) in best.items():
    s = v['slug']; st = state_of.get(bf_slug(s))
    M.append({'meeting_date': v['date'], 'slug': s, 'bf_track_slug': bf_slug(s), 'state': st, 'title': v.get('meeting'), 'n_races': len(v.get('races', [])), 'retrieved_utc': v.get('retrieved_utc'), 'bundle': src})
    for r in v.get('races', []):
        tm = re.match(r'^\s*([\d:.]+)\s*(?:\(([\d.]+)\))?', r.get('time') or '')
        g = re.match(r'^\s*([A-Za-z]+)\s*\(?(\d+)?', r.get('track_cond') or '')
        prize = re.sub(r'[^\d]', '', r.get('prize') or '')
        R.append({'meeting_date': v['date'], 'slug': s, 'race_no': r.get('race_no'), 'title': r.get('title'), 'distance_m': r.get('distance_m'), 'class': r.get('class'),
                  'going': g.group(1).title() if g else None, 'going_num': int(g.group(2)) if g and g.group(2) else None,
                  'race_time_s': secs(tm.group(1)) if tm else None, 'last600_s': float(tm.group(2)) if tm and tm.group(2) else None,
                  'prize': int(prize) if prize else None, 'stakes_header': r.get('stakes_header'), 'header_raw': r.get('header_raw'),
                  # jump-outs / barrier trials (Breednet lists Victorian jump-outs from May 2026): not races, excluded from all performance work
                  'is_trial': bool(re.search(r'jump\s*out|barrier\s*trial|^trial', (r.get('class') or '') + ' ' + (r.get('title') or ''), re.I)) and not prize})
        for x in r.get('runners', []):
            w = x.get('weight') or ''
            if re.search(r'\d+/\d+|-\s*\d', w): raise SystemExit(f'price text found in weight for {nk}; refusing to load')
            pos = x.get('pos') or ''; mg = x.get('margin') or ''
            dam, ds = x.get('dam'), x.get('damsire')
            if ds and re.match(r'^[A-Z]{2,3}\) \(', ds): dam = f"{dam} ({ds[:ds.index(')')]})"; ds = ds[ds.index(') (') + 3:]
            if ds: ds = ds.rstrip(')') + ')' * max(0, ds.count('(') - ds.rstrip(')').count(')'))
            U.append({'meeting_date': v['date'], 'slug': s, 'race_no': r.get('race_no'), 'pos_raw': pos, 'finish_pos': int(pos) if pos.isdigit() else None,
                      'margin_l': 0.0 if pos == '1' else (float(mg) if re.match(r'^\d+(\.\d+)?$', mg) else None), 'saddlecloth': x.get('saddlecloth'),
                      'horse': x.get('horse'), 'name_key': re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', x.get('horse') or '').upper().replace("'", '').strip(),
                      'weight_kg': float(w) if re.match(r'^\d+(\.\d+)?$', w) else None, 'jockey': x.get('jockey'), 'trainer': x.get('trainer'),
                      'age': x.get('age'), 'sex': x.get('sex'), 'sire': x.get('sire'), 'dam': dam, 'damsire': ds})
for name, rows in [('bn_meeting', M), ('bn_race', R), ('bn_runner', U)]:
    df = pd.DataFrame(rows); df['meeting_date'] = pd.to_datetime(df['meeting_date']).dt.date
    con.execute(f'drop table if exists {name}'); con.register('df', df); con.execute(f'create table {name} as select * from df'); con.unregister('df')

checks = []
def add(cid, what, expect, got, status): checks.append({'check': cid, 'what': what, 'expected': expect, 'got': got, 'status': status})
nt = con.execute('select count(*), coalesce(sum(case when is_trial then 1 else 0 end),0) from bn_race').fetchone()
add('B8', 'jump-outs / barrier trials flagged (excluded from analysis)', 'reported', f'{nt[1]} of {nt[0]} races', 'INFO')
n = con.execute("select count(*), count(distinct state), sum(n_races) from bn_meeting").fetchone()
add('B0', 'meetings / states / races loaded', '-', f'{n[0]} / {n[1]} / {n[2]}', 'INFO')
add('B0b', 'runners loaded', '-', con.execute('select count(*) from bn_runner').fetchone()[0], 'INFO')
unk = con.execute("select count(*) from bn_meeting where state is null").fetchone()[0]
add('B1', 'meetings whose venue has no state (not in Betfair)', 'few (picnic venues)', unk, 'FLAG' if unk else 'PASS')
j = con.execute("""with b as (select meeting_date, bf_track, state, count(distinct race_no) races, count(*) runners,
                       count(distinct case when win_flag then race_no||':'||name_key end) winners from bf_runner group by 1,2,3),
                  m as (select m.meeting_date, m.slug, m.bf_track_slug, m.n_races, (select count(*) from bn_runner u where u.meeting_date=m.meeting_date and u.slug=m.slug) runners from bn_meeting m)
                  select count(*) matched, sum(case when m.n_races=b.races then 1 else 0 end) same_races, sum(case when m.runners=b.runners then 1 else 0 end) same_runners
                  from m join b on b.meeting_date=m.meeting_date and lower(regexp_replace(replace(b.bf_track,'&','and'),'[^A-Za-z0-9]+','-','g'))=m.bf_track_slug""").fetchone()
add('B2', 'meetings also in Betfair: same race count', 'all', f'{j[1]} of {j[0]}', 'PASS' if j[0] and j[1] == j[0] else 'FLAG')
add('B3', 'meetings also in Betfair: same runner count', 'nearly all', f'{j[2]} of {j[0]}', 'PASS' if j[0] and j[2] >= 0.98 * j[0] else 'FLAG')
w = con.execute("""select count(*), sum(case when b.name_key is not null then 1 else 0 end) from bn_runner u
                  join bn_meeting m using (meeting_date, slug)
                  left join bf_runner b on b.meeting_date=u.meeting_date and lower(regexp_replace(replace(b.bf_track,'&','and'),'[^A-Za-z0-9]+','-','g'))=m.bf_track_slug
                       and b.race_no=u.race_no and b.win_flag and regexp_replace(b.name_key,'[^A-Z0-9]','','g')=regexp_replace(u.name_key,'[^A-Z0-9]','','g')
                  where u.finish_pos=1 and exists (select 1 from bf_runner b2 where b2.meeting_date=u.meeting_date and lower(regexp_replace(replace(b2.bf_track,'&','and'),'[^A-Za-z0-9]+','-','g'))=m.bf_track_slug)""").fetchone()
add('B4', 'winners that match Betfair (meetings in both)', '>= 99%', f'{w[1]} of {w[0]}', 'PASS' if w[0] and w[1] >= 0.99 * w[0] else 'FLAG')
sp = con.execute("select count(*), sum(case when distance_m/race_time_s between 14 and 19 then 1 else 0 end), sum(case when last600_s between 31 and 42 then 1 else 0 end) from bn_race where race_time_s>0").fetchone()
add('B5', 'races with a plausible time / last 600m', 'nearly all', f'{sp[1]} / {sp[2]} of {sp[0]}', 'PASS' if sp[0] and sp[1] >= 0.98 * sp[0] else 'FLAG')
mg = con.execute("select count(*), sum(case when u.margin_l is null then 1 else 0 end) from bn_runner u join bn_race r using (meeting_date, slug, race_no) where u.finish_pos>1 and not r.is_trial").fetchone()
add('B6', 'placed-behind runners with no margin (races only, jump-outs excluded)', 'few', f'{mg[1]} of {mg[0]}', 'PASS' if mg[0] and mg[1] <= 0.02 * mg[0] else 'FLAG')
try:   # overlap with Racing NSW results (Jul-Nov 2026): finish, weight and race time agree?
    x = con.execute("""select count(*), sum(case when abs(u.weight_kg - coalesce(n.weight_carried_kg, n.weight_kg)) < 0.01 then 1 else 0 end) from bn_runner u join bn_meeting m using (meeting_date, slug)
                      join (select r.*, nm.meeting_date from nsw_runner r join nsw_meeting nm using (key)) n on n.meeting_date = u.meeting_date and n.finish_pos = u.finish_pos and n.race_no = u.race_no
                      and regexp_replace(upper(n.horse),'[^A-Z0-9]','','g') = regexp_replace(u.name_key,'[^A-Z0-9]','','g')""").fetchone()
    add('B7', 'NSW overlap with Racing NSW results: same horse at same place, weight carried agrees', 'all', f'{x[1]} of {x[0]}', 'PASS' if x[0] and x[1] >= 0.98 * x[0] else ('SKIP' if not x[0] else 'FLAG'))
except Exception as e:
    add('B7', 'NSW overlap with Racing NSW results', '-', f'not run: {str(e)[:80]}', 'SKIP')
os.makedirs('out', exist_ok=True)
c = pd.DataFrame(checks); c.to_csv('out/checks_breednet.csv', index=False); print(c.to_string(index=False))
print(con.execute("select state, extract(year from meeting_date) y, count(*) meetings, sum(n_races) races from bn_meeting group by 1,2 order by 1,2").fetchdf().to_string(index=False))
