// helpers copied verbatim from history/browser_bundle.js (sha, pdfItems, parseFields)
window.ZW = window.ZW || {}; window.ZW.sha = async u8 => [...new Uint8Array(await crypto.subtle.digest('SHA-256', u8))].map(b=>b.toString(16).padStart(2,'0')).join('');
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

window.RQB = window.RQB || {};
window.RQB.parseFields = function(pages, date, track) {
    const clean = v => (v ?? '').toString().replace(/[|\r\n]+/g,' ').trim();
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
