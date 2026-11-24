// Breednet national results collector (full fields, every finisher), run inside a www.breednet.com.au tab.
// Light: plain fetch() of server-rendered result pages, parsed with DOMParser (no page rendering).
// Saves to IndexedDB racing_bundles/b under keys  bn:STATE:YYYY-MM-DD:Venue  (misses under bnmiss:).
// Resumable: keys already saved are skipped. Stops on any CAPTCHA / "are you human" page.
// Prices are NOT stored (the starting-price text is dropped during parsing).
window.RBX = window.RBX || {
  db() { return new Promise((res, rej) => { const q = indexedDB.open('racing_bundles', 1); q.onupgradeneeded = () => q.result.createObjectStore('b'); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); }); },
  async put(k, v) { const d = await this.db(); return new Promise((res, rej) => { const tx = d.transaction('b', 'readwrite'); tx.objectStore('b').put(v, k); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  async keys(prefix) { const d = await this.db(); return new Promise(res => { const q = d.transaction('b').objectStore('b').getAllKeys(); q.onsuccess = () => res(q.result.filter(k => !prefix || String(k).startsWith(prefix))); }); },
  async export(prefixes, filename) {
    const d = await this.db();
    const [keys, vals] = await Promise.all(['getAllKeys', 'getAll'].map(m => new Promise(res => { const q = d.transaction('b').objectStore('b')[m](); q.onsuccess = () => res(q.result); })));
    const lines = []; keys.forEach((k, i) => { if (prefixes.some(p => String(k).startsWith(p))) lines.push(JSON.stringify({ key: k, value: vals[i] })); });
    const gz = await new Response(new Blob([lines.join('\n')]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
    const a = document.createElement('a'); a.href = URL.createObjectURL(gz); a.download = filename; document.body.appendChild(a); a.click();
    return { records: lines.length, bytes: gz.size, filename };
  }
};

window.BN = window.BN || {};
Object.assign(BN, {
  st: { running: false, stop: false, done: 0, saved: 0, skipped: 0, miss: 0, err: 0, consecErr: 0, last: '', started: null, log: [] },
  clean(s) { return (s || '').replace(/\s+/g, ' ').trim(); },
  sleep(ms) { return new Promise(r => setTimeout(r, ms)); },
  slugs(track) {
    const base = track.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    const alt = { 'sandown': ['sandown-hillside', 'sandown-lakeside'], 'moonee-valley': ['the-valley'], 'randwick': ['randwick-kensington', 'royal-randwick'],
      'newcastle': ['beaumont-newcastle'], 'wagga': ['wagga-wagga'], 'rosehill': ['rosehill-gardens'], 'canterbury': ['canterbury-park'], 'illawarra-grange': ['kembla-grange'] };
    return [base, ...(alt[base] || []), base + '-synthetic'];
  },
  parse(html) {
    const d = new DOMParser().parseFromString(html, 'text/html');
    const h2 = d.querySelector('h2'); const first = d.querySelector('.runnerWrapper');
    const out = { meeting: this.clean(h2 && h2.textContent), races: [], v: 2 };
    if (!first) return out;
    let cur = null;
    for (const e of first.parentElement.children) {
      const cl = (e.className || '').toString();
      if (/^raceheader/.test(cl)) {
        const t = this.clean(e.textContent);
        const m = t.match(/^Race (\d+) - (.*?)\s*Class:(.*?)Track:(.*?)Time:(.*?)(?:Prizemoney:(.*))?$/);
        cur = { race_no: m ? +m[1] : null, title: m ? this.clean(m[2]) : t, class: m ? this.clean(m[3]) : null, track_cond: m ? this.clean(m[4]) : null,
          time: m ? this.clean(m[5]) : null, prize: m && m[6] ? this.clean(m[6]) : null, stakes_header: cl === 'raceheaderSR', header_raw: t, runners: [] };
        const dm = (cur.title.match(/\((\d{3,4})m\)/) || [])[1]; cur.distance_m = dm ? +dm : null;
        out.races.push(cur);
      } else if (cl === 'runnerWrapper' && cur) {
        const q = s => e.querySelector(s); const horse = q('.horse');
        const ht = this.clean(horse && horse.textContent); const sc = (ht.match(/^(\d+)\./) || [])[1];
        const a = horse && horse.querySelector('a');
        const br = this.clean(q('.breeding') && q('.breeding').textContent);
        const am = br.match(/^(\d+)([a-z]+)\s+(.*?)\s+x\s+(.*?(?:\s\([A-Z]{2,3}\))?)\s+\((.*)\)$/i);
        cur.runners.push({ pos: this.clean(q('.finishpos') && q('.finishpos').textContent), margin: this.clean(q('.margin') && q('.margin').textContent),
          saddlecloth: sc ? +sc : null, horse: this.clean(a ? a.textContent : ''), weight: (this.clean(q('.res-weight') && q('.res-weight').textContent).match(/^\d+(?:\.\d+)?/) || [''])[0],   // weight only: the cell also shows the starting price, which is dropped
          jockey: this.clean(q('.jockey') && q('.jockey').textContent).replace(/^R:\s*/, ''), trainer: this.clean(q('.trainer') && q('.trainer').textContent).replace(/^T:\s*/, ''),
          age: am ? +am[1] : null, sex: am ? am[2] : null, sire: am ? am[3] : null, dam: am ? am[4] : null, damsire: am ? am[5] : null });
      }
    }
    return out;
  },
  async meeting(item) {
    const tried = [];
    for (const slug of (item.slugs || this.slugs(item.bf_track))) {
      const path = `/race-results/australia/${slug}/${item.date}`;
      const r = await fetch(path, { credentials: 'same-origin' });
      const html = await r.text();
      if (/captcha|are you human|verify you are human|unusual traffic/i.test(html.slice(0, 20000)) && !/runnerWrapper/.test(html)) return { status: 'captcha', http: r.status, tried };
      if (r.status >= 400) return { status: 'http', http: r.status, tried };
      const p = this.parse(html); tried.push([slug, p.races.length]);
      if (p.races.length) return { status: 'ok', http: r.status, slug, path, tried, ...p };
      await this.sleep(800);
    }
    return { status: 'none', tried };
  },
  async run(queue, gap = 3000, force = false) {
    if (this.st.running) return 'already running';
    Object.assign(this.st, { running: true, stop: false, started: new Date().toISOString(), total: queue.length });
    const have = new Set([...(await RBX.keys('bn:')), ...(await RBX.keys('bnmiss:'))]);
    try {
      for (const item of queue) {
        if (this.st.stop) { this.st.last = 'stopped by request'; break; }
        const key = `bn:${item.state}:${item.date}:${item.bf_track}`;
        if (!force && (have.has(key) || have.has('bnmiss:' + key.slice(3)))) { this.st.skipped++; this.st.done++; continue; }
        let res;
        try { res = await this.meeting(item); } catch (e) { res = { status: 'error', error: String(e).slice(0, 200) }; }
        const stamp = new Date().toISOString();
        if (res.status === 'captcha') { this.st.last = 'CAPTCHA at ' + key + ' - stopped'; this.st.log.push(this.st.last); break; }
        if (res.status === 'ok') {
          await RBX.put(key, { key, state: item.state, date: item.date, bf_track: item.bf_track, tier: item.tier, retrieved_utc: stamp, ...res });
          this.st.saved++; this.st.consecErr = 0;
        } else if (res.status === 'none') {
          await RBX.put('bnmiss:' + key.slice(3), { key, state: item.state, date: item.date, bf_track: item.bf_track, retrieved_utc: stamp, ...res });
          this.st.miss++; this.st.consecErr = 0;
        } else {
          this.st.err++; this.st.consecErr++; this.st.log.push(`${stamp} ${key} ${res.status} ${res.http || ''} ${res.error || ''}`);
          if (this.st.consecErr >= 5) { this.st.log.push('5 errors in a row, pausing 5 min'); await this.sleep(300000); this.st.consecErr = 0; }
        }
        this.st.done++; this.st.last = key + ' ' + res.status;
        await this.sleep(gap + Math.random() * 1000);
      }
    } finally { this.st.running = false; this.st.finished = new Date().toISOString(); }
    return this.st;
  }
});
'BN ready';
