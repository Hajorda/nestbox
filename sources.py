"""Listing sources. Each search function returns a list of listing dicts with a common shape.

Rules every source follows:
- only paths its robots.txt allows (price/sort filters are applied locally, never in the URL)
- one request at a time, 2-4 s random pause between requests
- a 403/429 raises Blocked and the caller stops that source for the rest of the run
"""
import html, json, random, re, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


class Blocked(Exception):
    pass


REQUEST_HOOK = None        # called after every finished request; the scraper uses it to drive the progress bar


def fetch(url, tries=2):
    for _ in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en,fr;q=0.8,nl;q=0.6"})
            with urllib.request.urlopen(req, timeout=25) as r:
                body = r.read().decode("utf-8", "replace")
            pause()
            if REQUEST_HOOK:
                REQUEST_HOOK()
            return body
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                raise Blocked(f"{e.code} on {url}")
            print(f"  ! HTTP {e.code} {url}", file=sys.stderr)
        except Exception as e:  # network hiccup (hostel wifi): wait and retry once
            print(f"  ! {e} {url}", file=sys.stderr)
        time.sleep(6)
    if REQUEST_HOOK:
        REQUEST_HOOK()
    return None


def pause():
    time.sleep(random.uniform(2.0, 4.0))


def _text(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def _attr_json(page, name):
    """Value of a Vue attribute like :results='[...]' (single- or double-quoted, HTML-escaped)."""
    m = re.search(r":%s=(['\"])(.*?)\1\s" % re.escape(name), page, re.S)
    return json.loads(html.unescape(m.group(2))) if m else None


# ---------------------------------------------------------------- Immoweb
def immoweb_search(postal, slug, pages, furnished=False, max_pages=None):
    """Reads `pages` result pages; if the area has more listings than that (the site's order is not newest-first), reads on up to `max_pages`."""
    out, page, limit = [], 0, pages
    while page < limit:
        page += 1
        q = [f"page={page}"] if page > 1 else []
        if furnished:
            q.append("isFurnished=true")
        url = f"https://www.immoweb.be/en/search/apartment/for-rent/{slug}/{postal}" + ("?" + "&".join(q) if q else "")
        s = fetch(url)
        results = _attr_json(s, "results") if s else None
        if not results:
            break
        t = re.search(r"<title>\s*(\d[\d.,]*)\s+APARTMENT", s)
        if page == 1 and max_pages and t:
            limit = min(max_pages, max(pages, -(-int(re.sub(r"\D", "", t.group(1))) // 30)))     # 30 listings per page
        for x in results:
            p = x.get("property") or {}
            loc, price, tr = p.get("location") or {}, x.get("price") or {}, x.get("transaction") or {}
            if not price.get("mainValue") or tr.get("type") != "FOR_RENT":
                continue
            out.append({
                "id": f"iw-{x['id']}", "source": "immoweb",
                "url": f"https://www.immoweb.be/en/classified/{x['id']}",
                "title": p.get("title") or p.get("subtype", "").replace("_", " ").title(),
                "type": p.get("subtype", ""),
                "rent": price["mainValue"], "charges": price.get("additionalValue") or 0,
                "bedrooms": p.get("bedroomCount"), "m2": p.get("netHabitableSurface"),
                "postal": loc.get("postalCode") or postal, "locality": loc.get("locality") or "",
                "street": " ".join(str(v) for v in (loc.get("street"), loc.get("number")) if v),
                "lat": loc.get("latitude"), "lon": loc.get("longitude"),
                "agency": x.get("customerName") or "private", "modified": ((x.get("publication") or {}).get("lastModificationDate") or "")[:10], "epc": tr.get("certificate") or "",
                "furnished": True if furnished else None,
            })
        if len(results) < 30:
            break
    return out


def immoweb_details(item, page=None):
    s = page or fetch(item["url"])
    i = s.find("window.classified =") if s else -1
    if i < 0:
        return
    try:
        c, _ = json.JSONDecoder().raw_decode(s[i + len("window.classified ="):].lstrip())
    except ValueError:
        return
    prop, tr = c.get("property") or {}, c.get("transaction") or {}
    rental = tr.get("rental") or {}
    item["furnished"] = rental.get("isFurnished") if rental.get("isFurnished") is not None else item.get("furnished")
    item["kitchen"] = ((prop.get("kitchen") or {}).get("type") or "").lower().replace("_", " ")
    item["available"] = tr.get("availabilityDate") or ""
    alts = prop.get("alternativeDescriptions") or {}                 # the ad may be written in another language only: the main field is then empty
    text = prop.get("description") or next((alts[k] for k in ("en", "fr", "nl", "de") if alts.get(k)), "") or next(iter(alts.values()), "")
    item["description"] = _text(text)[:8000]
    item["page_read"] = True
    kit = prop.get("kitchen") or {}
    item["has_washer"], item["has_fridge"] = kit.get("hasWashingMachine"), kit.get("hasFridge")      # True / False / None (not filled in)
    item["bathrooms"], item["toilets"] = prop.get("bathroomCount"), prop.get("toiletCount")
    item["rooms"], item["specs_v"] = prop.get("roomCount"), 2
    if rental.get("monthlyRentalCosts") and not item.get("charges"):
        item["charges"] = rental["monthlyRentalCosts"]
    pub, stats = c.get("publication") or {}, c.get("statistics") or {}
    item["created"] = (pub.get("creationDate") or "")[:10]            # the day the ad went online ("" if the site does not say)
    if isinstance(stats.get("viewCount"), int):
        item["views"], item["saves"] = stats["viewCount"], stats.get("bookmarkCount") or 0     # how many people are looking: competition
    # agency contact details are part of the page we already fetched (no extra request, nothing hidden is revealed)
    cust = next((x for x in (c.get("customers") or []) if x.get("phoneNumber") or x.get("mobileNumber")), None) or ((c.get("customers") or [None])[0] or {})
    phone = re.sub(r"[^0-9+]", "", cust.get("mobileNumber") or cust.get("phoneNumber") or "")
    if 8 <= len(phone) <= 15:
        item["phone"] = phone
    site = cust.get("website") or ""
    if site.startswith(("http://", "https://")):
        item["website"] = site[:200]
    hours = cust.get("contactHoursMobile") if cust.get("mobileNumber") else cust.get("contactHoursLandline")
    if isinstance(hours, str) and hours:
        item["contact_hours"] = hours[:40]


# ---------------------------------------------------------------- Immovlan
def immovlan_search(postal, town, pages, max_pages=None):
    out, page, limit = [], 0, pages
    while page < limit:
        page += 1
        url = f"https://immovlan.be/en/real-estate?transactiontypes=for-rent&propertytypes=apartment&towns={town}" + (f"&page={page}" if page > 1 else "")
        s = fetch(url)
        if not s:
            break
        t = re.search(r'"numberOfItems":(\d+)', s)
        if page == 1 and max_pages and t:
            limit = min(max_pages, max(pages, -(-int(t.group(1)) // 20)))                      # about 20 listings per page
        found = 0
        for blob in re.findall(r'<script type="application/ld(?:\+|&#x2B;)json">(.*?)</script>', s, re.S):
            try:
                data = json.loads(blob)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            for el in data.get("itemListElement") or (data.get("mainEntity") or {}).get("itemListElement") or []:
                it, u = el.get("item") or {}, el.get("url")
                offer = it.get("offers") or {}
                m = re.search(r"/detail/([^/]+)/for-rent/(\d{4})/([^/]+)/([^/?#]+)", u or "")
                if not m or not offer.get("price"):
                    continue
                found += 1
                out.append({
                    "id": f"iv-{m.group(4)}", "source": "immovlan", "url": u,
                    "title": it.get("name") or "Apartment", "type": m.group(1).upper(),
                    "rent": int(offer["price"]), "charges": 0, "bedrooms": None, "m2": None,
                    "postal": m.group(2), "locality": m.group(3).replace("-", " ").title(), "street": "",
                    "lat": None, "lon": None, "agency": "", "furnished": None,
                })
        if found < 20:
            break
    return out


def immovlan_desc(text):
    """Only the listing's own description: the page text also holds specs ("Furnished No"), ads and similar listings."""
    m = re.search(r"\bDescription\b(.*?)(?:\bGeneral info\b|\bState of the property\b|$)", text, re.S)
    return (m.group(1) if m else "")[:8000]


def immovlan_details(item, page=None):
    s = page or fetch(item["url"])
    if not s:
        return
    text = _text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S))
    item["description"] = immovlan_desc(text)
    for key, pat, conv in (
        ("bedrooms", r"(\d+)\s*Bedroom\(?s?\)?", int),
        ("m2", r"Livable surface\s*(\d+)\s*m", int),
        ("charges", r"(?:Maintenance cost|Monthly charges)\s*(\d[\d ]*)\s*€", lambda v: int(v.replace(" ", ""))),
    ):
        m = re.search(pat, text, re.I)
        if m:
            item[key] = conv(m.group(1))
    m = re.search(r"Furnished\s*(Yes|No)\b", text, re.I)
    if m:
        item["furnished"] = m.group(1).lower() == "yes"
    if re.search(r"Kitchen equipment\s*(Yes|Equipped|Hyper|Super)", text, re.I):
        item["kitchen"] = "equipped"
    m = re.search(r"Availability\s*(?:From\s*)?(Immediately|[0-9/.-]{8,10})", text, re.I)
    if m:
        item["available"] = date.today().isoformat() if m.group(1).lower() == "immediately" else m.group(1)
    m = re.search(r"Rental deposit\s*(\d[\d ]*)\s*€", text)                      # the seller's own deposit figure (the AI-written text can differ)
    if m:
        item["deposit"] = int(m.group(1).replace(" ", ""))
    r = re.search(r'"numberOfRooms":(\d+)', s)
    if r:
        item["rooms"] = int(r.group(1))
    st = re.search(r"\b[A-Z]{3}\d{4,6}\s+(.{3,60}?)\s*,\s*\d{4}\s", text)                # address line under the title: "VBE80792 Rue Saint-Michel , 1000 Brussels"
    if st and not st.group(1).startswith("-") and not item.get("street"):
        item["street"] = st.group(1).strip()
    item["specs_v"] = 2
    item["page_read"] = True
    # facts that don't depend on the label: map position, last update, seller country
    g = re.search(r'"latitude":(-?[\d.]+),"longitude":(-?[\d.]+)', s)
    if g:
        item["lat"], item["lon"], item["approx_pos"] = float(g.group(1)), float(g.group(2)), False
    m = re.search(r"Last modified:\s*(\d{2})/(\d{2})/(\d{4})", text)
    if m:
        item["modified"] = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    if any(len(p) == 5 and p.isdigit() for p in re.findall(r'"postalCode":"(\w+)"', s)):
        item["agency_foreign"] = True             # a five-digit (French) postcode in the seller's address
    d = re.search(r'"datePosted":"(\d{4}-\d{2}-\d{2})', s)
    item["created"] = d.group(1) if d else ""
    item["geo_checked"] = True


# ---------------------------------------------------------------- 2ememain (private ads, no location filter in URL)
def ememain_search(pages, near, max_km, km):
    out = []
    for cat in ("appartements-studios-a-louer", "expat-rentals"):
        for page in range(1, pages + 1):
            url = f"https://www.2ememain.be/l/immo/{cat}/" + (f"p/{page}/" if page > 1 else "")
            s = fetch(url)
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', s or "", re.S)
            if not m:
                break
            listings = json.loads(m.group(1))["props"]["pageProps"]["searchRequestAndResponse"]["listings"]
            for x in listings:
                loc, cents = x.get("location") or {}, (x.get("priceInfo") or {}).get("priceCents") or 0
                if not loc.get("latitude") or cents < 30000 or km((loc["latitude"], loc["longitude"]), near) > max_km:
                    continue
                attrs = {a["key"]: a.get("value") for a in x.get("extendedAttributes") or []}
                m2 = re.search(r"(\d+)", attrs.get("livingArea") or "")
                out.append({
                    "id": f"2m-{x['itemId']}", "source": "2ememain", "url": "https://www.2ememain.be" + x["vipUrl"],
                    "title": x.get("title") or "", "type": "PRIVATE AD",
                    "rent": cents // 100, "charges": 0, "bedrooms": None,
                    "m2": int(m2.group(1)) if m2 and "ou plus" not in (attrs.get("livingArea") or "") else None,
                    "postal": "", "locality": loc.get("cityName") or "", "street": "",
                    "lat": loc["latitude"], "lon": loc["longitude"],
                    "created": {"aujourd'hui": date.today().isoformat(), "vandaag": date.today().isoformat(), "hier": (date.today() - timedelta(days=1)).isoformat(),
                                "gisteren": (date.today() - timedelta(days=1)).isoformat()}.get((x.get("date") or "").strip().lower(), ""),
                    "agency": (x.get("sellerInformation") or {}).get("sellerName") or "private",
                    "furnished": None, "description": x.get("description") or "",
                })
            if len(listings) < 30:
                break
    return out


# ---------------------------------------------------------------- mid-term platforms (short stays are their normal case)
# Approximate centres of communes, used where a card only gives a commune name (commute is then a rough estimate).
COMMUNE_CENTRES = {
    "brussels": ((50.846, 4.352), "1000"), "ixelles": ((50.833, 4.372), "1050"), "elsene": ((50.833, 4.372), "1050"),
    "schaerbeek": ((50.867, 4.377), "1030"), "schaarbeek": ((50.867, 4.377), "1030"), "evere": ((50.870, 4.403), "1140"),
    "etterbeek": ((50.836, 4.389), "1040"), "woluwe-saint-lambert": ((50.846, 4.425), "1200"), "sint-lambrechts-woluwe": ((50.846, 4.425), "1200"),
    "woluwe-saint-pierre": ((50.838, 4.431), "1150"), "saint-josse-ten-noode": ((50.853, 4.373), "1210"), "sint-joost-ten-node": ((50.853, 4.373), "1210"),
    "laeken": ((50.880, 4.350), "1020"), "haren": ((50.889, 4.420), "1130"), "jette": ((50.876, 4.327), "1090"), "koekelberg": ((50.862, 4.327), "1081"),
    "saint-gilles": ((50.827, 4.345), "1060"), "forest": ((50.811, 4.314), "1190"), "anderlecht": ((50.836, 4.307), "1070"),
    "uccle": ((50.800, 4.337), "1180"), "auderghem": ((50.815, 4.426), "1160"), "zaventem": ((50.884, 4.473), "1930"),
    "machelen": ((50.910, 4.442), "1830"), "diegem": ((50.893, 4.433), "1831"), "vilvoorde": ((50.928, 4.425), "1800"),
    "neder-over-heembeek": ((50.900, 4.390), "1120"), "sint-stevens-woluwe": ((50.868, 4.445), "1932"),
}
MONTHS3 = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}


def _cardtext(chunk):
    chunk = re.sub(r"<(script|style|svg|picture).*?</\1>", "", chunk, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", chunk))
    return re.sub(r"(\s*\|\s*)+", " | ", t).strip(" |")


def _from_date(text):
    """'From 19 Oct' / 'From 03 Jan 27' -> ISO date (next occurrence if no year)."""
    m = re.search(r"From\s+(\d{1,2})\s+([A-Za-z]{3})[a-z]*(?:\s+(\d{2}))?", text or "")
    if not m or m.group(2).lower() not in MONTHS3:
        return ""
    today = date.today()
    month, day = MONTHS3[m.group(2).lower()], int(m.group(1))
    year = 2000 + int(m.group(3)) if m.group(3) else today.year + (1 if (month, day) < (today.month, today.day) else 0)
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def _near(commune, near, max_km, km):
    c = COMMUNE_CENTRES.get(re.sub(r"\s+", "-", (commune or "").strip().lower()))
    return c if c and km(c[0], near) <= max_km else None


def housinganywhere_search(place, near, max_km, km):
    """One results page per place (robots.txt disallows the ?page= query form, so only the plain URL is read)."""
    s = fetch(f"https://housinganywhere.com/s/{place}--Belgium/apartment-for-rent")
    out = []
    for chunk in re.split(r'(?=<a href="https://housinganywhere\.com/room/)', s or "")[1:]:
        m = re.match(r'<a href="(https://housinganywhere\.com/room/(\w+)/[^"]+)"', chunk)
        t = re.search(r'title="(\w+) for rent for €([\d,]+) per month in ([^,"]+), ([^"]+)"', chunk)
        if not m or not t:
            continue
        kind, rent, city, street = t.group(1), int(t.group(2).replace(",", "")), html.unescape(t.group(3)), html.unescape(t.group(4))
        c = _near(city, near, max_km, km)
        if not c:
            continue
        txt = _cardtext(chunk[:9000])
        beds = re.search(r"(\d+)\s+bedroom", txt)
        size = re.search(r"(\d+)\s*m²", txt)
        out.append({
            "id": f"ha-{m.group(2)}", "source": "housinganywhere", "url": m.group(1),
            "title": f"{kind} in {street}, {city}", "type": kind.upper(), "rent": rent, "charges": 0,
            "bedrooms": int(beds.group(1)) if beds else (0 if kind.lower() == "studio" else None),
            "m2": int(size.group(1)) if size else None, "postal": c[1], "locality": city, "street": street,
            "lat": c[0][0], "lon": c[0][1], "approx_pos": True, "agency": "HousingAnywhere", "midterm": True,
            "available": date.today().isoformat() if "Available now" in txt else "", "furnished": None,
        })
    return out


def spotahome_search(pages):
    out = []
    for page in range(1, pages + 1):
        s = fetch("https://www.spotahome.com/s/brussels/for-rent:apartments" + (f"?page={page}" if page > 1 else ""))
        if not s:
            break
        for chunk in re.split(r'<div class="l-list__item"', s)[1:]:
            idm = re.search(r'data-homecard-scroll="(\d+)"', chunk[:200])
            if not idm:
                continue
            txt = _cardtext(chunk)
            t = re.search(r"([\w-]+(?:\s[\w-]+)?)\s+for rent in ([^|]+?)(?:,\s*Brussels)?\s*\|", txt)
            price = re.search(r"\|\s*(\d{3,5})\s*€\s*\|\s*/\s*\|\s*month", txt)
            if not price:
                continue
            size, beds = re.search(r"Size\s*\|\s*:\s*\|\s*(\d+)\s*\|\s*m²", txt), re.search(r"(\d+)-bedroom", txt)
            kind = (t.group(1) if t else "apartment").split()[-1].upper()
            desc = txt[txt.find("Amenities"):] if "Amenities" in txt else ""
            desc = re.sub(r"^Amenities\s*\|\s*:\s*(\|\s*[a-z_]+\s*)*", "", desc).strip(" |")[:400]
            out.append({
                "id": f"sh-{idm.group(1)}", "source": "spotahome", "url": f"https://www.spotahome.com/brussels/for-rent:apartments/{idm.group(1)}",
                "title": (t.group(0).rsplit("|", 1)[0].strip() if t else "Apartment in Brussels"), "type": kind,
                "rent": int(price.group(1)), "charges": 0, "bedrooms": int(beds.group(1)) if beds else (0 if "studio" in (t.group(0).lower() if t else "") else None),
                "m2": int(size.group(1)) if size else None, "postal": "", "locality": (t.group(2).strip() if t else "Brussels"), "street": "",
                "lat": None, "lon": None, "agency": "Spotahome", "midterm": True, "furnished": True, "bills_included": "BILLS INCLUDED" in txt,
                "available": _from_date(txt), "description": desc,
            })
    return out


def spotahome_details(item, page=None):
    """The listing page has exact coordinates, address and the minimum stay in days."""
    s = page or fetch(item["url"])
    if not s:
        return
    g = re.search(r'"postalCode":"(\d{4})".{0,80}?"geo":\{"@type":"GeoCoordinates","latitude":(-?[\d.]+),"longitude":(-?[\d.]+)', s, re.S)
    if g:
        item["postal"], item["lat"], item["lon"] = g.group(1), float(g.group(2)), float(g.group(3))
        item["approx_pos"], item["geo_checked"], item["page_read"] = False, True, True
    st = re.search(r'"streetAddress":"([^"]{3,80})"', s)
    if st:
        item["street"] = html.unescape(st.group(1))
    ms = re.search(r'minStay\\*",(\d+)', s)
    if ms:
        item["min_stay_months"] = max(1, round(int(ms.group(1)) / 30))
    d = re.search(r'<meta (?:name|property)="description" content="([^"]{20,600})"', s)
    if d and not item.get("description"):
        item["description"] = html.unescape(d.group(1))
    item.setdefault("description", "Spotahome listing")


# ---------------------------------------------------------------- one listing from a link you paste (manual add)
SUPPORTED_HOSTS = {"immoweb.be": "immoweb", "immovlan.be": "immovlan", "spotahome.com": "spotahome", "housinganywhere.com": "housinganywhere", "2ememain.be": "2ememain"}


def parse_listing_url(url):
    """(source, id, clean url) for a listing link on a supported site, otherwise ValueError. Only these hosts are ever fetched."""
    u = urllib.parse.urlparse((url or "").strip())
    host = (u.hostname or "").lower()
    if u.scheme not in ("http", "https") or not host:
        raise ValueError("that does not look like a web link")
    source = next((v for k, v in SUPPORTED_HOSTS.items() if host == k or host.endswith("." + k)), None)
    if not source:
        raise ValueError("unsupported site. Supported: Immoweb, Immovlan, Spotahome, HousingAnywhere, 2ememain")
    path = u.path
    rules = {
        "immoweb": (r"/(?:classified|annonce|zoekertje)/(?:[^/]+/)*?(\d{6,10})/?$", "iw-{}", "https://www.immoweb.be/en/classified/{}"),
        "immovlan": (r"/detail/[^/]+/for-rent/\d{4}/[^/]+/([A-Za-z0-9]+)/?$", "iv-{}", None),
        "spotahome": (r"/for-rent:[^/]+/(\d+)", "sh-{}", None),
        "housinganywhere": (r"/room/(\w+)/", "ha-{}", None),
        "2ememain": (r"/(m\d+)-", "2m-{}", None),
    }
    rx, idfmt, cleanfmt = rules[source]
    m = re.search(rx, path)
    if not m:
        raise ValueError(f"that link is not a single {source} listing (open the listing itself and copy its address)")
    clean = cleanfmt.format(m.group(1)) if cleanfmt else f"https://{host}{path}"
    return source, idfmt.format(m.group(1)), clean


def _meta(page, prop):
    m = re.search(r'<meta[^>]+(?:property|name)="%s"[^>]+content="([^"]*)"' % re.escape(prop), page)
    return html.unescape(m.group(1)).strip() if m else ""


def fetch_listing(url, rent_hint=None):
    """Open one listing page and return an item shaped like the search results, with the details already filled in.
    Raises ValueError with a message for the user when the link or page cannot be used."""
    source, lid, clean = parse_listing_url(url)
    s = fetch(clean)
    if not s:
        raise ValueError("could not open that page (wrong link, or the site is blocking us right now)")
    item = {"id": lid, "source": source, "url": clean, "title": "", "type": "APARTMENT", "rent": None, "charges": 0, "bedrooms": None, "m2": None,
            "postal": "", "locality": "", "street": "", "lat": None, "lon": None, "agency": "", "furnished": None, "manual": True,
            "added_manually": date.today().isoformat()}
    if source == "immoweb":
        i = s.find("window.classified =")
        try:
            c, _ = json.JSONDecoder().raw_decode(s[i + len("window.classified ="):].lstrip())
        except ValueError:
            raise ValueError("could not read that Immoweb page")
        prop, tr = c.get("property") or {}, c.get("transaction") or {}
        if tr.get("type") != "FOR_RENT":
            raise ValueError("that listing is not for rent")
        loc, rental, cust = prop.get("location") or {}, tr.get("rental") or {}, ((c.get("customers") or [None])[0] or {})
        item.update(title=prop.get("title") or (prop.get("subtype") or "Apartment").replace("_", " ").title(), type=prop.get("subtype") or "APARTMENT",
                    rent=rental.get("monthlyRentalPrice"), charges=rental.get("monthlyRentalCosts") or 0, bedrooms=prop.get("bedroomCount"), m2=prop.get("netHabitableSurface"),
                    postal=str(loc.get("postalCode") or ""), locality=loc.get("locality") or "", lat=loc.get("latitude"), lon=loc.get("longitude"),
                    street=" ".join(str(v) for v in (loc.get("street"), loc.get("number")) if v), agency=cust.get("name") or "private",
                    modified=((c.get("publication") or {}).get("lastModificationDate") or "")[:10])
        immoweb_details(item, page=s)
    elif source == "immovlan":
        text = _text(re.sub(r"<script.*?</script>|<style.*?</style>", " ", s, flags=re.S))
        m = re.search(r"Rent\s*(\d[\d ]*)\s*€", text)
        u = re.search(r"/detail/([^/]+)/for-rent/(\d{4})/([^/]+)/", clean)
        item.update(title=_meta(s, "og:title") or "Apartment for rent", type=u.group(1).upper(), postal=u.group(2), locality=u.group(3).replace("-", " ").title(),
                    rent=int(m.group(1).replace(" ", "")) if m else None)
        immovlan_details(item, page=s)
    else:                                           # Spotahome, HousingAnywhere, 2ememain: titles and prices from the page's structured data
        price = None
        for blob in re.findall(r'<script[^>]*ld(?:\+|&#x2B;)json[^>]*>(.*?)</script>', s, re.S):
            p = re.search(r'"price"\s*:\s*"?(\d{3,5})', blob)
            if p:
                price = int(p.group(1))
                break
        g = re.search(r'"postalCode":"(\d{4})".{0,80}?"geo":\{"@type":"GeoCoordinates","latitude":(-?[\d.]+),"longitude":(-?[\d.]+)', s, re.S)
        item.update(title=_meta(s, "og:title") or "Listing", rent=price, agency={"spotahome": "Spotahome", "housinganywhere": "HousingAnywhere"}.get(source, ""),
                    midterm=source in ("spotahome", "housinganywhere"), description=_text(_meta(s, "og:description"))[:8000])
        if g:
            item["postal"], item["lat"], item["lon"] = g.group(1), float(g.group(2)), float(g.group(3))
        b = re.search(r"(\d+)-bedroom", item["title"])
        item["bedrooms"] = int(b.group(1)) if b else (0 if re.search(r"studio", item["title"], re.I) else None)
        if source == "spotahome":
            item["furnished"] = True
            spotahome_details(item, page=s)
    if not item["rent"]:
        if rent_hint and 100 <= int(rent_hint) <= 10000:
            item["rent"] = int(rent_hint)
        else:
            raise ValueError("RENT_NEEDED: I could not find the monthly rent on that page. Type it in the Rent box and add the link again.")
    item["rent"] = int(item["rent"])
    return item


# ---------------------------------------------------------------- HousingAnywhere listing page: exact costs, stay rules and facilities
def housinganywhere_details(item, page=None):
    """The page's data holds the real numbers (in cents): rent, monthly extras, deposit, admin fee, HousingAnywhere's own fee, stay limits, facilities."""
    s = page or fetch(item["url"])
    i = s.find("window.__PRELOADED_STATE__= (") if s else -1
    if i < 0:
        return
    try:
        d, _ = json.JSONDecoder().raw_decode(re.sub(r"\bundefined\b", "null", s[i + len("window.__PRELOADED_STATE__= ("):]))
        e = d["listing"]["entity"]
    except (ValueError, KeyError, TypeError):
        return
    eur = lambda v: round(v / 100) if isinstance(v, (int, float)) else None
    if eur(e.get("price")):
        item["rent"] = eur(e["price"])
    costs = (e.get("costs") or {}).get("costs") or {}
    val = lambda k: eur((costs.get(k) or {}).get("value"))
    item["deposit"], item["admin_fee"], item["platform_fee"] = val("security-deposit"), val("administration-fee"), eur(e.get("haFee"))
    parts = {k.replace("-bill", "").replace("other-additional-costs", "other"): eur(c.get("value")) for k, c in costs.items()
             if isinstance(c, dict) and c.get("payableAt") == "monthly" and c.get("required") and eur(c.get("value"))}
    item["monthly_extra"], item["monthly_extra_parts"] = sum(parts.values()), parts            # electricity, gas, water, internet and "other additional costs"
    item["min_stay_months"], item["max_stay_months"] = e.get("minimumStayMonths") or None, e.get("maximumStay") or None
    item["couples_ok"] = {"yes": True, "no": False}.get(str(e.get("couplesAllowed")).lower())
    f = e.get("facilities") or {}
    shared = [k for k in ("bathroom", "kitchen", "toilet", "living_room") if f.get(k) not in (None, "", "private")]
    item["struct_shared"] = shared                                                                  # the listing itself says this room is not private
    wm = str(f.get("washing_machine") or "").lower()
    item["has_washer"] = True if wm in ("yes", "private") else item.get("has_washer")
    item["bedrooms"] = int(f["bedroom_count"]) if str(f.get("bedroom_count") or "").isdigit() else item.get("bedrooms")
    item["m2"] = int(f["total_size"]) if str(f.get("total_size") or "").isdigit() else item.get("m2")
    if f.get("bedroom_furnished") == "yes" or f.get("lroom_furniture") == "yes":
        item["furnished"] = True
    if e.get("street"):
        item["street"] = (e["street"] + " " + str(e.get("housenumber") or "")).strip()
    if e.get("latitude") and e.get("longitude"):
        item["lat"], item["lon"], item["approx_pos"] = float(e["latitude"]), float(e["longitude"]), False
    bp = (e.get("bookablePeriods") or [{}])[0].get("from", "")[:10]
    if bp:
        item["available"] = max(bp, date.today().isoformat())                                       # bookable from this day (never earlier than today)
    item["description"] = _text(e.get("description") or "")[:8000] or item.get("description", "")
    item["geo_checked"], item["specs_v"], item["page_read"] = True, 2, True
