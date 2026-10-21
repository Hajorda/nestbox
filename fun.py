"""The motivation layer of the listings page (the "🎉 Today" tab): today's 3, one-tap call results, 10-minute timer, goal bar, streaks,
sounds, spoken pep lines, face stickers, meme feedback, loot, rejection bingo and the weekly league between the people sharing the search.

report.py puts CSS / HTML / JS into the page. The data (events, settings, pictures) lives on the shared copy; the page reaches it at /api/fun
(on the shared copy directly, locally through serve.py which forwards it with the owner's token).
Sounds are synthesised in the browser (Web Audio), voices use the browser's own speech: nothing is downloaded from anywhere.
"""

TAB = '<a href="/#today" id="tabToday">🎉 Today</a>'

CSS = r"""
#todayview{display:none}body.todayv #todayview{display:block}body.todayv #allview,body.todayv #markedview,body.todayv #mapview{display:none}
.fbox{border:1px solid var(--line);border-radius:12px;background:var(--card);padding:12px 14px;margin:10px 0}.fbox h3{margin:0 0 8px;font-size:15px}
.hero{display:flex;gap:14px;align-items:center;flex-wrap:wrap}.avatar{position:relative;width:64px;height:64px;flex:none}
.avatar .face{width:100%;height:100%;border-radius:50%;object-fit:cover;border:3px solid var(--acc);background:var(--bg);display:flex;align-items:center;justify-content:center;font-size:30px}
.avatar .hat{position:absolute;top:-16px;left:50%;transform:translateX(-50%);font-size:26px;line-height:1}
.pbar{height:14px;border-radius:7px;background:var(--line);overflow:hidden;margin:4px 0}.pbar>i{display:block;height:100%;background:linear-gradient(90deg,#2ea043,#f5b301);border-radius:7px;transition:width .4s}
.bigline{font-size:15px}.bigline b{font-size:20px}
.outs{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 2px;padding-top:6px;border-top:1px dashed var(--line)}.outs button{font-size:13px;padding:5px 11px}
.outs button.win{border-color:#2ea043;color:#2ea043;font-weight:600}.outs details{width:100%}.outs details button{margin:3px 4px 0 0}
.tcard{margin:8px 0}.doneBox{text-align:center;padding:18px 8px}.doneBox .big{font-size:42px}
.timer{display:flex;flex-wrap:wrap;gap:10px;align-items:center}.timer .clock{font:700 28px ui-monospace,Menlo,monospace}
.bingo{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;max-width:420px}.bingo div{border:1px solid var(--line);border-radius:8px;padding:10px 4px;text-align:center;font-size:12.5px;background:var(--bg);min-height:44px;display:flex;align-items:center;justify-content:center}
.bingo div.lit{background:#2ea043;color:#fff;border-color:#2ea043;font-weight:600}.bingo div.line{outline:3px solid #f5b301}
.lootgrid{display:flex;flex-wrap:wrap;gap:6px}.lootgrid span{border:1px solid var(--line);border-radius:14px;padding:3px 10px;font-size:12.5px;background:var(--bg)}.lootgrid span.none{opacity:.35}
.league .row{display:flex;align-items:center;gap:10px;margin:6px 0}.league .row .pbar{flex:1}
.fsettings label{display:block;font-size:12.5px;color:var(--mut);margin:8px 0 2px}.fsettings .frow{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.fsettings img.prev{width:46px;height:46px;border-radius:8px;object-fit:cover;border:1px solid var(--line)}
#sticker{position:fixed;right:14px;bottom:70px;z-index:2002;display:flex;align-items:flex-end;gap:8px;pointer-events:none;animation:stk 3.4s ease forwards;max-width:min(92vw,420px)}
#sticker .pic{width:84px;height:84px;border-radius:50%;object-fit:cover;border:4px solid var(--acc);background:var(--card);display:flex;align-items:center;justify-content:center;font-size:40px;position:relative;flex:none}
#sticker .pic .crown{position:absolute;top:-22px;left:50%;transform:translateX(-50%);font-size:30px}
#sticker .meme{width:84px;height:84px;border-radius:10px;object-fit:cover;background:var(--card);display:flex;align-items:center;justify-content:center;font-size:44px;border:2px solid var(--line);flex:none}
#sticker img.meme{width:160px;height:auto;max-height:210px;object-fit:contain}
#sticker .pic{object-position:50% 20%}#sticker{flex-wrap:wrap;justify-content:flex-end}
.avatar .face{object-position:50% 20%}
.memelist{display:flex;flex-wrap:wrap;gap:8px;margin:4px 0}.memelist .mi{position:relative}.memelist .mi img{width:70px;height:70px;object-fit:cover;border-radius:8px;border:1px solid var(--line)}.memelist .mi button{position:absolute;top:-6px;right:-6px;padding:0 6px;border-radius:50%;line-height:18px;font-size:12px}
#sticker .say{background:var(--fg);color:var(--bg);padding:9px 12px;border-radius:14px;font-size:14px;font-weight:600;line-height:1.35}
@keyframes stk{0%{transform:translateY(40px) scale(.6);opacity:0}10%{transform:none;opacity:1}85%{opacity:1}100%{transform:translateY(20px);opacity:0}}
.confetti{position:fixed;top:-30px;z-index:2003;font-size:22px;pointer-events:none;animation:fall 2.6s linear forwards}
#tdPill{position:fixed;left:12px;bottom:12px;z-index:2001;display:none;align-items:center;gap:8px;background:var(--acc);color:#fff;border-radius:22px;padding:7px 8px 7px 14px;box-shadow:0 2px 10px rgba(0,0,0,.35);font-weight:700}
#tdPill.on{display:flex}#tdPill a{color:#fff;text-decoration:none;font:700 17px ui-monospace,Menlo,monospace}#tdPill button{border-radius:14px;padding:2px 10px;font-size:12px;background:rgba(255,255,255,.2);color:#fff;border:1px solid rgba(255,255,255,.5)}
/* random visitors */
.vis{position:fixed;z-index:2000}.walker{bottom:0;left:-200px;display:flex;flex-direction:column;align-items:center;pointer-events:none}
.walker img{height:150px;width:auto;filter:drop-shadow(0 3px 4px rgba(0,0,0,.4))}.walker .emo{font-size:96px;line-height:1}
.walker.walking img,.walker.walking .emo{animation:bob .45s ease-in-out infinite}@keyframes bob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-10px) rotate(2deg)}}
.vbub{position:absolute;bottom:100%;left:50%;transform:translateX(-50%);width:max-content;max-width:min(260px,80vw);background:var(--fg);color:var(--bg);padding:9px 12px;border-radius:14px;font-size:14px;font-weight:600;line-height:1.35;margin-bottom:6px}
.peek{pointer-events:none;transition:transform .9s ease}.peek img{height:130px;width:auto}.peek .emo{font-size:84px}
.peek.bl{left:18px;bottom:0;transform:translateY(112%)}.peek.br{right:18px;bottom:0;transform:translateY(112%)}.peek.tl{left:18px;top:0;transform:translateY(-112%) rotate(180deg)}.peek.tr{right:18px;top:0;transform:translateY(-112%) rotate(180deg)}
.peek.bl.in,.peek.br.in{transform:none}.peek.tl.in,.peek.tr.in{transform:rotate(180deg)}.peek.out{transition-duration:2.6s}
.peek .vbub{bottom:auto;top:100%;margin:6px 0 0}.peek.tl .vbub,.peek.tr .vbub{transform:translateX(-50%) rotate(180deg);top:auto;bottom:100%;margin:0 0 6px}
.ghost{left:-130px;animation:gdrift 11s linear forwards;cursor:pointer;text-align:center;user-select:none}.ghost .gh{font-size:70px;animation:gwob 1.6s ease-in-out infinite;line-height:1}
.ghost .nosign{background:#fff;color:#d1242f;border:4px solid #d1242f;border-radius:8px;font:900 22px system-ui;padding:0 12px;margin-top:-6px;transform:rotate(-6deg)}
@keyframes gdrift{to{left:calc(100vw + 20px)}}@keyframes gwob{0%,100%{transform:translateY(-14px)}50%{transform:translateY(14px)}}
.newsbar{left:0;right:0;top:0;height:34px;background:#b00020;color:#fff;display:flex;align-items:center;overflow:hidden;font:700 14px system-ui;box-shadow:0 2px 8px rgba(0,0,0,.4);animation:ndown .5s ease}
@keyframes ndown{from{transform:translateY(-100%)}}.newsbar .nb{background:#fff;color:#b00020;padding:0 10px;height:100%;display:flex;align-items:center;z-index:2;letter-spacing:1px}
.newsbar .nm{flex:1;overflow:hidden;white-space:nowrap}.newsbar .nm span{display:inline-block;padding-left:100%;animation:marq 16s linear forwards}@keyframes marq{to{transform:translateX(-100%)}}
.fakead{width:min(280px,86vw);background:#fff;color:#111;border:1px solid #888;border-radius:8px;box-shadow:0 4px 18px rgba(0,0,0,.45);overflow:hidden;font:13px system-ui;animation:adin .35s ease}@keyframes adin{from{transform:scale(.6);opacity:0}}
.fakead .ah{background:#f5b301;color:#000;font-size:10px;font-weight:700;padding:2px 6px;display:flex;justify-content:space-between;align-items:center}.fakead .ah button{border:0;background:none;font-size:14px;cursor:pointer;padding:0 4px;color:#000}
.fakead .ab{padding:10px 12px;cursor:pointer}.fakead .ab b{display:block;font-size:15px;margin-bottom:3px}.fakead .ab span{color:#444}.fakead .ab u{display:block;margin-top:6px;color:#1b64b8;font-weight:700}
#tdCount{position:fixed;left:12px;bottom:12px;z-index:2001;max-width:min(300px,70vw);border-radius:12px;padding:7px 12px;color:#fff;font:600 13px/1.35 system-ui;cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.35);background:#2ea043}
#tdPill.on~#tdCount{bottom:62px}#tdCount b{font-size:17px}#tdCount.s1{background:#9a7b00}#tdCount.s2{background:#c46a00}#tdCount.s3{background:#c62828}#tdCount.s4{background:#7f0000;animation:cpulse 1.2s ease-in-out infinite}#tdCount.s5{background:#000;border:2px solid #f00;animation:cpulse .7s ease-in-out infinite}
#tdCount.min{padding:5px 10px}#tdCount.min .cl2{display:none}@keyframes cpulse{50%{transform:scale(1.07)}}
#tdHelp summary{cursor:pointer}.helpgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:4px 18px;margin-top:8px}.helpgrid p{margin:2px 0 10px;font-size:13px;line-height:1.45;color:var(--mut)}
#tdNotif{display:flex;gap:10px;align-items:center;flex-wrap:wrap;border-color:var(--acc)}#tdNotif[hidden]{display:none}
#sticker.shake{animation:stkshake 4.5s ease forwards}#sticker.shake .pic{border-color:#d1242f}
@keyframes stkshake{0%{transform:translateY(40px) scale(.6);opacity:0}6%{transform:none;opacity:1}10%,30%,50%,70%{transform:translateX(-7px) rotate(-3deg)}20%,40%,60%,80%{transform:translateX(7px) rotate(3deg)}90%{opacity:1}100%{opacity:0}}
.roller{position:fixed;bottom:8px;left:-60px;z-index:2001;font-size:42px;pointer-events:none;animation:roll 7s linear forwards}
@keyframes roll{to{left:110vw;transform:rotate(1440deg)}}
.floater{position:fixed;z-index:2001;font-size:54px;pointer-events:none;animation:floatup 4.5s ease-in forwards;opacity:.9}
@keyframes floatup{0%{transform:translateY(0) scale(.5);opacity:0}15%{opacity:.95}to{transform:translateY(-70vh) scale(1.4) rotate(12deg);opacity:0}}
body.shake{animation:bodyshake .5s}@keyframes bodyshake{0%,100%{transform:none}20%{transform:translateX(-8px)}40%{transform:translateX(8px)}60%{transform:translateX(-5px)}80%{transform:translateX(5px)}}
@keyframes fall{to{transform:translateY(105vh) rotate(540deg);opacity:.9}}
"""

HTML = r"""<div id="todayview"><h2>🎉 Today <span class="sub" id="tdWho"></span></h2>
<div id="tdOff" class="sub"></div>
<details class="fbox" id="tdHelp"><summary><b>ℹ How this tab works</b> <span class="sub">what every feature does (tap to open or close)</span></summary>
<div class="helpgrid">
<div><b>🎯 Today's 3</b><p>Your own 3 flats for today, the best-scoring ones you have not contacted yet. Your partner gets the other flats, so you never call the same landlord. After 3 contacts you get a "done for today" screen and can stop without guilt (or take 3 more).</p></div>
<div><b>☎ One-tap results</b><p>Under each flat, press what happened: no answer, they replied, viewing booked, no thanks, and more. It saves the status of the flat, adds points and plays a reaction. Changing a status or copying a message also counts as a contact.</p></div>
<div><b>⏱ Just try 10 minutes</b><p>Starts a 10-minute timer (with optional hold music). Starting is the hard part: after ten minutes you may stop. A fanfare plays at the end. Nagging is paused while it runs.</p></div>
<div><b>🔥 Streak and avatar</b><p>A day counts when you log at least one contact. Your face gets a hat as the streak grows: 🧢 1 day, 🦸 3 days, 👑 7 days, 🏆 14 days. Miss a whole day and it starts again.</p></div>
<div><b>🎯 Goal bar</b><p>Team progress toward the number of viewings booked (default 5; change it in the fun settings). Each flat counts once.</p></div>
<div><b>🏁 League</b><p>Weekly points for each of you: 1 per contact, 3 for a reply, 10 for a viewing. It resets on Monday. You decide the prize together (set in the fun settings).</p></div>
<div><b>🎰 Rejection bingo</b><p>Nine squares for typical results (no answer, voicemail, already rented, only students...). Every result you log lights one. Three in a row wins and plays a fanfare.</p></div>
<div><b>👻 The no counter</b><p>Celebrates rejections instead of hiding them. The "10 no's per yes" rule is made up, but it feels true.</p></div>
<div><b>🎁 Loot</b><p>Every logged contact drops a random silly item into your collection. 40 items to find, no practical use whatsoever.</p></div>
<div><b>📣 Cheer and 👉 Poke</b><p>Cheer sends the other person confetti and your face. Poke sends a dark-humor push (with a sad trombone and a shaking screen). They appear within about 20 seconds if their page is open.</p></div>
<div><b>🔊 Sound, voice and dark humor</b><p>Sounds are made in your browser: a cheer for a call, a sad trombone for a no, a fanfare for a viewing. The voice reads the line aloud in a random funny voice (browsers may stay silent until you have clicked once). Dark humor can be turned off for gentle lines only.</p></div>
<div><b>😴 Nagging</b><p>If you log nothing for a while (20 minutes by default) while this page is open, it nags you, a bit harsher each time you ignore it. Only between 08:00 and 22:00, and never during the timer.</p></div>
<div><b>🔔 Hourly notifications</b><p>If you allow notifications, your browser shows a reminder every hour from 09:00 to 18:00 to find a flat, with how many contacts you have left today. It stays quiet once you reached today's number. On the shared site the reminders come from the server, so they arrive even when the tab is closed (the browser itself must still be running; on iPhone add the site to the Home Screen first). On the local page they only work while it is open.</p></div>
<div><b>👷 Random visitors</b><p>On every page (not the control panel), one visitor appears every 5 minutes by default: your face walks in and says a dark-humor line out loud, a face peeks from a corner, a landlord ghost drifts by with a NO sign (tap it to banish it, nothing is logged), a fake breaking-news bar scrolls past, or a fake ad appears (tapping the ad tells your partner you are giving up, closing it with the X is free). Active from 08:00 to midnight by default and quiet while you type; the pace and the hours are in the fun settings. Switch off or change the pace in the fun settings, or summon one from there.</p></div>
<div><b>🏠 Countdown</b><p>The little box at the bottom left counts the days until the deadline to find a home (set the date in the fun settings; leave it empty to hide the box; the date is shared with your partner). It gets more dramatic every week, from calm green to a pulsing black box. Tap it to shrink it.</p></div>
<div><b>🎭 More surprises</b><p>The random visitors also include: a landlord in a dressing gown who opens a door at the edge of the page and says "Sorry, already rented", a fake "battery low, hope at 12%" alert (the Charge button gives you a pep line), a fake chat from Mom, Dad or a pigeon, a "Landlord Jean-Pierre is typing…" bubble that never delivers, a cookie banner with two "Accept all" buttons, a delivery notice for your flat that is delayed indefinitely, fake reviews, a "give up?" dialog with only "No" and "Definitely no", and sound gags (door slam, pigeon, sad violin, cash register). Each group has a switch in the fun settings, and there is a "summon now" list to try them.</p></div>
<div><b>📻 Mood radio, sleep and jokes</b><p>Three no's in a row get a sad trumpet; a booked viewing gets a rave sting. After 10 quiet minutes the page dims and falls asleep (any move wakes it). Hovering a price now and then gets a rude joke about it.</p></div>
<div><b>🚪 Leaving the site</b><p>When your mouse heads for the browser's top bar, a full-screen overlay with a meme and a voice tries to stop you (at most once every 15 minutes, and only while you still have contacts left today). The browser also asks "Leave site?" if you close the tab. The tab title guilt-trips you while you are away and the face scolds you when you are back. No website can truly lock you in, so this is a persuasion attempt, not a lock. Switch it off in the fun settings.</p></div>
<div><b>🖼 Faces and memes</b><p>Your face and the memes are shown in the pop-up stickers: a random "yes" meme for replies and viewings, a "no" meme for rejections and nags, a "meh" meme for ordinary calls. Add or remove them in the fun settings. They are stored on your own shared copy.</p></div>
</div></details>
<div class="fbox" id="tdNotif" hidden></div>
<div class="fbox" id="tdHero"></div>
<div class="fbox"><h3>⏱ Just try 10 minutes</h3><div id="tdTimer"></div></div>
<div id="tdCards"></div>
<div class="fbox league"><h3>🏁 League, this week</h3><div id="tdLeague"></div></div>
<div class="fbox"><h3>🎯 Rejection bingo <span class="sub">(every call result lights a square, a full row wins)</span></h3><div id="tdBingo"></div></div>
<div class="fbox"><h3>👻 The no counter</h3><div id="tdNos"></div></div>
<div class="fbox"><h3>🎁 Loot collection <span class="sub">(every logged call drops one)</span></h3><div id="tdLoot"></div></div>
<details class="fbox fsettings" id="tdSet"><summary><b>⚙ Fun settings</b> <span class="sub">sound, voice, goal, your face and memes</span></summary>
 <div class="frow" style="margin-top:8px"><label style="margin:0"><input type="checkbox" id="fsSound"> sound effects</label><label style="margin:0"><input type="checkbox" id="fsVoice"> funny voice</label><label style="margin:0"><input type="checkbox" id="fsMusic"> hold music during the timer</label><label style="margin:0"><input type="checkbox" id="fsDark"> dark humor</label><label style="margin:0"><input type="checkbox" id="fsNudge"> nag me when I do nothing</label><label style="margin:0">after <select id="fsNudgeMin"><option>5</option><option>10</option><option>20</option><option>30</option><option>45</option></select> min</label></div>
 <label>Browser notifications (hourly reminder while this site is open)</label>
 <div class="frow"><label style="margin:0"><input type="checkbox" id="fsNotif"> hourly reminders</label><label style="margin:0">from <input type="number" id="fsNotifFrom" min="0" max="23" style="width:60px"> to <input type="number" id="fsNotifTo" min="1" max="23" style="width:60px"> o'clock</label><button id="fsNotifAsk">Allow notifications</button><button id="fsNotifTest">Send a test</button> <span class="sub" id="fsNotifState"></span></div>
 <div class="sub" id="fsPushState" style="margin-top:4px"></div><div class="sub" id="fsPushLink"></div>
 <label>Random visitors (a person walks in, faces peek, ghosts, fake news and fake ads on every page)</label>
 <div class="frow"><label style="margin:0"><input type="checkbox" id="fsVis"> random visitors</label><label style="margin:0">one every <input type="number" id="fsVisMin" min="1" max="120" style="width:60px"> minutes</label><label style="margin:0">from <input type="number" id="fsVisFrom" min="0" max="23" style="width:60px"> to <input type="number" id="fsVisTo" min="1" max="24" style="width:60px"> o'clock</label>
 <select id="fsSummon"></select><button id="fsSummonGo">summon now</button></div>
 <div class="frow" style="margin-top:6px"><label style="margin:0"><input type="checkbox" id="fsExtra"> fake popups (chat, alerts, ads, cookie banner, landlord cameo...)</label><label style="margin:0"><input type="checkbox" id="fsGags"> sound gags and mood radio</label><label style="margin:0"><input type="checkbox" id="fsSleep"> fall asleep when idle</label><label style="margin:0"><input type="checkbox" id="fsHover"> rude price jokes</label><label style="margin:0"><input type="checkbox" id="fsLeave"> try to stop me from leaving</label></div>
 <label>Deadline to find a home (shared countdown; leave empty to hide it)</label><div class="frow"><input type="date" id="fsDeadline"></div>
 <label>Goal: viewings booked</label><div class="frow"><input type="number" id="fsGoal" min="1" max="99" style="width:80px"> <span class="sub">calls per person per day</span> <input type="number" id="fsDaily" min="1" max="20" style="width:80px"></div>
 <label>Prize for the weekly winner (you decide together)</label><input type="text" id="fsPrize" maxlength="120" style="width:100%;max-width:420px" placeholder="e.g. the loser buys the first coffee in the new flat">
 <div class="frow" style="margin-top:6px"><button id="fsSave" class="primary">Save goal and prize</button></div>
 <label>Your face (a photo of you; shown in the stickers, shrunk before upload)</label><div class="frow"><img class="prev" id="pvFace" alt="" hidden><input type="file" accept="image/*" id="upFace"></div>
 <label>Memes (one is picked at random). "Yes" memes show on replies and viewings, "no" memes on rejections and nags, "meh" ones on ordinary logged calls</label>
 <div class="memelist" id="memeList"></div>
 <div class="frow"><label style="margin:0">add yes meme <input type="file" accept="image/*" id="upMemeYes"></label><label style="margin:0">add no meme <input type="file" accept="image/*" id="upMemeNo"></label><label style="margin:0">add meh meme <input type="file" accept="image/*" id="upMemeMeh"></label></div>
 <div class="sub" style="margin-top:8px">Pictures are stored on your own shared copy behind the login. Nothing is loaded from other websites.</div>
</details></div>"""

JS = r"""
// ================= motivation layer (fun.py) =================
const FUN={ev:[],set:{goal:5,daily:3,prize:''},assets:{},me:'',users:[],ok:false};
const OUT={noanswer:{l:'No answer',s:'contacted',t:'no'},voicemail:{l:'Voicemail',s:'contacted',t:'meh'},callback:{l:'Call me back later',s:'contacted',t:'meh'},french:{l:'Only speaks French',s:'contacted',t:'meh'},
 replied:{l:'They replied',s:'replied',t:'yes'},viewing:{l:'Viewing booked',s:'visit',t:'win'},rented:{l:'Already rented',s:'rejected',t:'no'},students:{l:'Only students',s:'rejected',t:'no'},
 expensive:{l:'Too expensive',s:'rejected',t:'no'},nothanks:{l:'No thanks',s:'rejected',t:'no'}};
const BINGO=['noanswer','voicemail','callback','rented','students','french','expensive','replied','viewing'];
const STATUS_OUT={visit:'viewing',replied:'replied',rejected:'nothanks'};
const PEP={call:['Call logged. The landlord does not know what is coming.','Another one down. You are on fire.','Nice. Every call is a lottery ticket.','Look at you, calling people like a professional.','Logged! The fridge is getting closer.'],
 no:['A no is just a yes that took a wrong turn.','Rejection is the landlord\'s loss, not yours.','Every no is one step closer to a fridge.','Ghosted again? Respect, you tried.','That landlord will regret this. Probably.'],
 replied:['They answered! Quick, act natural.','A reply! Somebody is awake in Brussels.','Conversation unlocked. Be charming.'],
 win:['A viewing! Put the crown on.','Fanfare! Somebody wants to show you a flat!','You booked a viewing. Legend behavior.','The landlord fears you!'],
 start:['Ten minutes. That is less than one episode of anything.','Just start. The phone is not that scary.','Ten minutes and you can stop. Probably.'],
 done:['Ten minutes done! You may stop now. Or not. Hero.','Timer finished. You survived.'],
 cheer:['cheers you on!','believes in you!','says: you can do this!','sends you a virtual high five!']};
const LOOT=['🧊 a slightly used fridge','🥖 a warm baguette','🔑 the key to nothing','🧦 one lonely sock','📞 a phone that works','🇫🇷 one French word','🇳🇱 one Dutch word','🛋 half a sofa','🪴 a plant that survived','☕ a free coffee','🍫 Belgian chocolate','🍟 a cone of fries','🧇 a waffle','🍺 a cold Belgian beer','🐌 a very slow snail','🦆 a rubber duck','🧯 a fire extinguisher (tenant duty)','📦 an unopened box','🪟 a window with a view','🚿 a hot shower','🛏 a real mattress','🧹 a broom with ambition','🔌 a working socket','📶 fast wifi','🧺 a washing machine!','🪑 a wobbly chair','🕯 a candle for luck','🍀 a four-leaf clover','🦄 a landlord who answers','🎫 a tram ticket','🥐 a croissant','🛎 a doorbell that works','🧲 a fridge magnet','🪞 a slightly cracked mirror','📜 a lease with no hidden clauses','🌞 a sunny balcony','🐈 a landlord\'s cat','🥇 a tiny gold medal','🏰 a very small castle','🧃 a juice box'];
const PEPD={call:['Call logged. One step further from the cardboard box.','Good. The hostel bunk bed misses you already.','Another call. The pigeons at Gare du Nord are disappointed.','You called a stranger to avoid sleeping under a bridge. Growth.','Logged. Your future fridge sends its regards.'],
 no:['They said no. The bridge said "we have room".','Rejected. The tent at the Canal says hi.','No again? A hostel roommate is snoring somewhere in your honor.','That no is free. The cardboard box costs extra.','Ghosted. Like your dignity at the hostel breakfast.','Dead end. Luckily your childhood dreams died years ago.'],
 replied:['They replied! Hide the desperation, wear the charm.','A real human answered. Do not scare them with your housing situation.','They answered. For once the universe blinked first.'],
 win:['A viewing! The bridge will have to find another tenant.','Viewing booked. The cardboard industry mourns.','You may keep the crown. The street may not have you.','Fanfare! You are 1 viewing further from being a pigeon.'],
 start:['Ten minutes. A homeless person has all day, you do not.','Start the timer. The hostel curfew will not.','Ten minutes of calls or ten nights of snoring roommates. Your pick.'],
 done:['Ten minutes done. The streets will have to wait.','Timer over. You are still technically housed in a hostel. Congratulations.'],
 poke:['wants to know if you like sleeping in a bunk bed.','says: call someone before the hostel charges you again.','whispers: the bridge is cold this time of year.','asks: do you want to be homeless? Because this is how.','says: the phone will not call itself.'],
 nudge:[['Hello? Nobody has called anyone in a while.','The listings are not going to call themselves.','Just checking in. The flat will not rent itself.'],
  ['Do you want to be homeless? Because this is how you become homeless.','Every minute you scroll, a better flat gets rented to somebody braver.','The hostel bunk bed is not a lifestyle. Call somebody.'],
  ['The bridge is cold, but at least it has no landlord. Still, call one.','Your internship ends in April. Your couch surfing karma ended in October.','Pigeons found a better flat than you. Pick up the phone.'],
  ['This is an intervention. Call. One. Landlord.','I am a website and I am more motivated than you. Think about that.','Cardboard is cheap this season. Do you want to save money that way?','Final warning: the next step is the tent. Call, you coward.']]};
const gentleNudge=['Quick reminder: one call is enough to feel good.','No calls for a while. Want to try 10 minutes?','Your partner is waiting for good news.'];
const darkOn=()=>lsGet('fsDark','1')==='1',nudgeOn=()=>!quiet()&&lsGet('fsNudge','1')==='1',nudgeMin=()=>+lsGet('fsNudgeMin',20)||20;
function line(k){return darkOn()&&PEPD[k]&&Math.random()<.75?pick(PEPD[k]):pick(PEP[k])}
const pick=a=>a[Math.floor(Math.random()*a.length)];
(function(){try{if(localStorage.getItem('fsReset')!=='2'){['fsSound','fsVoice','fsMusic','fsDark','fsNudge','fsNotif','fsVis','fsExtra','fsGags','fsSleep','fsHover','fsLeave'].forEach(k=>localStorage.setItem(k,'1'));localStorage.setItem('fsVisMin','5');localStorage.setItem('fsVisFrom','8');localStorage.setItem('fsVisTo','24');localStorage.setItem('countMin','0');localStorage.setItem('fsReset','2')}}catch(e){}})();
const cap=s=>s?s[0].toUpperCase()+s.slice(1):s;
const lsGet=(k,d)=>{try{const v=localStorage.getItem(k);return v===null?d:v}catch(e){return d}};
const lsSet=(k,v)=>{try{localStorage.setItem(k,v)}catch(e){}};
const quiet=()=>lsGet('quiet','0')==='1';
const soundOn=()=>!quiet()&&lsGet('fsSound','1')==='1',voiceOn=()=>!quiet()&&lsGet('fsVoice','1')==='1',musicOn=()=>!quiet()&&lsGet('fsMusic','1')==='1';
const dayOf=e=>String(e.t||'').slice(0,10),today=()=>nowLocal().slice(0,10);
const logsBy=u=>FUN.ev.filter(e=>e.k==='log'&&(!u||e.by===u));
const pts=e=>e.o==='viewing'?10:e.o==='replied'?3:1;
function ymd(d){return new Date(d-d.getTimezoneOffset()*6e4).toISOString().slice(0,10)}
function streak(u){const days=new Set(logsBy(u).map(dayOf));let d=new Date(),n=0;if(!days.has(ymd(d)))d=new Date(d-864e5);while(days.has(ymd(d))){n++;d=new Date(d-864e5)}return n}
function weekStart(){const d=new Date(),k=(d.getDay()+6)%7;return ymd(new Date(d.getFullYear(),d.getMonth(),d.getDate()-k))}
const hatFor=n=>n>=14?'🏆':n>=7?'👑':n>=3?'🦸':n>=1?'🧢':'';
const faceUrl=u=>FUN.assets['face_'+u];
function faceHtml(u,cls){const url=faceUrl(u);return url?`<img class="face" src="${esc(url)}" alt="${esc(u)}">`:`<div class="face">${esc((u||'?')[0].toUpperCase())}</div>`}
function bingoLit(){const s=new Set(FUN.ev.filter(e=>e.k==='log'&&e.o).map(e=>e.o));return BINGO.map(o=>s.has(o))}
function bingoLines(){const l=bingoLit(),L=[[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];return L.filter(r=>r.every(i=>l[i]))}
const lootOf=e=>{let h=0;for(const c of String(e.t)+String(e.lid)+String(e.by))h=(h*31+c.charCodeAt(0))>>>0;return h%LOOT.length};

// ---- sounds (synthesised, nothing downloaded)
let AC=null;
function audio(){if(!AC){const C=window.AudioContext||window.webkitAudioContext;if(!C)return null;AC=new C()}if(AC.state==='suspended')AC.resume();return AC}
function tone(f,t0,d,type,g,f2){const a=audio();if(!a)return;const o=a.createOscillator(),v=a.createGain(),T=a.currentTime+t0;o.type=type||'sine';o.frequency.setValueAtTime(f,T);if(f2)o.frequency.exponentialRampToValueAtTime(f2,T+d);
 v.gain.setValueAtTime(.0001,T);v.gain.exponentialRampToValueAtTime(g||.12,T+.03);v.gain.exponentialRampToValueAtTime(.0001,T+d);o.connect(v);v.connect(a.destination);o.start(T);o.stop(T+d+.05)}
function burst(t0,d,g,f){const a=audio();if(!a)return;const n=Math.floor(a.sampleRate*d),b=a.createBuffer(1,n,a.sampleRate),x=b.getChannelData(0);for(let i=0;i<n;i++)x[i]=(Math.random()*2-1)*(1-i/n);
 const s=a.createBufferSource(),fl=a.createBiquadFilter(),v=a.createGain();s.buffer=b;fl.type='bandpass';fl.frequency.value=f||1800;v.gain.value=g||.12;s.connect(fl);fl.connect(v);v.connect(a.destination);s.start(a.currentTime+t0)}
function sfx(kind){if(!soundOn())return;try{
 if(kind==='cheer'){for(let i=0;i<14;i++)burst(i*.07+Math.random()*.03,.25,.1,1200+Math.random()*2200);[523,659,784].forEach((f,i)=>tone(f,.05+i*.09,.3,'triangle',.08))}
 else if(kind==='trombone'){[[233,0,.45],[220,.5,.45],[208,.95,.45]].forEach(([f,t,d])=>tone(f,t,d,'sawtooth',.1,f*.97));tone(196,1.45,1.1,'sawtooth',.11,150)}
 else if(kind==='fanfare'){[523,659,784,1047].forEach((f,i)=>tone(f,i*.13,.22,'square',.09));[523,659,784,1047].forEach(f=>tone(f,.62,.9,'square',.06));for(let i=0;i<10;i++)burst(.6+i*.06,.2,.08,2500+Math.random()*2000)}
 else if(kind==='pop')tone(660,0,.12,'sine',.1,990)}catch(e){}}
let MUSIC=null;
function musicStart(){if(MUSIC||!soundOn()||!musicOn())return;const a=audio();if(!a)return;const ch=[[220,262,330,392],[294,349,440,523],[196,247,294,349],[262,330,392,494]];let i=0;
 const bar=()=>{const c=ch[i++%4];c.forEach((f,k)=>tone(f,k*.5,.9,'triangle',.03));tone(c[0]/2,0,1.8,'sine',.05)};bar();MUSIC=setInterval(bar,2000)}
function musicStop(){if(MUSIC){clearInterval(MUSIC);MUSIC=null}}
function say(t,p){if(!voiceOn()||!window.speechSynthesis)return;try{const u=new SpeechSynthesisUtterance(t);u.pitch=p||(.5+Math.random()*1.4);u.rate=.85+Math.random()*.45;speechSynthesis.cancel();speechSynthesis.speak(u)}catch(e){}}
function confetti(n,set){const em=set||['🎉','✨','🎊','⭐','🧡','💚'];for(let i=0;i<(n||24);i++){const s=document.createElement('span');s.className='confetti';s.textContent=pick(em);s.style.left=Math.random()*100+'vw';s.style.animationDelay=Math.random()*.8+'s';s.style.fontSize=16+Math.random()*18+'px';document.body.appendChild(s);setTimeout(()=>s.remove(),4000)}}
const memeKeys=k=>Object.keys(FUN.assets).filter(n=>new RegExp('^meme_'+k+'(_\\d+)?$').test(n));
const memePick=k=>{const l=memeKeys(k);return l.length?FUN.assets[pick(l)]:null};
function roller(e){const el=document.createElement('div');el.className='roller';el.textContent=e;document.body.appendChild(el);setTimeout(()=>el.remove(),7200)}
function floater(e){const el=document.createElement('div');el.className='floater';el.textContent=e;el.style.left=10+Math.random()*75+'vw';el.style.bottom='4vh';document.body.appendChild(el);setTimeout(()=>el.remove(),4600)}
function sticker(who,text,kind,withMeme,shake){const old=document.getElementById('sticker');if(old)old.remove();const el=document.createElement('div');el.id='sticker';
 const f=faceUrl(who),hat=kind==='win'?'👑':'';const memeUrl=memePick(kind==='win'||kind==='yes'?'yes':kind==='no'?'no':'meh');
 const pic=f?`<img class="pic" src="${esc(f)}" alt="">`:`<div class="pic">${kind==='no'?'😵':kind==='win'?'🕺':'😎'}<span class="crown">${hat}</span></div>`;
 const meme=withMeme===false?'':memeUrl?`<img class="meme" src="${esc(memeUrl)}" alt="">`:`<div class="meme">${kind==='no'?'👻':kind==='win'||kind==='yes'?'💃':'🎉'}</div>`;
 el.innerHTML=`<div class="say">${esc(text)}</div>${meme}${pic}`;if(shake)el.classList.add('shake');document.body.appendChild(el);setTimeout(()=>el.remove(),shake?4800:3500)}
function react(o){const t=(OUT[o]||{}).t||'meh',who=FUN.me||'me';const kind=t==='win'?'win':t==='no'?'no':t==='yes'?'yes':'meh';
 sfx(kind==='win'?'fanfare':kind==='no'?'trombone':'cheer');const ln=line(kind==='win'?'win':kind==='no'?'no':kind==='yes'?'replied':'call');
 sticker(who,ln,kind);say(ln);if(kind==='win'||kind==='yes')confetti(kind==='win'?36:18);
 if(kind==='no'&&darkOn()){confetti(10,['💀','🏚','📦','🥶','🪦']);if(Math.random()<.4)roller('🌿')}
 if(kind==='no'&&Math.random()<.35)floater(pick(['👻','💀','🕳']));resetNag()}

// ---- data
async function funLoad(){try{const r=await fetch('/api/fun');if(!r.ok)throw new Error(r.status);const j=await r.json();FUN.ev=j.events||[];FUN.set=j.settings||FUN.set;FUN.assets=j.assets||{};FUN.me=j.me||FUN.me;FUN.users=j.users||[];FUN.ok=true;checkCheers()}catch(e){FUN.ok=false}
 if(view==='today')renderToday()}
async function funPost(path,body){try{const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});return r.ok}catch(e){return false}}
function checkCheers(){const c=FUN.ev.filter(e=>(e.k==='cheer'||e.k==='poke')&&e.to===FUN.me);if(!c.length)return;const last=c[c.length-1].t,seen=lsGet('cheerSeen:'+FUN.me,null);
 if(seen===null){lsSet('cheerSeen:'+FUN.me,last);return}
 if(last>seen){lsSet('cheerSeen:'+FUN.me,last);const e=c[c.length-1];if(e.k==='poke'){const t=e.m==='ad'?cap(e.by)+' clicked a "cardboard box" ad. Somebody is giving up!':cap(e.by)+' '+pick(PEPD.poke);sfx('trombone');sticker(e.by,t,'no',true,true);floater('👉');document.body.classList.add('shake');setTimeout(()=>document.body.classList.remove('shake'),600);say(t)}
  else{const t=cap(e.by)+' '+pick(PEP.cheer);sfx('cheer');sticker(e.by,t,'win',false);confetti(30);say(t)}}}
async function onLog(lid,status,outcome){const o=outcome||STATUS_OUT[status]||null,before=bingoLines().length;
 FUN.ev.push({t:nowLocal(),by:FUN.me||'me',k:'log',lid,o,s:status,to:''});
 const ok=await funPost('/api/fun/event',{k:'log',lid,s:status,o});if(!ok)toast('Could not reach the shared copy to save your points (the status itself is saved).');
 react(o||'callback');moodRadio(o);if(bingoLines().length>before)setTimeout(()=>{sfx('fanfare');sticker(FUN.me,'BINGO! A full row!','win');confetti(50)},1400);
 if(view==='today')renderToday()}
let FUNPEND=null;
const _saveOrig=save;
save=async function(id,patch){const prev=(S[id]||{}).status||'new',pend=FUNPEND;FUNPEND=null;const r=await _saveOrig(id,patch);
 if(patch.status&&patch.status!=='new'&&(pend||patch.status!==prev))onLog(id,patch.status,pend&&pend.o);return r};

// ---- the Today tab
function todays(){const n=Math.max(1,FUN.users.length),i=Math.max(0,FUN.users.indexOf(FUN.me)),h=s=>{let k=0;for(const c of s)k=(k*31+c.charCodeAt(0))>>>0;return k};
 const done=logsBy(FUN.me).filter(e=>dayOf(e)===today());const extra=+lsGet('funExtra:'+today(),0)||0,want=(FUN.set.daily||3)+extra;
 const doneIds=new Set(done.map(e=>e.lid));
 const pool=D.filter(x=>x.good&&!x.gone&&x.verified&&st(x)==='new'&&!doneIds.has(x.id)&&h(x.id)%n===i).sort((a,b)=>(b.new-a.new)||(b.score-a.score));
 return{done,want,left:Math.max(0,want-done.length),pool}}
function outButtons(x){const main=['noanswer','replied','viewing','nothanks'],more=Object.keys(OUT).filter(o=>!main.includes(o));
 const b=o=>`<button data-out="${o}" data-lid="${x.id}"${OUT[o].t==='win'?' class="win"':''}>${OUT[o].t==='win'?'🎉 ':''}${OUT[o].l}</button>`;
 return `<div class="outs"><span class="sub">Result of the call:</span>${main.map(b).join('')}<details><summary class="sub">more results</summary>${more.map(b).join('')}</details></div>`}
function renderToday(){
 q('tdWho').textContent=FUN.me?'· you are '+cap(FUN.me):'';
 q('tdOff').textContent=FUN.ok?'':'The fun features need the shared copy (it is not reachable right now), so points and pictures are paused.';
 const t=todays(),me=FUN.me,s=streak(me),viewings=new Set(FUN.ev.filter(e=>e.k==='log'&&e.o==='viewing').map(e=>e.lid)).size,goal=FUN.set.goal||5,pctG=Math.min(100,Math.round(viewings/goal*100)),dn=t.done.length,pctD=Math.min(100,Math.round(dn/(t.want||1)*100));
 q('tdHero').innerHTML=`<div class="hero"><div class="avatar">${faceHtml(me)}<span class="hat">${hatFor(s)}</span></div><div style="flex:1;min-width:220px"><div class="bigline"><b>🔥 ${s}</b> day streak <span class="sub">(days with at least one contact; 🧢 1 · 🦸 3 · 👑 7 · 🏆 14)</span></div>
  <div class="sub">Today: ${dn} of ${t.want} contacts</div><div class="pbar"><i style="width:${pctD}%"></i></div>
  <div class="sub">Team goal: ${viewings} of ${goal} viewings booked</div><div class="pbar"><i style="width:${pctG}%"></i></div></div></div>
  <div style="margin-top:8px">${FUN.users.filter(u=>u!==me).map(u=>`<button data-cheer="${esc(u)}">📣 Cheer ${esc(cap(u))}</button> <button data-poke="${esc(u)}">👉 Poke ${esc(cap(u))}</button>`).join(' ')} <button id="fsMute">${soundOn()?'🔊 sound on':'🔇 sound off'}</button></div>`;
 const tm=+lsGet('funTimerEnd',0)||0,run=tm>Date.now();
 q('tdTimer').innerHTML=run?`<div class="timer"><span class="clock" id="tdClock">--:--</span><button data-timer="stop">stop</button><span class="sub">${musicOn()?'🎵 hold music is playing':''}</span></div>`:`<div class="timer"><button class="primary" data-timer="start">▶ Just try 10 minutes</button><span class="sub">Call as many as you can. After ten minutes you may stop.</span></div>`;
 if(run)tickTimer();
 {const a=(typeof nextActions==='function')?nextActions():null,n=a?a.replies.length+a.viewings.length+a.follow.length:0;
  q('tdCards').innerHTML=t.left>0?`<div class="fbox"><b>${t.left===1?'1 contact':t.left+' contacts'} left for today.</b> <span class="sub">${n?n+' thing'+(n>1?'s':'')+' waiting too (replies, viewings, follow-ups).':''}</span><div style="margin-top:8px"><a class="btn primary" href="/#next" style="padding:8px 16px">▶ Open "What to do now"</a></div></div>`
   :`<div class="fbox doneBox"><div class="big">🎉</div><b>Done for today!</b><div class="sub">You made ${dn} contacts. That is enough. Go and eat something nice.</div><button data-more="1" style="margin-top:8px">I want 3 more anyway</button> <a class="btn" href="/#next">▶ What to do now</a></div>`}
 const ws=weekStart(),score=u=>logsBy(u).filter(e=>dayOf(e)>=ws).reduce((a,e)=>a+pts(e),0),sc=FUN.users.map(u=>[u,score(u)]),mx=Math.max(1,...sc.map(x=>x[1]));
 const lead=sc.length>1&&sc[0][1]!==sc[1][1]?[...sc].sort((a,b)=>b[1]-a[1])[0][0]:null;
 q('tdLeague').innerHTML=sc.map(([u,v])=>`<div class="row"><div class="avatar" style="width:44px;height:44px">${faceHtml(u)}<span class="hat" style="font-size:18px;top:-12px">${hatFor(streak(u))}</span></div><b style="width:64px">${esc(cap(u))}</b><div class="pbar"><i style="width:${Math.round(v/mx*100)}%"></i></div><span>${v} pts</span></div>`).join('')+
  `<div class="sub">Points: 1 per contact, 3 for a reply, 10 for a booked viewing. ${lead?'Leading: <b>'+esc(cap(lead))+'</b>. ':''}${FUN.set.prize?'🏆 Prize: '+esc(FUN.set.prize):'Set a prize in the fun settings.'}</div>`;
 const lit=bingoLit(),lines=bingoLines(),inLine=new Set(lines.flat());
 q('tdBingo').innerHTML=`<div class="bingo">${BINGO.map((o,i)=>`<div class="${lit[i]?'lit':''}${inLine.has(i)?' line':''}">${esc(OUT[o].l)}</div>`).join('')}</div><div class="sub" style="margin-top:6px">${lines.length?'🎉 BINGO x'+lines.length+'!':'No full row yet.'}</div>`;
 const nos=FUN.ev.filter(e=>e.k==='log'&&e.o&&OUT[e.o].t==='no'),myNo=nos.filter(e=>e.by===me).length,yes=FUN.ev.filter(e=>e.k==='log'&&e.o&&['yes','win'].includes(OUT[e.o].t)).length;
 q('tdNos').innerHTML=`<div class="bigline">Your no's: <b>${myNo}</b> · team no's: <b>${nos.length}</b> · team yeses: <b>${yes}</b></div><div class="sub">Rule of thumb (made up, but it feels true): about 10 no's per yes. ${nos.length>=10&&!yes?'You are overdue a yes. It is coming.':nos.length?'Every no is a coin in the yes jar.':'Log a result to start the jar.'}</div>`;
 const got=new Map();logsBy().forEach(e=>{const k=lootOf(e);got.set(k,(got.get(k)||0)+1)});
 q('tdLoot').innerHTML=`<div class="sub" style="margin-bottom:6px">${got.size} of ${LOOT.length} found</div><div class="lootgrid">${LOOT.map((n,i)=>got.has(i)?`<span>${esc(n)}${got.get(i)>1?' ×'+got.get(i):''}</span>`:`<span class="none">❔ ???</span>`).join('')}</div>`;
 q('fsVis').checked=visOn();q('fsVisMin').value=visMin();q('fsVisFrom').value=visFrom();q('fsVisTo').value=visTo();if(document.activeElement!==q('fsDeadline'))q('fsDeadline').value=FUN.set.deadline||'';countdown();q('fsDark').checked=darkOn();q('fsNudge').checked=nudgeOn();q('fsNudgeMin').value=String(nudgeMin());q('fsNotif').checked=notifOn();q('fsNotifFrom').value=nFrom();q('fsNotifTo').value=nTo();renderNotifBar();
 const hp=q('tdHelp');if(hp&&!hp.dataset.init){hp.dataset.init='1';hp.open=lsGet('helpOpen','1')==='1';hp.addEventListener('toggle',()=>lsSet('helpOpen',hp.open?'1':'0'))}
 q('fsSound').checked=soundOn();q('fsVoice').checked=voiceOn();q('fsMusic').checked=musicOn();
 if(document.activeElement!==q('fsGoal'))q('fsGoal').value=FUN.set.goal;if(document.activeElement!==q('fsDaily'))q('fsDaily').value=FUN.set.daily;if(document.activeElement!==q('fsPrize'))q('fsPrize').value=FUN.set.prize||'';
 {const e=q('pvFace');e.hidden=!faceUrl(me);if(faceUrl(me))e.src=faceUrl(me)}
 q('memeList').innerHTML=Object.keys(FUN.assets).filter(n=>n.startsWith('meme_')).sort().map(n=>`<div class="mi" title="${esc(n.replace('meme_','').replace('_',' '))}"><img src="${esc(FUN.assets[n])}" alt=""><button data-delmeme="${n}" title="remove">×</button></div>`).join('')||'<span class="sub">No memes yet: emoji are used.</span>'}
function pill(){let p=document.getElementById('tdPill');if(!p){p=document.createElement('div');p.id='tdPill';p.innerHTML='<span>⏱</span><a href="/#today" id="tdPillClock">--:--</a><button data-timer="stop">stop</button>';document.body.appendChild(p)}
 const left=(+lsGet('funTimerEnd',0)||0)-Date.now();if(left<=0){p.classList.remove('on');return}p.classList.add('on');const s=Math.ceil(left/1000);document.getElementById('tdPillClock').textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}
function tickTimer(){const end=+lsGet('funTimerEnd',0)||0,c=q('tdClock'),left=end-Date.now();pill();
 if(left<=0){if(end){lsSet('funTimerEnd',0);musicStop();sfx('fanfare');const l=line('done');sticker(FUN.me,l,'win');say(l);confetti(40);funPost('/api/fun/event',{k:'timer'})}if(view==='today')renderToday();return}
 if(c){const s=Math.ceil(left/1000);c.textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')}}
setInterval(()=>{if(+lsGet('funTimerEnd',0)>0)tickTimer();else pill()},1000);pill();
function shrink(file,max,png){return new Promise((res,rej)=>{const img=new Image(),u=URL.createObjectURL(file);img.onload=()=>{const k=Math.min(1,max/Math.max(img.width,img.height)),c=document.createElement('canvas');c.width=Math.max(1,Math.round(img.width*k));c.height=Math.max(1,Math.round(img.height*k));c.getContext('2d').drawImage(img,0,0,c.width,c.height);URL.revokeObjectURL(u);if(!png){const x=c.getContext('2d');x.globalCompositeOperation='destination-over';x.fillStyle='#fff';x.fillRect(0,0,c.width,c.height)}c.toBlob(b=>b?res(b):rej(new Error('cannot convert the picture')),png?'image/png':'image/jpeg',.85)};img.onerror=()=>rej(new Error('that file is not a picture'));img.src=u})}
async function upload(slot,input){const f=input.files&&input.files[0];if(!f)return;try{
 if(/^meme_(yes|no|meh)$/.test(slot)){const used=new Set(Object.keys(FUN.assets));let i=1;while(used.has(slot+'_'+i)&&i<30)i++;if(i>=30)throw new Error('too many memes of this kind');slot=slot+'_'+i}
 const png=slot==='face',b=await shrink(f,png?320:480,png);
 const r=await fetch('/api/fun/asset?slot='+slot,{method:'POST',headers:{'Content-Type':png?'image/png':'image/jpeg','X-Flat':'1'},body:b});if(!r.ok)throw new Error((await r.json().catch(()=>({}))).error||'upload failed');toast('Picture saved');input.value='';await funLoad()}catch(err){toast('⚠ '+err.message)}}
document.addEventListener('click',async e=>{
 const ob=e.target.closest('button[data-out]');if(ob){const o=ob.dataset.out;FUNPEND={o};audio();await save(ob.dataset.lid,{status:OUT[o].s});render();return}
 const tb=e.target.closest('button[data-timer]');if(tb){audio();if(tb.dataset.timer==='start'){lsSet('funTimerEnd',Date.now()+6e5);pill();musicStart();const l=line('start');say(l);sfx('pop');toast(l)}else{lsSet('funTimerEnd',0);musicStop()}pill();renderToday();return}
 const ch=e.target.closest('button[data-cheer]');if(ch){audio();await funPost('/api/fun/event',{k:'cheer',to:ch.dataset.cheer});sfx('cheer');confetti(14);toast('Cheer sent to '+cap(ch.dataset.cheer)+'!');return}
 const vb=e.target.closest('button[data-vis]');if(vb){audio();({walk:visWalk,peek:visPeek,ghost:visGhost,news:visNews,ad:visAd})[vb.dataset.vis]();return}
 const nb=e.target.closest('button[data-notif]');if(nb){if(nb.dataset.notif==='ask')await askNotif();else{try{sessionStorage.setItem('notifLater','1')}catch(e){}renderNotifBar()}return}
 if(e.target.id==='fsNotifAsk'){await askNotif();return}
 if(e.target.id==='fsNotifTest'){if(lsGet('pushOn','0')==='1'){try{const r=await(await fetch('/api/push/test',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'})).json();toast(r.sent?'Test sent to '+r.sent+' device(s). It arrives in a few seconds, even if you close the site.':'No device is registered for you yet.')}catch(x){toast('Could not send the test')}return}
  if(!showNotif('🏠 Test reminder','This is how the hourly reminder will look. Now go and call somebody.'))toast('Allow notifications first (or this browser blocks them)');return}
 const dm=e.target.closest('button[data-delmeme]');if(dm){if(await funPost('/api/fun/asset/delete',{slot:dm.dataset.delmeme}))toast('Meme removed');await funLoad();return}
 const pk=e.target.closest('button[data-poke]');if(pk){audio();await funPost('/api/fun/event',{k:'poke',to:pk.dataset.poke});sfx('pop');toast('Poked '+cap(pk.dataset.poke)+'. They will hear about it.');return}
 const mo=e.target.closest('button[data-more]');if(mo){lsSet('funExtra:'+today(),(+lsGet('funExtra:'+today(),0)||0)+3);renderToday();return}
 if(e.target.id==='fsMute'){lsSet('fsSound',soundOn()?'0':'1');if(!soundOn())musicStop();renderToday();return}
 if(e.target.id==='fsSave'){const ok=await funPost('/api/fun/settings',{goal:+q('fsGoal').value||5,daily:+q('fsDaily').value||3,prize:q('fsPrize').value,deadline:q('fsDeadline').value||undefined});toast(ok?'Saved':'⚠ Could not save');await funLoad();return}
});
document.addEventListener('change',e=>{
 if(e.target.id==='fsSound'){lsSet('fsSound',e.target.checked?'1':'0');if(!e.target.checked)musicStop()}
 else if(e.target.id==='fsNotif'){lsSet('fsNotif',e.target.checked?'1':'0');if(!e.target.checked)pushUnsubscribe().then(renderNotifBar);else if(NF()&&Notification.permission==='default')askNotif();else if(window.FF_CLOUD)pushSubscribe().then(renderNotifBar);renderNotifBar()}
 else if(e.target.id==='fsNotifFrom'){lsSet('fsNotifFrom',Math.max(0,Math.min(23,+e.target.value||9)));if(lsGet('pushOn','0')==='1')pushSubscribe();renderNotifBar()}
 else if(e.target.id==='fsNotifTo'){lsSet('fsNotifTo',Math.max(1,Math.min(23,+e.target.value||18)));if(lsGet('pushOn','0')==='1')pushSubscribe();renderNotifBar()}
 else if(e.target.id==='fsVis')lsSet('fsVis',e.target.checked?'1':'0');
 else if(e.target.id==='fsVisMin')lsSet('fsVisMin',Math.max(1,Math.min(120,+e.target.value||5)));
 else if(e.target.id==='fsVisFrom')lsSet('fsVisFrom',Math.max(0,Math.min(23,+e.target.value||0)));
 else if(e.target.id==='fsVisTo')lsSet('fsVisTo',Math.max(1,Math.min(24,+e.target.value||24)));
 else if(e.target.id==='fsDark')lsSet('fsDark',e.target.checked?'1':'0');
 else if(e.target.id==='fsNudge'){lsSet('fsNudge',e.target.checked?'1':'0');resetNag()}
 else if(e.target.id==='fsNudgeMin'){lsSet('fsNudgeMin',e.target.value);resetNag()}
 else if(e.target.id==='fsVoice')lsSet('fsVoice',e.target.checked?'1':'0');
 else if(e.target.id==='fsMusic'){lsSet('fsMusic',e.target.checked?'1':'0');if(!e.target.checked)musicStop()}
 else if(e.target.id==='upFace')upload('face',e.target);else if(e.target.id==='upMemeNo')upload('meme_no',e.target);else if(e.target.id==='upMemeYes')upload('meme_yes',e.target);else if(e.target.id==='upMemeMeh')upload('meme_meh',e.target)});
// ---- browser notifications: an hourly reminder in the working hours (needs permission and an open tab)
const NF=()=>typeof Notification!=='undefined';
const notifOn=()=>!quiet()&&lsGet('fsNotif','1')==='1',nFrom=()=>+lsGet('fsNotifFrom',9),nTo=()=>+lsGet('fsNotifTo',18);
const NOTIF_LINES=['Hourly reminder: have you called a landlord yet?','The flat will not find itself. Do one call.','Do you want to be homeless? Just checking.','The bridge is still cold. A viewing is warmer.','Ten minutes. One landlord. You can do this.','Another hour gone. Another bunk bed night closer.'];
function notifState(){if(!NF())return 'This browser has no notifications.';return Notification.permission==='granted'?'Allowed.':Notification.permission==='denied'?'Blocked: allow them in the browser\'s site settings (the lock icon in the address bar).':'Not allowed yet.'}
function renderNotifBar(){const b=q('tdNotif');if(!b)return;const p=NF()?Notification.permission:'none';let later=false;try{later=sessionStorage.getItem('notifLater')==='1'}catch(e){}
 const show=NF()&&p!=='granted'&&!(later&&p==='default');b.hidden=!show;
 if(show)b.innerHTML=p==='denied'?'<span>🔔 <b>Notifications are blocked</b> in this browser. Click the lock icon next to the address, set Notifications to Allow, then reload this page.</span><button data-notif="ask">Try again</button>':'<span>🔔 <b>Allow notifications</b> to get a reminder every hour from '+nFrom()+':00 to '+nTo()+':00 to find a flat.</span><button class="primary" data-notif="ask">🔔 Allow notifications</button><button data-notif="later">Not now</button>';
 const st=q('fsNotifState');if(st)st.textContent=notifState();const ps=q('fsPushState');if(ps)ps.textContent=pushLine()}
async function askNotif(){if(!NF()){toast('This browser does not support notifications');return}try{const p=await Notification.requestPermission();if(p==='granted'&&window.FF_CLOUD){const ok=await pushSubscribe();toast(ok?'Done. Reminders will arrive even when the site is closed.':'Notifications on while the site is open (background reminders could not be set up).')}else toast(p==='granted'?'Notifications on. You will get an hourly reminder while this site is open.':p==='denied'?'Blocked. Allow them in the browser site settings.':'Not allowed')}catch(e){toast('Could not ask for permission')}renderNotifBar()}
// background reminders (Web Push): the shared copy sends them even when this site is closed. Only on the shared site (a service worker needs its own address).
const pushOK=()=>!!window.FF_CLOUD&&'serviceWorker' in navigator&&'PushManager' in window&&NF();
const u8=b=>{const p='='.repeat((4-b.length%4)%4),r=atob((b+p).replace(/-/g,'+').replace(/_/g,'/'));return Uint8Array.from([...r].map(c=>c.charCodeAt(0)))};
async function pushSubscribe(){if(!pushOK()||Notification.permission!=='granted')return false;try{
 const reg=await navigator.serviceWorker.register('/sw.js',{scope:'/'});await navigator.serviceWorker.ready;const k=await(await fetch('/api/push/key')).json();if(!k.supported)return false;
 const sub=(await reg.pushManager.getSubscription())||await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:u8(k.key)});
 const r=await fetch('/api/push/subscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({subscription:sub.toJSON(),from:nFrom(),to:nTo()})});
 if(r.ok){lsSet('pushOn','1');return true}}catch(e){console.warn('push',e)}return false}
async function pushUnsubscribe(){try{const reg=await navigator.serviceWorker.getRegistration('/');const sub=reg&&await reg.pushManager.getSubscription();if(sub){await fetch('/api/push/unsubscribe',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({endpoint:sub.endpoint})});await sub.unsubscribe()}}catch(e){}lsSet('pushOn','0')}
function pushLine(){if(!NF())return 'This browser has no notifications.';if(!window.FF_CLOUD)return 'Reminders when the site is closed only work on the shared site (open it from the link below).';
 if(!('serviceWorker' in navigator&&'PushManager' in window))return 'This browser cannot do background reminders (on iPhone, add the site to the Home Screen first).';return lsGet('pushOn','0')==='1'&&Notification.permission==='granted'?'✓ Background reminders are on: they arrive even when the site is closed.':'Background reminders are off.'}
function showNotif(title,body){if(!NF()||Notification.permission!=='granted')return false;try{const n=new Notification(title,{body,tag:'ff-hourly',icon:faceUrl(FUN.me)||undefined});n.onclick=()=>{window.focus();location.hash='#today';n.close()};return true}catch(e){return false}}
function hourly(){if(!notifOn()||!NF()||Notification.permission!=='granted'||lsGet('pushOn','0')==='1')return;const d=new Date(),h=d.getHours();if(h<nFrom()||h>nTo())return;const key=ymd(d)+'-'+h;if(lsGet('notifHour','')===key)return;if(d.getMinutes()>14)return;lsSet('notifHour',key);
 const t=todays();if(t.left<=0&&FUN.ok)return;if(+lsGet('funTimerEnd',0)>Date.now())return;
 const body=(darkOn()?pick(PEPD.nudge[Math.min(3,Math.floor(Math.random()*4))].concat(NOTIF_LINES)):pick(NOTIF_LINES))+(FUN.ok?'  '+t.left+' contact'+(t.left===1?'':'s')+' left today.':'');showNotif('🏠 Find a flat ('+h+':00)',body)}
setInterval(hourly,30000);
// ---- random visitors on every page + the countdown
const visOn=()=>!quiet()&&lsGet('fsVis','1')==='1',visMin=()=>Math.max(1,+lsGet('fsVisMin',5)||5),visFrom=()=>+lsGet('fsVisFrom',8),visTo=()=>+lsGet('fsVisTo',24);
const VIS_WALK=['Work hard, or you will be sleeping in a Belgian bus shelter.','I am a construction worker. I could build you a flat in forty years. Call a landlord instead.','Find a house. The pigeons already have a waiting list for your spot.','Do you want to be homeless? No? Then why is nobody calling?','Cardboard is cheap, but dignity is cheaper. Keep calling.','The bridge is cold, the tram is warm. Pay for neither. Find a flat.','Every landlord you skip is a bus shelter you move into.','You are one phone call away from not being a pigeon.'];
const VIS_PEEK=['Still no flat?','Call. Now.','I see you scrolling.','Homeless soon?','Landlords are waiting.','Boo. Go call somebody.','Tick tock.'];
const VIS_NEWS=['Local intern still without a flat. Pigeons offer him a spot.','Man scrolls housing website for third hour, calls nobody. Bridge reserves a spot.','Experts agree: sleeping in a hostel does not count as a permanent address.','Cardboard prices rise sharply as Brussels interns run out of time.','Shocking: landlords answer phones, but only if somebody calls them.','Intern spotted measuring a bus shelter. Sources say he is not joking.','Belgian pigeons form union to defend their territory from homeless interns.'];
const VIS_ADS=[{t:'📦 Cardboard box, only €0',s:'Bring your own tape. Pigeons not included.'},{t:'⛺ Tent for two, slightly damaged',s:'Canal view. Rain view too.'},{t:'🚏 Bus shelter, ground floor',s:'24/7 fresh air. Shared with strangers.'},{t:'🛏 Hostel bunk bed, top floor',s:'Now with free snoring. Rent by the night.'},{t:'🌉 Bridge, unfurnished',s:'Great acoustics. No landlord. No fridge.'}];
const crew=()=>FUN.users.length?FUN.users:['you'];
const visFace=u=>{const f=faceUrl(u);return f?`<img src="${esc(f)}" alt="">`:`<span class="emo">👷</span>`};
const clampBub=b=>{const r=b.getBoundingClientRect();b.style.marginLeft=(r.left<8?8-r.left:r.right>innerWidth-8?innerWidth-8-r.right:0)+'px'};
function visWalk(){const u=pick(crew()),el=document.createElement('div');el.className='vis walker';el.innerHTML=visFace(u)+'<div class="vbub" hidden></div>';document.body.appendChild(el);const w=innerWidth,stop=Math.round(w*(.2+Math.random()*.45));
 requestAnimationFrame(()=>requestAnimationFrame(()=>{el.classList.add('walking');el.style.transition='left 4.5s linear';el.style.left=stop+'px'}));
 setTimeout(()=>{el.classList.remove('walking');const t=pick(VIS_WALK),b=el.querySelector('.vbub');b.textContent=t;b.hidden=false;clampBub(b);sfx('pop');say(t,u===crew()[0]?.75:1.3);
  setTimeout(()=>{b.hidden=true;el.classList.add('walking');el.style.left=(w+220)+'px';setTimeout(()=>el.remove(),4800)},Math.max(3800,t.length*80))},4700)}
function visPeek(){const u=pick(crew()),side=pick(['bl','br','tl','tr']),el=document.createElement('div');el.className='vis peek '+side;const t=pick(VIS_PEEK);el.innerHTML=visFace(u)+`<div class="vbub">${esc(t)}</div>`;document.body.appendChild(el);
 requestAnimationFrame(()=>requestAnimationFrame(()=>{el.classList.add('in');clampBub(el.querySelector('.vbub'))}));setTimeout(()=>say(t),800);setTimeout(()=>{el.classList.remove('in');el.classList.add('out')},3600);setTimeout(()=>el.remove(),6600)}
function visGhost(){const el=document.createElement('div');el.className='vis ghost';el.innerHTML='<div class="gh">👻</div><div class="nosign">NO</div>';el.style.top=(12+Math.random()*55)+'vh';document.body.appendChild(el);
 el.onclick=()=>{el.remove();sfx('pop');toast('Landlord ghost banished. Nothing was logged.')};setTimeout(()=>el.remove(),11500);if(Math.random()<.5)say('Nooo.',.5)}
function visNews(){const t=pick(VIS_NEWS),el=document.createElement('div');el.className='vis newsbar';el.innerHTML=`<span class="nb">BREAKING</span><div class="nm"><span>${esc(t)}</span></div>`;document.body.appendChild(el);sfx('pop');say('Breaking news. '+t,.9);setTimeout(()=>el.remove(),17000)}
function visAd(){const a=pick(VIS_ADS),el=document.createElement('div');el.className='vis fakead';el.style.left=(5+Math.random()*50)+'vw';el.style.top=(14+Math.random()*40)+'vh';
 el.innerHTML=`<div class="ah"><span>AD · sponsored by despair</span><button title="close">✕</button></div><div class="ab"><b>${esc(a.t)}</b><span>${esc(a.s)}</span><u>Order now →</u></div>`;document.body.appendChild(el);
 el.querySelector('button').onclick=e=>{e.stopPropagation();el.remove()};
 el.querySelector('.ab').onclick=async()=>{el.remove();const p=crew().find(u=>u!==FUN.me);if(p){await funPost('/api/fun/event',{k:'poke',to:p,m:'ad'});toast('Ordered! '+cap(p)+' has been told you are giving up.')}else toast('Ordered. Nobody else to tell.');sfx('trombone')};
 setTimeout(()=>el.remove(),14000)}
let VISSTART=Date.now()+45000;
function visTick(){if(!visOn()||document.hidden||Date.now()<VISSTART)return;const h=new Date().getHours();if(h<visFrom()||h>=visTo())return;const a=document.activeElement;if(a&&/^(INPUT|TEXTAREA|SELECT)$/.test(a.tagName))return;
 const last=+lsGet('visLast',0)||0;if(Date.now()-last<visMin()*6e4-4000)return;lsSet('visLast',Date.now());visRandom()}
setInterval(visTick,10000);
function countdown(){if(!FUN.set.deadline){const old=document.getElementById('tdCount');if(old)old.remove();return}let c=document.getElementById('tdCount');if(!c){c=document.createElement('div');c.id='tdCount';c.onclick=()=>{lsSet('countMin',lsGet('countMin','0')==='1'?'0':'1');countdown()};document.body.appendChild(c)}
 const dl=FUN.set.deadline.split('-').map(Number),n=new Date(),days=Math.round((Date.UTC(dl[0],dl[1]-1,dl[2])-Date.UTC(n.getFullYear(),n.getMonth(),n.getDate()))/864e5);
 const hrs=Math.max(0,Math.ceil((new Date(dl[0],dl[1]-1,dl[2],23,59,59)-n)/36e5));
 const [st,msg]=days>60?[0,'Plenty of time. (That is a lie.)']:days>30?[1,'The clock is ticking.']:days>14?[2,'Panic is a valid strategy.']:days>7?[3,'Bus shelter brochures are being printed.']:days>3?[4,'The pigeons are measuring you for a nest.']:days>0?[5,'FINAL COUNTDOWN. Call EVERYONE.']:days===0?[5,'TODAY. The deadline is today. The bridge awaits.']:[5,'Deadline passed. How is the bridge?'];
 c.className='s'+st+(lsGet('countMin','0')==='1'?' min':'');
 const big=days>3?days+' day'+(days===1?'':'s'):days>0?days+' day'+(days===1?'':'s')+' '+(hrs-(days-1)*24>0&&days<=3?'(~'+hrs+' h)':''):days===0?'TODAY':Math.abs(days)+' days late';
 c.innerHTML=lsGet('countMin','0')==='1'?'🏠 <b>'+(days>0?days+'d':days===0?'today':'late')+'</b>':'🏠 <b>'+big+'</b> to find a home<div class="cl2">'+esc(msg)+'</div>';
 const key='countAnn';if(lsGet(key,'')!==today()&&days<=60&&FUN.ok){lsSet(key,today());setTimeout(()=>{const t=days>0?days+' days left to find a home. '+msg:msg;sticker(FUN.me,t,'no',false,days<=14);if(days<=30)say(t)},2500)}}
setInterval(countdown,60000);
// ---- nag: no contact logged for a while while this page is open -> push (daytime only), a bit harsher each time it is ignored
let NAGAT=Date.now(),NAGLVL=0;
function resetNag(){NAGAT=Date.now();NAGLVL=0}
function nag(){if(!nudgeOn()||document.hidden||!FUN.me)return;const h=new Date().getHours();if(h<8||h>=22)return;if(+lsGet('funTimerEnd',0)>Date.now())return;
 const mine=logsBy(FUN.me),last=mine.length?Date.parse(mine[mine.length-1].t):0;if(Date.now()-Math.max(NAGAT,last)<nudgeMin()*6e4)return;
 const lv=Math.min(NAGLVL,3),t=darkOn()?pick(PEPD.nudge[lv]):pick(gentleNudge);NAGLVL++;NAGAT=Date.now();
 sfx(lv>=2?'trombone':'pop');sticker(FUN.me,t,'no',lv>=1,true);say(t);if(lv>=1)floater(pick(['👻','🛏','🏚','📞']));if(lv>=2){roller('🌿');document.body.classList.add('shake');setTimeout(()=>document.body.classList.remove('shake'),600)}if(lv>=3)confetti(14,['💀','📦','🪦','📞'])}
setInterval(nag,30000);
if(!window.FF_CLOUD)fetch('/api/cloud').then(r=>r.json()).then(j=>{const e=q('fsPushLink');if(e&&j.url)e.innerHTML='Shared site: <a href="'+esc(j.url)+'" target="_blank" rel="noopener">'+esc(j.url)+'</a>'}).catch(()=>{});
if(window.FF_CLOUD&&NF()&&Notification.permission==='granted'&&notifOn())pushSubscribe();
countdown();
funLoad();setInterval(()=>{if(!document.hidden)funLoad()},20000);
"""


import fun_extra  # noqa: E402  (more surprises)
CSS += fun_extra.CSS
JS += fun_extra.JS
