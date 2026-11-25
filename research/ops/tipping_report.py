"""Tipping report card (observational; Batch 12 s2, requested by Damo 25 Nov 2026). Separate from model training, coefficient
selection, classification decisions and production scoring: it reads only the PUBLISHED day file after settlement and never writes to it.

Classifications (exactly as engine/export_ui.py assigns them on the dashboard):
  Race label / top pick:  'Strong selection'   top pick's calibrated win chance >= upper tercile of top-pick chances in the calibration
                                               period (national v2.2 30.2%, Queensland 26.7%);
                          'Leading contender'  >= lower tercile (national 23.2%, Queensland 22.6%);
                          'No clear selection' below the lower tercile;
                          'Insufficient evidence' the top pick has no prior form held, or more than half the field has none.
  Other runners:          'Contender' (ranked 2nd-3rd), 'Outsider' (4th or worse), 'Insufficient evidence' (no prior form held).
Report groups: all top picks; top picks by label; Contender; Outsider; Insufficient evidence (not top pick).

For each group: selections, winners, strike rate, expected winners (sum of calibrated chances) vs actual, calibration (mean predicted vs
observed), notional flat-unit ROI % at OPEN (TAB fixed win at the 7:30am run) and, separately, at CLOSE (final TAB fixed win in the
completed racecard), each on its own eligible sample; price coverage and missing counts. Percentages and counts only; no money.
Settlement: scratched = void; race with no result (abandoned or not published) = void and counted; dead heat for the win = price divided
by the number dead-heating; TAB late-scratching deductions are not published in the racecard and are NOT applied (counted and disclosed).
Never substitutes tote, starting price, Betfair or any other price. Notional ROI is a report card, not an objective.
Usage (from research/): python3 ops/tipping_report.py <YYYYMMDD>   (dates before 2026-11-26 are ignored unless TIPPING_FROM is set)"""
import sys, os, csv, json
import pandas as pd
Y = sys.argv[1]; ydate = f'{Y[:4]}-{Y[4:6]}-{Y[6:]}'; FROM = os.environ.get('TIPPING_FROM', '2026-11-26')
if ydate < FROM: print(f'tipping report: {ydate} is before {FROM} (first genuinely published day); nothing recorded'); sys.exit(0)
DJ = json.load(open(f'ui/data/racing_{ydate}.json')); os.makedirs('outputs', exist_ok=True)
L, S, MD = 'outputs/tipping_ledger.csv', 'outputs/tipping_report.csv', 'outputs/tipping_report.md'
COLS = ['date', 'meeting', 'state', 'race', 'n', 'horse', 'rank', 'classification', 'group', 'cal_pct', 'engine', 'prediction_file', 'exported_utc',
        'result', 'settlement', 'dead_heat_k', 'late_scratching_in_race', 'open_win', 'close_win', 'open_return', 'close_return']
num = lambda v: float(v) if v not in (None, '', 'None') else None
rows = []
for m in DJ['meetings']:
    if not m.get('rated'): continue
    prov = m.get('provenance') or {}
    for r in m['races']:
        fin = {h['n']: h.get('finish') for h in r['runners']}
        placed = [n for n, f in fin.items() if f not in (None, 'scratched')]
        winners = [n for n, f in fin.items() if str(f) == '1']; k = len(winners)
        late = any(f == 'scratched' for f in fin.values())
        for h in r['runners']:
            f = h.get('finish'); o = (h.get('open') or {}).get('win'); c = (h.get('close') or {}).get('win')
            grp = ('Top pick: ' + h['class']) if h['rank'] == 1 else ('Insufficient evidence (not top pick)' if h['class'] == 'Insufficient evidence' else h['class'])
            if f == 'scratched': st = 'void (scratched)'
            elif not placed or not winners: st = 'void (no result: abandoned or not published)'
            elif f is None: st = 'no result for this runner'
            else: st = 'won' + (f' (dead heat x{k})' if k > 1 else '') if str(f) == '1' else 'lost'
            ret = lambda p: (round(p / k - 1, 4) if st.startswith('won') else -1.0) if (p and p > 1 and st.startswith(('won', 'lost'))) else None
            rows.append({'date': ydate, 'meeting': m['name'], 'state': m.get('state'), 'race': r['no'], 'n': h['n'], 'horse': h['horse'], 'rank': h['rank'],
                         'classification': h['class'], 'group': grp, 'cal_pct': h.get('cal'), 'engine': prov.get('engine_release') or DJ['engine']['operational'],
                         'prediction_file': prov.get('v2_prediction_file'), 'exported_utc': DJ.get('exported_utc'), 'result': f, 'settlement': st,
                         'dead_heat_k': k if k > 1 else None, 'late_scratching_in_race': late, 'open_win': o, 'close_win': c,
                         'open_return': ret(num(o)), 'close_return': ret(num(c))})
seen = {(r['date'], r['meeting'], r['race'], r['n']) for r in csv.DictReader(open(L))} if os.path.exists(L) else set()
new = [x for x in rows if (x['date'], x['meeting'], str(x['race']), str(x['n'])) not in seen]
hdr = not os.path.exists(L) or os.path.getsize(L) == 0
with open(L, 'a', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    if hdr: w.writeheader()
    for x in new: w.writerow(x)
# ---- report card (rebuilt from the whole ledger every day; nothing is ever overwritten in the ledger)
A = pd.read_csv(L); A['settled'] = A.settlement.str.startswith(('won', 'lost')); A['won'] = A.settlement.str.startswith('won')
A['top'] = A['rank'] == 1
def card(g):
    s = g[g.settled]; n = len(s); op = s[s.open_return.notna()]; cl = s[s.close_return.notna()]
    p = s.cal_pct.astype(float) / 100
    return pd.Series({'selections': len(g), 'settled': n, 'void_scratched': int(g.settlement.eq('void (scratched)').sum()),
                      'void_no_result': int(g.settlement.str.startswith('void (no result').sum()), 'winners': int(s.won.sum()),
                      'strike_rate_%': round(100 * s.won.mean(), 1) if n else None, 'expected_winners': round(float(p.sum()), 1) if n else None,
                      'actual_over_expected': round(float(s.won.sum() / p.sum()), 2) if n and p.sum() else None,
                      'mean_predicted_%': round(100 * float(p.mean()), 1) if n else None,
                      'open_eligible': len(op), 'open_price_missing': n - len(op), 'roi_open_%': round(100 * op.open_return.mean(), 1) if len(op) else None,
                      'close_eligible': len(cl), 'close_price_missing': n - len(cl), 'roi_close_%': round(100 * cl.close_return.mean(), 1) if len(cl) else None,
                      'dead_heat_wins': int(s.settlement.str.contains('dead heat').sum()), 'winners_in_races_with_late_scratchings': int((s.won & s.late_scratching_in_race.astype(str).eq('True')).sum())})
groups = [('All top picks', A[A.top])] + [(g, x) for g, x in A.groupby('group')]
R = pd.DataFrame({name: card(g) for name, g in groups}).T
R.index.name = 'group'; R.to_csv(S)
cum = A[A.top].sort_values('date').groupby('date').apply(card, include_groups=False)
cum['cum_selections'] = cum.settled.cumsum(); cum['cum_winners'] = cum.winners.cumsum()
cum['cum_strike_%'] = (100 * cum.cum_winners / cum.cum_selections).round(1)
cum['cum_roi_open_%'] = (100 * A[A.top & A.open_return.notna()].groupby('date').open_return.sum().cumsum() / cum.open_eligible.cumsum()).round(1)
with open(MD, 'w') as fh:
    fh.write(f'# Tipping report card (observational; notional flat units; percentages and counts only)\n\nUpdated with {ydate}. Ledger: {L}. '
             'OPEN = TAB fixed win at the 7:30am run; CLOSE = final TAB fixed win in the completed racecard; each ROI uses only selections with that price. '
             'Scratched = void; abandoned or unpublished races = void; dead heats divide the price; TAB late-scratching deductions are not published and not applied. '
             'No tote, SP or Betfair substitutes. Not an optimisation target.\n\n')
    sa = A[A.settled].copy(); sa['band'] = pd.cut(sa.cal_pct.astype(float), [0, 5, 10, 20, 30, 100], labels=['under 5%', '5-10%', '10-20%', '20-30%', '30%+'])
    cal = sa.groupby('band', observed=True).agg(runners=('won', 'size'), mean_predicted_pct=('cal_pct', 'mean'), won_pct=('won', 'mean'))
    cal['won_pct'] = (100 * cal.won_pct).round(1); cal['mean_predicted_pct'] = cal.mean_predicted_pct.round(1)
    fh.write('## Calibration: every settled runner, by published calibrated chance\n\n' + cal.to_markdown() + '\n\n')
    fh.write(R.to_markdown() + '\n\n## All top picks by day (cumulative)\n\n' + cum[['settled', 'winners', 'cum_selections', 'cum_winners', 'cum_strike_%', 'open_eligible', 'cum_roi_open_%']].to_markdown() + '\n')
print(f'tipping report: {len(new)} runner rows added for {ydate}; all top picks to date: {int(R.loc["All top picks", "settled"])} settled, '
      f'strike {R.loc["All top picks", "strike_rate_%"]}%, open ROI {R.loc["All top picks", "roi_open_%"]}% on {int(R.loc["All top picks", "open_eligible"])}')
