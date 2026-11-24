"""Daily 7:30am run, last step: settle YESTERDAY from TAB's completed racecards (evaluation layer; no model reads this).
  python3 ops/settle_yesterday.py <yesterday YYYYMMDD> <results raw> [today YYYYMMDD]
Results raw = same racecard format as ops/daily_build.py, read the morning after (finish column filled).
Definitions (Damo, 25 Nov 2026):
  OPEN  = TAB fixed win/place price captured at our 7:30am run on race day.
  CLOSE = the final TAB fixed win/place price shown in TAB's racecard for the completed race. Missing if TAB does not
          show it; never replaced by tote dividends, Betfair or starting price.
Paper bets: 1 unit on each frozen top pick (top-rated runner of each rated race), settled at OPEN (and, for comparison,
at CLOSE). Win: profit = price - 1 if it won, else -1. Place: paid on top 3 with 8+ starters, top 2 with 5-7, none with
4 or fewer. Scratched selection = void. No quote = listed, excluded from returns. Late-scratching deductions: TAB does not
show them in the racecard, so none are applied (stated on the dashboard). Quoted prices are not executed bets."""
import sys, os, re, json, csv
Y = sys.argv[1]; RAW = sys.argv[2]; T = sys.argv[3] if len(sys.argv) > 3 else None
ydate = f'{Y[:4]}-{Y[4:6]}-{Y[6:]}'; yfile = f'ui/data/racing_{ydate}.json'
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
num = lambda x: float(x) if x not in (None, '', 'null', 'None', '-') else None
DJ = json.load(open(yfile)); res, cur = {}, None
for line in open(RAW, encoding='utf-8'):
    p = [x.strip() for x in line.rstrip('\n').split('|')]
    if not p[0] or p[0].startswith('#') or p[0] == 'MEET': continue
    if p[0] == 'RACE': cur = (p[1], int(p[2])); res[cur] = {'cap': p[10] if len(p) > 10 else None, 'run': {}}
    elif cur:
        res[cur]['run'][int(p[0])] = {'name': p[1], 'win': num(p[8] if len(p) > 8 else None), 'place': num(p[9] if len(p) > 9 else None),
                                     'status': p[10] if len(p) > 10 else None, 'finish': p[11] if len(p) > 11 and p[11] not in ('', '-', 'null') else None}
code = lambda m: m.get('tab_code') or {'Ipswich': 'IPS', 'Wyong': 'WYO', 'Geelong': 'GEL', 'Strathalbyn': 'STR', 'Albany': 'ABN', 'Launceston': 'LAU'}.get(m['name'])
rows = []
for m in DJ['meetings']:
    for r in m['races']:
        rr = res.get((code(m), r['no']))
        if not rr: continue
        starters = sum(1 for x in rr['run'].values() if x['finish'])
        for h in r['runners']:
            x = rr['run'].get(h['n'])
            if not x or nk(x['name']) != nk(h['horse']): continue
            mk = h.get('market') or {}
            if mk.get('fixed_win'): h['open'] = {'win': mk['fixed_win']['price'], 'place': (mk.get('fixed_place') or {}).get('price'), 'captured_utc': mk['fixed_win']['captured_utc'], 'source': 'TAB fixed'}
            scr = (x['status'] or '').lower() in ('latescratched', 'scratched')
            h['finish'] = 'scratched' if scr else x['finish']
            h['close'] = ({'win': x['win'], 'place': x['place'], 'captured_utc': rr['cap'], 'tab_status': x['status'], 'source': 'TAB fixed (completed racecard)'}
                          if (x['win'] and x['win'] > 1 and not scr) else {'missing': 'TAB racecard showed no final fixed price' if not scr else 'scratched', 'captured_utc': rr['cap']})
        r['starters'] = starters
for s in DJ['roi']['selections']:
    m = next(x for x in DJ['meetings'] if x['name'] == s['meeting']); r = next(x for x in m['races'] if x['no'] == s['race']); h = next(x for x in r['runners'] if x['n'] == s['n'])
    o, c, f = h.get('open') or {}, h.get('close') or {}, h.get('finish'); n = r.get('starters') or 0
    s.update({'price': o.get('win') or s.get('price'), 'price_source': 'TAB fixed (OPEN, 7:30am run)' if o.get('win') else s.get('price_source'), 'price_time_utc': o.get('captured_utc') or s.get('price_time_utc'), 'open_win': o.get('win'), 'open_place': o.get('place'), 'open_utc': o.get('captured_utc'), 'close_win': c.get('win'), 'close_place': c.get('place'), 'result': f})
    if f is None: s['settlement'] = 'no result yet'; continue
    if f == 'scratched': s.update({'settlement': 'void (scratched)', 'paper_return': 0.0}); continue
    won = str(f) == '1'; places = 3 if n >= 8 else 2 if n >= 5 else 0; placed = str(f).isdigit() and 1 <= int(f) <= places
    s['paper_return'] = (round(o['win'] - 1, 2) if won else -1.0) if o.get('win') else None
    s['paper_return_close'] = (round(c['win'] - 1, 2) if won else -1.0) if c.get('win') else None
    s['paper_place_return'] = (round(o['place'] - 1, 2) if placed else -1.0) if (o.get('place') and places) else None
    s['movement'] = round(c['win'] / o['win'], 3) if (o.get('win') and c.get('win')) else None
    s['settlement'] = ('won' if won else 'placed' if placed else 'lost') + ('' if o.get('win') else ' (no open price: excluded)')
st = [s for s in DJ['roi']['selections'] if s.get('paper_return') is not None and s.get('settlement', '').startswith(('won', 'placed', 'lost'))]
DJ['roi']['paper'] = {'selections': len(DJ['roi']['selections']), 'priced': sum(1 for s in DJ['roi']['selections'] if s.get('open_win')), 'settled': len(st),
                      'winners': sum(1 for s in st if s['paper_return'] > 0), 'return_units': round(sum(s['paper_return'] for s in st), 2),
                      'roi_pct': round(100 * sum(s['paper_return'] for s in st) / len(st), 1) if st else None,
                      'shortened': sum(1 for s in st if s.get('movement') and s['movement'] < 1), 'drifted': sum(1 for s in st if s.get('movement') and s['movement'] > 1)}
DJ['roi']['status'] = 'settled' if st else DJ['roi'].get('status', 'waiting')
DJ['roi']['definitions'] = 'OPEN = TAB fixed price at the 7:30am run. CLOSE = final TAB fixed price in the completed racecard (missing if not shown). Paper returns at OPEN, 1 unit. No late-scratching deductions applied (TAB does not publish them in the racecard). Quoted prices are not bets placed.'
json.dump(DJ, open(yfile, 'w'), separators=(',', ':'))
# append to the running ledger (one row per settled selection; never rewritten)
L = 'outputs/ledger.csv'; os.makedirs('outputs', exist_ok=True); new = not os.path.exists(L)
seen = {(r['date'], r['meeting'], r['race']) for r in csv.DictReader(open(L))} if not new else set()
cols = ['date', 'meeting', 'state', 'race', 'n', 'horse', 'model_version', 'win_chance', 'classification', 'open_win', 'open_place', 'open_utc', 'close_win', 'close_place',
        'result', 'settlement', 'paper_return', 'paper_return_close', 'paper_place_return', 'movement']
with open(L, 'a', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction='ignore')
    if new: w.writeheader()
    for s in DJ['roi']['selections']:
        if s.get('settlement') and s['settlement'] != 'no result yet' and (ydate, s['meeting'], str(s['race'])) not in seen: w.writerow({**s, 'date': ydate})
# running history into today's day file
if T:
    tfile = f"ui/data/racing_{T[:4]}-{T[4:6]}-{T[6:]}.json"
    if os.path.exists(tfile):
        rows = [r for r in csv.DictReader(open(L)) if r['paper_return'] not in ('', None)]
        def agg(rs): return {'bets': len(rs), 'wins': sum(float(r['paper_return']) > 0 for r in rs), 'return_units': round(sum(float(r['paper_return']) for r in rs), 2),
                             'roi_pct': round(100 * sum(float(r['paper_return']) for r in rs) / len(rs), 1) if rs else None}
        TJ = json.load(open(tfile))
        TJ['history'] = {'all': agg(rows), 'by_strength': {k: agg([r for r in rows if r['classification'] == k]) for k in sorted({r['classification'] for r in rows})},
                         'by_model': {k: agg([r for r in rows if r['model_version'] == k]) for k in sorted({r['model_version'] for r in rows})},
                         'by_state': {k: agg([r for r in rows if r['state'] == k]) for k in sorted({r['state'] for r in rows})}, 'from': min((r['date'] for r in rows), default=None)}
        json.dump(TJ, open(tfile, 'w'), separators=(',', ':'))
print('settled', DJ['roi']['paper'])
