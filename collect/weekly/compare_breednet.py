"""Parity check: a bundle collected by breednet.py vs the rows already in history.duckdb (bn_race, bn_runner) for the
same meetings. Prints per-field agreement; exit 1 if any core field agrees on < 99.5% of matched runners.
Usage: python3 compare_breednet.py NEW.jsonl.gz history.duckdb [report.md]"""
import sys, re, gzip, json, duckdb, pandas as pd
new, db = sys.argv[1], sys.argv[2]; rep = sys.argv[3] if len(sys.argv) > 3 else None
R, U = [], []
def secs(t):
    m = re.match(r'^(?:(\d+):)?(\d+(?:\.\d+)?)$', (t or '').strip()); return (int(m.group(1) or 0) * 60 + float(m.group(2))) if m else None
for line in gzip.open(new, 'rt', encoding='utf-8'):
    o = json.loads(line)
    if not o['key'].startswith('bnm:'): continue
    v = o['value']
    for r in v['races']:
        tm = re.match(r'^\s*([\d:.]+)\s*(?:\(([\d.]+)\))?', r.get('time') or '')
        R.append({'meeting_date': v['date'], 'slug': v['slug'], 'race_no': r['race_no'], 'title': r['title'], 'distance_m': r['distance_m'], 'class': r['class'],
                  'race_time_s': secs(tm.group(1)) if tm else None, 'n_runners': len(r['runners'])})
        for x in r['runners']:
            w = x.get('weight') or ''
            U.append({'meeting_date': v['date'], 'slug': v['slug'], 'race_no': r['race_no'], 'saddlecloth': x['saddlecloth'], 'pos_raw': x['pos'],
                      'horse': x['horse'], 'weight_kg': float(w) if re.match(r'^\d+(\.\d+)?$', w) else None, 'jockey': x['jockey'], 'trainer': x['trainer'],
                      'age': x['age'], 'sex': x['sex'], 'sire': x['sire']})
R, U = pd.DataFrame(R), pd.DataFrame(U)
con = duckdb.connect(db, read_only=True)
keys = R[['meeting_date', 'slug']].drop_duplicates(); con.register('k', keys)
oR = con.execute("select r.meeting_date::varchar meeting_date, r.slug, r.race_no, r.title, r.distance_m, r.class, r.race_time_s, (select count(*) from bn_runner u where u.meeting_date=r.meeting_date and u.slug=r.slug and u.race_no=r.race_no) n_runners from bn_race r join k on r.meeting_date::varchar=k.meeting_date and r.slug=k.slug").fetchdf()
oU = con.execute("select u.meeting_date::varchar meeting_date, u.slug, u.race_no, u.saddlecloth, u.pos_raw, u.horse, u.weight_kg, u.jockey, u.trainer, u.age, u.sex, u.sire from bn_runner u join k on u.meeting_date::varchar=k.meeting_date and u.slug=k.slug").fetchdf()
lines = [f'# Breednet collector parity: {new}', '', f'new: {len(keys)} meetings, {len(R)} races, {len(U)} runners; already in DB: '
         f'{oR[["meeting_date","slug"]].drop_duplicates().shape[0]} meetings, {len(oR)} races, {len(oU)} runners', '']
mr = R.merge(oR, on=['meeting_date', 'slug', 'race_no'], suffixes=('', '_db'))
lines.append(f'races matched: {len(mr)}'); bad = False
for c in ['title', 'distance_m', 'class', 'race_time_s', 'n_runners']:
    a = (mr[c].astype(str) == mr[c + '_db'].astype(str)).mean() if len(mr) else float('nan'); lines.append(f'- race {c}: {a:.2%}')
mu = U.merge(oU, on=['meeting_date', 'slug', 'race_no', 'saddlecloth', 'horse'], suffixes=('', '_db'))
lines.append(f'runners matched on race + saddlecloth + horse: {len(mu)} of {len(U)} new / {len(oU)} in DB')
for c in ['pos_raw', 'weight_kg', 'jockey', 'trainer', 'age', 'sex', 'sire']:
    a = (mu[c].astype(str) == mu[c + '_db'].astype(str)).mean() if len(mu) else float('nan'); lines.append(f'- runner {c}: {a:.2%}')
    if not (a >= 0.995): bad = True
if len(oU) and len(mu) < 0.995 * len(oU): bad = True
diff = mu[(mu.pos_raw.astype(str) != mu.pos_raw_db.astype(str)) | (mu.jockey != mu.jockey_db)].head(10)
if len(diff): lines += ['', 'first differences:', diff.to_string(index=False)]
lines += ['', 'RESULT: ' + ('FAIL' if bad or not len(mu) else 'PASS')]
txt = '\n'.join(lines); print(txt)
if rep: open(rep, 'w').write(txt + '\n')
sys.exit(1 if bad or not len(mu) else 0)
