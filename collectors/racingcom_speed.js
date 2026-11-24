// racing.com Victorian speed-data collector. Run on https://dxp-static.racing.com/sectionals/index.html
// Needs the meeting's meetCode (shown in the Speed Data iframe on www.racing.com race pages).
// Usage: const races = []; for (let r = 1; r <= n; r++) races.push({race_no: r, data: (await SPD.render(meetCode, r)).out});
// Per horse: finish, saddlecloth, barrier, trainer, jockey, distance run, early/mid/late/peak/average speed,
// Store: await RBX.put('spd:VIC:2026-11-23:flemington', {state:'VIC', date:'2026-11-23', slug:'flemington', meet_code, retrieved_utc:new Date().toISOString(), races});
// Export: await RBX.export(['spd:VIC:2026-11-23'], 'racing_rcspeed_daily_20261123.jsonl.gz')
// time from each 200m point to the finish with position, and 200m split times with rank. About 0.5s per race.
window.SPD={
 parse(doc){ const T=[...doc.querySelectorAll('table')]; if(T.length<6) return null; const cell=t=>[...t.rows].map(r=>[...r.cells].map(c=>c.textContent.replace(/\s+/g,' ').trim()));
   const horses=cell(T[0]).slice(1).map(r=>{const s=r.join(' ').trim(); const m=s.match(/^(\d+\w*|[A-Z]+)\s+(\d+)\.\s+(.+?)\s+\((\d+)\)\s+T:\s*(.+?)\s+J:\s*(.+)$/); return m?{pos:m[1],tab:m[2],horse:m[3],barrier:m[4],trainer:m[5],jockey:m[6]}:{raw:s};});
   const ov=cell(T[1]); const cum=cell(T[3]); const sp=cell(T[5]);
   return {overview_head:ov[0], overview:ov.slice(1), cum_head:cum[0], cum:cum.slice(1), split_head:sp[0], splits:sp.slice(1), horses}; },
 render(meet, race, timeout=15000){ return new Promise(res=>{ const f=document.createElement('iframe'); f.style.cssText='position:fixed;left:-3000px;top:0;width:1400px;height:1000px'; let done=false; const t0=Date.now();
   const fin=()=>{ if(done) return; done=true; clearInterval(iv); let out=null; try{out=SPD.parse(f.contentDocument);}catch(e){} f.remove(); res({out, ms:Date.now()-t0}); };
   const iv=setInterval(()=>{ try{ const T=f.contentDocument.querySelectorAll('table'); if(T.length>=6 && T[5].rows.length>1 && T[0].rows.length===T[5].rows.length) fin(); }catch(e){} if(Date.now()-t0>timeout) fin(); }, 500);
   f.src=`/sectionals/index.html#?meetCode=${meet}&raceNumber=${race}`; document.body.appendChild(f); }); }
};

// Shared export helper: every stored record whose key starts with prefix -> one gzipped JSON-lines download.
window.RBX = window.RBX || {
 db(){return new Promise((res,rej)=>{const r=indexedDB.open('racing_bundles',1);r.onupgradeneeded=()=>r.result.createObjectStore('b');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 async put(k,v){const db=await this.db();return new Promise((res,rej)=>{const t=db.transaction('b','readwrite');t.objectStore('b').put(v,k);t.oncomplete=res;t.onerror=()=>rej(t.error);})},
 async export(prefixes, filename){ const db=await this.db(); const [keys,vals]=await Promise.all([new Promise(r=>{const q=db.transaction('b').objectStore('b').getAllKeys(); q.onsuccess=()=>r(q.result)}), new Promise(r=>{const q=db.transaction('b').objectStore('b').getAll(); q.onsuccess=()=>r(q.result)})]);
   const P=[].concat(prefixes); const lines=[]; keys.forEach((k,i)=>{ if(typeof k==='string' && P.some(p=>k.startsWith(p))) lines.push(JSON.stringify({key:k,value:vals[i]})); });
   const gz=await new Response(new Blob([lines.join('\n')]).stream().pipeThrough(new CompressionStream('gzip'))).blob();
   const url=URL.createObjectURL(gz); const a=document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(url),600000);
   return {records:lines.length, bytes:gz.size, filename}; }
};
