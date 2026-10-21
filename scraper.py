#!/usr/bin/env python3
"""Nestbox, the scraper: Brussels, Dec 2026 - Apr 2027, near EUROCONTROL (Haren).

    python3 scraper.py                 # normal run (2-3 times a day is plenty)
    python3 scraper.py --offline       # re-score the saved catalog without any request (also re-uses cached AI results)
    python3 scraper.py --notify        # also send a macOS notification for new high-score listings
    python3 scraper.py --max 1200      # override the budget in config.json
    python3 scraper.py --no-ai         # skip the Gemini description analysis

Reads public search pages of Immoweb, Immovlan and 2ememain (only paths their robots.txt allows,
2-4 s between requests, stops a source at the first 403/429), then scores and ranks everything.
Listings not seen for 2 full runs are marked "possibly taken". Edit config.json for your details.
Only the Python standard library is used.
"""
import argparse, hashlib, json, os, re, signal, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
from datetime import date, datetime, timedelta

import firstrun, gemini, messages, progress as prog, report, scoring, sources

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, "state.json")
HISTORY = os.path.join(HERE, "history.json")
MANUAL = os.path.join(HERE, "manual.json")          # listings you added by link: {id: item}, merged into the catalog on every run
LOGDIR = os.path.join(HERE, "logs")
REQ = {}
DETAIL_KEYS = ("description", "furnished", "kitchen", "available", "charges", "bedrooms", "m2", "phone", "website", "contact_hours",
               "lat", "lon", "approx_pos", "modified", "agency_foreign", "geo_checked", "min_stay_months", "postal", "street", "created", "views", "saves", "has_washer", "has_fridge", "bathrooms", "toilets", "rechecked_at", "no_text", "deposit", "admin_fee", "platform_fee", "monthly_extra", "monthly_extra_parts", "max_stay_months", "couples_ok", "struct_shared", "rooms", "specs_v")
# computed per run, never stored in the catalog (search-time facts like rent, size, coordinates stay in it)
DERIVED = ("flags", "score", "new", "total", "good", "minutes", "how", "km", "also", "ai", "verified", "gone", "description")


PROGRESS = None


def planned_requests(cfg):
    """Upper estimate of the search requests (areas that have few listings stop after one page)."""
    n_areas = len(cfg.get("enabled_areas") or cfg["areas"])
    n = n_areas * (2 * cfg["pages_per_area"] + cfg["furnished_pages_per_area"]) + 6
    if cfg.get("midterm_enabled", True):
        n += len(cfg.get("housinganywhere_places", [])) + cfg.get("spotahome_pages", 2)
    return n


READERS = {"immoweb": sources.immoweb_details, "immovlan": sources.immovlan_details, "spotahome": sources.spotahome_details, "housinganywhere": sources.housinganywhere_details}


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def followups_due(cfg=None):
    """Contacted flats with no reply: some days after the first message, then some days after each follow-up, at most N follow-ups (config.json: followup_first_days 2,
    followup_next_days 3, followup_max 2; changeable in the control panel)."""
    cfg = cfg or load_json(os.path.join(HERE, "config.json"), {})
    first, nxt, mx = cfg.get("followup_first_days", 2), cfg.get("followup_next_days", 3), cfg.get("followup_max", 2)
    n = 0
    for e in load_json(os.path.join(HERE, "statuses.json"), {}).values():
        if e.get("status") != "contacted" or e.get("fu_n", 0) >= mx:
            continue
        try:
            age = (datetime.now() - datetime.fromisoformat(e.get("fu_at") or e.get("status_at") or e["at"])).total_seconds() / 86400
        except (KeyError, TypeError, ValueError):
            continue
        n += age >= (nxt if e.get("fu_n") else first)
    return n


def notify(title, text):
    esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')
    subprocess.run(["osascript", "-e", f'display notification "{esc(text)}" with title "{esc(title)}" sound name "Glass"'], check=False)


def fingerprint(c):
    """What a search result shows about a listing (price, charges, title, last-modified date). If it is the same as when the page was read, the page is unchanged."""
    return hashlib.sha1(f"{c.get('rent')}|{c.get('charges')}|{c.get('title')}|{c.get('modified')}".encode()).hexdigest()[:12]


TL = threading.local()                                       # requests made by the current search thread (the progress estimate needs a per-site count)


def collect(cfg, blocked):
    """Run all searches, the five sites side by side: each site is one thread that works through its own searches one request at a time
    (same politeness as before), so the total is about the slowest site instead of the sum of all of them.
    Returns (items, searched) where searched[(source, area)] = number of results."""
    jobs = []                                                # (source, area, label, fn, args, kw, planned), in the order the results are merged

    def add(source, area, label, fn, *args, planned=1, **kw):
        jobs.append((source, area, label, fn, args, kw, planned))

    enabled = cfg.get("enabled_areas") or list(cfg["areas"])
    for postal, a in cfg["areas"].items():
        if postal not in enabled:
            continue
        add("immoweb", postal, f"immoweb {postal} {a['immoweb']}", sources.immoweb_search, postal, a["immoweb"], cfg["pages_per_area"], max_pages=cfg.get("max_pages_per_area", 4), planned=cfg["pages_per_area"])
        if cfg["furnished_pages_per_area"]:
            add("immoweb", postal, f"immoweb {postal} furnished", sources.immoweb_search, postal, a["immoweb"], cfg["furnished_pages_per_area"], furnished=True, planned=cfg["furnished_pages_per_area"])
        add("immovlan", postal, f"immovlan {postal} {a['immovlan']}", sources.immovlan_search, postal, a["immovlan"], cfg["pages_per_area"], max_pages=cfg.get("max_pages_per_area", 4), planned=cfg["pages_per_area"])
    if cfg.get("midterm_enabled", True):               # platforms made for stays of a few months
        for place in cfg.get("housinganywhere_places", []):
            add("housinganywhere", place, f"housinganywhere {place}", sources.housinganywhere_search, place, scoring.EUROCONTROL, 12, scoring.km)
        add("spotahome", "", "spotahome brussels", sources.spotahome_search, cfg.get("spotahome_pages", 2), planned=cfg.get("spotahome_pages", 2))
    add("2ememain", "", "2ememain private ads", sources.ememain_search, 3, scoring.EUROCONTROL, 15, scoring.km, planned=6)

    out = [None] * len(jobs)
    lock = threading.Lock()

    def work(source, mine):                                  # one site: its searches one after the other
        for i in mine:
            _s, area, label, fn, args, kw, planned = jobs[i]
            if source in blocked:
                return
            TL.n = 0
            try:
                items = fn(*args, **kw)
            except sources.Blocked as e:
                blocked.add(source)
                with lock:
                    print(f"{label:34} BLOCKED ({e}); skipping {source} for this run")
                return
            with lock:
                print(f"{label:34} {len(items)}")
                PROGRESS.detail = label
                PROGRESS.adjust_total(-max(0, planned - TL.n))   # a small area stops after one page: shrink the estimate
            out[i] = items

    by_site = {}
    for i, j in enumerate(jobs):
        by_site.setdefault(j[0], []).append(i)
    with ThreadPoolExecutor(max_workers=max(1, len(by_site))) as pool:
        for fut in [pool.submit(work, src, idx) for src, idx in by_site.items()]:
            fut.result()                                     # a crash in one site's thread still stops the run, as before

    found, searched = {}, {}
    for i, (source, area, *_rest) in enumerate(jobs):        # merge in the original order, so the result is the same as when it ran one after the other
        if out[i] is None:
            continue
        searched[(source, area)] = searched.get((source, area), 0) + len(out[i])
        for it in out[i]:
            it["area"] = area
            if it["id"] in found:
                if it.get("furnished"):                  # same flat also came up in the furnished-only search
                    found[it["id"]]["furnished"] = True
            else:
                found[it["id"]] = it
    return list(found.values()), searched


def source_health(state, searched, blocked, path=None):
    """Did every site return about what it usually does? A site that suddenly returns 0 (or far fewer) listings has probably changed its pages or is blocking us:
    the page shows a warning instead of quietly listing fewer flats. 'typical' is the median of the last good runs, which a broken run never changes."""
    counts = Counter()
    for (src, _area), n in searched.items():
        counts[src] += n
    hist = state.setdefault("source_hist", {})
    health = {}
    for src in sorted(set(counts) | set(hist) | set(blocked)):
        prev, n = hist.get(src, []), counts.get(src, 0)
        typical = sorted(prev)[len(prev) // 2] if prev else None
        status = "blocked" if src in blocked else "zero" if n == 0 and (typical or 0) > 0 else "drop" if typical and n < 0.4 * typical else "ok"
        health[src] = {"count": n, "typical": typical, "status": status}
        if status == "ok":
            hist[src] = (prev + [n])[-10:]
    out = {"at": datetime.now().isoformat(timespec="minutes"), "sources": health}
    with open(path or os.path.join(HERE, "source_health.json"), "w") as f:
        json.dump(out, f, indent=1)
    return {k: v["status"] for k, v in health.items() if v["status"] != "ok"}


def update_catalog(state, fresh, searched, blocked, today):
    """Merge this run into the catalog and count how many runs each missing listing has been absent.
    A listing only counts as missed when its source was not blocked and its area search returned results
    (so a dropped wifi connection or a block never marks everything as taken)."""
    cat, details = state["catalog"], state["details"]
    ids, st = set(), {"added": 0, "seen_again": 0, "newly_possibly_taken": 0, "pruned": 0}
    for it in fresh:
        ids.add(it["id"])
        st["seen_again" if it["id"] in cat else "added"] += 1
        if it.get("description") and it["id"] not in details:      # 2ememain ships the text in the search result
            details[it["id"]] = {"description": it["description"]}
        base = {k: v for k, v in it.items() if k not in DERIVED}
        cat[it["id"]] = {**cat.get(it["id"], {}), **base, "last_seen": today, "seen_at": datetime.now().isoformat(timespec="minutes"), "missed": 0, "missed_at": 0}
        cat[it["id"]].setdefault("first_at", cat[it["id"]]["seen_at"])
    for lid, c in cat.items():
        if lid not in ids and not c.get("manual") and c["source"] not in blocked and searched.get((c["source"], c.get("area", "")), 0) > 0:
            if time.time() - c.get("missed_at", 0) >= 6 * 3600:        # one miss per 6 hours at most: several runs in an hour must not mark a flat "taken"
                c["missed"], c["missed_at"] = c.get("missed", 0) + 1, time.time()
                st["newly_possibly_taken"] += c["missed"] == 2
    cutoff = (date.fromisoformat(today) - timedelta(days=21)).isoformat()
    for lid in [k for k, c in cat.items() if c.get("last_seen", today) < cutoff and not c.get("manual")]:
        del cat[lid]
        st["pruned"] += 1
    return st


def _main(S):
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, help="budget incl. charges (default: config.json)")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--details", type=int, help="listing pages to read this run (default: config.json, about 3 s each)")
    ap.add_argument("--no-details", action="store_true")
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--ai", type=int, help="Gemini analyses this run (default: config.json)")
    ap.add_argument("--notify", action="store_true")
    ap.add_argument("--no-cloud", action="store_true", help="do not publish the page to the shared copy after this run")
    ap.add_argument("--prioritise", help="comma-separated listing ids that Gemini should check first")
    ap.add_argument("--read-only", action="store_true", help="skip the searches and only read listing pages (and run Gemini), best candidates first")
    ap.add_argument("--recheck", help="comma-separated listing ids: read their pages again and re-analyse them (no search)")
    a = ap.parse_args()
    ids_ok = lambda v: [x for x in (v or "").split(",") if re.fullmatch(r"[A-Za-z0-9_-]{3,60}", x)]
    recheck, prio = ids_ok(a.recheck), set(ids_ok(a.prioritise))
    if recheck:
        a.offline = True                                   # a recheck never searches: it only re-reads these listing pages
        prio |= set(recheck)
        S["recheck"] = recheck
    read_only = a.read_only and not recheck
    if read_only:
        a.offline = True                                   # no searches; reading pages below is still allowed
        S["read_only"] = True
    S["args"], S["offline"] = sys.argv[1:], a.offline

    firstrun.ensure_config()                                  # a fresh download has only config.example.json
    cfg = load_json(os.path.join(HERE, "config.json"), None)
    if (cfg.get("found_mode") or {}).get("on") and not (a.offline or a.recheck or a.read_only):
        print("Searching is paused: you found a flat. Resume it in the control panel or on the listings page.")
        return
    if a.max:
        cfg["budget"] = a.max
    if a.ai is not None:
        cfg["ai_per_run"] = a.ai
    state = {"seen": {}, "details": {}, "catalog": {}, "ai": {}}
    state.update(load_json(STATE, {}))
    today = date.today().isoformat()
    if not state["catalog"] and state.get("last"):                      # upgrade from the older state format
        state["catalog"] = {it["id"]: {**it, "last_seen": today, "missed": 0, "area": it.get("postal", "")} for it in state["last"]}

    manual = load_json(MANUAL, {})
    for lid, m in manual.items():                          # listings you added by link join the catalog and are never marked "taken"
        base = {k: v for k, v in m.items() if k not in DERIVED}
        prev = state["catalog"].get(lid)
        over = bool(prev) and bool(prev.get("manual_over_search") or not prev.get("manual"))        # the searches had already found this flat
        state["catalog"][lid] = {**base, **(prev or {}), "manual": True, "manual_over_search": over, "added_manually": m.get("added_manually"), "last_seen": today, "missed": 0}
        state["details"].setdefault(lid, {k: m[k] for k in DETAIL_KEYS if m.get(k) is not None})
        state["seen"].setdefault(lid, today)
    for lid in [k for k, c in state["catalog"].items() if c.get("manual") and k not in manual]:
        if state["catalog"][lid].get("manual_over_search"):         # the searches know this flat: just drop the "manual" status
            for k in ("manual", "manual_over_search", "added_manually"):
                state["catalog"][lid].pop(k, None)
        else:                                                       # it only exists because you added the link
            state["catalog"].pop(lid, None)
            state["details"].pop(lid, None)
    S["manual"] = len(manual)
    for lid in recheck:
        state["ai"].pop(lid, None)                         # force a fresh Gemini read of the new text
    first_run = state.setdefault("first_run", min(state["seen"].values(), default=today))
    blocked = set()
    global PROGRESS
    n_read = len(recheck) if recheck else 0 if ((a.offline and not read_only) or a.no_details) else (a.details if a.details is not None else cfg["detail_pages_per_run"])
    n_ai = 0 if a.no_ai else cfg["ai_per_run"] if gemini.api_key() else 0
    PROGRESS = prog.Progress({"search": 0 if a.offline else planned_requests(cfg), "read": n_read, "ai": n_ai, "build": 1})
    REQ.clear()

    def count_request():                                  # every finished request: progress bar + the per-run request counter
        REQ[PROGRESS.cur] = REQ.get(PROGRESS.cur, 0) + 1
        TL.n = getattr(TL, "n", 0) + 1
        PROGRESS.tick()
    sources.REQUEST_HOOK = count_request
    if not a.offline:
        PROGRESS.stage("search")
        fresh, searched = collect(cfg, blocked)
        S["found"], S["found_by_source"] = len(fresh), dict(Counter(it["source"] for it in fresh))
        S["catalog"] = update_catalog(state, fresh, searched, blocked, today)
        S["source_health"] = source_health(state, searched, blocked)

    all_items = [dict(c) for c in state["catalog"].values()]
    for it in all_items:
        it.update(state["details"].get(it["id"], {}))
        it["gone"] = it.get("missed", 0) >= 2
    items = scoring.dedupe(all_items)
    for it in items:
        scoring.analyse(it, cfg)

    # 1) read the full text of every candidate (budget + commute filters), best first, a batch per run
    candidates = [it for it in items if it["source"] in READERS and not it["gone"] and 550 <= it["rent"] <= cfg["budget"]
                  and (it["minutes"] or 0) <= cfg["read_max_minutes"] and "tiny" not in it["flags"]]
    # a listing page is (re)read when never read, or when an Immovlan page was read before we checked its map position
    stale_geo = lambda it: it["source"] == "immovlan" and not state["details"].get(it["id"], {}).get("geo_checked")
    def need_created(it):                       # read before we looked for the creation date, and the listing could be recent
        d = state["details"].get(it["id"])
        if not d or "created" in d or it["source"] not in ("immoweb", "immovlan"):
            return False
        m = it.get("modified")
        return not m or (date.today() - date.fromisoformat(m)).days <= cfg.get("new_days", 3) + 4
    def need_specs(it):                          # read before deposits, costs and availability were extracted: read once more
        d = state["details"].get(it["id"])
        return bool(d) and it["source"] in ("immovlan", "housinganywhere") and d.get("specs_v", 0) < 2
    # change detection: what the SEARCH shows (price, charges, title, last-modified) is fingerprinted when a page is read. A cached page is only read again
    # when that fingerprint changed (the ad was edited). Pages read before this existed get their fingerprint filled in silently, without a re-read.
    fails = state.setdefault("read_fail", {})
    cat = state["catalog"]
    for lid, d in state["details"].items():
        if "sfp" not in d and lid in cat:
            d["sfp"] = fingerprint(cat[lid])

    def changed(it):
        d = state["details"].get(it["id"])
        return bool(d) and d.get("sfp") not in (None, fingerprint(cat.get(it["id"], it)))

    def backed_off(it):                         # a page that keeps failing is not retried every run: next run, then after 1 day, then 3 days, then given up until the ad changes
        f = fails.get(it["id"])
        if not f:
            return False
        wait = (0, 0, 1, 3)[min(f["n"], 3)] if f["n"] < 5 else 10 ** 6
        return (date.today() - date.fromisoformat(f["last"])).days < wait and f.get("sfp") == fingerprint(cat.get(it["id"], it))
    for k in [k for k in fails if k not in cat]:
        del fails[k]                            # listings that left the catalog

    def note_fail(it):
        f = fails.get(it["id"], {"n": 0})
        fails[it["id"]] = {"n": f["n"] + 1, "last": date.today().isoformat(), "sfp": fingerprint(cat.get(it["id"], it))}
    cached_ok = sum(1 for it in candidates if it["id"] in state["details"] and not (stale_geo(it) or need_created(it) or need_specs(it) or changed(it)))
    unread = sorted((it for it in candidates if (it["id"] not in state["details"] and not backed_off(it)) or stale_geo(it) or need_created(it) or need_specs(it) or changed(it)),
                    key=lambda it: -it["score"])
    S["reads_skipped"] = cached_ok
    S["reads_changed"] = sum(1 for it in candidates if changed(it))
    S["reads_backed_off"] = sum(1 for it in candidates if it["id"] not in state["details"] and backed_off(it))
    gemini.USAGE.clear()
    gemini.USAGE.update(ok=0, failed=0, tokens_in=0, tokens_out=0)
    streamed = 0                                           # analyses already done by the background stream while pages were being read
    if recheck or read_only or not (a.offline or a.no_details):
        batch = [it for it in items if it["id"] in recheck and it["source"] in READERS] if recheck else unread[: a.details if a.details is not None else cfg["detail_pages_per_run"]]
        PROGRESS.stage("read", total=len(batch))
        S["read_attempted"] = len(batch)
        print(f"\nlisting pages to read: {len(batch)} of {len(unread)} unread candidates (best first); {S['reads_skipped']} cached pages unchanged and skipped, {S['reads_changed']} changed since the last read, {S['reads_backed_off']} failing pages waiting before a retry")
        stream = gemini.Stream(state["ai"], cfg, cfg["ai_per_run"], PROGRESS) if not a.no_ai else None     # Gemini works on each page as soon as it is read
        count_lock = threading.Lock()

        def read_site(src, its):                           # one site: its pages one after the other, with the usual 2-4 s pause between requests
            for it in its:
                if src in blocked:
                    return
                try:
                    READERS[src](it)
                except sources.Blocked as e:
                    blocked.add(src)
                    print(f"BLOCKED ({e})")
                    return
                except Exception as e:                     # one bad page must not stop the others
                    print(f"  ! could not read {it['url']}: {type(e).__name__}")
                    note_fail(it)
                    continue
                if recheck:
                    it["rechecked_at"] = datetime.now().isoformat(timespec="seconds")
                if (it.get("description") or it.get("page_read")) and (src != "spotahome" or it.get("geo_checked")):   # cache successes only, failures are retried
                    if not it.get("description"):
                        it["no_text"] = True                       # the page was read and the seller wrote no description at all
                    state["details"][it["id"]] = {k: it[k] for k in DETAIL_KEYS if it.get(k) is not None}
                    state["details"][it["id"]]["sfp"] = fingerprint(cat.get(it["id"], it))
                    state["details"][it["id"]]["read_at"] = datetime.now().isoformat(timespec="minutes")
                    fails.pop(it["id"], None)
                    with count_lock:
                        S["read_ok"] = S.get("read_ok", 0) + 1
                    if stream and it.get("description") and (it["id"] in prio or (not it["gone"] and it.get("total", it["rent"]) <= cfg["budget"])):
                        stream.submit(it)
                else:
                    note_fail(it)                                  # nothing usable came back: remember it, so the page is not hammered every run

        by_site = {}
        for it in batch:
            by_site.setdefault(it["source"], []).append(it)       # best candidates first inside each site
        if by_site:
            with ThreadPoolExecutor(max_workers=len(by_site)) as pool:      # different sites in parallel: still one request at a time per site
                list(pool.map(lambda kv: read_site(*kv), by_site.items()))
        streamed = stream.finish() if stream else 0

    # 2) Gemini reads the descriptions of the best listings (cached by text hash, so each text is paid for once)
    for it in all_items:                                   # pages were just read: merge twins again with the new street, price and cost facts
        it.update(state["details"].get(it["id"], {}))
    items = scoring.dedupe(all_items)
    if not a.no_ai:                                    # also in --offline: Gemini is not a listing site
        for it in items:
            scoring.analyse(it, cfg)
        ranked = sorted((it for it in items if it.get("description") and ((not it["gone"] and it.get("total", it["rent"]) <= cfg["budget"]) or it["id"] in prio)), key=lambda it: (it["id"] not in prio, -it["score"]))
        gemini.run(ranked, state["ai"], cfg, cfg["ai_per_run"] - streamed, progress=PROGRESS, already=streamed)       # what is left of the allowance, best first
        price = cfg.get("gemini_price") or {}
        u = gemini.USAGE
        S["ai"] = {"model": cfg.get("gemini_model"), "analyses": u["ok"], "failed": u["failed"], "tokens_in": u["tokens_in"], "tokens_out": u["tokens_out"],
                   "cost_est": round(u["tokens_in"] / 1e6 * price.get("input_per_million", 0.30) + u["tokens_out"] / 1e6 * price.get("output_per_million", 2.50), 5),
                   "stopped": u.get("stopped")}
    for it in items:
        cached = state["ai"].get(it["id"])
        it["ai"] = cached["r"] if cached and cached.get("h") == gemini.text_hash(it) else {}

    eligible = [it for it in items if it.get("description") and ((not it["gone"] and it.get("total", it["rent"]) <= cfg["budget"]) or it["id"] in prio)]
    n_checked = sum(1 for it in eligible if state["ai"].get(it["id"], {}).get("h") == gemini.text_hash(it))
    state["ai_stats"] = {"with_text": len(eligible), "checked": n_checked, "waiting": len(eligible) - n_checked}      # what the Gemini panel shows
    for it in items:
        scoring.analyse(it, cfg)
        it["first_seen"] = state["seen"].get(it["id"], today)
        # "added" = best known date the ad went online: the site's creation date, else its last update, else the day we first saw it
        # (only if that was after our very first run: on that day everything looked new)
        added, how = it.get("created") or None, "created"
        if not added and it.get("modified"):
            added, how = it["modified"], "updated"
        if not added and it["first_seen"] > first_run:
            added, how = it["first_seen"], "seen"
        it["added"], it["added_how"] = added, (how if added else "")
        it["new"] = bool(added) and (date.fromisoformat(today) - date.fromisoformat(added)).days <= cfg.get("new_days", 3)
        if not a.offline:
            state["seen"].setdefault(it["id"], today)
    items.sort(key=lambda it: -it["score"])

    sources.REQUEST_HOOK = None
    PROGRESS.stage("build", total=1)
    msgs = {}
    for it in items:
        m = messages.build(it, cfg)
        m["_lang"] = messages.language(it, cfg)
        msgs[it["id"]] = m
    report.write_csv(items, os.path.join(HERE, "listings.csv"))
    report.write_html(items, msgs, os.path.join(HERE, "listings.html"), cfg)
    state.pop("last", None)
    fd, tmp = tempfile.mkstemp(dir=HERE)             # atomic write: the control page reads this file while a run is going
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE)

    PROGRESS.finish()
    live = [it for it in items if not it["gone"]]
    good = [it for it in live if it["good"]]
    S.update(requests=dict(REQ), blocked=sorted(blocked), live=len(live), good=len(good), listings_total=len(items), possibly_taken=len(items) - len(live),
             new_recent=sum(1 for it in live if it["new"]), followups_due=followups_due())
    checked = sum(1 for it in candidates if it["id"] in state["details"])
    print(f"\n{len(live)} live listings ({len(items) - len(live)} possibly taken), {len(good)} within €{cfg['budget']} without red flags, "
          f"{sum(it['new'] for it in live)} new. Text read for {checked} of {len(candidates)} candidates; "
          f"AI summary for {sum(1 for it in live if it['ai'])}.\n")
    for it in good[:15]:
        print(f"{it['score']:6} €{it['total']:<5} ~{it['minutes']}min {it['locality'][:16]:16} {'ok' if it['verified'] else 'unread':6} {','.join(it['flags'])[:30]:30} {it['url']}")
    if a.notify and not a.offline:
        hot = [it for it in good if it["new"] and it["score"] >= cfg["notify_min_score"] and it["verified"]]
        if hot:
            best = hot[0]
            notify(f"{len(hot)} new flat(s) in budget", f"Best: €{best['total']} {best['locality']} ~{best['minutes']} min, score {best['score']}")
    if a.notify and not a.offline and followups_due():
        notify(f"{followups_due()} follow-up(s) due", "Contacted flats with no reply. Open the Listings page to send a reminder.")
    if not a.no_cloud:                                     # the shared copy for your friend: publish the new page, reconcile marks and notes
        try:
            import cloud_sync
            S["cloud"] = cloud_sync.publish()
            if S["cloud"].get("configured"):
                print("shared copy:", S["cloud"])
        except Exception as e:
            S["cloud"] = {"ok": False, "error": f"{type(e).__name__}: {str(e)[:120]}"}
    if blocked:
        print(f"\nBlocked sources this run: {', '.join(sorted(blocked))}. Wait a day before running again.", file=sys.stderr)
    print(f"\nOpen the page:  python3 {os.path.join(HERE, 'serve.py')}   then http://127.0.0.1:8765/")


class Tee:
    """Copies everything printed to a log file as well, so each run keeps its own log however it was started."""
    def __init__(self, stream, f):
        self.stream, self.f = stream, f

    def write(self, s):
        self.stream.write(s)
        self.f.write(s)
        return len(s)

    def flush(self):
        self.stream.flush()
        self.f.flush()

    def isatty(self):
        return False


def record_history(S):
    hist = load_json(HISTORY, [])
    hist.append(S)
    fd, tmp = tempfile.mkstemp(dir=HERE)
    with os.fdopen(fd, "w") as f:
        json.dump(hist[-300:], f)
    os.replace(tmp, HISTORY)


def prune_logs(keep=40):
    for name in sorted(os.listdir(LOGDIR))[:-keep]:
        try:
            os.remove(os.path.join(LOGDIR, name))
        except OSError:
            pass


def main():
    os.makedirs(LOGDIR, exist_ok=True)
    started = datetime.now()
    name = f"run-{started:%Y%m%d-%H%M%S}.log"
    logf = open(os.path.join(LOGDIR, name), "w")
    sys.stdout, sys.stderr = Tee(sys.__stdout__, logf), Tee(sys.__stderr__, logf)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))                 # the Stop button: still record the run
    S = {"started": started.isoformat(timespec="seconds"), "source": os.environ.get("FF_SOURCE", "cli"), "log": name}
    try:
        _main(S)
    except BaseException as e:
        S["error"] = "stopped" if isinstance(e, (SystemExit, KeyboardInterrupt)) else f"{type(e).__name__}: {e}"[:200]
        raise
    finally:
        S["duration_s"] = round((datetime.now() - started).total_seconds())
        S.setdefault("ai", {"analyses": 0, "failed": 0, "tokens_in": 0, "tokens_out": 0, "cost_est": 0})
        try:
            record_history(S)
        finally:
            sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
            logf.close()
            prune_logs()


if __name__ == "__main__":
    main()
