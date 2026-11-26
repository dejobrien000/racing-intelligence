"""Racing NSW 'Stewards Notifications' posts -> one staging row per notice (every version kept). Research data only.
Usage: python3 collect/nswstewards/parse.py <posts.jsonl> <out.csv> [history.duckdb]
Columns: post_id, version (capture order), date_gmt, modified_gmt, available_from_utc (= modified_gmt of that version),
meeting heading as printed, meeting_date (inferred: day/month in the heading, year from the post date), category
(LATE GEAR CHANGE, SURGERY, IN FOAL, OVERWEIGHT, ...), race_no, saddlecloth, horse as printed, horse_key, text, parse_note.
A notice that is not tied to a race and horse (e.g. 'MINIMUM RIDING WEIGHT' for a rider) is kept with race/horse blank."""
import sys, re, json, csv, html as H, datetime as dt
src, out = sys.argv[1], sys.argv[2]; db = sys.argv[3] if len(sys.argv) > 3 else None
MON = {m: i + 1 for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'])}
def nk(s): return re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', s.upper()))   # drops '(NZ)' and '(Trained by ...)'
def mdate(head, post_date):
    g = re.search(r'(\d{1,2})(?:st|nd|rd|th)?\s+(' + '|'.join(MON) + r')', head, re.I)
    if not g: return ''
    pd_ = dt.date.fromisoformat(post_date[:10]); y = pd_.year; mo = MON[g.group(2).lower()]
    if mo < pd_.month - 6: y += 1          # a December post about January racing
    if mo > pd_.month + 6: y -= 1
    try: return dt.date(y, mo, int(g.group(1))).isoformat()
    except ValueError: return ''
rows = []; vcount = {}
for ln in open(src, encoding='utf-8'):
    p = json.loads(ln); vcount[p['id']] = vcount.get(p['id'], 0) + 1
    h = p['content_html']
    h = re.sub(r'<strong[^>]*color:\s*#0000ff[^>]*>(.*?)</strong>', lambda m: '\n@@MEET@@' + re.sub('<[^>]+>', '', m.group(1)) + '\n', h, flags=re.S | re.I)
    h = re.sub(r'<strong[^>]*>(.*?)</strong>', lambda m: '@@B@@' + re.sub(r'<br\s*/?>\s*', ' ', m.group(1)).strip() + '@@/B@@', h, flags=re.S | re.I)
    h = re.sub(r'<br\s*/?>|</p>|<p[^>]*>', '\n', h, flags=re.I)
    text = H.unescape(re.sub(r'<[^>]+>', '', h))
    meet, cat = '', ''
    base = {'post_id': p['id'], 'version': vcount[p['id']], 'date_gmt': p['date_gmt'], 'modified_gmt': p['modified_gmt'],
            'available_from_utc': (p['modified_gmt'] or p['date_gmt'] or '') + 'Z', 'captured_utc': p['captured_utc'], 'title': H.unescape(p['title'])}
    for raw in text.split('\n'):
        s = raw.strip()
        if not s or s.lower().startswith('please note'): continue
        if s.startswith('@@MEET@@'): meet, cat = s[8:].strip(), ''; continue
        plain = re.sub(r'@@/?B@@', '', s).strip()
        if not plain: continue
        if re.fullmatch(r'@@B@@[^@]+@@/B@@', s) and plain.upper() == plain and len(plain) < 60: cat = plain.rstrip(':'); continue
        g = re.match(r'^Race\s*(\d{1,2})\s*,\s*No\.?\s*(\d{1,2})\s*[-–]\s*(.+?)\s*:\s*(.*)$', plain, re.I)
        r = dict(base, meeting_heading=meet, meeting_date=mdate(meet, p['date_gmt'] or p['captured_utc']), category=cat)
        if g: r.update(race_no=int(g.group(1)), saddlecloth=int(g.group(2)), horse=g.group(3).strip(), horse_key=nk(g.group(3).strip()), text=g.group(4).strip())
        else: r.update(text=plain, parse_note='not tied to a race and horse')
        rows.append(r)
if db and rows:
    import duckdb
    con = duckdb.connect(db, read_only=True)
    have = {(d, k) for d, k in con.execute("""select cast(m.meeting_date as varchar), regexp_replace(upper(r.name_key), '[^A-Z0-9]', '', 'g')
                                               from nsw_runner r join nsw_meeting m using(key)""").fetchall()}
    for r in rows:
        if r.get('horse_key'): r['in_database'] = 'yes' if (r['meeting_date'], r['horse_key']) in have else 'no'
cols = ['post_id', 'version', 'date_gmt', 'modified_gmt', 'available_from_utc', 'captured_utc', 'title', 'meeting_heading', 'meeting_date', 'category',
        'race_no', 'saddlecloth', 'horse', 'horse_key', 'text', 'in_database', 'parse_note']
with open(out, 'w', newline='', encoding='utf-8') as fh:
    w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
from collections import Counter
print('notices', len(rows), '| posts', len(vcount), '| tied to a horse', sum(1 for r in rows if r.get('horse')), '| categories', dict(Counter(r['category'] for r in rows).most_common(12)))
