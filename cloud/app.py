#!/usr/bin/env python3
"""Nestbox, shared copy. Runs on Railway for you and your friend.

What it does: serves the listings page that your Mac publishes, keeps the shared statuses / marks / notes on a persistent disk and records
who changed what. What it deliberately does NOT do: scraping, Gemini, settings, adding links. Those stay on the owner's computer.

Security: every page and API call needs a login (HTTP Basic over HTTPS) or the owner's publish token; repeated wrong passwords lock an address out
for a while; control endpoints answer 403; responses carry no-store / nosniff / no-frame headers.

Environment: PORT (set by Railway), DATA_DIR (the volume, default /data), USERS ("you:password,friend:password"), PUBLISH_TOKEN (the Mac's secret).
"""
import base64, zlib, gzip, hmac, json, os, random, re, tempfile, threading, time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from zoneinfo import ZoneInfo

try:
    from pywebpush import webpush, WebPushException      # background reminders (installed in the Docker image)
except ImportError:
    webpush = None

import search
import describe                                    # copied next to this file when deploying

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("DATA_DIR", "/data")
PORT = int(os.environ.get("PORT", "8080"))
TOKEN = os.environ.get("PUBLISH_TOKEN", "")
USERS = {}
for pair in os.environ.get("USERS", "").split(","):
    name, _, pw = pair.partition(":")
    if name.strip() and pw:
        USERS[name.strip().lower()[:20]] = pw
ALLOWED = {"new", "contacted", "replied", "visit", "applied", "rejected"}
FILES = {"listings.html", "descriptions.json"}
MAX_UPLOAD = 60_000_000
OUTCOMES = {"noanswer", "voicemail", "callback", "replied", "viewing", "rented", "students", "french", "expensive", "nothanks"}
SLOTS = {"face", "meme_no", "meme_yes"}
MAX_IMAGE = 600_000
FUN_DEFAULTS = {"goal": 5, "daily": 3, "prize": "", "deadline": ""}
IMG_TYPES = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
TZ = ZoneInfo(os.environ.get("TZ_NAME", "Europe/Brussels"))          # same clock as the owner's Mac, so "newer change wins" compares like with like
LOCK = threading.Lock()
DESC = {"mtime": 0, "data": {}}
FAILS = {}                                          # client address -> times of recent wrong passwords
CACHE = {}                                          # (mtime, user) -> gzipped page


def path(name):
    return os.path.join(DATA, name)


def read_json(name, default):
    try:
        with open(path(name)) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_atomic(name, data):
    os.makedirs(DATA, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA)
    with os.fdopen(fd, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())
    os.replace(tmp, path(name))


def now():
    return datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")


def descriptions():
    """descriptions.json, re-read only when it changes (it is a few MB)."""
    try:
        m = os.path.getmtime(path("descriptions.json"))
    except OSError:
        return {}
    if m != DESC["mtime"]:
        DESC.update(mtime=m, data=read_json("descriptions.json", {}))
    return DESC["data"]


def image_ext(raw):
    """The picture type from its first bytes (never from what the uploader claims), or None."""
    if raw[:3] == b"\xff\xd8\xff":
        return "jpg"
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "webp"
    if raw[:4] == b"GIF8":
        return "gif"
    return None


def fun_assets():
    out = {}
    try:
        names = os.listdir(DATA)
    except OSError:
        return out
    for n in names:
        m = re.fullmatch(r"fun_(face_[a-z0-9]{1,20}|meme_(?:yes|no|meh)(?:_\d{1,2})?)\.(jpg|png|webp|gif)", n)
        if m:
            out[m.group(1)] = f"/fun/{n}?v={int(os.path.getmtime(path(n)))}"
    return out


def fun_state(user):
    st = {**FUN_DEFAULTS, **read_json("fun_settings.json", {})}
    return {"me": user, "users": sorted(USERS), "events": read_json("events.json", [])[-3000:], "settings": st, "assets": fun_assets(), "now": now()}


def fun_post(handler, kind, user, route):
    """Event log, shared settings and picture upload for the motivation features. Returns True when the request was handled."""
    if route == "/api/fun/event":
        raw = handler.body(2_000)
        try:
            b = json.loads(raw or b"{}")
            k = b.get("k", "log")
            assert isinstance(b, dict) and k in ("log", "cheer", "timer", "poke")
            lid = str(b.get("lid") or "")[:40]
            assert lid == "" or re.fullmatch(r"[A-Za-z0-9_-]{3,60}", lid)
            o, stt = b.get("o"), b.get("s")
            assert o is None or o in OUTCOMES
            assert stt is None or stt in ALLOWED
            to = str(b.get("to") or "")[:20].lower()
            m = "ad" if b.get("m") == "ad" else ""
        except Exception:
            handler.send(400, {"error": "bad event"})
            return True
        who = str(b.get("by") or user)[:20].lower() if kind == "admin" else user
        with LOCK:
            ev = read_json("events.json", [])
            ev.append({"t": now(), "by": who, "k": k, "lid": lid, "o": o, "s": stt, "to": to, "m": m})
            write_atomic("events.json", json.dumps(ev[-5000:]))
        handler.send(200, {})
        return True
    if route == "/api/fun/settings":
        raw = handler.body(2_000)
        try:
            b = json.loads(raw or b"{}")
            cur = {**FUN_DEFAULTS, **read_json("fun_settings.json", {})}
            if "goal" in b:
                cur["goal"] = max(1, min(99, int(b["goal"])))
            if "daily" in b:
                cur["daily"] = max(1, min(20, int(b["daily"])))
            if "prize" in b:
                cur["prize"] = str(b["prize"])[:120]
            if isinstance(b.get("paused"), bool):
                cur["paused"] = b["paused"]
            if "deadline" in b:
                if str(b["deadline"]).strip():
                    assert re.fullmatch(r"20\d\d-\d\d-\d\d", str(b["deadline"]))
                    datetime.strptime(str(b["deadline"]), "%Y-%m-%d")
                cur["deadline"] = str(b["deadline"]).strip()
        except Exception:
            handler.send(400, {"error": "bad settings"})
            return True
        with LOCK:
            write_atomic("fun_settings.json", json.dumps(cur))
        handler.send(200, cur)
        return True
    m = re.fullmatch(r"/api/fun/asset\?slot=(face|meme_(?:yes|no|meh)(?:_\d{1,2})?)", route)
    if m:
        raw = handler.body(MAX_IMAGE)
        ext = image_ext(raw or b"")
        if not raw or not ext:
            handler.send(400, {"error": "that is not a small jpg/png/webp/gif picture (max 600 KB)"})
            return True
        slot = m.group(1)
        who = re.sub(r"[^a-z0-9]", "", user)[:20] or "owner"
        if kind == "admin":
            who = re.sub(r"[^a-z0-9]", "", (handler.headers.get("X-By") or "owner").lower())[:20] or "owner"
        base = f"fun_face_{who}" if slot == "face" else f"fun_{slot}"
        with LOCK:
            for e in IMG_TYPES:
                try:
                    os.remove(path(f"{base}.{e}"))
                except OSError:
                    pass
            write_atomic(f"{base}.{ext}", raw)
        handler.send(200, fun_assets())
        return True
    if route == "/api/fun/asset/delete":
        raw = handler.body(2_000)
        try:
            slot = json.loads(raw or b"{}")["slot"]
            assert re.fullmatch(r"face|meme_(?:yes|no|meh)(?:_\d{1,2})?", slot)
        except Exception:
            handler.send(400, {"error": "bad slot"})
            return True
        who = re.sub(r"[^a-z0-9]", "", (handler.headers.get("X-By") or "owner").lower() if kind == "admin" else user)[:20] or "owner"
        base = f"fun_face_{who}" if slot == "face" else f"fun_{slot}"
        with LOCK:
            for e in IMG_TYPES:
                try:
                    os.remove(path(f"{base}.{e}"))
                except OSError:
                    pass
        handler.send(200, fun_assets())
        return True
    return False


PUSH_HOSTS = (".googleapis.com", ".mozilla.com", ".apple.com", ".windows.com", ".microsoft.com")
PUSH_LINES = ["Hourly reminder: have you called a landlord yet?", "The flat will not find itself. Do one call.", "Do you want to be homeless? Just checking.",
              "The bridge is still cold. A viewing is warmer.", "Ten minutes. One landlord. You can do this.", "Another hour gone. Another bunk bed night closer.",
              "Hello? Nobody has called anyone in a while.", "Every minute you scroll, a better flat gets rented to somebody braver.",
              "Pigeons found a better flat than you. Pick up the phone.", "Do you want to save money on cardboard? Call a landlord."]
PUSH_GENTLE = ["Quick reminder: one call is enough to feel good.", "Want to try 10 minutes of calls?", "Your partner is waiting for good news."]


def vapid():
    from py_vapid import Vapid
    p = path("vapid.pem")
    if os.path.exists(p):
        return Vapid.from_file(p)
    v = Vapid()
    v.generate_keys()
    os.makedirs(DATA, exist_ok=True)
    v.save_key(p)
    return v


def vapid_public():
    from cryptography.hazmat.primitives import serialization
    raw = vapid().public_key.public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def push_send(sub, payload, origin):
    """True when sent, False when the browser says the subscription is gone (404/410), None on other errors."""
    try:
        webpush(subscription_info=sub, data=json.dumps(payload), vapid_private_key=vapid(), vapid_claims={"sub": origin}, ttl=3600)
        return True
    except WebPushException as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        return False if code in (404, 410) else None
    except Exception:
        return None


def days_left():
    try:
        dl = datetime.strptime({**FUN_DEFAULTS, **read_json("fun_settings.json", {})}["deadline"], "%Y-%m-%d").date()
        return (dl - datetime.now(TZ).date()).days
    except Exception:
        return None


def push_payload(user, h, left=None):
    face = next((f"/fun/{n}" for n in os.listdir(DATA) if re.fullmatch(rf"fun_face_{re.escape(user)}\.(jpg|png|webp|gif)", n)), None) if os.path.isdir(DATA) else None
    return {"title": f"🏠 Find a flat ({h}:00)", "body": random.choice(PUSH_LINES) + (f"  {left} contact{'s' if left != 1 else ''} left today." if left is not None else "") + (f" {days_left()} days left to find a home." if (days_left() or -1) > 0 else ""), "url": "/#today", "icon": face}


def contacts_left(user):
    day = now()[:10]
    daily = {**FUN_DEFAULTS, **read_json("fun_settings.json", {})}["daily"]
    done = sum(1 for e in read_json("events.json", []) if e.get("k") == "log" and e.get("by") == user and str(e.get("t", ""))[:10] == day)
    return max(0, daily - done)


def push_tick():
    """Once per hour inside each person's hours: send the reminder to every phone/computer they allowed, unless they already did today's contacts."""
    if not webpush or read_json("fun_settings.json", {}).get("paused"):          # paused: the owner found a flat
        return
    d = datetime.now(TZ)
    if d.minute > 14:
        return
    key, h = d.strftime("%Y-%m-%d") + f"-{d.hour}", d.hour
    data = read_json("push.json", {"subs": [], "origin": ""})
    changed, keep = False, []
    for s in data["subs"]:
        if not (s.get("from", 9) <= h <= s.get("to", 18)) or s.get("last") == key:
            keep.append(s)
            continue
        s["last"], changed = key, True
        left = contacts_left(s["user"])
        if left > 0:
            res = push_send(s["sub"], push_payload(s["user"], h, left), data.get("origin") or "https://example.com")
            if res is False:
                continue                                              # subscription expired: drop it
        keep.append(s)
    if changed:
        with LOCK:
            now_data = read_json("push.json", {"subs": [], "origin": ""})
            seen = {s["sub"]["endpoint"] for s in keep}
            now_data["subs"] = keep + [s for s in now_data["subs"] if s["sub"]["endpoint"] not in seen and s.get("last") != key]     # keep subscriptions added meanwhile
            write_atomic("push.json", json.dumps(now_data))


def push_loop():
    while True:
        time.sleep(30)
        try:
            push_tick()
        except Exception as e:
            print("push error", type(e).__name__, flush=True)


def push_post(handler, kind, user, route):
    if route not in ("/api/push/subscribe", "/api/push/unsubscribe", "/api/push/test", "/api/push/send"):
        return False
    if not webpush:
        handler.send(503, {"error": "background reminders are not installed on this server"})
        return True
    raw = handler.body(6_000)
    try:
        b = json.loads(raw or b"{}")
        assert isinstance(b, dict)
    except Exception:
        handler.send(400, {"error": "bad request"})
        return True
    origin = "https://" + (handler.headers.get("Host") or "example.com").split(":")[0]
    if route == "/api/push/send":                                       # the owner's Mac sends its morning summary to the owner's phones and browsers
        if kind != "admin":
            handler.send(403, {"error": "only the owner can send"})
            return True
        data = read_json("push.json", {"subs": []})
        mine = [s for s in data["subs"] if s["user"] == user]
        sent = sum(1 for s in mine if push_send(s["sub"], {"title": str(b.get("title", ""))[:80], "body": str(b.get("body", ""))[:300], "url": "/#next", "icon": None}, data.get("origin") or origin))
        handler.send(200, {"sent": sent})
        return True
    if route == "/api/push/test":
        data = read_json("push.json", {"subs": []})
        mine = [s for s in data["subs"] if s["user"] == user]
        sent = sum(1 for s in mine if push_send(s["sub"], {**push_payload(user, int(now()[11:13])), "title": "🏠 Test reminder", "body": "This is how a background reminder looks. Now go and call somebody."}, data.get("origin") or origin))
        handler.send(200, {"subscriptions": len(mine), "sent": sent})
        return True
    if route == "/api/push/unsubscribe":
        ep = str(b.get("endpoint") or "")
        with LOCK:
            data = read_json("push.json", {"subs": [], "origin": ""})
            data["subs"] = [s for s in data["subs"] if not (s["user"] == user and s["sub"]["endpoint"] == ep)]
            write_atomic("push.json", json.dumps(data))
        handler.send(200, {})
        return True
    sub = b.get("subscription") or {}
    try:
        ep, keys = str(sub["endpoint"]), sub["keys"]
        host = re.fullmatch(r"https://([a-z0-9.-]+)(?::\d+)?/\S{1,900}", ep).group(1)
        assert host.endswith(PUSH_HOSTS) and len(str(keys["p256dh"])) < 200 and len(str(keys["auth"])) < 100
        info = {"endpoint": ep, "keys": {"p256dh": str(keys["p256dh"]), "auth": str(keys["auth"])}}
        frm, to = max(0, min(23, int(b.get("from", 9)))), max(0, min(23, int(b.get("to", 18))))
    except Exception:
        handler.send(400, {"error": "that is not a valid push subscription"})
        return True
    with LOCK:
        data = read_json("push.json", {"subs": [], "origin": ""})
        data["origin"] = origin
        data["subs"] = [s for s in data["subs"] if s["sub"]["endpoint"] != ep]
        if sum(1 for s in data["subs"] if s["user"] == user) >= 10:
            handler.send(400, {"error": "too many devices"})
            return True
        data["subs"].append({"user": user, "sub": info, "from": frm, "to": to, "last": ""})
        write_atomic("push.json", json.dumps(data))
    handler.send(200, {"subscribed": True})
    return True


SW_JS = """self.addEventListener('push',e=>{let d={};try{d=e.data.json()}catch(x){}
 e.waitUntil(self.registration.showNotification(d.title||'Find a flat',{body:d.body||'',icon:d.icon||undefined,tag:'ff-hourly',renotify:true,data:{url:d.url||'/#today'}}))});
self.addEventListener('notificationclick',e=>{e.notification.close();const u=(e.notification.data&&e.notification.data.url)||'/#today';
 e.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(l=>{for(const c of l){if('focus' in c){c.navigate&&c.navigate(u);return c.focus()}}return clients.openWindow(u)}))});
self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(clients.claim()));
"""


def apply_patch(entry, body, user):
    """The same rules as the owner's local app: status, note, follow-up, mark and wrong report. Returns an error text or None."""
    status, mk, wr = body.get("status"), body.get("marked"), body.get("wrong")
    if not (status in ALLOWED or "note" in body or body.get("followup") is True or isinstance(mk, bool) or wr is False or isinstance(wr, dict)
            or isinstance(body.get("log"), dict) or "visit_at" in body):
        return "bad status"
    if status is not None and status not in ALLOWED:
        return "bad status"
    t = now()
    if status is not None and entry.get("status") != status:
        entry["status"], entry["status_at"] = status, t
    if body.get("followup") is True:
        entry["fu_at"], entry["fu_n"] = t, entry.get("fu_n", 0) + 1
    if "note" in body:
        entry["note"] = str(body["note"])[:2000]
    if isinstance(mk, bool):
        entry["marked"], entry["marked_at"] = mk, t if mk else None
    if wr is False:
        entry.pop("wrong", None)
    elif isinstance(wr, dict):
        entry["wrong"] = {"note": str(wr.get("note", ""))[:300], "flags": [str(f)[:30] for f in (wr.get("flags") or [])][:20], "at": t}
    if isinstance(body.get("log"), dict):
        lg = body["log"]
        entry["log"] = (entry.get("log") or [])[-59:] + [{"t": t, "k": str(lg.get("k", ""))[:20], "d": str(lg.get("d", ""))[:140], "by": user}]
    if "visit_at" in body:
        v = str(body["visit_at"])
        entry["visit_at"] = v if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d", v) else ""
        entry["visit_note"] = str(body.get("visit_note", ""))[:200]
        if entry["visit_at"] and entry.get("status") in (None, "new", "contacted", "replied"):
            entry["status"], entry["status_at"] = "visit", t
    entry["at"], entry["by"] = t, user                                # who changed it last
    return None


class H(BaseHTTPRequestHandler):
    server_version = "flatfinder"

    # ---- helpers
    def client(self):
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def send(self, code, body, ctype="application/json", extra=None):
        if not isinstance(body, bytes):
            body = (body if isinstance(body, str) else json.dumps(body)).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "strict-origin-when-cross-origin", **(extra or {})}.items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def who(self):
        """('admin'|'user', name) or None. Admin = the owner's publish token; user = a Basic-auth login."""
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer ") and TOKEN and hmac.compare_digest(auth[7:].strip(), TOKEN):
            return "admin", (self.headers.get("X-By") or "owner")[:20].lower()
        if auth.startswith("Basic "):
            import base64
            try:
                user, _, pw = base64.b64decode(auth[6:]).decode().partition(":")
            except Exception:
                return None
            ok = False
            for name, real in USERS.items():                            # compare against every user so the timing does not reveal which names exist
                ok |= hmac.compare_digest(name, user.strip().lower()) & hmac.compare_digest(real, pw)
            if ok:
                return "user", user.strip().lower()
        return None

    def gate(self):
        """Returns (kind, name) for an allowed request, or sends the 401/429 itself and returns None."""
        ip, t = self.client(), time.time()
        FAILS[ip] = [x for x in FAILS.get(ip, []) if t - x < 600]
        if len(FAILS[ip]) >= 8:
            self.send(429, {"error": "too many wrong passwords, try again in 10 minutes"})
            return None
        w = self.who()
        if w:
            return w
        if self.headers.get("Authorization"):
            FAILS[ip].append(t)
            time.sleep(0.6)
        self.send(401, "Login required", "text/plain", {"WWW-Authenticate": 'Basic realm="Nestbox"'})
        return None

    # ---- GET
    def do_GET(self):
        if self.path == "/health":
            return self.send(200, "ok", "text/plain")
        if self.headers.get("X-Forwarded-Proto") == "http" and os.environ.get("REQUIRE_HTTPS"):
            return self.send(301, "", "text/plain", {"Location": "https://" + (self.headers.get("Host") or "") + self.path})
        w = self.gate()
        if not w:
            return
        kind, user = w
        p = self.path.split("?")[0]
        if p in ("/", "/index.html", "/listings.html"):
            return self.page(user)
        if p == "/api/status":
            return self.send(200, read_json("statuses.json", {}))
        if p == "/sw.js":
            return self.send(200, SW_JS, "application/javascript", {"Service-Worker-Allowed": "/"})
        if p == "/api/push/key":
            try:
                return self.send(200, {"key": vapid_public(), "supported": bool(webpush)}) if webpush else self.send(200, {"supported": False})
            except Exception:
                return self.send(200, {"supported": False})
        if p == "/api/search":                                              # phone, email, address or any word: the descriptions and your notes
            qs = (parse_qs(self.path.partition("?")[2]).get("q") or [""])[0][:100]
            status = read_json("statuses.json", {})
            docs = {}
            for lid, text in descriptions().items():
                e = status.get(lid) or {}
                docs[lid] = [("ad", lid), ("description", text), ("your note", e.get("note", "")), ("history", " ; ".join(x.get("d", "") for x in e.get("log", [])))]
            return self.send(200, {lid: [{"where": w, "text": s} for w, s in hits] for lid, hits in search.run(qs, docs).items()})
        if p == "/api/fun":
            return self.send(200, fun_state(user))
        m = re.fullmatch(r"/fun/(fun_[a-z0-9_]+)\.(jpg|png|webp|gif)", p)
        if m:
            try:
                with open(path(m.group(1) + "." + m.group(2)), "rb") as f:
                    return self.send(200, f.read(), IMG_TYPES[m.group(2)], {"Cache-Control": "private, max-age=3600", "Content-Security-Policy": "default-src 'none'; sandbox"})
            except OSError:
                return self.send(404, "not found", "text/plain")
        if p == "/api/whoami":
            return self.send(200, {"user": user, "kind": kind})
        if p == "/api/run":                                              # the page polls this: report "nothing running" and when the page was last published
            try:
                upd = os.path.getmtime(path("listings.html"))
            except OSError:
                upd = None
            return self.send(200, {"running": False, "listings_updated": upd, "progress": None, "cloud": True})
        if p == "/api/listing":
            lid = (parse_qs(self.path.partition("?")[2]).get("id") or [""])[0]
            text = descriptions().get(lid) if re.fullmatch(r"[A-Za-z0-9_-]{3,60}", lid) else None
            return self.send(200, {"html": describe.highlight_html(text) if text else "<i>No text stored for this listing.</i>", "chars": len(text or "")})
        m = re.fullmatch(r"/logos/([a-z0-9]+\.(svg|png|webp|ico))", p)
        if m:
            ctype = {"svg": "image/svg+xml", "png": "image/png", "webp": "image/webp", "ico": "image/x-icon"}[m.group(2)]
            try:
                with open(os.path.join(HERE, "logos", m.group(1)), "rb") as f:
                    return self.send(200, f.read(), ctype, {"Cache-Control": "private, max-age=86400", "Content-Security-Policy": "default-src 'none'; sandbox"})
            except OSError:
                return self.send(404, "not found", "text/plain")
        self.send(404, {"error": "not found"})

    def page(self, user):
        try:
            mtime = os.path.getmtime(path("listings.html"))
        except OSError:
            return self.send(200, "<h2>No listings published yet.</h2><p>The owner publishes after each scrape.</p>", "text/html; charset=utf-8")
        key = (mtime, user)
        if key not in CACHE:
            CACHE.clear()
            with open(path("listings.html"), encoding="utf-8") as f:
                html = f.read()
            inject = '<script>window.FF_CLOUD=%s;</script>' % json.dumps({"user": user})
            CACHE[key] = gzip.compress(html.replace("<head>", "<head>" + inject, 1).encode("utf-8"), 6)
        raw = CACHE[key]
        if "gzip" in self.headers.get("Accept-Encoding", ""):
            return self.send(200, raw, "text/html; charset=utf-8", {"Content-Encoding": "gzip", "Vary": "Accept-Encoding"})
        self.send(200, gzip.decompress(raw), "text/html; charset=utf-8")

    # ---- POST / PUT
    def body(self, limit):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n > limit:
            return None
        data = self.rfile.read(n)
        return data if len(data) == n else None                      # an upload that broke off half way is refused, never saved

    def do_POST(self):
        w = self.gate()
        if not w:
            return
        kind, user = w
        if self.path.startswith("/api/fun/") and fun_post(self, kind, user, self.path):
            return
        if self.path.startswith("/api/push/") and push_post(self, kind, user, self.path):
            return
        if self.path != "/api/status":
            return self.send(403, {"error": "this is the shared copy: scraping, settings and adding links stay on the owner's computer"})
        raw = self.body(20_000)
        try:
            b = json.loads(raw or b"{}")
            lid = str(b["id"])[:40]
            assert isinstance(b, dict) and re.fullmatch(r"[A-Za-z0-9_-]{3,60}", lid)
        except Exception:
            return self.send(400, {"error": "bad request"})
        who = str(b.get("by") or user)[:20].lower() if kind == "admin" else user          # the owner's Mac says who made the change
        with LOCK:
            data = read_json("statuses.json", {})
            entry = data.get(lid, {"status": "new", "note": ""})
            err = apply_patch(entry, b, who)
            if err:
                return self.send(400, {"error": err})
            data[lid] = entry
            write_atomic("statuses.json", json.dumps(data, indent=1, ensure_ascii=False))
        self.send(200, {})

    def do_PUT(self):
        w = self.gate()
        if not w:
            return
        kind, user = w
        if kind != "admin":
            return self.send(403, {"error": "only the owner can publish"})
        if self.path == "/api/statuses":                               # the owner's Mac merges its notebook with this one: the newer entry wins
            raw = self.body(5_000_000)
            try:
                theirs = json.loads(raw or b"{}")
                assert isinstance(theirs, dict)
            except Exception:
                return self.send(400, {"error": "bad json"})
            with LOCK:
                mine = read_json("statuses.json", {})
                for lid, e in theirs.items():
                    if re.fullmatch(r"[A-Za-z0-9_-]{3,60}", str(lid)) and isinstance(e, dict):
                        old = mine.get(lid, {})
                        win, lose = (e, old) if str(e.get("at", "")) >= str(old.get("at", "")) else (old, e)
                        merged = dict(win)
                        if win.get("log") or lose.get("log"):                           # both sides' history is kept
                            seen, logs = set(), []
                            for x in (win.get("log") or []) + (lose.get("log") or []):
                                k = (x.get("t"), x.get("k"), x.get("d"))
                                if k not in seen:
                                    seen.add(k)
                                    logs.append(x)
                            merged["log"] = sorted(logs, key=lambda x: x.get("t", ""))[-60:]
                        mine[lid] = merged
                write_atomic("statuses.json", json.dumps(mine, indent=1, ensure_ascii=False))
            return self.send(200, mine)
        m = re.fullmatch(r"/api/files/([a-z_.]+)", self.path)
        if not m or m.group(1) not in FILES:
            return self.send(404, {"error": "unknown file"})
        raw = self.body(MAX_UPLOAD)
        if not raw:
            return self.send(400, {"error": "empty, too large or cut off"})
        if self.headers.get("Content-Encoding") == "gzip":
            try:
                d = zlib.decompressobj(31)
                raw = d.decompress(raw, MAX_UPLOAD)
                if d.unconsumed_tail or not d.eof:
                    raise ValueError("incomplete or too large")
            except Exception:
                return self.send(400, {"error": "bad gzip"})
        if m.group(1) == "listings.html" and b"</html>" not in raw[-400:]:
            return self.send(400, {"error": "the page is incomplete"})
        if m.group(1) == "descriptions.json":
            try:
                assert isinstance(json.loads(raw), dict)
            except Exception:
                return self.send(400, {"error": "bad json"})
        write_atomic(m.group(1), raw)
        CACHE.clear()
        self.send(200, {"saved": m.group(1), "bytes": len(raw)})

    def do_DELETE(self):
        w = self.gate()
        if not w:
            return
        m = re.fullmatch(r"/api/status/([A-Za-z0-9_-]{3,60})", self.path)
        if w[0] != "admin" or not m:
            return self.send(403, {"error": "only the owner can delete an entry"})
        with LOCK:
            data = read_json("statuses.json", {})
            gone = data.pop(m.group(1), None) is not None
            write_atomic("statuses.json", json.dumps(data, indent=1, ensure_ascii=False))
        self.send(200, {"deleted": gone})

    def log_message(self, *a):
        pass


if __name__ == "__main__":
    if not USERS or not TOKEN:
        raise SystemExit("USERS and PUBLISH_TOKEN must be set")
    print(f"nestbox (shared copy) on port {PORT}, data in {DATA}, {len(USERS)} users", flush=True)
    threading.Thread(target=push_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", PORT), H).serve_forever()
