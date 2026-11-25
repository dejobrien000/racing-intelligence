"""Racing SA tracking probe (Damo, 26 Nov 2026: collect SA overnight into a staged database; not production).
Reads a few public racingsa.com.au pages and one known tripleSdata sectional PDF with an honest User-Agent, a robots.txt check
and slow pacing; records where the per-race 'Sectional Times' links point. No browser impersonation, no cookies, no login."""
import re, sys, json, time, os, urllib.robotparser, requests
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
UA = 'RacingIntelligence-private/0.2 (personal non-commercial research; github.com/dejobrien000)'
S = requests.Session(); S.headers['User-Agent'] = UA
log = open(os.path.join(OUT, 'probe.log'), 'w')
def p(*a): print(*a); print(*a, file=log, flush=True)
def robots(base):
    try:
        r = S.get(base + '/robots.txt', timeout=30); p('robots', base, r.status_code, len(r.text)); open(os.path.join(OUT, re.sub(r'\W', '_', base) + '_robots.txt'), 'w').write(r.text)
        rp = urllib.robotparser.RobotFileParser(); rp.parse(r.text.splitlines() if r.status_code == 200 else []); return rp
    except Exception as ex: p('robots error', base, ex); return None
RP = {b: robots(b) for b in ['https://racingsa.com.au', 'https://d26j0amf97rmny.cloudfront.net']}
def get(url, name):
    base = re.match(r'https://[^/]+', url).group(0); rp = RP.get(base)
    if rp and not rp.can_fetch(UA, url): p('ROBOTS DISALLOW', url); return None
    time.sleep(3); r = S.get(url, timeout=60); p('GET', url, r.status_code, r.headers.get('content-type'), len(r.content))
    open(os.path.join(OUT, name), 'wb').write(r.content); return r
for url, name in [('https://racingsa.com.au/meeting/5185295', 'meeting_5185295.html'), ('https://racingsa.com.au/meetings/31-aug-24-morphettville', 'meeting_31aug24.html'),
                  ('https://racingsa.com.au/', 'home.html'), ('https://racingsa.com.au/results', 'results.html')]:
    r = get(url, name)
    if r is None or r.status_code != 200: continue
    h = r.text
    found = sorted(set(re.findall(r'https?://[^\s"\'<>]*(?:cloudfront|sectional|speedmap|\.pdf|/api/)[^\s"\'<>]*', h, re.I)))
    p(name, 'links with cloudfront/sectional/pdf/api:', len(found)); [p('   ', u) for u in found[:60]]
    rel = sorted(set(re.findall(r'(?:href|src|data-[a-z-]+)="([^"]*(?:ectional|peedmap|race/|meeting/|\.pdf|/api/)[^"]*)"', h, re.I)))
    p(name, 'attributes:', len(rel)); [p('   ', u) for u in rel[:80]]
    scripts = re.findall(r'<script[^>]*src="([^"]+)"', h); p(name, 'scripts:', scripts[:20])
    for k in ['__NEXT_DATA__', 'window.__', 'Sectional Times', 'sectional']:
        i = h.find(k); p(name, k, i, h[max(0, i - 200): i + 300].replace('\n', ' ') if i >= 0 else '')
r = get('https://d26j0amf97rmny.cloudfront.net/30072/2025-05-03_race02_sectional.pdf', 'sample_2025-05-03_race02.pdf')
try:
    import pdfplumber
    with pdfplumber.open(os.path.join(OUT, 'sample_2025-05-03_race02.pdf')) as pdf:
        p('pdf pages', len(pdf.pages)); txt = '\n\n=== PAGE ===\n'.join((pg.extract_text() or '') for pg in pdf.pages)
        open(os.path.join(OUT, 'sample_2025-05-03_race02.txt'), 'w').write(txt)
        tabs = [[t for t in pg.extract_tables()] for pg in pdf.pages]; json.dump(tabs, open(os.path.join(OUT, 'sample_2025-05-03_race02_tables.json'), 'w'))
        p('pdf text chars', len(txt))
except Exception as ex: p('pdf parse error', ex)
