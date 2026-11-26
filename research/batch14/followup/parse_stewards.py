"""Parse the stewards' reports ALREADY HELD (no new collection): QRIC (Queensland, branch raw-rqstewards, 2,827 meeting reports Oct 2022 -
Nov 2026, HTML) and Racing SA stipendiary stewards' reports (branch raw-sagear, PDFs, Oct 2022 - Nov 2024 so far).
Output (research staging, never read by ratings): research/staging/stewards/stewards_events.csv.gz, one row per horse paragraph or mention:
  state, date, venue_text, race_no, horse (name key), role ('subject' = the paragraph is about this horse; 'mentioned' = named inside another
  horse's paragraph: lower certainty), text (the paragraph or, for mentions, the sentence), one 0/1 column per event tag, first_mark_m
  (first distance mark mentioned, e.g. 'near the 400m' -> 400; meaning differs by phrase), phase flags, negated_tags.
Tags are REPORTED events (what stewards wrote), not observed or inferred. An absent comment is not evidence that nothing happened.
Timing: reports are written after the meeting (post-race, retrospective); usable for later races only. Report publication times are not held.
Negation: a tag is not set when 'no', 'not', 'nil', 'did not', 'didn't', 'never' or 'without' appears within the four words before it (the
cover tags are phrased negatively by nature and are handled by their own patterns). Vet: 'no (visible|significant) abnormalit' is recorded
as vet_clear, any other veterinary finding as vet_finding."""
import gzip, json, re, html, subprocess, os, sys, pandas as pd
RQ, SA = '/tmp/stew/rq', '/tmp/stew/sa'
OUT = '/home/claude/racing-intelligence/research/staging/stewards/stewards_events.csv.gz'
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\((NZ|IRE|GB|USA|FR|JPN|GER|AUS|ARG|BRZ|CAN|CHI|SAF|ITY)\)', '', str(s).upper()))
TAGS = {
    'held_up': r"held up|unable to (?:obtain|gain|secure) (?:a )?clear run|could not (?:obtain|gain) (?:a )?clear run|awaiting (?:a )?(?:clear )?run|denied (?:a )?clear run|blocked for (?:a )?run|without (?:a )?clear run|clear running (?:was )?(?:not|un)available|held up for (?:clear )?running",
    'checked': r"\bchecked\b|\bsteadied\b|tightened for room|\bcrowded\b|\bhampered\b|\bimpeded\b|\binconvenienced\b|lost (?:its|his|her) rightful running|clipped (?:the )?heels|awkwardly placed|awkward on the heels",
    'restrained': r"\brestrained\b|\bstood up\b",
    'bumped': r"\bbumped\b|made contact|heavy contact",
    'wide': r"\b(?:three|four|five|six|3|4|5|6)[- ]wide\b|raced wide|wide throughout|caught wide|trapped wide|wide (?:on|rounding|approaching) the (?:home )?turn|wide in the (?:early|middle) stages",
    'wide_no_cover': r"(?:with|having) no cover|without cover|without any cover|unable to (?:obtain|find|gain|get) cover|no cover",
    'wide_cover': r"wide with cover|(?:obtained|found|with) cover",
    'unable_improve': r"unable to improve|did not improve|failed to improve|unable to (?:make|run on)|could not improve",
    'disappointed_run': r"disappointed for (?:a )?run",
    'weakened': r"\bweakened\b|gave ground|\btired\b|\bfaded\b|dropped out|failed to (?:finish|run) on|did not (?:finish|run) on",
    'rider_concern': r"(?:rider|jockey)[^.]{0,40}(?:reported|stated|explained|advised|could offer no|offered no)|when (?:asked|questioned)",
    'performance_concern': r"did not respond|disappointing|below (?:market )?expectations|never travelled|not travel|travelled (?:poorly|flat)|felt (?:flat|short|wrong|amiss)|lacked|labou?red|did not (?:handle|finish off)|dower|lost (?:its|his|her) action|short in (?:its|his|her) action|resented",
    'vet_finding': r"(?:veterinary|vet)[^.]{0,60}(?:revealed|found|showed|diagnosed)(?![^.]{0,30}no (?:visible|significant|abnormal))|\blame\b|bled|epistaxis|arrhythmia|cardiac|respiratory|lacerat|injur",
    'vet_clear': r"no (?:visible |significant )?abnormalit",
    'slow_begin': r"slow to begin|began awkwardly|missed the start|jumped awkwardly|dwelt|began (?:very )?slowly",
    'over_raced': r"over-?raced|raced keenly|pulled hard|raced ungenerously",
    'laid_hung': r"laid (?:in|out)|hung (?:in|out)|lay in|lay out",
    'shifted': r"shifted (?:in|out)",
}
NEG = re.compile(r"\b(?:no|not|nil|did not|didn't|never|without)\b(?:\W+\w+){0,4}\W*$", re.I)
MARK = re.compile(r"(?:near|passing|approaching|leaving|at|inside|after|before|from|abeam|soon after|shortly after|over the (?:final|last|concluding)) (?:the )?(\d{2,4}) ?m(?:etres)?\b", re.I)
PH = {'ph_start': r"jump|began|start|slow to begin", 'ph_turn': r"home turn|rounding|turn", 'ph_straight': r"straight|final stages|concluding stages|over the final|near the line|(?:near|passing|inside) the (?:[1-3]\d{2}|50)m",
      'ph_early': r"early stages|middle stages|first turn|back straight"}
def tag(text):
    r = {}; neg = []
    for k, p in TAGS.items():
        hit = 0
        for m in re.finditer(p, text, re.I):
            if k not in ('wide_no_cover', 'wide_cover', 'vet_clear', 'held_up') and NEG.search(text[max(0, m.start() - 40):m.start()]): neg.append(k); continue
            hit = 1; break
        r[k] = hit
    if r['vet_clear']: r['vet_finding'] = 0 if not re.search(r"\blame\b|bled|epistaxis|arrhythmia|lacerat|injur", text, re.I) else r['vet_finding']
    mk = MARK.search(text); r['first_mark_m'] = int(mk.group(1)) if mk else None
    for k, p in PH.items(): r[k] = int(bool(re.search(p, text, re.I)))
    r['negated_tags'] = ','.join(sorted(set(neg))); return r
RACE = re.compile(r"^\s*RACE\s+(\d{1,2})\s*[:\-–]", re.I)
SUBJ = re.compile(r"^\s*([A-Z][A-Z0-9'’\.\- ]{1,30}?(?:\s\((?:NZ|IRE|GB|USA|FR|JPN|GER|AUS)\))?)\s*(?:\([A-Za-z\.\s'\-]+\))?\s*[–\-:]\s+(.*)$")
def paragraphs(text):
    """split into race blocks and horse paragraphs (a paragraph starts with an upper-case name followed by a dash)"""
    race, cur, out = None, None, []
    for line in text.split('\n'):
        ln = line.strip()
        if not ln:
            if cur: out.append(cur); cur = None
            continue
        m = RACE.match(ln)
        if m:
            if cur: out.append(cur); cur = None
            race = int(m.group(1)); continue
        s = SUBJ.match(ln)
        if race and s and s.group(1).strip().upper() == s.group(1).strip() and len(s.group(1).strip()) >= 3 and not re.match(r'^(RACE|GENERAL|STEWARDS|TRACK|RAIL|WEATHER|OFFICIALS|SUPPLEMENTARY|NOTE|JUDGE|CLERK|SCRATCHINGS|PROTEST|PENALTIES|FINES|SUSPENSIONS|AR\d)', s.group(1).strip()):
            if cur: out.append(cur)
            cur = [race, s.group(1).strip(), s.group(2).strip()]
        elif cur: cur[2] += ' ' + ln
    if cur: out.append(cur)
    return out
rows = []
def emit(state, date, venue, paras):
    names = {nk(p[1]) for p in paras}
    for race, name, txt in paras:
        r = {'state': state, 'date': date, 'venue_text': venue, 'race_no': race, 'horse': nk(name), 'role': 'subject', 'text': txt[:1500]}; r.update(tag(txt)); rows.append(r)
        # other horses named in this paragraph: keep the sentence that names them (lower certainty: who did what to whom is not parsed)
        for sent in re.split(r'(?<=[.;])\s+', txt):
            for cand in re.findall(r"\b([A-Z][A-Z'’\.\-]+(?: [A-Z][A-Z'’\.\-]+){0,3})\b", sent):
                k = nk(cand)
                if k in names and k != nk(name):
                    m_ = {'state': state, 'date': date, 'venue_text': venue, 'race_no': race, 'horse': k, 'role': 'mentioned', 'text': sent[:600]}; m_.update(tag(sent)); rows.append(m_)
n_rq = 0
with gzip.open(f'{RQ}/reports.jsonl.gz', 'rt') as fh:
    for line in fh:
        j = json.loads(line); t = j.get('report_html') or ''
        t = re.sub(r'<br\s*/?>|</p>|</div>|</li>', '\n', t); t = html.unescape(re.sub(r'<[^>]+>', '', t)).replace('\xa0', ' ')
        head = ' '.join(t.split('\n')[:12]); venue = j['code'].replace('%20', ' ')
        emit('QLD', pd.to_datetime(j['date']).date(), venue, paragraphs(t)); n_rq += 1
F = pd.read_csv(f'{SA}/files.csv'); F = F[(F.kind == 'stewards') & (F.http == 200)]; n_sa = 0
for _, f in F.iterrows():
    p = f'{SA}/{f.saved}'
    if not os.path.exists(p): continue
    t = subprocess.run(['pdftotext', '-layout', p, '-'], capture_output=True, text=True).stdout
    t = re.sub(r'[ \t]{2,}', ' ', t)
    emit('SA', pd.to_datetime(f.meeting_date).date(), str(f.meeting_id), paragraphs(t)); n_sa += 1
D = pd.DataFrame(rows); D.to_csv(OUT, index=False, compression='gzip')
tags = list(TAGS)
print('reports parsed QRIC', n_rq, 'SA', n_sa, '| rows', len(D), D.role.value_counts().to_dict())
print('subject paragraphs per report: QLD', round((D[(D.state == 'QLD') & (D.role == 'subject')].groupby(['date', 'venue_text']).size()).mean(), 1),
      'SA', round((D[(D.state == 'SA') & (D.role == 'subject')].groupby(['date', 'venue_text']).size()).mean(), 1))
print((D[D.role == 'subject'].groupby('state')[tags].mean() * 100).round(1).T.to_string())
