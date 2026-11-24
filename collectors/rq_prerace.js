// Racing Queensland PRE-RACE snapshot collector: fields, emergencies, scratchings, track condition, rail, weather,
// as published at the moment of collection. Run in a www.racingqueensland.com.au tab AFTER injecting
// history/browser_bundle.js (it provides pdfItems, RQB.parseFields, ZW.sha) and collectors/breednet_results.js's RBX
// helper (or the RBX block below). No prices, no tips, no login.
// Every snapshot is stored under a NEW key  rqpre:YYYYMMDD:CODE:<UTC stamp>  and never overwritten.
// Usage:  await RQP.meetings('20261125')            -> [{code, url}] thoroughbred meetings listed for that date
//         await RQP.snapshot('20261125', 'ipsw')     -> saves one snapshot, returns a summary
//         await RQP.all('20261125')                  -> snapshot of every listed meeting with a Race Fields PDF
//         await RBX.export(['rqpre:20261125'], 'racing_rq_prerace_20261125_<stamp>.jsonl.gz')
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
window.RQP = (() => {
  const TRACK = { DOOM: 'Doomben', E_FM: 'Eagle_Farm', IPSW: 'Ipswich', KCOY: 'Kilcoy', CRNS: 'Ladbrokes_Cannon_Park', MKAY: 'Mackay', ROCK: 'Rockhampton',
    SCST: 'Sunshine_Coast', SCPT: 'Sunshine_Coast_Poly_Track', GCST: 'TAB_Park_Gold_Coast', TWBA: 'Toowoomba', TOWN: 'Townsville', DALB: 'Dalby', WARW: 'Picklebet_Park_Warwick' };
  const txt = h => new DOMParser().parseFromString(h, 'text/html');
  const b64 = u8 => { let s = ''; for (let i = 0; i < u8.length; i += 0x8000) s += String.fromCharCode.apply(null, u8.subarray(i, i + 0x8000)); return btoa(s); };
  async function meetings(date) {
    const h = await (await fetch('/racing/full-calendar')).text(); const d = txt(h);
    const re = new RegExp(`/thoroughbred/meeting/([^/]+)/${date}$`);
    const seen = new Map();
    for (const u of [...d.querySelectorAll('a')].map(a => a.getAttribute('href') || '').filter(x => re.test(x))) { const code = decodeURIComponent(u.match(re)[1]).trim(); if (!seen.has(code.toUpperCase())) seen.set(code.toUpperCase(), { code, url: u }); }
    return [...seen.values()];
  }
  function conditions(doc) {
    const t = doc.body.innerText.replace(/\s+/g, ' ');
    const g = (re) => { const m = t.match(re); return m ? m[1].trim() : null; };
    return {
      track_condition: g(/Track (?:Turf|Synthetic|Poly(?:track)?)\s+((?:Good|Soft|Heavy|Firm|Synthetic)\s*\d*)/i) || g(/Tomorrow\s+((?:Good|Soft|Heavy|Firm|Synthetic)\s*\d*)/i) || g(/Today\s+((?:Good|Soft|Heavy|Firm|Synthetic)\s*\d*)/i),
      surface: g(/Track (Turf|Synthetic|Poly\w*)/i),
      rail: g(/Rail (.+?) Track (?:Turf|Synthetic|Poly)/i),
      penetrometer: g(/Pen (.+?) (?:Nil|\d+mm|Fine|Overcast|Light|Showers|Rain)/i),
      rainfall: g(/((?:Nil|[\d.]+mm)\s+last 24hrs,\s*[\d.]+mm last 7 days)/i),
      weather_text: g(/last 7 days (.+?) Track conditions update/i),
      conditions_updated: g(/Track conditions update: (.+?) Last Track Rating Update/i),
      rating_updated: g(/Last Track Rating Update: (.+?) (?:Nominations|Field|Weights)/i),
      scratchings_close: g(/Scratchings (\w{3} \d{2}\/\d{2}\/\d{2} \d{2}:\d{2}[ap]m)/i)
    };
  }
  function scratchings(doc) {
    return [...doc.querySelectorAll('.c-race-scratchings__race')].map(e => ({
      race_no: +(e.querySelector('.c-race-scratchings__race-number')?.textContent.trim() || 0),
      horses: [...e.querySelectorAll('.c-race-stratchings__horse')].map(h => { const s = h.textContent.trim().replace(/\s+/g, ' '); const m = s.match(/^(\d+)\.\s*(.*)$/); return m ? { saddlecloth: +m[1], horse: m[2] } : { saddlecloth: null, horse: s }; })
    }));
  }
  async function snapshot(date, code) {
    const t0 = new Date().toISOString(); const C = code.toUpperCase();
    const mu = `/racing/full-calendar/thoroughbred/meeting/${encodeURIComponent(code)}/${date}`;
    const mr = await fetch(mu); const mh = await mr.text(); const doc = txt(mh);
    if (/captcha|are you human/i.test(mh.slice(0, 5000))) throw new Error('CAPTCHA page: stop');
    const pu = `/RacingFile.ashx?path=/ThoroughbredMeetingFiles/rfd_${C}_${date}.pdf`;
    const pr = await fetch(pu); const pb = new Uint8Array(await pr.arrayBuffer()); const isPdf = new TextDecoder().decode(pb.slice(0, 5)).startsWith('%PDF');
    let fields = [], parse_error = null;
    if (isPdf) { try { fields = RQB.parseFields(await pdfItems(pb.buffer), date, TRACK[C] || C).map(r => { const v = r.split('|'); return { race_no: +v[2], race_name: v[3], distance_m: +v[4] || null, start_time: v[5], saddlecloth: +v[6] || null, horse: v[7], trainer: v[8], jockey: v[9], barrier: +v[10] || null, weight_kg: +v[11] || null, emergency: v[12] === 'EM' }; }); } catch (e) { parse_error = String(e).slice(0, 200); } }
    const snap = { kind: 'rq_prerace', schema: 1, date, meeting_code: C, track: TRACK[C] || null, retrieved_utc: t0, finished_utc: new Date().toISOString(),
      meeting_url: 'https://www.racingqueensland.com.au' + mu, meeting_http: mr.status, fields_pdf_url: 'https://www.racingqueensland.com.au' + pu, fields_pdf_http: pr.status,
      fields_pdf_ok: isPdf, fields_pdf_bytes: pb.length, fields_pdf_sha256: isPdf ? await ZW.sha(pb) : null, fields_pdf_b64: isPdf ? b64(pb) : null,
      conditions: conditions(doc), scratchings: scratchings(doc), fields, parse_error };
    const key = `rqpre:${date}:${C}:${t0.replace(/[-:.]/g, '')}`;
    if (await RBX.get(key)) throw new Error('key exists; refusing to overwrite ' + key);
    await RBX.put(key, snap);
    return { key, track: snap.track, runners: fields.length, races: new Set(fields.map(f => f.race_no)).size, scratched: snap.scratchings.reduce((a, r) => a + r.horses.length, 0), conditions: snap.conditions, parse_error };
  }
  async function all(date) { const ms = await meetings(date); const out = []; for (const m of ms) { try { out.push(await snapshot(date, m.code)); } catch (e) { out.push({ code: m.code, error: String(e).slice(0, 200) }); } await new Promise(r => setTimeout(r, 800)); } return out; }
  return { TRACK, meetings, snapshot, all, conditions, scratchings };
})();
