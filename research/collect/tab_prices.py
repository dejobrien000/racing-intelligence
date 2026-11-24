"""TAB fixed-odds price snapshot -> matched, timestamped quotes (DISPLAY LAYER ONLY; never read by any model).

Input: prices/<date>/tab_<stamp>.raw.txt, the racecards as returned by TAB's racing info-service
(api.beta.tab.com.au/v1/tab-info-service/racing/dates/<date>/meetings/R/<venue>/races/<n>), one block per race:
  RACE|venue|race|fixedOddsUpdateTime|oddsUpdateTime|hasFixedOdds
  n|name|returnWin|returnPlace|bettingStatus
Each TAB runner is matched to OUR field by meeting + race + runner number AND verified horse name. Only matched,
Open runners produce quotes. Earlier snapshots are never touched (write-once outputs).
Checks per race: TAB fixed-odds book (sum of 1/win over open runners) must be 1.00-1.60, else the race's quotes are held.
Usage (from research/): python3 collect/tab_prices.py 20261125 tab_20261124T205717Z [window_start_utc]"""
import sys, os, re, json, csv
D, STEM = sys.argv[1], sys.argv[2]; WSTART = sys.argv[3] if len(sys.argv) > 3 else None
DATE = f'{D[:4]}-{D[4:6]}-{D[6:]}'; base = f'prices/{D}'
CAP = re.search(r'(\d{8}T\d{6}Z)', STEM).group(1); CAP_ISO = f'{CAP[:4]}-{CAP[4:6]}-{CAP[6:8]}T{CAP[9:11]}:{CAP[11:13]}:{CAP[13:15]}Z'
VENUE = {'IPS': 'Ipswich', 'WYO': 'Wyong', 'GEL': 'Geelong', 'STR': 'Strathalbyn', 'ABN': 'Albany', 'LAU': 'Launceston'}
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
num = lambda x: None if x in ('', 'null', None) else float(x)

races, cur = [], None
for line in open(f'{base}/{STEM}.raw.txt'):
    line = line.strip()
    if not line or line.startswith('#'): continue
    p = line.split('|')
    if p[0] == 'RACE':
        cur = {'venue_code': p[1], 'meeting': VENUE[p[1]], 'race_no': int(p[2]), 'fixed_odds_update_utc': None if p[3] == 'null' else p[3],
               'tote_update_utc': p[4], 'has_fixed_odds': p[5] == 'true', 'runners': []}; races.append(cur)
    else:
        cur['runners'].append({'n': int(p[0]), 'name': p[1], 'win': num(p[2]), 'place': num(p[3]), 'status': p[4]})

# our field records, as shown on the dashboard (rated runners, not-scored entries, fields-only runners)
DJ = json.load(open(f'ui/data/racing_{DATE}.json')); ours = {}
for m in DJ['meetings']:
    for r in m['races']:
        for h in r['runners']: ours[(m['name'], r['no'], h['n'])] = {'horse': h['horse'], 'our_status': h.get('status', 'rated runner')}
        for h in r.get('not_scored', []): ours[(m['name'], r['no'], h['n'])] = {'horse': h['horse'], 'our_status': h['status']}

quotes, rows, rsum = [], [], []
for rc in races:
    opn = [x for x in rc['runners'] if x['status'] == 'Open' and x['win'] and x['win'] > 1]
    book = round(sum(1 / x['win'] for x in opn), 3) if opn else None
    ok_book = book is not None and 1.0 <= book <= 1.6
    rsum.append({k: rc[k] for k in ['meeting', 'race_no', 'fixed_odds_update_utc', 'tote_update_utc', 'has_fixed_odds']} |
                {'open_runners': len(opn), 'win_book': book, 'quotes_held': bool(rc['has_fixed_odds'] and not ok_book),
                 'note': None if rc['has_fixed_odds'] else 'TAB fixed odds not offered at capture (hasFixedOdds=false)'})
    for x in rc['runners']:
        o = ours.get((rc['meeting'], rc['race_no'], x['n']))
        match = 'not in our field' if o is None else ('matched' if nk(o['horse']) == nk(x['name']) else 'NAME MISMATCH')
        rows.append({'meeting': rc['meeting'], 'race': rc['race_no'], 'n': x['n'], 'tab_name': x['name'], 'our_name': o['horse'] if o else None,
                     'match': match, 'tab_status': x['status'], 'our_status': o['our_status'] if o else None,
                     'fixed_win': x['win'] if x['status'] == 'Open' else None, 'fixed_place': x['place'] if x['status'] == 'Open' else None,
                     'captured_utc': CAP_ISO, 'tab_fixed_odds_update_utc': rc['fixed_odds_update_utc']})
        if match == 'matched' and x['status'] == 'Open' and x['win'] and x['win'] > 1 and ok_book:
            for kind, v in [('fixed_win', x['win']), ('fixed_place', x['place'])]:
                if v and v > 1:
                    quotes.append({'meeting': rc['meeting'], 'race_no': rc['race_no'], 'saddlecloth': x['n'], 'horse_tab': x['name'], 'source': 'TAB',
                                   'kind': kind, 'price': v, 'betting_status': x['status'], 'captured_utc': CAP_ISO, 'window_start_utc': WSTART,
                                   'tab_fixed_odds_update_utc': rc['fixed_odds_update_utc'], 'match': 'number+name'})
with open(f'{base}/{STEM}.jsonl', 'x') as fh:
    for q in quotes: fh.write(json.dumps(q) + '\n')
with open(f'{base}/{STEM}_races.json', 'x') as fh: json.dump({'captured_utc': CAP_ISO, 'window_start_utc': WSTART, 'source': 'TAB racing info-service racecards', 'races': rsum}, fh, indent=1)
with open(f'{base}/{STEM}_match.csv', 'x', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
import collections
print('races', len(races), '| fixed odds offered', sum(r['has_fixed_odds'] for r in races), '| quotes', len(quotes), '| runners priced', len({(q['meeting'], q['race_no'], q['saddlecloth']) for q in quotes}))
print('match', dict(collections.Counter(r['match'] for r in rows)))
print('held races (book check)', [(r['meeting'], r['race_no'], r['win_book']) for r in rsum if r['quotes_held']])
print('books', [(r['meeting'][:3], r['race_no'], r['win_book']) for r in rsum if r['win_book']])
for r in rows:
    if r['match'] != 'matched': print('  ', r['meeting'], r['race'], r['n'], r['tab_name'], '| ours:', r['our_name'], r['match'])
dis = [r for r in rows if r['match'] == 'matched' and ((r['tab_status'] != 'Open') != (('scratch' in str(r['our_status'])) or r['our_status'] == 'probable emergency'))]
print('status disagreements (TAB vs our field):'); [print('  ', d['meeting'], d['race'], d['n'], d['tab_name'], 'TAB', d['tab_status'], '| ours', d['our_status']) for d in dis]
