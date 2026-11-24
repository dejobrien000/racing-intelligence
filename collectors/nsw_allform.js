// Racing NSW "All Form" collector, run in an mdata.racingnsw.com.au tab (same origin as nsw_freefields.js).
// For every NSW race meeting already saved by NSWC (keys nsw:...), fetch FreeFields/Form.aspx for that meeting and keep,
// for each horse in the field, its full career form lines (position, track/date, distance, going, class, prize, jockey,
// weight, barrier, 1st/2nd, race time and race last-600, margin, positions at 800 m and 400 m, spells).
// Betting prices at the end of each line are removed before saving. Saved as nswform:KEY. Resumable; stops on CAPTCHA.
window.NSWF = {
  st: { running: false, stop: false, done: 0, saved: 0, err: 0, last: '', log: [] },
  db() { return new Promise((res, rej) => { const q = indexedDB.open('racing_bundles', 1); q.onupgradeneeded = () => q.result.createObjectStore('b'); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); }); },
  async keys() { const d = await this.db(); return new Promise(res => { const q = d.transaction('b').objectStore('b').getAllKeys(); q.onsuccess = () => res(q.result); }); },
  async put(k, v) { const d = await this.db(); return new Promise((res, rej) => { const tx = d.transaction('b', 'readwrite'); tx.objectStore('b').put(v, k); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  clean(s) { return (s || '').replace(/\s+/g, ' ').trim(); },
  noPrices(s) { return s.replace(/,\s*\$\d[\d.]*\/.*$/, ''); },   // drops the trailing price sequence like ', $21/$26/$21/$26'
  parse(html) {
    const d = new DOMParser().parseFromString(html, 'text/html'); const horses = [];
    const titles = [...d.querySelectorAll('.race-title')].map(e => this.clean(e.textContent));
    d.querySelectorAll('table.horse-form-table').forEach((t, i) => {
      const rows = [...t.querySelectorAll(':scope > tbody > tr')];
      const header = this.clean(rows[0] && rows[0].textContent), info = this.clean(rows[1] && rows[1].textContent);
      const lines = [...t.querySelectorAll('table.horse-last-start tr')].map(r => {
        const pos = this.clean((r.querySelector('td.Pos') || {}).textContent || ''); const rem = r.querySelector('td.remain');
        if (rem) rem.querySelectorAll('br').forEach(b => b.replaceWith(' | '));
        return { pos, txt: this.noPrices(this.clean(rem ? rem.textContent : r.textContent)) };
      });
      horses.push({ i, header, info, lines });
    });
    return { titles, horses };
  },
  async run(gap = 3000) {
    if (this.st.running) return 'already running';
    Object.assign(this.st, { running: true, stop: false, started: new Date().toISOString() });
    const all = await this.keys(); const have = new Set(all.filter(k => k.startsWith('nswform:')));
    const todo = all.filter(k => k.startsWith('nsw:') && !/,Trial$/i.test(k)).map(k => k.slice(4)).filter(k => !have.has('nswform:' + k));
    this.st.todo = todo.length;
    try {
      for (const key of todo) {
        if (this.st.stop) break;
        try {
          const r = await fetch('/FreeFields/Form.aspx?Key=' + encodeURIComponent(key), { credentials: 'same-origin' }); const h = await r.text();
          if (/captcha|are you human/i.test(h.slice(0, 20000)) && !/horse-form-table/.test(h)) { this.st.log.push('CAPTCHA at ' + key); break; }
          const p = this.parse(h);
          await this.put('nswform:' + key, { key, http: r.status, retrieved_utc: new Date().toISOString(), not_available: /not currently available/i.test(h), ...p });
          this.st.saved++;
        } catch (e) { this.st.err++; this.st.log.push(key + ' ' + String(e).slice(0, 100)); }
        this.st.done++; this.st.last = key;
        await new Promise(r => setTimeout(r, gap + Math.random() * 1000));
      }
    } finally { this.st.running = false; this.st.finished = new Date().toISOString(); }
    return this.st;
  }
};
'NSWF ready';
