"""Everyday usability of the listings page: undo, quiet mode, saved filters with chips, "new since my last visit", keyboard shortcuts, a phone
layout (filters as a drawer, big tap targets) and a print view. report.py puts CSS and JS into the page (after the fun layer, so undo wraps its save)."""

TAB = '<a href="/#pipeline" id="tabPipe">🗂 Pipeline</a><a href="/#visits" id="tabVisits">📅 Visits</a>'
TABFIRST = '<a href="/#next" id="tabNext">▶ Next <span class="sub" id="nextCount"></span></a>'
HTML = '<div id="nextview"><h2>▶ What to do now <span class="sub" id="nextSum"></span></h2><div id="foundNote"></div><div id="nextList"></div></div><div id="pipeview"><h2>🗂 Pipeline <span class="sub" id="pipeSum"></span></h2><div id="pipeBoard"></div></div><div id="visitsview"><h2>📅 Viewings <span class="sub" id="visitsCount"></span></h2><div class="row" id="visitsBar"></div><div id="visitsList"></div></div>'

CSS = r"""
/* toast with an action */
#toast{display:flex;gap:10px;align-items:center}#toast.on{pointer-events:auto}#toast button{background:transparent;color:var(--bg);border:1px solid currentColor;border-radius:6px;padding:1px 10px;font-weight:700;cursor:pointer}
.hitnote{font-size:12.5px;margin-top:3px;color:var(--okfg);background:var(--ok);border-radius:6px;padding:3px 8px}.hitnote b{font-weight:700}
#gsearch{margin-left:8px;width:230px;padding:5px 10px;border-radius:14px;border:1px solid var(--line);background:var(--card);color:var(--fg);font-size:13px}
.why{font-size:12.5px;margin-top:2px;color:var(--mut)}.why b.ok{color:var(--goodfg)}.why b.no{color:var(--badfg)}.why .chk{color:var(--warnfg)}
#chips{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:6px 0}#chips .chip{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--acc);color:var(--acc);border-radius:14px;padding:2px 4px 2px 10px;font-size:12.5px;background:var(--card)}
#chips .chip button{border:0;background:none;color:inherit;cursor:pointer;font-size:14px;padding:0 6px;line-height:1}#chips .clear{font-size:12.5px}
.savedrow{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:8px 0}.savedrow select{min-width:170px}
.empty{border:1px dashed var(--line);border-radius:12px;padding:22px 16px;text-align:center;color:var(--mut);margin:12px 0}.empty .big{font-size:34px}.empty b{color:var(--fg);display:block;margin:4px 0 6px;font-size:15px}
.card.kfocus{outline:2px solid var(--acc);outline-offset:1px}
#quietBtn{font-size:13px;padding:3px 10px;margin-left:8px}body.quiet #quietBtn{border-color:var(--warnfg);color:var(--warnfg)}
body.quiet *,body.quiet *::before,body.quiet *::after{animation:none!important;transition:none!important}
body.quiet #sticker,body.quiet .confetti,body.quiet .floater,body.quiet .roller,body.quiet .vis,body.quiet .fk,body.quiet .hoverjoke,body.quiet #tdPill{display:none!important}
#kbhelp{position:fixed;inset:0;z-index:2100;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center}#kbhelp .box{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:14px;padding:16px 22px;max-width:340px}
#kbhelp kbd{border:1px solid var(--line);border-radius:5px;padding:0 6px;background:var(--bg);font-family:ui-monospace,Menlo,monospace}#kbhelp td{padding:3px 8px}
.applybar{display:none}
#nextview,#pipeview{display:none}body.nextv #nextview,body.pipev #pipeview{display:block}
body.nextv #allview,body.nextv #markedview,body.nextv #mapview,body.nextv #todayview,body.nextv #visitsview,body.pipev #allview,body.pipev #markedview,body.pipev #mapview,body.pipev #todayview,body.pipev #visitsview{display:none}
body.nextv #nextview~*, body.pipev #pipeview~*{}
.nsec{margin:16px 0 4px;font-weight:700;font-size:15px}.nsec .sub{font-weight:400}.nrow{display:flex;gap:10px;flex-wrap:wrap;align-items:center;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:9px 12px;margin:6px 0}
.nrow .nmain{flex:1;min-width:230px}.nrow .nmain b{font-size:14.5px}.nrow .nbtn{display:flex;flex-wrap:wrap;gap:6px}.nrow .nbtn button,.nrow .nbtn a.btn{font-size:13px;padding:5px 11px}
.nrow.urgent{border-left:4px solid var(--warnfg)}.nrow.scam{border-left:4px solid var(--badfg)}.ncaught{text-align:center;padding:26px 10px;color:var(--mut)}.ncaught .big{font-size:40px}
#foundNote .foundbar{background:var(--good);color:var(--goodfg);border-radius:10px;padding:10px 14px;margin:8px 0}#foundNote button{margin-left:6px}
.board{display:flex;gap:10px;overflow-x:auto;padding-bottom:10px;scroll-snap-type:x proximity}.col{flex:1 0 230px;min-width:230px;max-width:340px;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:8px;scroll-snap-align:start}
.col.over{outline:2px dashed var(--acc)}.col h3{margin:2px 4px 8px;font-size:13.5px;display:flex;justify-content:space-between;align-items:center}.col h3 span{color:var(--mut);font-weight:400}
.pcard{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:7px 9px;margin:6px 0;cursor:grab;font-size:13px}.pcard:active{cursor:grabbing}.pcard .t{font-weight:600;display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.pcard .m{display:flex;justify-content:space-between;gap:6px;color:var(--mut);font-size:12px;margin-top:2px}.pcard .tags{margin-top:3px;font-size:12px}.pcard button{float:right;padding:0 8px;font-size:15px;line-height:20px}
.pcard.chosen{border:2px solid #2ea043}.foundbar{background:var(--good);color:var(--goodfg);border-radius:10px;padding:10px 14px;margin:4px 0}.foundbar button{margin-left:6px}.colhint{color:var(--mut);font-size:12px;padding:4px}
#visitsview{display:none}body.visitsv #visitsview{display:block}body.visitsv #allview,body.visitsv #markedview,body.visitsv #mapview,body.visitsv #todayview{display:none}
.hist{grid-column:2/4;font-size:12.5px;margin-top:4px}.hist summary{cursor:pointer;color:var(--mut)}.hist>div>div{padding:2px 0}
.sched{grid-column:2/4;font-size:13px;margin-top:4px;display:flex;flex-wrap:wrap;gap:8px;align-items:center}.sched .when{font-weight:700;color:var(--acc)}
.vday{margin:14px 0 4px;font-weight:700;border-bottom:1px solid var(--line);padding-bottom:3px}.vrow{display:flex;gap:12px;flex-wrap:wrap;align-items:center;border:1px solid var(--line);border-radius:10px;background:var(--card);padding:8px 12px;margin:6px 0}
.vrow .t{font:700 17px ui-monospace,Menlo,monospace;min-width:56px}.vrow .what{flex:1;min-width:200px}
@media (max-width:700px){
 body{padding-left:10px;padding-right:10px}
 .tabs{overflow-x:auto;white-space:nowrap;padding-bottom:0;-webkit-overflow-scrolling:touch}.tabs a{padding:9px 12px}#run{display:none}
 button,select,input[type=number],input[type=search],input[type=text],input[type=date],.btn{min-height:40px;font-size:15px}
 .card{grid-template-columns:44px minmax(0,1fr);padding:10px}.card>*{grid-column:1/-1!important;min-width:0}.card>.score{grid-column:1!important}.card>div:nth-child(2){grid-column:2/-1!important}
 .card>.price{text-align:left;display:flex;gap:10px;flex-wrap:wrap;align-items:baseline}.card textarea.note{width:100%;box-sizing:border-box}
 details.filters:not([open]){display:block}
 details.filters[open]{position:fixed;inset:0;z-index:1500;overflow:auto;margin:0;border-radius:0;padding:12px 14px 90px}
 details.filters[open] .applybar{display:flex;position:fixed;left:0;right:0;bottom:0;background:var(--card);border-top:1px solid var(--line);padding:10px 14px;z-index:1501;gap:8px}
 details.filters .applybar button{flex:1}
 .fgrid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.fgrid>*{min-width:0}.fgrid input,.fgrid select{min-width:0;max-width:100%}fieldset{grid-column:1/-1}details.filters[open]{box-sizing:border-box;width:100vw}.savedrow button{flex:1 1 40%}.savedrow select{flex:1 1 100%}
 #tdCount{max-width:60vw;font-size:12px}#sticker{max-width:94vw}
}
@media print{
 body{background:#fff!important;color:#000!important}
 #top,#allview,#todayview,#mapview,#toast,#sticker,#tdPill,#tdCount,.vis,.fk,.confetti,#kbhelp,#health,#chips,.views,.leaflet-container{display:none!important}
 body.printing #markedview{display:block!important}#markedview .bar,#markedview .hint,#markedview button,#markedview textarea,.card select,.card .btn,.card .row2 a,.card details{display:none!important}
 .card{break-inside:avoid;border:1px solid #999!important;background:#fff!important;color:#000!important;box-shadow:none!important}.card a{color:#000!important}
}
"""

JS = r"""
// ================= everyday usability (ux.py) =================
let UNDOING=false;
function toastUndo(msg,undo){const t=q('toast');t.innerHTML='<span></span><button>Undo</button>';t.firstChild.textContent=msg;t.classList.add('on');
 const off=()=>{t.classList.remove('on');setTimeout(()=>{if(!t.classList.contains('on'))t.textContent=''},250)};const id=setTimeout(off,7000);
 t.querySelector('button').onclick=()=>{clearTimeout(id);off();undo()}}
const _saveFun=save;
save=async function(id,patch){const prev={...(S[id]||{})};const r=await _saveFun(id,patch);
 if(!UNDOING&&(('status' in patch&&patch.status!==(prev.status||'new'))||('marked' in patch&&!!patch.marked!==!!prev.marked))){
  const label='status' in patch?'Status: '+patch.status:patch.marked?'Marked':'Unmarked';
  toastUndo(label,async()=>{UNDOING=true;const p={};if('status' in patch)p.status=prev.status||'new';if('marked' in patch)p.marked=!!prev.marked;try{await _saveFun(id,p)}finally{UNDOING=false}render()})}
 return r};

// ---- search bar: a phone number, an email address, an address, or any word from the ad, your notes and your mail
const normPhone=s=>String(s).replace(/\D/g,'').replace(/^(00)?32/,'').replace(/^0+/,'');
let SEARCH={q:'',hits:{}},_sT=null,_sAsked='';
function qmatch(x){const qs=F.q.trim(),base=(x.addr+' '+x.title+' '+x.agency+' '+x.summary+' '+x.source+' '+x.flags.join(' ')+' '+(x.phone||'')+' '+x.id).toLowerCase();
 if(qs.toLowerCase().split(/\s+/).every(w=>base.includes(w)))return true;
 if(/^[+\d\s./()-]{6,}$/.test(qs)){const n=normPhone(qs),p=normPhone(x.phone||'');if(p&&n.length>=6&&(p.includes(n)||n.includes(p)))return true}
 return SEARCH.q===qs&&!!SEARCH.hits[x.id]}
function ensureSearch(){const qv=(F.q||'').trim();if(qv===_sAsked)return;_sAsked=qv;clearTimeout(_sT);if(qv.length<3){SEARCH={q:'',hits:{}};return}
 _sT=setTimeout(async()=>{try{const r=await fetch('/api/search?q='+encodeURIComponent(qv));if(!r.ok)return;const hits=await r.json();if((F.q||'').trim()!==qv)return;SEARCH={q:qv,hits};render()}catch(e){}},300)}
const hitHtml=x=>{if(!F.q||SEARCH.q!==F.q.trim())return '';const h=(SEARCH.hits[x.id]||[]).find(k=>k.where!=='ad'&&k.text)||(SEARCH.hits[x.id]||[])[0];if(!h||!h.text)return '';return `<div class="hitnote">🔎 found in <b>${esc(h.where)}</b>: “${esc(h.text)}”</div>`};
(function(){const r=q('run');if(r&&!q('gsearch')){const i=document.createElement('input');i.id='gsearch';i.type='search';i.placeholder='🔎 phone, email, address, word…';i.title='Finds a flat by its phone number, email address, street, a word from the ad, your notes or your mail. Press Enter to jump to the results.';r.insertAdjacentElement('afterend',i);
 i.addEventListener('input',()=>{q('f_q').value=i.value;if(view!=='all')location.hash='';changed()});i.addEventListener('keydown',e=>{if(e.key==='Enter'){const l=q('list');if(l)l.scrollIntoView()}})}})();
// ---- quiet mode: no sound, voice, animation, pop-ups or visitors at all
function applyQuiet(){const on=lsGet('quiet','0')==='1';document.body.classList.toggle('quiet',on);const b=q('quietBtn');if(b){b.textContent=on?'🔇 Quiet':'🔊 Fun';b.title=on?'Quiet mode is on: no sounds, voices, animations or pop-ups. Click to turn the fun back on.':'Click for quiet mode: stops all sounds, voices, animations and pop-ups.'}
 if(on){try{musicStop();speechSynthesis.cancel()}catch(e){}document.querySelectorAll('.vis,.fk,#sticker,.hoverjoke').forEach(e=>e.remove())}}
(function(){const r=q('run');if(r&&!q('quietBtn')){const b=document.createElement('button');b.id='quietBtn';r.insertAdjacentElement('afterend',b);b.onclick=()=>{lsSet('quiet',lsGet('quiet','0')==='1'?'0':'1');applyQuiet()}}applyQuiet()})();

// ---- why this listing is shown
const GOODF=['stay_ok','short_term','fridge','furnished','laundry_machine','domicile_ok','bills_incl'],BADF=/^(shared|no_domicile|students_only|long_only|no_couple|check_scam|wrong_location|far|not_flat|too_late)$/,CHKF=['ask_lease','maybe_shared','no_text','unread','couple_extra','utilities_excluded','deposit_high','late','check_registration'];
function whyHtml(x){const lab=f=>(label[f]||f.replace(/_/g,' ')),pos=GOODF.filter(f=>x.flags.includes(f)).slice(0,4).map(lab),bad=x.flags.filter(f=>BADF.test(f)).map(lab),chk=CHKF.filter(f=>x.flags.includes(f)).slice(0,2).map(lab);
 if(x.total>B)bad.unshift('over budget (€'+x.total+')');
 const m=x.minutes!=null?x.minutes+' min to work':'';
 if(x.good&&!bad.length)return `<div class="why"><b class="ok">✓ good:</b> within budget (€${x.total})${m?', '+m:''}${pos.length?', '+pos.join(', '):''}${chk.length?` <span class="chk">· check: ${chk.join(', ')}</span>`:''}</div>`;
 if(bad.length)return `<div class="why"><b class="no">✗ not good:</b> ${bad.slice(0,3).join(', ')}${pos.length?' <span>· but: '+pos.slice(0,2).join(', ')+'</span>':''}</div>`;
 return `<div class="why"><b>~ okay:</b> ${m||'details missing'}${pos.length?', '+pos.join(', '):''}</div>`}

// ---- saved filters, filter chips and "new since my last visit"
const SINCE=(()=>{let v=null;try{v=localStorage.getItem('lastVisit')}catch(e){}return v||new Date(Date.now()-864e5).toISOString()})();
const markVisit=()=>{try{localStorage.setItem('lastVisit',new Date().toISOString())}catch(e){}};
addEventListener('pagehide',markVisit);document.addEventListener('visibilitychange',()=>{if(document.hidden)markVisit()});
const sinceNew=x=>{const t=Date.parse(x.first_at||'')||Date.parse((x.first_seen||'')+'T00:00');return !!t&&t>Date.parse(SINCE)};
const FNAME={q:'search',pmin:'from €',pmax:'up to €',beds:'bedrooms',m2:'min m²',commute:'max min',score:'min score',value:'min value',eff:'real cost ≤ €',avail:'free by',upd:'updated ≤ days',status:'status',area:'area',src:'site',flags:'must have',good:'hide deal-breakers',gone:'hide possibly taken',rej:'hide rejected',since:'new since my last visit'};
function chipText(k){const v=F[k];if(k==='since')return 'new since my last visit';if(typeof DEF[k]==='boolean')return (v?'':'show ')+FNAME[k];return FNAME[k]+': '+(Array.isArray(v)?v.join(', '):v)}
function renderChips(){const el=q('chips');if(!el)return;const ks=Object.keys(DEF).filter(k=>!['sort','dir'].includes(k)&&JSON.stringify(F[k])!==JSON.stringify(DEF[k]));
 el.innerHTML=ks.length?ks.map(k=>`<span class="chip">${esc(chipText(k))}<button data-chip="${k}" title="remove this filter">✕</button></span>`).join('')+'<button class="clear" data-chip="*">Clear all</button>':''}
function savedList(){try{return JSON.parse(localStorage.getItem('savedFilters')||'{}')}catch(e){return {}}}
function renderSaved(){const s=q('savedF');if(!s)return;const l=savedList();s.innerHTML='<option value="">Saved filters…</option>'+Object.keys(l).map(n=>`<option>${esc(n)}</option>`).join('')}
(function(){const f=document.querySelector('details.filters');if(!f||q('savedF'))return;
 const row=document.createElement('div');row.className='savedrow';row.innerHTML='<select id="savedF"></select><button id="saveF">Save these filters…</button><button id="delF">Delete saved</button><button id="clearAll">Clear all</button>';
 f.querySelector('summary').insertAdjacentElement('afterend',row);
 const ap=document.createElement('div');ap.className='applybar';ap.innerHTML='<button class="primary" id="applyF">Show results</button><button id="clearAll2">Clear all</button>';f.appendChild(ap);
 const ch=document.createElement('div');ch.id='chips';q('count').insertAdjacentElement('beforebegin',ch);renderSaved()})();
document.addEventListener('click',e=>{const t=e.target;
 if(t.id==='saveF'){const n=prompt('Name for these filters (for example "Evere under €1,000 with fridge"):','');if(n&&n.trim()){const l=savedList();l[n.trim().slice(0,60)]=F;try{localStorage.setItem('savedFilters',JSON.stringify(l))}catch(x){}renderSaved();q('savedF').value=n.trim().slice(0,60);toast('Saved')}return}
 if(t.id==='delF'){const n=q('savedF').value;if(!n)return;const l=savedList();delete l[n];try{localStorage.setItem('savedFilters',JSON.stringify(l))}catch(x){}renderSaved();toast('Deleted');return}
 if(t.id==='clearAll'||t.id==='clearAll2'||t.dataset.chip==='*'){F={...DEF};syncUI();changed();return}
 if(t.dataset.chip){F[t.dataset.chip]=DEF[t.dataset.chip];syncUI();changed();return}
 if(t.id==='applyF'){document.querySelector('details.filters').open=false;window.scrollTo(0,0);return}
 if(t.dataset.f==='since'){F={...DEF,since:true,good:false,gone:false};syncUI();changed();q('list').scrollIntoView();return}
 if(t.dataset.print){document.body.classList.add('printing');setTimeout(()=>{print();setTimeout(()=>document.body.classList.remove('printing'),500)},50);return}});
document.addEventListener('change',e=>{if(e.target.id==='savedF'&&e.target.value){F={...DEF,...savedList()[e.target.value]};syncUI();changed()}});
const _render=render;render=function(){_render();renderChips();const n=D.filter(sinceNew).length,b=q('banner');if(b&&!b.querySelector('[data-f=since]'))b.insertAdjacentHTML('beforeend',`<span class="pill" data-f="since" title="Listings first found after your last visit to this page (${esc(SINCE.slice(0,16).replace('T',' '))})">${n} new since my last visit</span>`)};

// ---- keyboard: j/k move, m mark, o open the ad, c copy the message, / search, ? help, q quiet
let KI=-1;
function kcards(){return [...document.querySelectorAll('#allview .card,#markedview .card')].filter(c=>c.offsetParent)}
function kgo(d){const l=kcards();if(!l.length)return;l.forEach(c=>c.classList.remove('kfocus'));KI=Math.max(0,Math.min(l.length-1,KI+d));l[KI].classList.add('kfocus');l[KI].scrollIntoView({block:'center',behavior:'smooth'})}
document.addEventListener('keydown',e=>{const a=document.activeElement;if(a&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName)||e.ctrlKey||e.metaKey||e.altKey)return;
 const k=e.key,l=kcards(),c=l[KI];
 if(k==='j')kgo(1);else if(k==='k')kgo(-1);
 else if(k==='m'&&c){const b=c.querySelector('[data-mark]');if(b)b.click()}
 else if(k==='o'&&c){const a1=c.querySelector('div > a[target=_blank]');if(a1)window.open(a1.href,'_blank','noopener')}
 else if(k==='c'&&c){const b=c.querySelector('button[data-id][data-l]');if(b)b.click()}
 else if(k==='/'){e.preventDefault();const s=q('f_q');if(s)s.focus()}
 else if(k==='q'){lsSet('quiet',lsGet('quiet','0')==='1'?'0':'1');applyQuiet()}
 else if(k==='?'){const o=document.getElementById('kbhelp');if(o){o.remove();return}const d=document.createElement('div');d.id='kbhelp';d.innerHTML='<div class="box"><b>Keyboard shortcuts</b><table><tr><td><kbd>j</kbd> <kbd>k</kbd></td><td>next / previous flat</td></tr><tr><td><kbd>m</kbd></td><td>mark or unmark</td></tr><tr><td><kbd>o</kbd></td><td>open the original ad</td></tr><tr><td><kbd>c</kbd></td><td>copy the message</td></tr><tr><td><kbd>/</kbd></td><td>search</td></tr><tr><td><kbd>q</kbd></td><td>quiet mode</td></tr><tr><td><kbd>?</kbd></td><td>this help</td></tr></table></div>';d.onclick=()=>d.remove();document.body.appendChild(d)}});
addEventListener('keydown',e=>{if(e.key==='Escape'){const o=document.getElementById('kbhelp');if(o)o.remove()}});

// ---- contact log (what you did, when) and viewings with a calendar export
const nowL=()=>{const d=new Date();return new Date(d-d.getTimezoneOffset()*6e4).toISOString().slice(0,16)};
let _rq=null;const rq=()=>{clearTimeout(_rq);_rq=setTimeout(render,250)};
function logAct(id,k,d){const e=S[id]=S[id]||{status:'new',note:''};(e.log=e.log||[]).push({t:nowL(),k,d,by:(typeof FUN!=='undefined'&&FUN.me)||''});e.log=e.log.slice(-60);
 if(server){fetch('/api/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,log:{k,d}})}).catch(()=>{})}else{try{localStorage.setItem('status',JSON.stringify(S))}catch(x){}}rq()}
const KICON={message:'✉',gmail:'✉',wa:'💬',call:'☎',status:'●',reply:'↩',visit:'📅',follow:'🔁'};
const HOPEN=new Set();document.addEventListener('toggle',e=>{const d=e.target;if(d.classList&&d.classList.contains('hist')){if(d.open)HOPEN.add(d.dataset.h);else HOPEN.delete(d.dataset.h)}},true);
const histHtml=x=>{const l=(S[x.id]||{}).log||[];if(!l.length)return '';return `<details class="hist" data-h="${x.id}"${HOPEN.has(x.id)?' open':''}><summary>🕘 history (${l.length}) · last: ${esc(l[l.length-1].d)}</summary><div>${l.slice().reverse().map(e=>`<div><span class="sub">${esc(String(e.t).replace('T',' '))}</span> ${KICON[e.k]||'•'} ${esc(e.d)}${e.by?` <span class="sub">(${esc(e.by)})</span>`:''}</div>`).join('')}</div></details>`};
const vfmt=t=>{const d=new Date(t);return d.toLocaleString([], {weekday:'short',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'})};
const schedHtml=x=>{const s=S[x.id]||{};if(s.visit_at)return `<div class="sched">📅 <span class="when">viewing ${esc(vfmt(s.visit_at))}</span>${s.visit_note?`<span class="sub">${esc(s.visit_note)}</span>`:''} <button data-visit="${x.id}">change</button><a class="btn" href="${gcal(x,s)}" target="_blank" rel="noopener">add to Google Calendar</a></div>`;
 return `<div class="sched"><button data-visit="${x.id}" title="Pick the date and time of the viewing. It shows on the Visits tab and can go to your calendar.">📅 schedule a viewing</button></div>`};
const p2=n=>String(n).padStart(2,'0'),icsT=t=>t.replace(/[-:]/g,'')+'00',endOf=t=>{const d=new Date(new Date(t).getTime()+45*6e4);return d.getFullYear()+p2(d.getMonth()+1)+p2(d.getDate())+'T'+p2(d.getHours())+p2(d.getMinutes())+'00'};
const gcal=(x,s)=>'https://calendar.google.com/calendar/render?action=TEMPLATE&text='+encodeURIComponent('Viewing: '+(x.addr||x.title))+'&dates='+icsT(s.visit_at)+'/'+endOf(s.visit_at)+'&location='+encodeURIComponent(x.addr||'')+'&details='+encodeURIComponent([x.url,x.phone?'Phone: '+x.phone:'',x.agency?'Agency: '+x.agency:'',s.visit_note||''].filter(Boolean).join('\n'));
const icsEsc=s=>String(s||'').replace(/\\/g,'\\\\').replace(/;/g,'\\;').replace(/,/g,'\\,').replace(/\n/g,'\\n');
function makeIcs(list){const L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//flat finder//EN','CALSCALE:GREGORIAN'];list.forEach(([x,s])=>{L.push('BEGIN:VEVENT','UID:'+x.id+'-'+s.visit_at+'@flatfinder','DTSTAMP:'+new Date().toISOString().replace(/[-:]/g,'').slice(0,15)+'Z','DTSTART:'+icsT(s.visit_at),'DTEND:'+endOf(s.visit_at),'SUMMARY:'+icsEsc('Viewing: '+(x.addr||x.title)),'LOCATION:'+icsEsc(x.addr||''),'DESCRIPTION:'+icsEsc([x.url,x.phone?'Phone: '+x.phone:'',x.agency?'Agency: '+x.agency:'',s.visit_note||''].filter(Boolean).join('\n')),'END:VEVENT')});L.push('END:VCALENDAR');
 return L.map(l=>{const o=[];while(l.length>73){o.push(l.slice(0,73));l=' '+l.slice(73)}o.push(l);return o.join('\r\n')}).join('\r\n')+'\r\n'}
function downloadIcs(list,name){const b=new Blob([makeIcs(list)],{type:'text/calendar'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download=name;document.body.appendChild(a);a.click();setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove()},500)}
const visitList=()=>D.map(x=>[x,S[x.id]||{}]).filter(([x,s])=>s.visit_at).sort((a,b)=>a[1].visit_at<b[1].visit_at?-1:1);
function renderVisits(){const l=visitList(),now=nowL(),up=l.filter(([x,s])=>s.visit_at>=now.slice(0,10)+'T00:00'),past=l.filter(([x,s])=>s.visit_at<now.slice(0,10)+'T00:00');
 q('visitsCount').textContent=up.length?'· '+up.length+' coming up':'';q('visitsBar').innerHTML=up.length?'<button class="primary" data-ics="up">⬇ Calendar file (.ics) for all</button><button data-print="1">🖨 Print</button><span class="sub">The .ics file opens in Apple Calendar, Google Calendar and Outlook.</span>':'';
 const day=t=>{const d=new Date(t.slice(0,10)+'T12:00'),n=Math.round((d-new Date(now.slice(0,10)+'T12:00'))/864e5);return (n===0?'Today · ':n===1?'Tomorrow · ':'')+d.toLocaleDateString([], {weekday:'long',day:'numeric',month:'long'})};
 let h='',last='';up.forEach(([x,s])=>{const d=s.visit_at.slice(0,10);if(d!==last){h+=`<div class="vday">${esc(day(s.visit_at))}</div>`;last=d}
  h+=`<div class="vrow"><span class="t">${esc(s.visit_at.slice(11))}</span><div class="what"><a href="${esc(x.url)}" target="_blank" rel="noopener"><b>${esc(x.addr||x.title)}</b></a><div class="sub">€${x.total} · ${esc(x.agency||'')}${s.visit_note?' · '+esc(s.visit_note):''}</div></div>${x.phone?`<a class="btn" href="tel:${esc(x.phone)}">☎ ${esc(x.phone)}</a>`:''}<a class="btn" href="${gcal(x,s)}" target="_blank" rel="noopener">Google Calendar</a><button data-visit="${x.id}">change</button></div>`});
 if(!up.length)h='<div class="empty"><div class="big">📅</div><b>No viewings planned yet</b>On a flat\'s card press "📅 schedule a viewing". It shows here, in date order, and you can put them all in your calendar.</div>';
 if(past.length)h+=`<details style="margin-top:14px"><summary class="sub">${past.length} earlier viewing${past.length>1?'s':''}</summary>${past.reverse().map(([x,s])=>`<div class="vrow"><span class="t sub">${esc(s.visit_at.replace('T',' '))}</span><div class="what">${esc(x.addr||x.title)}</div></div>`).join('')}</details>`;
 q('visitsList').innerHTML=h}
function visitDialog(id){const x=D.find(d=>d.id===id);if(!x||document.querySelector('.modalbk'))return;const s=S[id]||{};
 const el=document.createElement('div');el.className='modalbk';el.innerHTML=`<div class="box" style="text-align:left"><h3 style="margin-top:0">📅 Viewing</h3><div class="sub">${esc(x.addr||x.title)}</div><label class="sub" style="display:block;margin-top:10px">Date and time<input type="datetime-local" id="vdt" style="display:block;width:100%;margin-top:3px"></label><label class="sub" style="display:block;margin-top:8px">Note (who you meet, how to enter)<input type="text" id="vnote" maxlength="200" style="display:block;width:100%;margin-top:3px"></label><div class="frow"><button class="primary" id="vsave">Save</button><button id="vclear">Remove viewing</button><button id="vcancel">Cancel</button></div></div>`;
 document.body.appendChild(el);const dt=el.querySelector('#vdt');dt.value=s.visit_at||(new Date(Date.now()+864e5).toISOString().slice(0,10)+'T17:30');el.querySelector('#vnote').value=s.visit_note||'';
 const done=async v=>{const note=el.querySelector('#vnote').value;el.remove();await save(id,{visit_at:v,visit_note:note});logAct(id,'visit',v?'viewing planned for '+v.replace('T',' '):'viewing removed');render()};
 el.querySelector('#vsave').onclick=()=>{if(!dt.value){toast('Pick a date and time');return}done(dt.value)};el.querySelector('#vclear').onclick=()=>done('');el.querySelector('#vcancel').onclick=()=>el.remove()}
document.addEventListener('click',e=>{const v=e.target.closest('[data-visit]');if(v){visitDialog(v.dataset.visit);return}const i=e.target.closest('[data-ics]');if(i){const l=visitList().filter(([x,s])=>s.visit_at>=nowL().slice(0,10)+'T00:00');downloadIcs(l,'viewings.ics');return}
 const t=e.target.closest('a[href^="tel:"]');if(t){const c=t.closest('.card');const b=c&&c.querySelector('[data-st]');if(b)logAct(b.dataset.st,'call','tapped the call link')}});
const _saveUx=save;save=async function(id,patch){const prev=(S[id]||{}).status||'new';const r=await _saveUx(id,patch);if(patch.status&&patch.status!==prev)logAct(id,'status','status: '+prev+' → '+patch.status);return r};
(function(){const h=document.querySelector('#markedview h2');if(h&&!h.querySelector('[data-print]'))h.insertAdjacentHTML('beforeend',' <button data-print="1" style="font-size:12px">🖨 Print shortlist</button>')})();

// ---- Next: what to do now (replies to answer, viewings, follow-ups, best new flats)
const answeredAt=x=>{let t='';((S[x.id]||{}).log||[]).forEach(e=>{if(e.k==='answered'&&e.t>t)t=e.t});return t};
const OPENST=['new','contacted','replied','visit'];
function nextActions(){const found=FOUND&&FOUND.on,today=nowL().slice(0,10),tom=new Date(Date.now()+864e5).toISOString().slice(0,10),cut=new Date(Date.now()-2*36e5);const cutS=new Date(cut-cut.getTimezoneOffset()*6e4).toISOString().slice(0,16);
 const replies=D.filter(x=>{const m=MAIL[x.id];return m&&m.last&&OPENST.includes(st(x))&&m.last.date>(m.last_out||'')&&m.last.date>answeredAt(x)}).sort((a,b)=>MAIL[b.id].last.date<MAIL[a.id].last.date?-1:1);
 const viewings=D.filter(x=>{const v=(S[x.id]||{}).visit_at||'';return (v.slice(0,10)===today||v.slice(0,10)===tom)&&v>=cutS}).sort((a,b)=>S[a.id].visit_at<S[b.id].visit_at?-1:1);
 const follow=found?[]:D.filter(isDue).sort((a,b)=>lastAct(a)-lastAct(b));
 const n=Math.max(1,(FUN.users||[]).length),i=Math.max(0,(FUN.users||[]).indexOf(FUN.me)),h=s=>{let k=0;for(const c of s)k=(k*31+c.charCodeAt(0))>>>0;return k};
 const fresh=found?[]:D.filter(x=>x.good&&!x.gone&&x.verified&&st(x)==='new'&&h(x.id)%n===i).sort((a,b)=>(b.new-a.new)||(b.score-a.score)).slice(0,5);
 return{replies,viewings,follow,fresh,total:replies.length+viewings.length+follow.length+fresh.length}}
const nb=(act,id,label,cls)=>`<button data-na="${act}" data-id2="${id}"${cls?` class="${cls}"`:''}>${label}</button>`;
const gthread=l=>`https://mail.google.com/mail/u/0/#all/${encodeURIComponent(l.thread)}`;
function nrow(x,mainSub,btns,cls){return `<div class="nrow ${cls||''}"><div class="nmain"><a href="${esc(x.url)}" target="_blank" rel="noopener"><b>${esc(x.addr||x.title)}</b></a> <span class="sub">€${x.total} · ${x.minutes!=null?'~'+x.minutes+' min · ':''}${esc(x.agency||x.source)}</span><div class="sub">${mainSub}</div></div><div class="nbtn">${btns}</div></div>`}
function renderNext(){const a=nextActions(),el=q('nextList');let h='';
 const sec=(t,n,sub)=>`<div class="nsec">${t} <span class="sub">${n?'('+n+')':''} ${sub||''}</span></div>`;
 if(a.replies.length){h+=sec('✉ Replies waiting for your answer',a.replies.length);a.replies.forEach(x=>{const l=MAIL[x.id].last;h+=nrow(x,`from <b>${esc(nameOf(l.from))}</b>, ${agoT(l.date)}: “${esc(l.snippet)}”${l.scam?' <b style="color:var(--badfg)">⚠ spam</b>':''}`,
  `<a class="btn" href="${gthread(l)}" target="_blank" rel="noopener">open in Gmail</a>${nb('answered',x.id,'✓ I answered')}${nb('sched',x.id,'📅 viewing')}${nb('st:rejected',x.id,'not interested')}`,l.scam?'scam':'urgent')})}
 if(a.viewings.length){h+=sec('📅 Viewings today and tomorrow',a.viewings.length);a.viewings.forEach(x=>{const s=S[x.id],past=s.visit_at<nowL();h+=nrow(x,`<b>${esc(vfmt(s.visit_at))}</b>${s.visit_note?' · '+esc(s.visit_note):''}${past?' · <b>how did it go?</b>':''}`,
  `${x.phone?`<a class="btn" href="tel:${esc(x.phone)}">☎ call</a>`:''}<a class="btn" href="${gcal(x,s)}" target="_blank" rel="noopener">calendar</a>${past?nb('st:applied',x.id,'👍 I want it')+nb('st:rejected',x.id,'👎 no'):nb('sched',x.id,'change')}`,'urgent')})}
 if(a.follow.length){h+=sec('🔁 Follow-ups due',a.follow.length,'(no answer yet)');a.follow.forEach(x=>{h+=nrow(x,esc(dueText(x)),
  `<button data-fu="${x.id}" data-l="${x.lang}">copy follow-up (${x.lang.toUpperCase()})</button>${['fr','nl','en'].filter(l=>l!==x.lang).map(l=>`<button data-fu="${x.id}" data-l="${l}">${l.toUpperCase()}</button>`).join('')}${nb('st:replied',x.id,'they answered')}${nb('st:rejected',x.id,'give up')}`)})}
 if(a.fresh.length){h+=sec('🏠 Best new flats to contact',a.fresh.length,'(picked for you; your partner gets the other ones)');a.fresh.forEach(x=>{h+=nrow(x,`${whyHtml(x).replace(/<\/?div[^>]*>/g,'')}`,
  `<button data-id="${x.id}" data-l="${x.lang}" class="primary">copy message (${x.lang.toUpperCase()})</button><a class="btn" href="${gmailUrl(x)}" target="_blank" rel="noopener" data-gm="${x.id}">✉ Gmail</a>${x.phone?`<a class="btn" href="tel:${esc(x.phone)}">☎ ${esc(x.phone)}</a>`:''}${isMobile(x)?`<a class="btn wa" href="https://wa.me/${x.phone.replace(/\D/g,'')}" target="_blank" rel="noopener" data-wa="${x.id}">WhatsApp</a>`:''}${nb('st:rejected',x.id,'not for me')}`)})}
 if(!h)h=`<div class="ncaught"><div class="big">🎉</div><b>You are all caught up</b><div>No reply to answer, no viewing today, no follow-up due${FOUND&&FOUND.on?'':' and no new good flat waiting. A new search brings more.'}</div></div>`;
 el.innerHTML=h;const bits=[a.replies.length&&a.replies.length+' to answer',a.viewings.length&&a.viewings.length+' viewing'+(a.viewings.length>1?'s':''),a.follow.length&&a.follow.length+' follow-up'+(a.follow.length>1?'s':''),a.fresh.length&&a.fresh.length+' new'].filter(Boolean);q('nextSum').textContent=bits.length?'· '+bits.join(' · '):'';
 foundNote()}
function foundBar(){const x=D.find(d=>d.id===FOUND.lid);return `<div class="foundbar">🎉 <b>You found a flat${x?': '+esc(x.addr||x.title):''}.</b> Searching and reminders are paused and the other flats are archived (nothing is deleted). <button data-found-off="1">Resume searching</button> <button data-found-arch="1">${SHOWARCH?'Hide':'Show'} the archive</button></div>`}
function foundNote(){const el=q('foundNote');if(!el)return;el.innerHTML=(FOUND&&FOUND.on)?foundBar():''}
let SHOWARCH=false;
function countNext(){if(typeof D==='undefined')return;const a=nextActions(),n=a.replies.length+a.viewings.length+a.follow.length;const e=q('nextCount');if(e)e.textContent=n?'('+n+')':''}
// ---- Pipeline: every flat by where it stands; drag a card to another column or tap ⋯
const PCOLS=[['new','New (starred and best)'],['contacted','Contacted'],['replied','Replied'],['visit','Viewing'],['applied','Applied'],['rejected','Rejected']];
function renderPipe(){const cols=PCOLS.map(([k,name])=>{let l=D.filter(x=>st(x)===k&&!(x.gone&&k==='new'));const total=l.length;
  if(k==='new')l=l.filter(x=>(S[x.id]||{}).marked||x.good).sort((a,b)=>(((S[b.id]||{}).marked?1:0)-((S[a.id]||{}).marked?1:0))||b.score-a.score).slice(0,10);else l=l.sort((a,b)=>(lastAct(b)||0)-(lastAct(a)||0));
  if(k==='rejected')l=l.slice(0,30);
  return `<div class="col" data-col="${k}"><h3>${name} <span>${total}</span></h3>${l.map(pcard).join('')||'<div class="colhint">empty</div>'}${total>l.length?`<div class="colhint">+${total-l.length} more in <a href="/#" data-status-filter="${k}">Listings</a></div>`:''}</div>`}).join('');
 q('pipeBoard').innerHTML='<div class="board">'+cols+'</div>';q('pipeSum').textContent='· drag a card to move it, or tap ⋯'}
const agoMs=t=>{const m=Math.round((Date.now()-t)/6e4);return m<2?'just now':m<90?m+' min ago':m<2880?Math.round(m/60)+' h ago':Math.round(m/1440)+' days ago'};
function pcard(x){const s=S[x.id]||{},m=MAIL[x.id],t=lastAct(x);return `<div class="pcard${s.chosen?' chosen':''}" draggable="true" data-pc="${x.id}"><button data-pm="${x.id}" title="Move to another column">⋯</button><a class="t" href="${esc(x.url)}" target="_blank" rel="noopener" title="${esc(x.title)}">${esc(x.addr||x.title)}</a><div class="m"><span>€${x.total}</span><span>${t?agoMs(t):(x.added?'added '+ago(x.added):'')}</span></div><div class="tags">${s.chosen?'🏠 chosen ':''}${m&&m.last?'✉ reply ':''}${s.visit_at?'📅 '+esc(s.visit_at.slice(5,16).replace('T',' '))+' ':''}${isDue(x)?'<span style="color:var(--warnfg)">🔁 follow-up due</span>':''}</div></div>`}
function moveDialog(id){const x=D.find(d=>d.id===id);if(!x||document.querySelector('.modalbk'))return;const el=document.createElement('div');el.className='modalbk';el.innerHTML=`<div class="box" style="text-align:left"><h3 style="margin-top:0">Move</h3><div class="sub">${esc(x.addr||x.title)}</div><div class="frow" style="flex-direction:column;align-items:stretch">${PCOLS.map(([k,n])=>`<button data-mv="${k}"${st(x)===k?' disabled':''}>${n.replace(' (starred and best)','')}</button>`).join('')}<button id="mvx">Cancel</button></div></div>`;document.body.appendChild(el);
 el.onclick=async e=>{const b=e.target.closest('[data-mv]');if(b){el.remove();await save(id,{status:b.dataset.mv});render()}else if(e.target.id==='mvx'||e.target===el)el.remove()}}
// ---- you found a flat
function foundDialog(id){const x=D.find(d=>d.id===id);if(!x||document.querySelector('.modalbk'))return;const el=document.createElement('div');el.className='modalbk';el.innerHTML=`<div class="box" style="text-align:left"><div style="font-size:42px;text-align:center">🏠</div><h3 style="text-align:center">This is the one?</h3><div class="sub" style="text-align:center">${esc(x.addr||x.title)} · €${x.total}</div><p class="sub">Searching, follow-up reminders, the morning summary and the hourly reminders are paused. The other flats are archived, not deleted. You can resume any time.</p><div class="frow" style="justify-content:center"><button class="primary" id="fy">Yes, we found it 🎉</button><button id="fn">Not yet</button></div></div>`;document.body.appendChild(el);
 el.querySelector('#fn').onclick=()=>el.remove();el.querySelector('#fy').onclick=async()=>{el.remove();try{await postJson('/api/found',{on:true,lid:id});confetti&&confetti(60);toast('Congratulations! Rebuilding the page…');afterRun('Saving…')}catch(e){toast('⚠ '+e.message)}}}
document.addEventListener('click',async e=>{const t=e.target;
 const na=t.closest('[data-na]');if(na){const id=na.dataset.id2,a=na.dataset.na;if(a==='answered'){logAct(id,'answered','marked the reply as answered');render()}else if(a==='sched')visitDialog(id);else if(a.startsWith('st:')){await save(id,{status:a.slice(3)});render()}return}
 const pm=t.closest('[data-pm]');if(pm){moveDialog(pm.dataset.pm);return}
 const fo=t.closest('[data-found]');if(fo){foundDialog(fo.dataset.found);return}
 if(t.closest('[data-found-off]')){try{await postJson('/api/found',{on:false});toast('Resuming…');afterRun('Resuming…')}catch(err){toast('⚠ '+err.message)}return}
 if(t.closest('[data-found-arch]')){SHOWARCH=!SHOWARCH;render();return}
 const sf=t.closest('[data-status-filter]');if(sf){e.preventDefault();location.hash='';F={...DEF,status:sf.dataset.statusFilter==='new'?'todo':sf.dataset.statusFilter==='rejected'?'rejected':'active',good:false,gone:false,rej:false};syncUI();changed()}});
let DRAGID=null;document.addEventListener('dragstart',e=>{const c=e.target.closest&&e.target.closest('[data-pc]');if(c){DRAGID=c.dataset.pc;e.dataTransfer.effectAllowed='move';try{e.dataTransfer.setData('text/plain',DRAGID)}catch(x){}}});
document.addEventListener('dragover',e=>{const c=e.target.closest&&e.target.closest('[data-col]');if(c&&DRAGID){e.preventDefault();document.querySelectorAll('.col.over').forEach(x=>x.classList.remove('over'));c.classList.add('over')}});
document.addEventListener('dragend',()=>{DRAGID=null;document.querySelectorAll('.col.over').forEach(x=>x.classList.remove('over'))});
document.addEventListener('drop',async e=>{const c=e.target.closest&&e.target.closest('[data-col]');if(c&&DRAGID){e.preventDefault();const id=DRAGID;DRAGID=null;if(st(D.find(d=>d.id===id))!==c.dataset.col){await save(id,{status:c.dataset.col});render()}document.querySelectorAll('.col.over').forEach(x=>x.classList.remove('over'))}});
const _renderN=render;render=function(){_renderN();countNext();ensureSearch();const gs=q('gsearch');if(gs&&document.activeElement!==gs&&gs.value!==F.q)gs.value=F.q;if(FOUND&&FOUND.on){const bn=q('banner');if(bn)bn.innerHTML=foundBar();const sh=q('short'),fu=q('fu');if(sh)sh.innerHTML='';if(fu)fu.innerHTML=''}};
try{if(!location.hash&&sessionStorage.getItem('landed')!=='1'){sessionStorage.setItem('landed','1');setTimeout(()=>{if(!location.hash&&typeof nextActions==='function'){const a=nextActions();if(a.replies.length+a.viewings.length+a.follow.length>0)location.hash='#next'}},1500)}}catch(e){}
applyQuiet();
setTimeout(()=>{if(innerWidth<=700){const f=document.querySelector('details.filters');if(f)f.open=false;['howscore','stats'].forEach(i=>{const d=q(i);if(d&&lsGet(i+'MobileSeen','0')==='0')d.open=false})}},0);
"""
