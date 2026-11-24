"""25 Nov 2026 (b): national coverage, market price layer, Results/ROI, freshness, simpler primary view (kg scale moved to Advanced)."""
import re
p = 'ui/index.html'; s = open(p).read()
def rep(old, new, count=1):
    global s
    assert s.count(old) >= 1, ('missing', old[:80])
    s = s.replace(old, new) if count == 0 else s.replace(old, new, count)
def func(name, new):
    """replace a whole top-level function: from '\nfunction name(' to the next top-level line starting 'function ' or 'const '"""
    global s
    i = s.index('\nfunction ' + name + '(')
    m = re.compile(r'\n(function |const )').search(s, i + 1)
    s = s[:i] + '\n' + new.strip('\n') + s[m.start():]

# ---------- CSS ----------
rep('.row{display:grid;grid-template-columns:34px minmax(0,1.8fr) minmax(0,1.5fr) 62px minmax(0,1.7fr) 104px 156px 76px;',
    '.row{display:grid;grid-template-columns:34px minmax(0,1.5fr) minmax(0,1.35fr) 84px minmax(0,1.5fr) 150px 96px minmax(0,1.6fr);')
rep(' .row{grid-template-columns:28px minmax(0,1fr) auto;grid-template-areas:"rk hn pl" "rk rc rc" "rk mt mt";',
    ' .row{grid-template-columns:28px minmax(0,1fr) auto;grid-template-areas:"rk hn pl" "rk rc mk" "rk mt mt" "rk why why";')
rep(' .row .c-rt,.row .c-ir,.row .c-gp,.row .c-ev{display:none}',
    ' .row .c-rt,.row .c-ir,.row .c-gp,.row .c-ev{display:none}\n .row .c-mk{grid-area:mk;text-align:right}.row .c-why{grid-area:why}.mo{display:inline!important}')
rep('.wait{', '.warn{border:1px solid #7a5a2e;background:#211a10;color:#f1c98f;border-radius:10px;padding:10px 14px;margin:0 0 12px;font-size:14px}\n'
             '.info{border:1px solid var(--line);background:var(--panel2);color:var(--mute);border-radius:10px;padding:10px 14px;margin:0 0 12px;font-size:14px}\n'
             '.fresh{margin:0 0 12px}.mo{display:none}tr.strike td{color:var(--faint);text-decoration:line-through}\n.wait{')

# ---------- helpers ----------
rep("const CLS={'Strong selection':'p-strong',", "const CLS={'Not rated':'p-ins','Strong selection':'p-strong',")
rep("const $=id=>document.getElementById(id);",
    "const $=id=>document.getElementById(id);\nlet adv=false;\nconst RM=()=>D.meetings.filter(m=>m.rated);\n"
    "const price=mk=>{if(!mk)return '<span class=\"faint\" title=\"No authorised price feed connected\">no feed</span>';const w=mk.fixed_win,b=mk.exchange_back||mk.exchange_ltp;let o='';"
    "if(w)o+='<span class=\"num\">$'+(+w.price).toFixed(2)+'</span>'+(mk.fixed_place?' <span class=\"sub num\">place $'+(+mk.fixed_place.price).toFixed(2)+'</span>':'')+'<div class=\"sub\">'+esc(w.source)+' fixed · '+esc(bris(w.captured_utc))+'</div>';"
    "if(b)o+='<div><span class=\"num\">'+(+b.price).toFixed(2)+'</span> <span class=\"sub\">'+esc(b.source)+' exchange (not TAB) · '+esc(bris(b.captured_utc))+'</span></div>';return o||'<span class=\"faint\">–</span>'};\n"
    "const reasons=h=>(h.reasons&&h.reasons.length?esc(h.reasons.join(' · ')):'<span class=\"faint\">No single factor stands out</span>');")

func('stats', r"""function stats(){const rated=RM().flatMap(m=>m.races),all=D.meetings.flatMap(m=>m.races);const lab=l=>rated.filter(r=>r.label===l).length;return {races:all,rated,n:all.reduce((a,r)=>a+r.runners.filter(x=>(x.status||'runner')==='runner').length,0),strong:lab('Strong selection'),lead:lab('Leading contender'),none:lab('No clear selection'),ins:lab('Insufficient evidence'),fo:all.length-rated.length}}
function freshBox(){
 const F=D.freshness||{};const now=Date.now();const day0=new Date(D.date+'T00:00:00+10:00').getTime();
 const left=D.meetings.flatMap(m=>m.races).filter(r=>r.time_brisbane_min!=null&&day0+r.time_brisbane_min*60000>now).length;
 const mins=F.latest_update_utc?Math.round((now-new Date(F.latest_update_utc))/60000):null;const stale=left>0&&mins!=null&&mins>(F.stale_after_min||90);
 const age=mins==null?'unknown':mins<60?mins+' min ago':Math.floor(mins/60)+' h '+(mins%60)+' min ago';
 return (stale?'<div class="warn"><b>Data may be stale.</b> The last successful update was '+esc(age)+' ('+esc(bris(F.latest_update_utc))+') and '+left+' race'+(left>1?'s are':' is')+' still to run. Scratchings or rider changes since then are not reflected.</div>':'')+
  '<div class="fresh sm mute">Latest successful update <b>'+esc(F.latest_update_utc?bris(F.latest_update_utc):'–')+'</b> ('+esc(age)+') · page built '+esc(bris(D.exported_utc))+' · Brisbane time</div>';
}
function mktBox(){const M=D.markets||{};if(M.runners_priced)return '';return '<div class="info"><b>Market prices:</b> '+esc(M.message||'No price feed connected.')+'<div style="margin-top:6px">'+(M.sources||[]).map(x=>'<span class="badge" style="margin:4px 6px 0 0" title="'+esc(x.detail||'')+'">'+esc(x.name)+': '+esc(x.status)+'</span>').join('')+'</div></div>'}
function coverage(){const C=D.completeness;if(!C)return '';const T=C.rows.reduce((a,r)=>({e:a.e+r.races_expected,c:a.c+r.races_collected,n:a.n+r.runners,p:a.p+r.prices,q:a.q+r.races_rated}),{e:0,c:0,n:0,p:0,q:0});
 return '<section class="panel" style="margin-top:16px"><div class="ph"><h2>Coverage: every Australian thoroughbred meeting today</h2></div><div class="scroll"><table><thead><tr><th>Meeting</th><th class="r">Races expected</th><th class="r">Fields collected</th><th class="r">Runners</th><th class="r">Races rated</th><th class="r">Runners priced</th><th class="hidem">Fields source</th><th>Missing or limited</th></tr></thead><tbody>'+
 C.rows.map(r=>'<tr data-go="'+r.meeting.toLowerCase()+'-r1" style="cursor:pointer"><td><b>'+esc(r.meeting)+'</b> <span class="sub">'+esc(r.state)+'</span></td><td class="r num">'+r.races_expected+'</td><td class="r num">'+r.races_collected+'</td><td class="r num">'+r.runners+'</td><td class="r num">'+r.races_rated+'</td><td class="r num">'+r.prices+'</td><td class="sm hidem">'+esc(r.fields_source)+'</td><td class="sm mute">'+(r.issues.length?r.issues.map(esc).join('; '):'–')+'</td></tr>').join('')+
 '<tr><td><b>Total</b></td><td class="r num"><b>'+T.e+'</b></td><td class="r num"><b>'+T.c+'</b></td><td class="r num"><b>'+T.n+'</b></td><td class="r num"><b>'+T.q+'</b></td><td class="r num"><b>'+T.p+'</b></td><td class="hidem"></td><td></td></tr></tbody></table></div><p class="sm faint" style="margin:8px 0 0">Calendar: '+esc(C.calendar_source)+'. '+esc(C.act_nt||'')+'. Not included: '+esc((C.excluded||[]).join(', '))+'.</p></section>';}""")

func('boardRows', r"""function boardRows(list){
 return '<div class="board"><div class="row hd"><div class="r">#</div><div>Horse</div><div>Race</div><div>Rank in race</div><div>Model win chance</div><div>Selection strength</div><div>Market price</div><div>Key reasons</div></div>'+list.map(e=>{
  const col=COLOR[e.class];const rk=e.rank===1?'Top-rated':ordinal(e.rank).replace(' of field','');
  return '<div class="row" tabindex="0" data-h="'+esc(e.meeting)+'|'+e.race+'|'+e.n+'"><div class="rk c-rk">'+e.day_rank+'</div><div class="c-hn"><div class="hn"><span class="sc">'+e.n+'</span>'+esc(e.horse)+'</div></div><div class="c-rc sub">'+esc(e.meeting)+' R'+e.race+' · <span class="num">'+esc(e.time)+'</span> <span class="faint">'+esc(e.tz)+'</span><span class="mo"> · '+rk+'</span></div><div class="c-ir sm">'+rk+'</div><div class="c-mt" style="display:grid;grid-template-columns:minmax(0,1fr) 46px;gap:8px;align-items:center">'+meter(e.cal,e.cal_lo,e.cal_hi,col)+'<span class="num r">'+pc(e.cal)+'</span></div><div class="c-pl">'+pill(e.class)+'</div><div class="c-mk sm">'+price(e.market)+'</div><div class="c-why sm mute">'+reasons(e)+'</div></div>'}).join('')+'</div>';
}""")

# ---------- Today ----------
rep("return '<div class=\"head\"><div><h1>'+esc(D.weekday)", "return freshBox()+'<div class=\"head\"><div><h1>'+esc(D.weekday)")
rep("D.meetings.length+' meetings · '+s.races.length+' races · '+s.n+' runners scored · '+esc(D.engine.operational)+'</div>",
    "D.meetings.length+' meetings · '+s.races.length+' races · '+s.n+' runners · '+s.rated.length+' races rated by '+esc(D.engine.operational)+(s.fo?' · '+s.fo+' shown as fields only':'')+'</div>")
rep("+snapLine()+'</div></div>'+", "+snapLine()+'</div></div>'+mktBox()+")
rep("shown in Meetings.</p></section>'+", "shown in Meetings.</p></section>'+coverage()+")
rep("No market prices are used, and a high chance is not a statement that a bet is good value.",
    "Market prices are never used by the model; when a feed is connected they are shown beside it, labelled by source and time. A high chance is not a statement that a bet is good value.")
rep("<span class=\"faint\">Brisbane time</span></div></div>';", "<span><i class=\"sw\" style=\"background:var(--bg);border:1px dashed var(--line)\"></i>Not rated (fields only)</span><span class=\"faint\">Brisbane time</span></div></div>';")
rep("<div class=\"sub\">'+esc(m.conditions.going||'')+'</div></div><div class=\"track\">", "<div class=\"sub\">'+esc(m.rated?(m.conditions.going||m.state):m.state+' · fields only')+'</div></div><div class=\"track\">")

# ---------- Meetings ----------
rep("<span class=\"badge\"><span class=\"dot\"></span>'+esc(s.label)+' · fields '+esc(bris(s.fields_captured_utc))+' · scored '+esc(bris(s.v2_scored_utc))+'</span></div>'+",
    "<span class=\"badge\"><span class=\"dot\"></span>'+esc(s.label)+' · fields '+esc(bris(s.fields_captured_utc))+(s.v2_scored_utc?' · scored '+esc(bris(s.v2_scored_utc)):'')+'</span></div>'+(m.rated?'':'<div class=\"warn\" style=\"background:var(--panel2);border-color:var(--line);color:var(--mute)\"><b style=\"color:var(--ink)\">Fields only.</b> '+esc(m.reason)+'</div>')+")
rep("<div><span>Sectional history</span>'+(m.sectionals?'Queensland sectionals used':'Not published for NSW history')+'</div></div></section>'+",
    "<div><span>Sectional history</span>'+(!m.rated?'Not rated':m.sectionals?'Queensland sectionals used':'Not published for NSW/Vic history')+'</div></div>'+((m.notes||[]).length?'<p class=\"sm faint\" style=\"margin:10px 0 0\">'+m.notes.map(esc).join(' ')+'</p>':'')+'</section>'+")
rep("</small></button>').join('')+'</div>'+vRace(m,r);", "</small></button>').join('')+'</div>'+(m.rated?vRace(m,r):vFields(m,r));")

func('vRace', r"""function vRace(m,r){
 const cols=adv?11:6;
 return '<section class="panel"><div class="ph"><div><h2>'+esc(m.name)+' · Race '+r.no+' · '+r.distance_m+'m'+(m.conditions.going?' · '+esc(m.conditions.going):'')+'</h2><div class="mute sm" style="margin-top:4px">'+esc(r.name)+(r.class?' · '+esc(r.class):'')+' · <span class="num">'+esc(r.time)+' '+esc(r.tz)+'</span> · '+r.field+' runners</div></div>'+pill(r.label)+'</div>'+
 '<div style="display:flex;justify-content:flex-end;margin:-4px 0 8px"><button class="btn" data-adv="1" aria-pressed="'+adv+'">'+(adv?'Hide advanced view':'Advanced view')+'</button></div>'+
 (adv?'<div class="fig" id="rail" data-m="'+m.id+'" data-r="'+r.no+'"><svg></svg></div><p class="sm faint" style="margin:2px 0 12px">Each number is a runner placed on the relative-performance scale (kg-equivalent units, 0 = this field\'s average). It is a statistical scale, not the weight carried and not a beaten margin.</p>':'')+
 '<div class="scroll"><table><thead><tr><th>Rank</th><th>Horse</th><th class="r">Model win chance</th><th class="hidem">Selection strength</th><th>Market price</th><th class="hidem">Key reasons</th>'+(adv?'<th class="hidem">Bar</th><th class="r hidem">Wt</th><th class="r">Scale</th><th class="r hidem">Raw chance</th><th class="hidem">Evidence</th>':'')+'</tr></thead><tbody>'+
 r.runners.map(h=>'<tr class="rn'+(h.rank===1?' lead':'')+(open===m.id+'|'+r.no+'|'+h.n?' xp':'')+'" data-x="'+m.id+'|'+r.no+'|'+h.n+'"><td class="num">'+h.rank+'</td><td><span class="sc">'+h.n+'</span><b>'+esc(h.horse)+'</b><div class="sub">'+esc(h.jockey||'jockey tba')+' · '+esc(h.trainer||'')+'</div></td><td class="r num"><b>'+pc(h.cal)+'</b><div class="sub">'+h.cal_lo.toFixed(0)+'–'+h.cal_hi.toFixed(0)+'%</div></td><td class="hidem">'+(h.rank===1||h.class==='Insufficient evidence'?pill(h.class):'<span class="sub">'+esc(h.class)+'</span>')+'</td><td class="sm">'+price(h.market)+'</td><td class="sm mute hidem">'+reasons(h)+'</td>'+
  (adv?'<td class="num hidem">'+(h.barrier??'–')+'</td><td class="r num hidem">'+(h.weight??'–')+(h.claim?'<span class="sub"> (a'+h.claim+')</span>':'')+'</td><td class="r num">'+kg(h.rating)+'</td><td class="r num hidem">'+pc(h.chance)+'</td><td class="hidem">'+evDots(h.evidence.score,h.evidence.max)+'</td>':'')+'</tr>'+(open===m.id+'|'+r.no+'|'+h.n?'<tr class="xp"><td colspan="'+cols+'">'+expand(m,r,h)+'</td></tr>':'')).join('')+'</tbody></table></div>'+
 (r.not_scored.length?'<p class="sm mute" style="margin:12px 0 0"><b>Not scored:</b> '+r.not_scored.map(x=>esc(x.n+'. '+x.horse)+' ('+esc(x.status)+(x.when?', '+esc(x.when):'')+')').join(' · ')+'. Scratched runners are removed; emergencies are not counted until they gain a start.</p>':'')+'</section>';
}
function vFields(m,r){
 const act=r.runners.filter(x=>x.status==='runner');
 return '<section class="panel"><div class="ph"><div><h2>'+esc(m.name)+' · Race '+r.no+' · '+r.distance_m+'m</h2><div class="mute sm" style="margin-top:4px">'+esc(r.name)+(r.class?' · '+esc(r.class):'')+' · <span class="num">'+esc(r.time)+' '+esc(r.tz)+'</span> · '+act.length+' runners</div></div>'+pill('Not rated')+'</div>'+
 '<p class="sm mute" style="margin:0 0 10px">'+r.coverage.with_history+' of '+r.coverage.runners+' runners have any runs in our NSW, Vic or Qld history.</p>'+
 '<div class="scroll"><table><thead><tr><th>No.</th><th>Horse</th><th class="hidem">Bar</th><th class="hidem">Jockey · trainer</th><th class="r hidem">Wt</th><th>Market price</th><th class="hidem">In our history</th></tr></thead><tbody>'+
 r.runners.map(h=>'<tr class="'+(h.status==='scratched'?'strike':'')+'"><td class="num">'+h.n+'</td><td><b>'+esc(h.horse)+'</b>'+(h.status!=='runner'?' <span class="sub">('+esc(h.status)+')</span>':'')+'<div class="sub">'+esc(h.age_sex||'')+' · '+esc(h.jockey||'jockey tba')+'</div></td><td class="num hidem">'+h.barrier+'</td><td class="sm hidem">'+esc(h.jockey||'–')+'<div class="sub">'+esc(h.trainer||'')+'</div></td><td class="r num hidem">'+h.weight+(h.claim!=null?'<span class="sub"> (a'+h.claim+')</span>':'')+'</td><td class="sm">'+price(h.market)+'</td><td class="sm hidem">'+(h.history_runs?h.history_runs+' run'+(h.history_runs>1?'s':''):'<span class="faint">none</span>')+'</td></tr>').join('')+'</tbody></table></div></section>';
}""")

func('expand', r"""function expand(m,r,h){
 const neg=(h.against||[]);
 return '<div class="ex"><div class="mini"><div><span class="faint sm">Barrier · weight</span><div>'+(h.barrier??'–')+' · '+(h.weight??'–')+'kg</div></div><div><span class="faint sm">Selection strength</span><div>'+esc(h.class)+'</div></div><div><span class="faint sm">Helping most</span><div>'+reasons(h)+'</div></div><div><span class="faint sm">Holding it back</span><div>'+(neg.length?esc(neg.join(' · ')):'–')+'</div></div></div><button class="btn pri" style="margin-top:10px" data-h="'+esc(m.name)+'|'+r.no+'|'+h.n+'">Why this rating?</button></div>';
}""")

# ---------- Drawer: lead with chance, strength, price; scale moves to Advanced ----------
i = s.index("'<div class=\"trio\"><div><small>Final race rating</small>"); j = s.index("'<h3>Why this rating</h3>", i)
s = s[:i] + ("'<div class=\"trio\"><div><small>Model win chance</small><b class=\"num\">'+pc(h.cal)+'</b><small>calibrated · 80% band '+h.cal_lo.toFixed(1)+'–'+pc(h.cal_hi)+'</small></div>"
             "<div><small>Selection strength</small><b style=\"font-size:19px\">'+esc(h.class)+'</b><small>'+(h.rank===1?'top-rated in this race':ordinal(h.rank))+' · evidence '+h.evidence.score+' of '+h.evidence.max+'</small></div>"
             "<div><small>Market price</small><div style=\"margin:4px 0\">'+price(h.market)+'</div><small>display only; never used by the model</small></div></div>'+"
             "'<details><summary>Advanced: relative-performance scale</summary><div class=\"mini\" style=\"margin-top:8px\"><div><span class=\"faint sm\">Final race rating</span><div class=\"num\">'+kg(h.rating)+'</div></div><div><span class=\"faint sm\">Underlying ability vs this field</span><div class=\"num\">'+(a.rated_runs?kg(aRel):'Debut')+'</div></div><div><span class=\"faint sm\">Raw model chance</span><div class=\"num\">'+pc(h.chance)+'</div></div></div>"
             "<p class=\"sm faint\" style=\"margin:8px 0 0\">A statistical relative-performance scale in kg-equivalent units, so different factors share one currency. It is not the weight carried and not a beaten margin; 0 is this field\\'s average runner.'+(a.rated_runs?' Ability from '+a.rated_runs+' rated run'+(a.rated_runs>1?'s':'')+(a.sd_kg!=null?', uncertainty ± '+a.sd_kg.toFixed(1):'')+'.':' No rated runs yet: a starting estimate, not a measurement.')+'</p></details>'+\n ") + s[j:]
rep("They add up exactly to the final rating.</p>", "They are on the relative-performance scale (see Advanced above) and add up exactly to the final rating.</p>")

# ---------- Compare: rated meetings only ----------
i = s.index('\nfunction vCompare('); j = s.index('\nfunction vResults(')
s = s[:i] + s[i:j].replace('D.meetings.', 'RM().') + s[j:]

# ---------- Results & ROI ----------
rep("<section class=\"panel\" style=\"margin-top:16px\"><h2>Saved prediction fingerprints</h2>", "'+roiBox()+'<section class=\"panel\" style=\"margin-top:16px\"><h2>Saved prediction fingerprints</h2>")
i = s.index('\nfunction vResults('); j = s.index('\nfunction vMethod(')
s = s[:i] + s[i:j].replace("D.meetings.map(m=>{const s=", "RM().map(m=>{const s=") + s[j:]
s = s.replace('\nfunction vMethod(', r"""
function roiBox(){const R=D.roi;if(!R)return '';
 return '<section class="panel" style="margin-top:16px"><div class="ph"><h2>Selections and returns</h2><span class="badge">'+R.paper.selections+' selections · '+R.paper.priced+' priced · '+R.paper.settled+' settled</span></div>'+
 '<p class="sm mute" style="margin:4px 0 10px"><b>Paper</b> returns use the recorded quote; <b>realised</b> returns are only bets you placed and record yourself ('+R.realised.bets+' so far). They are never mixed. No authorised price feed is connected, so no paper return can be calculated yet; every selection is still recorded before racing so nothing is chosen after the fact.</p>'+
 '<div class="scroll"><table><thead><tr><th>Race</th><th>Selection</th><th class="r">Model win chance</th><th class="hidem">Strength</th><th>Quoted price</th><th>Result</th><th class="hidem">Settlement</th></tr></thead><tbody>'+
 R.selections.map(x=>'<tr data-go="'+x.meeting.toLowerCase()+'-r'+x.race+'" style="cursor:pointer"><td class="num">'+esc(x.meeting)+' R'+x.race+'<div class="sub">'+esc(x.time)+' '+esc(x.tz)+'</div></td><td><span class="sc">'+x.n+'</span>'+esc(x.horse)+'<div class="sub">'+esc(x.model_version)+' · rank '+x.rank+'</div></td><td class="r num">'+pc(x.win_chance)+'</td><td class="hidem">'+pill(x.classification)+'</td><td class="sm">'+(x.price?'$'+(+x.price).toFixed(2)+'<div class="sub">'+esc(x.price_source)+' · '+esc(bris(x.price_time_utc))+'</div>':'<span class="faint">none captured</span>')+'</td><td>'+(x.result?esc(x.result):'<span class="faint">–</span>')+'</td><td class="sm hidem">'+esc(x.settlement)+'</td></tr>').join('')+'</tbody></table></div>'+
 '<h3 style="margin-top:16px">Rules</h3><ul class="sm" style="margin:6px 0 0;padding-left:18px">'+R.rules.map(x=>'<li>'+esc(x)+'</li>').join('')+'</ul>'+
 '<p class="sm faint" style="margin:10px 0 0">When results and prices exist, returns are grouped by date, course, state, model version, selection strength and period, each with win rate, average price, return and sample size.</p></section>';}
function vMethod(""", 1)

# ---------- events, labels, footer ----------
rep("const t=e.target.closest('[data-v],[data-n],[data-m],[data-r],[data-x],[data-h],[data-go],#close,#scrim');if(!t)return;",
    "const t=e.target.closest('[data-v],[data-n],[data-m],[data-r],[data-x],[data-h],[data-go],[data-adv],#close,#scrim');if(!t)return;\n if(t.dataset.adv){adv=!adv;render();return}")
rep('<button class="tab" data-v="results">Results</button>', '<button class="tab" data-v="results">Results &amp; returns</button>')
rep("+'. Performance data only: no market prices are used.</p>", "+'. The model uses performance data only; prices are a separate, labelled display layer.</p>")
open(p, 'w').write(s); print('patched', len(s))
