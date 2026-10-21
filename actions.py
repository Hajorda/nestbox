"""What to do now: replies to answer, viewings today and tomorrow, follow-ups due and the best new flats. The listings page works this out in the browser
(the "Next" tab); this module does the same for the morning digest. Both use the same rules:

- reply waiting: a flat you wrote to, whose latest incoming mail is newer than your latest outgoing mail and newer than your last "I answered"
- viewing: a planned viewing today or tomorrow
- follow-up due: status "contacted" for N days with no reply (N and the maximum number of follow-ups are settings)
- new: the best flats you have not touched, from pool.json (written when the page is built)
"""
import json, os
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
OPEN = ("new", "contacted", "replied", "visit")


def _answered(entry):
    return max([x.get("t", "") for x in (entry.get("log") or []) if x.get("k") == "answered"] or [""])


def compute(cfg, statuses, mail, pool, now=None):
    now = now or datetime.now()
    today, tomorrow = now.date().isoformat(), (now.date() + timedelta(days=1)).isoformat()
    first, nxt, mx = cfg.get("followup_first_days", 2), cfg.get("followup_next_days", 3), cfg.get("followup_max", 2)
    out = {"replies": [], "viewings": [], "followups": [], "new": []}
    for lid, e in statuses.items():
        st = e.get("status", "new")
        m = mail.get(lid) or {}
        last = m.get("last")
        if st in OPEN and last and last["date"] > (m.get("last_out") or "") and last["date"] > _answered(e):
            out["replies"].append({"id": lid, "from": last["from"].split("<")[0].strip(), "snippet": last["snippet"], "date": last["date"]})
        v = e.get("visit_at") or ""
        if v[:10] in (today, tomorrow) and v >= (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M"):
            out["viewings"].append({"id": lid, "when": v, "note": e.get("visit_note", "")})
        if st == "contacted" and e.get("fu_n", 0) < mx:
            try:
                age = (now - datetime.fromisoformat(e.get("fu_at") or e.get("status_at") or e["at"])).total_seconds() / 86400
            except (KeyError, TypeError, ValueError):
                continue
            if age >= (nxt if e.get("fu_n") else first):
                out["followups"].append({"id": lid, "days": int(age)})
    out["viewings"].sort(key=lambda x: x["when"])
    out["new"] = [p for p in pool if (statuses.get(p["id"]) or {}).get("status", "new") == "new"][:5]
    if (cfg.get("found_mode") or {}).get("on"):                                   # you found a flat: only replies and viewings still matter
        out["followups"], out["new"] = [], []
    return out


def label(lid, catalog, pool=()):
    c = catalog.get(lid) or next((p for p in pool if p["id"] == lid), {})
    return " ".join(x for x in (c.get("street"), c.get("locality")) if x) or c.get("addr") or c.get("title") or lid


def digest_text(a, catalog, pool=()):
    """(title, body) for the morning notification, or None when there is nothing to do."""
    parts = []
    if a["replies"]:
        parts.append(f"{len(a['replies'])} repl{'y' if len(a['replies']) == 1 else 'ies'} to answer")
    if a["viewings"]:
        v = a["viewings"][0]
        parts.append(f"{len(a['viewings'])} viewing{'s' if len(a['viewings']) > 1 else ''} ({v['when'][11:]} {label(v['id'], catalog, pool)}{' …' if len(a['viewings']) > 1 else ''})")
    if a["followups"]:
        parts.append(f"{len(a['followups'])} follow-up{'s' if len(a['followups']) > 1 else ''} due")
    if a["new"]:
        parts.append(f"{len(a['new'])} new good flats")
    if not parts:
        return None
    return "☀ Your flat search today", " · ".join(parts)
