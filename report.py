"""listings.csv + listings.html (contact-now shortlist, filters, copy-message buttons, status + notes)."""
import csv, hashlib, json, os
import fun
import firstrun
import ux
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))


def logo_url(source):
    """data/logos/<source>.png|svg|ico|webp, if you put one there (served at /logos/...); otherwise a letter badge is drawn."""
    for ext in ("svg", "png", "webp", "ico"):
        if os.path.exists(os.path.join(HERE, "data", "logos", f"{source}.{ext}")):
            return f"/logos/{source}.{ext}"
    return ""

STATUSES = ["new", "contacted", "replied", "visit", "applied", "rejected"]


def write_csv(items, path):
    cols = ["score", "new", "gone", "verified", "total", "rent", "charges", "minutes", "how", "km", "bedrooms", "m2", "locality",
            "postal", "street", "type", "furnished", "available", "flags", "phone", "agency", "source", "url"]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols)
        for it in items:
            w.writerow(["; ".join(it[c]) if c == "flags" else it.get(c, "") for c in cols])


def position(it, cfg):
    """(lat, lon, approximate). Exact when the listing gives a position; otherwise the area centre, spread a little so pins do not stack."""
    approx = bool(it.get("approx_pos"))
    if it.get("lat") and it.get("lon") and not approx:
        return it["lat"], it["lon"], False
    base = (it["lat"], it["lon"]) if it.get("lat") and it.get("lon") else (cfg["areas"].get(it.get("postal") or "") or {}).get("centre")
    if not base:
        return None, None, True
    h = int(hashlib.md5(it["id"].encode()).hexdigest()[:8], 16)
    return round(base[0] + ((h % 1000) / 1000 - 0.5) * 0.008, 5), round(base[1] + (((h >> 10) % 1000) / 1000 - 0.5) * 0.012, 5), True


def write_html(items, messages, path, cfg):
    data = [{
        "id": it["id"], "score": it["score"], "new": bool(it.get("new")), "title": it["title"][:80], "url": it["url"],
        "addr": " ".join(x for x in (it.get("street"), it.get("postal"), it.get("locality")) if x),
        "agency": it.get("agency") or "", "source": it["source"], "rent": it["rent"], "charges": it.get("charges") or 0,
        "total": it["total"], "minutes": it["minutes"], "how": it["how"], "km": it["km"], "beds": it.get("bedrooms"),
        "m2": it.get("m2"), "avail": it.get("available") or "", "flags": it["flags"], "good": it["good"],
        "gone": bool(it.get("gone")), "verified": bool(it.get("verified")), "phone": it.get("phone") or "",
        "website": it.get("website") or "", "hours": it.get("contact_hours") or "",
        "summary": (it.get("ai") or {}).get("summary", ""), "ev": {f: (it.get("evidence") or {}).get(f, "")[:150] for f in it["flags"] if (it.get("evidence") or {}).get(f)}, "lease": (it.get("ai") or {}).get("min_lease_months"),
        "epc": it.get("epc") or "", "modified": it.get("modified") or "", "first_seen": it.get("first_seen") or "", "logo": logo_url(it["source"]),
        "added": it.get("added") or "", "added_how": it.get("added_how") or "", "views": it.get("views"), "saves": it.get("saves"), "value": it.get("value"), "vparts": it.get("value_parts") or {}, "effective": it.get("effective"), "extras": it.get("extras") or {},
        "fee_range": it.get("fee_range"), "fee_note": it.get("fee_note") or "", "ppm2": it.get("ppm2"), "m2pp": it.get("m2_pp"), "costs": {"deposit": it.get("deposit_eur"), "deposit_src": it.get("deposit_src") or "", "deposit_months": round(it["deposit_eur"] / it["rent"], 1) if it.get("deposit_eur") and it.get("rent") else None,
                  "admin_fee": it.get("admin_fee"), "platform_fee": it.get("platform_fee"), "fee_exact": bool(it.get("fee_exact")), "fees_once": (it.get("extras") or {}).get("fee_once"),
                  "monthly_extra": it.get("monthly_extra"), "monthly_parts": it.get("monthly_extra_parts") or {}, "util_est": (it.get("extras") or {}).get("utilities") if it.get("monthly_extra") is None else None,
                  "unknown_extra": (it.get("extras") or {}).get("unknown_extra"), "couple": it.get("couple_extra"), "one_off_text": it.get("one_off_text"),
                  "min_stay": it.get("min_stay_months"), "max_stay": it.get("max_stay_months"), "couples_ok": it.get("couples_ok")},
        "upfront": it.get("upfront"), "late_days": it.get("late_days"), "beds_src": it.get("beds_src") or "", "m2_src": it.get("m2_src") or "",
        "lat": position(it, cfg)[0], "lon": position(it, cfg)[1], "approx": position(it, cfg)[2],
        "first_at": it.get("first_at") or "", "seen_at": it.get("seen_at") or "", "read_at": it.get("read_at") or "", "missed": it.get("missed", 0), "last_seen": it.get("last_seen") or "", "manual": bool(it.get("manual")), "rechecked": it.get("rechecked_at") or "", "similar": it.get("similar", 0), "postal": it.get("postal") or "", "locality": it.get("locality") or "", "ai": bool(it.get("ai")), "also": it.get("also", []), "msg": messages[it["id"]], "lang": messages[it["id"]]["_lang"],
    } for it in items]
    tram = [[n, p[0], p[1]] for n, p in (json.load(open(os.path.join(HERE, "data", "tram62.json"))).get("stops") or {}).items()]
    page = TEMPLATE.replace("__TRAM__", json.dumps(tram, ensure_ascii=False)).replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")) \
        .replace("__NEWDAYS__", str(cfg.get("new_days", 3))).replace("__STAMP__", datetime.now().strftime("%Y-%m-%d %H:%M")).replace("__BUDGET__", str(cfg["budget"])) \
        .replace("__ICON__", icon_b64()).replace("__FOUND__", json.dumps(cfg.get("found_mode") or {"on": False})).replace("__SETUP__", "true" if firstrun.needs_setup(cfg) else "false").replace("__FOLLOW__", json.dumps({"first": cfg.get("followup_first_days", 2), "next": cfg.get("followup_next_days", 3), "max": 0 if (cfg.get("found_mode") or {}).get("on") else cfg.get("followup_max", 2)})).replace("__HEALTH__", json.dumps(source_health())).replace("__STATUSES__", json.dumps(STATUSES)) \
        .replace("__FUNTAB__", fun.TAB).replace("__FUNCSS__", fun.CSS).replace("__FUNHTML__", fun.HTML).replace("__FUNJS__", fun.JS).replace("__UXTAB__", ux.TAB).replace("__UXTABFIRST__", ux.TABFIRST).replace("__UXHTML__", ux.HTML).replace("__UXCSS__", ux.CSS).replace("__UXJS__", ux.JS)
    with open(path, "w") as f:
        f.write(page)
    pool = sorted((d for d in data if d["good"] and not d["gone"] and d["verified"]), key=lambda d: (not d["new"], -d["score"]))[:40]          # for the morning digest
    with open(os.path.join(HERE, "pool.json"), "w") as f:
        json.dump([{"id": d["id"], "title": d["title"], "addr": d["addr"], "total": d["total"], "score": d["score"], "new": d["new"]} for d in pool], f)


def icon_b64():
    import base64
    try:
        with open(os.path.join(HERE, "icon.svg"), "rb") as f:
            return base64.b64encode(f.read()).decode()
    except OSError:
        return ""


HEALTH_FILE = os.path.join(HERE, "source_health.json")


def source_health():
    try:
        with open(HEALTH_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


TEMPLATE = r"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Nestbox</title><link rel="icon" type="image/svg+xml" href="data:image/svg+xml;base64,__ICON__">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css" integrity="sha384-sHL9NAb7lN7rfvG5lfHpm643Xkcjzp4jFvuavGOndn6pjVqS6ny56CAt3nsEVT4H" crossorigin="anonymous">
<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js" integrity="sha384-cxOPjt7s7Iz04uaHJceBmS+qpjv2JkIHNVcuOrM+YHwZOmJGBXI00mdUXEq65HTH" crossorigin="anonymous"></script>
<style>
:root{color-scheme:light dark;--bg:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e4e4e7;--good:#e6f4ea;--goodfg:#1e6b34;--bad:#fde8e8;--badfg:#a32020;--warn:#fff3d6;--warnfg:#8a5a00;--ok:#eef1f6;--okfg:#3a4a63;--acc:#2856d6;--card:#f7f7f9}
@media (prefers-color-scheme:dark){:root{--bg:#151517;--fg:#ececf0;--mut:#9a9aa3;--line:#2c2c31;--good:#16301f;--goodfg:#8fd6a4;--bad:#3a1818;--badfg:#f2a3a3;--warn:#3a2f12;--warnfg:#f0c674;--ok:#22262e;--okfg:#b6c2d6;--acc:#7a9cff;--card:#1d1d21}}
*{box-sizing:border-box}body{background:var(--bg);color:var(--fg);font:14px/1.45 -apple-system,system-ui,sans-serif;margin:0;padding:0 16px 16px;max-width:1100px;margin-inline:auto}
h1{font-size:20px;margin:12px 0 4px}h2{font-size:15px;margin:18px 0 4px}.sub{color:var(--mut);font-size:12px}a{color:var(--acc);text-decoration:none;font-weight:600}
#top{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--line)}
.tabs{display:flex;gap:4px;align-items:center;padding-top:8px}.tabs a{padding:5px 14px;border-radius:8px 8px 0 0;color:var(--mut);font-weight:600}
.tabs a.on{background:var(--card);color:var(--fg);border:1px solid var(--line);border-bottom:none}#run{margin-left:auto;font-size:12px}
#banner{padding:8px 0;display:flex;flex-wrap:wrap;gap:6px 14px;align-items:center}
#banner b{font-size:16px}.pill{border:1px solid var(--line);border-radius:14px;padding:2px 10px;background:var(--card);cursor:pointer;font-size:12px}
.bar{display:flex;flex-wrap:wrap;gap:8px 16px;margin:10px 0;align-items:center}label{white-space:nowrap}
select,input[type=number],input[type=search],input[type=date],input[type=text],button,textarea{font:inherit;color:inherit;background:var(--card);border:1px solid var(--line);border-radius:6px;padding:4px 8px}button{cursor:pointer}
.card{border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:8px 0;background:var(--card);display:grid;grid-template-columns:52px 1fr auto;gap:4px 12px}
.card.st-rejected{opacity:.4}.card.gone{opacity:.55}.card.st-contacted,.card.st-replied,.card.st-visit,.card.st-applied{border-left:4px solid var(--acc)}
.score{font-size:20px;font-weight:700;text-align:center}.price{text-align:right;white-space:nowrap;font-weight:600}
.tag{display:inline-block;font-size:11px;padding:1px 6px;border-radius:9px;margin:3px 4px 0 0;background:var(--ok);color:var(--okfg)}
.tag.good{background:var(--good);color:var(--goodfg)}.tag.bad{background:var(--bad);color:var(--badfg)}.tag.warn{background:var(--warn);color:var(--warnfg)}.tag.new{background:var(--acc);color:#fff}
details#stats,details#howscore{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:8px 12px;margin:8px 0}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:8px;margin-top:10px}.tile{border:1px solid var(--line);border-radius:8px;padding:6px 10px;background:var(--bg)}
.tile b{display:block;font-size:20px;line-height:1.2}.tile span{font-size:12px;color:var(--mut)}.tile.acc b{color:var(--acc)}
.lists{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:8px 18px;margin-top:10px}.lists table{width:100%;border-collapse:collapse;font-size:13px}
.lists td{padding:2px 0}.lists td:last-child{text-align:right;font-variant-numeric:tabular-nums}.lists h3{font-size:12px;color:var(--mut);margin:0 0 4px;font-weight:600}
.btn{font:inherit;border:1px solid var(--line);border-radius:6px;padding:4px 8px;background:var(--card);color:var(--fg);font-weight:400;display:inline-block}
.btn.wa{border-color:#2fb65a;color:#2fb65a;font-weight:600}.btn.wa:hover{background:#2fb65a;color:#fff}
.how{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:10px 24px;margin-top:8px}.how h3{font-size:12px;color:var(--mut);margin:0 0 4px;font-weight:600}
.how table{width:100%;border-collapse:collapse;font-size:13px}.how td{padding:2px 0;vertical-align:top}.how td:last-child{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums;padding-left:12px}
.how .bands td:last-child{color:var(--mut);font-size:12px;font-variant-numeric:normal}.b-great{color:var(--goodfg)}.b-good{color:var(--acc)}.b-weak{color:var(--badfg)}
.how .pos{color:var(--goodfg);font-weight:600}.how .neg{color:var(--badfg);font-weight:600}
.desc{margin-top:4px}.desc summary{cursor:pointer;font-size:12px;color:var(--mut)}
.desc-body{font-size:12.5px;line-height:1.55;max-height:280px;overflow:auto;border:1px solid var(--line);border-radius:6px;padding:7px 9px;background:var(--bg);margin-top:4px}
mark{border-radius:3px;padding:0 2px;color:inherit}.hl-bad{background:var(--bad);color:var(--badfg)}.hl-good{background:var(--good);color:var(--goodfg)}.hl-warn{background:var(--warn);color:var(--warnfg)}.hl-info{background:var(--ok);color:var(--okfg)}
.tag.manual{background:#7c3aed;color:#fff;font-weight:600}.tag.wrongpill{background:var(--bad);color:var(--badfg);font-weight:700}
.starbig{display:block;margin:8px auto 0;padding:3px 6px;min-width:44px;line-height:1;text-align:center;border-radius:8px}.starbig .g{display:block;font-size:24px}.starbig .w{display:block;font-size:10px;margin-top:1px}
.starbig.on{border-color:#f5b301;color:#f5b301}.starbig:hover{border-color:#f5b301}
.star{font-size:17px;line-height:1;padding:2px 9px}.star.on{color:#f5b301;border-color:#f5b301}
.wrongnote{grid-column:2/4;font-size:12.5px;background:var(--bad);color:var(--badfg);border-radius:6px;padding:5px 9px;margin-top:4px}
.healthbar{background:var(--bad);color:var(--badfg);border-radius:8px;padding:7px 12px;margin:6px 0;font-size:13px}#health button{font-size:12px;margin-bottom:6px}
.mailnote{grid-column:2/4;font-size:12.5px;background:var(--ok);color:var(--okfg);border-radius:6px;padding:5px 9px;margin-top:4px}.mailnote.maybe{background:var(--warn);color:var(--warnfg)}.mailnote.sub{background:none;color:var(--mut)}.mailnote button{font-size:12px;padding:1px 8px;margin-left:4px}
details#addbox{border:1px solid var(--line);border-radius:10px;background:var(--card);padding:8px 12px;margin:8px 0}.addrow{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
button.primary{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}
body.cloud #tabControl,body.cloud #addbox,body.cloud [data-recheck],body.cloud [data-rmmanual]{display:none!important}
#markedview,#mapview{display:none}body.marked #markedview{display:block}body.marked #allview,body.mapv #allview,body.mapv #markedview{display:none}body.mapv #mapview{display:block}
.leaflet-container{font:inherit;border-radius:10px}.leaflet-popup-content{color:#1d1d1f}.leaflet-popup-content a{color:#2856d6}.leaflet-popup-content button{background:#f1f1f4;color:#1d1d1f;border:1px solid #c4c4cc;border-radius:6px;padding:4px 12px;font:inherit;cursor:pointer}.leaflet-popup-content button:hover{background:#e4e4ea}.legend{background:rgba(255,255,255,.92);color:#1d1d1f;padding:6px 9px;border-radius:8px;font-size:12px;line-height:1.6}
.legend i{display:inline-block;width:11px;height:11px;border-radius:50%;margin-right:5px;vertical-align:-1px}
.costs{font-size:12px;color:var(--mut);margin-top:4px;line-height:1.7}.costs span{white-space:nowrap;margin-right:10px}.costs b{color:var(--fg)}.costs .warnc{color:var(--warnfg)}
.val{display:block;font-size:11px;font-weight:700;margin-top:2px;padding:1px 4px;border-radius:6px;background:var(--ok);color:var(--okfg);cursor:help}
.val.hi{background:var(--good);color:var(--goodfg)}.val.mid{background:var(--good);color:var(--goodfg);opacity:.75}.val.lo{background:var(--bad);color:var(--badfg)}
.score.great{color:var(--goodfg)}.score.good{color:var(--acc)}.score.weak{color:var(--mut)}
.src{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:5px;color:#fff;font-size:10px;font-weight:800;vertical-align:middle;margin-right:6px;object-fit:contain;background:#888}
img.src{background:#fff;border:1px solid var(--line);padding:1px}
.tag.stay{background:var(--goodfg);color:var(--bg);font-weight:700;font-size:12px;padding:2px 9px;animation:pulse 1.8s ease-in-out infinite}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(46,160,67,.55);transform:scale(1)}50%{box-shadow:0 0 0 7px rgba(46,160,67,0);transform:scale(1.06)}}
@media (prefers-reduced-motion:reduce){.tag.stay{animation:none}}
.row2{grid-column:2/4;display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px}.note{grid-column:2/4;width:100%;min-height:30px;resize:vertical;font-size:13px}
.ai{font-size:12.5px;margin-top:2px}#toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:var(--fg);color:var(--bg);padding:8px 14px;border-radius:8px;opacity:0;transition:.2s;pointer-events:none;z-index:9}
#toast.on{opacity:1}
.views{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0}.views button{border-radius:14px;padding:3px 12px;font-size:12.5px}
details.filters{border:1px solid var(--line);border-radius:10px;padding:8px 12px;background:var(--card);margin:8px 0}summary{cursor:pointer;font-weight:600}
.fgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:10px 14px;margin-top:10px}.fgrid label{display:block;font-size:12px;color:var(--mut);white-space:normal}.fgrid label>input,.fgrid label>select,.fgrid label>.pair{display:flex;margin-top:3px}.fgrid label>input[type=search],.fgrid label>input[type=number],.fgrid label>input[type=date],.fgrid label>select{display:block}
.fgrid .wide{grid-column:1/-1}.fgrid input,.fgrid select{width:100%;color:var(--fg)}.pair{display:flex;gap:6px}
fieldset{border:1px solid var(--line);border-radius:8px;margin:0;padding:6px 10px;grid-column:span 2}legend{font-size:12px;color:var(--mut);padding:0 4px}
.fgrid fieldset label{display:flex;flex-direction:row;align-items:center;gap:6px;color:var(--fg);font-size:13px;margin:3px 0}.fgrid fieldset label input{width:auto}
fieldset img.src,fieldset .src{width:16px;height:16px;margin:0;font-size:8px}fieldset.cols>div{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:0 12px}
.hint{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;border:1px solid var(--mut);color:var(--mut);font-size:10px;font-weight:700;margin-left:5px;cursor:help;position:relative;vertical-align:middle;line-height:1;flex:none}
.hint:hover,.hint:focus{color:var(--acc);border-color:var(--acc);outline:none}
.hint::after{content:attr(data-hint);position:absolute;left:50%;bottom:calc(100% + 7px);transform:translateX(-50%);width:max-content;max-width:min(270px,70vw);background:var(--fg);color:var(--bg);padding:7px 10px;border-radius:8px;font-size:12px;font-weight:400;line-height:1.4;white-space:normal;text-align:left;opacity:0;pointer-events:none;transition:opacity .12s;z-index:30;text-transform:none;letter-spacing:0}
.hint:hover::after,.hint:focus::after{opacity:1}.tile .hint{position:absolute;top:6px;right:6px;margin:0}.tile{position:relative}
__FUNCSS__
__UXCSS__
</style></head><body>
<div id="top"><nav class="tabs">__UXTABFIRST__<a href="/" id="tabAll" class="on">Listings</a><a href="/#marked" id="tabMarked">★ Marked <span class="sub" id="markedCount"></span></a><a href="/#map" id="tabMap">🗺 Map</a>__FUNTAB____UXTAB__<a href="/control" id="tabControl">Control panel</a><span id="run"></span></nav><div id="banner"></div><div id="health"></div></div>
<h1><img src="data:image/svg+xml;base64,__ICON__" width="34" height="34" alt="" style="vertical-align:-8px;border-radius:8px"> Nestbox <span class="sub" style="font-size:14px;font-weight:400">flat hunting in Brussels</span></h1><div class="sub" id="meta"></div>
<details id="addbox"><summary>＋ Add a listing by link <span data-h="add"></span></summary>
 <div class="addrow"><input id="addUrl" type="url" placeholder="Paste the link of one listing (Immoweb, Immovlan, Spotahome, HousingAnywhere, 2ememain)" style="flex:1;min-width:240px">
 <input id="addRent" type="number" step="50" placeholder="rent € (only if asked)" style="width:150px"><button id="addGo" class="primary">Add</button></div>
 <div class="sub" id="addMsg" style="margin-top:4px"></div></details>
<div id="allview">
<details id="stats" open><summary>Stats <span class="sub" id="statline"></span> <span data-h="stats"></span></summary><div id="statbody"></div></details>
<details id="howscore" open><summary>How scoring works <span class="sub">· two numbers on every card</span> <span data-h="how"></span></summary>
<p class="sub" style="margin:8px 0 0">The big number is the <b>match score</b> (does it fit what you need?). The small <b>value</b> number under it is <b>value points</b> (what do you get for the money?). Hover over either number on a card for the exact breakdown.</p>
<div class="how">
<div><h3>What is a good match score?</h3><table class="bands">
<tr><td><b class="b-great">100 or more</b> excellent</td><td>top 10% of good flats</td></tr>
<tr><td><b class="b-good">80 to 99</b> very good</td><td>next 25%</td></tr>
<tr><td><b>60 to 79</b> okay</td><td>the middle</td></tr>
<tr><td><b class="b-weak">under 60</b> weak</td><td>bottom 25%: probably a catch</td></tr>
</table><p class="sub" style="margin:2px 0 10px">Measured on today's good flats (median 73). Contact 80+ first.</p>
<h3>Match score: starts at 100</h3><table>
<tr><td>Price: every €10 of rent + charges above €900</td><td class="neg">−1</td></tr>
<tr><td>Commute: every minute above 15 (unknown = 45)</td><td class="neg">−0.9</td></tr>
<tr><td>Furnished</td><td class="pos">+18</td></tr><tr><td>Short stay OK (listing says so, or the minimum lease fits your stay)</td><td class="pos">+15</td></tr>
<tr><td>Address registration allowed</td><td class="pos">+10</td></tr><tr><td>Fridge or equipped kitchen</td><td class="pos">+4</td></tr><tr><td>Washing machine inside the flat (not shared, not just a connection)</td><td class="pos">+4</td></tr><tr><td>Listing text was read</td><td class="pos">+3</td></tr>
<tr><td>Fresh ad: online up to 3 days / up to 7 days</td><td class="pos">+6 / +3</td></tr><tr><td>Old ad: online more than 21 days</td><td class="neg">−4</td></tr>
<tr><td>Over your budget</td><td class="neg">−50</td></tr>
<tr><td>Free more than 2 weeks / 1 month after your move-in</td><td class="neg">−10 / −30</td></tr>
</table><h3 style="margin-top:8px">Problems that cost points</h3><table>
<tr><td>Shared room or flat</td><td class="neg">−80</td></tr><tr><td>Not a flat (storage, parking, office)</td><td class="neg">−80</td></tr><tr><td>Map pin far from the place named</td><td class="neg">−80</td></tr>
<tr><td>No address registration</td><td class="neg">−60</td></tr><tr><td>More than 25 km from EUROCONTROL</td><td class="neg">−60</td></tr>
<tr><td>One person only / students only</td><td class="neg">−40</td></tr><tr><td>Suspiciously cheap (under €550)</td><td class="neg">−40</td></tr>
<tr><td>Long lease only (9 months or more)</td><td class="neg">−30</td></tr><tr><td>Not updated for 45+ days</td><td class="neg">−25</td></tr>
<tr><td>Agency address abroad</td><td class="neg">−15</td></tr><tr><td>Under the minimum size</td><td class="neg">−15</td></tr>
<tr><td>Minimum lease longer than your stay</td><td class="neg">−12</td></tr>
</table></div>
<div><h3>What are good value points?</h3><table class="bands">
<tr><td><b class="b-great">53 or more</b> excellent</td><td>top 10%</td></tr>
<tr><td><b class="b-good">47 to 52</b> good</td><td>next 15%</td></tr>
<tr><td><b>40 to 46</b> average</td><td>the middle</td></tr>
<tr><td><b class="b-weak">under 40</b> below average</td><td>bottom 35%</td></tr>
</table><p class="sub" style="margin:2px 0 10px">Value points are lower than they look: a flat would need to be cheap, big, close, furnished and energy-efficient all at once to pass 65, and none does today (median 42, best 64). So 50 or more is already a very good deal.</p>
<h3>Value points: out of 100</h3><table>
<tr><td>Cost: real monthly cost, €600 or less = full, your budget (€__BUDGET__) = 0</td><td>40</td></tr>
<tr><td>Size: 20 m² = 0, 50 m² or more = full (unknown = 6)</td><td>15</td></tr>
<tr><td>Layout: studio 4, 1 bedroom 8, 2+ bedrooms 10 (unknown = 5)</td><td>10</td></tr>
<tr><td>Commute: 10 min = full, 60 min = 0 (unknown = 5)</td><td>15</td></tr>
<tr><td>Included: furnished 5, bills 3, fridge 2, washing machine 3, short stay 2</td><td>15</td></tr>
<tr><td>Energy rating: A/B 5, C 4, D 3, E 1, F/G 0, unknown 2</td><td>5</td></tr>
</table><p class="sub">A deal-breaker caps the value points at 25, however cheap the flat is.</p>
<h3 style="margin-top:8px">Real monthly cost</h3><p class="sub" style="margin:2px 0">Rent + charges, plus utilities when a platform excludes them, plus a furniture allowance if the flat is unfurnished, plus the platform's one-off fee spread over the months of your stay. The amounts are assumptions you can edit in the control panel.</p>
<h3 style="margin-top:8px">"Good" match</h3><p class="sub" style="margin:2px 0">Within your budget and no deal-breaker: no registration, long lease only, one person or students only, shared, wrong map location, too far, suspiciously cheap, or not a flat. The list hides everything else by default.</p>
<h3 style="margin-top:8px">How the description is read</h3><p class="sub" style="margin:2px 0">In French, Dutch and English, with negation ("no shared kitchen", "pas de colocation", "non meublé" do not count). A flat is either whole or shared: a shared kitchen, bathroom, shower or toilet, or "room for rent" / "private room", means shared. Shared laundry is fine and only gets a grey tag; a machine connection is not a machine. Hover over a tag to see the phrase it came from, or open "read the description" on a card to see the text with the key phrases marked.</p>
<h3 style="margin-top:8px">NEW tag</h3><p class="sub" style="margin:2px 0">Put online in the last __NEWDAYS__ days. Fresh ads are answered fastest, so contact those first.</p></div>
</div></details>
<div id="fu"></div>
<h2>Contact now <span class="sub">(best 10 you have not contacted yet: newest first, then text-checked, then best score)</span> <span data-h="contact"></span></h2><div id="short"></div>
<h2>All listings <span data-h="cards"></span></h2>
<div class="sub">Quick views <span data-h="views"></span></div><div class="views" id="views"></div>
<details class="filters" open><summary>Filters <span class="sub" id="fsum"></span> <span data-h="filters"></span></summary>
<div class="fgrid">
 <label class="wide">Search <span data-h="q"></span><input id="f_q" type="search" placeholder="street, area, agency, any word from the description"></label>
 <label>Price per month, € (from – to) <span data-h="price"></span><span class="pair"><input id="f_pmin" type="number" step="50" placeholder="min"><input id="f_pmax" type="number" step="50" placeholder="max"></span></label>
 <label>Bedrooms <span data-h="beds"></span><select id="f_beds"><option value="any">any</option><option value="0">studio</option><option value="1">1</option><option value="2">2 or more</option></select></label>
 <label>Min size (m²) <span data-h="m2"></span><input id="f_m2" type="number" step="5"></label>
 <label>Max commute (min) <span data-h="commute"></span><input id="f_commute" type="number" step="5"></label>
 <label>Min score <span data-h="score"></span><input id="f_score" type="number" step="5"></label>
 <label>Min value points <span data-h="value"></span><input id="f_value" type="number" step="5"></label>
 <label>Real cost up to, € <span data-h="eff"></span><input id="f_eff" type="number" step="50"></label>
 <label>Free by <span data-h="avail"></span><input id="f_avail" type="date"></label>
 <label>Updated within (days) <span data-h="upd"></span><input id="f_upd" type="number" min="1" step="1"></label>
 <label>My status <span data-h="status"></span><select id="f_status"><option value="">all</option><option value="todo">not contacted yet</option><option value="active">contacted / replied / visit / applied</option><option value="rejected">rejected</option></select></label>
 <label>Area <span data-h="area"></span><select id="f_area" multiple size="5"></select></label>
 <fieldset class="cols"><legend>Source <span data-h="src"></span></legend><div id="f_src"></div></fieldset>
 <fieldset class="cols"><legend>Must have <span data-h="must"></span></legend><div id="f_flags"></div></fieldset>
 <fieldset class="cols"><legend>Hide <span data-h="hide"></span></legend><div><label><input type="checkbox" id="f_good"> deal-breakers and over budget <span data-h="h_good"></span></label>
  <label><input type="checkbox" id="f_gone"> possibly taken <span data-h="h_gone"></span></label><label><input type="checkbox" id="f_rej"> ones I rejected <span data-h="h_rej"></span></label></div></fieldset>
</div><div class="sub">Listings with an unknown size or commute are kept when you filter by size or commute.</div></details>
<div class="bar"><label>Sort by <span data-h="sort"></span> <select id="sort"><option value="score">best score</option><option value="total">price</option><option value="minutes">commute</option><option value="m2">size</option><option value="value">value points</option><option value="effective">real monthly cost</option><option value="ppm2">real price per m²</option><option value="newest">newest added</option><option value="updated">recently updated</option><option value="avail">available soonest</option><option value="beds">bedrooms</option></select></label>
<button id="dir"></button><button id="reset">Reset filters</button><span class="sub" id="count"></span></div>
<div id="list"></div>
<div style="text-align:center;margin:16px 0 28px"><button id="more" class="primary" style="display:none;padding:10px 26px;font-size:14px">Show 50 more</button> <button id="moreAll" style="display:none;padding:10px 18px;font-size:14px">Show all</button>
 <div class="sub" id="moreNote" style="margin-top:6px"></div></div><div id="sentinel" style="height:1px"></div></div>
<div id="markedview"><h2>★ Marked flats <span class="sub" id="mcount"></span> <span data-h="marked"></span></h2>
 <div class="bar"><label>Sort by <select id="msort"><option value="recent">recently marked</option><option value="score">best score</option><option value="value">best value</option><option value="total">cheapest</option></select></label></div>
 <div id="mlist"></div></div><div id="mapview"><h2>🗺 Map <span class="sub" id="mapcount"></span> <span data-h="map"></span></h2>
 <div class="bar"><label>Colour pins by <select id="mColor"><option value="score">match score</option><option value="value">value points</option></select></label>
  <label><input type="checkbox" id="mOnlyMarked"> only ★ marked</label><label><input type="checkbox" id="mApprox" checked> include approximate positions</label>
  <span class="sub">Shows the flats that match your filters on the Listings tab.</span></div>
 <div id="map" style="height:68vh;min-height:380px;border:1px solid var(--line);border-radius:10px"></div></div>__FUNHTML____UXHTML__<div id="toast"></div>
<script>
if(window.FF_CLOUD)document.body.classList.add('cloud');         // the shared copy: no scraping, settings or adding links here
const FOUND=__FOUND__,SETUP_NEEDED=__SETUP__,FUC=__FOLLOW__,HEALTH=__HEALTH__,D=__DATA__,ST=__STATUSES__,B=__BUDGET__,NEWDAYS=__NEWDAYS__,TRAM=__TRAM__;document.getElementById('meta').textContent=D.length+" listings · budget €"+B+" incl. charges · commute = estimate door-to-desk · updated __STAMP__";
let S={},server=false;const q=id=>document.getElementById(id);
const toast=m=>{const t=q('toast');t.textContent=m;t.classList.add('on');setTimeout(()=>t.classList.remove('on'),1800)};
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const st=x=>(S[x.id]||{}).status||'new';
async function load(){try{const r=await fetch('/api/status');if(r.ok){S=await r.json();server=true}}catch(e){}
 if(!server){try{S=JSON.parse(localStorage.getItem('status')||'{}')}catch(e){}}render()}
const nowLocal=()=>{const d=new Date();return new Date(d-d.getTimezoneOffset()*6e4).toISOString().slice(0,16)};
async function save(id,patch){const prev=S[id]||{},now=nowLocal();let p={...patch};
 if(patch.followup){p={fu_at:now,fu_n:(prev.fu_n||0)+1}}else if(patch.status&&patch.status!==prev.status){p.status_at=now}
 S[id]={...prev,...p,at:now};
 if('marked' in patch){S[id].marked=patch.marked;S[id].marked_at=patch.marked?now:null}
 if(patch.wrong===false)delete S[id].wrong;else if(patch.wrong)S[id].wrong={...patch.wrong,at:now};
 if(server){try{await fetch('/api/status',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,...patch})})}catch(e){toast('Could not save (is serve.py running?)')}}
 else{try{localStorage.setItem('status',JSON.stringify(S))}catch(e){}}}
const cls=f=>/shared|no_domicile|students_only|long_only|no_couple|check_scam|wrong_location|far|not_flat|too_late/.test(f)?'bad':/unread|no_text|lease_6m|tiny|stale|agency_abroad|check_registration|ask_lease|maybe_shared|couple_extra|extra_costs_unknown|price_mismatch|deposit_high|late/.test(f)?'warn':/furnished|short_term|domicile_ok|laundry_machine/.test(f)?'good':'';
const SRC={immoweb:['IW','#1b64b8','Immoweb'],immovlan:['IV','#c2410c','Immovlan'],'2ememain':['2M','#a85d00','2ememain'],housinganywhere:['HA','#0b7a75','HousingAnywhere'],spotahome:['SH','#6d4bd0','Spotahome']};
const badge=x=>{const s=SRC[x.source]||[x.source.slice(0,2).toUpperCase(),'#666',x.source];return x.logo?`<img class="src" src="${esc(x.logo)}" alt="${s[2]}" title="${s[2]}">`:`<span class="src" style="background:${s[1]}" title="${s[2]}">${s[0]}</span>`};
const ago=d=>{const n=Math.round((Date.now()-new Date(d+'T12:00:00'))/864e5);return n<=0?'today':n===1?'yesterday':n+' days ago'};
const label={no_text:'no description in the listing',couple_extra:'extra for two people',utilities_excluded:'utilities not included',extra_costs_unknown:'extra costs: amount not stated',price_mismatch:'text and listing disagree on price',deposit_high:'deposit above 2 months',late:'free later than your move-in',too_late:'free too late for you',laundry_machine:'washing machine',shared_laundry:'shared laundry',laundry_hookup:'machine connection only',maybe_shared:'maybe shared: check',ask_lease:'ask: is the stay length OK?',not_flat:'not a flat (storage, parking, office)',check_scam:'suspiciously cheap',wrong_location:'location mismatch: map pin is elsewhere',far:'too far away',stale:'old listing, not updated for weeks',agency_abroad:'agency abroad',midterm:'mid-term platform',check_registration:'ask: address registration',unread:'text not checked',lease_6m:'minimum lease longer than your stay',no_couple:'one person only',long_only:'long lease only',no_domicile:'no registration',check_scam:'suspiciously cheap'};
const DESC={},OPEN=new Set();
document.addEventListener('toggle',async e=>{const d=e.target;if(!d.dataset||!d.dataset.desc)return;const id=d.dataset.desc,body=d.querySelector('.desc-body');
 if(!d.open){OPEN.delete(id);return}OPEN.add(id);if(DESC[id]){body.innerHTML=DESC[id];return}
 try{const r=await fetch('/api/listing?id='+encodeURIComponent(id));const j=await r.json();DESC[id]='<div class="sub" style="margin-bottom:4px"><mark class="hl-bad">deal-breaker</mark> <mark class="hl-warn">check</mark> <mark class="hl-good">good</mark> <mark class="hl-info">info</mark></div>'+j.html;body.innerHTML=DESC[id]}
 catch(err){body.textContent='Open this page through serve.py (http://127.0.0.1:8765/) to read descriptions.'}},true);
const DAY=864e5;
const lastAct=x=>{const s=S[x.id]||{};return Date.parse(s.fu_at||s.status_at||s.at)||null};
const isDue=x=>{const s=S[x.id]||{};if(s.status!=='contacted'||(s.fu_n||0)>=FUC.max)return false;const t=lastAct(x);return !!t&&Date.now()-t>=(s.fu_n?FUC.next:FUC.first)*DAY};
const dueText=x=>{const s=S[x.id]||{},d=Math.floor((Date.now()-lastAct(x))/DAY);return s.fu_n?`follow-up sent ${d} days ago, no reply`:`contacted ${d} days ago, no reply`};
const isMobile=x=>/^\+324\d{8}$/.test(x.phone||'');
const callHint=x=>{if(x.hours&&x.hours!=='anytime')return x.hours;const d=new Date(),h=d.getHours()+d.getMinutes()/60,ok=d.getDay()>=1&&d.getDay()<=5&&((h>=9&&h<12)||(h>=14&&h<17.5));return ok?'good time to call now':'best: weekdays 9:00-12:00 or 14:00-17:30'};
const scoreCls=v=>v>=100?'great':v>=80?'good':v<60?'weak':'';
const scoreWord=v=>v>=100?'excellent':v>=80?'very good':v>=60?'okay':'weak';
const valCls=v=>v>=53?'hi':v>=47?'mid':v<40?'lo':'';
const valWord=v=>v>=53?'excellent':v>=47?'good':v>=40?'average':'below average';
const MON=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const fmtD=d=>{const p=String(d).slice(0,10).split('-');return p.length===3?(+p[2])+' '+MON[+p[1]-1]+' '+p[0]:esc(d)};
function costsHtml(x){const c=x.costs||{},p=[],E=n=>'€'+Math.round(n).toLocaleString('en');
 if(c.monthly_extra)p.push(`<span class="warnc" title="Monthly costs on top of the rent, from the listing data: ${esc(Object.entries(c.monthly_parts||{}).map(([k,v])=>k+' €'+v).join(', '))}"><b>+${E(c.monthly_extra)}/month</b> extras (${esc(Object.entries(c.monthly_parts||{}).map(([k,v])=>k+' '+v).join(', '))})</span>`);
 else if(c.util_est)p.push(`<span title="The listing says utilities are not included and gives no figure. This is an estimate (editable in config.json)."><b>+${E(c.util_est)}/month</b> utilities (estimate)</span>`);
 if(c.couple)p.push(`<span class="warnc" title="${esc((x.ev&&x.ev.couple_extra)||'')}"><b>+${E(c.couple)}/month</b> for two people (text)</span>`);
 if(c.unknown_extra)p.push(`<span class="warnc" title="${esc((x.ev&&x.ev.extra_costs_unknown)||'')}">other monthly costs, amount not stated (estimate +${E(c.unknown_extra)})</span>`);
 if(c.deposit)p.push(`<span class="${c.deposit_months>2.05?'warnc':''}" title="${c.deposit_src==='listing'?'From the listing data.':'From the description: '+esc((x.ev&&x.ev.deposit)||'')} The Brussels cap is 2 months of rent."><b>deposit ${E(c.deposit)}</b>${c.deposit_months?' ('+c.deposit_months+' months)':''}</span>`);
 if(c.fee_exact)p.push(`<span class="warnc" title="From the listing data of the platform."><b>fees ${E(c.fees_once)} once</b> (platform ${E(c.platform_fee)}${c.admin_fee?' + admin '+E(c.admin_fee):''})</span>`);
 else if(c.one_off_text)p.push(`<span class="warnc"><b>fees ${E(c.one_off_text)}</b> once (text)</span>`);
 if(c.min_stay)p.push(`<span title="Minimum${c.max_stay?' and maximum':''} stay from the listing data.">stay ${c.min_stay}${c.max_stay?'–'+c.max_stay:'+'} months</span>`);
 if(c.couples_ok===true)p.push('<span>couples OK</span>');
 return p.length?`<div class="costs">${p.join('')}</div>`:''}
const starBtn=x=>{const m=!!(S[x.id]||{}).marked;return `<button class="starbig${m?' on':''}" data-mark="${x.id}" title="${m?'Marked. Press to unmark.':'Mark this flat: it appears in the ★ Marked tab.'}"><span class="g">${m?'★':'☆'}</span><span class="w">${m?'marked':'mark'}</span></button>`};
const eur=n=>'€'+Math.round(n).toLocaleString('en');
const valTip=x=>{const p=x.vparts||{},e=x.extras||{};return `Value points ${x.value}/100 = cost ${p.cost}/40 + size ${p.size}/15 + layout ${p.layout}/10 + commute ${p.commute}/15 + included ${p.included}/15 + energy ${p.energy}/5. Size: ${x.m2?x.m2+' m² = '+x.m2pp+' m² per person':'unknown'}; bedrooms: ${x.beds??'unknown'}. Real monthly cost ${eur(x.effective)} = rent+charges ${eur(x.total)}${e.utilities?` + utilities ${eur(e.utilities)}`:''}${e.furniture?` + furniture/linen ${eur(e.furniture)}`:''}${e.fee_once?` + platform fee ${eur(e.fee_once)} once (${eur(e.fee_per_month)}/month over your stay)`:''}${x.ppm2?`. Real price per m²: €${x.ppm2}`:''}.`};
const SRCNAME={immoweb:'Immoweb',immovlan:'Immovlan','2ememain':'2ememain',housinganywhere:'HousingAnywhere',spotahome:'Spotahome'};
function renderHealth(){const el=q('health');if(!el)return;if(SETUP_NEEDED){el.innerHTML='<div class="healthbar" style="background:var(--ok);color:var(--okfg)">👋 <b>Welcome.</b> Answer a few questions so the messages carry your name and the search fits you: <a href="/setup"><b>start the setup (2 minutes)</b></a></div>';return}const bad=Object.entries((HEALTH.sources||{})).filter(([k,v])=>v.status!=='ok'),key='hide:'+(HEALTH.at||'');let hidden=false;try{hidden=sessionStorage.getItem(key)==='1'}catch(e){}
 if(!bad.length||hidden){el.innerHTML='';return}
 el.innerHTML=bad.map(([k,v])=>`<div class="healthbar">⚠ <b>${esc(SRCNAME[k]||k)}</b> ${v.status==='blocked'?'is blocking us right now':v.status==='zero'?'returned 0 results':'returned only '+v.count+' results'}${v.typical?' (usually about '+v.typical+')':''}. ${v.status==='blocked'?'Wait a day before running again.':'The site may have changed its pages, so this tool may be broken for it.'} Its listings were not refreshed in the last run (${esc((HEALTH.at||'').replace('T',' '))}).</div>`).join('')+'<button id="healthX" class="sub">hide until the next run</button>';
 q('healthX').onclick=()=>{try{sessionStorage.setItem(key,'1')}catch(e){}renderHealth()}}
const agoDT=d=>{if(!d)return 'unknown';const m=Math.round((Date.now()-Date.parse(d.length<=10?d+'T12:00':d))/6e4);return m<2?'just now':m<90?m+' min ago':m<2880?Math.round(m/60)+' h ago':Math.round(m/1440)+' days ago'};
const freshHtml=x=>`<span class="sub" title="When this tool last saw the listing in a search, and when its own page was last opened and read.">seen ${agoDT(x.seen_at||x.last_seen)}${x.read_at?' · page read '+agoDT(x.read_at):x.verified?'':' · page not read yet'} ·</span> `;
const goneWhy=x=>`possibly taken: missing from the last ${x.missed||2} searches (last seen ${agoDT(x.seen_at||x.last_seen)}). Open the original to check.`;
let MAIL={},MAILSIG='';
const nameOf=f=>(String(f||'').split('<')[0].replace(/"/g,'').trim()||String(f||''));
const agoT=d=>{const m=Math.round((Date.now()-Date.parse(d))/6e4);return m<2?'just now':m<90?m+' min ago':m<2880?Math.round(m/60)+' h ago':Math.round(m/1440)+' days ago'};
const gmailSubject=x=>({fr:'Demande de visite – ',nl:'Bezichtiging aanvragen – ',en:'Viewing request – '}[x.lang]||'Viewing request – ')+(x.addr||'');
const gmailUrl=x=>'https://mail.google.com/mail/?view=cm&fs=1&su='+encodeURIComponent(gmailSubject(x))+'&body='+encodeURIComponent((x.msg&&x.msg[x.lang])||'');
const mailHtml=x=>{const m=MAIL[x.id];if(!m)return '';let h='';
 if(m.last){const l=m.last;h+=`<div class="mailnote">✉ <b>${m['in']} ${m['in']>1?'replies':'reply'}</b> · last from ${esc(nameOf(l.from))}, ${agoT(l.date)}: “${esc(l.snippet)}” <a href="https://mail.google.com/mail/u/0/#all/${esc(l.thread)}" target="_blank" rel="noopener">open in Gmail</a></div>`;
  if(l.scam)h+=`<div class="mailnote" style="background:var(--bad);color:var(--badfg)">⚠ <b>spam</b></div>`;}
 else if(m.out)h+=`<div class="mailnote sub">✉ you wrote, no reply yet</div>`;
 (m.maybe||[]).slice(0,2).forEach(r=>{h+=`<div class="mailnote maybe">✉ possible reply from ${esc(nameOf(r.from))} (same agency, maybe another flat): “${esc(r.snippet)}” <button data-mdec="1" data-mid="${esc(r.id)}" data-lid="${x.id}">it is this flat</button><button data-mdec="0" data-mid="${esc(r.id)}" data-lid="${x.id}">not this flat</button> <a href="https://mail.google.com/mail/u/0/#all/${esc(r.thread)}" target="_blank" rel="noopener">open</a></div>`});
 return h};
async function loadMail(){if(window.FF_CLOUD)return;try{const r=await fetch('/api/mail');if(!r.ok)return;const j=await r.json(),sig=JSON.stringify(j.mail);if(sig!==MAILSIG){MAILSIG=sig;MAIL=j.mail||{};render()}}catch(e){}}
function card(x){const s=st(x),n=(S[x.id]||{}).note||'';return `<div class="card st-${s}${x.gone?' gone':''}"><div class="score ${scoreCls(x.score)}" title="Match score ${x.score}: ${scoreWord(x.score)} (100+ excellent, 80+ very good, 60+ okay, under 60 weak)">${x.score}<span class="val ${valCls(x.value)}" title="${esc(valTip(x))} Rating: ${valWord(x.value)} (53+ excellent, 47+ good, 40+ average).">value ${x.value}</span>${starBtn(x)}</div>
 <div>${badge(x)}<a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a>${x.new?` <span class="tag new" title="${esc(x.added_how==='created'?'Put online on '+x.added:x.added_how==='updated'?'Last updated on '+x.added+' (this site does not show the creation date, so this is approximate)':'First seen by this tool on '+x.added)}">NEW · ${ago(x.added)}</span>`:''}${x.gone?` <span class="tag bad" title="${esc(goneWhy(x))}">${esc(goneWhy(x))}</span> <a class="btn" href="${esc(x.url)}" target="_blank" rel="noopener">check the original ↗</a>`:''}${x.manual?' <span class="tag manual" title="You added this listing by link, so it stays in your list and is never hidden or marked taken.">manually added</span>':''}${(S[x.id]||{}).wrong?' <span class="tag wrongpill" title="You reported something on this card as wrong. The mark stays until you remove it.">⚑ marked wrong</span>':''}
 <div class="sub">${esc(x.addr)} · ${esc(x.agency)} · ${x.source}${x.similar?` · <b>+${x.similar} similar unit${x.similar>1?'s':''} in the same building</b>`:''}${x.also.map(u=>` · <a href="${esc(u)}" target="_blank" rel="noopener">also listed here</a>`).join('')}</div>
 ${x.summary?`<div class="ai">${esc(x.summary)}</div>`:''}
 ${whyHtml(x)}
 ${hitHtml(x)}
 ${x.verified?`<details class="desc" data-desc="${x.id}"${OPEN.has(x.id)?' open':''}><summary>read the description (key phrases marked)</summary><div class="desc-body">${DESC[x.id]||'loading…'}</div></details>`:''}
 <div>${x.flags.includes('stay_ok')?`<span class="tag stay" title="The listing text says short stays are accepted or the minimum lease fits your stay. Still confirm the length with the landlord.">✓ SHORT STAY OK</span>`:''}${x.flags.filter(f=>f!=='stay_ok'&&f!=='short_term').map(f=>`<span class="tag ${cls(f)}" title="${esc((TAGHINT[f]||'')+(x.ev&&x.ev[f]?' Found in the text: “'+x.ev[f]+'”':''))}">${esc(label[f]||f.replace('_',' '))}</span>`).join('')}${x.lease?`<span class="tag ${x.lease>5?'warn':''}">min lease ${x.lease} mo</span>`:''}</div>${costsHtml(x)}</div>
 <div class="price">€${x.total}<div class="sub">${x.rent}+${x.charges}</div>${x.effective&&x.effective-x.total>=20?`<div class="sub" title="${esc(valTip(x))}" style="cursor:help">real ≈ ${eur(x.effective)}/mo</div>`:''}${x.fee_range?`<div class="sub" style="color:var(--warnfg)" title="${esc(x.fee_note)}">fee ${eur(x.fee_range[0])}–${eur(x.fee_range[1])} once (assumed)</div>`:''}${x.upfront?`<div class="sub" title="Deposit + first month + extras + one-off fees: the cash you need to move in.">upfront ≈ ${eur(x.upfront)}</div>`:''}<div class="sub" title="${x.m2?(x.m2pp+' m² per person'+(x.m2_src?'. Size taken from the description.':'')):'Size: the seller did not give it.'} ${x.beds==null?'Bedrooms: the seller did not give it.':(x.beds_src==='text'?'Bedrooms taken from the description.':x.beds_src==='rooms'?'The listing data says one room, so this is a studio.':'')}">${x.beds===0?'studio':(x.beds??'? bd')+(x.beds==null?'':' bd')}${x.beds_src?'*':''} · ${x.m2??'?'} m²${x.m2_src?'*':''}${x.ppm2?` · €${x.ppm2}/m²`:''}</div></div>
 <div class="row2">${freshHtml(x)}<span class="sub">~${x.minutes??'?'} min (${esc(x.how)}) · ${x.avail?'free from '+fmtD(x.avail):'free: not stated'} · ${x.added?(x.added_how==='created'?'added ':x.added_how==='updated'?'updated ':'first seen ')+ago(x.added):'date unknown'}${x.views!=null?` · ${x.views} views, ${x.saves||0} saved`:''}${x.epc?' · EPC '+esc(x.epc):''}</span>
 ${x.phone?`<a href="tel:${esc(x.phone)}" title="Typical agency office hours; check the agency. Calling in the morning usually gets a visit slot before the email senders.">call ${esc(x.phone)}</a><span class="sub"${callHint(x).startsWith('good')?' style="color:var(--goodfg)"':''}>${esc(callHint(x))}</span>`:''}
 ${/^https?:/.test(x.website)?`<a href="${esc(x.website)}" target="_blank" rel="noopener" class="sub">agency site</a>`:''}
 <button data-id="${x.id}" data-l="${x.lang}">copy message (${x.lang.toUpperCase()})</button>
 ${['fr','nl','en'].filter(l=>l!==x.lang).map(l=>`<button data-id="${x.id}" data-l="${l}">${l.toUpperCase()}</button>`).join('')}
 <a class="btn" href="${gmailUrl(x)}" target="_blank" rel="noopener" data-gm="${x.id}" title="Opens a Gmail compose window with the message and a normal subject (the address). Add the agency's email address and send. Replies to it are found automatically once Gmail is linked (control panel).">✉ Gmail</a>
 ${isMobile(x)?`<a class="btn wa" href="https://wa.me/${x.phone.replace(/\D/g,'')}" target="_blank" rel="noopener" data-wa="${x.id}" title="Copies the message first, then opens a WhatsApp chat with ${esc(x.phone)}. Paste it and press send.">WhatsApp</a>`:''}
 ${['contacted','replied','visit','applied'].includes(s)&&!window.FF_CLOUD&&!(FOUND&&FOUND.on)?`<button data-found="${x.id}" title="This is the flat you take: pauses searching and reminders">🏠 this is the one</button>`:''}
 ${isDue(x)?`<span class="tag warn" title="No answer yet. A short reminder after 2 days often gets a reply.">follow-up due: ${esc(dueText(x))}</span><button data-fu="${x.id}" data-l="${x.lang}">copy follow-up (${x.lang.toUpperCase()})</button>${['fr','nl','en'].filter(l=>l!==x.lang).map(l=>`<button data-fu="${x.id}" data-l="${l}">${l.toUpperCase()}</button>`).join('')}`:''}
 ${(S[x.id]||{}).wrong?`<button data-unwrong="${x.id}" title="Remove the wrong mark (do this when the card looks right to you)">remove wrong mark</button>`:`<button data-wrong="${x.id}" title="Something on this card is wrong (a tag, the price, the location...). Mark it and say what.">⚑ report wrong</button>`}
 ${['immoweb','immovlan','spotahome'].includes(x.source)?`<button data-recheck="${x.id}" title="Read the listing page again and re-analyse it. A wrong mark stays until you remove it.">↻ recheck</button>`:''}
 ${x.manual?`<button data-rmmanual="${x.id}" title="Remove this listing that you added by link">remove</button>`:''}
 ${(S[x.id]||{}).by?`<span class="sub" title="Who last changed the status, mark or note">by ${esc(S[x.id].by)}</span>`:''}
 <select data-st="${x.id}">${ST.map(o=>`<option ${o===s?'selected':''}>${o}</option>`).join('')}</select></div>
 ${(S[x.id]||{}).wrong?`<div class="wrongnote">⚑ You marked this wrong${S[x.id].wrong.note?': “'+esc(S[x.id].wrong.note)+'”':''}. Tags at that moment: ${esc((S[x.id].wrong.flags||[]).join(', ')||'none')}. ${x.rechecked?'Rechecked at '+esc(x.rechecked.replace('T',' ').slice(0,16))+' (the tags above are the new ones). ':'Not rechecked yet. '}Press "remove wrong mark" when it looks right.</div>`:''}
 ${mailHtml(x)}
 ${schedHtml(x)}
 ${histHtml(x)}
 <textarea class="note" data-note="${x.id}" placeholder="notes: who you spoke to, visit time, questions...">${esc(n)}</textarea></div>`}
const HINTS={add:'Paste the address of one listing and the tool opens that page, reads it (price, size, text, dates), scores it with Gemini and adds it to your list with a purple "manually added" pill. It is never hidden or marked taken, and you can remove it again.',
marked:'Flats you marked with the star. They stay here whatever the filters say, with your status and notes.',
t_marked:'Flats you marked with the star.',t_manual:'Listings you added by link.',t_wrong:'Listings where you reported that a tag or number is wrong. Each one stays marked until you remove the mark, even after a recheck.',filters:'Narrow the list. Everything is optional; empty boxes mean "any". Your choices are remembered in this browser.',
q:'Type any words. They are matched against the street, area, agency, the Gemini summary, the source and the tags.',
price:'Rent + charges per month as the listing shows it. Platform fees are not in this number, see "Real cost" for that.',
beds:'Number of bedrooms. A studio has the bed in the living room. If you pick a number, listings with an unknown bedroom count are hidden.',
m2:'Living area in m². Listings that do not show a size are kept, so you do not lose them by accident.',
commute:'Estimated door-to-door minutes to EUROCONTROL (walking, tram 62, bus or train). An estimate, not a timetable. Unknown positions are kept.',
score:'Match score: how well a flat fits you. It rewards low price, short commute, furnished, short-stay OK, registration allowed, and subtracts points for risks. 60 to 79 is okay, 80 to 99 very good, 100 or more excellent.',
value:'Value points (0 to 100): price versus what you get. Cost 40, size 15, layout 10, commute 15, included extras 15, energy rating 5. 50 or more is already a very good deal (53+ excellent, 47+ good, under 40 below average). Hover a card\'s "value" number for the breakdown.',
eff:'Real monthly cost over your whole stay: rent + charges + utilities if excluded + furniture allowance if unfurnished + the platform fee spread over the months. Edit the assumptions in the control panel.',
avail:'Only flats free on or before this date. Flats with an unknown date are kept.',
upd:'Only listings changed in the last N days. Listings that nobody has updated for weeks are often already rented.',
status:'Your own progress on each flat (set it on the card). "Not contacted yet" is your to-do list.',
area:'Postal code and commune with the number of listings. Hold ctrl (or cmd on Mac) to pick several areas.',
src:'The website a listing comes from. Tick several to show only those.',
must:'Show only flats that have ALL the ticked tags.',
hide:'Switch these off to see everything, including flats that have a deal-breaker.',
h_good:'Hides flats that are over your budget or have a deal-breaker: no address registration, one person only, students only, long lease only, shared room, wrong map location, too far, scam signs.',
h_gone:'Hides listings that were not found in the last two searches. They are probably rented. Flats you already contacted stay visible.',
h_rej:'Hides flats you set to "rejected".',
sort:'Order of the list. The arrow button reverses it. Listings with an unknown value for that sort go to the end.',
views:'One click sets the filters and sorting for a common search. You can change anything afterwards, and "Reset filters" clears all.',
cards:'Left number: match score (higher = fits you better). Under it: value points (hover for the breakdown). "real ≈" is the monthly cost including fees. The small logo is the source website.',
fu:'Flats you contacted 2 or more days ago that have not answered. Press "copy follow-up", paste it where you wrote the first time, and the reminder resets (a second reminder comes 3 days later, then it stops).',
contact:'The 10 best good flats you have not contacted yet, fresh ads first (landlords answer the first replies), then text-checked ones, then by score. Press "copy message", paste it into the listing\'s contact form, and the flat moves to "contacted".',
how:'Explains the two numbers on each card: the match score and the value points, and what counts for or against a flat. Close it with the arrow and it stays closed.',
map:'Every flat that matches your filters on the Listings tab, as a pin. Colour = match score or value points (your choice): green best, blue very good, orange okay, red weak. Gold ring = marked ★. Pale dashed pins only have an approximate position (the area centre) because the listing gave no exact location. Black ring = EUROCONTROL, grey dots = tram 62 stops. Click a pin for the details and to mark it.',
stats:'Numbers about all listings and your progress. Close it with the arrow and it stays closed.',
t_found:'Every listing stored from all websites, including ones your filters hide.',t_live:'Listings still seen in recent searches (not "possibly taken").',
t_good:'In budget and none of the deal-breakers: no registration, one person only, students only, long lease only, shared, wrong map location, too far, scam signs.',
t_new:'Listings put online in the last few days (you can change how many in the control panel). Fresh ads get answers fastest, so contact these first. Based on the site\'s creation date where it shows one, otherwise on the last update date.',t_todo:'Good flats you have not messaged yet. This is your to-do list.',t_contacted:'Flats you set to contacted, replied, visit or applied.',
t_replied:'Flats where the landlord answered.',t_visit:'Flats with a visit planned.',t_applied:'Flats you applied for.',t_rejected:'Flats you ruled out.',
t_rate:'(replied + visits + applied) divided by contacted. Low numbers mean: message more flats, faster.',
t_read:'Listings whose full page was opened and read by the scraper. Unread ones may hide a problem such as a 12-month minimum.',
t_ai:'Listings whose description Gemini analysed (minimum lease, registration, one-person rules, summary).',
t_stay:'Good flats with the SHORT STAY OK tag: the text says short stays are fine, or the minimum lease fits your stay.',
t_ask:'Text was read but says nothing about lease length. Worth asking if your stay length is OK.',t_gone:'Not found in the last two searches. Probably rented: call to confirm.',
t_min:'Cheapest good flat (rent + charges).',t_med:'Middle price of the good flats (rent + charges).',t_effmed:'Middle real monthly cost of the good flats, including platform fees, utilities and furniture allowance.',t_best:'Highest value points among the good flats.'};
const TAGHINT={no_text:'The page was read, but the seller wrote no description. Only the listing data (price, size, rooms) can be trusted: ask before you count on anything else.',couple_extra:'The listing charges an extra monthly amount for a second person or a couple. It is already counted in the real cost.',utilities_excluded:'The rent does not include utilities such as water, electricity, gas or internet.',extra_costs_unknown:'The text mentions other monthly costs but gives no amount. A small estimate is counted in the real cost: ask the landlord.',price_mismatch:'The description quotes a different rent than the listing data. Trust the listing data, but ask.',deposit_high:'The deposit is more than 2 months of rent. In Brussels the legal cap for a normal lease is 2 months.',late:'Free more than 2 weeks after your move-in date.',too_late:'Free long after you need it (see the setting in the control panel), so it is dropped from the good list.',laundry_machine:'There is a washing machine inside the flat (not shared).',shared_laundry:'The laundry room or machine is shared with other residents. That is normal for a whole flat, just so you know.',laundry_hookup:'Only a connection for a washing machine: you would have to bring or buy the machine.',maybe_shared:'The text mentions a room that may be rented separately. Check that you get the whole flat.',furnished:'The listing says it is furnished.',fridge:'There is a fridge or a fully equipped kitchen.',domicile_ok:'The text says you can register your address (domiciliation) here.',
ask_lease:'The text was read but does not mention lease length. Ask whether your stay length is OK.',unread:'The scraper has not opened this listing page yet, so red flags may be hidden. It is read in a later run.',
lease_6m:'The minimum lease is longer than your stay. Possible, but you would have to negotiate.',tiny:'Under the minimum size you set. Tight for two people.',stale:'Not updated for weeks, so probably already rented.',
agency_abroad:'The seller\'s address is in another country. Be careful.',check_registration:'Platform listings rarely say whether you can register your address. Ask before you book.',midterm:'A platform made for stays of a few months. Usually fees apply.',
bills_incl:'Bills such as water, electricity or internet seem to be included in the rent.',wrong_location:'The listing\'s map position is far from the place it names.',far:'More than 25 km from EUROCONTROL.',
no_domicile:'The listing says you cannot register your address. That is a problem for the commune.',no_couple:'The listing says one person only.',long_only:'The minimum lease is 9 months or more.',students_only:'Only for students.',
shared:'A room in a shared flat or co-living, not a whole flat.',check_scam:'Under 550 EUR for a whole flat: usually a scam or not an apartment.',not_flat:'Looks like a storage, parking or office ad.',
stay_ok:'Short stays are accepted or the minimum lease fits your stay.'};
const hintEl=k=>HINTS[k]?`<span class="hint" tabindex="0" data-hint="${esc(HINTS[k])}">?</span>`:'';
function fillHints(root=document){root.querySelectorAll('[data-h]').forEach(e=>{const t=HINTS[e.dataset.h];if(t){e.className='hint';e.tabIndex=0;e.textContent='?';e.dataset.hint=t}})}
const FLAGS=[['manual','Manually added'],['marked','Marked ★'],['wrong','Marked wrong by me'],['laundry_machine','Washing machine in the flat'],['furnished','Furnished'],['stay_ok','Short stay OK'],['domicile_ok','Registration allowed'],['fridge','Fridge / equipped kitchen'],['ask_lease','Ask about lease length'],['verified','Listing text read'],['ai','Checked by Gemini'],['new','New (last '+NEWDAYS+' days)']];
const DEF={q:'',pmin:'',pmax:'',beds:'any',m2:'',commute:'45',score:'',value:'',eff:'',avail:'',upd:'',status:'',area:[],src:[],flags:[],good:true,gone:true,rej:true,since:false,sort:'score',dir:'desc'};
const NATDIR={value:'desc',effective:'asc',score:'desc',total:'asc',minutes:'asc',m2:'desc',ppm2:'asc',newest:'desc',updated:'desc',avail:'asc',beds:'desc'};
const VIEWS=[['Best matches',{}],['Best value',{sort:'value',dir:'desc'}],['Lowest real cost',{sort:'effective',dir:'asc'}],['Cheapest',{sort:'total',dir:'asc'}],['Short stay OK',{flags:['stay_ok']}],['Ask about lease length',{flags:['ask_lease'],sort:'total',dir:'asc'}],['Closest to work',{sort:'minutes',dir:'asc'}],['Furnished up to €1000',{flags:['furnished'],pmax:'1000',sort:'total',dir:'asc'}],['New listings',{flags:['new'],sort:'newest',dir:'desc'}],['Recently updated',{sort:'updated',dir:'desc'}]];
let F={...DEF},LIMIT=50;try{F={...DEF,...JSON.parse(localStorage.getItem('filters')||'{}')}}catch(e){}
const areaKey=x=>((x.postal||'')+' '+(x.locality||'')).trim();
const has=(x,k)=>k==='verified'?x.verified:k==='ai'?x.ai:k==='new'?x.new:k==='manual'?x.manual:k==='marked'?!!(S[x.id]||{}).marked:k==='wrong'?!!(S[x.id]||{}).wrong:x.flags.includes(k);
const ACTIVE=['contacted','replied','visit','applied'];
function matches(x){const s=st(x),n=v=>v===''||v==null?null:+v;
 if(!x.manual){if(F.good&&!x.good)return false;if(F.gone&&x.gone&&!ACTIVE.includes(s))return false;if(F.rej&&s==='rejected'&&F.status!=='rejected')return false}
 if(F.q&&!qmatch(x))return false
 if(n(F.pmin)!=null&&x.total<n(F.pmin))return false;if(n(F.pmax)!=null&&x.total>n(F.pmax))return false;
 if(F.beds!=='any'){if(x.beds==null)return false;if(F.beds==='2'?x.beds<2:x.beds!==+F.beds)return false}
 if(n(F.m2)!=null&&x.m2!=null&&x.m2<n(F.m2))return false;if(n(F.commute)!=null&&x.minutes!=null&&x.minutes>n(F.commute))return false;
 if(n(F.score)!=null&&x.score<n(F.score))return false;if(n(F.value)!=null&&(x.value??0)<n(F.value))return false;if(n(F.eff)!=null&&x.effective!=null&&x.effective>n(F.eff))return false;if(F.avail&&x.avail&&x.avail>F.avail)return false;
 if(n(F.upd)!=null){const d=x.modified||x.first_seen;if(!d||(Date.now()-Date.parse(d))/864e5>n(F.upd))return false}
 if(F.since&&!sinceNew(x))return false;
 if(FOUND&&FOUND.on&&!SHOWARCH&&x.id!==FOUND.lid)return false;
 if(F.src.length&&!F.src.includes(x.source))return false;if(F.area.length&&!F.area.includes(areaKey(x)))return false;
 if(F.flags.some(k=>!has(x,k)))return false;
 if(F.status==='todo'&&s!=='new')return false;if(F.status==='active'&&!ACTIVE.includes(s))return false;if(F.status==='rejected'&&s!=='rejected')return false;return true}
const VAL={value:x=>x.value,effective:x=>x.effective,score:x=>x.score,total:x=>x.total,minutes:x=>x.minutes,m2:x=>x.m2,ppm2:x=>x.ppm2,newest:x=>Date.parse(x.added||x.first_seen)||null,updated:x=>Date.parse(x.modified||x.first_seen)||null,avail:x=>x.avail?Date.parse(x.avail):null,beds:x=>x.beds};
function sorted(L){const f=VAL[F.sort],d=F.dir==='asc'?1:-1;return L.sort((a,b)=>{const x=f(a),y=f(b);if(x==null&&y==null)return b.score-a.score;if(x==null)return 1;if(y==null)return -1;return(x-y)*d||b.score-a.score})}
function buildFilters(){const cnt=(f)=>{const m={};D.forEach(x=>{const k=f(x);m[k]=(m[k]||0)+1});return Object.entries(m).sort((a,b)=>b[1]-a[1])};
 q('f_area').innerHTML=cnt(areaKey).map(([k,n])=>`<option value="${esc(k)}">${esc(k||'unknown')} (${n})</option>`).join('');
 q('f_src').innerHTML=cnt(x=>x.source).map(([k,n])=>`<label><input type="checkbox" data-src="${esc(k)}"> ${badge(D.find(x=>x.source===k))}${esc((SRC[k]||[0,0,k])[2])} (${n})</label>`).join('');
 const FH={verified:HINTS.t_read,ai:HINTS.t_ai,new:HINTS.t_new,...TAGHINT};
 q('f_flags').innerHTML='<div>'+FLAGS.map(([k,l])=>`<label><input type="checkbox" data-flag="${k}"> ${l}${FH[k]?` <span class="hint" tabindex="0" data-hint="${esc(FH[k])}">?</span>`:''}</label>`).join('')+'</div>';
 q('f_src').innerHTML='<div>'+q('f_src').innerHTML+'</div>';
 q('views').innerHTML=VIEWS.map(([l,o],i)=>`<button data-view="${i}">${l}</button>`).join('')}
function syncUI(){const m={q:'f_q',pmin:'f_pmin',pmax:'f_pmax',beds:'f_beds',m2:'f_m2',commute:'f_commute',score:'f_score',value:'f_value',eff:'f_eff',avail:'f_avail',upd:'f_upd',status:'f_status',sort:'sort'};
 for(const k in m)q(m[k]).value=F[k];[...q('f_area').options].forEach(o=>o.selected=F.area.includes(o.value));
 document.querySelectorAll('#f_src input').forEach(i=>i.checked=F.src.includes(i.dataset.src));document.querySelectorAll('#f_flags input').forEach(i=>i.checked=F.flags.includes(i.dataset.flag));
 q('f_good').checked=F.good;q('f_gone').checked=F.gone;q('f_rej').checked=F.rej;q('dir').textContent=F.dir==='asc'?'↑ low to high':'↓ high to low'}
function readUI(){const m={q:'f_q',pmin:'f_pmin',pmax:'f_pmax',beds:'f_beds',m2:'f_m2',commute:'f_commute',score:'f_score',value:'f_value',eff:'f_eff',avail:'f_avail',upd:'f_upd',status:'f_status'};
 for(const k in m)F[k]=q(m[k]).value;F.area=[...q('f_area').selectedOptions].map(o=>o.value);
 F.src=[...document.querySelectorAll('#f_src input:checked')].map(i=>i.dataset.src);F.flags=[...document.querySelectorAll('#f_flags input:checked')].map(i=>i.dataset.flag);
 F.good=q('f_good').checked;F.gone=q('f_gone').checked;F.rej=q('f_rej').checked}
function renderStats(){const live=D.filter(x=>!x.gone),good=live.filter(x=>x.good),S2=k=>D.filter(x=>st(x)===k).length;
 const contacted=D.filter(x=>st(x)!=='new'&&st(x)!=='rejected').length,replied=S2('replied')+S2('visit')+S2('applied');
 const med=a=>{if(!a.length)return null;const s=[...a].sort((x,y)=>x-y),m=s.length>>1;return s.length%2?s[m]:(s[m-1]+s[m])/2};
 const prices=good.map(x=>x.total),eff=good.map(x=>x.effective).filter(Boolean),pct=(a,b)=>b?Math.round(100*a/b)+'%':'–';
 const T=(n,l,c='',h='')=>`<div class="tile ${c}"><b>${n}</b><span>${l}</span>${h?hintEl(h):''}</div>`;
 const tbl=(title,rows)=>`<div><h3>${title}</h3><table>${rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td></tr>`).join('')}</table></div>`;
 const bySrc={},byArea={};live.forEach(x=>{(bySrc[x.source]=bySrc[x.source]||[0,0])[0]++;if(x.good)bySrc[x.source][1]++;const a=areaKey(x)||'unknown';(byArea[a]=byArea[a]||[0,0])[0]++;if(x.good)byArea[a][1]++});
 const srcRows=Object.entries(bySrc).sort((a,b)=>b[1][1]-a[1][1]).map(([k,v])=>[`${badge(D.find(x=>x.source===k))}${esc((SRC[k]||[0,0,k])[2])}`,`${v[1]} good / ${v[0]}`]);
 const areaRows=Object.entries(byArea).sort((a,b)=>b[1][1]-a[1][1]).slice(0,8).map(([k,v])=>[esc(k),`${v[1]} good / ${v[0]}`]);
 q('statline').textContent=`· ${live.length} found · ${good.length} good · ${S2('new')?'':''}${contacted} contacted`;
 q('statbody').innerHTML=`<div class="tiles">${T(D.length,'listings found in total','','t_found')}${T(live.length,'live (not possibly taken)','','t_live')}${T(good.length,'good matches (in budget, no red flag)','acc','t_good')}${T(D.filter(x=>x.new).length,'added in the last '+NEWDAYS+' days','acc','t_new')}
 ${T(good.filter(x=>st(x)==='new').length,'good ones not contacted yet','acc','t_todo')}${T(contacted,'contacted','','t_contacted')}${T(S2('replied'),'replied','','t_replied')}${T(S2('visit'),'visits planned','','t_visit')}${T(S2('applied'),'applied','','t_applied')}${T(S2('rejected'),'rejected','','t_rejected')}${T(pct(replied,contacted),'reply rate','','t_rate')}
 ${T(live.filter(x=>x.verified).length+' / '+live.length,'listing text read','','t_read')}${T(live.filter(x=>x.ai).length,'checked by Gemini','','t_ai')}${T(D.filter(x=>(S[x.id]||{}).marked).length,'marked ★','acc','t_marked')}${T(D.filter(x=>x.manual).length,'added by link','','t_manual')}${T(D.filter(x=>(S[x.id]||{}).wrong).length,'marked wrong','','t_wrong')}${T(good.filter(x=>x.flags.includes('stay_ok')).length,'short stay OK (good ones)','acc','t_stay')}${T(good.filter(x=>x.flags.includes('ask_lease')).length,'ask about lease length','','t_ask')}${T(D.filter(x=>x.gone).length,'possibly taken','','t_gone')}
 ${T(prices.length?eur(Math.min(...prices)):'–','cheapest good flat','','t_min')}${T(prices.length?eur(med(prices)):'–','median good flat','','t_med')}${T(eff.length?eur(med(eff)):'–','median real cost (with fees)','','t_effmed')}${T(good.length?Math.max(...good.map(x=>x.value||0)):'–','best value points','','t_best')}</div>
 <div class="lists">${tbl('By source (good / found)',srcRows)}${tbl('By area, top 8 (good / found)',areaRows)}</div>`}
const viewFromHash=()=>location.hash==='#marked'?'marked':location.hash==='#map'?'map':location.hash==='#today'?'today':location.hash==='#visits'?'visits':location.hash==='#next'?'next':location.hash==='#pipeline'?'pipeline':'all';
let view=viewFromHash();
let MAP=null,LAYER=null,mapFitted=false;
const EURO=[50.88347,4.43077];
const pinColor=(x,mode)=>mode==='value'?(x.value>=53?'#2ea043':x.value>=47?'#2f6fed':x.value<40?'#d1242f':'#e08a00'):(x.score>=100?'#2ea043':x.score>=80?'#2f6fed':x.score<60?'#d1242f':'#e08a00');
function popupHtml(x){const sm=(S[x.id]||{}).marked,keep=['stay_ok','furnished','laundry_machine','shared_laundry','deposit_high','couple_extra','late','too_late'];
 return `<div style="min-width:210px;font:13px/1.45 -apple-system,system-ui,sans-serif"><b><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a></b><br>${esc(x.addr)}<br><b>€${x.total}</b>${x.effective>x.total+19?' · real ≈ €'+x.effective:''} · ${x.beds===0?'studio':(x.beds??'?')+' bd'} · ${x.m2??'?'} m²<br>score ${x.score} · value ${x.value} · ~${x.minutes??'?'} min${x.approx?'<br><i>approximate position (area centre)</i>':''}<br>${x.flags.filter(f=>keep.includes(f)).map(f=>esc(label[f]||f.replace('_',' '))).join(' · ')}<div style="margin-top:6px"><button data-mark="${x.id}">${sm?'★ marked':'☆ mark'}</button></div></div>`}
function renderMap(){if(view!=='map')return;const box=q('map');
 if(typeof L==='undefined'){box.innerHTML='<div class="sub" style="padding:18px">The map library could not be loaded. The map needs an internet connection (it loads Leaflet and OpenStreetMap).</div>';return}
 if(!MAP){MAP=L.map('map').setView(EURO,12);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(MAP);
  L.circleMarker(EURO,{radius:10,color:'#000',weight:3,fillColor:'#fff',fillOpacity:1}).addTo(MAP).bindTooltip('EUROCONTROL',{permanent:true,direction:'top'});
  TRAM.forEach(([n,la,lo])=>L.circleMarker([la,lo],{radius:3,color:'#555',weight:1,fillColor:'#999',fillOpacity:.9}).addTo(MAP).bindTooltip('tram 62: '+n));
  const lg=L.control({position:'bottomright'});lg.onAdd=()=>{const d=L.DomUtil.create('div','legend');d.innerHTML='<i style="background:#2ea043"></i>best <i style="background:#2f6fed"></i>very good <i style="background:#e08a00"></i>okay <i style="background:#d1242f"></i>weak<br><span style="color:#a37800">◯ gold ring = marked ★</span><br>pale = approximate position<br>grey dots = tram 62';return d};lg.addTo(MAP)}
 if(LAYER)LAYER.remove();LAYER=L.layerGroup().addTo(MAP);
 const mode=q('mColor').value;let list=D.filter(matches).filter(x=>x.lat!=null);const n0=list.length;
 if(q('mOnlyMarked').checked)list=list.filter(x=>(S[x.id]||{}).marked);if(!q('mApprox').checked)list=list.filter(x=>!x.approx);
 list.sort((a,b)=>a.score-b.score);   // best flats are drawn last, on top
 const pts=[EURO];
 list.forEach(x=>{const mk=(S[x.id]||{}).marked,c=pinColor(x,mode);pts.push([x.lat,x.lon]);
  L.circleMarker([x.lat,x.lon],{radius:mk?10:7,color:mk?'#f5b301':'#fff',weight:mk?3:1.5,fillColor:c,fillOpacity:x.approx?.4:.9,dashArray:x.approx?'3':null}).addTo(LAYER).bindPopup(popupHtml(x))});
 q('mapcount').textContent=`(${list.length} flats on the map · ${D.filter(matches).length-n0} without any position)`;
 setTimeout(()=>{MAP.invalidateSize();if(!mapFitted&&pts.length>1){MAP.fitBounds(pts,{padding:[30,30],maxZoom:14});mapFitted=true}},60)}
function renderMarked(){const M=D.filter(x=>(S[x.id]||{}).marked),k=q('msort').value;
 M.sort((a,b)=>k==='recent'?String((S[b.id]||{}).marked_at||'').localeCompare(String((S[a.id]||{}).marked_at||'')):k==='total'?a.total-b.total:(b[k]??0)-(a[k]??0));
 q('mcount').textContent='('+M.length+')';q('markedCount').textContent=M.length?'('+M.length+')':'';
 q('mlist').innerHTML=M.map(card).join('')||'<div class="sub" style="padding:12px">Nothing marked yet. Press the ☆ on any card to mark it.</div>'}
function showError(err){let b=document.getElementById('err');if(!b){b=document.createElement('div');b.id='err';b.style.cssText='background:#fde8e8;color:#a32020;border:1px solid #a32020;border-radius:8px;padding:8px 12px;margin:8px 0;font-size:13px';document.body.insertBefore(b,document.body.firstChild)}
 b.textContent='⚠ The page hit an error: '+(err&&err.message||err)+'. Reload with Ctrl+Shift+R (Cmd+Shift+R on Mac). If it stays, send me this message.'}
window.addEventListener('error',e=>showError(e.error||e.message));
function render(){try{renderInner()}catch(err){showError(err);console.error(err)}}
function renderInner(){document.body.classList.toggle('nextv',view==='next');document.body.classList.toggle('pipev',view==='pipeline');q('tabNext').classList.toggle('on',view==='next');q('tabPipe').classList.toggle('on',view==='pipeline');if(view==='next')renderNext();if(view==='pipeline')renderPipe();document.body.classList.toggle('visitsv',view==='visits');q('tabVisits').classList.toggle('on',view==='visits');if(view==='visits')renderVisits();document.body.classList.toggle('todayv',view==='today');q('tabToday').classList.toggle('on',view==='today');if(view==='today')renderToday();document.body.classList.toggle('marked',view==='marked');document.body.classList.toggle('mapv',view==='map');q('tabAll').classList.toggle('on',view==='all');q('tabMarked').classList.toggle('on',view==='marked');q('tabMap').classList.toggle('on',view==='map');renderMarked();renderStats();renderMap();const live=D.filter(x=>!x.gone&&x.good),todo=live.filter(x=>st(x)==='new'),c=k=>D.filter(x=>st(x)===k).length,due=D.filter(isDue);
 q('fu').innerHTML=due.length?`<h2 id="fuh" style="color:var(--warnfg)">Follow-ups due (${due.length}) ${hintEl('fu')}</h2>`+due.map(card).join(''):'';
 q('banner').innerHTML=`<b>${todo.length} good flats not contacted yet</b><span class="pill" data-f="todo">show them</span>${due.length?`<span class="pill" data-f="fu" style="border-color:var(--warnfg);color:var(--warnfg)">${due.length} follow-up${due.length>1?'s':''} due</span>`:''}<span class="sub">contacted ${c('contacted')} · replied ${c('replied')} · visits ${c('visit')} · applied ${c('applied')}</span>`;
 const unread=todo.filter(x=>!x.verified).length;
 q('short').innerHTML=(unread?`<div class="sub" style="margin:4px 0">${unread} more good flats are not listed here because their text has not been read yet, so a shared flat or a long lease could hide in them. They are read in the next runs, or press Scrape now with a higher "listing pages read" number.</div>`:'')+todo.filter(x=>x.verified).slice().sort((a,b)=>(b.new-a.new)||(b.verified-a.verified)||(b.score-a.score)).slice(0,10).map(card).join('')||'<div class="sub">Nothing new to contact.</div>';
 const L=sorted(D.filter(matches));q('count').textContent=`${L.length} of ${D.length} listings match · showing ${Math.min(L.length,LIMIT)}`;
 q('list').innerHTML=L.slice(0,LIMIT).map(card).join('')||(D.length?'<div class="empty"><div class="big">🔍</div><b>No listing matches these filters</b>Remove a filter above (the little ✕ buttons) or press <a href="#" data-chip="*" onclick="return false">Clear all</a>.</div>':'<div class="empty"><div class="big">🏠</div><b>No listings yet</b>Open the <a href="/control">Control panel</a> and press <b style="display:inline">Scrape now</b>. The first run takes about 10 minutes. Or try <code>python3 serve.py --demo</code> to see the page with sample listings.</div>');
 const left=L.length-LIMIT;q('more').style.display=q('moreAll').style.display=left>0?'inline-block':'none';
 q('more').textContent=`Show ${Math.min(50,Math.max(left,0))} more (${Math.max(left,0)} left)`;q('moreAll').textContent=`Show all ${L.length}`;q('moreNote').textContent=left>0?'More flats also load by themselves as you scroll down.':(L.length?'That is every flat that matches your filters.':'');
 const n=Object.keys(DEF).filter(k=>!['sort','dir'].includes(k)&&JSON.stringify(F[k])!==JSON.stringify(DEF[k])).length;q('fsum').textContent=n?`· ${n} changed`:''}
function changed(){readUI();LIMIT=50;try{localStorage.setItem('filters',JSON.stringify(F))}catch(e){}render()}
function initFilters(){buildFilters();syncUI();fillHints();
 q('sort').addEventListener('change',()=>{F.sort=q('sort').value;F.dir=NATDIR[F.sort];syncUI();changed()});
 q('dir').onclick=()=>{F.dir=F.dir==='asc'?'desc':'asc';syncUI();changed()};
 q('reset').onclick=()=>{F={...DEF};syncUI();changed()};q('more').onclick=()=>{LIMIT+=50;render()};q('moreAll').onclick=()=>{LIMIT=1e9;render()};
 q('views').addEventListener('click',e=>{const b=e.target.closest('button[data-view]');if(!b)return;F={...DEF,...VIEWS[+b.dataset.view][1]};syncUI();changed()});
 document.querySelector('details.filters').addEventListener('input',changed);document.querySelector('details.filters').addEventListener('change',changed)}
document.addEventListener('click',async e=>{
 if(e.target.dataset.f==='fu'){q('fu').scrollIntoView();return}
 const md=e.target.closest('button[data-mdec]');if(md){try{await postJson('/api/mail/decide',{mid:md.dataset.mid,lid:md.dataset.lid,ok:md.dataset.mdec==='1'});MAILSIG='';await loadMail()}catch(err){toast('⚠ '+err.message)}return}
 const gm=e.target.closest('a[data-gm]');if(gm){const x=D.find(d=>d.id===gm.dataset.gm);if(x)logAct(x.id,'gmail','opened a Gmail draft');if(x&&st(x)==='new'){await save(x.id,{status:'contacted'});render()}return}
 const mk=e.target.closest('button[data-mark]');if(mk){const x=D.find(d=>d.id===mk.dataset.mark);await save(x.id,{marked:!(S[x.id]||{}).marked});render();return}
 const wb=e.target.closest('button[data-wrong]');if(wb){const x=D.find(d=>d.id===wb.dataset.wrong);
  const note=prompt('What is wrong on this card? For example: "it is not shared", "the price is different", "the washing machine is shared". (Cancel = do not mark it)','');
  if(note===null)return;await save(x.id,{wrong:{note:note.slice(0,300),flags:x.flags}});toast('Marked wrong. It stays marked until you remove the mark.');render();return}
 const uw=e.target.closest('button[data-unwrong]');if(uw){await save(uw.dataset.unwrong,{wrong:false});toast('Wrong mark removed');render();return}
 const rc=e.target.closest('button[data-recheck]');if(rc){try{await postJson('/api/recheck',{ids:[rc.dataset.recheck]});afterRun('Rechecking: reading the page again and re-analysing it…')}catch(err){toast('⚠ '+err.message)}return}
 const rm=e.target.closest('button[data-rmmanual]');if(rm){if(!confirm('Remove this listing that you added by link?'))return;try{await postJson('/api/manual/remove',{id:rm.dataset.rmmanual});afterRun('Removed. Rebuilding the page…')}catch(err){toast('⚠ '+err.message)}return}
 const wa=e.target.closest('a[data-wa]');if(wa){const x=D.find(d=>d.id===wa.dataset.wa);try{navigator.clipboard.writeText(x.msg[x.lang])}catch(err){}
  toast('Message copied. Paste it in WhatsApp and press send.');logAct(x.id,'wa','opened WhatsApp with the message');if(st(x)==='new'){await save(x.id,{status:'contacted'});render()}return}
 const fb=e.target.closest('button[data-fu]');if(fb){const x=D.find(d=>d.id===fb.dataset.fu);try{await navigator.clipboard.writeText(x.msg['fu_'+fb.dataset.l]);toast('Follow-up copied ('+fb.dataset.l.toUpperCase()+'). Paste it where you wrote first.');logAct(x.id,'follow','copied the follow-up ('+fb.dataset.l.toUpperCase()+')');await save(x.id,{followup:true});render()}catch(err){toast('Copy failed, select the text by hand')}return}
 if(e.target.dataset.f==='todo'){F={...DEF,status:'todo'};syncUI();changed();q('list').scrollIntoView();return}
 const b=e.target.closest('button[data-id]');if(!b)return;const x=D.find(d=>d.id===b.dataset.id);
 try{await navigator.clipboard.writeText(x.msg[b.dataset.l]);toast('Message copied ('+b.dataset.l.toUpperCase()+') — paste it into the contact form');logAct(x.id,'message','copied the message ('+b.dataset.l.toUpperCase()+')');
 if(st(x)==='new'){await save(x.id,{status:'contacted'});render()}}catch(err){toast('Copy failed — select the text by hand')}});
document.addEventListener('change',async e=>{if(e.target.dataset.st){await save(e.target.dataset.st,{status:e.target.value});render()}
 else if(e.target.dataset.note!==undefined&&e.target.classList.contains('note')){await save(e.target.dataset.note,{note:e.target.value});toast('Note saved')}});
async function postJson(path,body){const r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const j=await r.json().catch(()=>({}));if(!r.ok)throw new Error(j.error||('HTTP '+r.status));return j}
async function afterRun(msg){toast(msg);for(let i=0;i<80;i++){await new Promise(r=>setTimeout(r,1500));try{const r=await(await fetch('/api/run')).json();if(!r.running&&i>0){location.reload();return}}catch(e){}}location.reload()}
q('addGo').onclick=async()=>{const url=q('addUrl').value.trim(),rent=q('addRent').value;if(!url){q('addMsg').textContent='Paste a link first.';return}
 q('addGo').disabled=true;q('addMsg').textContent='Opening the page and reading it…';
 try{const r=await postJson('/api/add',{url,rent});q('addMsg').textContent=(r.existed?'Updated: ':'Added: ')+r.title+' (€'+r.rent+'). '+(r.scoring?'Scoring it now…':(r.note||'It will be scored in the next run.'));
  if(r.scoring)afterRun('Added. Scoring it with Gemini…');else q('addGo').disabled=false}
 catch(err){q('addMsg').textContent='⚠ '+err.message.replace('RENT_NEEDED: ','');if(/RENT_NEEDED/.test(err.message))q('addRent').focus();q('addGo').disabled=false}};
q('msort').addEventListener('change',render);
if('IntersectionObserver' in window){new IntersectionObserver(es=>{if(es.some(e=>e.isIntersecting)&&view==='all'&&q('more').style.display!=='none'){LIMIT+=50;render()}},{rootMargin:'900px'}).observe(q('sentinel'))}
window.addEventListener('hashchange',()=>{view=viewFromHash();mapFitted=false;render();window.scrollTo(0,0)});['mColor','mOnlyMarked','mApprox'].forEach(i=>q(i).addEventListener('change',renderMap));
__FUNJS__
__UXJS__
renderHealth();initFilters();load();loadMail();setInterval(loadMail,120000);
(function(){const f=document.querySelector('details.filters');try{if(localStorage.getItem('filtersOpen')==='0')f.open=false}catch(e){}f.addEventListener('toggle',()=>{try{localStorage.setItem('filtersOpen',f.open?'1':'0')}catch(e){}})})();
(function(){const h=q('howscore');try{if(localStorage.getItem('howOpen')==='0')h.open=false}catch(e){}h.addEventListener('toggle',()=>{try{localStorage.setItem('howOpen',h.open?'1':'0')}catch(e){}})})();
(function(){const d=q('stats');try{if(localStorage.getItem('statsOpen')==='0')d.open=false}catch(e){}d.addEventListener('toggle',()=>{try{localStorage.setItem('statsOpen',d.open?'1':'0')}catch(e){}})})();
let built=null;async function poll(){try{const r=await(await fetch('/api/run')).json(),e=q('run');if(built===null)built=r.listings_updated;
 if(r.running)e.innerHTML='<span style="color:var(--warnfg)">● scraping…</span> <a href="/control">live log</a>';
 else if(r.listings_updated&&built&&r.listings_updated>built)e.innerHTML='<a href="/">↻ new results ready, reload</a>';else e.textContent=''}catch(x){}}
poll();setInterval(poll,5000);
</script></body></html>"""
