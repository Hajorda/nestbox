"""Tests for mail_link.py with a fake Gmail (no network). Run: python3 test_mail_link.py"""
import json, os, tempfile
import mail_link as ml

ml.DATA_FILE = os.path.join(tempfile.mkdtemp(), "mail.json")
ml.HERE = os.path.dirname(ml.DATA_FILE)

CAT = {"iw-21872526": {"street": "Avenue Henri Dunant 9", "agency": "Expertissimmo Woluwe", "postal": "1140"},
       "iv-vbe73026": {"street": "Rue Général Fivé", "agency": "Immo Etterbeek"},
       "sh-1": {"street": "", "agency": "private"}, "iw-99999999": {"street": "Rue Belliard 3", "agency": "Expertissimmo Woluwe"}}
ST = {"iw-21872526": {"status": "contacted"}, "iv-vbe73026": {"status": "contacted"}, "sh-1": {"status": "new"}, "iw-99999999": {"status": "contacted"}}


def raw(i, thread, frm, subj, snip, ts):
    return {"id": i, "threadId": thread, "snippet": snip, "internalDate": str(ts * 1000), "payload": {"headers": [
        {"name": "From", "value": frm}, {"name": "To", "value": "x"}, {"name": "Subject", "value": subj}]}}


MAILS = {"m1": raw("m1", "T1", "Anna <anna@expertissimmo.be>", "Re: Viewing request", "Thanks, the flat at Avenue Henri Dunant 9 is free on Friday", 1_800_000_000),
         "m2": raw("m2", "T1", "Ali <me@gmail.com>", "Viewing request", "Hello, we saw Avenue Henri Dunant 9", 1_799_990_000),
         "m3": raw("m3", "T2", "Bob <bob@expertissimmo.be>", "Other flat", "Rue Belliard 3 is also available", 1_800_000_100),
         "m4": raw("m4", "T1", "Anna <anna@expertissimmo.be>", "Re: Viewing request", "Does 15:00 work?", 1_800_000_200)}
QUERIES = []


def fake(path, params=None):
    if path == "/profile":
        return {"emailAddress": "me@gmail.com"}
    if path == "/messages":
        q = params["q"]
        QUERIES.append(q)
        hits = []
        if "Henri Dunant" in q or "21872526" in q:
            hits = ["m1", "m2"]
        elif "Expertissimmo" in q:
            hits = ["m1", "m3"]
        return {"messages": [{"id": h} for h in hits]}
    return MAILS[path.split("/")[-1]]


s, w = ml.terms("iw-21872526", CAT["iw-21872526"])
assert s == ['"Avenue Henri Dunant 9"', '"21872526"'] and w == ['"Expertissimmo Woluwe"'], (s, w)
assert ml.terms("iv-vbe73026", CAT["iv-vbe73026"])[0] == ['"vbe73026"']          # no house number in the street: only the listing number is strong
assert ml.terms("sh-1", CAT["sh-1"]) == ([], [])                                  # private ads give nothing to match on

new = ml.poll(CAT, ST, api_fn=fake, now=1_800_100_000)
assert [n[0] for n in new] == ["iw-21872526"] and new[0][1]["subject"] == "Re: Viewing request", new      # the landlord's reply is new; my own sent mail and the weak match are not
S = ml.summary()
o = S["iw-21872526"]
assert o["in"] == 1 and o["out"] == 1 and o["last"]["id"] == "m1", o
assert [m["id"] for m in o["maybe"]] == ["m3"], o["maybe"]                          # the agency's mail about another flat is only "maybe"
assert "iv-vbe73026" not in S or S["iv-vbe73026"]["in"] == 0

# a thread with a strong match carries its later messages even when they do not repeat the address
MAILS["m1"]["threadId"] = "T1"
def fake2(path, params=None):
    if path == "/messages" and "Henri Dunant" in params["q"]:
        return {"messages": [{"id": "m1"}, {"id": "m4"}]}
    return fake(path, params)
new2 = ml.poll(CAT, ST, api_fn=fake2, now=1_800_100_000)
assert ml.summary()["iw-21872526"]["in"] == 2, ml.summary()

ml.decide("m3", "iw-21872526", True)                                               # you confirm the weak match
assert ml.summary()["iw-21872526"]["in"] == 3
ml.decide("m3", "iw-21872526", False)                                              # or reject it
assert ml.summary()["iw-21872526"]["in"] == 2 and not ml.summary()["iw-21872526"]["maybe"]

# failures are recorded, not raised
def boom(path, params=None):
    raise RuntimeError("Gmail said 401")
assert ml.poll(CAT, ST, api_fn=boom) == [] and "401" in ml.info()["error"]
# the only flat contacted at an agency: the agency's mails are a strong match
CAT2 = {"iv-vbe73026": CAT["iv-vbe73026"]}
ml.DATA_FILE = os.path.join(tempfile.mkdtemp(), "mail.json")
def fake3(path, params=None):
    if path == "/messages" and "Immo Etterbeek" in params["q"]:
        return {"messages": [{"id": "m3"}]}
    if path == "/messages":
        return {"messages": []}
    return fake(path, params)
new3 = ml.poll(CAT2, {"iv-vbe73026": {"status": "contacted"}}, api_fn=fake3)
assert ml.summary()["iv-vbe73026"]["in"] == 1 and len(new3) == 1
# automated mail is ignored, platform mail never counts as a lone-agency match
assert ml.automated({"labelIds": ["CATEGORY_PROMOTIONS"], "payload": {"headers": []}})
assert ml.automated(raw("x", "T", "HousingAnywhere <hello@housinganywhere.com>", "Welcome to HousingAnywhere!", "", 1))
assert ml.automated(raw("x", "T", "News <newsletter@x.be>", "Hello", "", 1))
assert not ml.automated(raw("x", "T", "Anna <anna@expertissimmo.be>", "Re: Viewing request", "", 1))
HA = {"ha-1": {"street": "", "agency": "HousingAnywhere", "source": "housinganywhere"}}
def fake4(path, params=None):
    if path == "/messages" and "HousingAnywhere" in params["q"]:
        return {"messages": [{"id": "h1"}, {"id": "h2"}]}
    if path == "/messages":
        return {"messages": []}
    if path.endswith("h1"):
        return raw("h1", "TH", "HousingAnywhere <hello@housinganywhere.com>", "Welcome to HousingAnywhere!", "welcome", 1_800_000_000)
    return raw("h2", "TH2", "ANNIE via HousingAnywhere <relay@housinganywhere.com>", "New message", "Bonjour, je vous remercie", 1_800_000_050)
ml.DATA_FILE = os.path.join(tempfile.mkdtemp(), "mail.json")
assert ml.poll(HA, {"ha-1": {"status": "contacted"}}, api_fn=fake4) == []
S4 = ml.summary()["ha-1"]
assert S4["in"] == 0 and [x["id"] for x in S4["maybe"]] == ["h2"], S4                # the welcome mail is gone; the relayed message is only "possible"
assert ml.scam("Evan <mercurio@gmail.com>", "Re: Immoweb - Interest in a To rent ad", "Dear Customer, Welcome to HousingAnywhere!")
assert not ml.scam("HousingAnywhere <hello@housinganywhere.com>", "Welcome", "Welcome to HousingAnywhere")
assert not ml.scam("Anna <anna@gmail.com>", "Re: Viewing request", "Friday at 15:00 works")
print("mail_link tests passed")
