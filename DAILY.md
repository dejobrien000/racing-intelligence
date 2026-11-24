# Daily racing collection: runbook for the scheduled task

Run once each morning. **D** = yesterday in Australia/Brisbane. Damo's PC: Windows, user `furlo`,
connected folder `C:\Users\furlo\Downloads`. All data goes to that folder. Never log in anywhere, never
type a password or API key, never store prices (the collectors already skip SP and tote columns), never
delete files. If any page shows a CAPTCHA or "Are you human?", stop that source and report it.

## 0. Setup
1. `get_device_info`. If the PC can't be reached, stop and report that the PC was off or asleep.
2. Stage `C:\Users\furlo\Downloads\racing_intelligence_code.zip` and unzip it into a new working folder.
   Paths below are inside that folder.
3. Load the Claude in Chrome tools in one ToolSearch call (tabs_context_mcp, tabs_create_mcp, navigate,
   javascript_tool, tabs_close_mcp). Call tabs_context_mcp. Use a NEW tab for each source below (Chrome
   allows one automatic download per tab). Close every tab you opened before finishing.
4. Chrome allows ONE automatic download per tab. Every export below must run in a tab that has not
   downloaded anything yet. If an exported file doesn't appear in Downloads, open a fresh tab on the same
   site, read the records back from IndexedDB `racing_bundles`/`b` and save them from there (RBX.export
   works in the fresh tab once collectors/*.js is injected, because IndexedDB is shared by the site).
   Check every file with device_list_dir before moving on.
5. To load a collector into a page, read the .js file and pass its full text to javascript_tool on that tab.
   A javascript_tool call times out at 45 seconds: start long jobs without awaiting them, store progress on
   `window`, and poll.

## 1. Queensland (Racing Queensland)
1. New tab: `https://www.racingqueensland.com.au/industry/thoroughbred/thoroughbred-sectionals`.
2. Inject `history/browser_bundle.js`.
3. Start: `window.__d={}; (async()=>{ const ms=RQB.meetingList().filter(m=>m.date==='YYYYMMDD'); window.__d.n=ms.length; if(!ms.length){window.__d.done=true;return;} const res=await RQB.run(ms,2); const blob=await RQB.bundle(res); ZW.save(blob,'racing_rq_daily_YYYYMMDD.zip'); window.__d.ok=res.filter(r=>r.raw.length).length; window.__d.done=true; })();`
   (YYYYMMDD = D). Poll `window.__d` until `done`. Zero meetings is normal on some days (Racing Queensland
   posts only tracked meetings; Mondays often have none). Record "0 tracked meetings", not an error.

## 1b. Queensland PRE-RACE fields snapshot (today, and tomorrow if published)
Racing Queensland publishes each meeting's Race Fields PDF, scratchings, track condition, rail and weather on its
calendar pages. Snapshots are immutable: each one is a new IndexedDB key and a new file; never edit or replace one.
1. In the Racing Queensland tab, inject `collectors/rq_pdf_helpers.js`, then `collectors/rq_prerace.js`.
2. `window.__p = {}; (async()=>{ window.__p.today = await RQP.all('<TODAY YYYYMMDD>'); window.__p.tomorrow = await RQP.all('<TOMORROW YYYYMMDD>'); window.__p.done = true; })();`
   Poll `window.__p` until `done`. A meeting with no Race Fields PDF (non-TAB or not yet published) shows 0 runners: normal.
3. New tab on `https://www.racingqueensland.com.au/robots.txt`, inject `collectors/rq_prerace.js` (it defines RBX), then
   `await RBX.export(['rqpre:<TODAY>', 'rqpre:<TOMORROW>'], 'racing_rq_prerace_<TODAY>_snap<UTC stamp>.jsonl.gz')`.
4. Report meetings, races and runners per date, scratchings listed, track condition and rail. No tips, no prices.
Scoring is done separately (research/prerace/score_prerace.py) from these files; this run only collects.

## 1c. NSW and ACT PRE-RACE fields snapshot (today, and tomorrow if published)
Racing NSW publishes acceptances with barriers, weights, jockeys, scratchings, track condition and rail on its FreeFields
pages. Same rule: every snapshot is a new key and a new file.
1. New tab: `https://mdata.racingnsw.com.au/FreeFields/Calendar.aspx?State=NSW`. Inject `collectors/nsw_prerace.js`.
2. `window.__n = {}; (async()=>{ window.__n.today = await NSWP.all('<TODAY YYYYMMDD>'); window.__n.tomorrow = await NSWP.all('<TOMORROW YYYYMMDD>'); window.__n.done = true; })();`
   Poll `window.__n` until `done`.
3. New tab on `https://mdata.racingnsw.com.au/robots.txt`, inject `collectors/nsw_prerace.js`, then
   `await RBX.export(['nswpre:<TODAY>', 'nswpre:<TOMORROW>'], 'racing_nsw_prerace_<TODAY>_snap<UTC stamp>.jsonl.gz')`.
4. Report meetings, races, acceptors, scratchings, going and rail. No tips, no prices.
Scoring (separate): `python3 prerace/score_national_prerace.py <file> ../history/history.duckdb <YYYYMMDD>` from research/
(one race date per run), then `python3 prerace/daily_ranking.py <YYYYMMDD>` once every meeting for that date is scored.
Both write new timestamped files only.

## 1d. ENGINE v2 scoring and the daily ranking (after every v1 scoring run for a date)
From research/: `PYTHONPATH=. python3 engine/score_v2.py <YYYYMMDD>` then `PYTHONPATH=. python3 engine/daily_ranking_v2.py <YYYYMMDD>`.
v2 = the v1 operational score + learned terms (Qld: horse records, jockey & trainer; NSW/Vic: jockey & trainer, age & sex,
form changes & head-to-head, discovery-chosen interactions). Model: benchmarks/engine_v2/manifest.json. The history frame
engine/frames/national.parquet must end BEFORE the race date (rebuild it with `PYTHONPATH=. python3 engine/lab.py` after
loading yesterday's results). Writes new timestamped files only; v1 files are never edited.

## 2. NSW and ACT (Racing NSW results pages)
1. New tab: `https://mdata.racingnsw.com.au/FreeFields/Calendar_Results.aspx`.
2. Inject `collectors/nsw_freefields.js`.
3. Keys: `const all=await NSWC.calendarKeys();` then keep keys starting with D, D-1 and D-2 in the
   `YYYYMonDD` form (e.g. `2026Nov23`). Re-fetching D-1 and D-2 replaces interim results with final ones.
4. Start without awaiting: `NSWC.run(keys, 3000, true)`. Poll `NSWC.st` until `running` is false.
5. Export: `await RBX.export(keys.map(k=>'nsw:'+k), 'racing_nsw_freefields_daily_YYYYMMDD.jsonl.gz')`.

### 2b. NSW career form (Racing NSW "All Form" pages)
1. In the same mdata tab, inject `collectors/nsw_allform.js` and start `NSWF.run(3000)`. It fetches the form page for every
   saved NSW race meeting that doesn't have one yet (so the meetings just collected). Poll `NSWF.st` until `running` is false.
2. Export from a FRESH mdata tab: `await RBX.export(['nswform:<key date>'], 'racing_nsw_allform_daily_YYYYMMDD.jsonl.gz')`
   where `<key date>` is like `2026Nov22` (one prefix per day collected). Prices are removed by the collector.

## 3. Victoria (racing.com)
1. New tab: `https://www.racing.com/calendar`. Click "Table view". Read the page text. Find D's
   Victorian meetings of type Metro, Provincial, Country or Picnic (skip JumpOut and Trial). Slug = the
   name in lower case with spaces as hyphens (e.g. "Sportsbet-Ballarat" -> `sportsbet-ballarat`). If race 1's
   results page doesn't load for a slug, try the name without its sponsor prefix.
2. Same tab: inject `collectors/racingcom_results.js`. For each meeting, ONE AT A TIME, start
   `window.__m=null; RC.meeting({state:'VIC', date:'YYYY-MM-DD', cands:[slug]}).then(m=>window.__m=m||'none')`,
   poll until `window.__m` is set, then `await RC.put('rc:VIC:YYYY-MM-DD:'+slug, window.__m)` if it isn't
   'none'. Note each meeting's `meet_code` and `n_races`. Many country meetings have no Speed Data tab
   (no tracking): meet_code stays null. Record that as "no speed data published", not an error. These pages are heavy: wait 10 seconds between
   meetings. If the tab stops responding, close it, open a fresh racing.com tab, re-inject, and carry on.
3. Export from a FRESH www.racing.com tab (the results tab has been busy and may hit the download limit):
   `await RBX.export(['rc:VIC:YYYY-MM-DD'], 'racing_rc_daily_YYYYMMDD.jsonl.gz')`.
4. Only if at least one meeting has a meet_code: new tab `https://dxp-static.racing.com/sectionals/index.html`. Inject `collectors/racingcom_speed.js`.
   For each meeting with a meet_code: `const races=[]; for(let r=1;r<=n;r++){ races.push({race_no:r, data:(await SPD.render(code,r)).out}); }`
   (split into calls under 45 s), then
   `await RBX.put('spd:VIC:YYYY-MM-DD:'+slug, {state:'VIC', date:'YYYY-MM-DD', slug, meet_code:code, retrieved_utc:new Date().toISOString(), races})`.
5. Export: `await RBX.export(['spd:VIC:YYYY-MM-DD'], 'racing_rcspeed_daily_YYYYMMDD.jsonl.gz')`.

## 3b. Every Australian state (Breednet results: full fields, no barriers or sectionals)
1. New tab `https://www.breednet.com.au/robots.txt` (light page, same site). Inject `collectors/breednet_results.js`
   then `collectors/breednet_dates.js`.
2. Start `BN.runDates('<D-2>','<D>', null, 2500)` (dates as YYYY-MM-DD; `null` = every Australian race meeting
   listed for those days, all states, country and picnic included). Poll `BN.ds` until `running` is false
   (each poll under 45 s). It skips meetings already saved.
3. Export from a FRESH robots.txt tab: `await RBX.export(['bnm:YYYY-MM-DD','bnidx:YYYY-MM-DD'], 'racing_breednet_daily_YYYYMMDD.jsonl.gz')`
   for each of D-2..D (one file per tab, or one export with all three date prefixes).
4. Backfill (NSW, ACT, Vic, Oct 2022 onward) may still be running from 24 Nov in the Breednet tab. Don't close that
   tab. If it was closed, re-inject both files in a new tab and restart `BN.runDates('2022-10-01','2026-11-23', <NSW/Vic/ACT slug list in collectors/README.md>, 2500)`;
   it skips everything already saved.

## 4. Check the day's files
1. Stage the day's new files from Downloads (`racing_rq_daily_YYYYMMDD.zip`, `racing_nsw_freefields_daily_YYYYMMDD.jsonl.gz`,
   `racing_rc_daily_YYYYMMDD.jsonl.gz`, `racing_rcspeed_daily_YYYYMMDD.jsonl.gz`, `racing_breednet_daily_YYYYMMDD.jsonl.gz`)
   plus `racing_betfair_2026.zip`, into one new folder.
2. `python3 -I history/load_history.py <folder>` then `python3 -I history/load_nsw_vic.py <folder> history/history.duckdb`,
   then `python3 -I history/load_breednet.py <folder of ALL racing_breednet_*.jsonl.gz files> history/history.duckdb`.
   Betfair files lag about a month, so Betfair cross-checks will show no overlap for D; that is expected.
   Flag anything else: missing barriers or weights, missing "results last published", missing meet codes,
   implausible last-600m times, parse errors in the Queensland log.
3. Append one line to `C:\Users\furlo\Downloads\racing_daily_log.md` (stage it first if it exists, keep its
   contents, then commit with the staged mtime as expectedMtimeMs; create it if missing):
   `YYYY-MM-DD | Qld meetings n | NSW meetings n (races, runners) | Vic meetings n (races, runners, speed-data races) | flags`.

## 5. Report
Send a short summary: meetings and races per state, files saved, anything flagged or skipped. Plain
language, no file paths unless something needs Damo's attention.
