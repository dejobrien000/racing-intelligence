"""Batch 16 B10 (part 1): how official beaten margins relate to measured time, and how stable that is. Research only; no prices.
Per race: seconds per official length = least-squares slope through the origin of (measured time behind the winner) on (official
margin), beaten runners with margins 0.5-10 L (where margins are given in fine steps). Then medians by state, year, course,
distance band, margin band and field size. Empirical relationship only: it is not the official calculation rule.
Sources: Qld (Racing Queensland tracking + official margins), SA (TripleS tracking + official margins), Vic (TripleS sections,
staged; finish time = sum of measured sections) joined to Breednet official margins by date and horse.
Usage (from research/): python3 batch16/b10_margins.py -> batch16/out_b10_margins.json"""
import re, json, duckdb, numpy as np, pandas as pd
OUT = {}
def slopes(R):
    R = R[(R.margin_l >= 0.5) & (R.margin_l <= 10) & R.gap_s.notna() & (R.gap_s >= 0)]
    g = R.groupby('race_id'); num = (R.margin_l * R.gap_s).groupby(R.race_id).sum(); den = (R.margin_l ** 2).groupby(R.race_id).sum(); n = g.size()
    s = (num / den)[n >= 4]
    meta = R.groupby('race_id').agg(state=('state', 'first'), yr=('yr', 'first'), course=('course', 'first'), distance_m=('distance_m', 'first'), field=('field', 'first'))
    return meta.join(s.rename('spl'), how='inner')
def load_runs(st):
    R = pd.read_parquet(f'/home/claude/b14/runs_{st}.parquet', columns=['race_id', 'horse', 'fp', 't', 'margin_l', 'distance_m', 'meeting_date', 'field_x'])
    R = R.rename(columns={'field_x': 'field'}); R = R[R.t.notna() & (R.t > 0)].copy()
    tw = R[R.fp == 1].groupby('race_id').t.min(); R['gap_s'] = R.t - R.race_id.map(tw)
    R['state'] = st; R['yr'] = pd.to_datetime(R.meeting_date).dt.year; R['course'] = R.race_id.str.split('-').str[1].str.replace('_', ' ')
    return R
con = duckdb.connect('../history/history.duckdb', read_only=True)
def load_vic():
    st = 'staging/vic_triples'; races = pd.read_csv(f'{st}/races.csv', dtype={'meeting_id': str}); runs = pd.read_csv(f'{st}/runners.csv', dtype={'meeting_id': str, 'saddlecloth': str})
    runs = runs[runs.tracked == 1] if 'tracked' in runs else runs
    tcol = [c for c in runs.columns if 'total' in c.lower() and 'time' in c.lower()][0]
    runs = runs.drop(columns=['race_date'], errors='ignore').merge(races[['meeting_id', 'race_no', 'race_date', 'distance_m', 'course_code']].rename(columns={'race_date': 'rdate'}), on=['meeting_id', 'race_no'], how='left')
    nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', str(s).upper()))
    runs['name_key'] = runs.horse.map(nk)
    bn = con.execute("select m.meeting_date, m.slug, m.state, u.race_no, u.name_key, u.finish_pos, u.margin_l from bn_runner u join bn_meeting m using (meeting_date, slug) where m.state='VIC' and m.meeting_date >= '2026-07-01'").fetchdf()
    bn['rdate'] = pd.to_datetime(bn.meeting_date).dt.strftime('%Y-%m-%d'); bn['name_key'] = bn.name_key.astype(str).str.replace(r'[^A-Z0-9]', '', regex=True)
    J = runs.merge(bn, on=['rdate', 'name_key'], how='inner', suffixes=('', '_bn'))
    J = J.rename(columns={tcol: 't'}); J = J[J.t > 0]; J['race_id'] = J.meeting_id + '-' + J.race_no.astype(str)
    tw = J[J.finish_pos == 1].groupby('race_id').t.min(); J['gap_s'] = J.t - J.race_id.map(tw)
    J['fp'] = J.finish_pos; J['state'] = 'VIC'; J['yr'] = 2026; J['course'] = J.slug; J['field'] = J.groupby('race_id').name_key.transform('size')
    return J[['race_id', 'fp', 't', 'gap_s', 'margin_l', 'distance_m', 'state', 'yr', 'course', 'field']]
frames = [load_runs('QLD'), load_runs('SA')]
try: frames.append(load_vic())
except Exception as e: OUT['vic_error'] = str(e)[:300]
S = pd.concat([slopes(R) for R in frames])
q = lambda x: {'races': int(len(x)), 'median_s_per_L': round(float(x.median()), 4), 'iqr': [round(float(x.quantile(.25)), 3), round(float(x.quantile(.75)), 3)]}
OUT['by_state'] = {k: q(v.spl) for k, v in S.groupby('state')}
OUT['by_state_year'] = {f'{k[0]} {k[1]}': q(v.spl) for k, v in S.groupby(['state', 'yr']) if len(v) >= 50}
S['dband'] = pd.cut(S.distance_m, [0, 1150, 1450, 1750, 9999], labels=['<=1150', '1151-1450', '1451-1750', '1751+']).astype(str)
OUT['by_state_distance'] = {f'{k[0]} {k[1]}': q(v.spl) for k, v in S.groupby(['state', 'dband']) if len(v) >= 30}
cy = S.groupby(['state', 'course', 'yr']).spl.agg(['size', 'median']).reset_index(); cy = cy[cy['size'] >= 25]
OUT['by_course_year'] = {f"{r.state} {r.course} {r.yr}": [int(r['size']), round(float(r['median']), 4)] for _, r in cy.iterrows()}
cc = S.groupby(['state', 'course']).spl.agg(['size', 'median']).reset_index(); cc = cc[cc['size'] >= 40]
OUT['by_course'] = {f"{r.state} {r.course}": [int(r['size']), round(float(r['median']), 4)] for _, r in cc.sort_values('median').iterrows()}
OUT['course_spread'] = {st: {'courses': int(len(g)), 'min': round(float(g['median'].min()), 4), 'max': round(float(g['median'].max()), 4)} for st, g in cc.groupby('state')}
S['fb'] = pd.cut(S.field, [0, 8, 11, 14, 30], labels=['<=8', '9-11', '12-14', '15+']).astype(str)
OUT['by_state_field'] = {f'{k[0]} {k[1]}': q(v.spl) for k, v in S.groupby(['state', 'fb']) if len(v) >= 30}
# margin bands: is the relationship linear (same s/L for short and long margins)?
A = pd.concat(frames); A = A[(A.margin_l > 0) & A.gap_s.notna()]
A['mb'] = pd.cut(A.margin_l, [0, 1, 3, 6, 10, 20, 99], labels=['<1 L', '1-3', '3-6', '6-10', '10-20', '20+'])
OUT['gap_per_length_by_margin_band'] = {f'{st} {mb}': round(float((g.gap_s / g.margin_l).median()), 4) for (st, mb), g in A.groupby(['state', 'mb'], observed=True) if len(g) >= 100}
json.dump(OUT, open('batch16/out_b10_margins.json', 'w'), indent=1); print(json.dumps({k: OUT[k] for k in ['by_state', 'course_spread']}, indent=0)); print(json.dumps(OUT.get('by_state_year'))); print(json.dumps(OUT.get('gap_per_length_by_margin_band')))
