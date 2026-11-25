"""Weekly incremental master-database update (runs on GitHub Actions from research/, after the db pack is restored).
1. Breednet results (all states held) for the last 10+ days -> incremental merge into history.duckdb (only meetings in the
   new bundle are replaced; everything else is untouched). Missing fields stay missing.
2. Racing Queensland tracking: not yet ported -> Queensland history is left unchanged and the report says so.
3. Rebuild the derived national tables (national.py with the states in ops/db_config.json, engine/lab.py, v3 frame).
4. Checks (loader checks B0-B8 plus row counts and rating drift); writes ops/weekly_report.md. Exit 1 if a check fails,
   so the workflow never publishes a broken version."""
import os, sys, json, subprocess, datetime as dt, duckdb, pandas as pd, numpy as np
R = os.getcwd(); ROOT = os.path.dirname(R); DB = os.path.join(ROOT, 'history', 'history.duckdb'); rep = ['# Weekly master-database update', '']
run = lambda *a, **k: subprocess.run(list(a), check=True, **k)
con = duckdb.connect(DB, read_only=True); last = con.execute('select max(meeting_date) from bn_meeting').fetchone()[0]
before = {t: con.execute(f'select count(*) from {t}').fetchone()[0] for t in ['bn_meeting', 'bn_race', 'bn_runner', 'race', 'starter']}; con.close()
today = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=10)).date(); d0 = min(last - dt.timedelta(days=9), today - dt.timedelta(days=10)); d1 = today - dt.timedelta(days=1)
rep += [f'- Run (Brisbane): {today}; previous Breednet history to {last}; collecting {d0} to {d1} (re-fetching recent days picks up corrections)', '']
os.makedirs(os.path.join(ROOT, 'breednet', 'weekly'), exist_ok=True)
bundle = os.path.join(ROOT, 'breednet', 'weekly', f'racing_breednet_weekly_{d0:%Y%m%d}_{d1:%Y%m%d}.jsonl.gz')
run(sys.executable, os.path.join(ROOT, 'collect', 'weekly', 'breednet.py'), 'dates', str(d0), str(d1), bundle, '--states', 'NSW,VIC,ACT,SA,WA,TAS')
st = json.load(open(bundle.replace('.jsonl.gz', '') + '.stats.json'))
rep += [f"- Breednet: {st['meetings']} meetings collected, {st['miss']} empty, {st['err']} errors, CAPTCHA stop: {st['captcha']}"]
if st['captcha'] or st['err'] > 5: rep.append('- STOP: collection incomplete; database not changed'); open('ops/weekly_report.md', 'w').write('\n'.join(rep) + '\n'); sys.exit(1)
tmp = os.path.join(ROOT, 'breednet', 'weekly_load'); os.makedirs(tmp, exist_ok=True); os.replace(bundle, os.path.join(tmp, os.path.basename(bundle)))
out = subprocess.run([sys.executable, os.path.join(ROOT, 'history', 'load_breednet.py'), tmp, DB, '--incremental'], capture_output=True, text=True, check=True).stdout
rep += ['', '```', out.strip()[:6000], '```', '', '- Racing Queensland tracking: collector not yet ported; Queensland history unchanged this week']
cfg = json.load(open('ops/db_config.json')); env = {**os.environ, 'NAT_STATES': ','.join(cfg['national_states']), 'PYTHONPATH': '.'}
old = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'state', 'dyn_nat'])
run(sys.executable, 'national.py', DB, env=env, stdout=subprocess.DEVNULL); run(sys.executable, 'engine/lab.py', env=env, stdout=subprocess.DEVNULL)
run(sys.executable, 'engine/build_frame_v3.py', env=env, stdout=subprocess.DEVNULL)
new = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'state', 'dyn_nat'])
j = old.merge(new, on=['race', 'horse'], suffixes=('_old', ''))
drift = (j.dyn_nat - j.dyn_nat_old).abs()
con = duckdb.connect(DB, read_only=True); after = {t: con.execute(f'select count(*) from {t}').fetchone()[0] for t in before}; newlast = con.execute('select max(meeting_date) from bn_meeting').fetchone()[0]
checks = {'no table lost rows': all(after[t] >= before[t] for t in before), 'frame did not shrink': len(new) >= len(old), 'every old run still present': len(j) == len(old),
          'old ratings barely moved (95th pct < 0.5 kg)': float(drift.quantile(.95)) < 0.5, 'history advanced or held': newlast >= last}
rep += ['', '| Check | Result |', '| --- | --- |'] + [f'| {k} | {"PASS" if v else "FAIL"} |' for k, v in checks.items()]
rep += ['', f'- Rows before -> after: ' + ', '.join(f'{t} {before[t]} -> {after[t]}' for t in before), f'- National frame rows {len(old)} -> {len(new)}; history to {newlast}',
        f'- Rating change on existing runs: mean {drift.mean():.3f} kg, 95th pct {drift.quantile(.95):.3f} kg, max {drift.max():.2f} kg']
open('ops/weekly_report.md', 'w').write('\n'.join(rep) + '\n'); open('ops/weekly_version.txt', 'w').write(f'master-{newlast}')
print('\n'.join(rep)); sys.exit(0 if all(checks.values()) else 1)
