"""Batch 16 B7: Engine v2.4 candidate (handicap weight slope) release checks, re-runnable as data arrives. Read-only.
1. Race-class parity: TAB's own class field (collected from 27 Nov 2026) against Breednet's class for the same race (the training
   source), once the weekly update has loaded Breednet results for those dates. The candidate's flag must agree with what training saw.
2. Apprentice claimers in Benchmark races (prospective): expected wins (model chance) vs actual, production and v2.4 shadow.
3. Paired prospective comparison v2.4 shadow vs production (from outputs/prospective_eval.csv).
Usage (from research/): PYTHONPATH=. python3 batch16/b7_v24_checks.py   -> batch16/out_b7_v24_checks.json"""
import os, re, glob, json, math, duckdb, pandas as pd, numpy as np
from engine import v22
OUT = {}
# ---------- 1. class parity ----------
rows = []
for f in sorted(glob.glob('collect/national/2026*/race_class_*.txt')) + sorted(glob.glob('collect/national/2026*/races.csv')):
    D = f.split('/')[2]; vc = {}
    try: vc = {r.venue_code.upper(): (r.venue, r.state) for r in pd.read_csv(f'collect/national/{D}/races.csv', dtype=str).itertuples()}
    except Exception: pass
    if f.endswith('.txt'):
        for line in open(f):
            p = line.rstrip('\n').split('|')
            if p[0] == 'CLASS' and p[1].upper() in vc: rows.append({'date': D, 'venue': vc[p[1].upper()][0], 'state': vc[p[1].upper()][1], 'race_no': int(p[2]), 'tab_class': p[4]})
    else:
        R = pd.read_csv(f, dtype=str)
        if 'race_class' in R:
            for r in R.itertuples():
                if isinstance(r.race_class, str) and r.race_class: rows.append({'date': D, 'venue': r.venue, 'state': r.state, 'race_no': int(r.race_no), 'tab_class': r.race_class})
TC = pd.DataFrame(rows).drop_duplicates(['date', 'venue', 'race_no']) if rows else pd.DataFrame(columns=['date', 'venue', 'state', 'race_no', 'tab_class'])
con = duckdb.connect('../history/history.duckdb', read_only=True)
bn = con.execute("select m.meeting_date, m.slug, m.state, r.race_no, r.class from bn_race r join bn_meeting m using (meeting_date, slug)").fetchdf()
bn['date'] = pd.to_datetime(bn.meeting_date).dt.strftime('%Y%m%d'); slug = lambda t: re.sub(r'[^a-z0-9]+', '-', str(t).lower()).strip('-')
TC['slug'] = TC.venue.map(slug); J = TC.merge(bn, left_on=['date', 'slug', 'race_no'], right_on=['date', 'slug', 'race_no'], how='left', suffixes=('', '_bn'))
J['train_flag'] = J['class'].fillna('').str.match(r'^Benchmark').astype(float).where(J['class'].notna())   # national.py: case-sensitive '^Benchmark'
J['serve_flag'] = [v22.hcp_flag(s, c) for s, c in zip(J.state, J.tab_class)]
m = J[J.train_flag.notna()]
OUT['class_parity'] = {'tab_races_collected': int(len(TC)), 'dates': sorted(TC.date.unique().tolist()), 'matched_to_breednet': int(len(m)),
                       'agree': int((m.train_flag == m.serve_flag).sum()) if len(m) else 0,
                       'disagree_examples': m[m.train_flag != m.serve_flag][['date', 'venue', 'race_no', 'tab_class', 'class']].head(20).to_dict('records') if len(m) else [],
                       'tab_class_counts': TC.tab_class.str.replace(r'\d+', 'N', regex=True).value_counts().head(25).to_dict(),
                       'status': 'complete' if len(m) else f'waiting: Breednet results for {", ".join(sorted(TC.date.unique()))} are not in the master database yet (weekly update)'}
# ---------- 2/3. prospective ----------
L = pd.read_csv('outputs/prospective_eval.csv') if os.path.exists('outputs/prospective_eval.csv') else pd.DataFrame()
if len(L):
    k = ['date', 'meeting', 'race']; p = L[L.prediction == 'production']; s4 = L[L.engine.astype(str).str.startswith('Engine v2.4-candidate')]
    j = p.merge(s4, on=k, suffixes=('_p', '_s'))
    if len(j):
        d = j.log_lik_s - j.log_lik_p; se = d.std(ddof=1) / math.sqrt(len(d)) if len(d) > 1 else float('nan')
        OUT['prospective_v24_vs_production'] = {'paired_races': int(len(j)), 'gain_per_race': round(float(d.mean()), 4), 'lo95': round(float(d.mean() - 1.96 * se), 4), 'hi95': round(float(d.mean() + 1.96 * se), 4),
                                                'top_pick_pts': round(100 * float(j.top_pick_won_s.mean() - j.top_pick_won_p.mean()), 1)}
    else: OUT['prospective_v24_vs_production'] = {'paired_races': 0, 'status': 'first settled races are judged the morning after 27 Nov'}
cl = []
for dayf in sorted(glob.glob('ui/data/racing_2026-*.json')):
    DJ = json.load(open(dayf)); D = DJ['date'].replace('-', '')
    for mt in DJ['meetings']:
        for r in mt.get('races', []):
            fin = {h['n']: h.get('finish') for h in r['runners']}
            if not any(fin.values()): continue
            for h in r['runners']:
                if (h.get('claim') or 0) > 0 and h.get('chance') is not None: cl.append({'date': D, 'meeting': mt['name'], 'race': r['no'], 'n': h['n'], 'class': r.get('class'), 'chance': h['chance'] / 100, 'won': int(str(fin.get(h['n'])) == '1')})
C = pd.DataFrame(cl)
OUT['claimers_settled'] = {'runners': int(len(C)), 'wins': int(C.won.sum()) if len(C) else 0, 'expected_production': round(float(C.chance.sum()), 2) if len(C) else 0,
                           'note': 'all settled claimer rides with production chances; Benchmark split and v2.4 shadow added once the class field and shadow are settled'}
json.dump(OUT, open('batch16/out_b7_v24_checks.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=1, default=str)[:2500])
