"""Emergency check (Batch 19 A1): for one race date, classify every unscratched emergency in the 7:30am TAB capture with the national
gained-start count rule (an emergency has gained a start when the number of main-field scratchings already listed by TAB reaches its
place in the emergency order), then compare with who actually ran (results capture). Also reports the original rule (every emergency
left out) and Queensland's rule (every unscratched emergency counted once the capture is treated as after scratchings close).
Only TAB's explicit scratch statuses count as scratchings; any other status is neither a scratching nor a start.
Usage (from research/): python3 ops/check_emergencies.py <YYYYMMDD> [<morning raw>] [<results raw>] -> prints a table and writes
outputs/emergency_check_<YYYYMMDD>.json"""
import sys, glob, json, pandas as pd
D = sys.argv[1]
MR = sys.argv[2] if len(sys.argv) > 2 else sorted(glob.glob(f'collect/national/{D}/tab_*.raw.txt'))[0]
RR = sys.argv[3] if len(sys.argv) > 3 else (sorted(glob.glob(f'collect/national/{D}/results_*.raw.txt')) or [None])[-1]
SCR = ('latescratched', 'scratched')

def parse(p):
    rows, ven, rn, state = [], None, None, {}
    for l in open(p):
        l = l.strip(); q = l.split('|')
        if not l or l.startswith('#'): continue
        if q[0] == 'MEET': state[q[1]] = q[3] if len(q) > 3 else None; continue
        if q[0] == 'RACES': continue
        if q[0] == 'RACE': ven, rn = q[1], int(q[2]); continue
        if ven and len(q) >= 12 and q[0].isdigit():
            rows.append({'ven': ven, 'state': state.get(ven), 'race': rn, 'n': int(q[0]), 'name': q[1], 'emergency': q[7].lower() == 'true', 'status': q[10], 'last': q[11]})
    return pd.DataFrame(rows)

M = parse(MR); out = []
for (v, r), g in M.groupby(['ven', 'race']):
    scr = g.status.str.lower().isin(SCR); k = int((~g.emergency & scr).sum())
    em = g[g.emergency & ~scr].sort_values('n')
    for i, (_, e) in enumerate(em.iterrows()):
        out.append({'ven': v, 'state': e.state, 'race': r, 'n': int(e.n), 'name': e['name'], 'status_at_capture': e.status, 'main_field_scratchings_at_capture': k,
                    'national_rule_gained': i < k, 'qld_rule_counted': True})
O = pd.DataFrame(out)
res = {'date': D, 'morning_capture': MR, 'results_capture': RR, 'unscratched_emergencies_at_capture': int(len(O))}
if RR and len(O):
    R = parse(RR); O = O.merge(R[['ven', 'race', 'n', 'status', 'last']].rename(columns={'status': 'status_at_results', 'last': 'finish'}), on=['ven', 'race', 'n'], how='left')
    O['started'] = O.status_at_results.notna() & ~O.status_at_results.fillna('').str.lower().isin(SCR)
    O['result_found'] = O.status_at_results.notna()
    for rule in ['national_rule_gained', 'qld_rule_counted']:
        t = O[O.result_found]
        res[rule] = {'counted_and_started': int((t[rule] & t.started).sum()), 'counted_but_did_not_start': int((t[rule] & ~t.started).sum()),
                     'left_out_but_started': int((~t[rule] & t.started).sum()), 'left_out_and_did_not_start': int((~t[rule] & ~t.started).sum())}
    res['original_rule'] = {'left_out_but_started': int(O[O.result_found].started.sum()), 'left_out_and_did_not_start': int((~O[O.result_found].started).sum())}
    res['no_result_found'] = int((~O.result_found).sum())
    res['by_state'] = {s: {'emergencies': int(len(g)), 'national_rule_correct': int((g.national_rule_gained == g.started).sum())} for s, g in O[O.result_found].groupby('state')}
print(O.to_string(index=False) if len(O) else 'no unscratched emergencies'); print(json.dumps(res, indent=1))
O.to_csv(f'outputs/emergency_check_{D}.csv', index=False); json.dump(res, open(f'outputs/emergency_check_{D}.json', 'w'), indent=1)
