"""Flags, commute estimate and score for each listing."""
import json, math, os, re, unicodedata
from datetime import date, datetime

import describe

HERE = os.path.dirname(os.path.abspath(__file__))
EUROCONTROL = (50.88347, 4.43077)  # Rue de la Fusée 96, 1130 Haren
TRAM62_EUROCONTROL_STOP = (50.8795, 4.43393)
SHUTTLE_STOPS = {"Gare Centrale": (50.8455, 4.3570), "Square Ambiorix": (50.8466, 4.3830)}
with open(os.path.join(HERE, "data", "tram62.json")) as f:
    TRAM62 = {k: tuple(v) for k, v in json.load(f)["stops"].items()}

# keyword flags found in descriptions (FR / NL / EN)
RED = {"no_domicile", "students_only", "long_only", "no_couple", "shared", "wrong_location", "far", "check_scam", "not_flat", "too_late"}


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def walk_min(dist_km):
    return dist_km * 1.3 * 12          # streets are ~30% longer than a straight line, 5 km/h


def commute(pos, shuttle=False):
    """Rough door-to-desk minutes by the best of: walking, tram 62, generic STIB/train, Eurocontrol shuttle.
    An estimate to rank listings, not a timetable; check the real route in the STIB app before visiting."""
    direct = km(pos, EUROCONTROL)
    options = {"walk": walk_min(direct)}
    stop, d_stop = min(((n, km(pos, p)) for n, p in TRAM62.items()), key=lambda t: t[1])
    if d_stop < 1.5:
        ride = km(TRAM62[stop], TRAM62_EUROCONTROL_STOP) * 1.35 / 18 * 60  # tram ~18 km/h along the route
        options["tram 62 from " + stop] = walk_min(d_stop) + 5 + ride + walk_min(0.45)
    options["bus/train"] = 12 + direct * 4.0                            # ~15 km/h door to door incl. waits
    if shuttle:
        name, d_sh = min(((n, km(pos, p)) for n, p in SHUTTLE_STOPS.items()), key=lambda t: t[1])
        if d_sh < 2:
            options["shuttle from " + name] = walk_min(d_sh) + 8 + 25
    how = min(options, key=options.get)
    return round(options[how]), how, round(direct, 1)


def analyse(item, cfg):
    flags, evidence = describe.facts(item.get("description") or "", item.get("title") or "")     # keyword rules with negation; evidence = the phrase found
    item["evidence"] = evidence
    # structured fields of the listing page beat free text
    if item.get("has_washer"):
        flags["laundry_machine"], flags["shared_laundry"], flags["laundry_hookup"] = True, False, False
        evidence.setdefault("laundry_machine", "listing data: washing machine in the kitchen")
    if item.get("has_fridge"):
        flags["fridge"] = True
        evidence.setdefault("fridge", "listing data: fridge in the kitchen")
    if item.get("struct_shared"):                                    # HousingAnywhere's own data: a room that is not private
        flags["shared"] = True
        evidence.setdefault("shared", "listing data: " + ", ".join(item["struct_shared"]) + " not private")
    if item.get("couples_ok") is False:
        flags["no_couple"] = True
        evidence.setdefault("no_couple", "listing data: couples not allowed")
    # ---- money and size facts from the text (listing data, when the site has it, always wins)
    text = item.get("description") or ""
    cst, nums = describe.costs(text), describe.numbers(text, item.get("title") or "")
    item.setdefault("beds_src", "")                                  # kept across the repeated scoring passes of one run
    item.setdefault("m2_src", "")
    if item.get("bedrooms") is None:
        if nums["bedrooms"] is not None:
            item["bedrooms"], item["beds_src"] = nums["bedrooms"], "text"
        elif item.get("rooms") == 1:
            item["bedrooms"], item["beds_src"] = 0, "rooms"           # the listing data says one room: a studio
    if not item.get("m2") and nums["m2"]:
        item["m2"], item["m2_src"] = nums["m2"], "text"
    dep, dep_src = item.get("deposit"), "listing" if item.get("deposit") else ""
    if not dep and cst.get("deposit"):
        dep, dep_src = cst["deposit"], "text"
    elif not dep and cst.get("deposit_months") and item.get("rent"):
        dep, dep_src = round(cst["deposit_months"] * item["rent"]), "text"
    item["deposit_eur"], item["deposit_src"] = dep, dep_src
    if dep:
        evidence.setdefault("deposit", cst.get("deposit_ev") or f"listing data: deposit {dep} EUR")
        if item.get("rent") and dep / item["rent"] > 2.05:
            flags["deposit_high"] = True                                 # Brussels caps the deposit at 2 months of rent
            evidence["deposit_high"] = f"deposit {dep} EUR = {dep / item['rent']:.1f} months of rent"
    item["couple_extra"] = cst.get("couple_extra")
    if item["couple_extra"]:
        flags["couple_extra"] = True
        evidence["couple_extra"] = cst.get("couple_ev", "")
    item["one_off_text"] = cst.get("one_off") or 0
    item["utilities_excluded"] = bool(cst.get("utilities_excluded"))
    if item["utilities_excluded"]:
        flags["utilities_excluded"] = True
        evidence["utilities_excluded"] = cst.get("util_ev", "")
    unk = re.search(r"other\s+monthly\s+costs|additional\s+monthly\s+(?:costs|charges)|extra\s+monthly\s+costs|autres\s+frais\s+mensuels|frais\s+mensuels\s+(?:suppl[ée]mentaires|additionnels)", text, re.I)
    item["extra_unknown"] = bool(unk) and item.get("monthly_extra") is None and not cst.get("couple_extra")
    if item["extra_unknown"]:
        flags["extra_costs_unknown"] = True
        evidence["extra_costs_unknown"] = text[max(0, unk.start() - 40):unk.end() + 70]
    tr = cst.get("text_rent")
    if tr and item.get("rent") and abs(tr - item["rent"]) > max(20, 0.03 * item["rent"]):
        flags["price_mismatch"] = True                                   # the description quotes another rent than the listing data
        evidence["price_mismatch"] = f"the text says {tr} EUR, the listing data says {item['rent']} EUR"
    if item.get("furnished") is not None:   # explicit field beats the text, but Immoweb text can still say "meublé"
        flags["furnished"] = bool(item["furnished"]) or (item["source"] != "immovlan" and flags["furnished"])
    if "equipped" in (item.get("kitchen") or ""):
        flags["fridge"] = True
    if re.search(r"KOT|ROOM|STUDENT|SHARED", item.get("type") or "", re.I):
        flags["shared"] = True
    stay_months = max(1, round((date.fromisoformat(cfg["profile"]["move_out"]) - date.fromisoformat(cfg["profile"]["move_in"])).days / 30.4))
    ai = item.get("ai") or {}                     # facts read by Gemini from the listing text (see gemini.py)
    months = ai.get("min_lease_months") or item.get("min_stay_months")   # Gemini, or the exact minimum stay a platform publishes
    if months and months >= 9:
        flags["long_only"] = True
    elif months and stay_months < months < 9:
        flags["lease_6m"] = True                  # minimum lease is longer than your stay: possible, but must be negotiated
    if ai.get("allows_registration") is False:
        flags["no_domicile"] = True
    elif ai.get("allows_registration"):
        flags["domicile_ok"] = True
    if ai.get("two_people_ok") is False:
        flags["no_couple"] = True
    if ai.get("shared_accommodation"):
        flags["shared"] = True
        if ai.get("sharing_evidence"):
            evidence.setdefault("shared", ai["sharing_evidence"])
    if ai.get("washing_machine") is True and not flags.get("shared"):
        flags["laundry_machine"], flags["shared_laundry"], flags["laundry_hookup"] = True, False, False
    elif ai.get("shared_laundry") and not flags.get("laundry_machine"):
        flags["shared_laundry"] = True
    for k_ai, k_flag in (("short_stay_ok", "short_term"), ("furnished", "furnished"), ("has_fridge", "fridge")):
        if ai.get(k_ai):
            flags[k_flag] = True
    # "short stay OK": the listing text says short/mid-term stays are accepted, or the minimum lease is 6 months or less
    flags["stay_ok"] = bool(flags.get("short_term") or item.get("midterm") or (months and months <= stay_months))
    if item.get("midterm"):
        flags["midterm"] = True                   # platform built for stays of a few months (HousingAnywhere, Spotahome)
        flags["check_registration"] = not ai.get("allows_registration")   # platforms rarely say if you can register the address
    item["verified"] = bool(item.get("description")) or bool(item.get("no_text"))
    if item.get("no_text"):
        flags["no_text"] = True                                          # read, but the seller wrote nothing: only the structured data can be trusted
        evidence["no_text"] = "the listing has no description"
    # text read, but it says nothing about lease length: worth asking (many landlords accept a few months, especially furnished)
    flags["ask_lease"] = bool(item["verified"] and not months and not flags.get("stay_ok") and not flags.get("long_only") and not item.get("midterm"))
    if not item["verified"] and item["source"] not in ("2ememain", "housinganywhere"):
        flags["unread"] = True                    # full text not read yet: red flags may be hiding in it
    total = item["rent"] + (item.get("charges") or 0)
    if item["source"] == "2ememain" and re.search(r"garde[\s-]?meuble|self[\s-]?storage|opslag|\bbox\b|garage|parking|emplacement|\bcave\b|kantoor|bureau", item.get("title") or "", re.I):
        flags["not_flat"] = True                  # private ads are messy: storage units, parking spaces, offices
    if total < 550:
        flags["check_scam"] = True          # suspiciously cheap for a whole flat
    if item.get("m2") and item["m2"] < cfg["min_m2"]:
        flags["tiny"] = True
    item["flags"] = [k for k, v in flags.items() if v]
    item["total"] = total

    centre = (cfg["areas"].get(item["postal"]) or {}).get("centre")
    pos = (item["lat"], item["lon"]) if item.get("lat") else tuple(centre) if centre else None
    item["minutes"], item["how"], item["km"] = commute(pos, cfg["eurocontrol_shuttle"]) if pos else (None, "", None)

    # sanity checks on what the listing page itself says (a label can be wrong; map coordinates and dates are harder to fake)
    extra = []
    if item.get("lat") and not item.get("approx_pos") and centre and km((item["lat"], item["lon"]), tuple(centre)) > 8:
        extra.append("wrong_location")            # e.g. labelled Sint-Joost-ten-Node but the map pin is in Antwerp
    if item["km"] and item["km"] > 25:
        extra.append("far")
    try:
        if item.get("modified") and (date.today() - date.fromisoformat(item["modified"])).days > 45:
            extra.append("stale")                 # not updated for weeks: probably already rented
    except ValueError:
        pass
    if item.get("agency_foreign"):
        extra.append("agency_abroad")
    item["flags"] += extra
    flags.update({k: True for k in extra})
    value_points(item, flags, stay_months, cfg)

    score = 100.0
    score -= max(0, total - 900) / 10                    # €10 above €900 = -1
    score -= max(0, (item["minutes"] or 45) - 15) * 0.9  # each minute beyond 15 = -0.9
    score += 18 if flags.get("furnished") else 0         # furnished landlords accept a stay of a few months far more often
    score += 15 if flags.get("stay_ok") else 0
    score += 10 if flags.get("domicile_ok") else 0
    score += 4 if flags.get("fridge") else 0
    score += 4 if flags.get("laundry_machine") else 0                        # a washing machine of your own inside the flat
    score -= 60 if flags.get("no_domicile") else 0
    score -= 30 if flags.get("long_only") else 0
    score -= 40 if flags.get("students_only") or flags.get("no_couple") else 0
    score -= 80 if flags.get("shared") else 0
    score -= 10 if flags.get("maybe_shared") and not flags.get("shared") else 0
    score -= 12 if flags.get("lease_6m") else 0
    score += 3 if item["verified"] else 0
    score -= 15 if flags.get("tiny") else 0
    fresh = (item.get("created") or item.get("modified") or "")[:10]       # fresh ads get answered faster; old ones are often already gone
    if fresh:
        try:
            d = (date.today() - date.fromisoformat(fresh)).days
            score += 6 if d <= 3 else 3 if d <= 7 else -4 if d > 21 else 0
        except ValueError:
            pass
    score -= 40 if flags.get("check_scam") else 0
    score -= 80 if flags.get("not_flat") else 0
    score -= 80 if flags.get("wrong_location") else 0
    score -= 60 if flags.get("far") else 0
    score -= 25 if flags.get("stale") else 0
    score -= 15 if flags.get("agency_abroad") else 0
    av = item.get("available") or ""
    try:
        avd = datetime.strptime(av[:10], "%Y-%m-%d").date() if "-" in av else datetime.strptime(av[:10].replace(".", "/"), "%d/%m/%Y").date()
        item["available"] = avd.isoformat()
        start = date.fromisoformat(cfg["profile"]["move_in"])
        late = (avd - start).days
        item["late_days"] = late
        score -= 30 if late > 31 else 10 if late > 14 else 0
        if late > cfg.get("max_late_days", 45):
            item["flags"].append("too_late")                             # free long after you need it
            flags["too_late"] = True
            score -= 40
        elif late > 14:
            item["flags"].append("late")
    except ValueError:
        pass
    if total > cfg["budget"]:
        score -= 50
    item["score"] = round(score, 1)
    item["good"] = total <= cfg["budget"] and not RED & set(item["flags"])


def value_points(item, flags, stay_months, cfg):
    """Price-performance points (0-100), separate from the match score. It prices the whole stay, not just the rent shown:
    the monthly extras (utilities and other costs), a surcharge for two people, a furniture allowance for unfurnished flats and the
    one-off fees spread over your stay. Exact numbers from the listing (HousingAnywhere) win over assumptions."""
    fee_cfg = (cfg.get("fees") or {}).get(item["source"])
    item["fee_exact"] = item.get("platform_fee") is not None
    if item["fee_exact"]:
        fees_once = (item.get("platform_fee") or 0) + (item.get("admin_fee") or 0)        # the platform's real fee and admin fee
    elif fee_cfg:
        lo, hi = (max(fee_cfg.get("min", 0), item["rent"] * fee_cfg[k]) for k in ("pct_low", "pct_high"))
        item["fee_range"], item["fee_note"] = [round(lo), round(hi)], fee_cfg.get("note", "")
        fees_once = (lo + hi) / 2                                                         # an assumption: the listing has not been read yet
    else:
        fees_once = 0
    fees_once += item.get("one_off_text") or 0
    util = unknown = 0
    if item.get("monthly_extra") is not None:
        util = item["monthly_extra"]                                                      # exact: electricity + gas + water + internet + other costs
    elif not flags.get("bills_incl") and not item.get("bills_included"):
        if item["source"] in ("housinganywhere", "spotahome") or (item.get("utilities_excluded") and not item.get("charges")):
            util = cfg.get("utilities_estimate", 120)                                     # utilities excluded and no figure given: an assumption
    if item.get("extra_unknown"):
        unknown = cfg.get("unknown_extra_estimate", 60)                                   # "other monthly costs" with no amount: an assumption
    couple = item.get("couple_extra") or 0                                                # you are two people
    furn = 0 if flags.get("furnished") else cfg.get("unfurnished_extra", 100) * (1 if item.get("verified") else 0.5)
    effective = item["total"] + util + unknown + couple + furn + fees_once / stay_months
    item["effective"] = round(effective)
    item["extras"] = {"utilities": round(util), "unknown_extra": round(unknown), "couple": round(couple), "furniture": round(furn),
                      "fee_once": round(fees_once), "fee_per_month": round(fees_once / stay_months)}
    item["upfront"] = round((item.get("deposit_eur") or 0) + item["total"] + util + unknown + couple + fees_once)   # deposit + first month + one-off fees
    item["ppm2"] = round(effective / item["m2"], 1) if item.get("m2") else None

    # ---- points (max 100): cost 40 + size 15 + layout 10 + commute 15 + included 15 + energy 5
    floor, ceiling = 600, cfg["budget"]
    cost_pts = 40 * min(1, max(0, (ceiling - effective) / (ceiling - floor)))        # real monthly cost: 600 EUR = full points, your budget = 0
    m2, beds = item.get("m2"), item.get("bedrooms")
    size_pts = 6 if not m2 else 15 * min(1, max(0, (m2 - 20) / 30))                  # for two people: 20 m2 = 0 points, 50 m2 or more = full
    layout_pts = 5 if beds is None else 4 if beds == 0 else 8 if beds == 1 else 10   # studio 4, 1 bedroom 8, 2+ bedrooms 10 (a room each)
    mins = item.get("minutes")
    commute_pts = 5 if mins is None else 15 * min(1, max(0, 1 - (mins - 10) / 50))   # 10 min = full, 60 min = 0
    included_pts = (5 if flags.get("furnished") else 0) + (3 if (flags.get("bills_incl") or item.get("bills_included")) else 0) \
        + (2 if flags.get("fridge") else 0) + (3 if flags.get("laundry_machine") else 0) + (2 if flags.get("stay_ok") else 0)
    energy_pts = {"A++": 5, "A+": 5, "A": 5, "B": 5, "C": 4, "D": 3, "E": 1, "F": 0, "G": 0}.get((item.get("epc") or "").upper().replace(" ", ""), 2)
    value = cost_pts + size_pts + layout_pts + commute_pts + included_pts + energy_pts
    if RED & set(item["flags"]):
        value = min(value, 25)                                # a deal-breaker caps the value, however cheap
    item["value"] = round(value)
    item["value_parts"] = {"cost": round(cost_pts), "size": round(size_pts), "layout": layout_pts, "commute": round(commute_pts), "included": included_pts, "energy": energy_pts}
    item["m2_pp"] = round(m2 / 2, 1) if m2 else None


_MERGE_KEYS = ("deposit", "admin_fee", "platform_fee", "monthly_extra", "monthly_extra_parts", "min_stay_months", "max_stay_months", "couples_ok",
               "struct_shared", "available", "bedrooms", "m2", "rooms", "furnished", "description")


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode())


def dedupe(items):
    """Same flat on several sites (same postal code and rent, plus the same size or the same street): keep the copy with the most data
    (text read first, then Immoweb > Immovlan > others) and copy over whatever the other copy knows that this one does not."""
    order = {"immoweb": 0, "immovlan": 1, "housinganywhere": 2, "spotahome": 3, "2ememain": 4}
    seen, texts, out = {}, {}, []
    for it in items:
        it.pop("also", None)                                         # dedupe can run twice per run: start from a clean slate
        it.pop("similar", None)
    for it in sorted(items, key=lambda i: (0 if i.get("description") else 1, order.get(i["source"], 9))):
        keys = []
        if it.get("m2") and it["postal"]:
            keys.append(("m2", it["postal"], it["rent"], it["m2"]))
        if len(_norm(it.get("street"))) >= 6 and it["postal"]:
            keys.append(("st", it["postal"], it["rent"], _norm(it["street"])))
        twin = next((seen[k] for k in keys if k in seen), None)
        if twin is not None:
            twin.setdefault("also", []).append(it["url"])
            for k in _MERGE_KEYS:
                if twin.get(k) in (None, "", [], {}) and it.get(k) not in (None, "", [], {}):
                    twin[k] = it[k]
            continue
        # several units of one building with the same text and rent: show one card with a count
        tkey = (it["postal"], it["rent"], (it.get("description") or "")[:200]) if len(it.get("description") or "") > 120 else None
        if tkey and tkey in texts:
            texts[tkey]["similar"] = texts[tkey].get("similar", 0) + 1
            continue
        for k in keys:
            seen[k] = it
        if tkey:
            texts[tkey] = it
        out.append(it)
    return out
