// Racing NSW results collector (mdata.racingnsw.com.au/FreeFields). Run on any mdata.racingnsw.com.au page.
// One request per meeting (all races on one page). Results are kept by Racing NSW for roughly four months.
// Usage: await NSWC.run(keys, 3000, force)  (force=true re-fetches keys already stored, e.g. interim results)
// Export: await RBX.export(['nsw:2026Nov23'], 'racing_nsw_freefields_daily_20261123.jsonl.gz')
// Old usage note: where keys look like '2026Oct03,NSW,Royal Randwick' (calendar page lists them).
// Stops if a CAPTCHA ("Are you human?") appears. Prices (SP column) are not captured.
window.NSWC = {
 st:{done:0,fail:0,total:0,errors:[],running:false},
 txt(e){return (e?.textContent||'').replace(/\s+/g,' ').trim()},
 async sha(s){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')},
 db(){return new Promise((res,rej)=>{const r=indexedDB.open('racing_bundles',1);r.onupgradeneeded=()=>r.result.createObjectStore('b');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 async put(k,v){const db=await this.db();return new Promise((res,rej)=>{const t=db.transaction('b','readwrite');t.objectStore('b').put(v,k);t.oncomplete=res;t.onerror=()=>rej(t.error);})},
 async keys(){const db=await this.db();return new Promise((res,rej)=>{const r=db.transaction('b').objectStore('b').getAllKeys();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 calendarKeys: async function(){ const cal=await fetch('/FreeFields/Calendar_Results.aspx').then(r=>r.text()); return [...new Set([...cal.matchAll(/Results\.aspx\?Key=([^"'&]+)/g)].map(m=>decodeURIComponent(m[1].replace(/\+/g,' '))))]; },
 parse(h,key){
  const d=new DOMParser().parseFromString(h,'text/html'); const T=e=>this.txt(e);
  const m={key, page_title:T(d.querySelector('div.freeze')).slice(0,400), venue_info:T(d.querySelector('div.race-venue-bottom')), na:/not currently available/.test(h), races:[]};
  for(const ti of [...d.querySelectorAll('div.race-title')]){
   const info=ti.nextElementSibling; const grp=info?.nextElementSibling; const tbl=grp?.querySelector('table.race-strip-fields');
   const race={title:T(ti), info:T(info), runners:[]};
   if(tbl){ for(const r of [...tbl.rows].slice(1)){ const c=cls=>T(r.querySelector('td.'+cls)); const cells=[...r.cells];
     race.runners.push({row_class:r.className, finish:c('finish-results'), tab:T(cells[2]), horse:c('horsename-results'), trainer:c('trainer-results'), jockey:T(cells[6]), margin:c('marg-results'), barrier:c('bar-results'), weight:c('wgt-results'), penalty:c('pen-results'), bmark:c('bmark-results'), sire_dam:c('SireDam-results')}); } }
   m.races.push(race);
  }
  return m;
 },
 async run(keys, gap=3000, force=false){
  this.st.running=true; this.st.total=keys.length; const have=new Set(await this.keys());
  for(const k of keys){
   const id='nsw:'+k; if(have.has(id) && !force){this.st.done++; continue;}
   const url='/FreeFields/Results.aspx?Key='+encodeURIComponent(k);
   try{ const r=await fetch(url); const h=await r.text();
     if(/Are you human/i.test(h)){this.st.errors.push('CAPTCHA at '+k); this.st.running=false; return;}
     if(/not currently available/.test(h) || !/race-strip-fields/.test(h)){ this.st.errors.push('no results: '+k); }
     else { const m=this.parse(h,k); m.http=r.status; m.bytes=h.length; m.sha256=await this.sha(h); m.retrieved_utc=new Date().toISOString(); m.url='https://mdata.racingnsw.com.au'+url; await this.put(id,m); }
     this.st.done++;
   }catch(e){this.st.fail++; this.st.errors.push(k+': '+e.message);}
   await new Promise(r=>setTimeout(r,gap+Math.random()*1000));
  }
  this.st.running=false;
 }
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
