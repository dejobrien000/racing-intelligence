// Racing NSW PRE-RACE snapshot collector (NSW and ACT meetings on Racing NSW FreeFields): accepted fields (saddlecloth,
// horse, trainer, jockey incl. claim, barrier, weight, penalty, benchmark), scratchings, track condition, weather,
// penetrometer, rail and "fields last published", exactly as published when collected. No prices, no tips.
// Run in a mdata.racingnsw.com.au tab. Every snapshot is a NEW IndexedDB key  nswpre:YYYYMMDD:Venue:<UTC stamp>.
// Usage: await NSWP.meetings()                 -> keys like '2026Nov25,NSW,Wyong' listed on the calendar
//        await NSWP.snapshot('2026Nov25,NSW,Wyong')
//        await NSWP.all('2026Nov25')           -> every listed meeting on that date
//        await RBX.export(['nswpre:20261125'], 'racing_nsw_prerace_20261125_snap<UTC>.jsonl.gz')
window.RBX = window.RBX || {
  db() { return new Promise((res, rej) => { const q = indexedDB.open('racing_bundles', 1); q.onupgradeneeded = () => q.result.createObjectStore('b'); q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error); }); },
  async put(k, v) { const d = await this.db(); return new Promise((res, rej) => { const tx = d.transaction('b', 'readwrite'); tx.objectStore('b').put(v, k); tx.oncomplete = () => res(); tx.onerror = () => rej(tx.error); }); },
  async get(k) { const d = await this.db(); return new Promise(res => { const q = d.transaction('b').objectStore('b').get(k); q.onsuccess = () => res(q.result); }); },
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
if (!window.RBX.get) window.RBX.get = async function (k) { const d = await this.db(); return new Promise(res => { const q = d.transaction('b').objectStore('b').get(k); q.onsuccess = () => res(q.result); }); };
window.NSWP = (() => {
  const MON = { Jan: '01', Feb: '02', Mar: '03', Apr: '04', May: '05', Jun: '06', Jul: '07', Aug: '08', Sep: '09', Oct: '10', Nov: '11', Dec: '12' };
  const ymd = key => { const m = key.match(/^(\d{4})(\w{3})(\d{2})/); return m ? m[1] + MON[m[2]] + m[3] : null; };
  const dom = h => new DOMParser().parseFromString(h, 'text/html');
  const clean = s => (s || '').replace(/\s+/g, ' ').trim();
  async function sha(s) { const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)); return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, '0')).join(''); }
  async function meetings() {
    const d = dom(await (await fetch('/FreeFields/Calendar.aspx?State=NSW')).text());
    return [...new Set([...d.querySelectorAll('a')].map(a => a.getAttribute('href') || '').filter(x => /Acceptances\.aspx/i.test(x)).map(x => decodeURIComponent(x.split('Key=')[1] || '')))].filter(Boolean);
  }
  function fields(doc) {
    const txt = doc.body.innerText; const out = []; const heads = [];
    const re = /Race (\d+) - (\d{1,2}:\d{2}[AP]M) (.*?) \((\d{3,4}) METRES\)/g; let m;
    const flat = txt.replace(/\s+/g, ' ');
    while ((m = re.exec(flat))) heads.push({ race_no: +m[1], start_time: m[2], race_name: clean(m[3]), distance_m: +m[4] });
    const tables = [...doc.querySelectorAll('table.race-strip-fields')];
    tables.forEach((tb, i) => {
      const H = [...tb.rows[0].cells].map(c => clean(c.textContent));
      const col = n => H.findIndex(h => h.toLowerCase().startsWith(n));
      const ci = { no: col('no'), last: col('last'), horse: col('horse'), tr: col('trainer'), jk: col('jockey'), bar: col('barrier'), wt: col('wgt'), pwt: col('probable'), pen: col('penalty'), bm: col("b'mark") };
      const h = heads[i] || {};
      for (const r of [...tb.rows].slice(1)) {
        const c = [...r.cells].map(x => clean(x.textContent)); if (!c[ci.horse]) continue;
        const jk = c[ci.jk] || ''; const claim = (jk.match(/\(a([\d.]+)/) || [])[1];
        out.push({ race_no: h.race_no ?? i + 1, race_name: h.race_name || null, distance_m: h.distance_m || null, start_time: h.start_time || null,
          saddlecloth: +c[ci.no] || null, last10: c[ci.last] || null, horse: c[ci.horse], trainer: c[ci.tr] || null, jockey: jk.replace(/\s*\(a.*?\)\s*$/, '') || null,
          claim_kg: claim ? +claim : null, barrier: +c[ci.bar] || null, weight_kg: parseFloat(c[ci.wt]) || null, probable_weight_kg: parseFloat(c[ci.pwt]) || null,
          penalty_kg: parseFloat(c[ci.pen]) || null, benchmark: c[ci.bm] || null, emergency: /^E/i.test(c[ci.no]) || /\(E\)/.test(c[ci.horse]) });
      }
    });
    return out;
  }
  function conditions(doc) {
    const t = clean(doc.body.innerText); const g = re => { const m = t.match(re); return m ? clean(m[1]) : null; };
    return { track_condition: g(/Track Condition:\s*(.*?)\s*Weather:/i), weather: g(/Weather:\s*(.*?)\s*Penetrometer:/i), penetrometer: g(/Penetrometer:\s*(.*?)\s*Track Information:/i),
      track_information: g(/Track Information:\s*(.*?)\s*(?:Fields Last Published|Rail Position)/i), fields_last_published: g(/Fields Last Published:\s*(.*?\d{1,2}:\d{2}[AP]M \w+)/i),
      rail: g(/Rail Position:\s*(.*?)\s*(?:Race 1 -|Track Condition|Weather|$)/i) };
  }
  function scratchings(doc) {
    const sections = {};
    for (const tb of doc.querySelectorAll('table.scratch-table')) {
      let p = tb.previousElementSibling, k = 0; while (p && !p.textContent.trim() && k < 5) { p = p.previousElementSibling; k++; }
      const label = p ? clean(p.textContent) : 'Unlabelled'; let race = null; const items = [];
      for (const r of tb.rows) { const c = [...r.cells].map(x => clean(x.textContent)); if (c.length < 2) continue;
        const rm = c[0].match(/Race (\d+)/); if (rm) race = +rm[1];
        const im = c[1].match(/^(\d{1,2})\s+(.*?)(?:\s+\((.*?)\))?(?:\s+-\s+(.*))?$/); if (im && race) items.push({ race_no: race, saddlecloth: +im[1], horse: im[2], when: im[3] || null, detail: im[4] || null }); }
      sections[label] = items;
    }
    const scr = [...(sections['Scratchings'] || []), ...(sections['Late Scratchings'] || [])];
    const byRace = {}; for (const x of scr) (byRace[x.race_no] = byRace[x.race_no] || []).push({ saddlecloth: x.saddlecloth, horse: x.horse, when: x.when });
    return { parsed: Object.entries(byRace).map(([r, h]) => ({ race_no: +r, horses: h })), sections };
  }
  async function snapshot(key) {
    const t0 = new Date().toISOString(); const date = ymd(key); const venue = key.split(',')[2];
    const au = '/FreeFields/Acceptances.aspx?Key=' + encodeURIComponent(key); const su = '/FreeFields/Scratchings.aspx?Key=' + encodeURIComponent(key);
    const ar = await fetch(au); const ah = await ar.text(); if (/captcha|are you human/i.test(ah.slice(0, 5000))) throw new Error('CAPTCHA page: stop');
    const sr = await fetch(su); const sh = await sr.text();
    const ad = dom(ah), sd = dom(sh); const scr = scratchings(sd);
    const snap = { kind: 'nsw_prerace', schema: 1, key_rnsw: key, date, venue, state: key.split(',')[1], retrieved_utc: t0, acceptances_url: 'https://mdata.racingnsw.com.au' + au, acceptances_http: ar.status,
      acceptances_sha256: await sha(ah), scratchings_url: 'https://mdata.racingnsw.com.au' + su, scratchings_http: sr.status, scratchings_text: clean(sd.body.innerText).slice(0, 20000),
      conditions: { ...conditions(ad), ...Object.fromEntries(Object.entries(conditions(sd)).filter(([k, v]) => v && k !== 'fields_last_published')), scratchings_last_published: (clean(sd.body.innerText).match(/Scratchings Last Published:\s*(.*?\d{1,2}:\d{2}[AP]M \w+)/i) || [])[1] || null }, scratchings: scr.parsed, scratch_sections: scr.sections, scratchings_text_sha256: await sha(clean(sd.body.innerText)), fields: fields(ad) };
    const k = `nswpre:${date}:${venue}:${t0.replace(/[-:.]/g, '')}`;
    if (await RBX.get(k)) throw new Error('key exists; refusing to overwrite ' + k);
    await RBX.put(k, snap);
    return { key: k, venue, races: new Set(snap.fields.map(f => f.race_no)).size, runners: snap.fields.length, scratched_listed: snap.scratchings.reduce((a, r) => a + r.horses.length, 0), conditions: snap.conditions };
  }
  async function all(datePrefix) { const ks = (await meetings()).filter(k => k.startsWith(datePrefix)); const out = []; for (const k of ks) { try { out.push(await snapshot(k)); } catch (e) { out.push({ key: k, error: String(e).slice(0, 200) }); } await new Promise(r => setTimeout(r, 1500)); } return out; }
  return { meetings, snapshot, all, fields, conditions, scratchings, ymd };
})();
