"""Batch 29 item 8: same as batch28/b28_profile_ranges.py, with one validated model per engine family.
Usage: python3 batch29/b29_profile_ranges.py <day json> <national frame> <national model json> <qld frame> <qld model json>
(the national model must be the one fitted on the rating the day was published with: v2.3 days -> batch27, v2.5 days -> batch29 refit).
Batch 28 item 4 (approved: research-labelled, expanded horse profiles only, not the default race view): calibrated performance range
for each rated runner in the dashboard PREVIEW day file. Uses the Batch 27 P4 model exactly as fitted on 2023 (batch27/out_b27_uncertainty.json;
coverage of its 80% range 78% in 2024 and 2025-26, 77-80% in every group), on the rating the day was published with (28 Nov = Engine v2.3,
frame engine/frames/national_c2.parquet). National-family meetings only; Queensland rows are left without a range (not fitted there).
  expected = b x (rating - field mean rating)                                     b = 0.762 (kg of performance per kg of rating, fitted 2023)
  spread   = sqrt(const + A rating sd^2 + B horse variability + C new trip / new course / 120d+ spell / maiden + D history incomplete)
  80% range = expected + spread x [q10, q90] of the 2023 standardised errors
No confidence score is produced. Usage: python3 batch28/b28_profile_ranges.py <preview day json> <frame> (writes the json in place)"""
import sys, re, json, numpy as np, pandas as pd
DAY, FRN, MN, FRQ, MQ = sys.argv[1:6]
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
d = json.load(open(DAY)); D = pd.Timestamp(d['date'])
def load(FR):
    H = pd.read_parquet(FR, columns=['horse', 'date', 'race', 'venue', 'distance_m', 'dyn_nat_inn']); H['date'] = pd.to_datetime(H.date); return H[H.date < D]
E = pd.read_parquet('engine/frames/experience_at_run.parquet', columns=['race_key', 'horse', 'source']).rename(columns={'race_key': 'race'})
POP = 28.9; FAM = {}
for key, FR, MJ in [('NAT', FRN, MN), ('QLD', FRQ, MQ)]:
    H = load(FR).merge(E, on=['race', 'horse'], how='left').sort_values(['horse', 'date', 'race']); U = json.load(open(MJ))
    FAM[key] = (dict(tuple(H.groupby('horse'))), U['mean_slope_b_fit2023'], U['variance_model_kg2'], U['standardised_error_q10_q90_fit2023'], MJ)
n_done = 0; wide_names = {'C new trip': 'new trip', 'C new course': 'first time at this course', 'C 120d+ spell': 'back from a spell', 'C maiden race': 'maiden race', 'D history incomplete': 'history incomplete'}
for m in d['meetings']:
    if not m.get('rated'): continue
    G, b, C, (q10, q90), MJ = FAM['QLD' if (m.get('model_family') == 'QLD' or m.get('state') == 'QLD') else 'NAT']
    for r in m['races']:
        rr = [h for h in r['runners'] if h.get('ability') and h['ability'].get('rating_kg') is not None and h.get('profile')]
        if len(rr) < 2: continue
        mean = float(np.mean([h['ability']['rating_kg'] for h in rr]))
        for h in rr:
            a = h['ability']; g = G.get(nk(h['horse']))
            inn = g.dyn_nat_inn.dropna().values if g is not None else np.array([])
            n = len(inn); hvar = ((((inn ** 2).sum() - inn.sum() ** 2 / n) if n else 0.0) + 6 * POP) / (n + 6)
            dist = float(r['distance_m']); trips = g.distance_m.astype(float).values if g is not None else np.array([])
            new_trip = float(not (np.abs(np.log(trips) - np.log(dist)) <= 0.10).any()) if len(trips) else 1.0
            ven = m['name'].lower(); new_course = float(not (g.venue.astype(str).str.lower().str.contains(re.escape(ven.split()[0])).any())) if g is not None else 1.0
            spell = float((a.get('days_since') or 0) >= 120); maiden = float('maiden' in str(r.get('class', '')).lower())
            incomplete = float(g is not None and len(g) and str(g.source.iloc[-1]) not in ('complete', 'nan', 'None'))
            comp = {'constant': 1.0, 'A rating variance': (a.get('sd_kg') or 5.0) ** 2, 'B horse variability': hvar, 'C new trip': new_trip, 'C new course': new_course,
                    'C 120d+ spell': spell, 'C maiden race': maiden, 'D history incomplete': incomplete}
            var = sum(C[k] * v for k, v in comp.items()); sig = float(np.sqrt(var)); ex = b * (a['rating_kg'] - mean)
            wide = [wide_names[k] for k in wide_names if comp[k] and C[k] > 0]
            h['profile']['range_research'] = {'expected_kg': round(ex, 1), 'lo_kg': round(ex + sig * q10, 1), 'hi_kg': round(ex + sig * q90, 1), 'wide': ', '.join(wide) or None,
                                              'model': ('Queensland' if MJ == MQ else 'national') + ' range model ' + MJ.split('/')[-1] + ' (fitted 2023; coverage about 78% in 2024 and 2025-26)'}
            n_done += 1
json.dump(d, open(DAY, 'w'), separators=(',', ':')); print('ranges added', n_done)
