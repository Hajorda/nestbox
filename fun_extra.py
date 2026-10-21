"""More surprises for the Today layer (fun.py appends this): landlord cameo, fake alert / chat / typing bubble / cookie banner / delivery notice /
review, sound gags and mood radio, idle sleep, hover jokes about prices, a fake give-up dialog and the leave-the-site blocker.
Everything is drawn or synthesised in the browser; nothing is loaded from other websites."""

CSS = r"""
.cameo{right:0;bottom:70px;width:140px;height:210px;pointer-events:none}
.cameo .room{position:absolute;right:0;top:0;width:128px;height:210px;background:#1a1208;border:5px solid #3d2a17;border-right:0}
.cameo .man{position:absolute;right:4px;bottom:4px;width:104px;opacity:0;transition:opacity .4s .5s}.cameo .man svg{width:104px;height:174px}
.cameo .door{position:absolute;right:0;top:0;width:128px;height:210px;background:#6b4a2b;border:5px solid #3d2a17;border-right:0;transform-origin:right center;transition:transform 1s ease;box-shadow:inset 0 0 0 4px #7b5834}
.cameo .door::after{content:'';position:absolute;left:12px;top:100px;width:10px;height:10px;border-radius:50%;background:#d4af37}
.cameo.open .door{transform:scaleX(.1)}.cameo.open .man{opacity:1}
.cameo .vbub{left:auto;right:0;transform:none;bottom:100%;max-width:min(230px,70vw)}
.fk{position:fixed;z-index:2000;background:#fff;color:#111;border-radius:14px;box-shadow:0 6px 24px rgba(0,0,0,.45);font:13px/1.4 system-ui;animation:adin .35s ease}
.fk.alert{top:46px;right:14px;width:min(320px,90vw);padding:12px 14px;display:flex;gap:10px;align-items:flex-start}.fk.alert .ic{font-size:28px;line-height:1}.fk.alert b{display:block;font-size:14px}
.fk button{border:1px solid #bbb;background:#f2f2f2;color:#111;border-radius:8px;padding:3px 12px;margin-top:6px;cursor:pointer}.fk button.primary{background:#1b64b8;border-color:#1b64b8;color:#fff}
.fk.chat{left:14px;bottom:70px;width:min(300px,86vw);padding:10px 12px}.fk.chat .who{font-weight:700;margin-bottom:4px}.fk.chat .m{background:#e9e9eb;border-radius:14px;padding:7px 11px;margin:4px 0;max-width:92%;width:fit-content}
.dots span{display:inline-block;width:7px;height:7px;border-radius:50%;background:#888;margin:0 2px;animation:dotb 1s infinite}.dots span:nth-child(2){animation-delay:.15s}.dots span:nth-child(3){animation-delay:.3s}
@keyframes dotb{0%,60%,100%{transform:translateY(0);opacity:.5}30%{transform:translateY(-5px);opacity:1}}
.fk.cookie{left:0;right:0;bottom:0;border-radius:0;padding:12px 16px;display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:center}.fk.cookie button{margin:0}
.modalbk{position:fixed;inset:0;z-index:2005;background:rgba(0,0,0,.68);display:flex;align-items:center;justify-content:center;padding:16px}
.modalbk .box{background:var(--card,#222);color:var(--fg,#eee);border:1px solid var(--line,#444);border-radius:16px;padding:20px 22px;max-width:440px;text-align:center;box-shadow:0 10px 40px rgba(0,0,0,.6)}
.modalbk .box img{max-width:100%;max-height:46vh;border-radius:10px;margin-bottom:8px}.modalbk .box h3{margin:6px 0}.modalbk .frow{display:flex;gap:10px;justify-content:center;flex-wrap:wrap;margin-top:10px}
.sleepbk{position:fixed;inset:0;z-index:2004;background:rgba(0,0,12,.78);display:flex;flex-direction:column;align-items:center;justify-content:center;color:#cfd6ff;text-align:center;cursor:pointer}
.sleepbk img{height:200px;width:auto;transform:rotate(-8deg);filter:grayscale(.3)}.sleepbk .zs{font-size:46px;animation:zfloat 2.4s ease-in-out infinite}.sleepbk .emo{font-size:110px}
@keyframes zfloat{0%{transform:translateY(10px);opacity:.3}50%{opacity:1}100%{transform:translateY(-26px);opacity:.2}}
.hoverjoke{position:fixed;z-index:2006;background:#b00020;color:#fff;padding:7px 11px;border-radius:10px;font:600 13px/1.35 system-ui;max-width:260px;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.4)}
"""

JS = r"""
// ================= more surprises (fun_extra.py) =================
const extraOn=()=>!quiet()&&lsGet('fsExtra','1')==='1',gagsOn=()=>!quiet()&&lsGet('fsGags','1')==='1',sleepOn=()=>!quiet()&&lsGet('fsSleep','1')==='1',hoverOn=()=>!quiet()&&lsGet('fsHover','1')==='1',leaveOn=()=>!quiet()&&lsGet('fsLeave','1')==='1';
const mk=(cls,html)=>{const el=document.createElement('div');el.className=cls;el.innerHTML=html;document.body.appendChild(el);return el};
const rmIn=(el,ms)=>setTimeout(()=>el.remove(),ms);
const timerRunning=()=>+lsGet('funTimerEnd',0)>Date.now();

// ---- more sounds
const _sfxBase=sfx;
sfx=function(kind){if(!soundOn())return;try{
 if(kind==='door'){burst(0,.16,.35,160);tone(90,0,.28,'sine',.3,38)}
 else if(kind==='coo'){tone(390,0,.2,'sine',.11,310);tone(340,.26,.3,'sine',.11,250);tone(390,.75,.2,'sine',.1,320);tone(330,1.0,.35,'sine',.1,230)}
 else if(kind==='violin'){[[440,0],[415,1],[392,2],[349,3.1]].forEach(([f,t])=>tone(f,t,1.1,'sawtooth',.045,f*.985))}
 else if(kind==='cash'){tone(1568,0,.3,'triangle',.12);tone(2093,.13,.5,'triangle',.1);burst(.04,.12,.14,6500);burst(.5,.1,.1,3000)}
 else if(kind==='trumpet'){[[392,0,.45],[392,.5,.45],[349,1,.5],[311,1.55,1.3]].forEach(([f,t,d])=>tone(f,t,d,'sawtooth',.07,f*.97))}
 else if(kind==='rave'){for(let i=0;i<8;i++){tone(130,i*.25,.14,'sine',.28,45);burst(i*.25+.125,.06,.08,7000)}[523,659,784,1047,784,659,784,1047].forEach((f,i)=>tone(f,i*.25,.2,'square',.05))}
 else _sfxBase(kind)}catch(e){}};

// ---- the landlord in a dressing gown opens a door at the edge of the page
const LANDLORD_SVG='<svg viewBox="0 0 120 200"><ellipse cx="60" cy="193" rx="36" ry="6" fill="rgba(0,0,0,.4)"/><path d="M30 190 L36 120 Q60 108 84 120 L90 190 Z" fill="#8b1e3f"/><path d="M52 112 L60 150 L68 112 Z" fill="#f1c9a5"/><rect x="34" y="148" width="52" height="8" fill="#f5e6c8"/><path d="M60 156 L57 190" stroke="#6d1631" stroke-width="2"/><ellipse cx="46" cy="194" rx="12" ry="5" fill="#5a3b22"/><ellipse cx="74" cy="194" rx="12" ry="5" fill="#5a3b22"/><path d="M86 125 L92 140" stroke="#8b1e3f" stroke-width="11" stroke-linecap="round"/><rect x="88" y="132" width="14" height="16" rx="2" fill="#fff"/><path d="M102 136 q8 4 0 10" stroke="#fff" stroke-width="3" fill="none"/><circle cx="60" cy="62" r="30" fill="#f1c9a5"/><path d="M31 64 Q28 44 41 37 M89 64 Q92 44 79 37" stroke="#aaa" stroke-width="7" fill="none" stroke-linecap="round"/><circle cx="49" cy="58" r="3.5" fill="#222"/><circle cx="71" cy="58" r="3.5" fill="#222"/><path d="M43 50 L55 54 M77 50 L65 54" stroke="#444" stroke-width="3"/><path d="M42 74 Q60 64 78 74 Q60 82 42 74Z" fill="#555"/><path d="M52 87 Q60 92 68 87" stroke="#7a3b2e" stroke-width="2" fill="none"/></svg>';
function visCameo(){const el=mk('vis cameo','<div class="room"></div><div class="man">'+LANDLORD_SVG+'<div class="vbub" hidden></div></div><div class="door"></div>');
 setTimeout(()=>{el.classList.add('open');sfx('door')},400);
 setTimeout(()=>{const b=el.querySelector('.vbub'),t=pick(['Sorry, already rented.','Sorry, already rented. Since this morning.','Already rented. Try the bridge.','No viewings. No refunds. No mercy.']);b.textContent=t;b.hidden=false;say(t,.55)},1700);
 setTimeout(()=>{el.querySelector('.vbub').hidden=true;el.classList.remove('open')},5300);setTimeout(()=>sfx('door'),6200);rmIn(el,7400)}

// ---- fake system things
function visAlert(){const hope=3+Math.floor(Math.random()*17),el=mk('fk alert',`<div class="ic">🪫</div><div><b>Battery low</b>Your hope is at ${hope}%.<br><button class="primary">Charge</button> <button class="x2">Ignore</button></div>`);sfx('pop');
 el.querySelector('.primary').onclick=()=>{el.remove();const t=line('call');sticker(FUN.me,t,'yes');say(t);toast('Charging… hope is at '+(hope+25)+'%')};el.querySelector('.x2').onclick=()=>el.remove();rmIn(el,16000)}
const CHAT=[['Mom','Did you find a flat yet?',['Your cousin lives in a van and he is thriving.','Your old room is free. Under the stairs.','I told the neighbours you are "between homes". They stopped waving.']],
 ['Dad','So... how is the flat hunt going?',['Remember: a bridge is just a very open-plan apartment.','Do not worry. A tent is cheaper than a lease.']],
 ['Hostel reception','Reminder: your bunk is paid until tomorrow.',['After that the pigeons have first dibs.','Late checkout is not an option. Neither is a bed.']],
 ['Pigeon_47','Hey roomie, I saved you the good spot under the bridge.',['Rent is breadcrumbs, payable weekly.','No pets. Except me.']]];
function visChat(){const [who,q,rep]=pick(CHAT),r=pick(rep),dots='<div class="m dots"><span></span><span></span><span></span></div>',el=mk('fk chat',`<div class="who">${esc(who)}</div><div class="body">${dots}</div>`),body=el.querySelector('.body');sfx('pop');
 setTimeout(()=>{body.innerHTML=`<div class="m">${esc(q)}</div>`+dots;sfx('pop');say(who+' says. '+q,who==='Mom'?1.5:.8)},2200);
 setTimeout(()=>{body.innerHTML=`<div class="m">${esc(q)}</div><div class="m">${esc(r)}</div>`;sfx('pop');say(r,who==='Mom'?1.5:.8)},6200);rmIn(el,16000)}
function visTyping(){const el=mk('fk chat',`<div class="who">Landlord Jean-Pierre</div><div class="m dots"><span></span><span></span><span></span></div><div style="font-size:11px;color:#666">typing…</div>`);sfx('pop');setTimeout(()=>{el.remove();sfx('violin')},12000)}
function visCookie(){if(document.querySelector('.fk.cookie'))return;const el=mk('fk cookie','<span>🍪 We use cookies to track how homeless you are.</span><button class="primary">Accept all</button><button class="primary">Accept all</button>');
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{el.remove();toast('Thank you. Tracking started. You are 94% homeless.');sfx('pop')});rmIn(el,22000)}
function visDelivery(){const el=mk('fk alert','<div class="ic">📦</div><div><b>Delivery update</b>Your flat has been delayed indefinitely.<br><span style="color:#666">New ETA: never. Last seen: a bus shelter.</span><br><button class="primary">Track package</button> <button class="x2">Dismiss</button></div>');sfx('pop');
 el.querySelector('.primary').onclick=()=>{el.remove();const t='Package located: in a cardboard box next to a pigeon. Signature required: yours.';sticker(FUN.me,t,'no');say(t)};el.querySelector('.x2').onclick=()=>el.remove();rmIn(el,16000)}
const REVIEWS=[['Bridge. No walls. Great acoustics.','Pigeon_47'],['Bus shelter. Fresh air all year. Nobody answers the door because there is none.','Jean-Pierre'],['Hostel bunk bed. Snoring included at no extra cost.','Tired Intern'],['Cardboard box. Waterproof for four minutes.','Wet Sam'],['Tent by the canal. Very open-plan.','Camper Kev'],['Parking space. Technically a studio.','Landlord of the Year']];
function visReview(){const [t,w]=pick(REVIEWS),n=1+Math.floor(Math.random()*2),el=mk('fk alert',`<div class="ic">⭐</div><div><b>${'★'.repeat(n)}${'☆'.repeat(5-n)}</b>${esc(t)}<br><span style="color:#666">— ${esc(w)}, verified resident</span></div>`);sfx('pop');rmIn(el,12000)}
function visGag(){const k=pick(['door','coo','violin','cash']);sfx(k);floater({door:'🚪',coo:'🐦',violin:'🎻',cash:'💰'}[k]);if(k==='cash')toast('💰 Rent is due!')}
function visGiveUp(){if(document.querySelector('.modalbk'))return;const el=mk('modalbk','<div class="box"><div style="font-size:44px">🤔</div><h3>Are you sure you want to give up?</h3><div class="sub">This cannot be undone. The pigeons are watching.</div><div class="frow"><button class="primary">No</button><button class="primary">Definitely no</button></div></div>');say('Are you sure you want to give up?');
 el.querySelectorAll('button').forEach(b=>b.onclick=()=>{el.remove();confetti(40);sfx('cheer');const t=line('call');say(t);sticker(FUN.me,t,'yes')})}

// ---- one place that decides what comes next (the five older visitors plus these)
const VISITORS=[[16,visWalk,'walk-in',0],[8,visPeek,'peek-a-boo',0],[6,visGhost,'ghost',0],[6,visNews,'news bar',0],[6,visAd,'fake ad',0],
 [7,visCameo,'landlord cameo',1],[5,visAlert,'battery alert',1],[7,visChat,'fake chat message',1],[4,visTyping,'landlord typing…',1],[3,visCookie,'cookie banner',1],[3,visDelivery,'delivery notice',1],[4,visReview,'fake review',1],[3,visGiveUp,'give-up dialog',1],[6,visGag,'sound gag',2]];
const visAllowed=()=>VISITORS.filter(v=>v[3]===0||(v[3]===1&&extraOn())||(v[3]===2&&gagsOn()));
function visRandom(){const l=visAllowed(),t=l.reduce((a,v)=>a+v[0],0);let r=Math.random()*t;for(const v of l){r-=v[0];if(r<=0){v[1]();return}}l[0][1]()}

// ---- mood radio: a sad trumpet after three no's in a row, a rave sting after a viewing
function moodRadio(o){if(!gagsOn())return;const mine=logsBy(FUN.me).slice(-3);
 if(o==='viewing')setTimeout(()=>{sfx('rave');toast('🎉 Rave mode. Enjoy it.')},900);
 else if(mine.length===3&&mine.every(e=>e.o&&OUT[e.o]&&OUT[e.o].t==='no'))setTimeout(()=>{sfx('trumpet');toast('🎺 Three no\'s in a row. The sad trumpet salutes you.')},1500)}

// ---- idle sleep: after 10 quiet minutes the page dims and falls asleep
let LASTACT=Date.now(),SLEEP=null,SNORE=null;
function wake(){if(!SLEEP)return;SLEEP.el.remove();clearInterval(SNORE);SLEEP=null;LASTACT=Date.now();const t='I am awake! I am awake! Call somebody.';sticker(FUN.me,t,'win',false,true);say(t,1.2)}
['mousemove','keydown','scroll','touchstart','click','wheel'].forEach(ev=>addEventListener(ev,()=>{if(SLEEP){if(Date.now()-SLEEP.t>900)wake()}else LASTACT=Date.now()},{passive:true}));
function sleepNow(){const f=faceUrl(FUN.me),el=mk('sleepbk',(f?`<img src="${esc(f)}" alt="">`:'<div class="emo">😴</div>')+'<div class="zs">💤 zzz…</div><div>Nobody has done anything for 10 minutes. Click to wake up.</div>');SLEEP={el,t:Date.now()};say('Yaaawn…',.5);
 SNORE=setInterval(()=>{if(soundOn()){burst(0,.7,.1,220);tone(70,0,.7,'sine',.06,55)}},3200)}
setInterval(()=>{if(sleepOn()&&!SLEEP&&!document.hidden&&FUN.me&&!timerRunning()&&Date.now()-LASTACT>6e5)sleepNow()},15000);

// ---- rude jokes when you hover a price
const HOVER_JOKES=[p=>p+' for THIS? My cardboard box is free and has a better view.',p=>p+' a month. For that money the pigeons would sign your lease.',p=>p+'? The bridge is cheaper. And has no landlord.',p=>'Wow, '+p+'. A hostel bunk is looking pretty good right now.',p=>p+' is a cry for help from the landlord.',p=>'For '+p+' you get walls. Probably. Maybe two.',p=>'Only '+p+'. The fridge costs extra.'];
let HOVT=0;document.addEventListener('mouseover',e=>{if(!hoverOn())return;const el=e.target.closest&&e.target.closest('.price');if(!el||Date.now()-HOVT<9000||Math.random()>.5)return;HOVT=Date.now();
 const p=(el.textContent.match(/€\s?[\d.,]+/)||['This price'])[0],r=el.getBoundingClientRect(),t=mk('hoverjoke',esc(pick(HOVER_JOKES)(p)));t.style.left=Math.max(8,Math.min(innerWidth-270,r.left-120))+'px';t.style.top=Math.min(innerHeight-70,r.bottom+6)+'px';rmIn(t,4200)});

// ---- leaving the site: exit intent overlay, a "really leave?" prompt and a guilt-trip tab title
let LEAVEAT=0;
function leaveOverlay(){if(document.querySelector('.modalbk')||Date.now()-LEAVEAT<9e5)return;LEAVEAT=Date.now();const l=todays().left,memes=memeKeys('no'),m=memes.length?FUN.assets[pick(memes)]:null,f=faceUrl(FUN.me);
 const line1=pick(['WHERE DO YOU THINK YOU ARE GOING?','Leaving already? The bridge is that way.','The pigeons saw you move towards the exit.','Nobody leaves until one landlord is called.']);
 const el=mk('modalbk',`<div class="box">${m?`<img src="${esc(m)}" alt="">`:f?`<img src="${esc(f)}" alt="" style="max-height:200px">`:'<div style="font-size:64px">🚪</div>'}<h3>${esc(line1)}</h3><div class="sub">${l>0?l+' contact'+(l===1?'':'s')+' left today. ':''}${esc(pick(PEPD.nudge[2]))}</div><div class="frow"><button class="primary" data-s="1">Fine, I will stay and call someone</button><button data-s="0">I am leaving anyway</button></div></div>`);
 sfx('trombone');say(line1,.7);el.querySelectorAll('button').forEach(b=>b.onclick=()=>{el.remove();if(b.dataset.s==='1'){confetti(30);sfx('cheer');const t=line('call');say(t);sticker(FUN.me,t,'yes')}else{say('Coward.',.6);toast('Your bunk bed is waiting.')}})}
document.documentElement.addEventListener('mouseleave',e=>{if(leaveOn()&&e.clientY<=0&&FUN.me&&(!FUN.ok||todays().left>0))leaveOverlay()});
let NOUNLOAD=false;document.addEventListener('click',e=>{if(e.target.closest&&e.target.closest('a[href^="/"]'))NOUNLOAD=true},true);
window.addEventListener('beforeunload',e=>{if(!leaveOn()||NOUNLOAD||!FUN.me||!FUN.ok||todays().left<=0||Date.now()-PAGEOPEN<120000)return;e.preventDefault();e.returnValue=''});
const PAGEOPEN=Date.now(),TITLE0=document.title;let TITLET=null;
document.addEventListener('visibilitychange',()=>{if(!leaveOn())return;
 if(document.hidden){const msgs=['🏚 Come back!','📞 Call a landlord!','🌉 The bridge misses you','👻 They said no… try again'];let i=0;TITLET=setInterval(()=>{document.title=msgs[i++%msgs.length]},1500);document.title=msgs[0]}
 else{clearInterval(TITLET);document.title=TITLE0;if(PAGEOPEN&&Date.now()-PAGEOPEN>60000&&FUN.me){const t=pick(['Oh, you came back. Disappointing that you left.','Welcome back, deserter. Call somebody.','The pigeons kept your seat warm.']);sticker(FUN.me,t,'no',true,true);say(t,.8)}}});

// ---- settings for these (checkboxes + a summon list)
const _renderToday2=renderToday;
renderToday=function(){_renderToday2();[['fsExtra',extraOn],['fsGags',gagsOn],['fsSleep',sleepOn],['fsHover',hoverOn],['fsLeave',leaveOn]].forEach(([id,f])=>{const e=q(id);if(e)e.checked=f()});
 const s=q('fsSummon');if(s&&!s.options.length)VISITORS.forEach((v,i)=>{const o=document.createElement('option');o.value=i;o.textContent=v[2];s.appendChild(o)})};
document.addEventListener('change',e=>{const m={fsExtra:'fsExtra',fsGags:'fsGags',fsSleep:'fsSleep',fsHover:'fsHover',fsLeave:'fsLeave'}[e.target.id];if(m)lsSet(m,e.target.checked?'1':'0')});
document.addEventListener('click',e=>{if(e.target.id==='fsSummonGo'){audio();VISITORS[+q('fsSummon').value][1]()}});
"""
