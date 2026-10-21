"""Links your Gmail to the flats, read-only, so a reply shows up on the right card.

No code is put in your emails. Replies are matched by what is already natural in them:
- the flat's address or listing number in the subject or text (strong match),
- a thread that started from the subject of a message sent from the "Gmail" button on the card (that subject names the address),
- the agency's name (weak match: shown as "possible reply" and you confirm it).

Setup (once): see README "Link your Gmail", then   python3 mail_link.py connect
Only the read-only Gmail scope is requested; the program can never send, delete or change mail. Mail text stays on this Mac (mail.json): the shared copy
only learns that a flat got a reply (its status becomes "replied"), never the text.
"""
import base64, hashlib, html, http.server, json, os, re, secrets, sys, tempfile, threading, time, urllib.error, urllib.parse, urllib.request, webbrowser
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT_FILE = os.path.join(HERE, "gmail_client.json")      # downloaded from Google Cloud (OAuth client, type "Desktop app")
TOKEN_FILE = os.path.join(HERE, "gmail_token.json")        # written by "connect"; keep private
DATA_FILE = os.path.join(HERE, "mail.json")
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
AUTH_URL, TOKEN_URL, API = "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "https://gmail.googleapis.com/gmail/v1/users/me"
ACTIVE = ("contacted", "replied", "visit", "applied")        # flats worth checking the inbox for
PLATFORMS = ("housinganywhere", "spotahome")                 # every mail from these comes from the platform, so the sender says nothing about WHICH flat
AUTOMATED_SUBJECT = re.compile(r"welcome to|newsletter|fresh finds|new places in|unsubscribe|verify your|confirm your (e-?mail|account)|your (weekly|daily)|recommended for you|price drop|saved search|bienvenue|nieuwsbrief", re.I)
AUTOMATED_FROM = re.compile(r"no-?reply|do-?not-?reply|newsletter|mailer-daemon|notifications?@|marketing@|news@", re.I)
LOCK = threading.Lock()
_TOKEN = {"access": None, "exp": 0}


# ------------------------------------------------------------------ files
def _read(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write(path, data, private=False):
    fd, tmp = tempfile.mkstemp(dir=HERE)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    if private:
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def load():
    return _read(DATA_FILE, {"msgs": {}, "manual": {}, "me": "", "last_poll": 0, "error": ""})


# ------------------------------------------------------------------ Google sign-in (once)
def _client():
    c = _read(CLIENT_FILE, None)
    c = (c or {}).get("installed") or (c or {}).get("web")
    if not c or not c.get("client_id"):
        raise SystemExit("gmail_client.json is missing or not an OAuth client file. See README, section 'Link your Gmail'.")
    return c


def _b64(b):
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def connect():
    """Opens Google's sign-in page in your browser; stores a refresh token (read-only Gmail) in gmail_token.json."""
    c = _client()
    verifier = secrets.token_urlsafe(64)
    state = secrets.token_urlsafe(16)
    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state") == [state] and q.get("code"):
                result["code"] = q["code"][0]
                msg = "Connected. You can close this tab and go back to the terminal."
            else:
                result["error"] = (q.get("error") or ["unexpected request"])[0]
                msg = "Sign-in did not complete: " + result["error"]
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{srv.server_port}/"
    url = AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": c["client_id"], "redirect_uri": redirect, "response_type": "code", "scope": SCOPE, "state": state,
        "code_challenge": _b64(hashlib.sha256(verifier.encode()).digest()), "code_challenge_method": "S256", "access_type": "offline", "prompt": "consent"})
    print("Opening Google's sign-in page. If nothing opens, copy this link into your browser:\n" + url + "\n")
    webbrowser.open(url)
    srv.timeout = 300
    srv.handle_request()
    srv.server_close()
    if "code" not in result:
        raise SystemExit("Not connected: " + result.get("error", "timed out"))
    tok = _post_form(TOKEN_URL, {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""), "code": result["code"], "code_verifier": verifier,
                                 "redirect_uri": redirect, "grant_type": "authorization_code"})
    if not tok.get("refresh_token"):
        raise SystemExit("Google did not return a refresh token. Remove the app at myaccount.google.com/permissions and run connect again.")
    _write(TOKEN_FILE, {"refresh_token": tok["refresh_token"]}, private=True)
    _TOKEN.update(access=tok.get("access_token"), exp=time.time() + int(tok.get("expires_in", 3000)) - 60)
    print("Connected as", profile().get("emailAddress", "?"))


def _post_form(url, fields):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(fields).encode(), method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Google said {e.code}: {e.read()[:200].decode('utf-8', 'replace')}")


def _access():
    if _TOKEN["access"] and time.time() < _TOKEN["exp"]:
        return _TOKEN["access"]
    t = _read(TOKEN_FILE, None)
    if not t:
        raise RuntimeError("not connected")
    c = _client()
    tok = _post_form(TOKEN_URL, {"client_id": c["client_id"], "client_secret": c.get("client_secret", ""), "refresh_token": t["refresh_token"], "grant_type": "refresh_token"})
    _TOKEN.update(access=tok["access_token"], exp=time.time() + int(tok.get("expires_in", 3000)) - 60)
    return _TOKEN["access"]


def api(path, params=None):
    """GET on the Gmail API (read-only)."""
    url = API + path + (("?" + urllib.parse.urlencode(params, doseq=True)) if params else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + _access()})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gmail said {e.code}")


def profile():
    return api("/profile")


def connected():
    return os.path.exists(TOKEN_FILE) and os.path.exists(CLIENT_FILE)


# ------------------------------------------------------------------ matching
def terms(lid, c):
    """(strong, weak) search terms for one catalog entry. Strong: its address with a house number, its listing number. Weak: the agency name."""
    strong, weak = [], []
    street = (c.get("street") or "").strip()
    if street and re.search(r"\d", street) and len(street) >= 6:
        strong.append(f'"{street}"')
    ref = lid.split("-", 1)[-1]
    if len(ref) >= 5 and re.search(r"\d{4}", ref):
        strong.append(f'"{ref}"')
    ag = (c.get("agency") or "").strip()
    if len(ag) >= 4 and not re.fullmatch(r"(?i)private|particulier|privé|none|n/a", ag):
        weak.append(f'"{ag}"')
    return strong, weak


def _hdr(m, name):
    for h in (m.get("payload") or {}).get("headers", []):
        if h["name"].lower() == name:
            return h["value"]
    return ""


BRANDS = {"housinganywhere": "housinganywhere", "airbnb": "airbnb", "booking.com": "booking", "spotahome": "spotahome", "immoweb": "immoweb", "immovlan": "immovlan", "2ememain": "2ememain"}
FREEMAIL = re.compile(r"@(gmail|googlemail|outlook|hotmail|live|yahoo|proton|protonmail|icloud|gmx|mail)\.", re.I)


def scam(frm, subject, snippet):
    """A free-mail address (gmail, outlook...) that talks like a platform ("Welcome to HousingAnywhere", "Immoweb - Interest in your ad") is how rental scams start."""
    if not FREEMAIL.search(frm or ""):
        return False
    text = f"{subject} {snippet}".lower()
    return any(b in text for b in BRANDS) and not any(b in (frm or "").lower() for b in BRANDS.values())


def automated(raw):
    """Marketing, welcome and notification mail: it is never a landlord's answer."""
    if "CATEGORY_PROMOTIONS" in (raw.get("labelIds") or []) or _hdr(raw, "list-unsubscribe") or _hdr(raw, "auto-submitted").lower().startswith("auto") or _hdr(raw, "precedence").lower() in ("bulk", "list", "junk"):
        return True
    return bool(AUTOMATED_SUBJECT.search(_hdr(raw, "subject")) or AUTOMATED_FROM.search(_hdr(raw, "from")))


def _msg(raw, me, strong):
    return {"t": raw.get("threadId", ""), "from": _hdr(raw, "from")[:120], "to": _hdr(raw, "to")[:120], "subject": html.unescape(_hdr(raw, "subject"))[:160],
            "date": datetime.fromtimestamp(int(raw.get("internalDate", 0)) / 1000).strftime("%Y-%m-%dT%H:%M"), "snippet": html.unescape(raw.get("snippet") or "")[:240],
            "mine": bool(me) and me.lower() in _hdr(raw, "from").lower(), "strong": strong}


def poll(catalog, statuses, api_fn=None, days=45, limit=40, now=None, subjects=None):
    """Checks the inbox for the flats you contacted. Returns the list of new replies [(lid, msg)] (messages from others that were not stored before)."""
    api_fn = api_fn or api
    now = now or time.time()
    with LOCK:
        d = load()
        d["error"] = ""
        try:
            if not d.get("me"):
                d["me"] = api_fn("/profile").get("emailAddress", "")
            todo = [(lid, catalog[lid]) for lid, e in statuses.items() if lid in catalog and e.get("status") in ACTIVE][:limit]
            new = []
            agency_flats = {}
            for lid, c in todo:
                for w in terms(lid, c)[1]:
                    agency_flats.setdefault(w, set()).add(lid)
            for mid in [k for k, v in d["msgs"].items() if AUTOMATED_SUBJECT.search(v.get("subject", "")) or AUTOMATED_FROM.search(v.get("from", ""))]:
                del d["msgs"][mid]                                       # mail stored before these rules existed
            subj_count = {}
            for s in (subjects or {}).values():
                subj_count[s] = subj_count.get(s, 0) + 1
            for lid, c in todo:
                strong, weak = terms(lid, c)
                s = (subjects or {}).get(lid)
                if s:                                   # the subject of the draft the Gmail button made: a reply keeps it ("Re: ...")
                    (strong if subj_count[s] == 1 else weak).append(f'subject:"{s}"')
                for q_terms, is_strong in ((strong, True), (weak, False)):
                    if not q_terms:
                        continue
                    if not is_strong and len(agency_flats.get(q_terms[0], ())) == 1 and c.get("source") not in PLATFORMS:
                        is_strong = True            # the only flat you contacted at this agency: its mails can only be about this flat (not for platforms: they mail about everything)
                    res = api_fn("/messages", {"q": f"({' OR '.join(q_terms)}) newer_than:{days}d", "maxResults": 15})
                    for ref in res.get("messages", []) or []:
                        key = d["msgs"].get(ref["id"])
                        if key and (key["strong"] or not is_strong) and lid in key.get("lids", []):
                            continue
                        raw = api_fn("/messages/" + ref["id"], {"format": "metadata", "metadataHeaders": ["From", "To", "Subject", "Date", "List-Unsubscribe", "Auto-Submitted", "Precedence"]})
                        if automated(raw):
                            continue
                        m = d["msgs"].get(ref["id"]) or _msg(raw, d["me"], is_strong)
                        first = ref["id"] not in d["msgs"]
                        m["strong"] = m.get("strong") or is_strong
                        m.setdefault("lids", [])
                        if lid not in m["lids"]:
                            m["lids"].append(lid)
                        d["msgs"][ref["id"]] = m
                        if first and not m["mine"] and m["strong"]:
                            new.append((lid, m))
            # a thread that holds a strong match belongs to that flat: its other messages (for example the landlord's short answers) follow it
            by_thread = {}
            for mid, m in d["msgs"].items():
                if m["strong"]:
                    by_thread.setdefault(m["t"], set()).update(m["lids"])
            for mid, m in d["msgs"].items():
                if not m["strong"] and by_thread.get(m["t"]):
                    m["strong"], m["lids"] = True, sorted(by_thread[m["t"]])
                    if not m["mine"]:
                        new.append((m["lids"][0], m))
            cutoff = datetime.fromtimestamp(now - 90 * 86400).strftime("%Y-%m-%dT%H:%M")
            d["msgs"] = {k: m for k, m in d["msgs"].items() if m["date"] >= cutoff}
            d["last_poll"] = now
        except Exception as e:
            d["error"] = f"{type(e).__name__}: {e}"[:200]
            new = []
        _write(DATA_FILE, d)
    return new


def summary():
    """What the page needs per flat: {lid: {"in": n, "out": n, "last": {...}, "maybe": [...]}}; manual answers (confirm / reject) are applied."""
    d = load()
    out = {}
    for mid, m in d["msgs"].items():
        for lid in m.get("lids", []):
            verdict = d["manual"].get(f"{mid}:{lid}")
            if verdict is False:
                continue
            strong = m["strong"] or verdict is True
            o = out.setdefault(lid, {"in": 0, "out": 0, "last": None, "last_out": "", "maybe": []})
            row = {"id": mid, "thread": m["t"], "from": m["from"], "subject": html.unescape(m["subject"]), "date": m["date"], "snippet": html.unescape(m["snippet"]), "scam": scam(m["from"], m["subject"], m["snippet"])}
            if not strong:
                if not m["mine"]:
                    o["maybe"].append(row)
                continue
            o["out" if m["mine"] else "in"] += 1
            if m["mine"] and m["date"] > o["last_out"]:
                o["last_out"] = m["date"]
            if not m["mine"] and (not o["last"] or row["date"] > o["last"]["date"]):
                o["last"] = row
    return out


def decide(mid, lid, ok):
    with LOCK:
        d = load()
        d["manual"][f"{mid}:{lid}"] = bool(ok)
        _write(DATA_FILE, d)


def info():
    d = load()
    return {"client_file": os.path.exists(CLIENT_FILE), "connected": connected(), "me": d.get("me", ""), "last_poll": d.get("last_poll", 0), "error": d.get("error", ""), "messages": len(d.get("msgs", {}))}


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "connect":
        connect()
    elif cmd == "status":
        print(json.dumps(info(), indent=1))
    elif cmd == "poll":
        st = _read(os.path.join(HERE, "state.json"), {})
        res = poll(st.get("catalog", {}), _read(os.path.join(HERE, "statuses.json"), {}))
        print(f"{len(res)} new replies;", json.dumps(info()))
    else:
        print("usage: python3 mail_link.py connect | status | poll")
