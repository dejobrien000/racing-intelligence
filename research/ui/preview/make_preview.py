"""Batch 27 P7: PREVIEW of a simplified dashboard for Damo's review (the live ui/index.html is not changed; rollback = keep publishing it).
Same visual identity, same data contract. Changes: navigation (Today's racing / Races & horses / Performance / About / Research lab),
a plain-language Performance page, an About page, research and technical records moved to the Research lab, today's data notes folded
away, the assessment time on each race, a rating-history chart in each horse profile, and a preview banner. Old links (#compare,
#results, #method) still work. Usage (from research/): python3 ui/preview/make_preview.py -> ui/preview/index.html"""
import re
src = open('ui/index.html', encoding='utf-8').read()
def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:80], src.count(old)); src = src.replace(old, new)
# 1 navigation and a preview banner
rep('''   <button class="tab" data-v="today">Today</button>
   <button class="tab" data-v="meetings">Meetings</button>
   <button class="tab" data-v="compare">Engine Performance</button>
   <button class="tab" data-v="results">Results &amp; returns</button>
   <button class="tab" data-v="method">How it works</button>''',
'''   <button class="tab" data-v="today">Today's racing</button>
   <button class="tab" data-v="meetings">Races &amp; horses</button>
   <button class="tab" data-v="performance">Performance</button>
   <button class="tab" data-v="about">About</button>
   <button class="tab" data-v="lab">Research lab</button>''')
rep('<main class="wrap" id="view">', '<div class="wrap"><div class="info" style="margin:12px 0 0"><b>Preview layout for review.</b> Same engine, same saved assessments; only the layout and explanations differ. The live dashboard is unchanged.</div></div>\n<main class="wrap" id="view">')
# 2 routing (old addresses keep working)
rep("$('view').innerHTML=view==='today'?vToday():view==='meetings'?vMeetings():view==='compare'?vCompare():view==='results'?vResults():vMethod();",
    "$('view').innerHTML=view==='today'?vToday():view==='meetings'?vMeetings():view==='performance'?vPerf():view==='lab'?vLab():vAbout();")
rep("view=['today','meetings','compare','results','method'].includes(h)?h:'today';",
    "h=({compare:'performance',results:'performance',method:'about'})[h]||h;view=['today','meetings','performance','about','lab'].includes(h)?h:'today';")
# 3 Today: market and coverage notes folded into one closed panel at the end
rep("+'</div></div>'+mktBox()+\n '<div class=\"figs\">", "+'</div></div>'+\n '<div class=\"figs\">")
rep("qualified runners. Runners with no prior form, and races where most of the field has none, are left out of the board but shown in Meetings.</p></section>'+coverage()+",
    "qualified runners. Runners with no prior form, and races where most of the field has none, are left out of the board but shown in Races &amp; horses.</p></section>'+")
# the day-at-a-glance grid ends the Today view; append the notes after it
m = re.search(r"(function vToday\(\)\{.*?\n)(\})", src, re.S); body = m.group(1)
last = body.rstrip('\n'); assert last.endswith(';')
src = src.replace(m.group(0), last[:-1] + "+'<details class=\"panel\" style=\"margin-top:16px\"><summary><b>Today\\'s data notes</b> <span class=\"sm mute\">(prices, coverage)</span></summary>'+mktBox()+coverage()+'</details>';\n}", 1)
# 4 race header: when the assessment was made; a one-line reading guide under each race
rep("+r.field+' runners'+(r.confidence?", "+r.field+' runners'+(()=>{const s_=m.snapshots.find(x=>x.id===m.default_snapshot);return s_&&s_.v2_scored_utc?' · Assessed <span class=\"num\">'+esc(hm(s_.v2_scored_utc))+'</span> Brisbane':''})()+(r.confidence?")
rep("((r.emergencies_included||[]).length?'<p class=\"sm mute\" style=\"margin:12px 0 0\"><b>Emergencies included:</b>",
    "'<p class=\"sm faint\" style=\"margin:10px 0 0\">Model win chance is a probability, not a certainty: a 25% chance loses three times in four. The band is its 80% range. Prices are TAB\\'s, shown for information; they never enter the ratings. Tap a horse for its profile.</p>'+((r.emergencies_included||[]).length?'<p class=\"sm mute\" style=\"margin:12px 0 0\"><b>Emergencies included:</b>")
# 5 rating history chart in the horse profile (display only; uses the export's profile.common.recent)
rep(" return '<h3 style=\"margin-top:18px\">Performance profile</h3><div class=\"mini\" style=\"margin-top:8px\">'+",
    " return '<h3 style=\"margin-top:18px\">Performance profile</h3>'+spark((p.common&&p.common.recent)||p.recent||[])+'<div class=\"mini\" style=\"margin-top:8px\">'+")
NEW_JS = r"""
// ---- Batch 27 preview additions ----
function spark(rs){
 if(!rs||rs.length<2)return '';
 const W=320,H=90,P=8,vals=rs.flatMap(r=>[r[1],r[2]]).filter(v=>v!=null);if(!vals.length)return '';
 const lo=Math.min(...vals)-1,hi=Math.max(...vals)+1,x=i=>P+i*(W-2*P)/(rs.length-1),y=v=>H-P-(v-lo)/(hi-lo)*(H-2*P);
 const line=rs.map((r,i)=>r[2]==null?'':(i?'L':'M')+x(i).toFixed(1)+' '+y(r[2]).toFixed(1)).join(' ');
 const dots=rs.map((r,i)=>r[1]==null?'':'<circle cx="'+x(i).toFixed(1)+'" cy="'+y(r[1]).toFixed(1)+'" r="3.2" fill="var(--sky)"><title>'+esc(r[0])+': run '+kg(r[1],1)+' kg, rating going in '+kg(r[2],1)+' kg</title></circle>').join('');
 return '<div style="margin-top:8px"><svg viewBox="0 0 '+W+' '+H+'" style="width:100%;max-width:420px;height:auto" role="img" aria-label="Last runs: performance and rating"><path d="'+line+'" fill="none" stroke="var(--mute)" stroke-width="1.6"/>'+dots+'</svg><div class="sm faint">Last '+rs.length+' held runs, oldest left. Dots: each run\'s performance against its field. Grey line: the ability rating the horse carried into each run. Common national scale.</div></div>';
}
function frag_(html){const t=document.createElement('template');t.innerHTML=html;return t.content}
function grab_(f,h2){const s=[...f.querySelectorAll('section.panel')].find(x=>{const h=x.querySelector('h2');return h&&h.textContent.trim().startsWith(h2)});return s?s.outerHTML:''}
function vPerf(){
 const E=D.engine_performance;let fam='',byEng='',ck='';
 if(E&&!E.error){const f=frag_(vCompare());const g=f.querySelector('.grid2');fam=g?g.outerHTML:'';byEng=grab_(f,'Production record by engine');ck=grab_(f,'Prospective checkpoints')}
 const guide='<section class="panel"><h2>How to read this page</h2><ul class="sm" style="margin:8px 0 0;padding-left:18px;display:grid;gap:6px">'+
  '<li><b>Only forward-looking results count here.</b> Every assessment is saved before its race starts and never changed. Tests on past races are research, kept in the Research lab.</li>'+
  '<li><b>Top pick won</b>: how often the highest-rated runner won. <b>Winner in top 3</b>: how often the winner was one of the top three.</li>'+
  '<li><b>Fit</b>: how much chance the engine gave the actual winners, averaged over races; higher is better. It rewards honest chances, not just picking winners.</li>'+
  '<li><b>Versus the previous engine</b>: both scored the same races before the start, so the comparison is like for like.</li>'+
  '<li><b>Small samples mislead.</b> A few days of racing can swing either way. Early numbers are a direction, not proof, and a better rating does not mean proportionally more winners.</li></ul></section>';
 const roi=roiBox();
 return '<div class="head"><div><h1>Performance</h1><div class="mute" style="margin-top:6px">How the live engines have gone on races run since each was released.</div></div></div>'+guide+
  (fam?'<div style="margin-top:16px">'+fam+'</div>':'<div class="wait"><p>Figures appear once results are settled.</p></div>')+byEng+ck+
  (roi?'<details class="panel" style="margin-top:16px"><summary><b>Paper selections at TAB prices</b> <span class="sm mute">(evaluation only; prices never enter the ratings)</span></summary>'+roi+'</details>':'');
}
function vLab(){
 const E=D.engine_performance;let parts='';
 if(E&&!E.error){const f=frag_(vCompare());parts=[...f.children].filter(x=>!(x.classList.contains('head')||x.classList.contains('grid2')||/^(Production record by engine|Prospective checkpoints)/.test(((x.querySelector&&x.querySelector('h2'))||{}).textContent||''))).map(x=>x.outerHTML).join('')}
 const fp=grab_(frag_(vResults()),'Saved prediction fingerprints');
 return '<div class="head"><div><h1>Research lab</h1><div class="mute" style="margin-top:6px">Candidate engines under test, research on past races and technical records. Nothing here is a live assessment, and results on past races are not proof of future performance.</div></div></div>'+parts+
  (fp?'<details class="panel" style="margin-top:16px"><summary><b>Technical record: saved prediction fingerprints</b></summary>'+fp+'</details>':'');
}
function vAbout(){
 const sec=(t,b)=>'<section class="panel" style="margin-top:16px"><h2>'+t+'</h2>'+b+'</section>';
 const li=a=>'<ul class="sm" style="margin:8px 0 0;padding-left:18px;display:grid;gap:8px">'+a.map(x=>'<li>'+x+'</li>').join('')+'</ul>';
 return '<div class="head"><div><h1>About Horse Intel</h1><div class="mute" style="margin-top:6px">A private research project that rates Australian thoroughbreds from performance alone and checks itself honestly.</div></div></div>'+
 sec('In one paragraph','<p class="sm" style="margin:8px 0 0">Every racing morning Horse Intel rates each runner at Australian thoroughbred meetings from what horses have actually done on the track: margins, weights carried, times and the strength of the horses they met. It turns that into a chance for every runner, saves it before the race starts and later checks it against the result. It never uses betting prices, odds or market moves.</p>')+
 sec('What makes it different',li([
  '<b>Ability measured against the opposition.</b> Ratings are in kilograms, built from margins and weights against the actual horses met, so a close second to good horses can rate above a win in a weak field.',
  '<b>Each horse\'s own development.</b> Ratings move after every run, faster for lightly raced horses, and each profile shows the latest run, the typical level, the level it can repeat and its best.',
  '<b>Weights learned from evidence.</b> Form, time figures, jockey and trainer records, age and sex, course, going and distance records and weight are combined with weights learned from thousands of past races. A factor is only used if it improved forecasts on races it was not fitted on.',
  '<b>Jurisdiction-specific.</b> One national engine covers NSW, Victoria, the ACT, South Australia, Western Australia and Tasmania; Queensland has its own engine that also uses official sectionals and race-shape data.',
  '<b>Research kept apart from the live engine.</b> Measured sectional speed, distance suitability, barriers and returns from long spells are researched separately and only adopted once they improve forecasts.',
  '<b>Independent of the market.</b> No prices, odds or market moves enter the ratings. TAB prices are shown for information only.',
  '<b>Judged forward, not just backward.</b> Each morning\'s assessments are saved before racing and settled afterwards. Candidate engines are scored alongside on the same races, out of sight, before any is adopted.']))+
 sec('Reading a horse',li([
  '<b>Demonstrated ability</b>: what the horse has actually shown, run by run, measured against its field.',
  '<b>Sustainable ability</b>: the level it can be expected to repeat. That is the rating, not its single best run; the profile also shows the second-best of its last six runs.',
  '<b>Expected performance today</b>: ability adjusted for today: distance, track and going, weight, jockey and trainer, and time since its last run.',
  '<b>Uncertainty</b>: how sure the rating is. Lightly raced horses, new distances or courses and maiden races carry wider ranges; first starters have no demonstrated ability at all, only an estimate from similar horses, their trainer and their age.',
  '<b>Model win chance</b>: a probability, not a prediction. A 25% chance loses three times in four, and the favourite of the model will often be beaten.']))+
 sec('What the research has shown',li([
  'Each released engine had to beat the previous one on the same past races before it went live, and each is then followed on new races.',
  'Past-race results are research evidence. Only races run after an engine was released, shown on the Performance page, count as independent evidence, and that record is still short.']))+
 sec('Current limitations',li([
  'Ratings use results up to the latest weekly history update, so a run in the last few days may not be in a horse\'s rating yet.',
  'Barrier and sectional history exist only for Queensland (and South Australian tracking research); rail positions are not used.',
  'Darwin and other Northern Territory meetings are shown as fields only.',
  'First starters and horses whose earlier races we do not hold are rated from population averages, trainer, jockey, age and sex, never from invented form.',
  'It is a research tool, not betting advice. Nothing here guarantees a result.']));
}
"""
# 8 Batch 28 item 4 (approved): research-labelled performance range in the EXPANDED horse profile only (data from batch28/b28_profile_ranges.py)
rep("""'</div><p class="sm faint" style="margin:6px 0 0">Each figure is one run measured against its field. '""",
    """'</div>'+(p.range_research?rangeBox(p.range_research):'')+'<p class="sm faint" style="margin:6px 0 0">Each figure is one run measured against its field. '""")
NEW_JS += r"""
function rangeBox(r){
 return '<div class="sm" style="margin:10px 0 0;padding:8px 10px;border:1px dashed rgba(127,140,160,.55);border-radius:8px"><span class="tag">Research</span> '+
  '<b>Expected run today, against this field:</b> '+kg(r.expected_kg,1)+' kg &nbsp; <b>80% range:</b> '+kg(r.lo_kg,1)+' to '+kg(r.hi_kg,1)+' kg'+
  (r.wide?' <span class="faint">(wider because: '+esc(r.wide)+')</span>':'')+
  '<div class="faint" style="margin-top:4px">Where this horse\'s run is likely to land 8 times in 10, in kg better (+) or worse (−) than the average runner in this race. '+
  'It is not a win chance: an 80% range is not an 80% chance of winning. On past races the range held about 78% of runs. Research display only; the engine does not use it.</div></div>';
}
"""
rep("function render(){", NEW_JS + "function render(){")
rep('<title>Racing Intelligence</title>', '<title>Horse Intel preview</title>')
open('ui/preview/index.html', 'w', encoding='utf-8').write(src); print('ui/preview/index.html', len(src))
