// Breednet date-driven crawler (adds to breednet_results.js; needs RBX and BN.parse loaded first).
// For each date: fetch /results/daily-results?t_date=YYYY-MM-DD (the national index of meetings),
// save it as bnidx:DATE, then fetch every Australian race meeting whose venue slug is in `wanted`
// and save it as bnm:DATE:slug. Resumable (skips saved keys); stops on CAPTCHA.
Object.assign(BN, {
  ds: { running: false, stop: false, date: '', dates: 0, idx: 0, meetings: 0, miss: 0, err: 0, consec: 0, started: null, log: [] },
  dateList(from, to) { const out = []; for (let d = new Date(from + 'T00:00:00Z'); d <= new Date(to + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + 1)) out.push(d.toISOString().slice(0, 10)); return out; },
  async getText(path) {
    const r = await fetch(path, { credentials: 'same-origin' }); const h = await r.text();
    if (/captcha|are you human|verify you are human|unusual traffic/i.test(h.slice(0, 20000)) && !/meetingPanel|runnerWrapper/.test(h)) throw new Error('CAPTCHA');
    if (r.status >= 400) throw new Error('HTTP ' + r.status);
    return h;
  },
  parseIndex(html, date) {
    const d = new DOMParser().parseFromString(html, 'text/html'); const race = new Set(), trial = new Set(); let other = 0;
    for (const p of d.querySelectorAll('.meetingPanel')) {
      const a = p.querySelector('a[href*="-results/"]'); if (!a) continue;
      const parts = (a.getAttribute('href') || '').split('?')[0].split('/');   // ['', 'race-results', 'australia', slug, date]
      if (parts[2] !== 'australia' || parts[4] !== date) { other++; continue; }
      (parts[1] === 'trial-results' ? trial : race).add(parts[3]);
    }
    return { race: [...race], trial: [...trial], other };
  },
  async runDates(from, to, wanted, gap = 2500) {
    if (this.ds.running) return 'already running';
    const W = wanted ? new Set(wanted) : null;   // null = every Australian race meeting that day
    Object.assign(this.ds, { running: true, stop: false, started: new Date().toISOString(), from, to });
    const have = new Set(await RBX.keys('bn'));
    const pause = () => this.sleep(gap + Math.random() * 1000);
    try {
      for (const date of this.dateList(from, to)) {
        if (this.ds.stop) break;
        this.ds.date = date;
        try {
          let idx;
          if (have.has('bnidx:' + date)) {
            const db = await RBX.db(); idx = await new Promise(res => { const q = db.transaction('b').objectStore('b').get('bnidx:' + date); q.onsuccess = () => res(q.result); });
          } else {
            idx = { date, ...this.parseIndex(await this.getText('/results/daily-results?t_date=' + date), date), retrieved_utc: new Date().toISOString() };
            await RBX.put('bnidx:' + date, idx); this.ds.idx++; await pause();
          }
          for (const slug of idx.race.filter(s => !W || W.has(s))) {
            const key = `bnm:${date}:${slug}`;
            if (have.has(key) || have.has('bnmiss:' + date + ':' + slug)) continue;
            const path = `/race-results/australia/${slug}/${date}`;
            const p = this.parse(await this.getText(path));
            if (p.races.length) { await RBX.put(key, { key, date, slug, path, retrieved_utc: new Date().toISOString(), ...p }); this.ds.meetings++; }
            else { await RBX.put('bnmiss:' + date + ':' + slug, { date, slug, retrieved_utc: new Date().toISOString() }); this.ds.miss++; }
            this.ds.consec = 0; await pause();
          }
          this.ds.dates++;
        } catch (e) {
          const msg = String(e.message || e);
          this.ds.log.push(new Date().toISOString() + ' ' + date + ' ' + msg.slice(0, 120));
          if (msg === 'CAPTCHA') { this.ds.log.push('stopped: CAPTCHA'); break; }
          this.ds.err++; this.ds.consec++;
          if (this.ds.consec >= 5) { this.ds.log.push('5 errors in a row, pausing 5 min'); await this.sleep(300000); this.ds.consec = 0; }
          await pause();
        }
      }
    } finally { this.ds.running = false; this.ds.finished = new Date().toISOString(); }
    return this.ds;
  }
});
'BN dates ready';
