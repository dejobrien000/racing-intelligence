// racing.com results collector (NSW + Victoria). Run on a www.racing.com page in a logged-out browser.
// Usage: RC.run([{state:'VIC', date:'2026-10-03', cands:['flemington']}, ...]) -> IndexedDB 'racing_bundles'/'b' keys rc:STATE:DATE:SLUG
// WARNING: each race is a full racing.com page render. Fine for a day's meetings; too heavy for multi-year history (froze Chrome on 24 Nov 2026).
// Daily use: const m = await RC.meeting({state:'VIC', date:'2026-11-23', cands:['flemington']}); await RC.put('rc:VIC:2026-11-23:flemington', m);
// Export: await RBX.export(['rc:VIC:2026-11-23'], 'racing_rc_daily_20261123.jsonl.gz')
// Never captures prices: SP/tote columns are skipped by the parser.

window.RC={ven:[["randwick","randwick-kensington"],["flemington"],["warwick-farm"],["caulfield"],["rosehill"],["canterbury","canterbury-park"],["sandown-hillside","sandown-lakeside"],["moonee-valley"],["newcastle","beaumont-newcastle"],["pakenham","pakenham-synthetic"],["kilmore"],["wyong"],["bendigo"],["hawkesbury"],["sale"],["kembla-grange"],["cranbourne","cranbourne-synthetic"],["canberra"],["ballarat","ballarat-synthetic"],["mornington"],["geelong","geelong-synthetic"],["seymour"],["gosford"],["traralgon"],["mortlake"],["coffs-harbour"],["wycheproof"],["dubbo"],["wagga","wagga-riverside"],["moree"],["warrnambool"],["casino"],["swan-hill"],["wangaratta"],["queanbeyan"],["coonabarabran"],["port-macquarie"],["yarra-valley"],["st-arnaud"],["albury"],["scone"],["kyneton"],["orange"],["muswellbrook"],["echuca"],["horsham"],["nowra"],["moe"],["lismore"],["wodonga"],["avoca"],["narromine"],["taree"],["bathurst"],["grafton"],["tamworth"],["bairnsdale"],["coonamble"],["manangatang"],["hamilton"],["forbes"],["mildura"],["goulburn"],["cootamundra"],["ballina"],["moruya"],["illawarra-grange"],["tatura"],["coleraine"],["leeton"],["armidale"],["bowraville"],["wellington"],["corowa"],["griffith"],["donald"],["tuncurry","tuncurry-forster"],["gundagai"],["kempsey"],["mudgee"],["casterton"],["warracknabeal"],["murwillumbah"],["murtoa"],["narrandera"],["gunnedah"],["quirindi"],["gilgandra"],["sapphire-coast"],["warren"],["inverell"],["cowra"],["werribee"],["stawell"],["parkes"],["ararat"],["terang"],["kerang"],["stony-creek"],["towong"],["edenhope"],["colac"],["tumut"],["walcha"],["hanging-rock"],["great-western"],["camperdown"],["glen-innes"],["burrumbeet"],["nhill"],["penshurst"],["dunkeld"],["gunbower"],["benalla"]], q:'',
 st:{done:0,skipped:0,miss:0,err:0,races:0,running:false,current:'',started:new Date().toISOString(),log:[]},
 sl:ms=>new Promise(r=>setTimeout(r,ms)),
 async sha(s){const b=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s));return [...new Uint8Array(b)].map(x=>x.toString(16).padStart(2,'0')).join('')},
 db(){return new Promise((res,rej)=>{const r=indexedDB.open('racing_bundles',1);r.onupgradeneeded=()=>r.result.createObjectStore('b');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 async put(k,v){const db=await this.db();return new Promise((res,rej)=>{const t=db.transaction('b','readwrite');t.objectStore('b').put(v,k);t.oncomplete=res;t.onerror=()=>rej(t.error);})},
 async keys(){const db=await this.db();return new Promise((res,rej)=>{const r=db.transaction('b').objectStore('b').getAllKeys();r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 async get(k){const db=await this.db();return new Promise((res,rej)=>{const r=db.transaction('b').objectStore('b').get(k);r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error);})},
 decode(q){const out=[];for(let i=0;i+9<=q.length;i+=9){const s=q[i],d='20'+q.substr(i+1,2)+'-'+q.substr(i+3,2)+'-'+q.substr(i+5,2),v=+q.substr(i+7,2);out.push({state:{N:'NSW',V:'VIC',A:'ACT'}[s],date:d,cands:this.ven[v]});}return out;},
 render(url, ready, timeout){ return new Promise(res=>{ const f=document.createElement('iframe'); f.style.cssText='position:fixed;left:-3000px;top:0;width:1200px;height:900px'; let done=false,obs=null; const t0=Date.now();
   const fin=ok=>{ if(done) return; done=true; try{obs&&obs.disconnect()}catch(e){} clearTimeout(to); let txt=''; let src=null; try{txt=f.contentDocument.body.innerText||''; src=[...f.contentDocument.querySelectorAll('iframe')].map(x=>x.src).find(s=>/sectionals/.test(s))||null;}catch(e){} f.remove(); res({ok,txt,src,ms:Date.now()-t0}); };
   const check=()=>{ try{ const d=f.contentDocument; if(d && d.body && ready(d.body.textContent, d)) fin(true);}catch(e){} };
   f.addEventListener('load',()=>{ try{ obs=new MutationObserver(check); obs.observe(f.contentDocument,{childList:true,subtree:true}); check(); }catch(e){} });
   const to=setTimeout(()=>{check(); fin(false)}, timeout); f.src=url; document.body.appendChild(f); }); },
 parseResults(txt){ const L=txt.split('\n').map(s=>s.trim()).filter(Boolean); const g=re=>{const m=txt.match(re);return m?m[1].trim():null};
   const head={race_time:g(/Race Time:\s*([0-9:.]+)/), prize:g(/Prize Money:\s*(\$[0-9,]+)/), conditions:g(/\n([^\n]*Track name:[^\n]*)/), track_cond:g(/\b((?:Good|Soft|Heavy|Firm|Synthetic)(?:\s*\d+)?)\s*\n?\s*Track/), rail:g(/Track\s*\n?\s*Rail\s*\n?\s*([^\n]+)/)||g(/Rail\s*\n?\s*([^\n]+)/), start:g(/\n(\d{1,2}:\d{2}[ap]m)\n/), distance:g(/\n(\d{3,4})m\n/)};
   const i=L.indexOf('ONE POOL'); const runners=[]; if(i<0) return {head,runners};
   const posRe=/^(\d+(st|nd|rd|th)|SCR|LSCR|FF|DNF|NTD|LR|DQ|PU|FELL|DSQ)$/; const hRe=/^(\d+)\.\s+(.+?)\s+\((\d+)\)$/;
   for(let k=i+1;k<L.length;k++){ if(!posRe.test(L[k])||!hRe.test(L[k+1]||'')) continue; const m=L[k+1].match(hRe); const r={pos:L[k],tab:m[1],horse:m[2],barrier:m[3]};
     let j=k+2; if(L[j]==='T:'){r.trainer=L[j+1];j+=2;} if(L[j]==='J:'){r.jockey=L[j+1];j+=2;}
     for(let q=j;q<Math.min(j+6,L.length);q++){const s=L[q]; if(/^[\d.]+kg$/.test(s)) r.weight=s; else if(/^\d+(st|nd|rd|th)\/\d+(st|nd|rd|th)$/.test(s)) r.pos800_400=s; else if(r.weight && !r.margin && /^([\d.]+L|\d+:\d{2}\.\d+|\d{2}\.\d+|NK|HD|SHD|NOSE|DH|LSHD|SNK|LNK|1\/2HD)$/i.test(s)) r.margin=s;}
     runners.push(r);} return {head,runners}; },
 async meeting(m){ for(const slug of m.cands){ const base=`/form/${m.date}/${slug}/race/`; const races=[]; let nRaces=null, meetCode=null;
     for(let r=1;r<=(nRaces||12);r++){ const R=await this.render(base+r+'/results', t=>{const u=t.toUpperCase(); return u.includes('ONE POOL')&&u.includes('RACE TIME:')}, r===1?14000:12000);
       if(r===1 && !R.ok){ break; }
       if(nRaces===null){ const mm=R.txt.match(/Final Result\s*\n?\s*All\s*\n?([\d\s]+)/i); nRaces=mm?Math.max(...mm[1].trim().split(/\s+/).map(Number)):12; }
       const p=this.parseResults(R.txt); p.race_no=r; p.ok=R.ok; p.render_ms=R.ms; p.url='https://www.racing.com'+base+r+'/results'; p.retrieved_utc=new Date().toISOString(); p.text_sha256=await this.sha(R.txt); races.push(p); this.st.races++;
       if(r===1 && m.state==='VIC'){ const S=await this.render(base+'1/speed-data', (t,d)=>[...d.querySelectorAll('iframe')].some(x=>/sectionals/.test(x.src)), 9000); meetCode=(S.src||'').match(/meetCode=(\d+)/)?.[1]||null; }
       await this.sl(900);
     }
     if(races.length) return {state:m.state,date:m.date,slug,n_races:nRaces,meet_code:meetCode,races}; }
   return null; },
 async run(list){ if(this.st.running) return 'already running'; this.st.running=true; const have=new Set(await this.keys());
   for(const m of list){ const id='rc:'+m.state+':'+m.date+':'+m.cands[0]; if(have.has(id)){this.st.skipped++; continue;} this.st.current=id;
     try{ const out=await this.meeting(m); if(out){ await this.put(id,out); this.st.done++; } else { await this.put('miss:'+id,{m,at:new Date().toISOString()}); this.st.miss++; } }
     catch(e){ this.st.err++; this.st.log.push(id+': '+e.message); }
     if(this.st.stop) break; }
   this.st.running=false; this.st.finished=new Date().toISOString(); }
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
