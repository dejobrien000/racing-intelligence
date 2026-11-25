"""Parity check: a bundle from rq.py vs the rows already in history.duckdb (x_race, x_runner, x_sec, x_field) for the same
(date, track). Usage: python3 compare_rq.py BUNDLE.zip history.duckdb [report.md]. Exit 1 unless every table matches."""
import sys, io, zipfile, duckdb, pandas as pd
z = zipfile.ZipFile(sys.argv[1]); con = duckdb.connect(sys.argv[2], read_only=True); rep = [f'# RQ collector parity: {sys.argv[1]}', '']; ok = True
for k, t in [('races', 'x_race'), ('runners', 'x_runner'), ('secs', 'x_sec'), ('fields', 'x_field')]:
    new = pd.read_csv(io.BytesIO(z.read(f'parsed/{k}.psv')), sep='|', dtype=str, keep_default_na=False, quoting=3)
    keys = new[['date', 'track']].drop_duplicates(); con.register('k', keys)
    old = con.execute(f'select t.* from {t} t join k on t.date = k.date and t.track = k.track').fetchdf().astype(str).replace({'None': '', 'nan': ''})
    cols = [c for c in new.columns if c in old.columns]; a = set(map(tuple, new[cols].values)); b = set(map(tuple, old[cols].values))
    same = len(a & b); rep.append(f'- {k}: new {len(new)} rows, DB {len(old)} rows, identical {same}; only new {len(a - b)}, only DB {len(b - a)}')
    if a != b:
        ok = False; rep.append('  first differences (new / DB):'); rep += ['  N ' + '|'.join(x) for x in sorted(a - b)[:3]] + ['  D ' + '|'.join(x) for x in sorted(b - a)[:3]]
    con.unregister('k')
rep += ['', 'RESULT: ' + ('PASS' if ok else 'FAIL')]; txt = '\n'.join(rep); print(txt)
if len(sys.argv) > 3: open(sys.argv[3], 'w').write(txt + '\n')
sys.exit(0 if ok else 1)
