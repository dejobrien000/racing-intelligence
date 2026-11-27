"""Prospective evaluation ledger (observational; Batch 11 follow-up, requested by Damo 25 Nov 2026).
After yesterday is settled, append one row per race and per prediction set (the published production prediction, plus any SHADOW
candidate saved before the race) to outputs/prospective_eval.csv: winner's model rank and chance, log-likelihood, top pick's finish.
Reads only saved predictions and results. Nothing here feeds a rating, a coefficient or model development; prices are not used.
Races dated 26 Nov 2026 or later are 'untouched' (first prospective evidence for Engine v2.2 / v2.1.1 / v2.1.2-candidate).
Usage (from research/): python3 ops/evaluate_prospective.py <YYYYMMDD>"""
import sys, os, re, csv, json, glob, math
import pandas as pd
Y = sys.argv[1]; ydate = f'{Y[:4]}-{Y[4:6]}-{Y[6:]}'; DJ = json.load(open(f'ui/data/racing_{ydate}.json'))
L = 'outputs/prospective_eval.csv'; os.makedirs('outputs', exist_ok=True)
COLS = ['date', 'status', 'meeting', 'state', 'race', 'prediction', 'engine', 'prediction_file', 'starters', 'winner_n', 'winner_horse', 'winner_rank', 'winner_chance_pct',
        'log_lik', 'null_log_lik', 'top_pick_n', 'top_pick_horse', 'top_pick_finish', 'top_pick_won', 'winner_in_top3', 'top_pick_cal_pct', 'race_label', 'data_confidence']
seen = {(r['date'], r['meeting'], r['race'], r['prediction'], r['engine']) for r in csv.DictReader(open(L))} if os.path.exists(L) else set()   # engine in the key: several shadows per race (27 Nov 2026)
status = 'untouched (26 Nov 2026 on)' if ydate >= '2026-11-26' else 'pre-release day'
def row(m, r, pred, engine, pfile, chances, finish, cal=None):
    """chances: {n: raw model chance %}; finish: {n: finishing position string or 'scratched'}"""
    ran = {n: f for n, f in finish.items() if f not in (None, 'scratched') and n in chances}
    if not ran: return None
    tot = sum(chances[n] for n in ran); p = {n: chances[n] / tot for n in ran}
    order = sorted(ran, key=lambda n: -p[n]); rank = {n: i + 1 for i, n in enumerate(order)}
    winners = [n for n, f in ran.items() if str(f) == '1']
    if not winners: return None
    w = winners[0]; t = order[0]; horses = {h['n']: h['horse'] for h in r['runners']}
    return {'date': ydate, 'status': status, 'meeting': m['name'], 'state': m.get('state'), 'race': r['no'], 'prediction': pred, 'engine': engine, 'prediction_file': pfile,
            'starters': len(ran), 'winner_n': w, 'winner_horse': horses.get(w), 'winner_rank': rank[w], 'winner_chance_pct': round(100 * p[w], 2),
            'log_lik': round(math.log(max(p[w], 1e-9)), 5), 'null_log_lik': round(-math.log(len(ran)), 5), 'top_pick_n': t, 'top_pick_horse': horses.get(t),
            'top_pick_finish': ran[t], 'top_pick_won': int(t in winners), 'winner_in_top3': int(rank[w] <= 3), 'top_pick_cal_pct': (cal or {}).get(t),
            'race_label': r.get('label'), 'data_confidence': (r.get('confidence') or {}).get('level')}
SH = pd.read_csv('prospective/shadow/qld_v2_1_2/INDEX.csv') if os.path.exists('prospective/shadow/qld_v2_1_2/INDEX.csv') else None
PV = pd.read_csv('prospective/shadow/prev_engines/INDEX.csv') if os.path.exists('prospective/shadow/prev_engines/INDEX.csv') else None   # previous production engines (from 27 Nov 2026)
V4 = pd.read_csv('prospective/shadow/v2_4_candidate/INDEX.csv') if os.path.exists('prospective/shadow/v2_4_candidate/INDEX.csv') else None   # Engine v2.4 candidate shadow (from 27 Nov 2026)
UR = pd.read_csv('prospective/shadow/update_rule/INDEX.csv') if os.path.exists('prospective/shadow/update_rule/INDEX.csv') else None   # rating update rule candidate shadow (Batch 16 B9, from 28 Nov 2026)
CO = pd.read_csv('prospective/shadow/cap_only/INDEX.csv') if os.path.exists('prospective/shadow/cap_only/INDEX.csv') else None   # cap-only comparator shadow (Batch 16 B9)
out = []
for m in DJ['meetings']:
    if not m.get('rated'): continue
    eng = (m.get('provenance') or {}).get('engine_release') or DJ['engine']['operational']; pf = (m.get('provenance') or {}).get('v2_prediction_file')
    shf = None
    if SH is not None and m.get('model_family') == 'QLD':
        s = SH[(SH.date.astype(str) == Y) & (SH.track == m['name']) & SH.file.str.contains('/v2_') & SH.file.str.endswith('_runners.csv')]
        if len(s): shf = s.sort_values('scored_utc').file.iloc[-1]
    shadow = pd.read_csv(shf) if shf else None
    v4, v4f = None, None
    try:
        if V4 is not None and m.get('model_family') != 'QLD':
            s4 = V4[(V4.date.astype(str) == Y) & (V4.track == m['name']) & V4.file.str.contains('/v2_') & V4.file.str.endswith('_runners.csv')]
            if len(s4): v4f = s4.sort_values('scored_utc').file.iloc[-1]; v4 = pd.read_csv(v4f)
    except Exception as ex: print('WARNING v2.4 shadow unreadable for', m['name'], str(ex)[:100]); v4 = None
    ur, urf = None, None
    try:
        if UR is not None and m.get('model_family') != 'QLD':
            su = UR[(UR.date.astype(str) == Y) & (UR.track == m['name']) & UR.file.str.contains('/v2_') & UR.file.str.endswith('_runners.csv')]
            if len(su): urf = su.sort_values('scored_utc').file.iloc[-1]; ur = pd.read_csv(urf)
    except Exception as ex: print('WARNING update-rule shadow unreadable for', m['name'], str(ex)[:100]); ur = None
    co, cof = None, None
    try:
        if CO is not None and m.get('model_family') != 'QLD':
            sc = CO[(CO.date.astype(str) == Y) & (CO.track == m['name']) & CO.file.str.contains('/v2_') & CO.file.str.endswith('_runners.csv')]
            if len(sc): cof = sc.sort_values('scored_utc').file.iloc[-1]; co = pd.read_csv(cof)
    except Exception as ex: print('WARNING cap-only shadow unreadable for', m['name'], str(ex)[:100]); co = None
    prev, pvf, prev_label = None, None, None
    try:
        if PV is not None:
            s_ = PV[(PV.date.astype(str) == Y) & (PV.track == m['name']) & PV.file.str.contains('/v2_') & PV.file.str.endswith('_runners.csv')]
            if len(s_):
                pvf = s_.sort_values('scored_utc').file.iloc[-1]; prev = pd.read_csv(pvf)
                prev_label = json.load(open(pvf.replace('_runners.csv', '_manifest.json'))).get('engine_release', '?') + ' (previous production, not live)'
    except Exception as ex: print('WARNING previous-engine predictions unreadable for', m['name'], str(ex)[:100]); prev = None
    for r in m['races']:
        fin = {h['n']: h.get('finish') for h in r['runners']}
        if not any(fin.values()): continue
        x = row(m, r, 'production', eng, pf, {h['n']: h['chance'] for h in r['runners']}, fin, {h['n']: h.get('cal') for h in r['runners']})
        if x: out.append(x)
        if shadow is not None:
            g = shadow[shadow.race_no == r['no']]
            x = row(m, r, 'shadow', 'Engine v2.1.2-candidate (Qld, not live)', shf, dict(zip(g.saddlecloth.astype(int), g.v2_chance_pct.astype(float))), fin)
            if x: out.append(x)
        if v4 is not None:
            g = v4[v4.race_no == r['no']]
            x = row(m, r, 'shadow', 'Engine v2.4-candidate (not live)', v4f, dict(zip(g.saddlecloth.astype(int), g.v2_chance_pct.astype(float))), fin)
            if x: out.append(x)
        if ur is not None:
            g = ur[ur.race_no == r['no']]
            x = row(m, r, 'shadow', 'Update-rule candidate (not live)', urf, dict(zip(g.saddlecloth.astype(int), g.v2_chance_pct.astype(float))), fin)
            if x: out.append(x)
        if co is not None:
            g = co[co.race_no == r['no']]
            x = row(m, r, 'shadow', 'Cap-only candidate (not live)', cof, dict(zip(g.saddlecloth.astype(int), g.v2_chance_pct.astype(float))), fin)
            if x: out.append(x)
        if prev is not None:
            g = prev[prev.race_no == r['no']]
            x = row(m, r, 'previous_engine', prev_label, pvf, dict(zip(g.saddlecloth.astype(int), g.v2_chance_pct.astype(float))), fin)
            if x: out.append(x)
new = [o for o in out if (o['date'], o['meeting'], str(o['race']), o['prediction'], o['engine']) not in seen]
need_header = not os.path.exists(L) or os.path.getsize(L) == 0
with open(L, 'a', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    if need_header: w.writeheader()
    for o in new: w.writerow(o)
A = pd.read_csv(L)
for (st, pred), g in A.groupby(['status', 'prediction']):
    print(f"{st} | {pred}: {len(g)} races, top pick won {int(g.top_pick_won.sum())} ({100 * g.top_pick_won.mean():.0f}%), winner in top 3 {100 * g.winner_in_top3.mean():.0f}%, "
          f"log-lik per race {g.log_lik.mean():.3f} vs field-size baseline {g.null_log_lik.mean():.3f}")
print(f'evaluation ledger: {len(new)} new rows for {ydate} ({len(out) - len(new)} already held)')
