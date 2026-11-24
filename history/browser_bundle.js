// Racing Intelligence: history bundle builder. Run in a browser tab on
// https://www.racingqueensland.com.au/industry/thoroughbred/thoroughbred-sectionals
// It fetches RQ tracking ZIPs + Race Fields PDFs (all 1,266+ tracked Qld meetings) and Betfair ANZ files,
// parses them in the page, strips every Betfair price column, and saves one bundle per year:
//   racing_rq_YYYY.zip      raw/sectionals/*.zip, raw/racefields/*.pdf, parsed/{races,runners,secs,fields,log}.psv
//   racing_betfair_YYYY.zip ANZ_Thoroughbreds_*_noprices.csv + MANIFEST.csv
// Progress: window.__status. Start: window.RUN({rqYears:[2022,...], bfYears:[2020,...]})

window.ZW = (() => {
  const T = new Uint32Array(256); for (let n=0;n<256;n++){ let c=n; for(let k=0;k<8;k++) c = c&1 ? 0xEDB88320^(c>>>1) : c>>>1; T[n]=c>>>0; }
  const crc32 = u8 => { let c = 0xFFFFFFFF; for (let i=0;i<u8.length;i++) c = T[(c^u8[i])&0xFF]^(c>>>8); return (c^0xFFFFFFFF)>>>0; };
  const deflate = async u8 => new Uint8Array(await new Response(new Blob([u8]).stream().pipeThrough(new CompressionStream('deflate-raw'))).arrayBuffer());
  const inflate = async u8 => new Uint8Array(await new Response(new Blob([u8]).stream().pipeThrough(new DecompressionStream('deflate-raw'))).arrayBuffer());
  async function build(entries) { const parts = [], central = []; let off = 0; const enc = new TextEncoder();
    for (const e of entries) { const name = enc.encode(e.name); const crc = crc32(e.data); const comp = e.compress ? await deflate(e.data) : e.data; const method = e.compress ? 8 : 0;
      const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0,0x04034b50,true); lh.setUint16(4,20,true); lh.setUint16(6,0x0800,true); lh.setUint16(8,method,true); lh.setUint16(12,0x21,true); lh.setUint32(14,crc,true); lh.setUint32(18,comp.length,true); lh.setUint32(22,e.data.length,true); lh.setUint16(26,name.length,true);
      parts.push(new Uint8Array(lh.buffer), name, comp);
      const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0,0x02014b50,true); ch.setUint16(4,20,true); ch.setUint16(6,20,true); ch.setUint16(8,0x0800,true); ch.setUint16(10,method,true); ch.setUint16(14,0x21,true); ch.setUint32(16,crc,true); ch.setUint32(20,comp.length,true); ch.setUint32(24,e.data.length,true); ch.setUint16(28,name.length,true); ch.setUint32(42,off,true);
      central.push(new Uint8Array(ch.buffer), name); off += 30 + name.length + comp.length; }
    const cdSize = central.reduce((a,b)=>a+b.length,0); const end = new DataView(new ArrayBuffer(22)); end.setUint32(0,0x06054b50,true); end.setUint16(8,entries.length,true); end.setUint16(10,entries.length,true); end.setUint32(12,cdSize,true); end.setUint32(16,off,true);
    return new Blob([...parts, ...central, new Uint8Array(end.buffer)], {type:'application/zip'}); }
  function readZip(buf) { const dv = new DataView(buf), u8 = new Uint8Array(buf); let eocd=-1; for (let i=buf.byteLength-22;i>=0;i--){ if(dv.getUint32(i,true)===0x06054b50){eocd=i;break;} }
    const n=dv.getUint16(eocd+10,true); let off=dv.getUint32(eocd+16,true); const out=[];
    for(let k=0;k<n;k++){ const method=dv.getUint16(off+10,true), csize=dv.getUint32(off+20,true), fl=dv.getUint16(off+28,true), el=dv.getUint16(off+30,true), cl=dv.getUint16(off+32,true), lho=dv.getUint32(off+42,true); const name=new TextDecoder().decode(u8.slice(off+46,off+46+fl)); off+=46+fl+el+cl;
      const lfl=dv.getUint16(lho+26,true), lel=dv.getUint16(lho+28,true); out.push({name, method, data: u8.subarray(lho+30+lfl+lel, lho+30+lfl+lel+csize)}); } return out; }
  const sha = async u8 => [...new Uint8Array(await crypto.subtle.digest('SHA-256', u8))].map(b=>b.toString(16).padStart(2,'0')).join('');
  function save(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url), 120000); }
  return {crc32, deflate, inflate, build, readZip, sha, save};
})();

window.pdfItems = async (buf) => {
  const u8 = new Uint8Array(buf); const latin = new TextDecoder('latin1').decode(u8);
  const re = /stream\r?\n/g; let m; const pages = [];
  while ((m = re.exec(latin))) { const start = m.index + m[0].length; const end = latin.indexOf('endstream', start); const dict = latin.slice(Math.max(0, latin.lastIndexOf('<<', m.index)), m.index); re.lastIndex = end;
    if (!/FlateDecode/.test(dict) || /Length1|Image|CIDInit|XObject/.test(dict)) continue; let d = u8.slice(start, end); let e = d.length; while (e > 0 && (d[e-1]===10||d[e-1]===13)) e--; d = d.slice(0, e);
    let t; try { t = new TextDecoder('latin1').decode(await new Response(new Blob([d]).stream().pipeThrough(new DecompressionStream('deflate'))).arrayBuffer()); } catch(err) { continue; }
    if (!/Tj/.test(t)) continue; const items = []; let lx=0, ly=0; const rx = /1 0 0 -1 (-?[\d.]+) (-?[\d.]+) Tm|(-?[\d.]+) (-?[\d.]+) Td|\(((?:\\.|[^\\)])*)\) Tj/g; let k;
    while ((k = rx.exec(t))) { if (k[1]!==undefined){lx=+k[1];ly=+k[2];} else if (k[3]!==undefined){lx+=+k[3];ly-=+k[4];} else items.push({x:Math.round(lx), y:Math.round(ly), s:k[5].replace(/\\(.)/g,'$1')}); }
    pages.push({items}); }
  return pages; };

window.RQB = (() => {
  const CODES = {Doomben:'DOOM', Eagle_Farm:'E_FM', Ipswich:'IPSW', Kilcoy:'KCOY', Ladbrokes_Cannon_Park:'CRNS', Mackay:'MKAY', Rockhampton:'ROCK', Sunshine_Coast:'SCST', Sunshine_Coast_Poly_Track:'SCPT', TAB_Park_Gold_Coast:'GCST', Toowoomba:'TWBA', Townsville:'TOWN', Dalby:'DALB', Picklebet_Park_Warwick:'WARW'};
  const ts = s => { if(!s) return ''; const m=s.match(/(\d+):(\d+):([\d.]+)/); return m? (+m[1]*3600 + +m[2]*60 + +m[3]).toFixed(3) : s; };
  const clean = v => (v ?? '').toString().replace(/[|\r\n]+/g,' ').trim();
  async function parseZip(buf, date, track) {
    const races=[], runners=[], secs=[];
    for (const e of window.ZW.readZip(buf)) { if (!/\.xml$/i.test(e.name)) continue;
      const txt = new TextDecoder().decode(e.method===8 ? await window.ZW.inflate(e.data) : e.data);
      const doc = new DOMParser().parseFromString(txt,'application/xml'); const r = doc.documentElement; if (!r || r.nodeName!=='RaceSummary') continue;
      const T = (el, sel) => { const x = el.querySelector(sel); return x ? (x.getAttribute('Time') ?? x.textContent.trim()) : ''; };
      const rn = +(e.name.match(/_R(\d+)\.xml$/i)||[])[1]; const hs=[...r.querySelectorAll('Horses > HorseSummary')];
      races.push([date, track, rn, r.getAttribute('MeetingCode'), r.getAttribute('RaceCode'), T(r,':scope > RaceName'), ts(T(r,':scope > FinishTime')), T(r,':scope > TrackName'), T(r,':scope > TrackCondition'), T(r,':scope > RailPosition'), hs.length].map(clean).join('|'));
      for (const h of hs) { const a=x=>h.getAttribute(x)??''; const sub=h.querySelector(':scope > ResultSubState');
        runners.push([date, track, rn, a('HorseCode'),a('Name'),a('Bib'),a('FinalRank'),a('OfficialMarginDecimal'),ts(T(h,':scope > FinishTime')),a('IsFinishTimeOfficial'),T(h,':scope > ResultState'), sub && sub.getAttribute('xsi:nil')!=='true' ? sub.textContent : '', a('DistanceTravelled'),a('DistanceTraveledDifference')].map(clean).join('|'));
        if (T(h,':scope > ResultState') === 'DidNotStart') continue;
        for (const s of h.querySelectorAll(':scope > Sections > SectionSummary')) { const q=x=>{const y=s.querySelector(':scope > '+x); return y? y.textContent.trim():'';};
          secs.push([date, track, rn, a('Bib'), s.getAttribute('CumulatedDistance'),q('RealDistance'),q('Rank'),ts(T(s,':scope > IntermediateTime')),ts(T(s,':scope > SectionTime')),q('AvgSpeed'),q('TopSpeed'),q('AverageStrideFrequency'),q('AverageStrideLength'),q('AverageDistanceToRail'),s.getAttribute('MarginDecimal')].map(clean).join('|')); } } }
    return {races, runners, secs}; }
  function parseFields(pages, date, track) {
    const bases=[569,5899,11229]; const col = x => x<5500?0:(x<10850?1:2); const near=(a,b,t)=>Math.abs(a-b)<=t; const rows=[]; let race=null; const races={};
    pages.forEach(pg => { for (const c of [0,1,2]) { const b=bases[c]; const it = pg.items.filter(i=>col(i.x)===c).sort((p,q)=>p.y-q.y||p.x-q.x);
      const anchors = it.filter(i=>near(i.x,b+4522,40) && /^\s*\d{2}\.\d\s*$/.test(i.s)).map(i=>i.y);
      for (const i of it) {
        if (i.x>=b-450 && i.x<=b-150 && /^\s*\d{1,2}\s*$/.test(i.s)) { race=+i.s.trim(); races[race]={name: it.filter(j=>near(j.x,b,5) && j.y>=i.y-10 && j.y<=i.y+260 && !/metres$/.test(j.s)).map(j=>j.s).join('').replace(/\s+/g,' ').trim()}; continue; }
        if (race && near(i.x,b,5) && /^\d+ metres$/.test(i.s)) { races[race].dist=i.s.replace(' metres',''); const st=it.find(j=>j.y===i.y && /\d\d:\d\d[AP]M/.test(j.s)); races[race].time = st?st.s:''; continue; }
        if (race && near(i.x,b+4522,40) && /^\s*\d{2}\.\d\s*$/.test(i.s)) { const y=i.y; const nextA = anchors.find(a=>a>y+20) ?? Infinity; const nh = it.find(j=>j.y>y+20 && ((j.x>=b-450 && j.x<=b-150 && /^\s*\d{1,2}\s*$/.test(j.s)) || /metres$/.test(j.s))); const lim = Math.min(nextA, nh?nh.y:Infinity) - 10;
          const tab=it.find(j=>near(j.x,b,5) && near(j.y,y,10) && /^\d{1,2}$/.test(j.s.trim())); const bar=it.find(j=>j.x>b+4150 && j.x<b+4450 && near(j.y,y,10));
          const name=it.filter(j=>near(j.x,b+399,5) && j.y>=y-10 && j.y<=lim).map(j=>j.s).join('').trim(); const jock=it.filter(j=>j.x>b+2800 && j.x<b+4150 && j.y>=y-10 && j.y<=lim).map(j=>j.s).join('').replace(/\s+/g,' ').trim();
          let em=''; let nm=name; if (nm.startsWith('(EM)')) { em='EM'; nm=nm.slice(4); } const mm = nm.match(/^(.*)\(([^()]*)\)$/);
          rows.push([date, track, race, races[race].name, races[race].dist||'', races[race].time||'', tab?tab.s.trim():'', mm?mm[1].trim():nm, mm?mm[2].trim():'', jock, bar?bar.s.trim():'', i.s.trim(), em].map(clean).join('|')); } } } });
    return rows; }
  async function getBuf(url) { for (let a=0;a<3;a++) { try { const r = await fetch(url); const b = await r.arrayBuffer(); const head = new TextDecoder().decode(new Uint8Array(b).slice(0,5)); return {status:r.status, buf:b, ok: r.ok && (head.startsWith('%PDF') || head.startsWith('PK')) }; } catch(e) { await new Promise(r=>setTimeout(r, 1500)); } } return {status:0, buf:null, ok:false}; }
  async function meeting(m) { const out = {date:m.date, track:m.track, raw:[], races:[], runners:[], secs:[], fields:[], log:[]};
    const zu = `/RacingFile.ashx?path=/Sectional/${m.date}_${m.track}_T.zip`; const z = await getBuf(zu);
    out.log.push([m.date, m.track, 'sectional_zip', 'https://www.racingqueensland.com.au'+zu, z.status, z.buf?z.buf.byteLength:0, z.ok && z.buf ? await window.ZW.sha(new Uint8Array(z.buf)) : '', new Date().toISOString()].join('|'));
    if (z.ok) { out.raw.push({name:`sectionals/${m.date}_${m.track}_T.zip`, data:new Uint8Array(z.buf)}); try { const p = await parseZip(z.buf, m.date, m.track); out.races=p.races; out.runners=p.runners; out.secs=p.secs; } catch(e) { out.log.push([m.date,m.track,'parse_error_zip','',0,0,String(e).slice(0,100),''].join('|')); } }
    const code = CODES[m.track]; if (code) { const fu = `/RacingFile.ashx?path=/ThoroughbredMeetingFiles/rfd_${code}_${m.date}.pdf`; const f = await getBuf(fu);
      out.log.push([m.date, m.track, 'race_fields_pdf', 'https://www.racingqueensland.com.au'+fu, f.status, f.buf?f.buf.byteLength:0, f.ok && f.buf ? await window.ZW.sha(new Uint8Array(f.buf)) : '', new Date().toISOString()].join('|'));
      if (f.ok) { out.raw.push({name:`racefields/rfd_${code}_${m.date}.pdf`, data:new Uint8Array(f.buf)}); try { out.fields = parseFields(await window.pdfItems(f.buf), m.date, m.track); } catch(e) { out.log.push([m.date,m.track,'parse_error_pdf','',0,0,String(e).slice(0,100),''].join('|')); } } }
    return out; }
  async function run(meetings, conc=3, progress) { const res = new Array(meetings.length); let next = 0, done = 0;
    const worker = async () => { while (next < meetings.length) { const i = next++; res[i] = await meeting(meetings[i]); done++; if (progress) progress(done); await new Promise(r=>setTimeout(r, 150)); } };
    await Promise.all(Array.from({length:conc}, worker)); return res; }
  const HEAD = {races:'date|track|race_no|meeting_code|race_code|race_name|finish_time_s|track_name|track_condition|rail|n_horses', runners:'date|track|race_no|horse_code|name|bib|final_rank|official_margin|finish_time_s|is_official|result_state|result_substate|dist_travelled|dist_diff', secs:'date|track|race_no|bib|cum_dist|real_dist|rank|inter_s|section_s|avg_speed|top_speed|stride_freq|stride_len|dist_rail|margin_dec', fields:'date|track|race_no|race_name|distance_m|start_time|tab|horse|trainer|jockey|barrier|weight_kg|emergency', log:'date|track|kind|url|http_status|bytes|sha256|retrieved_utc'};
  async function bundle(results) { const enc = new TextEncoder(); const entries = [];
    for (const r of results) for (const f of r.raw) entries.push({name: 'raw/'+f.name, data: f.data, compress: false});
    for (const k of ['races','runners','secs','fields','log']) entries.push({name: `parsed/${k}.psv`, data: enc.encode([HEAD[k], ...results.flatMap(r=>r[k])].join('\n')+'\n'), compress: true});
    return window.ZW.build(entries); }
  function meetingList() { const sec = {}; for (const h of [...document.querySelectorAll('a')].map(a=>a.getAttribute('href')).filter(Boolean)) { const m = h.match(/\/Sectional\/(\d{8})_(.+)_T\.(csv|zip|pdf)$/i); if (m) sec[m[1]+'|'+m[2]] = {date:m[1], track:m[2]}; } return Object.values(sec).sort((a,b)=>a.date.localeCompare(b.date)); }
  return {CODES, parseZip, parseFields, meeting, run, bundle, HEAD, meetingList};
})();

window.BF = (() => {
  const KEEP = ['LOCAL_MEETING_DATE','SCHEDULED_RACE_TIME','ACTUAL_OFF_TIME','TRACK','STATE_CODE','RACE_NO','WIN_MARKET_ID','WIN_MARKET_NAME','PLACE_MARKET_ID','RACING_TYPE','DISTANCE','RACE_TYPE','SELECTION_ID','TAB_NUMBER','SELECTION_NAME','WIN_RESULT','PLACE_RESULT'];
  const parse = line => { const out=[]; let cur='', q=false; for (let i=0;i<line.length;i++){ const ch=line[i]; if(q){ if(ch==='"'){ if(line[i+1]==='"'){cur+='"';i++;} else q=false; } else cur+=ch; } else { if(ch===','){out.push(cur);cur='';} else if(ch==='"') q=true; else cur+=ch; } } out.push(cur); return out; };
  function strip(txt) { const lines = txt.split(/\r?\n/).filter(l=>l.length); const H = parse(lines[0]); const idx = KEEP.map(k=>H.indexOf(k));
    const esc = v => /[",\n]/.test(v) ? '"'+v.replace(/"/g,'""')+'"' : v; const out = [KEEP.join(',')]; let bad = 0;
    for (const l of lines.slice(1)) { const f = parse(l); if (f.length !== H.length) { bad++; continue; } out.push(idx.map(i=> i<0 ? '' : esc(f[i])).join(',')); }
    return {csv: out.join('\n')+'\n', rows: out.length-1, bad, ncols: H.length, missing: KEEP.filter((k,i)=>idx[i]<0).join(' ')}; }
  const BASE = 'https://betfair-datascientists.github.io/data/assets/';
  async function year(y) { const enc = new TextEncoder(); const entries = []; const man = ['file,source_url,source_bytes,source_sha256,inner_file,rows_kept,rows_malformed,source_columns,missing_columns,retrieved_utc'];
    const sources = y < 2026 ? [`ANZ_Thoroughbreds_${y}.zip`] : Array.from({length:12},(_,i)=>`ANZ_Thoroughbreds_${y}_${String(i+1).padStart(2,'0')}.csv`);
    for (const f of sources) { const r = await fetch(BASE+f); if (!r.ok) continue; const b = new Uint8Array(await r.arrayBuffer()); const h = await window.ZW.sha(b);
      const inner = f.endsWith('.zip') ? await Promise.all(window.ZW.readZip(b.buffer).filter(e=>/\.csv$/i.test(e.name)).map(async e=>({name:e.name, data: e.method===8 ? await window.ZW.inflate(e.data) : e.data}))) : [{name:f, data:b}];
      for (const e of inner) { const s = strip(new TextDecoder().decode(e.data)); const nm = e.name.split('/').pop().replace(/\.csv$/i,'_noprices.csv');
        entries.push({name: nm, data: enc.encode(s.csv), compress: true}); man.push([nm, BASE+f, b.length, h, e.name, s.rows, s.bad, s.ncols, s.missing, new Date().toISOString()].join(',')); } }
    entries.push({name:'MANIFEST.csv', data: enc.encode(man.join('\n')+'\n'), compress: true});
    return {blob: await window.ZW.build(entries), manifest: man}; }
  return {strip, year};
})();

window.RUN = async function({rqYears = [2022,2023,2024,2025,2026], bfYears = [2020,2021,2022,2023,2024,2025,2026], conc = 3} = {}) {
  window.__status = {started: new Date().toISOString(), done: [], current: null, progress: 0, errors: []};
  const all = window.RQB.meetingList();
  for (const y of rqYears) { const ms = all.filter(m=>m.date.startsWith(String(y))); window.__status.current = `rq ${y} (${ms.length} meetings)`;
    try { const res = await window.RQB.run(ms, conc, d => window.__status.progress = d); const blob = await window.RQB.bundle(res);
      window.ZW.save(blob, `racing_rq_${y}.zip`); const logs = res.flatMap(r=>r.log);
      window.__status.done.push({file:`racing_rq_${y}.zip`, bytes: blob.size, meetings: ms.length, zipsOk: res.filter(r=>r.raw.some(f=>f.name.startsWith('sectionals'))).length, fieldsOk: res.filter(r=>r.raw.some(f=>f.name.startsWith('racefields'))).length, parseErrors: logs.filter(l=>l.includes('parse_error')).length}); }
    catch(e) { window.__status.errors.push(`rq ${y}: ${e}`); }
    await new Promise(r=>setTimeout(r, 2000)); }
  for (const y of bfYears) { window.__status.current = `betfair ${y}`;
    try { const {blob, manifest} = await window.BF.year(y); window.ZW.save(blob, `racing_betfair_${y}.zip`); window.__status.done.push({file:`racing_betfair_${y}.zip`, bytes: blob.size, files: manifest.length-1}); }
    catch(e) { window.__status.errors.push(`betfair ${y}: ${e}`); }
    await new Promise(r=>setTimeout(r, 2000)); }
  window.__status.current = 'finished'; window.__status.finished = new Date().toISOString(); return window.__status; };
