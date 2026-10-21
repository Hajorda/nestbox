"""Tests for the parts that are not keyword reading: message templates, first-run setup, source health, merging the notebooks and the demo build.
Run: python3 test_core.py"""
import json, os, shutil, subprocess, sys, tempfile
import cloud_sync, firstrun, messages

HERE = os.path.dirname(os.path.abspath(__file__))
cfg = json.load(open(os.path.join(HERE, "config.example.json")))
item = {"street": "Rue du Test 5", "postal": "1140", "locality": "Evere", "rent": 900, "url": "https://example.com/x", "title": "Nice flat", "agency": "Demo"}

# ---- templates: the defaults render, a custom text renders, a typo stays visible, odd braces never crash
out = messages.build(item, cfg)
assert set(out) == set(messages.DEFAULTS) and all("{" not in v and "}" not in v for v in out.values()), "a placeholder was left unfilled"
assert "Rue du Test 5 1140 Evere" in out["en"] and "€900/month" in out["en"]
v = messages.variables(item, cfg, "fr")
assert messages.render("Hi {signature}, {typo} {", v).startswith("Hi Your Name, {typo}")
assert messages.render("{{braces}} {where}", v) == "{braces} Rue du Test 5 1140 Evere"

# ---- first run: example config, wizard validation
assert firstrun.needs_setup(cfg)
tmp = tempfile.mkdtemp()
firstrun.CONFIG, firstrun.HERE = os.path.join(tmp, "config.json"), tmp
shutil.copy(os.path.join(HERE, "config.example.json"), os.path.join(tmp, "config.example.json"))
firstrun.EXAMPLE = os.path.join(tmp, "config.example.json")
assert os.path.exists(firstrun.ensure_config()) and firstrun.needs_setup(firstrun.load())
good = {"name": "Sam Tester", "email": "sam@example.com", "phone": "+32 400", "budget": 1000, "move_in": "2027-01-05", "move_out": "2027-06-30", "areas": ["1140"]}
for bad, why in (({**good, "name": ""}, "name"), ({**good, "budget": 50}, "budget"), ({**good, "move_out": "2027-01-01"}, "dates"), ({**good, "areas": ["9999"]}, "area"), ({"name": "x"}, "missing")):
    assert firstrun.apply_setup(bad)[0], f"the wizard accepted a bad {why}"
err, saved = firstrun.apply_setup({**good, "second_name": "Pat"})
assert err is None and saved["profile"]["signature"] == "Sam Tester" and saved["enabled_areas"] == ["1140"] and not firstrun.needs_setup(firstrun.load())
assert "Sam Tester et Pat" in messages.build(item, saved)["fr"] or "Sam Tester et Pat" in messages.variables(item, saved, "fr")["intro"]

# ---- source health: a site that suddenly returns nothing is flagged, a broken run does not change what is "typical"
import scraper
p = os.path.join(tmp, "sh.json")
st = {"source_hist": {"immoweb": [480, 490, 470], "immovlan": [300, 310, 305], "spotahome": [96, 96]}}
assert scraper.source_health(st, {("immoweb", "1"): 0, ("immovlan", "1"): 100, ("spotahome", ""): 96}, set(), path=p) == {"immoweb": "zero", "immovlan": "drop"}
assert st["source_hist"]["immoweb"] == [480, 490, 470] and st["source_hist"]["spotahome"][-1] == 96
assert scraper.source_health(st, {("immoweb", "1"): 480}, {"immovlan"}, path=p).get("immovlan") == "blocked"

# ---- two notebooks merge: the newer entry wins, both histories are kept
a = {"x": {"at": "2026-10-21T10:00", "status": "new", "log": [{"t": "1", "k": "k", "d": "a"}]}}
b = {"x": {"at": "2026-10-21T11:00", "status": "contacted", "log": [{"t": "2", "k": "k", "d": "b"}]}}
m = cloud_sync.merge(a, b)["x"]
assert m["status"] == "contacted" and [e["d"] for e in m["log"]] == ["a", "b"]

# ---- what to do now
import actions
from datetime import datetime
now = datetime(2026, 10, 21, 10, 0)
S = {"a": {"status": "contacted", "at": "2026-10-18T09:00", "status_at": "2026-10-18T09:00"},                       # contacted 3 days ago: follow-up due
     "b": {"status": "replied", "at": "2026-10-20T09:00", "status_at": "2026-10-20T09:00"},                       # unanswered reply
     "c": {"status": "replied", "at": "2026-10-20T09:00", "log": [{"t": "2026-10-20T12:00", "k": "answered"}]},       # answered after the reply
     "d": {"status": "visit", "visit_at": "2026-10-21T17:30", "visit_note": "caretaker"},
     "e": {"status": "visit", "visit_at": "2026-10-23T17:30"},                                                      # too far away
     "f": {"status": "rejected", "at": "2026-10-10T09:00"},
     "g": {"status": "contacted", "at": "2026-10-18T09:00", "fu_n": 2}}                                           # already followed up twice
M = {"b": {"last": {"date": "2026-10-20T08:00", "from": "Anna <a@x.be>", "snippet": "Friday?"}, "last_out": "2026-10-19T09:00"},
     "c": {"last": {"date": "2026-10-20T08:00", "from": "Bob <b@x.be>", "snippet": "ok"}, "last_out": ""},
     "f": {"last": {"date": "2026-10-20T08:00", "from": "Z", "snippet": "z"}, "last_out": ""}}
pool = [{"id": "n1", "title": "t1", "addr": "A", "total": 800, "score": 99, "new": True}, {"id": "a", "title": "t", "addr": "B", "total": 900, "score": 90, "new": False}, {"id": "n2", "title": "t2", "addr": "C", "total": 700, "score": 80, "new": False}]
r = actions.compute({}, S, M, pool, now=now)
assert [x["id"] for x in r["replies"]] == ["b"], r["replies"]
assert [x["id"] for x in r["viewings"]] == ["d"]
assert [x["id"] for x in r["followups"]] == ["a"], r["followups"]
assert [x["id"] for x in r["new"]] == ["n1", "n2"]              # "a" is already contacted
assert actions.compute({"followup_first_days": 5}, S, M, pool, now=now)["followups"] == []
title, body = actions.digest_text(r, {}, pool)
assert "1 reply to answer" in body and "1 viewing" in body and "1 follow-up due" in body and "2 new good flats" in body, body
f = actions.compute({"found_mode": {"on": True}}, S, M, pool, now=now)
assert f["followups"] == [] and f["new"] == [] and [x["id"] for x in f["replies"]] == ["b"] and len(f["viewings"]) == 1
assert actions.digest_text({"replies": [], "viewings": [], "followups": [], "new": []}, {}) is None

# ---- search: phone in any spelling, email, accents
import search
docs = {"a": [("phone", "+32 473 79 65 52"), ("description", "Contact Éric: Kemal@YesProperties.be, salle d'eau équipée, frigo")], "b": [("your note", "called 02 555 01 04, voicemail")]}
assert list(search.run("0473/79.65.52", docs)) == ["a"] and list(search.run("0032473796552", docs)) == ["a"] and list(search.run("473796552", docs)) == ["a"]
assert list(search.run("02 555 01 04", docs)) == ["b"] and search.run("kemal@yesproperties.be", docs)["a"][0][0] == "description"
assert "équipée" in search.run("equipee frigo", docs)["a"][0][1] and search.run("zzzz", docs) == {} and search.run("ab", docs) == {}

# ---- the demo builds a page that contains the demo listings and no personal data
r = subprocess.run([sys.executable, os.path.join(HERE, "demo.py"), "--build-only"], capture_output=True, text=True)
page = open(os.path.join(HERE, "demo_site", "listings.html"), encoding="utf-8").read()
assert r.returncode == 0 and "demo1000" in page and "example.com/demo" in page and "</html>" in page[-200:]
real = json.load(open(os.path.join(HERE, "config.json")))["profile"]
for secret in (real.get("phone"), real.get("email")):
    assert not secret or secret not in page, "personal data found in the demo page"
shutil.rmtree(os.path.join(HERE, "demo_site"), ignore_errors=True)
print("core tests passed")
