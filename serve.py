#!/usr/bin/env python3
"""Local app server:  python3 serve.py   ->  http://127.0.0.1:8765/

  /          the ranked listings page (statuses + notes are saved to statuses.json)
  /control   control panel: edit search settings, start a scrape, see the live log, set an automatic schedule

Safety: listens on 127.0.0.1 only; rejects requests whose Host/Origin is not this server (blocks other websites and
DNS-rebinding tricks); settings are validated against a whitelist; the scraper is started as a fixed argument list
(no shell); one run at a time; automatic runs are limited to every 2 h or slower and pause for 24 h if a site blocks us.
"""
import json, os, random, re, subprocess, sys, tempfile, threading, time

import cloud_sync
import actions
import firstrun
import health
import mail_link
import messages
import describe
import gemini
import sources
from datetime import date, datetime
from urllib.parse import parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("FF_PORT", "8765"))
STATUS_FILE = os.path.join(HERE, "statuses.json")
CONFIG_FILE = os.path.join(HERE, "config.json")
SCHEDULE_FILE = os.path.join(HERE, "schedule.json")
LOG_FILE = os.path.join(HERE, "run.log")
PROGRESS_FILE = os.path.join(HERE, "progress.json")
STATE_FILE = os.path.join(HERE, "state.json")
MANUAL_FILE = os.path.join(HERE, "manual.json")
ID_RX = re.compile(r"[A-Za-z0-9_-]{3,60}")
ALLOWED = {"new", "contacted", "replied", "visit", "applied", "rejected"}
HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}
MANUAL_COOLDOWN = 300          # seconds between two online runs started by hand
MIN_EVERY_MINUTES = 120        # fastest allowed automatic interval

NUM = {"budget": (300, 5000), "min_m2": (0, 200), "pages_per_area": (1, 4), "max_pages_per_area": (1, 6), "new_days": (1, 30), "max_late_days": (1, 365), "furnished_pages_per_area": (0, 3),
       "detail_pages_per_run": (0, 300), "ai_per_run": (0, 200), "read_max_minutes": (10, 120), "notify_min_score": (0, 150),
       "utilities_estimate": (0, 500), "unfurnished_extra": (0, 500), "followup_first_days": (1, 30), "followup_next_days": (1, 30), "followup_max": (0, 5)}
NUM_DEFAULT = {"followup_first_days": 2, "followup_next_days": 3, "followup_max": 2}
PROFILE_TEXT = ("names", "signature", "second_name", "phone", "email", "visit_times", "workplace")
FILE_LOCK = threading.Lock()
RUN = {"proc": None, "started": None, "finished": None, "code": None, "source": "", "args": []}
JITTER = [random.randint(0, 600)]


# ---------------------------------------------------------------- small helpers
def read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, data):
    fd, tmp = tempfile.mkstemp(dir=HERE)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)                      # atomic: never leaves a half-written file


def clean_text(v, n=120):
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(v)).strip()[:n]


def key_present():
    if os.environ.get("GEMINI_API_KEY", "").strip():
        return True
    try:
        with open(os.path.join(HERE, ".env")) as f:
            return any(l.partition("=")[0].strip() == "GEMINI_API_KEY" and l.partition("=")[2].strip() for l in f)
    except OSError:
        return False


# ---------------------------------------------------------------- settings
def get_settings():
    cfg = read_json(CONFIG_FILE, {})
    areas = [{"postal": p, "name": a["immoweb"].replace("-", " ").title(), "lang": a.get("lang", "fr")} for p, a in cfg.get("areas", {}).items()]
    out = {k: cfg.get(k, NUM_DEFAULT.get(k)) for k in NUM}
    out.update({"eurocontrol_shuttle": bool(cfg.get("eurocontrol_shuttle")), "midterm_enabled": cfg.get("midterm_enabled", True), "digest_enabled": cfg.get("digest_enabled", True), "digest_time": cfg.get("digest_time", "08:30"), "found_mode": cfg.get("found_mode") or {"on": False}, "gemini_model": cfg.get("gemini_model", "gemini-2.5-flash"),
                "areas": areas, "enabled_areas": cfg.get("enabled_areas") or [a["postal"] for a in areas],
                "profile": cfg.get("profile", {}), "gemini_key_present": key_present(), "fees": cfg.get("fees", {})})
    return out


def apply_settings(body):
    """Validate and merge. Returns (error, None) or (None, settings). Unknown keys are ignored."""
    with FILE_LOCK:
        cfg = read_json(CONFIG_FILE, {})
        for k, (lo, hi) in NUM.items():
            if k in body:
                if not isinstance(body[k], int) or isinstance(body[k], bool) or not lo <= body[k] <= hi:
                    return f"{k} must be a whole number between {lo} and {hi}", None
                cfg[k] = body[k]
        for k in ("eurocontrol_shuttle", "midterm_enabled", "digest_enabled"):
            if k in body:
                if not isinstance(body[k], bool):
                    return f"{k} must be true/false", None
                cfg[k] = body[k]
        if isinstance(body.get("fees"), dict):
            for src, f in body["fees"].items():
                if src not in cfg.get("fees", {}) or not isinstance(f, dict):
                    return f"unknown fee source {src}", None
                try:
                    lo, hi, mn = float(f["pct_low"]), float(f["pct_high"]), float(f.get("min", 0))
                except (KeyError, TypeError, ValueError):
                    return "fee values must be numbers", None
                if not (0 <= lo <= hi <= 1) or not 0 <= mn <= 2000:
                    return "fee: 0% <= low <= high <= 100%, minimum 0-2000", None
                cfg["fees"][src].update(pct_low=lo, pct_high=hi, min=mn)
        if "digest_time" in body:
            if not isinstance(body["digest_time"], str) or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", body["digest_time"]):
                return "digest_time must look like 08:30", None
            cfg["digest_time"] = body["digest_time"]
        if "gemini_model" in body:
            if not isinstance(body["gemini_model"], str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,60}", body["gemini_model"]):
                return "gemini_model: letters, digits, dot, dash only", None
            cfg["gemini_model"] = body["gemini_model"]
        if "enabled_areas" in body:
            ea = body["enabled_areas"]
            if not isinstance(ea, list) or not ea or any(p not in cfg.get("areas", {}) for p in ea):
                return "pick at least one known area", None
            cfg["enabled_areas"] = list(dict.fromkeys(ea))
        if isinstance(body.get("profile"), dict):
            prof = cfg.setdefault("profile", {})
            for k in PROFILE_TEXT:
                if k in body["profile"]:
                    prof[k] = clean_text(body["profile"][k])
            try:
                mi, mo = body["profile"].get("move_in", prof.get("move_in")), body["profile"].get("move_out", prof.get("move_out"))
                if date.fromisoformat(mo) <= date.fromisoformat(mi):
                    return "move-out must be after move-in", None
                prof["move_in"], prof["move_out"] = mi, mo
                ie = body["profile"].get("internship_end", prof.get("internship_end"))
                if ie:
                    date.fromisoformat(ie)
                    prof["internship_end"] = ie
            except (TypeError, ValueError):
                return "dates must look like 2026-12-01", None
        write_json(CONFIG_FILE, cfg)
    return None, get_settings()


# ---------------------------------------------------------------- scrape runs
def external_running():
    """A scrape this server did not start (a terminal run, or one started before a server restart) keeps progress.json fresh while it works."""
    p = read_json(PROGRESS_FILE, None)
    return bool(p and p.get("running") and time.time() - p.get("updated", 0) < 90)


def running():
    p = RUN["proc"]
    return (p is not None and p.poll() is None) or (p is None and external_running())


def build_args(o):
    args = []
    for flag in ("offline", "read_only", "no_ai", "no_details", "notify"):
        if o.get(flag) is True:
            args.append("--" + flag.replace("_", "-"))
    for key in ("prioritise", "recheck"):
        v = o.get(key)
        if v:
            if not isinstance(v, list) or len(v) > 20 or any(not isinstance(x, str) or not ID_RX.fullmatch(x) for x in v):
                raise ValueError(f"{key} must be a short list of listing ids")
            args += [f"--{key}", ",".join(v)]
    for key, lo, hi in (("details", 0, 500), ("max", 300, 5000), ("ai", 1, 200)):
        v = o.get(key)
        if v not in (None, ""):
            if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
                raise ValueError(f"{key} must be a whole number between {lo} and {hi}")
            args += [f"--{key}", str(v)]
    return args


def start_run(options, source):
    """Returns (error, None) or (None, args)."""
    try:
        args = build_args(options)
    except ValueError as e:
        return str(e), None
    with FILE_LOCK:
        if running():
            return "a run is already in progress", None
        offline = "--offline" in args or "--recheck" in args
        if not offline and (read_json(CONFIG_FILE, {}).get("found_mode") or {}).get("on"):
            return "searching is paused because you found a flat (Resume searching on the listings page or in the control panel)", None
        if not offline and RUN["finished"] and source == "manual" and time.time() - RUN["finished"] < MANUAL_COOLDOWN:
            wait = int(MANUAL_COOLDOWN - (time.time() - RUN["finished"]))
            return f"please wait {wait}s: runs close together make the sites suspicious", None
        try:
            os.remove(PROGRESS_FILE)             # don't show the previous run's bar while the new one starts
        except OSError:
            pass
        env = dict(os.environ, PYTHONUNBUFFERED="1", FF_SOURCE=source)
        log = open(LOG_FILE, "w")
        log.write(f"# {datetime.now():%Y-%m-%d %H:%M:%S} {source} run: scraper.py {' '.join(args)}\n")
        log.flush()
        RUN.update(proc=subprocess.Popen([sys.executable, "-u", os.path.join(HERE, "scraper.py"), *args], cwd=HERE, stdout=log,
                                         stderr=subprocess.STDOUT, env=env), started=time.time(), finished=None, code=None, source=source, args=args)
        if not offline:
            sched = read_json(SCHEDULE_FILE, {})
            sched["last_run_ts"] = time.time()
            write_json(SCHEDULE_FILE, sched)
            JITTER[0] = random.randint(0, 600)
    threading.Thread(target=watch, daemon=True).start()
    return None, args


def add_manual(body):
    """Fetch the listing behind a pasted link, store it in manual.json, and start a quick re-score so it shows up scored."""
    url = str(body.get("url", ""))[:600]
    try:
        hint = int(body["rent"]) if body.get("rent") not in (None, "") else None
    except (TypeError, ValueError):
        return "rent must be a whole number", None
    try:
        item = sources.fetch_listing(url, hint)
    except sources.Blocked:
        return "the site refused the request (blocked or rate-limited). Try again later.", None
    except ValueError as e:
        return str(e), None
    except Exception as e:
        return f"could not read that page ({type(e).__name__})", None
    with FILE_LOCK:
        m = read_json(MANUAL_FILE, {})
        existed = item["id"] in m
        m[item["id"]] = item
        write_json(MANUAL_FILE, m)
    err, _ = start_run({"offline": True, "ai": 3, "prioritise": [item["id"]], "notify": False}, "manual")
    return None, {"id": item["id"], "title": item["title"], "rent": item["rent"], "existed": existed, "scoring": err is None, "note": err}


def remove_manual(body):
    lid = str(body.get("id", ""))
    if not ID_RX.fullmatch(lid):
        return "bad id", None
    with FILE_LOCK:
        m = read_json(MANUAL_FILE, {})
        if lid not in m:
            return "that listing was not added by link", None
        del m[lid]
        write_json(MANUAL_FILE, m)
    err, _ = start_run({"offline": True, "no_ai": True, "notify": False}, "manual")
    return None, {"removed": lid, "scoring": err is None}


def recheck(body):
    ids = body.get("ids")
    if not isinstance(ids, list) or not 1 <= len(ids) <= 5 or any(not isinstance(x, str) or not ID_RX.fullmatch(x) for x in ids):
        return "give 1 to 5 listing ids", None
    err, _ = start_run({"recheck": ids, "ai": len(ids), "notify": False}, "manual")
    return (err, None) if err else (None, {"rechecking": ids})


def watch():
    p = RUN["proc"]
    code = p.wait()
    RUN.update(finished=time.time(), code=code)
    if "BLOCKED" in log_text() and "--offline" not in RUN["args"]:
        with FILE_LOCK:                          # a site blocked us: automatic runs pause for 24 h
            s = read_json(SCHEDULE_FILE, {})
            s["paused_until"] = time.time() + 86400
            write_json(SCHEDULE_FILE, s)


def log_text(lines=60):
    try:
        with open(LOG_FILE, errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    except OSError:
        return ""


def run_status():
    s = read_json(SCHEDULE_FILE, {})
    log = log_text()
    progress = read_json(PROGRESS_FILE, None)
    if progress and not running():
        progress["running"] = False              # the process ended (also covers a crash that left "running" set)
    return {"progress": progress, "running": running(), "started": RUN["started"], "finished": RUN["finished"], "code": RUN["code"], "source": RUN["source"],
            "args": RUN["args"], "log": log, "blocked": "BLOCKED" in log, "paused_until": s.get("paused_until") if s.get("paused_until", 0) > time.time() else None,
            "listings_updated": os.path.getmtime(os.path.join(HERE, "listings.html")) if os.path.exists(os.path.join(HERE, "listings.html")) else None}


HISTORY_FILE = os.path.join(HERE, "history.json")


def history():
    """Past runs (newest first) and the totals over all of them."""
    runs = read_json(HISTORY_FILE, [])
    ai = [r.get("ai") or {} for r in runs]
    tot = {"runs": len(runs), "analyses": sum(a.get("analyses", 0) for a in ai), "tokens_in": sum(a.get("tokens_in", 0) for a in ai),
           "tokens_out": sum(a.get("tokens_out", 0) for a in ai), "cost_est": round(sum(a.get("cost_est", 0) for a in ai), 4),
           "requests": sum(sum((r.get("requests") or {}).values()) for r in runs)}
    return {"runs": runs[::-1][:60], "totals": tot}


def avg_cost(cfg):
    """Cost of one analysis: measured over past runs once there are at least 5, otherwise a typical one (about 430 tokens in, 150 out)."""
    t = history()["totals"]
    if t["analyses"] >= 5:
        return round(t["cost_est"] / t["analyses"], 5)
    price = cfg.get("gemini_price") or {}
    return round(430 / 1e6 * price.get("input_per_million", 0.30) + 150 / 1e6 * price.get("output_per_million", 2.50), 5)


_STATE_CACHE = {"mtime": 0, "data": {}}


def listing_text(query):
    """The stored description of one listing with its key phrases marked (HTML-escaped, so safe to insert)."""
    lid = (parse_qs(query).get("id") or [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_-]{3,60}", lid):
        return {"html": "unknown listing"}
    try:
        mtime = os.path.getmtime(STATE_FILE)
        if mtime != _STATE_CACHE["mtime"]:
            _STATE_CACHE.update(mtime=mtime, data=read_json(STATE_FILE, {}))
    except OSError:
        return {"html": "no data yet"}
    text = (_STATE_CACHE["data"].get("details", {}).get(lid) or {}).get("description")
    nt = (_STATE_CACHE["data"].get("details", {}).get(lid) or {}).get("no_text")
    return {"html": describe.highlight_html(text) if text else ("<i>The seller wrote no description.</i>" if nt else "<i>The text of this listing has not been read yet.</i>"), "chars": len(text or "")}


def cloud_info():
    cfg = cloud_sync.settings()
    return {"configured": bool(cfg), "url": cfg["url"] if cfg else None, "last": cloud_sync.last_status()}


def gemini_stats():
    """How many of the listings whose text we have read were already checked by Gemini (same text-hash rule as the scraper)."""
    cfg, st = read_json(CONFIG_FILE, {}), read_json(STATE_FILE, {})
    cat, det, ai = st.get("catalog", {}), st.get("details", {}), st.get("ai", {})
    with_text = checked = 0
    for lid, c in cat.items():
        d = det.get(lid, {}).get("description")
        if not d or c.get("missed", 0) >= 2 or c.get("rent", 0) > cfg.get("budget", 1300):
            continue
        with_text += 1
        if ai.get(lid, {}).get("h") == gemini.text_hash({"title": c.get("title"), "description": d}):
            checked += 1
    ss = st.get("ai_stats")                                # the scraper's own count (merged duplicates, same budget rule); falls back to a raw count
    if ss:
        with_text, checked = ss["with_text"], ss["checked"]
    return {"key_present": key_present(), "model": cfg.get("gemini_model", "gemini-2.5-flash"), "checked": checked, "with_text": with_text,
            "waiting": with_text - checked, "ever_checked": len(ai), "per_run": cfg.get("ai_per_run", 40), "seconds_each": 5,
            "avg_cost": avg_cost(cfg)}


# ---------------------------------------------------------------- automatic schedule
def get_schedule():
    s = read_json(SCHEDULE_FILE, {})
    out = {"enabled": bool(s.get("enabled")), "every_minutes": s.get("every_minutes", 360), "start_hour": s.get("start_hour", 7),
           "end_hour": s.get("end_hour", 23), "notify": s.get("notify", True), "ai": s.get("ai", True), "min_every_minutes": MIN_EVERY_MINUTES}
    if out["enabled"]:
        out["next_run_ts"] = max(s.get("last_run_ts", 0) + out["every_minutes"] * 60 + JITTER[0], s.get("paused_until", 0))
    return out


def apply_schedule(body):
    with FILE_LOCK:
        s = read_json(SCHEDULE_FILE, {})
        ints = {"every_minutes": (MIN_EVERY_MINUTES, 1440), "start_hour": (0, 23), "end_hour": (1, 24)}
        for k, (lo, hi) in ints.items():
            if k in body:
                if not isinstance(body[k], int) or isinstance(body[k], bool) or not lo <= body[k] <= hi:
                    return f"{k} must be a whole number between {lo} and {hi}", None
                s[k] = body[k]
        for k in ("enabled", "notify", "ai"):
            if k in body:
                if not isinstance(body[k], bool):
                    return f"{k} must be true/false", None
                s[k] = body[k]
        if s.get("start_hour", 7) >= s.get("end_hour", 23):
            return "active hours: start must be before end", None
        if body.get("enabled"):
            s.pop("paused_until", None)
        write_json(SCHEDULE_FILE, s)
    return None, get_schedule()


MAIL_LOCK = threading.Lock()


def templates_payload():
    cfg, st = read_json(CONFIG_FILE, {}), read_json(STATE_FILE, {})
    cat = st.get("catalog", {})
    pick = [(lid, c) for lid, c in cat.items() if not c.get("missed") and c.get("street")][:25] or list(cat.items())[:25]
    return {"templates": messages.templates(), "defaults": messages.DEFAULTS, "custom": sorted(messages.overrides()), "placeholders": messages.PLACEHOLDERS,
            "listings": [{"id": lid, "title": (c.get("title") or lid)[:60], "addr": " ".join(x for x in (c.get("street"), c.get("locality")) if x)} for lid, c in pick], "profile_ok": bool(cfg.get("profile"))}


def templates_save(body):
    key = body.get("key")
    if key not in messages.DEFAULTS:
        return "unknown message", None
    with FILE_LOCK:
        cur = read_json(messages.TEMPLATES_FILE, {})
        if body.get("reset"):
            cur.pop(key, None)
        else:
            text = body.get("text")
            if not isinstance(text, str) or not text.strip() or len(text) > 4000:
                return "the message must be text of at most 4000 characters", None
            cur[key] = text
        write_json(messages.TEMPLATES_FILE, cur)
    return None, {}


def templates_preview(body):
    cfg, st = read_json(CONFIG_FILE, {}), read_json(STATE_FILE, {})
    c = (st.get("catalog") or {}).get(str(body.get("id")), {})
    key = body.get("key") if body.get("key") in messages.DEFAULTS else "en"
    text = body.get("text") if isinstance(body.get("text"), str) else messages.templates()[key]
    item = {**c, "url": c.get("url", "https://example.com/listing")}
    return messages.render(text[:4000], messages.variables(item, cfg, key[-2:]))


def mail_check():
    """One look at the inbox (read-only). New replies: a notification, the flat becomes "replied" (also on the shared copy) and counts a point in the Today tab."""
    if not mail_link.connected() or not MAIL_LOCK.acquire(blocking=False):
        return None
    try:
        state, statuses = read_json(STATE_FILE, {}), load_status()
        new = mail_link.poll(state.get("catalog", {}), statuses)
        summ = mail_link.summary()
        for lid, e0 in list(load_status().items()):                     # a "replied" the mail check set from automated mail that is no longer a reply: take it back
            if e0.get("status") == "replied" and any(x.get("by") == "mail" and x.get("k") == "reply" for x in (e0.get("log") or [])) and not (summ.get(lid) or {}).get("in"):
                with FILE_LOCK:
                    data = load_status()
                    e = dict(data.get(lid) or {})
                    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
                    e["status"], e["status_at"], e["at"] = "contacted", now, now
                    e["log"] = (e.get("log") or [])[-59:] + [{"t": now, "k": "status", "d": "back to contacted: the 'reply' was an automatic email", "by": "mail"}]
                    data[lid] = e
                    write_json(STATUS_FILE, data)
                    if cloud_sync.settings():
                        threading.Thread(target=cloud_sync.forward_status, args=({"id": lid, "status": "contacted"},), daemon=True).start()
        due = {lid for lid, o in summ.items() if o["in"] and o["last"] and (statuses.get(lid) or {}).get("status") in ("new", "contacted")}      # a flat you wrote to, and somebody answered
        for lid, m in new:
            c = state.get("catalog", {}).get(lid, {})
            name = m["from"].split("<")[0].strip() or "the agency"
            subprocess.run(["osascript", "-e", 'display notification "%s" with title "Reply about %s" sound name "Glass"' % (
                m["snippet"][:90].replace('"', "'").replace("\\", ""), (c.get("street") or c.get("locality") or lid).replace('"', "'"))], check=False)
        for lid in due | {lid for lid, _m in new}:
            with FILE_LOCK:
                data = load_status()
                e = dict(data.get(lid) or {"status": "new", "note": ""})
                if e.get("status") in ("new", "contacted") or lid in {x[0] for x in new}:
                    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
                    if lid in {x[0] for x in new}:
                        m = next(x[1] for x in new if x[0] == lid)
                        e["log"] = (e.get("log") or [])[-59:] + [{"t": now, "k": "reply", "d": ("reply from " + (m["from"].split("<")[0].strip() or "the agency") + ": " + m["snippet"])[:140], "by": "mail"}]
                    if e.get("status") in ("new", "contacted"):
                        e.update(status="replied", status_at=now, by="mail")
                    e["at"] = now
                    data[lid] = e
                    write_json(STATUS_FILE, data)
                    if cloud_sync.settings():
                        threading.Thread(target=cloud_sync.forward_status, args=({"id": lid, "status": "replied"},), daemon=True).start()
                        threading.Thread(target=cloud_sync.proxy, args=("POST", "/api/fun/event", json.dumps({"k": "log", "lid": lid, "s": "replied", "o": "replied"}).encode()), daemon=True).start()
        return len(new)
    finally:
        MAIL_LOCK.release()


def mail_loop():
    time.sleep(20)
    while True:
        try:
            mail_check()
        except Exception as ex:
            print("mail check failed:", type(ex).__name__)
        time.sleep(300)


def next_actions():
    cfg, st = read_json(CONFIG_FILE, {}), read_json(STATE_FILE, {})
    return actions.compute(cfg, load_status(), mail_link.summary(), read_json(os.path.join(HERE, "pool.json"), []))


def send_digest(force=False):
    """The morning summary as a macOS notification (and a push to the phone / browser if the shared copy is set up). Returns the text or None."""
    cfg, st = read_json(CONFIG_FILE, {}), read_json(STATE_FILE, {})
    if (cfg.get("found_mode") or {}).get("on") and not force:
        return None
    pool = read_json(os.path.join(HERE, "pool.json"), [])
    a = actions.compute(cfg, load_status(), mail_link.summary(), pool)
    text = actions.digest_text(a, st.get("catalog", {}), pool)
    if not text:
        return None
    title, body = text
    subprocess.run(["osascript", "-e", 'display notification "%s" with title "%s" sound name "Glass"' % (body.replace('"', "'"), title)], check=False)
    if cloud_sync.settings():
        threading.Thread(target=cloud_sync.proxy, args=("POST", "/api/push/send", json.dumps({"title": title, "body": body}).encode()), daemon=True).start()
    return body


def digest_loop():
    """Once a day at the set time (default 08:30; if the Mac was asleep, as soon as it wakes, until 18:00)."""
    while True:
        time.sleep(60)
        try:
            cfg = read_json(CONFIG_FILE, {})
            if not cfg.get("digest_enabled", True):
                continue
            now = datetime.now()
            f = read_json(os.path.join(HERE, "digest.json"), {})
            if now.strftime("%H:%M") >= cfg.get("digest_time", "08:30") and now.hour < 18 and f.get("date") != now.date().isoformat():
                send_digest()
                write_json(os.path.join(HERE, "digest.json"), {"date": now.date().isoformat()})
        except Exception as e:
            print("digest:", e, file=sys.stderr)


def set_found(body):
    """You found a flat: remember which one, pause searching and reminders, keep every record. Or resume."""
    on = bool(body.get("on"))
    lid = str(body.get("lid") or "")[:40]
    with FILE_LOCK:
        cfg = read_json(CONFIG_FILE, {})
        now = datetime.now().strftime("%Y-%m-%dT%H:%M")
        if on:
            cat = read_json(STATE_FILE, {}).get("catalog", {})
            if lid not in cat:
                return "unknown flat"
            cfg["found_mode"] = {"on": True, "lid": lid, "at": now}
            data = load_status()
            e = dict(data.get(lid) or {"status": "new", "note": ""})
            e.update(status="applied", status_at=now, at=now, chosen=True, marked=True)
            e["log"] = (e.get("log") or [])[-59:] + [{"t": now, "k": "status", "d": "🏠 this is the one: searching and reminders paused", "by": "me"}]
            data[lid] = e
            write_json(STATUS_FILE, data)
        else:
            old = (cfg.get("found_mode") or {}).get("lid")
            cfg["found_mode"] = {"on": False}
            data = load_status()
            if old in data:
                data[old].pop("chosen", None)
                write_json(STATUS_FILE, data)
        write_json(CONFIG_FILE, cfg)
    if cloud_sync.settings():
        threading.Thread(target=cloud_sync.proxy, args=("POST", "/api/fun/settings", json.dumps({"paused": on}).encode()), daemon=True).start()
        if on:
            threading.Thread(target=cloud_sync.forward_status, args=({"id": lid, "status": "applied"},), daemon=True).start()
    return None


def scheduler_loop():
    while True:
        time.sleep(20)
        try:
            s = read_json(SCHEDULE_FILE, {})
            now = datetime.now()
            if not s.get("enabled") or running() or time.time() < s.get("paused_until", 0):
                continue
            if not s.get("start_hour", 7) <= now.hour < s.get("end_hour", 23):
                continue
            if time.time() >= s.get("last_run_ts", 0) + s.get("every_minutes", 360) * 60 + JITTER[0]:
                start_run({"notify": s.get("notify", True), "no_ai": not s.get("ai", True)}, "schedule")
        except Exception as e:                  # the scheduler must never die
            print("scheduler:", e, file=sys.stderr)


# ---------------------------------------------------------------- HTTP
def load_status():
    return read_json(STATUS_FILE, {})


class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if ctype.startswith("image/"):
            self.send_header("Content-Security-Policy", "default-src 'none'; sandbox")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else (body if isinstance(body, str) else json.dumps(body)).encode())

    def _local_only(self):
        if self.headers.get("Host") not in HOSTS:
            self._send(403, {"error": "bad host"})
            return False
        origin = self.headers.get("Origin")
        if origin and origin not in {f"http://{h}" for h in HOSTS}:
            self._send(403, {"error": "bad origin"})
            return False
        return True

    def _file(self, name):
        try:
            with open(os.path.join(HERE, name), "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        except OSError:
            return self._send(404, "File missing: run scraper.py first" if name == "listings.html" else "not found", "text/plain")

    def do_GET(self):
        if not self._local_only():
            return
        if re.fullmatch(r"/api/fun|/fun/fun_[a-z0-9_]+\.(?:jpg|png|webp|gif)(?:\?v=\d+)?", self.path):
            code, data, ctype = cloud_sync.proxy("GET", self.path)
            return self._send(code, data, ctype)
        if self.path == "/icon.svg":
            try:
                with open(os.path.join(HERE, "icon.svg"), "rb") as f:
                    return self._send(200, f.read(), "image/svg+xml")
            except OSError:
                return self._send(404, "not found", "text/plain")
        if self.path in ("/setup", "/setup.html"):
            return self._file("setup.html")
        if self.path == "/api/setup":
            cfg = firstrun.load()
            return self._send(200, {"needs_setup": firstrun.needs_setup(cfg), "profile": cfg.get("profile", {}), "budget": cfg.get("budget"),
                                    "enabled": cfg.get("enabled_areas") or list(cfg.get("areas", {})),
                                    "areas": [{"postal": p, "name": a["immoweb"].replace("-", " ").title(), "lang": a.get("lang", "fr")} for p, a in cfg.get("areas", {}).items()]})
        if self.path == "/api/health":
            return self._send(200, health.checks())
        if self.path == "/api/next":
            return self._send(200, next_actions())
        if self.path == "/api/templates":
            return self._send(200, templates_payload())
        if self.path == "/api/mail":
            return self._send(200, {"info": mail_link.info(), "mail": mail_link.summary()})
        if self.path.startswith("/api/listing?"):
            return self._send(200, listing_text(self.path.partition("?")[2]))
        routes = {"/api/status": lambda: cloud_sync.merged_statuses(load_status()), "/api/cloud": cloud_info, "/api/config": get_settings, "/api/schedule": get_schedule, "/api/run": run_status, "/api/gemini": gemini_stats, "/api/history": history}
        if self.path in routes:
            return self._send(200, routes[self.path]())
        if self.path in ("/", "/index.html", "/listings.html"):
            return self._file("listings.html")
        lg = re.fullmatch(r"/logs/(run-\d{8}-\d{6}\.log)", self.path)
        if lg:                                      # a run's text log (fixed name pattern only)
            try:
                with open(os.path.join(HERE, "logs", lg.group(1)), "rb") as f:
                    return self._send(200, f.read(), "text/plain; charset=utf-8")
            except OSError:
                return self._send(404, "log not found (old logs are removed, the newest 40 are kept)", "text/plain")
        m = re.fullmatch(r"/logos/([a-z0-9]+\.(svg|png|webp|ico))", self.path)
        if m:                                       # logos you drop into data/logos/ (fixed name pattern, no path tricks possible)
            ctype = {"svg": "image/svg+xml", "png": "image/png", "webp": "image/webp", "ico": "image/x-icon"}[m.group(2)]
            try:
                with open(os.path.join(HERE, "data", "logos", m.group(1)), "rb") as f:
                    return self._send(200, f.read(), ctype)
            except OSError:
                return self._send(404, "not found", "text/plain")
        if self.path in ("/control", "/control.html"):
            return self._file("control.html")
        self._send(404, "not found", "text/plain")

    def do_POST(self):
        if not self._local_only():
            return
        if re.fullmatch(r"/api/fun/asset\?slot=(?:face|meme_(?:yes|no|meh)(?:_\d{1,2})?)", self.path):      # a small picture for the shared copy; the custom header below forces a CORS preflight
            if self.headers.get("X-Flat") != "1" or not self.headers.get("Content-Type", "").startswith("image/"):
                return self._send(400, {"error": "bad upload"})
            n = int(self.headers.get("Content-Length", 0) or 0)
            if n > 600_000:
                return self._send(413, {"error": "picture too big (max 600 KB)"})
            code, data, ctype = cloud_sync.proxy("POST", self.path, self.rfile.read(n), self.headers["Content-Type"])
            return self._send(code, data, ctype)
        # JSON content-type forces a CORS preflight, so other websites in your browser can't write here
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self._send(400, {"error": "json only"})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20_000)) or b"{}")
            assert isinstance(body, dict)
        except Exception:
            return self._send(400, {"error": "bad json"})
        if self.path == "/api/status":
            return self._post_status(body)
        if self.path == "/api/found":
            err = set_found(body)
            if err:
                return self._send(400, {"error": err})
            start_run({"offline": True}, "manual")           # rebuild the page: it hides the rest while you are done searching
            return self._send(200, {})
        if self.path == "/api/digest/test":
            text = send_digest(force=True)
            return self._send(200, {"sent": bool(text), "text": text or "Nothing to do right now, so no notification."})
        if self.path == "/api/setup":
            with FILE_LOCK:
                err, _cfg = firstrun.apply_setup(body)
            if err:
                return self._send(400, {"error": err})
            start_run({"offline": True}, "manual")           # rebuild the page with the new details
            return self._send(200, {})
        if self.path == "/api/health/ping":
            return self._send(200, health.checks(ping=True))
        if self.path == "/api/templates/save":
            err, _ = templates_save(body)
            if err:
                return self._send(400, {"error": err})
            start_run({"offline": True}, "manual")           # rebuild the page so the cards use the new text
            return self._send(200, {})
        if self.path == "/api/templates/preview":
            return self._send(200, {"text": templates_preview(body)})
        if self.path == "/api/mail/refresh":
            n = mail_check()
            return self._send(200, {"new": n, "info": mail_link.info()} if n is not None else {"error": "Gmail is not connected yet (see the control panel)"})
        if self.path == "/api/mail/decide":
            try:
                mail_link.decide(str(body["mid"])[:40], str(body["lid"])[:40], bool(body["ok"]))
            except Exception:
                return self._send(400, {"error": "bad request"})
            return self._send(200, {})
        if self.path in ("/api/fun/event", "/api/fun/settings", "/api/fun/asset/delete"):
            code, data, ctype = cloud_sync.proxy("POST", self.path, json.dumps(body).encode())
            return self._send(code, data, ctype)
        if self.path == "/api/config":
            err, res = apply_settings(body)
        elif self.path == "/api/schedule":
            err, res = apply_schedule(body)
        elif self.path == "/api/run":
            err, res = start_run(body, "manual")
            res = {"started": True, "args": res} if res is not None else None
        elif self.path == "/api/add":
            err, res = add_manual(body)
        elif self.path == "/api/manual/remove":
            err, res = remove_manual(body)
        elif self.path == "/api/recheck":
            err, res = recheck(body)
        elif self.path == "/api/cloud/publish":
            res = cloud_sync.publish()
            err, res = (None, res) if res.get("ok") else (res.get("error") or "the shared copy is not set up (CLOUD_URL and CLOUD_TOKEN in .env)", None)
        elif self.path == "/api/stop":
            if running() and RUN["proc"] is not None:
                RUN["proc"].terminate()
            err, res = None, {"stopped": True}
        else:
            return self._send(404, {"error": "not found"})
        self._send(400 if err else 200, {"error": err} if err else res)

    def _post_status(self, body):
        try:
            lid, status = str(body["id"])[:40], body.get("status")
            assert status is None or status in ALLOWED
            mk, wr = body.get("marked"), body.get("wrong")
            assert status is not None or "note" in body or body.get("followup") is True or isinstance(mk, bool) or wr is False or isinstance(wr, dict) or isinstance(body.get("log"), dict) or "visit_at" in body
        except Exception:
            return self._send(400, {"error": "bad status"})
        with FILE_LOCK:
            data = load_status()
            entry = dict(cloud_sync.merged_statuses(data).get(lid) or data.get(lid) or {"status": "new", "note": ""})    # start from what your friend may have changed too
            now = datetime.now().strftime("%Y-%m-%dT%H:%M")
            if status is not None and entry.get("status") != status:
                entry["status"], entry["status_at"] = status, now        # when the status last changed: drives the follow-up reminder
            if body.get("followup") is True:
                entry["fu_at"], entry["fu_n"] = now, entry.get("fu_n", 0) + 1
            if "note" in body:
                entry["note"] = str(body["note"])[:2000]
            if isinstance(mk, bool):
                entry["marked"], entry["marked_at"] = mk, now if mk else None
            if wr is False:
                entry.pop("wrong", None)                                   # you removed the "wrong" mark
            elif isinstance(wr, dict):                                     # what you reported as wrong, and the tags at that moment (a rechecked listing keeps this)
                entry["wrong"] = {"note": str(wr.get("note", ""))[:300], "flags": [str(f)[:30] for f in (wr.get("flags") or [])][:20], "at": now}
            cfg = cloud_sync.settings()
            who = cfg["owner"] if cfg else "me"
            if isinstance(body.get("log"), dict):
                lg = body["log"]
                entry["log"] = (entry.get("log") or [])[-59:] + [{"t": now, "k": str(lg.get("k", ""))[:20], "d": str(lg.get("d", ""))[:140], "by": who}]
            if "visit_at" in body:
                v = str(body["visit_at"])
                entry["visit_at"] = v if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", v) else ""
                entry["visit_note"] = str(body.get("visit_note", ""))[:200]
                if entry["visit_at"] and entry.get("status") in (None, "new", "contacted", "replied"):
                    entry["status"], entry["status_at"] = "visit", now
            entry["at"] = now
            if cfg:
                entry["by"] = cfg["owner"]                                  # who made the change, shown on the card
            data[lid] = entry
            write_json(STATUS_FILE, data)
        if cloud_sync.settings():
            threading.Thread(target=cloud_sync.forward_status, args=(body,), daemon=True).start()     # same change to the shared copy
        self._send(200, {})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    firstrun.ensure_config()
    threading.Thread(target=scheduler_loop, daemon=True).start()
    threading.Thread(target=mail_loop, daemon=True).start()
    threading.Thread(target=digest_loop, daemon=True).start()
    print(f"Listings:       http://127.0.0.1:{PORT}/\nControl panel:  http://127.0.0.1:{PORT}/control   (keep this window open for automatic runs; Ctrl-C to stop)")
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
