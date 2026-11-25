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

def parse(pages):
    """pages: list of page texts (pdfplumber extract_text)."""
    probs = []; p1 = pages[0]; L = [l.strip() for l in p1.splitlines() if l.strip()]
    race = {'venue': L[0] if L else None}
    m = re.search(r'Race (\d+): (.+?) - (\d+)m', p1); race.update(race_no=int(m.group(1)), race_name=m.group(2).strip(), distance_m=int(m.group(3))) if m else probs.append('no race line')
    m = re.search(r'(\d{2} \w{3} \d{4}) - (\d{1,2}:\d{2}[AP]M)', p1); race.update(date_text=m.group(1), start_time=m.group(2)) if m else probs.append('no date line')
    m = re.search(r'Track Rating: ([^,\n]+)', p1); race['track_rating'] = m.group(1).strip() if m else None
    m = re.search(r'Weather: ([^,\n]+)', p1); race['weather'] = m.group(1).strip() if m else None
    m = re.search(r'Rail Position: ([^\n]+?)(?:;? ?Sectional \d+m)?\s*$', p1, re.M); race['rail'] = m.group(1).strip().rstrip(';') if m else None
    m = re.search(r'Sectional (\d+)m', p1); race['sectional_m'] = int(m.group(1)) if m else None
    m = re.search(r'Report Created: (.+?) \(', p1); race['report_created'] = m.group(1).strip() if m else None
    m = re.search(r'^Section (Overall(?: L\d+)+)\s*$', p1, re.M)
    cols = m.group(1).split() if m else None
    if not cols: probs.append('no section header'); return race, [], [], probs
    race['columns'] = ' '.join(cols)
    m = re.search(r'^Field Times ((?:\S+ ?)+)$', p1, re.M); race['field_times'] = m.group(1).strip() if m else None
    race['race_time_s'] = tsec(race['field_times'].split()[0]) if race.get('field_times') else None
    m = re.search(r'Scratched: (.+)', p1); race['scratched_text'] = m.group(1).strip() if m else ''
    # page-1 results rows: "pos # NAME barrier topspeed fastest first400 overall c1 [r] c2 [r] ... margin dist"
    runners = {}
    rowre = re.compile(r'^(\d+|DNF|DNT|NA|-) (\d+) (.+?) (\d+) (\S+) (\S+) (\S+) (\S+) (.*)$')
    for i, l in enumerate(L):
        mm = rowre.match(l)
        if not mm or not re.search(r'\[\s*\d+\]|\bDN[FT]\b|-:--', mm.group(9) + ' ' + mm.group(8)): continue
        pos, sc, name, bar, top, fast, f400, overall, rest = mm.groups()
        tail = re.sub(r'(?:' + TIME + r'|-:--\.--|NA) ?\[\s*\d+\]', '', rest).split()
        margin = tail[0] if tail else None; dist = tail[1] if len(tail) > 1 else None
        jl = L[i + 1] if i + 1 < len(L) else ''
        jockey = re.split(r' \d+-\d+| \(|\s+-?\d', jl)[0].strip()
        mg = 0.0 if pos == '1' else (num(margin[:-1]) if margin and margin.endswith('L') else None)
        runners[int(sc)] = {'margin_l': mg, 'saddlecloth': int(sc), 'horse': name.strip(), 'jockey': jockey, 'barrier': int(bar), 'finish_pos_text': pos,
                            'top_speed_kmh': num(top), 'fastest_section_s': tsec(fast), 'first400_s': tsec(f400), 'finish_time_s': tsec(overall),
                            'margin_text': margin, 'ground_rel_winner_m': num(dist) if dist else (0.0 if pos == '1' else None)}
    if not runners: probs.append('no runner rows on page 1')
    # runner pages
    segs = []; seen = set()
    rows = {'Average Speed [km/h]': 'avg_kmh', 'Top Speed [km/h]': 'top_kmh', 'Avg. Dist. to Rail [m]': 'rail_m', 'Avg. Stride Freq. [Hz]': 'sf', 'Avg. Stride Length [m]': 'sl'}
    for pg in pages[1:]:
        mh = re.search(r'Horse/Jockey Name (.+?)/', pg)
        if not mh: continue
        nm = mh.group(1).strip(); sc = next((k for k, v in runners.items() if v['horse'] == nm), None)
        if sc is None:   # name may run into the venue column: match by prefix
            sc = next((k for k, v in runners.items() if pg.find('Horse/Jockey Name ' + v['horse'] + '/') >= 0), None)
        if sc is None: probs.append(f'runner page not matched: {nm}'); continue
        if sc in seen: probs.append(f'duplicate runner page {sc}'); continue
        seen.add(sc); r = runners[sc]
        m = re.search(r'Finish Rank (\S+)', pg); r['finish_rank_text'] = m.group(1) if m else None
        m = re.search(r'Race State (\w+)', pg); r['race_state'] = m.group(1) if m else None
        lines = [l.strip() for l in pg.splitlines()]
        tl = next((l for l in lines if re.match(r'^(?:' + TIME + r'|-:--\.--|NA)\s*\[', l)), None)
        sl_ = next((l for l in lines if re.match(r'^\((?:' + TIME + r'|-:--\.--)\)', l)), None)
        cum = re.findall(r'(' + TIME + r'|-:--\.--|NA)\s*\[\s*(\d+|-)?\s*\]', tl) if tl else []
        spl = re.findall(r'\((' + TIME + r'|-:--\.--)\)', sl_) if sl_ else []
        vals = {}
        n = len(cols)
        for lab, key in rows.items():   # the metric row: label followed only by numbers / NA (not the '(Section)' summary line)
            ml = next((l for l in lines if l.startswith(lab + ' ') and re.fullmatch(r'(?:\s+(?:-?\d+(?:\.\d+)?|NA|-))+', l[len(lab):])), None)
            vals[key] = [num(x) for x in ml[len(lab):].split()] if ml else []
        if len(cum) != n or len(spl) != n: probs.append(f'#{sc} {nm}: {len(cum)} times / {len(spl)} splits for {n} columns'); continue
        for key, v in vals.items():
            if v and len(v) != n: probs.append(f'#{sc} {key}: {len(v)} values for {n} columns'); vals[key] = []
        D = race.get('distance_m'); marks = [None] + [int(c[1:]) for c in cols[1:]]   # metres out at the START of each column's section
        overall_t = tsec(cum[0][0])
        for j in range(n):
            end_out = marks[j + 1] if j + 1 < n else 0                               # metres out at the END of the section
            end_pos = cum[j + 1][1] if j + 1 < n else cum[0][1]
            to_fin_end = tsec(cum[j + 1][0]) if j + 1 < n else 0.0
            sec = lambda k: vals[k][j] if vals[k] else None
            segs.append({'saddlecloth': sc, 'col': cols[j], 'segment_end_m': (D - end_out) if D else None,
                         'seg_len_m': ((marks[j] if j else D) - end_out) if D else None,
                         'position': int(end_pos) if end_pos and end_pos.isdigit() else None,
                         'inter_s': round(overall_t - to_fin_end, 3) if (overall_t is not None and to_fin_end is not None) else None,
                         'split_s': tsec(spl[j]), 'avg_speed_ms': round(sec('avg_kmh') / 3.6, 3) if sec('avg_kmh') is not None else None,
                         'top_speed_ms': round(sec('top_kmh') / 3.6, 3) if sec('top_kmh') is not None else None,
                         'stride_freq_hz': sec('sf'), 'stride_len_m': sec('sl'), 'dist_to_rail_m': sec('rail_m')})
    miss = [k for k in runners if k not in seen]
    if miss: probs.append(f'no runner page for saddlecloths {miss}')
    return race, list(runners.values()), segs, probs

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
