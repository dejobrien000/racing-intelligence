"""Stage Damo's Victorian TripleS sectional CSV package (supplied 26 Nov 2026) and validate it. STAGING ONLY: nothing here
enters the master database or the ratings until a separate decision.

Usage: python3 -I history/stage_vic_triples.py <unpacked package dir> <history.duckdb> <out dir>

PROVENANCE (from the package README): exact downloaded bytes of TripleS race CSV exports, file names = Racing.com meeting id
+ race number, dates from Racing.com's calendar, source URLs on d3qmfyv6ad9vwv.cloudfront.net. Supplied by Damo; not
collected by Claude. Every file's sha256 is re-checked against SHA256SUMS.txt before parsing.

FILE LAYOUT (two styles, both kept as-is):
  line 1, 5 fields: date (d/mm/yyyy h:mm:ss AM, sometimes m/d) ; meeting label (contains ISO date) ; race name ; race time
                    (hh:mm:ss.fff) ; <TRACKCODE>_<distance>m_TRACK
  line 1, 3 fields: ISO date ; meeting label ; race name            (no race time, no distance: distance = last section mark)
  runner lines: horse ; saddlecloth ; then repeating [section end (m from start) ; speed m/s ; section time]
     section time is hh:mm:ss.fff or m:ss.ff. The first section is the short one (e.g. 100, 118, 147, 225 m), then 200 m each.
     Speed is 0 in some files while times are present: speed is then derived (section length / time) and flagged.
     A runner whose every time is zero is 'not tracked' (scratched or no data): kept, flagged, never treated as a run.
The meeting label's ISO date is the authority for the race date; the first-field date is checked against it.

OUTPUTS (out dir): races.csv, runners.csv, sections.csv, validation.csv, checks.txt
VALIDATION against our Betfair-sourced race lists (names, saddlecloths and the winner only; no prices are read):
  every TripleS runner found in the same race; saddlecloths agree; fastest tracked time = official winner; race times;
  section marks run to the race distance; speeds agree with length/time."""
import sys, os, re, csv, hashlib, glob, datetime as dt
from collections import Counter, defaultdict
PKG, DB, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(OUT, exist_ok=True)
def nk(s): return re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', s.upper()))
def secs(t):
    t = t.strip()
    if not t: return None
    p = t.split(':')
    try:
        if len(p) == 3: return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2])
        if len(p) == 2: return int(p[0]) * 60 + float(p[1])
        return float(t)
    except ValueError: return None
sums = dict(reversed(l.split(None, 1)) for l in open(os.path.join(PKG, 'SHA256SUMS.txt')).read().strip().split('\n'))
sums = {k.strip(): v for k, v in sums.items()}
cov = {r['archive_file']: r for r in csv.DictReader(open(os.path.join(PKG, 'coverage.csv'))) if r.get('archive_file')}
flag = {r['archive_file']: r['notes'] for r in csv.DictReader(open(os.path.join(PKG, 'flagged_originals.csv')))}
RACES, RUN, SEC, issues = [], [], [], Counter()
for f in sorted(glob.glob(os.path.join(PKG, 'original_csv', '*', '*.csv'))):
    rel = os.path.relpath(f, PKG); raw = open(f, 'rb').read(); sha = hashlib.sha256(raw).hexdigest()
    if sums.get(rel) != sha: issues['checksum mismatch'] += 1; continue
    L = [l for l in raw.decode('utf-8-sig').replace('\r', '').split('\n') if l.strip()]
    m = L[0].split(';'); c = cov.get(rel, {})
    label_date = (re.search(r'(\d{4}-\d{2}-\d{2})', m[1]) or [None, ''])[1] if len(m) > 1 else ''
    d0 = m[0].strip(); g = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', d0)
    if g:
        dm = f'{g.group(3)}-{int(g.group(2)):02d}-{int(g.group(1)):02d}'; md = f'{g.group(3)}-{int(g.group(1)):02d}-{int(g.group(2)):02d}'
        first_date_style = 'day/month' if dm == label_date else 'month/day' if md == label_date else 'disagrees with label'
    else: first_date_style = 'iso' if d0[:10] == label_date else 'disagrees with label'
    trk = m[4].strip() if len(m) >= 5 else ''
    g = re.match(r'([A-Z0-9]+)_(\d+)m_', trk)
    race = {'file': rel, 'sha256': sha, 'meeting_id': c.get('meeting_id', rel.split('/')[-1].split('_')[0]), 'race_id': c.get('race_id', ''),
            'race_no': int(rel.split('_')[-1][:2]), 'race_date': label_date or c.get('race_date', ''), 'folder_date': rel.split('/')[1],
            'coverage_track': c.get('track', ''), 'meeting_label': m[1].strip() if len(m) > 1 else '', 'race_name': m[2].strip() if len(m) > 2 else '',
            'layout': f'{len(m)}-field header', 'first_field_date': d0, 'first_field_date_style': first_date_style,
            'header_time_s': secs(m[3]) if len(m) >= 4 else None, 'course_code': trk, 'course_code_m': int(g.group(2)) if g else None,
            'package_flag': flag.get(rel, ''), 'source_url': c.get('source_url', '')}
    if race['race_date'] != race['folder_date']: issues['label date differs from folder date'] += 1
    marks = None; derived_speed = False; n_tracked = 0
    for order, ln in enumerate(L[1:], 1):
        p = ln.split(';'); name, cloth = p[0].strip(), p[1].strip()
        trip = [(int(float(p[i])), float(p[i + 1] or 0), secs(p[i + 2])) for i in range(2, len(p) - 2, 3)]
        tracked = any(t and t > 0 for _, _, t in trip)
        complete = bool(trip) and all(t and t > 0 for _, _, t in trip)   # partial = tracking stops part-way (did not finish, or tracking lost)
        cum, prev = 0.0, 0
        for k, (mark, spd, t) in enumerate(trip, 1):
            seg = mark - prev; d_spd = round(seg / t, 3) if t else None
            if tracked and spd == 0 and t: derived_speed = True
            cum = cum + t if t else cum
            SEC.append({'file': rel, 'race_date': race['race_date'], 'meeting_id': race['meeting_id'], 'race_no': race['race_no'], 'saddlecloth': cloth,
                        'horse': name, 'section_no': k, 'section_end_m': mark, 'section_len_m': seg, 'section_time_s': t if tracked else None,
                        'cum_time_s': round(cum, 3) if tracked else None, 'speed_ms_file': spd if spd else None,
                        'speed_ms_derived': d_spd if tracked else None})
            prev = mark
        marks = marks or [x[0] for x in trip]
        n_tracked += tracked
        RUN.append({'file': rel, 'race_date': race['race_date'], 'meeting_id': race['meeting_id'], 'race_no': race['race_no'], 'row_order': order,
                    'horse': name, 'horse_key': nk(name), 'saddlecloth': cloth, 'tracked': int(tracked), 'complete': int(complete),
                    'tracking_status': 'complete' if complete else 'partial (stops part-way)' if tracked else 'none (all times zero)',
                    'total_time_s': round(sum(t for _, _, t in trip if t), 3) if tracked else None, 'sections': len(trip),
                    'last_mark_m': trip[-1][0] if trip else None})
    race.update(runners=len(L) - 1, tracked_runners=n_tracked, sections=len(marks or []), first_section_m=(marks or [None])[0],
                distance_m=marks[-1] if marks else None, speed_from_file=int(not derived_speed))   # distance = the last section mark
    RACES.append(race)

# ---------------------------------------------------------------- internal checks
by_file = defaultdict(list)
for r in RUN: by_file[r['file']].append(r)
for race in RACES:
    rs = [r for r in by_file[race['file']] if r['complete']]   # fastest and distance checks use complete runs only
    if rs:
        fastest = min(rs, key=lambda r: r['total_time_s'])
        race['fastest_horse'], race['fastest_time_s'] = fastest['horse'], fastest['total_time_s']
        race['first_row_is_fastest'] = int(by_file[race['file']][0]['horse'] == fastest['horse'])
        race['header_time_minus_fastest_s'] = round(race['header_time_s'] - fastest['total_time_s'], 3) if race['header_time_s'] else None
        race['marks_reach_distance'] = int(all(r['last_mark_m'] == race['distance_m'] for r in rs))
        tt = sorted(r['total_time_s'] for r in rs); race['winning_margin_s'] = round(tt[1] - tt[0], 3) if len(tt) > 1 else None
sp = [(s['speed_ms_file'], s['speed_ms_derived']) for s in SEC if s['speed_ms_file'] and s['speed_ms_derived']]
speed_ok = sum(abs(a - b) <= 0.15 for a, b in sp)

# ---------------------------------------------------------------- validation against our Victorian race lists (Betfair-sourced)
import duckdb
con = duckdb.connect(DB, read_only=True)
bf = defaultdict(list)
for d, trk, rn, sc, name, k, win in con.execute("""select cast(meeting_date as varchar), bf_track, race_no, saddlecloth, name, name_key, win_flag
                                                    from bf_runner where state = 'VIC' and meeting_date >= '2026-07-01'""").fetchall():
    bf[(d, rn)].append((trk, str(sc), name, re.sub(r'[^A-Z0-9]', '', (k or name).upper()), win))
VAL = []
for race in RACES:
    ours = by_file[race['file']]; cand = defaultdict(list)
    for row in bf.get((race['race_date'], race['race_no']), []): cand[row[0]].append(row)
    v = {'file': race['file'], 'race_date': race['race_date'], 'race_no': race['race_no'], 'meeting_label': race['meeting_label']}
    if race['race_date'] > '2026-10-31':
        v['status'] = 'outside our Betfair-sourced lists (to 31 Oct)'; VAL.append(v)
        for r in ours:
            if not r['complete']: r['quarantine_reason'] = 'partial tracking (stops part-way)' if r['tracked'] else 'all times zero; 1-25 Nov, not yet checkable (scratched or untracked)'
        continue
    best = max(cand.items(), key=lambda kv: len({x[3] for x in kv[1]} & {r['horse_key'] for r in ours}), default=(None, []))
    keys = {x[3]: x for x in best[1]}; tr = [r for r in ours if r['tracked']]; hit = [r for r in tr if r['horse_key'] in keys]
    untr = [r for r in ours if not r['tracked']]
    v.update(bf_track=best[0] or '', tracked=len(tr), found_in_race=len(hit), bf_runners=len(best[1]),
             saddlecloth_agree=sum(keys[r['horse_key']][1] == r['saddlecloth'] for r in hit),
             untracked=len(untr), untracked_but_ran=sum(r['horse_key'] in keys for r in untr),
             starters_without_tracking=sum(1 for k in keys if k not in {r['horse_key'] for r in ours}))
    bd = {x[0] for x in best[1]}
    winner = [x for x in best[1] if x[4] in (1, '1', True)]
    v['bf_winner'] = ' / '.join(x[2] for x in winner); v['dead_heat'] = int(len(winner) > 1)
    v['fastest_is_winner'] = '' if not winner or not race.get('fastest_horse') else int(nk(race['fastest_horse']) in {x[3] for x in winner})
    v['winning_margin_tracked_s'] = race.get('winning_margin_s')
    v['status'] = 'no matching race' if not hit else 'all tracked runners found' if len(hit) == len(tr) else 'some tracked runners not found'
    for r in ours:
        if not r['complete']: r['quarantine_reason'] = ('partial tracking (stops part-way)' if r['tracked'] else
            'all times zero; in the official field: ran without tracking' if r['horse_key'] in keys else 'all times zero; not in the official field: scratched') if hit else \
            ('partial tracking (stops part-way)' if r['tracked'] else 'all times zero; race not in our reference lists')
    VAL.append(v)

def dump(name, rows):
    cols = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(OUT, name), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
for n, rows in [('races.csv', RACES), ('runners.csv', RUN), ('sections.csv', SEC), ('validation.csv', VAL)]: dump(n, rows)
Q = [r for r in RUN if not r['complete']]; dump('quarantine_runners.csv', Q)   # kept with reasons; nothing is discarded
inb = [v for v in VAL if 'found_in_race' in v]
fw = [v for v in inb if v.get('fastest_is_winner') != '']
rep = [f"files {len(RACES)} | checksum mismatches {issues['checksum mismatch']} | meetings {len({r['meeting_id'] for r in RACES})} | dates {min(r['race_date'] for r in RACES)} to {max(r['race_date'] for r in RACES)}",
       f"layouts {dict(Counter(r['layout'] for r in RACES))} | first-field date style {dict(Counter(r['first_field_date_style'] for r in RACES))}",
       f"label date differs from folder date: {issues['label date differs from folder date']}",
       f"runners {len(RUN)} | with any positive time {sum(r['tracked'] for r in RUN)} (complete {sum(r['complete'] for r in RUN)}, partial {sum(r['tracked'] - r['complete'] for r in RUN)}) | none (all-zero times) {sum(1 - r['tracked'] for r in RUN)} | sections {len(SEC)}",
       f"file speed (speed AT the section mark) vs section average (length/time): within 1 m/s {sum(abs(a - b) <= 1 for a, b in sp)}/{len(sp)}; files with zero speeds but times {sum(1 - r['speed_from_file'] for r in RACES)}",
       f"section marks reach the race distance (all tracked runners): {sum(r.get('marks_reach_distance', 0) for r in RACES)}/{sum(1 for r in RACES if 'marks_reach_distance' in r)}",
       f"first row is the fastest tracked runner: {sum(r.get('first_row_is_fastest', 0) for r in RACES)}/{sum(1 for r in RACES if 'first_row_is_fastest' in r)}",
       "5-field header time minus fastest tracked time: median " + str(sorted(r['header_time_minus_fastest_s'] for r in RACES if r.get('header_time_minus_fastest_s') is not None)[len([1 for r in RACES if r.get('header_time_minus_fastest_s') is not None]) // 2]) + " s (the header time is NOT the winner's time; not used)",
       f"course code length vs race distance (5-field): same {sum(r['course_code_m'] == r['distance_m'] for r in RACES if r['course_code_m'])} / differ {sum(r['course_code_m'] != r['distance_m'] for r in RACES if r['course_code_m'])} (the code names the course, not the race distance)",
       f"VALIDATION vs our Victorian race lists (to 31 Oct): races {len(inb)} | {dict(Counter(v['status'] for v in inb))}",
       f"   tracked runners found {sum(v['found_in_race'] for v in inb)}/{sum(v['tracked'] for v in inb)} | saddlecloth agrees {sum(v['saddlecloth_agree'] for v in inb)}/{sum(v['found_in_race'] for v in inb)}",
       f"   untracked (all-zero) runners {sum(v['untracked'] for v in inb)}: listed as starters {sum(v['untracked_but_ran'] for v in inb)} (= ran but no tracking), not listed {sum(v['untracked'] - v['untracked_but_ran'] for v in inb)} (= scratched)",
       f"   starters in our lists missing from the TripleS file: {sum(v['starters_without_tracking'] for v in inb)}",
       f"   fastest complete run = official winner (dead heats count either): {sum(v['fastest_is_winner'] for v in fw)}/{len(fw)}; dead heats {sum(v.get('dead_heat', 0) for v in fw)}",
       "   winner differs: " + '; '.join(f"{v['file'].split('/')[-1]} {v['bf_winner']} (tracked gap {v.get('winning_margin_tracked_s')} s)" for v in fw if v['fastest_is_winner'] == 0),
       f"1-25 Nov races (not yet in our lists, checked internally only): {sum(1 for v in VAL if 'outside' in v['status'])}",
       f"package-flagged files: {sum(1 for r in RACES if r['package_flag'])}",
       "quarantined runners (kept, with reasons): " + str(dict(Counter(r['quarantine_reason'] for r in Q)))]
open(os.path.join(OUT, 'checks.txt'), 'w').write('\n'.join(rep) + '\n'); print('\n'.join(rep))
