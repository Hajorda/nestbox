#!/usr/bin/env python3
"""Try Nestbox without searching anything: builds a copy in demo_site/ with made-up listings (fake streets, agencies and phone numbers, links that
go to example.com) and opens it on http://127.0.0.1:8766/. Your real data is never touched.

    python3 demo.py              build and start the demo (Ctrl-C stops it)
    python3 demo.py --build-only just build demo_site/ and exit
"""
import json, os, random, shutil, subprocess, sys
from datetime import date, datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DEST = os.path.join(HERE, "demo_site")
PORT = 8766
COPY = [f for f in os.listdir(HERE) if f.endswith((".py", ".html")) and f not in ("demo.py",)] + ["config.example.json", "icon.svg"]

STREETS = ["Rue de l'Exemple", "Avenue des Tilleuls", "Chaussée de Démo", "Rue du Test", "Boulevard Fictif", "Place du Marché Imaginaire", "Rue des Lilas", "Avenue Exemple", "Rue de la Maquette"]
AGENCIES = ["Demo Immo", "Maison Fictive", "Exemple Estates", "Test Property", "Immo Imaginaire", "Sample Homes", ""]
GOOD = ["Bright {t} of {m2} m² with an equipped kitchen (fridge, oven), furnished. Short stays from 3 months are possible and registration at the address is possible. Washing machine in the flat. Charges included.",
        "Quiet {t} close to public transport. Fully furnished, fridge and cooking plates. Flexible lease, mid-term rental welcome. Domiciliation possible. Available from {av}.",
        "Lovely {t}, {m2} m², fresh paint, equipped open kitchen with refrigerator. A 6 month lease is fine. We accept two people."]
BAD = ["Room for rent in a shared flat. Shared kitchen and shared bathroom with two other tenants.",
       "Minimum lease of 1 year. Bail 3-6-9. Registration is not possible. For one person only.",
       "Reserved for students only. Shared kitchen. Colocation with 3 flatmates.",
       "Spacious {t}, {m2} m². Minimum rental period: one year. Domiciliation possible. Unfurnished, no fridge."]


def build():
    if os.path.exists(DEST):
        shutil.rmtree(DEST)
    os.makedirs(os.path.join(DEST, "data"))
    for f in COPY:
        shutil.copy(os.path.join(HERE, f), DEST)
    shutil.copy(os.path.join(HERE, "data", "tram62.json"), os.path.join(DEST, "data"))
    cfg = json.load(open(os.path.join(HERE, "config.example.json")))
    cfg["profile"].update(signature="Alex Demo", names="Alex Demo", phone="+32 2 555 00 00", email="alex@example.com", second_name="")
    cfg["profile"].update(move_in=(date.today() + timedelta(days=21)).isoformat(), move_out=(date.today() + timedelta(days=200)).isoformat())
    cfg["setup_done"] = True
    cfg["enabled_areas"] = list(cfg["areas"])[:6]
    json.dump(cfg, open(os.path.join(DEST, "config.json"), "w"), indent=2)
    rnd = random.Random(7)
    today = date.today()
    cat, details, seen = {}, {}, {}
    srcs = [("immoweb", "iw", "https://www.immoweb.be/en/classified/"), ("immovlan", "iv", "https://immovlan.be/en/detail/apartment/for-rent/"), ("spotahome", "sh", "https://www.spotahome.com/brussels/for-rent:apartments/"),
            ("housinganywhere", "ha", "https://housinganywhere.com/room/"), ("2ememain", "2m", "https://www.2ememain.be/v/immo/")]
    postals = cfg["enabled_areas"]
    for i in range(48):
        source, pre, base = srcs[i % len(srcs)]
        postal = postals[i % len(postals)]
        a = cfg["areas"][postal]
        lat, lon = a["centre"][0] + rnd.uniform(-.008, .008), a["centre"][1] + rnd.uniform(-.012, .012)
        typ = rnd.choice(["studio", "1-bedroom apartment", "apartment", "2-bedroom apartment"])
        beds = 0 if typ == "studio" else 2 if typ.startswith("2") else 1
        m2 = rnd.randint(26, 82)
        rent = rnd.choice([560, 640, 720, 790, 850, 910, 960, 1040, 1100, 1180, 1250, 1380, 1520])
        charges = rnd.choice([0, 25, 50, 80, 120])
        bad = rnd.random() < .3
        text = rnd.choice(BAD if bad else GOOD).format(t=typ, m2=m2, av=(today + timedelta(days=rnd.randint(5, 30))).isoformat())
        lid = f"{pre}-demo{1000 + i}"
        street = f"{rnd.choice(STREETS)} {rnd.randint(1, 120)}"
        first = today - timedelta(days=rnd.randint(0, 20))
        cat[lid] = {"id": lid, "source": source, "url": f"https://example.com/demo/{lid}", "title": f"{typ.title()} in {a['immoweb'].replace('-', ' ').title()}", "type": "APARTMENT", "rent": rent, "charges": charges,
                    "bedrooms": beds, "m2": m2, "postal": postal, "locality": a["immoweb"].replace("-", " ").title(), "street": street, "lat": lat, "lon": lon, "agency": rnd.choice(AGENCIES),
                    "furnished": rnd.random() < .6, "last_seen": today.isoformat(), "missed": 0, "missed_at": 0, "area": postal, "modified": (today - timedelta(days=rnd.randint(0, 6))).isoformat(),
                    "epc": rnd.choice(["A", "B", "C", "D"]), "seen_at": datetime.now().isoformat(timespec="minutes"), "first_at": first.isoformat() + "T09:00"}
        if i in (5, 17):
            cat[lid]["missed"] = 3                                   # shows the "possibly taken" display
        details[lid] = {"description": text, "page_read": True, "read_at": datetime.now().isoformat(timespec="minutes"), "phone": f"+32 2 555 01 {i:02d}"}
        seen[lid] = first.isoformat()
    json.dump({"seen": seen, "details": details, "catalog": cat, "ai": {}, "first_run": min(seen.values())}, open(os.path.join(DEST, "state.json"), "w"))
    ids = list(cat)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M")
    ago = lambda days, h=9: (datetime.now() - timedelta(days=days)).replace(hour=h, minute=0).strftime("%Y-%m-%dT%H:%M")
    today_visit = datetime.now().replace(hour=17, minute=30).strftime("%Y-%m-%dT%H:%M")
    json.dump({ids[0]: {"status": "contacted", "note": "Called, nobody answered. Try again after 18:00.", "status_at": ago(3), "at": ago(3), "marked": True, "marked_at": ago(3),
                        "log": [{"t": ago(3), "k": "message", "d": "copied the message (FR)", "by": "demo"}, {"t": ago(3), "k": "call", "d": "tapped the call link", "by": "demo"}]},
               ids[1]: {"status": "replied", "note": "They offer a viewing on Friday.", "status_at": ago(1), "at": ago(1), "marked": True, "marked_at": ago(2)},
               ids[2]: {"status": "visit", "note": "", "status_at": ago(1), "at": ago(1), "visit_at": today_visit, "visit_note": "Ask for the caretaker"},
               ids[3]: {"status": "contacted", "note": "", "status_at": ago(4), "at": ago(4)},
               ids[4]: {"status": "contacted", "note": "", "status_at": ago(1), "at": ago(1)},
               ids[5]: {"status": "rejected", "note": "Shared kitchen.", "status_at": ago(2), "at": ago(2)}},
              open(os.path.join(DEST, "statuses.json"), "w"), indent=1)
    json.dump({"msgs": {"d1": {"t": "T1", "from": "Marie Dupont <marie@demo-immo.example>", "to": "alex@example.com", "subject": "Re: Viewing request", "date": ago(0, 8), "snippet": "Hello, yes the flat is still free. Would Friday at 18:00 work for a viewing?",
                               "mine": False, "strong": True, "lids": [ids[1]], "scam": False},
                        "d2": {"t": "T2", "from": "Jan Peeters <jan@demo-immo.example>", "to": "alex@example.com", "subject": "Re: Bezichtiging", "date": ago(0, 7), "snippet": "Goedemorgen, de woning is helaas al verhuurd.",
                               "mine": False, "strong": True, "lids": [ids[4]], "scam": False}}, "manual": {}, "me": "alex@example.com", "last_poll": 0, "error": ""}, open(os.path.join(DEST, "mail.json"), "w"))
    r = subprocess.run([sys.executable, "scraper.py", "--offline", "--no-cloud", "--no-ai"], cwd=DEST, capture_output=True, text=True)
    if not os.path.exists(os.path.join(DEST, "listings.html")):
        sys.exit("could not build the demo page:\n" + r.stderr[-800:])
    print(f"Demo built in {DEST}")


if __name__ == "__main__":
    build()
    if "--build-only" in sys.argv:
        sys.exit(0)
    env = dict(os.environ, FF_PORT=str(PORT))
    print(f"\nDemo page:  http://127.0.0.1:{PORT}/   (made-up listings; Ctrl-C to stop)\nControl panel: http://127.0.0.1:{PORT}/control")
    try:
        subprocess.run([sys.executable, "serve.py"], cwd=DEST, env=env)
    except KeyboardInterrupt:
        pass
