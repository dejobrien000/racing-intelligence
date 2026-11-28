"""Batch 29 item 1: class parity for the handicap weight slope (wt_x_hcp), before the v2.6 release.
Training flag (third-layer fit, national races only): Breednet class label == 'Benchmark' (case-sensitive extraction in national.py, so WA's
'BenchMark NN+' is not counted). Serving flag: engine/v22.hcp_flag(state, TAB class) - 1 when TAB's class contains BMnn, WA always 0.
HISTORICAL parity: TAB's own class strings for PAST starts (form_past_starts.csv, the same TAB vocabulary as raceClassConditions, e.g.
'BM64', '3YO+ BM0-56', 'MDN') for races already in the master history, matched to the same run (horse name key + date) -> serving flag
vs training flag on identical races.
LIVE parity: raceClassConditions captured BEFORE the race (races.csv race_class / race_class_*.txt, 27-28 Nov) vs the same race's class as
TAB later lists it among past starts (form records captured on later days) -> the field read at scoring equals the field the historical
check used. Usage (from research/): python3 batch29/b29_class_parity.py"""
import sys, re, glob, json, numpy as np, pandas as pd
sys.path.insert(0, '.'); from engine import v22
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
PS = []
for f in sorted(glob.glob('collect/national/2026*/form_past_starts.csv')):
    p = pd.read_csv(f, dtype=str); p['captured_day'] = f.split('/')[2]; PS.append(p)
PS = pd.concat(PS); PS = PS[PS.start_type.isin(['LastStarts', 'WinRun'])].copy()
PS['horse'] = PS.name.map(nk); PS['date'] = pd.to_datetime(PS.start_date, errors='coerce'); PS = PS.dropna(subset=['date'])
PS = PS.drop_duplicates(['horse', 'date', 'class'])
F = pd.read_parquet('engine/frames/national_consolidated.parquet', columns=['horse', 'date', 'state', 'class_label', 'race_id', 'distance_m'])
F['date'] = pd.to_datetime(F.date); F = F[F.state != 'QLD']
M = PS.merge(F, on=['horse', 'date'], how='inner')
M['dist_ok'] = (pd.to_numeric(M.distance, errors='coerce') - M.distance_m).abs() <= 50
M = M[M.dist_ok].drop_duplicates(['race_id', 'horse'])
M['train'] = (M.class_label == 'Benchmark').astype(float); M['serve'] = [v22.hcp_flag(s, c) for s, c in zip(M.state, M['class'])]
OUT = {'historical': {'matched_runs': int(len(M)), 'races': int(M.race_id.nunique()), 'date_range': [str(M.date.min().date()), str(M.date.max().date())]}}
K = M.dropna(subset=['serve'])
OUT['historical']['agreement'] = round(float((K.train == K.serve).mean()), 4)
OUT['historical']['confusion'] = {f'train {int(a)} / serve {int(b)}': int(((K.train == a) & (K.serve == b)).sum()) for a in (0, 1) for b in (0, 1)}
OUT['historical']['by_state'] = {s: {'runs': int(len(g)), 'agreement': round(float((g.train == g.serve).mean()), 4)} for s, g in K.groupby('state')}
dis = K[K.train != K.serve]
OUT['historical']['disagreements_by_pattern'] = (dis.assign(pat=dis['class'].str.replace(r'\d+', 'n', regex=True) + ' | ' + dis.class_label + ' | ' + dis.state)
                                                 .pat.value_counts().head(15).to_dict())
OUT['historical']['bm0_n_pattern'] = {'runs': int(K['class'].str.contains(r'BM0-\d', na=False).sum()),
                                      'agreement': round(float((K[K['class'].str.contains(r'BM0-\d', na=False)].train == K[K['class'].str.contains(r'BM0-\d', na=False)].serve).mean()), 4) if K['class'].str.contains(r'BM0-\d', na=False).any() else None}
# ---------- live: pre-race raceClassConditions vs the class TAB lists for the same race afterwards ----------
L = []
for D in ['20261127', '20261128']:
    rc = v22.race_classes(D)
    R = pd.read_csv(f'collect/national/{D}/races.csv', dtype=str)
    for r in R.itertuples():
        c = rc.get((v22._slug(r.venue), int(r.race_no)))
        if c: L.append({'date': pd.Timestamp(D), 'venue': r.venue, 'venue_code': str(r.venue_code).upper(), 'race_no': int(r.race_no), 'state': r.state, 'dist': int(float(r.distance_m)), 'pre_class': c})
L = pd.DataFrame(L)
VC = PS.assign(vc=PS.venue.str.upper())
J = L.merge(VC[['date', 'vc', 'distance', 'class']].drop_duplicates(), left_on=['date', 'venue_code'], right_on=['date', 'vc'], how='inner') if len(L) else pd.DataFrame()
if len(J): J = J[(pd.to_numeric(J.distance, errors='coerce') - J.dist).abs() <= 50].drop_duplicates(['date', 'venue', 'race_no', 'class'])
OUT['live'] = {'races_with_pre_race_class': int(len(L)), 'races_also_listed_later': int(J[['date', 'venue', 'race_no']].drop_duplicates().shape[0]) if len(J) else 0}
if len(J):
    J['same_string'] = J.pre_class.str.strip().str.upper() == J['class'].str.strip().str.upper()
    J['same_flag'] = [v22.hcp_flag(s, a) == v22.hcp_flag(s, b) for s, a, b in zip(J.state, J.pre_class, J['class'])]
    OUT['live'].update({'same_class_string': round(float(J.same_string.mean()), 4), 'same_serving_flag': round(float(J.same_flag.mean()), 4),
                        'differences': J[~J.same_string][['date', 'venue', 'race_no', 'pre_class', 'class']].astype(str).head(10).to_dict('records')})
json.dump(OUT, open('batch29/out_b29_class_parity.json', 'w'), indent=1); print(json.dumps(OUT, indent=1))
