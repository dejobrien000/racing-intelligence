"""Parse a Racing SA / tripleSdata race sectional PDF (2024+ format) into rows shaped like our Queensland tracking tables.

The report counts sections back from the finish: column 'Overall' is the first section (start -> the first L-mark) and column
'L<k>' is the 200 m section from k metres out to k-200. In each column the time shown is from that point to the finish, '[n]' is the
runner's position at that point ('Overall' = finishing position) and '(t)' is the section's own time.
Converted to the Queensland convention: one row per section, keyed by segment_end_m = metres from the start at the END of the
section, position = position at the end of the section, inter_s = time from the start at the end of the section, split_s = section
time, speeds in m/s. Ground covered is only given relative to the winner ('Distance Travelled From Winner'), kept as such.
Returns (race: dict, runners: list[dict], segments: list[dict], problems: list[str]). Never guesses a value: missing -> None."""
import re
TIME = r'(?:\d+:)?\d+\.\d+'
def tsec(s):
    if s is None: return None
    s = s.strip()
    if not re.fullmatch(TIME, s): return None
    if ':' in s: m, x = s.split(':'); return round(int(m) * 60 + float(x), 3)
    return float(s)
def num(s):
    try: return float(s)
    except (TypeError, ValueError): return None

TOK = r'(' + TIME + r'|-:--\.--|NA|DNT|DNF)'
def _cols(text):
    out = []
    for m in re.finditer(r'^Section ((?:Overall|L\d+)(?: L\d+)*)\s*$', text, re.M): out += m.group(1).split()
    return out
def _timeline(l):   # a line made only of time tokens, each with an optional [rank]
    toks = re.findall(TOK + r'(?:\s*\[\s*(\d+|-)?\s*\])?', l)
    rest = re.sub(TOK + r'(?:\s*\[\s*(\d+|-)?\s*\])?', '', l).strip()
    return toks if toks and not rest else None
def _splitline(l):
    toks = re.findall(r'\((' + TIME + r'|-:--\.--|NA)\)', l)
    rest = re.sub(r'\((?:' + TIME + r'|-:--\.--|NA)\)', '', l).strip()
    return toks if toks and not rest else None
def _header(p1, race, probs):
    L = [l.strip() for l in p1.splitlines() if l.strip()]
    race['venue'] = L[0].rstrip(' -') if L else None
    m = re.search(r'Race (\d+): (.+?) -\s*\n?\s*(\d+)m', p1); race.update(race_no=int(m.group(1)), race_name=m.group(2).strip(), distance_m=int(m.group(3))) if m else probs.append('no race line')
    m = re.search(r'(\d{1,2} [A-Za-z]+ \d{4}) - (\d{1,2}:\d{2}\s?[AP]M)', p1); race.update(date_text=m.group(1), start_time=m.group(2).replace(' ', '')) if m else probs.append('no date line')
    m = re.search(r'Track Rating: ([^,\n]+)', p1); race['track_rating'] = m.group(1).strip() if m else None
    m = re.search(r'Weather: ([^,\n]+)', p1); race['weather'] = m.group(1).strip() if m else None
    m = re.search(r'Rail Position: ([^\n]+?)(?:;? ?Sectional \d+m)?\s*$', p1, re.M); race['rail'] = m.group(1).strip().rstrip(';') if m else None
    m = re.search(r'Sectional (\d+)m', p1); race['sectional_m'] = int(m.group(1)) if m else None
    m = re.search(r'Report Created: (.+?)(?: \(|$)', p1, re.M); race['report_created'] = m.group(1).strip() if m else None
    m = re.search(r'^Field Times ((?:\S+ ?)+)$', p1, re.M); race['field_times'] = m.group(1).strip() if m else None
    race['race_time_s'] = tsec(race['field_times'].split()[0]) if race.get('field_times') else None
    m = re.search(r'Scratched: (.+)', '\n'.join(L)); race['scratched_text'] = m.group(1).strip() if m else ''
def _summary_rows(pages):
    """identity rows from the results table(s): saddlecloth, name, barrier, margin, metres vs winner, first 400 m. Both layouts."""
    rows = {}
    for pg in pages:
        L = [l.strip() for l in pg.splitlines() if l.strip()]
        for i, l in enumerate(L):
            nxt = L[i + 1] if i + 1 < len(L) else ''
            # newer layout (2026-): "1 8 Dirty Gold 0:53.23 0:24.20 70.8 (800-600) ..." / "(2) Jason Holder 0.5L (+3) 0:34.43 ..."
            m = re.match(r'^(\d+|DNF|DNT|NA|-) (\d+) (.+?) (' + TIME + r'|NA|-:--\.--) (' + TIME + r'|NA|-:--\.--) ([\d.]+|NA) \(', l)
            if m:
                pos, sc, name, overall, f400, top = m.groups(); r = rows.setdefault(int(sc), {'saddlecloth': int(sc)})
                r.update(horse=name.strip(), finish_pos_text=pos, finish_time_s=tsec(overall), first400_s=tsec(f400), top_speed_kmh=num(top))
                m2 = re.match(r'^\((\d+)\) (.+?)(?: (\d+(?:\.\d+)?)L \(([+-]?\d+)\))? (?:' + TIME + r'|NA|-:--\.--) ', nxt + ' ')
                if m2:
                    r.update(barrier=int(m2.group(1)), jockey=m2.group(2).strip())
                    r['margin_l'] = 0.0 if pos == '1' else num(m2.group(3)); r['ground_rel_winner_m'] = 0.0 if pos == '1' else num(m2.group(4))
                continue
            # older layout: "1 4 VOLTAGE POINT 3 68.7 0:10.83 0:24.60 1:01.20 0:55.87 [3] ... [margin] [metres]"
            m = re.match(r'^(\d+|DNF|DNT|NA|-) (\d+) (.+?) (\d+) ([\d.]+|NA) (\S+) (\S+) (.*)$', l)
            if not m or not re.search(r'\[\s*\d+\]|-:--', m.group(8)): continue
            pos, sc, name, bar, top, fast, f400, rest = m.groups(); r = rows.setdefault(int(sc), {'saddlecloth': int(sc)})
            r.update(horse=name.strip(), finish_pos_text=pos, barrier=int(bar), top_speed_kmh=num(top), first400_s=tsec(f400))
            if 'jockey' not in r: r['jockey'] = re.split(r' \d+-\d+| \(|\s+-?\d', nxt)[0].strip()
            tail = re.sub(TOK + r'\s*\[\s*(?:\d+|-)?\s*\]', '', rest).split()
            tm = [t for t in tail if re.fullmatch(TIME, t)]
            if tm and 'finish_time_s' not in r: r['finish_time_s'] = tsec(tm[0])
            mg = [t for t in tail if re.fullmatch(r'\d+(?:\.\d+)?L', t)]; dw = [t for t in tail if re.fullmatch(r'[+-]\d+', t)]
            if pos == '1': r['margin_l'] = 0.0; r['ground_rel_winner_m'] = 0.0
            if mg: r['margin_l'] = num(mg[0][:-1])
            if dw: r['ground_rel_winner_m'] = num(dw[0])
    return rows

def parse(pages):
    """pages: list of page texts (pdfplumber extract_text). Tracking comes from the runner pages; identity from the results table."""
    probs = []; race = {}
    if not pages: return race, [], [], ['no pages']
    _header(pages[0], race, probs)
    first_runner = next((i for i, pg in enumerate(pages) if 'Horse/Jockey Name' in pg), len(pages))
    summ = _summary_rows(pages[:first_runner]); scols = _cols('\n'.join(pages[:first_runner]))
    runners = []; segs = []; seen = set()
    rowlabels = {'Average Speed [km/h]': 'avg_kmh', 'Top Speed [km/h]': 'top_kmh', 'Avg. Dist. to Rail [m]': 'rail_m', 'Avg. Stride Freq. [Hz]': 'sf', 'Avg. Stride Length [m]': 'sl'}
    D = race.get('distance_m')
    for pg in pages[first_runner:]:
        mh = re.search(r'Horse/Jockey Name (.+?)/(.+?)(?:\s{2,}|$|\s+(?:Thomas|Sportsbet|Morphettville|Gawler|Murray|[A-Z][a-z]+ (?:SA|Racing)))', pg, re.M)
        if not mh:   # early-2024 layout: no '/jockey'; the venue may run on after the name: take the longest known name it starts with
            ml = re.search(r'Horse/Jockey Name (.+?)\s*$', pg, re.M)
            if not ml: continue
            line = ml.group(1); lk = re.sub(r'[^A-Z0-9]', '', line.upper())
            cands = sorted((v['horse'] for v in summ.values() if v.get('horse') and lk.startswith(re.sub(r'[^A-Z0-9]', '', v['horse'].upper()))), key=len, reverse=True)
            nmv = cands[0] if cands else (line.split(race.get('venue') or '\x00')[0] if race.get('venue') else line)
            mh = re.match(r'(.+)()', nmv.strip())
        if not mh: continue
        nm = mh.group(1).strip(); key = re.sub(r'[^A-Z0-9]', '', nm.upper())
        sc = next((k for k, v in summ.items() if re.sub(r'[^A-Z0-9]', '', v.get('horse', '').upper()) == key), None)
        cols = _cols(pg)
        if not cols: probs.append(f'{nm}: no section header on runner page'); continue
        if scols and len(scols) == len(cols) and scols != cols: cols = scols     # early-2024 runner pages label sections one step off
        lines = [l.strip() for l in pg.splitlines()]
        cum = []; spl = []
        for l in lines:
            t = _timeline(l)
            if t and len(cum) < len(cols): cum += t; continue
            sp = _splitline(l)
            if sp and len(spl) < len(cols): spl += sp
        vals = {k: [] for k in rowlabels.values()}
        for l in lines:
            for lab, k in rowlabels.items():
                if l.startswith(lab + ' ') and re.fullmatch(r'(?:\s+(?:-?\d+(?:\.\d+)?|NA|-))+', l[len(lab):]): vals[k] += [num(x) for x in l[len(lab):].split()]
        n = len(cols)
        if len(cum) != n or len(spl) != n: probs.append(f'{nm}: {len(cum)} times / {len(spl)} splits for {n} columns'); continue
        for k, v in vals.items():
            if v and len(v) != n: probs.append(f'{nm} {k}: {len(v)} values for {n} columns'); vals[k] = []
        m = re.search(r'Finish Rank (\S+)', pg); fr = m.group(1) if m else None
        m = re.search(r'Race State (\w+)', pg); state = m.group(1) if m else None
        m = re.search(r'Fastest Section Time \(Section\) (' + TIME + r')', pg); fast = tsec(m.group(1)) if m else None
        m = re.search(r'Top Speed \[km/h\] \(Section\) ([\d.]+)', pg); top = num(m.group(1)) if m else None
        r = dict(summ.get(sc, {})) if sc is not None else {}
        r.update(saddlecloth=sc, horse=nm.upper(), jockey=r.get('jockey') or (mh.group(2) or '').strip() or None, finish_rank_text=fr, race_state=state,
                 fastest_section_s=fast if (fast is not None and fast < 100) else None, top_speed_kmh=r.get('top_speed_kmh') or top)
        r.setdefault('finish_pos_text', fr); r['finish_time_s'] = r.get('finish_time_s') or tsec(cum[0][0])
        if sc is None: r['needs_saddlecloth'] = True
        if (sc, nm) in seen: probs.append(f'duplicate runner page {nm}'); continue
        seen.add((sc, nm)); runners.append(r)
        marks = [None if c == 'Overall' or (D and c == f'L{D}') else int(c[1:]) for c in cols]
        overall_t = tsec(cum[0][0])
        for j in range(n):
            end_out = marks[j + 1] if j + 1 < n else 0
            end_pos = cum[j + 1][1] if j + 1 < n else (fr if fr and fr.isdigit() else cum[0][1])
            to_fin_end = tsec(cum[j + 1][0]) if j + 1 < n else 0.0
            start_out = marks[j] if marks[j] is not None else D
            sec = lambda k: vals[k][j] if vals[k] else None
            if end_out is None: probs.append(f'{nm}: unexpected column order {cols}'); break
            segs.append({'saddlecloth': sc, 'horse': nm.upper(), 'col': cols[j], 'segment_end_m': (D - end_out) if D else None,
                         'seg_len_m': (start_out - end_out) if (D and start_out is not None and end_out is not None) else None,
                         'position': int(end_pos) if end_pos and str(end_pos).isdigit() else None,
                         'inter_s': round(overall_t - to_fin_end, 3) if (overall_t is not None and to_fin_end is not None) else None,
                         'split_s': tsec(spl[j]), 'avg_speed_ms': round(sec('avg_kmh') / 3.6, 3) if sec('avg_kmh') is not None else None,
                         'top_speed_ms': round(sec('top_kmh') / 3.6, 3) if sec('top_kmh') is not None else None,
                         'stride_freq_hz': sec('sf'), 'stride_len_m': sec('sl'), 'dist_to_rail_m': sec('rail_m')})
    if not runners: probs.append('no runner pages parsed')
    missing = [k for k in summ if k not in {r.get('saddlecloth') for r in runners}]
    if missing and runners: probs.append(f'no runner page for saddlecloths {missing}')
    race['columns'] = ' '.join(_cols(pages[first_runner]) if first_runner < len(pages) else [])
    return race, runners, segs, probs

def parse_pdf(path):
    import pdfplumber
    with pdfplumber.open(path) as pdf: pages = [(pg.extract_text() or '') for pg in pdf.pages]
    return parse(pages), pages

if __name__ == '__main__':
    import sys, json
    (race, runners, segs, probs), _ = parse_pdf(sys.argv[1])
    print(json.dumps(race, indent=1)); print(len(runners), 'runners', len(segs), 'segments'); print('problems', probs)
    for r in runners[:3]: print(r)
    for s in segs[:7]: print(s)

# ---- newest layout (from late July 2026: 'TRIPLESDATA GPS SECTIONALS'). Results table only: cumulative times, section times,
# position at the start of each section, distance run. Per-section speed, stride and rail are drawn as charts in this layout and
# are NOT read (left empty rather than decoded from graphics).
MON = {m: i for i, m in enumerate(['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'], 1)}
def parse_2026(pages):
    probs = []; race = {'layout': 'gps2026'}; p1 = pages[0]
    L = [l.strip() for l in p1.splitlines() if l.strip()]
    race['venue'] = L[1].title() if len(L) > 1 else None
    m = re.search(r'● \w{3} (\d{2}) (\w{3}) (\d{4})', p1); race['date_text'] = f'{m.group(1)} {m.group(2).title()} {m.group(3)}' if m else None
    rp = next((pg for pg in pages if re.search(r'RACE \d+ · .+? · \d+M', pg)), '')
    m = re.search(r'RACE (\d+) · (.+?) · (\d+)M', rp)
    if m: race.update(race_no=int(m.group(1)), race_name=m.group(2).strip().title(), distance_m=int(m.group(3)))
    else: probs.append('no race line')
    m = re.search(r'^(\d{1,2}:\d{2} [AP]M)', p1, re.M); race['start_time'] = m.group(1).replace(' ', '') if m else None
    m = re.search(r'TRACK - (.+?) WEATHER - (.+?) RAIL - (.+?)(?:, SECTIONAL (\d+)M)?(?: TELEMETRY|$)', p1, re.M)
    if m: race.update(track_rating=m.group(1).title(), weather=m.group(2).title(), rail=m.group(3), sectional_m=int(m.group(4)) if m.group(4) else None)
    hdr = re.search(r'POSITION IN ((?:L\d+ ?)+)', p1); cols = hdr.group(1).split() if hdr else []
    if not cols: probs.append('no column header'); return race, [], [], probs
    race['columns'] = ' '.join(cols); D = race.get('distance_m') or int(cols[0][1:])
    first_runner = next((i for i, pg in enumerate(pages) if i and 'HOW ' in pg and ' RAN' in pg), len(pages))
    text = '\n'.join(pages[:first_runner]); lines = [l.strip() for l in text.splitlines() if l.strip()]
    r1 = re.compile(r'^(\d+|DNF|DNT|-) (\d+) (.+?) (' + TIME + r'|DNF|NA|-:--\.--) (—|\d+(?:\.\d+)?L|DH|NA|-) ([\d.]+|NA|—|-) ([\d.]+|NA|—|-) ((?:(?:' + TIME + r'|-:--\.--|NA) ?)+)$')
    runners = []; segs = []; n = len(cols)
    for i, l in enumerate(lines):
        m = r1.match(l)
        if not m: continue
        pos, sc, name, ftime, marg, f400, top, cums = m.groups(); cum = cums.split()
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        m2 = re.match(r'^(\d+) (.+?) (\d{3,4}) (?:\(([+-]?\d+)\) )?([\d.]+|NA|—|-) (\S+) (.*)$', nxt)
        if len(cum) != n: probs.append(f'{name}: {len(cum)} times for {n} columns'); continue
        spl = re.findall(r'\((' + TIME + r'|-:--\.--|NA)\)(?:\[(\d+)\])?', m2.group(7)) if m2 else []
        if len(spl) != n: probs.append(f'{name}: {len(spl)} splits for {n} columns'); continue
        r = {'saddlecloth': int(sc), 'horse': name.strip().upper(), 'finish_pos_text': pos, 'finish_rank_text': pos, 'finish_time_s': tsec(ftime),
             'margin_l': 0.0 if pos == '1' else (num(marg[:-1]) if marg.endswith('L') else None), 'first400_s': tsec(f400), 'top_speed_kmh': num(top),
             'barrier': int(m2.group(1)) if m2 else None, 'jockey': m2.group(2).strip() if m2 else None, 'ground_m': int(m2.group(3)) if m2 else None,
             'ground_rel_winner_m': (0.0 if pos == '1' else num(m2.group(4))) if m2 else None, 'race_state': 'Finished' if pos.isdigit() else pos}
        runners.append(r); overall_t = tsec(cum[0])
        marks = [None] + [int(c[1:]) for c in cols[1:]]
        for j in range(n):
            end_out = marks[j + 1] if j + 1 < n else 0
            end_pos = spl[j + 1][1] if j + 1 < n else (pos if pos.isdigit() else None)
            to_fin_end = tsec(cum[j + 1]) if j + 1 < n else 0.0
            start_out = marks[j] if marks[j] is not None else D
            segs.append({'saddlecloth': int(sc), 'horse': r['horse'], 'col': cols[j], 'segment_end_m': D - end_out, 'seg_len_m': start_out - end_out,
                         'position': int(end_pos) if end_pos and str(end_pos).isdigit() else None,
                         'inter_s': round(overall_t - to_fin_end, 3) if (overall_t is not None and to_fin_end is not None) else None,
                         'split_s': tsec(spl[j][0]), 'avg_speed_ms': None, 'top_speed_ms': None, 'stride_freq_hz': None, 'stride_len_m': None, 'dist_to_rail_m': None})
    if not runners: probs.append('no runner rows parsed (2026 layout)')
    w = [r['finish_time_s'] for r in runners if r.get('finish_pos_text') == '1' and r.get('finish_time_s')]
    race['race_time_s'] = w[0] if w else None
    return race, runners, segs, probs
