"""Daily 7:30am run, step 1: turn TAB racecards (collected by the run, see ops/DAILY_RUN.md) into the day's field files.
Input : collect/national/<D>/tab_<stamp>.raw.txt
  MEET|VEN|meetingName|state
  RACE|VEN|raceNumber|raceName|raceStartTime(UTC)|raceDistance|trackCondition|railPosition|hasFixedOdds|fixedOddsUpdateTime|captured_utc
  n|name|barrier|weight|claim|rider|trainer|emergency|win|place|bettingStatus|finish
Output: races.csv, runners.csv, calendar.json (same schema as the hand-built 25 Nov files), a Racing-Queensland-format
bundle for QLD meetings (so the Queensland model scores them), prices/<D>/tab_<stamp>.raw.txt (OPEN prices), and
nat_venues.txt (NSW/VIC/ACT meetings for the national model). SA/WA/TAS/NT meetings are fields only until their
history is in the master database. Prices are written to prices/ only; no model reads that folder."""
import sys, os, re, json, gzip, hashlib, datetime as dt
from zoneinfo import ZoneInfo
D, RAW = sys.argv[1], sys.argv[2]
DATE = f'{D[:4]}-{D[4:6]}-{D[6:]}'; base = f'collect/national/{D}'; os.makedirs(base, exist_ok=True)
STATE_TZ = {'QLD': 'Australia/Brisbane', 'NSW': 'Australia/Sydney', 'ACT': 'Australia/Sydney', 'VIC': 'Australia/Melbourne', 'TAS': 'Australia/Hobart',
            'SA': 'Australia/Adelaide', 'WA': 'Australia/Perth', 'NT': 'Australia/Darwin'}
NAT, QLD = {'NSW', 'VIC', 'ACT'}, {'QLD'}
meets, races, cur = {}, [], None
for line in open(RAW, encoding='utf-8'):
    p = [x.strip() for x in line.rstrip('\n').split('|')]
    if not p[0] or p[0].startswith('#'): continue
    if p[0] == 'MEET': meets[p[1]] = {'code': p[1], 'name': p[2].title(), 'state': p[3].upper()}
    elif p[0] == 'RACE':
        cur = {'ven': p[1], 'no': int(p[2]), 'name': p[3], 'start': p[4], 'dist': p[5], 'track': p[6], 'rail': p[7], 'has': p[8] == 'true', 'fx': p[9], 'cap': p[10], 'run': []}; races.append(cur)
    elif cur is not None and len(p) >= 11:
        cur['run'].append(dict(zip(['n', 'name', 'barrier', 'weight', 'claim', 'rider', 'trainer', 'emergency', 'win', 'place', 'status', 'finish'], p + [''] * (12 - len(p)))))
nul = lambda x: None if x in ('', 'null', 'None', '-') else x
cap = max(r['cap'] for r in races); stamp = cap.replace('-', '').replace(':', '')[:15] + 'Z'
csv = lambda v: '"' + str(v).replace('"', "'") + '"' if (',' in str(v) or '"' in str(v)) else str(v)
R = ['venue,venue_code,state,tz,race_no,start_local,distance_m,race_name,class_text,track_condition,rail']
N = ['venue_code,race_no,saddlecloth,horse,barrier,trainer,jockey,weight_kg,claim,age_sex,page_status,emergency']
rq, nat, cal, problems = {}, set(), [], []
for r in races:
    m = meets.get(r['ven'])
    if m is None or m['state'] not in STATE_TZ: continue
    s = dt.datetime.fromisoformat(r['start'].replace('Z', '+00:00')).astimezone(ZoneInfo(STATE_TZ[m['state']]))
    loc = s.strftime('%I:%M%p').lstrip('0').lower(); vc = r['ven'].lower()
    R.append(','.join(csv(x) for x in [m['name'], vc, m['state'], s.tzname(), r['no'], loc, nul(r['dist']) or 0, r['name'], r['name'], nul(r['track']) or '', nul(r['rail']) or '']))
    for x in r['run']:
        if not nul(x['barrier']) or not nul(x['weight']): problems.append(f"{m['name']} R{r['no']} #{x['n']} missing barrier/weight"); continue
        scr = (x['status'] or '').lower() in ('latescratched', 'scratched')
        cl = nul(x['claim']); cl = f'a{float(cl):g}' if cl and float(cl) > 0 else ''
        N.append(','.join(csv(v) for v in [vc, r['no'], x['n'], x['name'].title(), x['barrier'], x['trainer'], nul(x['rider']) or '', x['weight'], cl, '', 'scratched' if scr else 'runner',
                                           str(str(x['emergency']).lower() == 'true')]))
    if m['state'] in NAT: nat.add(m['name'])
    if m['state'] in QLD: rq.setdefault(m['code'], []).append(r)
for c in sorted({r['ven'] for r in races}):
    m = meets.get(c)
    if m: cal.append({'name': m['name'], 'state': m['state'], 'tab_code': c, 'races': sum(1 for r in races if r['ven'] == c),
                      'fields_source': 'TAB racecards (read at the 7:30am run)'})
open(f'{base}/races.csv', 'w').write('\n'.join(R) + '\n'); open(f'{base}/runners.csv', 'w').write('\n'.join(N) + '\n')
json.dump({'date': DATE, 'source': f'TAB racing info-service meetings list and racecards, captured {cap}', 'excluded': ['non-Australian meetings'],
           'act_nt': 'ACT and NT meetings included when TAB lists them', 'meetings': cal}, open(f'{base}/calendar.json', 'w'), indent=1)
open(f'{base}/nat_venues.txt', 'w').write(','.join(sorted(nat)))
# Queensland meetings in Racing Queensland bundle format (fields from TAB; Queensland model)
if rq:
    os.makedirs(f'{base}/bundles', exist_ok=True); out = f'{base}/bundles/rqpre_{D}_snap{stamp}.jsonl.gz'; raw_sha = hashlib.sha256(open(RAW, 'rb').read()).hexdigest()
    with gzip.open(out, 'wt') as fh:
        for code, rs in rq.items():
            fields, scr = [], []
            for r in rs:
                s = dt.datetime.fromisoformat(r['start'].replace('Z', '+00:00')).astimezone(ZoneInfo('Australia/Brisbane')); sc = []
                for x in r['run']:
                    if not nul(x['barrier']) or not nul(x['weight']): continue
                    if (x['status'] or '').lower() in ('latescratched', 'scratched'): sc.append({'saddlecloth': int(x['n']), 'horse': x['name'].title()}); continue
                    fields.append({'race_no': r['no'], 'race_name': r['name'], 'distance_m': int(float(nul(r['dist']) or 0)), 'start_time': s.strftime('%I:%M%p'),
                                   'saddlecloth': int(x['n']), 'horse': x['name'].title(), 'trainer': x['trainer'], 'jockey': nul(x['rider']), 'barrier': int(float(x['barrier'])),
                                   'weight_kg': float(x['weight']), 'emergency': str(x['emergency']).lower() == 'true'})
                if sc: scr.append({'race_no': r['no'], 'horses': sc})
            v = {'kind': 'rqpre', 'date': D, 'meeting_code': code, 'track': meets[code]['name'], 'retrieved_utc': cap, 'fields_pdf_sha256': raw_sha,
                 'source': 'TAB racecards (fields, scratchings, track); Racing Queensland format for the Queensland model',
                 'conditions': {'track_condition': nul(rs[0]['track']), 'rail': nul(rs[0]['rail']), 'scratchings_close': f"Wed {DATE[8:10]}/{DATE[5:7]}/{DATE[2:4]} 07:30am"},
                 'scratchings': scr, 'fields': fields}
            fh.write(json.dumps({'key': f'rqpre:{D}:{code}:{stamp}', 'value': v}) + '\n')
    print('rq bundle', out)
# OPEN prices (display layer only) in the price-snapshot format read by collect/tab_prices.py
os.makedirs(f'prices/{D}', exist_ok=True)
with open(f'prices/{D}/tab_{stamp}.raw.txt', 'w') as fh:
    fh.write(f'# OPEN prices: TAB fixed odds at the 7:30am run, captured {cap}\n')
    for r in races:
        if r['ven'] not in meets: continue
        fh.write(f"RACE|{r['ven']}|{r['no']}|{r['fx'] or 'null'}|null|{'true' if r['has'] else 'false'}\n")
        for x in r['run']: fh.write(f"{x['n']}|{x['name']}|{x['win'] or 'null'}|{x['place'] or 'null'}|{x['status'] or 'null'}\n")
print('stamp', stamp); print('meetings', len(cal), '| national-model meetings', sorted(nat), '| queensland', sorted(m['name'] for c, m in meets.items() if c in rq))
if problems: print('PROBLEMS', len(problems), problems[:10])
