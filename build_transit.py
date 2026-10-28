#!/usr/bin/env python3
"""Builds data/transit.json: the tram and bus lines that stop at EUROCONTROL (route shapes and stops), from OpenStreetMap through the Overpass API.
Run it again only if the lines change:  python3 build_transit.py   The map tab draws this file; nothing else needs the internet."""
import json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "transit.json")
EURO = (50.88347, 4.43077)
MIRRORS = ["https://lz4.overpass-api.de/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter", "https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter", "https://overpass.private.coffee/api/interpreter"]
UA = "nestbox-hobby-project/1.0 (personal use)"
COLORS = ["#7b2cbf", "#111827", "#0aa5a5", "#c2185b", "#5d4037", "#455a64", "#00838f", "#6a1b9a", "#827717", "#37474f"]     # none of them is a pin colour (green, blue, orange, red)


def overpass(query):
    for attempt in range(6):
        for url in MIRRORS:
            try:
                req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": query}).encode(), headers={"User-Agent": UA, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=100) as r:
                    return json.load(r)
            except Exception as e:
                print(f"  ! {url}: {e}", file=sys.stderr)
        time.sleep(10 * (attempt + 1))
    raise SystemExit("Overpass is not answering right now; try again later")


def main():
    lat, lon = EURO
    found = overpass(f'[out:json][timeout:60];(node(around:600,{lat},{lon})[public_transport];node(around:600,{lat},{lon})[highway=bus_stop];node(around:600,{lat},{lon})[railway=tram_stop];);rel(bn)[type=route][route~"^(tram|bus)$"];out tags;')
    ids = [e["id"] for e in found["elements"] if (e.get("tags") or {}).get("ref")]
    if not ids:
        raise SystemExit("no lines found near EUROCONTROL")
    geo = overpass(f'[out:json][timeout:90];rel(id:{",".join(map(str, ids))});out geom;')
    lines = {}
    for rel in geo["elements"]:
        t = rel.get("tags") or {}
        key = (t.get("route"), t.get("ref"))
        ln = lines.setdefault(key, {"mode": t.get("route"), "ref": t.get("ref"), "name": t.get("name") or "", "operator": t.get("operator") or "", "shapes": [], "stops": {}})
        for m in rel.get("members", []):
            if m["type"] == "way" and m.get("geometry") and not m.get("role"):
                ln["shapes"].append([[round(p["lat"], 5), round(p["lon"], 5)] for p in m["geometry"]])
            elif m["type"] == "node" and m.get("role", "").startswith("stop") and "lat" in m:
                ln["stops"].setdefault(f'{m["lat"]:.4f},{m["lon"]:.4f}', [m.get("ref") or "", round(m["lat"], 5), round(m["lon"], 5)])
    out = []
    for i, (key, ln) in enumerate(sorted(lines.items(), key=lambda kv: (kv[0][0] != "tram", kv[0][1] or ""))):
        out.append({"mode": ln["mode"], "ref": ln["ref"], "name": ln["name"], "color": COLORS[i % len(COLORS)], "shapes": ln["shapes"], "stops": list(ln["stops"].values())})
    with open(OUT, "w") as f:
        json.dump({"source": "OpenStreetMap contributors (ODbL), via Overpass", "euro": list(EURO), "lines": out}, f, separators=(",", ":"))
    print("lines:", ", ".join(f'{l["mode"]} {l["ref"]}' for l in out), "->", OUT)


if __name__ == "__main__":
    main()
