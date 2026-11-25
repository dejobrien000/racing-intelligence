"""Racing Queensland tracking + Race Fields collector for GitHub Actions (Python port of history/browser_bundle.js RQB).
Reads RQ's public sectionals page for the list of tracked meetings, then for each meeting downloads the tracking ZIP
(RaceSummary XML per race) and the Race Fields PDF, and parses them exactly as the browser bundle did. Honest User-Agent,
polite pacing, stops at any CAPTCHA page. Output: a bundle zip in the same layout the history loader reads:
  raw/sectionals/<date>_<track>_T.zip, raw/racefields/rfd_<CODE>_<date>.pdf, parsed/{races,runners,secs,fields,log}.psv
Usage: python3 rq.py FROM_YYYYMMDD TO_YYYYMMDD OUT.zip"""
import sys, re, io, time, random, zlib, zipfile, hashlib, datetime as dt, xml.etree.ElementTree as ET
import requests, codecs
# Browsers decode the label 'latin1' as windows-1252 (WHATWG); undefined bytes map to the same code point.
codecs.register_error('whatwg1252', lambda e: (''.join(chr(b) for b in e.object[e.start:e.end]), e.end))
W1252 = lambda b: b.decode('cp1252', errors='whatwg1252')
BASE = 'https://www.racingqueensland.com.au'; LIST = BASE + '/industry/thoroughbred/thoroughbred-sectionals'
UA = 'RacingIntelligence-private/0.2 (personal non-commercial research; github.com/dejobrien000)'
S = requests.Session(); S.headers['User-Agent'] = UA
CAPTCHA = re.compile(r'captcha|are you human|verify you are human|unusual traffic', re.I)
CODES = {'Doomben': 'DOOM', 'Eagle_Farm': 'E_FM', 'Ipswich': 'IPSW', 'Kilcoy': 'KCOY', 'Ladbrokes_Cannon_Park': 'CRNS', 'Mackay': 'MKAY', 'Rockhampton': 'ROCK', 'Sunshine_Coast': 'SCST',
         'Sunshine_Coast_Poly_Track': 'SCPT', 'TAB_Park_Gold_Coast': 'GCST', 'Toowoomba': 'TWBA', 'Townsville': 'TOWN', 'Dalby': 'DALB', 'Picklebet_Park_Warwick': 'WARW'}
HEAD = {'races': 'date|track|race_no|meeting_code|race_code|race_name|finish_time_s|track_name|track_condition|rail|n_horses',
        'runners': 'date|track|race_no|horse_code|name|bib|final_rank|official_margin|finish_time_s|is_official|result_state|result_substate|dist_travelled|dist_diff',
        'secs': 'date|track|race_no|bib|cum_dist|real_dist|rank|inter_s|section_s|avg_speed|top_speed|stride_freq|stride_len|dist_rail|margin_dec',
        'fields': 'date|track|race_no|race_name|distance_m|start_time|tab|horse|trainer|jockey|barrier|weight_kg|emergency',
        'log': 'date|track|kind|url|http_status|bytes|sha256|retrieved_utc'}
now = lambda: dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
def clean(v): return re.sub(r'[|\r\n]+', ' ', '' if v is None else str(v)).strip()
def jround(x): import math; return math.floor(x + 0.5)          # JavaScript Math.round
def jfix3(x):                                                    # JavaScript Number.toFixed(3)
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(x).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))   # exact binary value, as JavaScript does
def ts(s):
    if not s: return ''
    m = re.search(r'(\d+):(\d+):([\d.]+)', s)
    return jfix3(int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])) if m else s
def local(tag): return tag.split('}')[-1] if isinstance(tag, str) else ''
def child(el, name):
    for c in el:
        if local(c.tag) == name: return c
def T(el, name):
    x = child(el, name)
    if x is None: return ''
    return x.get('Time') if x.get('Time') is not None else ''.join(x.itertext()).strip()   # textContent
def parse_zip(buf, date, track):
    races, runners, secs = [], [], []
    z = zipfile.ZipFile(io.BytesIO(buf))
    for name in z.namelist():                                   # same order as the zip directory, like the browser
        if not re.search(r'\.xml$', name, re.I): continue
        txt = z.read(name).decode('utf-8-sig', errors='replace')
        try: r = ET.fromstring(txt)
        except ET.ParseError:                                    # a few RQ files are cut short; the browser keeps what parsed
            from lxml import etree as LX                         # before the break, and so does libxml2's recover mode
            try: r = LX.fromstring(txt.encode('utf-8'), parser=LX.XMLParser(recover=True))
            except LX.XMLSyntaxError: continue                   # empty file: browser gets a parsererror document, skipped
            if r is None: continue
        if local(r.tag) != 'RaceSummary': continue
        m = re.search(r'_R(\d+)\.xml$', name, re.I); rn = int(m[1]) if m else 'NaN'
        hs = [h for H in r.iter() if local(H.tag) == 'Horses' for h in H if local(h.tag) == 'HorseSummary']
        races.append('|'.join(clean(v) for v in [date, track, rn, r.get('MeetingCode') or '', r.get('RaceCode') or '', T(r, 'RaceName'), ts(T(r, 'FinishTime')), T(r, 'TrackName'), T(r, 'TrackCondition'), T(r, 'RailPosition'), len(hs)]))
        for h in hs:
            a = lambda k: h.get(k) or ''
            sub = child(h, 'ResultSubState'); nil = sub is not None and any(local(k) == 'nil' and v == 'true' for k, v in sub.attrib.items())
            runners.append('|'.join(clean(v) for v in [date, track, rn, a('HorseCode'), a('Name'), a('Bib'), a('FinalRank'), a('OfficialMarginDecimal'), ts(T(h, 'FinishTime')), a('IsFinishTimeOfficial'),
                                                         T(h, 'ResultState'), (''.join(sub.itertext()) if sub is not None and not nil else ''), a('DistanceTravelled'), a('DistanceTraveledDifference')]))
            if T(h, 'ResultState') == 'DidNotStart': continue
            sec = child(h, 'Sections')
            for s in (sec if sec is not None else []):
                if local(s.tag) != 'SectionSummary': continue
                q = lambda k: (''.join(child(s, k).itertext()).strip() if child(s, k) is not None else '')
                secs.append('|'.join(clean(v) for v in [date, track, rn, a('Bib'), s.get('CumulatedDistance') or '', q('RealDistance'), q('Rank'), ts(T(s, 'IntermediateTime')), ts(T(s, 'SectionTime')),
                                                          q('AvgSpeed'), q('TopSpeed'), q('AverageStrideFrequency'), q('AverageStrideLength'), q('AverageDistanceToRail'), s.get('MarginDecimal') or '']))
    return races, runners, secs
def pdf_items(u8):                                               # port of window.pdfItems (content streams, Tm/Td/Tj only)
    latin = W1252(u8); pages = []; rx = re.compile(r'stream\r?\n'); pos = 0
    while True:                                                  # same scan as the browser: resume at each 'endstream'
        m = rx.search(latin, pos)
        if not m: break
        start = m.end(); end = latin.find('endstream', start)
        if end < 0: break
        pos = end
        dic = latin[max(0, latin.rfind('<<', 0, m.start())):m.start()]
        if 'FlateDecode' not in dic or re.search(r'Length1|Image|CIDInit|XObject', dic): continue
        d = u8[start:end].rstrip(b'\r\n')
        try:
            zd = zlib.decompressobj(); raw_ = zd.decompress(d)
            if not zd.eof or zd.unused_data: continue           # DecompressionStream rejects truncated or trailing data
            t = W1252(raw_)
        except Exception: continue
        if 'Tj' not in t: continue
        items = []; lx = ly = 0.0
        for k in re.finditer(r'1 0 0 -1 (-?[\d.]+) (-?[\d.]+) Tm|(-?[\d.]+) (-?[\d.]+) Td|\(((?:\\.|[^\\)])*)\) Tj', t):
            if k[1] is not None: lx, ly = float(k[1]), float(k[2])
            elif k[3] is not None: lx += float(k[3]); ly -= float(k[4])
            else: items.append({'x': jround(lx), 'y': jround(ly), 's': re.sub(r'\\(.)', r'\1', k[5])})
        pages.append(items)
    return pages
def parse_fields(pages, date, track):                            # port of RQB.parseFields (three-column Race Fields layout)
    bases = [569, 5899, 11229]; col = lambda x: 0 if x < 5500 else (1 if x < 10850 else 2); near = lambda a, b, t: abs(a - b) <= t
    rows, race, races = [], None, {}
    for pg in pages:
        for c in range(3):
            b = bases[c]; it = sorted([i for i in pg if col(i['x']) == c], key=lambda i: (i['y'], i['x']))
            anchors = [i['y'] for i in it if near(i['x'], b + 4522, 40) and re.fullmatch(r'\s*\d{2}\.\d\s*', i['s'])]
            for i in it:
                if b - 450 <= i['x'] <= b - 150 and re.fullmatch(r'\s*\d{1,2}\s*', i['s']):
                    race = int(i['s'].strip())
                    races[race] = {'name': re.sub(r'\s+', ' ', ''.join(j['s'] for j in it if near(j['x'], b, 5) and i['y'] - 10 <= j['y'] <= i['y'] + 260 and not j['s'].endswith('metres'))).strip()}; continue
                if race and near(i['x'], b, 5) and re.fullmatch(r'\d+ metres', i['s']):
                    races[race]['dist'] = i['s'].replace(' metres', ''); st = next((j for j in it if j['y'] == i['y'] and re.search(r'\d\d:\d\d[AP]M', j['s'])), None); races[race]['time'] = st['s'] if st else ''; continue
                if race and near(i['x'], b + 4522, 40) and re.fullmatch(r'\s*\d{2}\.\d\s*', i['s']):
                    y = i['y']; nextA = next((a for a in anchors if a > y + 20), float('inf'))
                    nh = next((j for j in it if j['y'] > y + 20 and ((b - 450 <= j['x'] <= b - 150 and re.fullmatch(r'\s*\d{1,2}\s*', j['s'])) or j['s'].endswith('metres'))), None)
                    lim = min(nextA, nh['y'] if nh else float('inf')) - 10
                    tab = next((j for j in it if near(j['x'], b, 5) and near(j['y'], y, 10) and re.fullmatch(r'\d{1,2}', j['s'].strip())), None)
                    bar = next((j for j in it if b + 4150 < j['x'] < b + 4450 and near(j['y'], y, 10)), None)
                    name = ''.join(j['s'] for j in it if near(j['x'], b + 399, 5) and y - 10 <= j['y'] <= lim).strip()
                    jock = re.sub(r'\s+', ' ', ''.join(j['s'] for j in it if b + 2800 < j['x'] < b + 4150 and y - 10 <= j['y'] <= lim)).strip()
                    em = ''; nm = name
                    if nm.startswith('(EM)'): em = 'EM'; nm = nm[4:]
                    mm = re.match(r'^(.*)\(([^()]*)\)$', nm)
                    rows.append('|'.join(clean(v) for v in [date, track, race, races[race]['name'], races[race].get('dist', ''), races[race].get('time', ''), tab['s'].strip() if tab else '',
                                                              mm[1].strip() if mm else nm, mm[2].strip() if mm else '', jock, bar['s'].strip() if bar else '', i['s'].strip(), em]))
    return rows
def get(url):
    for a in range(3):
        try:
            r = S.get(url, timeout=60)
            if r.status_code == 200 and CAPTCHA.search(r.text[:20000] if r.headers.get('content-type', '').startswith('text') else ''): raise SystemExit('STOP: CAPTCHA page at ' + url)
            return r
        except requests.RequestException:
            time.sleep(15 * (a + 1))
    return None
def meeting_list():
    r = get(LIST); found = {}
    for h in re.findall(r'href="([^"]+)"', r.text if r is not None else ''):
        m = re.search(r'/Sectional/(\d{8})_(.+)_T\.(csv|zip|pdf)$', h, re.I)
        if m: found[m[1] + '|' + m[2]] = (m[1], m[2])
    return sorted(found.values())
def main():
    d0, d1, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ms = [m for m in meeting_list() if d0 <= m[0] <= d1]; print('tracked meetings in window:', len(ms), ms, flush=True)
    parts = {k: [] for k in HEAD}; raw = {}
    for date, track in ms:
        zu = f'/RacingFile.ashx?path=/Sectional/{date}_{track}_T.zip'; r = get(BASE + zu); ok = r is not None and r.status_code == 200 and r.content[:2] == b'PK'
        parts['log'].append('|'.join([date, track, 'sectional_zip', BASE + zu, str(r.status_code if r is not None else 0), str(len(r.content) if r is not None else 0), hashlib.sha256(r.content).hexdigest() if ok else '', now()]))
        if ok:
            raw[f'raw/sectionals/{date}_{track}_T.zip'] = r.content
            try: a, b, c = parse_zip(r.content, date, track); parts['races'] += a; parts['runners'] += b; parts['secs'] += c
            except Exception as e: parts['log'].append('|'.join([date, track, 'parse_error_zip', '', '0', '0', clean(str(e))[:100], '']))
        time.sleep(2 + random.random())
        code = CODES.get(track)
        if code:
            fu = f'/RacingFile.ashx?path=/ThoroughbredMeetingFiles/rfd_{code}_{date}.pdf'; f = get(BASE + fu); okf = f is not None and f.status_code == 200 and f.content[:4] == b'%PDF'
            parts['log'].append('|'.join([date, track, 'race_fields_pdf', BASE + fu, str(f.status_code if f is not None else 0), str(len(f.content) if f is not None else 0), hashlib.sha256(f.content).hexdigest() if okf else '', now()]))
            if okf:
                raw[f'raw/racefields/rfd_{code}_{date}.pdf'] = f.content
                try: parts['fields'] += parse_fields(pdf_items(f.content), date, track)
                except Exception as e: parts['log'].append('|'.join([date, track, 'parse_error_pdf', '', '0', '0', clean(str(e))[:100], '']))
            time.sleep(2 + random.random())
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for n, b in raw.items(): z.writestr(zipfile.ZipInfo(n), b, compress_type=zipfile.ZIP_STORED)
        for k in HEAD: z.writestr(f'parsed/{k}.psv', '\n'.join([HEAD[k]] + parts[k]) + '\n')
    print({k: len(v) for k, v in parts.items()}, '->', out)
if __name__ == '__main__': main()
