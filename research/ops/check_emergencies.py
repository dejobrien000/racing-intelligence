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
    # Batch 20 H17: morning eligibility vs eventual participation. Main-field scratchings at capture vs by the results capture.
    Rr = R.copy(); Rr['scr'] = Rr.status.fillna('').str.lower().isin(SCR)
    Mm = M.copy(); Mm['scr'] = Mm.status.fillna('').str.lower().isin(SCR)
    later = (Rr[~Rr.n.isin([])].merge(Mm[['ven', 'race', 'n', 'emergency', 'scr']], on=['ven', 'race', 'n'], suffixes=('', '_m')))
    k_res = later[~later.emergency & later.scr].groupby(['ven', 'race']).size(); k_cap = later[~later.emergency & later.scr_m].groupby(['ven', 'race']).size()
    O['main_scr_by_results'] = [int(k_res.get((v, r), 0)) for v, r in zip(O.ven, O.race)]
    O['later_main_scratchings'] = O.main_scr_by_results - O.main_field_scratchings_at_capture
    def reading(x):
        if not x.result_found: return 'no result found'
        if x.national_rule_gained and x.started: return 'eligible at capture (inferred) and ran'
        if x.national_rule_gained and not x.started: return 'admitted but did not run: later scratching or misread (check)'
        if (not x.national_rule_gained) and x.started: return ('gained a start after the capture (later scratchings; not knowable at cutoff)' if x.later_main_scratchings > 0 else 'ran although the rule left it out (rule miss)')
        return 'not eligible at capture and did not run'
    O['reading'] = O.apply(reading, axis=1); res['readings'] = O.reading.value_counts().to_dict()
    # Batch 24 (Damo 27 Nov): the six categories of record. Morning eligibility comes ONLY from the 7:30am capture (TAB statuses and the
    # gained-start count); participation and later TAB statuses are used only to verify it, never to define it.
    def category(x):
        if not x.result_found or str(x.status_at_capture).strip().lower() in ('', 'nan', 'none', 'null'): return 'eligibility uncertain'
        later_scr = str(x.status_at_results).lower() in SCR
        if x.national_rule_gained:
            if x.started: return 'eligible at the morning cutoff and started'
            if later_scr: return 'eligible at the morning cutoff, scratched later (TAB status at results: scratched)'
            return 'incorrectly admitted at the morning cutoff'
        if x.started: return ('ineligible at the morning cutoff, gained a start from later scratchings' if x.later_main_scratchings > 0
                              else 'incorrectly excluded at the morning cutoff')
        return 'ineligible at the morning cutoff and did not start'
    O['category'] = O.apply(category, axis=1); res['categories'] = O.category.value_counts().to_dict()
    res['rule_failures'] = int(O.category.isin(['incorrectly admitted at the morning cutoff', 'incorrectly excluded at the morning cutoff']).sum())
    per = later.groupby(['ven', 'race']).agg(scr_at_capture=('scr_m', 'sum'), scr_by_results=('scr', 'sum')).reset_index()
    res['races'] = {'total': int(len(per)), 'with_scratchings_before_cutoff': int((per.scr_at_capture > 0).sum()), 'with_later_scratchings': int((per.scr_by_results > per.scr_at_capture).sum())}
    res['note'] = 'eligibility at the morning cutoff is inferred from TAB statuses and emergency numbers (no official emergency order or field limit is read); participation comes from the results capture'
    res['by_state'] = {s: {'emergencies': int(len(g)), 'national_rule_correct': int((g.national_rule_gained == g.started).sum())} for s, g in O[O.result_found].groupby('state')}
print(O.to_string(index=False) if len(O) else 'no unscratched emergencies'); print(json.dumps(res, indent=1))
O.to_csv(f'outputs/emergency_check_{D}.csv', index=False); json.dump(res, open(f'outputs/emergency_check_{D}.json', 'w'), indent=1)
