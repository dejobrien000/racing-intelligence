"""Weekly incremental master-database update (runs on GitHub Actions from research/, after the db pack is restored).
1. Breednet results (all states held) for the last 10+ days -> incremental merge into history.duckdb (only meetings in the
   new bundle are replaced; everything else is untouched). Missing fields stay missing.
2. Racing Queensland tracking + Race Fields for the same window (collect/weekly/rq.py) -> incremental merge
   (history/load_history.py --incremental: only meetings in the new bundle are replaced).
3. Rebuild every derived table from the database: Qld runs, Qld ratings and features, national runs (states in
   ops/db_config.json), engine frames (v2 and v3 rating).
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
subprocess.run([sys.executable, os.path.join(ROOT, 'collect', 'weekly', 'breednet.py'), 'dates', str(d0), str(d1), bundle, '--states', 'NSW,VIC,ACT,SA,WA,TAS,QLD'])   # exit 2 = CAPTCHA, read below (QLD: country meetings + ages)
st = json.load(open(bundle.replace('.jsonl.gz', '') + '.stats.json'))
rep += [f"- Breednet: {st['meetings']} meetings collected, {st['miss']} empty, {st['err']} errors, CAPTCHA stop: {st['captcha']}",
        f"- Venues on Breednet with no state in venue_states.json (not collected): {', '.join(sorted(st.get('unknown_venues', {}))) or 'none'}"]
if st['captcha'] or st['err'] > 5: rep.append('- STOP: collection incomplete; database not changed'); open('ops/weekly_report.md', 'w').write('\n'.join(rep) + '\n'); sys.exit(1)
tmp = os.path.join(ROOT, 'breednet', 'weekly_load'); os.makedirs(tmp, exist_ok=True); os.replace(bundle, os.path.join(tmp, os.path.basename(bundle)))
RQ_ = os.path.join(ROOT, 'collect', 'weekly', 'retry_queue.json')   # older meetings to (re)collect, e.g. after a server error in a backfill
if os.path.exists(RQ_) and json.load(open(RQ_)):
    rb = os.path.join(ROOT, 'breednet', 'weekly', f'racing_breednet_retry_{d1:%Y%m%d}.jsonl.gz')
    subprocess.run([sys.executable, os.path.join(ROOT, 'collect', 'weekly', 'breednet.py'), 'queue', RQ_, rb])
    rs = json.load(open(rb.replace('.jsonl.gz', '') + '.stats.json'))
    rep.append(f"- Breednet retry list ({len(json.load(open(RQ_)))} meetings): {rs['meetings']} collected, {rs['miss']} empty, {rs['err']} errors")
    if not rs['captcha'] and os.path.exists(rb): os.replace(rb, os.path.join(tmp, os.path.basename(rb)))
out = subprocess.run([sys.executable, os.path.join(ROOT, 'history', 'load_breednet.py'), tmp, DB, '--incremental'], capture_output=True, text=True, check=True).stdout
rep += ['', '```', out.strip()[:6000], '```']
rqz = os.path.join(ROOT, 'rq_weekly', f'racing_rq_weekly_{d0:%Y%m%d}_{d1:%Y%m%d}.zip'); os.makedirs(os.path.dirname(rqz), exist_ok=True)
rc = subprocess.run([sys.executable, os.path.join(ROOT, 'collect', 'weekly', 'rq.py'), f'{d0:%Y%m%d}', f'{d1:%Y%m%d}', rqz], capture_output=True, text=True)
rep += ['', '- Racing Queensland: ' + (rc.stdout.strip().splitlines() or ['no output'])[-1][:300]]
if rc.returncode: rep.append('- STOP: Racing Queensland collection failed (' + (rc.stderr.strip().splitlines() or [''])[-1][:200] + '); database not published'); open('ops/weekly_report.md', 'w').write('\n'.join(rep) + '\n'); sys.exit(1)
out = subprocess.run([sys.executable, os.path.join(ROOT, 'history', 'load_history.py'), '--incremental', rqz, DB], capture_output=True, text=True, check=True).stdout
rep += ['', '```', out.strip()[:4000], '```']
cfg = json.load(open('ops/db_config.json')); env = {**os.environ, 'NAT_STATES': ','.join(cfg['national_states']), 'NAT_QLD_BN': '1' if cfg.get('qld_breednet_in_national_rating') else '0', 'PYTHONPATH': '.'}
old = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'state', 'dyn_nat']); oldq = len(pd.read_parquet('runs.parquet', columns=['race_id']))
for a in [('build_runs.py', DB, 'runs.parquet'), ('rating_v0.py', 'runs.parquet', 'runs_rated_dev.parquet', '--fit-until=2024-12-31'), ('rating_v0.py', 'runs.parquet', 'runs_rated.parquet'),
          ('features.py', 'runs_rated_dev.parquet', DB, 'features.parquet'), ('inv20_pace_figures.py', DB), ('national.py', DB), ('ops/build_dyn_nat_qld.py',),
          ('engine/lab.py',), ('engine/build_frame_v3.py',)]:
    t0 = dt.datetime.now(); run(sys.executable, *a, env=env, stdout=subprocess.DEVNULL); rep.append(f'- rebuilt: {" ".join(a)} ({(dt.datetime.now() - t0).seconds}s)')
newq = len(pd.read_parquet('runs.parquet', columns=['race_id']))
new = pd.read_parquet('engine/frames/national.parquet', columns=['race', 'horse', 'state', 'dyn_nat'])
j = old.merge(new, on=['race', 'horse'], suffixes=('_old', ''))
drift = (j.dyn_nat - j.dyn_nat_old).abs()
con = duckdb.connect(DB, read_only=True); after = {t: con.execute(f'select count(*) from {t}').fetchone()[0] for t in before}; newlast = con.execute('select max(meeting_date) from bn_meeting').fetchone()[0]
checks = {'no table lost rows': all(after[t] >= before[t] for t in before), 'frame did not shrink': len(new) >= len(old), 'every old run still present': len(j) == len(old),
          'old ratings barely moved (95th pct < 0.5 kg)': float(drift.quantile(.95)) < 0.5, 'history advanced or held': newlast >= last,
          'Queensland runs did not shrink': newq >= oldq,
          'no Queensland file failed to parse': con.execute("select observed from checks where id = 'K3'").fetchone()[0] == '0'}
rep += ['', '| Check | Result |', '| --- | --- |'] + [f'| {k} | {"PASS" if v else "FAIL"} |' for k, v in checks.items()]
rep += ['', f'- Rows before -> after: ' + ', '.join(f'{t} {before[t]} -> {after[t]}' for t in before), f'- National frame rows {len(old)} -> {len(new)}; Queensland runs {oldq} -> {newq}; history to {newlast}',
        f'- Rating change on existing runs: mean {drift.mean():.3f} kg, 95th pct {drift.quantile(.95):.3f} kg, max {drift.max():.2f} kg']
open('ops/weekly_report.md', 'w').write('\n'.join(rep) + '\n'); open('ops/weekly_version.txt', 'w').write(f'master-{newlast}')
print('\n'.join(rep)); sys.exit(0 if all(checks.values()) else 1)
