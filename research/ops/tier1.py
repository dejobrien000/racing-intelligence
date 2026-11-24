"""Racing Intelligence - Tier 1 race-day process (runs in any cloud session; needs no history database, no PC).
Works on the dashboard's published day file (data/racing_<date>.json). Market prices are a DISPLAY layer only.

  python3 tier1.py due   <day.json> <from_utc> <to_utc>        races starting in [from, to): 'start_utc|VEN|race|url'
  python3 tier1.py apply <day.json> <raw.txt> <out.json>         TAB racecard snapshot -> prices, scratchings, movement
  python3 tier1.py merge <new.json> <published.json> <out.json>  keep price history/results already published
Raw format (one block per race, values as returned by TAB's racing info-service racecard):
  RACE|VEN|race|fixedOddsUpdateTime|oddsUpdateTime|hasFixedOdds|captured_utc
  n|name|returnWin|returnPlace|bettingStatus|finish      (finish = finishing position once the race is run, else -)
Rules: a runner is priced only if TAB's number AND name match our field; LateScratched -> 'Scratched per TAB';
hasFixedOdds=false -> 'Not offered yet (TAB)'; quotes after a race's start never count for the returns ledger, whose
quote is the last fixed win price at or before start minus 5 minutes. 1-unit paper bets; scratched selection = void."""
import sys, re, json, datetime as dt
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
VEN = {'Ipswich': 'IPS', 'Wyong': 'WYO', 'Geelong': 'GEL', 'Strathalbyn': 'STR', 'Albany': 'ABN', 'Launceston': 'LAU'}
JUR = lambda m: 'QLD' if m['state'] == 'QLD' else 'NSW'
T = lambda s: dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def start_utc(D, r): return dt.datetime.fromisoformat(D['date'] + 'T00:00:00+10:00') + dt.timedelta(minutes=r['time_brisbane_min'] or 0)
def code(m): return m.get('tab_code') or VEN.get(m['name'])
def iso(x): return x.astimezone(dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def due(D, a, b):
    for m in D['meetings']:
        for r in m['races']:
            s = start_utc(D, r)
            if a <= s < b and code(m):
                print(f"{iso(s)}|{code(m)}|{r['no']}|https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/{D['date']}/meetings/R/{code(m)}/races/{r['no']}?jurisdiction={JUR(m)}")

def parse(path):
    races, cur = [], None
    for line in open(path):
        p = line.strip().split('|')
        if not p[0] or p[0].startswith('#'): continue
        if p[0] == 'RACE':
            cur = {'ven': p[1], 'no': int(p[2]), 'fx': None if p[3] in ('null', '') else p[3], 'has': p[5] == 'true', 'cap': p[6], 'run': []}; races.append(cur)
        else:
            f = lambda i: p[i] if len(p) > i and p[i] not in ('', 'null', '-') else None
            cur['run'].append({'n': int(p[0]), 'name': p[1], 'win': float(f(2)) if f(2) else None, 'place': float(f(3)) if f(3) else None, 'status': f(4), 'finish': f(5)})
    return races

def apply(D, races):
    bym = {code(m): m for m in D['meetings'] if code(m)}; caps = []
    for rc in races:
        m = bym.get(rc['ven']); r = next((x for x in m['races'] if x['no'] == rc['no']), None) if m else None
        if r is None: continue
        cap = rc['cap']; caps.append(cap); late = T(cap) >= start_utc(D, r)
        r.setdefault('tab', {}).update({'checked_utc': cap, 'has_fixed_odds': rc['has'], 'fixed_odds_update_utc': rc['fx']})
        ours = {h['n']: h for h in r['runners']}
        for x in rc['run']:
            h = ours.get(x['n'])
            if h is None or nk(h['horse']) != nk(x['name']): continue          # unmatched: never priced
            if x['finish']: h['finish'] = x['finish']
            if late: continue                                                  # no market updates once the race has started
            if x['status'] and x['status'] != 'Open':
                h['market'] = {'note': 'Scratched per TAB', 'captured_utc': cap}
                if m.get('rated') and h.get('status', 'runner') == 'runner': r.setdefault('scratched_since_rating', []).append(h['n'])
                if not m.get('rated') and h.get('status') in ('runner', 'probable emergency'): h['status'] = 'scratched (TAB)'
                continue
            if not rc['has'] or not x['win'] or x['win'] <= 1:
                h['market'] = {'note': 'Not offered yet (TAB)', 'captured_utc': cap}; continue
            mk = h.get('market') if isinstance(h.get('market'), dict) and h['market'].get('fixed_win') else {'quotes': 0}
            first = mk.get('first_win') or (mk.get('fixed_win') and {'price': mk['fixed_win']['price'], 'captured_utc': mk['fixed_win']['captured_utc']}) or {'price': x['win'], 'captured_utc': cap}
            mk.update({'fixed_win': {'price': x['win'], 'source': 'TAB', 'captured_utc': cap}, 'first_win': first, 'quotes': mk.get('quotes', 0) + 1})
            if x['place'] and x['place'] > 1: mk['fixed_place'] = {'price': x['place'], 'source': 'TAB', 'captured_utc': cap}
            mk.pop('note', None); h['market'] = mk
            h.setdefault('mh', []).append([cap, x['win']]); mk['quotes'] = len(h['mh'])
            if T(cap) <= start_utc(D, r) - dt.timedelta(minutes=5): h['ledger_quote'] = {'price': x['win'], 'captured_utc': cap}
    finish(D, caps)

def finish(D, caps):
    # leaderboard + returns ledger from the meetings (single source of truth)
    lb = {(e['meeting'], e['race'], e['n']): e for e in D.get('leaderboard', [])}
    for m in D['meetings']:
        for r in m['races']:
            for h in r['runners']:
                e = lb.get((m['name'], r['no'], h['n']))
                if e: e['market'] = h.get('market')
    sel = D['roi']['selections']
    for s in sel:
        m = next(x for x in D['meetings'] if x['name'] == s['meeting']); r = next(x for x in m['races'] if x['no'] == s['race']); h = next(x for x in r['runners'] if x['n'] == s['n'])
        q = h.get('ledger_quote')
        if q: s.update({'price': q['price'], 'price_source': 'TAB fixed win', 'price_time_utc': q['captured_utc']})
        if (h.get('market') or {}).get('note') == 'Scratched per TAB' and not q: s['settlement'] = 'void (scratched)'
        if h.get('finish'):
            s['result'] = h['finish']; won = str(h['finish']).strip() == '1'
            s['settlement'] = ('won' if won else 'lost') if s['price'] else ('won (no quote)' if won else 'lost (no quote)')
            s['paper_return'] = (round(s['price'] - 1, 2) if won else -1.0) if s['price'] else None
    st = [s for s in sel if s.get('paper_return') is not None]
    D['roi']['paper'] = {'selections': len(sel), 'priced': sum(1 for s in sel if s['price']), 'settled': len(st),
                         'winners': sum(1 for s in st if s['paper_return'] > 0), 'return_units': round(sum(s['paper_return'] for s in st), 2),
                         'roi_pct': round(100 * sum(s['paper_return'] for s in st) / len(st), 1) if st else None}
    g = {}
    for s in st:
        for key in [('Meeting', s['meeting']), ('State', s['state']), ('Strength', s['classification']), ('Model', s['model_version'])]:
            a = g.setdefault(key, {'group': key[0], 'value': key[1], 'bets': 0, 'wins': 0, 'ret': 0.0, 'prices': []})
            a['bets'] += 1; a['wins'] += s['paper_return'] > 0; a['ret'] += s['paper_return']; a['prices'].append(s['price'])
    D['roi']['groups'] = [{'group': a['group'], 'value': a['value'], 'bets': a['bets'], 'win_rate_pct': round(100 * a['wins'] / a['bets'], 1),
                           'avg_price': round(sum(a['prices']) / len(a['prices']), 2), 'return_units': round(a['ret'], 2), 'roi_pct': round(100 * a['ret'] / a['bets'], 1)} for a in g.values()]
    if st: D['roi']['status'] = 'settling' if len(st) < len(sel) else 'settled'
    priced = sum(1 for m in D['meetings'] for r in m['races'] for h in r['runners'] if (h.get('market') or {}).get('fixed_win'))
    D.setdefault('markets', {}).update({'runners_priced': priced})
    for c in D.get('completeness', {}).get('rows', []):
        m = next((x for x in D['meetings'] if x['name'] == c['meeting']), None)
        if m: c['prices'] = sum(1 for r in m['races'] for h in r['runners'] if (h.get('market') or {}).get('fixed_win'))
    if caps:
        D['freshness']['latest_update_utc'] = max([D['freshness'].get('latest_update_utc') or ''] + caps)
        D['freshness']['prices_updated_utc'] = max(caps)

def merge(N, P):
    """carry price history, ledger quotes and results from the published file into a freshly exported one"""
    old = {(m['name'], r['no'], h['n'], nk(h['horse'])): h for m in P['meetings'] for r in m['races'] for h in r['runners']}
    for m in N['meetings']:
        for r in m['races']:
            ro = next((x for x in next((y for y in P['meetings'] if y['name'] == m['name']), {'races': []})['races'] if x['no'] == r['no']), None)
            if ro and ro.get('tab') and (not r.get('tab') or ro['tab']['checked_utc'] > r['tab']['checked_utc']): r['tab'] = ro['tab']
            for h in r['runners']:
                o = old.get((m['name'], r['no'], h['n'], nk(h['horse'])))
                if not o: continue
                for k in ['mh', 'ledger_quote', 'finish']:
                    if o.get(k) and not h.get(k): h[k] = o[k]
                om, nm = o.get('market') or {}, h.get('market') or {}
                if (om.get('fixed_win') or {}).get('captured_utc', '') > (nm.get('fixed_win') or {}).get('captured_utc', '') or (om.get('note') and om.get('captured_utc', '') > (nm.get('captured_utc') or (nm.get('fixed_win') or {}).get('captured_utc', ''))): h['market'] = om
    finish(N, [])

if __name__ == '__main__':
    cmd = sys.argv[1]; D = json.load(open(sys.argv[2]))
    if cmd == 'due': due(D, T(sys.argv[3]), T(sys.argv[4]))
    elif cmd == 'apply': apply(D, parse(sys.argv[3])); json.dump(D, open(sys.argv[4], 'w'), separators=(',', ':')); print('ok', D['markets']['runners_priced'], 'priced |', D['roi']['paper'])
    elif cmd == 'merge': merge(D, json.load(open(sys.argv[3]))); json.dump(D, open(sys.argv[4], 'w'), separators=(',', ':')); print('merged', D['markets']['runners_priced'], 'priced')
