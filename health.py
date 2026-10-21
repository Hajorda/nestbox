"""One place that says what works and what does not, each with how to fix it. Without ping=True it only looks at local files (fast, no network);
with ping=True it makes ONE request to each listing site and to Google/Gemini to see whether this computer can reach them."""
import json, os, socket, sys, time, urllib.request

import cloud_sync, firstrun, mail_link

HERE = os.path.dirname(os.path.abspath(__file__))
SITES = {"immoweb": "https://www.immoweb.be/en", "immovlan": "https://immovlan.be/en", "2ememain": "https://www.2ememain.be/", "housinganywhere": "https://housinganywhere.com/", "spotahome": "https://www.spotahome.com/"}
NAMES = {"immoweb": "Immoweb", "immovlan": "Immovlan", "2ememain": "2ememain", "housinganywhere": "HousingAnywhere", "spotahome": "Spotahome"}


def _read(name, default):
    try:
        with open(os.path.join(HERE, name)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _c(id, label, status, detail, fix=""):
    return {"id": id, "label": label, "status": status, "detail": detail, "fix": fix}


def ping_sites():
    out = {}
    import sources
    for key, url in SITES.items():
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": sources.UA})
            with urllib.request.urlopen(req, timeout=12) as r:
                out[key] = (r.status, round(time.time() - t0, 1))
        except urllib.error.HTTPError as e:
            out[key] = (e.code, round(time.time() - t0, 1))
        except Exception as e:
            out[key] = (0, type(e).__name__)
    try:
        socket.create_connection(("generativelanguage.googleapis.com", 443), timeout=8).close()
        out["gemini"] = (200, 0)
    except OSError as e:
        out["gemini"] = (0, type(e).__name__)
    return out


def checks(ping=False):
    cfg, state, hist = firstrun.load(), _read("state.json", {}), _read("history.json", [])
    res = []
    v = sys.version_info
    res.append(_c("python", "Python", "ok" if v >= (3, 9) else "bad", f"version {v.major}.{v.minor}.{v.micro}", "" if v >= (3, 9) else "Install Python 3.9 or newer from python.org."))
    p = cfg.get("profile", {})
    if firstrun.needs_setup(cfg):
        res.append(_c("setup", "Your details", "bad", "The setup is not done yet: messages would be signed 'Your Name'.", "Open the setup page (/setup) and answer the few questions."))
    else:
        missing = [k for k in ("signature", "phone", "email", "move_in", "move_out") if not str(p.get(k, "")).strip()]
        res.append(_c("setup", "Your details", "warn" if missing else "ok", ("Missing: " + ", ".join(missing)) if missing else f"{p.get('signature')} · budget €{cfg.get('budget')} · {len(cfg.get('enabled_areas') or cfg.get('areas', {}))} areas", "Fill them in under 'Your details' in the control panel." if missing else ""))
    n = len(state.get("catalog", {}))
    last = hist[-1] if hist else None
    if not n:
        res.append(_c("data", "Listings", "warn", "No listings yet.", "Press 'Scrape now' (about 10 minutes the first time), or run the demo: python3 demo.py"))
    else:
        age = (time.time() - time.mktime(time.strptime(last["started"][:16], "%Y-%m-%dT%H:%M"))) / 3600 if last else None
        res.append(_c("data", "Listings", "warn" if age and age > 48 else "ok", f"{n} listings tracked" + (f" · last run {age:.0f} h ago" if age is not None else ""), "The data is old. Press 'Scrape now' or turn on automatic runs." if age and age > 48 else ""))
    sh = _read("source_health.json", {}).get("sources", {})
    for k, name in NAMES.items():
        s = sh.get(k)
        if not s:
            res.append(_c("site-" + k, name, "info", "Not searched yet.", ""))
        elif s["status"] == "ok":
            res.append(_c("site-" + k, name, "ok", f"{s['count']} results in the last run"))
        elif s["status"] == "blocked":
            res.append(_c("site-" + k, name, "bad", "The site is blocking us.", "Wait a day before the next run. Do not retry quickly: that makes it worse."))
        else:
            res.append(_c("site-" + k, name, "bad", f"{s['count']} results (usually about {s.get('typical') or '?'}).", "The site probably changed its pages, so this scraper needs an update. The other sites still work."))
    import gemini
    key = gemini.api_key()
    ai = state.get("ai_stats") or {}
    res.append(_c("gemini", "Gemini (description checks)", "ok" if key else "info", ("Key found. " + (f"{ai.get('checked', 0)} of {ai.get('with_text', 0)} descriptions checked." if ai else "")) if key else "No key: the keyword reader still works, Gemini is optional.",
                  "" if key else "Optional: put GEMINI_API_KEY=... in the .env file (free key at aistudio.google.com)."))
    cl = cloud_sync.settings()
    if not cl:
        res.append(_c("cloud", "Shared copy (Railway)", "info", "Not set up. Optional: lets a friend see the list.", "See the README, section 'Shared copy'."))
    else:
        l = cloud_sync.last_status() or {}
        res.append(_c("cloud", "Shared copy (Railway)", "ok" if l.get("ok") else "warn", f"{cl['url']} · " + ("last publish OK at " + str(l.get("at", ""))[:16] if l.get("ok") else (l.get("error") or "not published yet")), "" if l.get("ok") else "Press 'Publish now' in the control panel and read the error."))
    mi = mail_link.info()
    if not mi["client_file"]:
        res.append(_c("mail", "Gmail link", "info", "Not set up. Optional: shows replies on the right flat.", "See the control panel, 'Gmail link'."))
    elif not mi["connected"]:
        res.append(_c("mail", "Gmail link", "warn", "Client file found, not signed in.", "Run: python3 mail_link.py connect"))
    else:
        res.append(_c("mail", "Gmail link", "bad" if mi["error"] else "ok", (mi["error"] or f"connected as {mi['me']}, {mi['messages']} messages tracked"), "Run: python3 mail_link.py connect (the sign-in may have expired)." if mi["error"] else ""))
    sched = _read("schedule.json", {})
    res.append(_c("schedule", "Automatic runs", "ok" if sched.get("enabled") else "info", "On" if sched.get("enabled") else "Off: runs only when you press 'Scrape now'.", "" if sched.get("enabled") else "Turn them on under 'Automatic runs' (needs this server to stay open)."))
    if ping:
        p = ping_sites()
        for k, name in NAMES.items():
            code, t = p.get(k, (0, "?"))
            res.append(_c("ping-" + k, name + " reachable", "ok" if 200 <= code < 400 else "warn" if code in (403, 429) else "bad", f"HTTP {code} in {t}s" if code else f"cannot connect ({t})",
                          "" if 200 <= code < 400 else "Blocked by the site: wait a day." if code in (403, 429) else "Check your internet connection or a VPN / firewall."))
        code, t = p.get("gemini", (0, "?"))
        res.append(_c("ping-gemini", "Google Gemini reachable", "ok" if code else "warn", "connected" if code else f"cannot connect ({t})", "" if code else "Check your internet connection."))
    return res
