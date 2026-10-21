"""Publishes the listings page to the shared copy on Railway and keeps the notebook (marks, statuses, notes) in sync, both ways.

Settings live in .env next to this file:  CLOUD_URL=https://....up.railway.app   CLOUD_TOKEN=<the owner's publish token>   CLOUD_OWNER=you
Nothing is sent unless CLOUD_URL and CLOUD_TOKEN are set. What is sent: the finished listings page and the listing descriptions (the text of the
ads), over HTTPS to your own Railway service. Never sent: .env, the Gemini key, config.json, state.json, the run history.
"""
import gzip, json, os, tempfile, threading, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
_CACHE = {"t": 0.0, "data": None}
STATUS_FILE = os.path.join(HERE, "cloud_status.json")


def settings():
    env = {}
    try:
        with open(os.path.join(HERE, ".env")) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                env[k.strip()] = v.strip().strip("'\"")
    except OSError:
        pass
    for k in ("CLOUD_URL", "CLOUD_TOKEN", "CLOUD_OWNER"):
        env[k] = os.environ.get(k) or env.get(k, "")
    if not (env["CLOUD_URL"].startswith("https://") and env["CLOUD_TOKEN"]):
        return None
    return {"url": env["CLOUD_URL"].rstrip("/"), "token": env["CLOUD_TOKEN"], "owner": (env["CLOUD_OWNER"] or "owner").lower()[:20]}


def _request(cfg, method, path, body=None, ctype="application/octet-stream", timeout=60, gz=False):
    headers = {"Authorization": "Bearer " + cfg["token"], "X-By": cfg["owner"], "Content-Type": ctype, "User-Agent": "flat-finder-publisher"}
    if gz and body:                                                    # the page is 6 MB of text: compressed it is a few hundred KB, so a weak connection can still finish the upload
        body, headers["Content-Encoding"] = gzip.compress(body, 6), "gzip"
    req = urllib.request.Request(cfg["url"] + path, data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    fd, tmp = tempfile.mkstemp(dir=HERE)
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def merge(a, b):
    """Two notebooks: for each listing the entry changed most recently wins."""
    out = dict(a)
    for lid, e in b.items():
        old = out.get(lid) or {}
        win, lose = (e, old) if str(e.get("at", "")) >= str(old.get("at", "")) else (old, e)
        merged = dict(win)
        if win.get("log") or lose.get("log"):                                  # both sides' history is kept
            seen, logs = set(), []
            for x in (win.get("log") or []) + (lose.get("log") or []):
                k = (x.get("t"), x.get("k"), x.get("d"))
                if k not in seen:
                    seen.add(k)
                    logs.append(x)
            merged["log"] = sorted(logs, key=lambda x: x.get("t", ""))[-60:]
        out[lid] = merged
    return out


def publish():
    """Push the page and the descriptions, then reconcile the notebooks. Returns a short summary (also stored for the control panel)."""
    cfg = settings()
    if not cfg:
        return {"configured": False}
    t0 = time.time()
    res = {"configured": True, "url": cfg["url"], "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    try:
        with open(os.path.join(HERE, "listings.html"), "rb") as f:
            page = f.read()
        _request(cfg, "PUT", "/api/files/listings.html", page, "text/html", timeout=120, gz=True)
        state = _read_json(os.path.join(HERE, "state.json"), {})
        desc = {lid: d["description"] for lid, d in state.get("details", {}).items() if d.get("description") and lid in state.get("catalog", {})}
        _request(cfg, "PUT", "/api/files/descriptions.json", json.dumps(desc, ensure_ascii=False).encode(), "application/json", timeout=120, gz=True)
        local = _read_json(os.path.join(HERE, "statuses.json"), {})
        remote = json.loads(_request(cfg, "GET", "/api/status") or b"{}")
        merged = merge(local, remote)
        _write_json(os.path.join(HERE, "statuses.json"), merged)
        _request(cfg, "PUT", "/api/statuses", json.dumps(merged).encode(), "application/json")
        res.update(ok=True, page_kb=len(page) // 1024, descriptions=len(desc), statuses=len(merged), seconds=round(time.time() - t0, 1))
    except Exception as e:                                             # publishing must never break a scrape
        res.update(ok=False, error=f"{type(e).__name__}: {str(e)[:150]}")
    _write_json(STATUS_FILE, res)
    return res


def forward_status(body):
    """A mark / note / status you just made locally: send the same change to the shared copy (best effort)."""
    cfg = settings()
    if not cfg:
        return
    try:
        _request(cfg, "POST", "/api/status", json.dumps({**body, "by": cfg["owner"]}).encode(), "application/json", timeout=8)
    except Exception:
        pass                                                           # it will be reconciled at the next publish


def merged_statuses(local):
    """Your notebook plus what your friend changed on the shared copy (cached for 15 s; falls back to the local one if the cloud is unreachable)."""
    cfg = settings()
    if not cfg:
        return local
    if time.time() - _CACHE["t"] > 15:
        try:
            _CACHE["data"] = json.loads(_request(cfg, "GET", "/api/status", timeout=4) or b"{}")
        except Exception:
            _CACHE["data"] = None
        _CACHE["t"] = time.time()
    return merge(local, _CACHE["data"]) if _CACHE["data"] else local


def last_status():
    return _read_json(STATUS_FILE, None)


def proxy(method, path, body=None, ctype="application/json"):
    """The motivation features live on the shared copy; the local page talks to them through this. Returns (status, bytes, content type)."""
    cfg = settings()
    if not cfg:
        return 503, b'{"error": "the shared copy is not set up (CLOUD_URL / CLOUD_TOKEN in .env)"}', "application/json"
    req = urllib.request.Request(cfg["url"] + path, data=body, method=method, headers={
        "Authorization": "Bearer " + cfg["token"], "X-By": cfg["owner"], "Content-Type": ctype, "User-Agent": "flat-finder-publisher"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read(), r.headers.get("Content-Type", "application/json")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type", "application/json")
    except Exception:
        return 502, b'{"error": "the shared copy is unreachable"}', "application/json"
