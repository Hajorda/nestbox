"""Reads a listing's title and description (French, Dutch, English) and returns facts, each with the phrase that proves it.

One place for every keyword rule. What makes it better than a plain keyword search:
- negation: "no shared kitchen", "pas de colocation", "non meublé", "geen gedeelde keuken", "not furnished" do not count as positives
- evidence: every flag keeps the phrase it came from, shown in the tag's tooltip on the page, so you can check it
- highlighting: the description can be shown with the important phrases marked (red = deal-breaker, orange = check, green = good, grey = info)

Your rules for sharing: a flat is either whole or shared. A shared kitchen, bathroom, shower or toilet means a shared flat. "Room for rent" and
"private room" are treated as shared. A shared laundry room is fine (grey tag only), a washing machine inside the flat is a plus, and a mere
washing-machine connection is not a machine.
"""
import html, re

# ---- rules: name -> (kind, negatable, pattern). kind: bad | warn | good | info (also the highlight colour)
SHARED = (
    r"colocation|\bcoloc\b|co-?living|cohousing|cohabitation|(?:flat|house)\s?-?share|\b(?:flat|house|room)\s?mates?\b|\bkot\b|studentenkamer|student\s+room|"
    r"shared\s+(?:flat|apartment|house|accommodation|kitchens?|bathrooms?|bath|toilets?|showers?(?:\s?rooms?)?|wc|living\s?room)|"
    r"(?:common|communal)\s+(?:kitchen|bathroom|toilets?|shower(?:\s?room)?|wc|living\s?room)|"
    r"(?:kitchen|bathroom|toilets?|shower(?:\s?room)?|wc)\s+(?:is\s+|are\s+)?(?:shared|communal)\b|"
    r"shar(?:e|es|ing)\s+(?:the\s+|a\s+|an\s+|your\s+)?(?:kitchen|bathroom|toilets?|shower|flat|apartment|house|living\s?room)|"
    r"(?:one|1|a|private|single)\s+(?:bed)?room\s+(?:in|within|of)\s+(?:a\s+|an\s+|the\s+)?(?:shared|\d[\s-]*bed|house|colocation)|"
    r"room\s+(?:in|within)\s+(?:a\s+)?(?:shared|house|flat\s?share)|\brooms?\s+(?:for\s+rent|to\s+let)\b|\b(?:à|a)\s+louer\s+(?:des\s+)?chambres?\b|\bchambres?\s+(?:pour|destin[ée]es?\s+(?:à|aux))\s+(?:des\s+)?(?:[ée]tudiants?|stagiaires?)|\brooms?\s+for\s+(?:students?|interns?)|(?<!\d )(?<!deux )(?<!trois )\bchambres\s+(?:à|a)\s+louer\b|\bprivate\s+room\b|"
    r"chambre\s+(?:dans|au\s+sein\s+d\S*)\s+(?:une?\s+|l'|la\s+)?(?:colocation|maison|appartement\s+partag\S+|logement\s+partag\S+|appartement\s+de\s+\d)|\bchambre\s+(?:à\s+louer|priv[ée]e)\b|"
    r"(?:cuisine|salle\s+de\s+bains?|salle\s+d'eau|douche|sanitaires?|salon|wc|toilettes?)\s+(?:commune?s?|partag[ée]e?s?)|"
    r"partag(?:er|e|ent)\s+(?:la\s+|le\s+|les\s+|l')?(?:cuisine|salle\s+de\s+bains?|douche|appartement|logement|maison|sanitaires?|toilettes?)|"
    r"gedeelde\s+(?:keuken|badkamer|woning|toilet|douche|living)|gemeenschappelijke\s+(?:keuken|badkamer|toilet|douche|woonkamer)|"
    r"deel(?:t|en)\s+(?:de\s+|een\s+)?(?:keuken|badkamer|woning|appartement|huis|toilet|douche)|kamer\s+in\s+(?:een\s+)?(?:gedeeld|huis|appartement|woning)|\bkamers?\s+(?:te\s+huur|voor\s+studenten)\b"
)
MAYBE_SHARED = (
    r"\b(?:single|spacious|furnished|bright)\s+room\b(?!\s+(?:of|with|for\s+storage))|room\s+available\b|bedroom\s+available|available\s+room|\bper\s+(?:room|person)\b|"
    r"chambre\s+disponible|prix\s+par\s+(?:chambre|personne)|kamer\s+beschikbaar|\bper\s+kamer\b"
)
_APPL = r"(?:washing\s+machines?|washer[-\s]dryers?|washer|tumble\s+dryers?|dryer|lave[-\s]linge|sèche[-\s]linge|machines?\s+à\s+laver|wasmachines?|wasdroger|droogkast|wasautomaat)"
_APPLS = _APPL + r"(?:\s*(?:,|/|&|and|et|en|ou|of)\s*(?:a\s+|an\s+|une?\s+|een\s+)?" + _APPL + r")*"      # "washing machine and dryer"
_LROOM = r"(?:laundry\s+(?:room|facilit\w+)|buanderie|laverie|wasruimte|wasplaats)"
_WITH = r"(?:\s+\S+){0,5}?\s+(?:with|avec|met|equipped\s+with|équipée?\s+de|équipée?\s+d')\s+(?:a\s+|an\s+|une?\s+|een\s+|de\s+|the\s+)?"
SHARED_LAUNDRY = (
    r"(?:shared|common|communal|commune?|partag[ée]e?|gedeelde|gemeenschappelijke|basement|sous-sol|kelder|cellar)\s+" + _LROOM + _WITH + _APPLS + r"|"        # "shared laundry room ... with washing machine and dryer"
    + _LROOM + r"\s+(?:commune?|partag[ée]e?|shared|gedeelde|common|communal)" + _WITH + _APPLS + r"|"
    + _LROOM + r"\s+(?:in|on|au|dans|op)\s+(?:the\s+|de\s+|le\s+|l')?(?:basement|cellar|sous-sol|cave|kelder|building|immeuble|gebouw|floor|résidence)" + _WITH + _APPLS + r"|"
    r"(?:shared|common|communal|collective|gedeelde|gemeenschappelijke)\s+" + _APPLS + r"|" + _APPLS + r"\s+(?:is\s+|are\s+)?(?:shared|common|communal|commune?s?|collectifs?|collective|partag[ée]e?s?|gedeeld\w*)\b|"
    r"shared\s+(?:laundry|washing|washer|dryer|washroom|laundromat)|(?:common|communal|collective)\s+(?:laundry|washing)|"
    r"laundry\s+(?:room|facilit\w+)\s+(?:is\s+)?shared|laundry\s+(?:room|facilit\w+)\s+(?:in|on)\s+the\s+(?:basement|building|cellar|floor)|"
    r"(?:shares?|sharing)\s+(?:a\s+|the\s+)?(?:laundry|washing)|"
    r"(?:access|accès|toegang)\s+(?:to|à|tot)\s+(?:a\s+|the\s+|une?\s+|een\s+|de\s+)?(?:laundry|buanderie|laverie|wasruimte|wasplaats)|"
    r"(?:buanderie|laverie|salle\s+de\s+lavage)\s+(?:commune|partag[ée]e|collective|au\s+sous-sol|dans\s+(?:l'immeuble|la\s+résidence|le\s+bâtiment))|machine\s+à\s+laver\s+(?:commune|partag[ée]e)|"
    r"gedeelde\s+(?:was(?:ruimte|plaats)?|wasmachine|droogkast)|(?:wasruimte|wasplaats|wasserette)\s+(?:in\s+(?:de\s+)?(?:kelder|gebouw)|gemeenschappelijk)|gemeenschappelijke\s+(?:was(?:ruimte|plaats)?|wasmachine)"
)
HOOKUP = (
    r"(?:(?:space|place|spot|room|plek|ruimte|plaats)\s+(?:for|pour|voor)|emplacement(?:\s+(?:pour|de))?)\s+(?:a\s+|an\s+|une?\s+|een\s+)?" + _APPLS + r"|"
    + _APPLS + r"\s+(?:connections?|hook-?ups?|points?|aansluiting(?:en)?|raccord(?:ement)?s?)|"
    r"(?:connections?|hook-?ups?|aansluiting(?:en)?|raccord(?:ement)?s?|branchements?|point\s+d'eau)\s+(?:for\s+|pour\s+|voor\s+|de\s+|d')?(?:a\s+|an\s+|une?\s+|een\s+)?" + _APPLS
)
MACHINE = (r"\b(?:washing\s+machines?|washer[-\s]dryers?|washer|tumble\s+dryers?|dryer|machines?\s+à\s+laver|lave[-\s]linge|sèche[-\s]linge|"
           r"wasmachines?|wasdroger|droogkast|wasautomaat)\b")

_YEARS = (r"(?:(?:[1-9]|one|two|three|een|twee|drie|un|une|deux|trois)[\s-]*(?:years?|ans?|jaar|jaren)(?![a-zé])|"
          r"(?:12|1[3-9]|2\d|twelve|douze|twaalf)[\s-]*(?:months?|mois|maanden))")
_FLEX = r"(?!.{0,50}?(?:shorter|plus\s+court|kortere?|negotiable|flexible|on\s+request))"
LONG_ONLY = (r"(?:(?:minimum|min\.?|minimale?|at\s+least|au\s+moins)\s+(?:\w+[\s:]+){0,3}?(?:of\s+|de\s+|van\s+)?" + _YEARS + r"|"
             + _YEARS + r"[\s-]*(?:minimum|min\b)|"
             r"(?:lease|bail|contract|huurcontract|huurovereenkomst|rental|dur[ée]e|duur)\s+(?:term\s+|duration\s+|period\s+|du\s+bail\s*)?(?:of|de|van|:)?\s*" + _YEARS + r"|"
             + _YEARS + r"[\s-]*(?:lease|bail|contract|rental|huur\w*)|"
             r"bail\s+(?:de\s+)?3[\s,-]*6[\s,-]*9|3[\s/-]6[\s/-]9|\b9\s+ans\b|\b9\s+jaar\b|long\s+term\s+only|langdurig\w*\s+(?:huur|verblijf)\s+enkel)" + _FLEX)
SHORT_TERM = (r"courte\s+dur[ée]e|court\s+terme|moyen\s+terme|kortlopend|korte\s+termijn|short[\s-]+term(?!\s+(?:lease|rental|contract)\s+of\s+(?:1|one|12))|mid[\s-]+term|medium[\s-]+term|"
              r"\b[1-9]\s*(?:à|-|tot|to)\s*1[0-2]?\s*(?:mois|months|maanden)|\b[1-9]\s*(?:or|ou|of|and|et|en|/)\s*(?:1[0-2]|[1-9])[\s-]*(?:months?|mois|maanden)|"
              r"(?:minimum|min\.?|minimale?|au\s+moins|at\s+least)\s+(?:\w+[\s:]+){0,3}?(?:of\s+|de\s+|van\s+)?[1-6][\s-]*(?:months?|mois|maanden)|"
              r"(?:from|dès|vanaf)\s+(?:1|one|un|een)\s+(?:months?|mois|maand)|flexible\s+(?:lease|duration|dur[ée]e|stay)|location\s+temporaire|tijdelijke\s+verhuur|mobility\s+lease|bail\s+de\s+mobilit[ée]|"
              r"stays?\s+from\s+\d+\s+months?")

RULES = {
    "shared":        ("bad",  True,  SHARED),
    "maybe_shared":  ("warn", True,  MAYBE_SHARED),
    "shared_laundry": ("info", True, SHARED_LAUNDRY),
    "laundry_hookup": ("info", True, HOOKUP),
    "laundry_machine": ("good", True, MACHINE),
    "no_domicile":   ("bad",  False, r"registration\s+(?:is\s+)?(?:not\s+(?:possible|allowed)|impossible|prohibited|forbidden)|no\s+(?:address\s+)?registration|cannot\s+(?:register|be\s+registered)|(?:pas|non)\s+(?:de\s+)?possibilit\w+\s+de\s+(?:se\s+)?domicili|inschrijving\s+(?:is\s+)?(?:niet\s+mogelijk|onmogelijk)|geen\s+inschrijving|niet\s+mogelijk\s+om\s+(?:zich\s+)?in\s+te\s+schrijven|(pas|sans|aucune|non)\s+(de\s+)?domicil|domiciliation\s+(impossible|interdite|non\s+autoris|pas\s+possible)|geen\s+domicili|domicili\w*\s+niet\s+(mogelijk|toegestaan)|no\s+domicil|not\s+possible\s+to\s+(register|domicil)|without\s+domicil"),
    "domicile_ok":   ("good", True,  r"(?:address\s+)?registration\s+(?:is\s+)?(?:possible|allowed|accepted|permitted)|(?:can|may)\s+(?:register|be\s+registered|domicil\w+)|inschrijving\s+(?:is\s+)?(?:mogelijk|toegestaan)|peut\s+(?:se\s+)?domicilier|domiciliation\s+est\s+possible|domiciliation\s+(possible|autoris|accept)|domicili\w*\s+(mogelijk|toegestaan)|domicil\w*\s+(is\s+)?(possible|allowed)|possibilit\w+\s+de\s+(se\s+)?domicil|registration\s+(possible|allowed)"),
    "short_term":    ("good", True,  SHORT_TERM),
    "long_only":     ("bad",  True,  LONG_ONLY),
    "students_only": ("bad",  True,  r"(r[ée]serv[ée]\s+aux|uniquement\s+(pour\s+)?(les\s+)?)[ée]tudiants|enkel\s+(voor\s+)?studenten|students\s+only"),
    "no_couple":     ("bad",  True,  r"(?:one|1|single)\s+(?:person|occupant|tenant)s?\s+(?:only|max)|only\s+(?:one|1|a\s+single)\s+(?:person|occupant|tenant)|(?:max|maximum)\s+(?:1|one)\s+(?:person|occupant|tenant)|1\s+persoon\s+(?:max|enkel|alleen)|geen\s+koppels|pas\s+de\s+couples?|no\s+couples|singles?\s+only|pour\s+une\s+(seule\s+)?personne|for\s+(one|a\s+single)\s+person|voor\s+(één|1)\s+persoon|une\s+seule\s+personne|1\s+personne\s+(max|uniquement)|single\s+(person|occupancy)\s+only|één\s+persoon"),
    "fridge":        ("good", True,  r"frigo|r[ée]frig[ée]rateur|koelkast|fridge|refrigerator|cuisine\s+(?:ouverte\s+)?(?:super\s+|hyper\s+|semi[\s-]?|enti[èe]rement\s+|totalement\s+)?[ée]quip[ée]e|(?:volledig\s+|half\s+|semi[\s-]?)?(?:ingerichte|uitgeruste)\s+keuken|(?:fully|semi|partly|well)[\s-]*equipped\s+(?:open\s+|separate\s+|modern\s+)?kitchen|equipped\s+kitchen|kitchen(?:ette)?\s+(?:is\s+)?(?:fully\s+)?equipped|equipped\s+with\s+(?:essential\s+|all\s+|modern\s+)?(?:kitchen\s+)?appliances|[ée]lectrom[ée]nager"),
    "furnished":     ("good", True,  r"\bmeubl[é]e?s?\b|(?:appartement|studio|logement)\s+meubles?\b|gemeubeld|(?<!can be )(?<!may be )(?<!could be )\bfurnished(?!\s+(?:at|for)\s+(?:an?\s+)?(?:extra|additional))|\bbemeubeld|\bfurnishings\b|\barredato"),
    "bills_incl":    ("good", True,  r"all[\s-]?in\b|all[\s-]?inclusive|bills\s+included|utilities\s+included|charges\s+(?:are\s+)?included|incl(?:uding|\.)?\s+(?:all\s+)?(?:utilities|bills|charges)|toutes\s+charges\s+comprises|charges\s+comprises|kosten\s+inbegrepen|alles\s+inbegrepen"),
}
_COMPILED = {k: (kind, neg, re.compile(p, re.I)) for k, (kind, neg, p) in RULES.items()}
_NEG = re.compile(r"(?:\bnot?\b|\bno\b|\bnon\b|\bnone\b|\bwithout\b|\bsans\b|\bpas\s+(?:de|d')|\bgeen\b|\bniet\b|\bzonder\b|n'est\s+pas|\bnever\b)", re.I)
_PARTIAL = re.compile(r"\bsemi[-\s]?|\bpartly\b|\bpartially\b", re.I)
_URL = re.compile(r"https?://\S+")


def clean_text(s):
    """Decoded text, tags removed, links replaced, whitespace collapsed."""
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", _URL.sub("[link]", s)).strip()


def _negated(text, start, flag=""):
    seg = text[max(0, start - 30):start]
    cut = max(seg.rfind(c) for c in ".;!?:\n")
    seg = seg[cut + 1:] if cut >= 0 else seg
    return bool(_NEG.search(seg) or (flag == "furnished" and _PARTIAL.search(seg)))


def _overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def scan(text):
    """All rule matches as (start, end, flag, kind, negated). A washing machine inside a 'shared laundry' or 'connection' phrase is not counted."""
    spans = []
    for flag, (kind, negatable, rx) in _COMPILED.items():
        for m in rx.finditer(text):
            spans.append((m.start(), m.end(), flag, kind, negatable and _negated(text, m.start(), flag)))
    blockers = [(s, e) for s, e, f, _k, n in spans if f in ("shared_laundry", "laundry_hookup") and not n]
    return [sp for sp in spans if not (sp[2] == "laundry_machine" and any(_overlap(sp, b) for b in blockers))]


def facts(description, title=""):
    """(flags, evidence): flags[name] is True when a non-negated match exists; evidence[name] is the phrase around it."""
    text = f"{clean_text(title)}. {clean_text(description)}"
    flags, ev = {k: False for k in RULES}, {}
    for s, e, flag, _kind, neg in scan(text):
        if neg or flag in ev:
            continue
        flags[flag] = True
        ev[flag] = ("…" if s > 40 else "") + text[max(0, s - 40):e + 40].strip() + ("…" if e + 40 < len(text) else "")
    if flags["laundry_machine"]:                   # a machine of its own makes the building's laundry room irrelevant
        flags["shared_laundry"] = flags["laundry_hookup"] = False
    return flags, ev


def highlight_html(description):
    """The description, escaped, with the important phrases wrapped in <mark class="hl-kind" title="flag">."""
    text = clean_text(description)
    spans = sorted((s, e, f, k) for s, e, f, k, n in scan(text) if not n)
    out, pos = [], 0
    for s, e, f, k in spans:
        if s < pos:
            continue                                # overlapping match: keep the first
        out.append(html.escape(text[pos:s]))
        out.append(f'<mark class="hl-{k}" title="{f.replace("_", " ")}">{html.escape(text[s:e])}</mark>')
        pos = e
    out.append(html.escape(text[pos:]))
    return "".join(out)


# ---------------------------------------------------------------- money and size facts
_EUR = r"(?:€\s?(\d[\d.,\s]{0,7}\d|\d)|(\d[\d.,\s]{0,7}\d|\d)\s?(?:€|eur\b|euros?\b))"
_WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "une": 1, "un": 1, "deux": 2, "trois": 3, "quatre": 4, "een": 1, "twee": 2, "drie": 3, "vier": 4}


def _num(s):
    """'1,250' / '1.250' / '1 250' / '1.250,50' / '125' -> 1250 / 1250 / 1250 / 1250 / 125 (whole euros)."""
    s = re.sub(r"\s", "", s or "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", "") if re.search(r",\d{3}$", s) else s.replace(",", ".")
    elif "." in s and re.search(r"\.\d{3}$", s):
        s = s.replace(".", "")
    try:
        return int(round(float(s)))
    except ValueError:
        return None


def _eur(m):
    return _num(m.group(1) or m.group(2))


def _snip(text, s, e):
    return ("…" if s > 50 else "") + text[max(0, s - 50):e + 50].strip() + ("…" if e + 50 < len(text) else "")


_COUPLE = re.compile(r"couples?|second\s+(?:person|occupant|tenant)|2nd\s+(?:person|occupant)|two\s+(?:people|persons|occupants|tenants)|deuxième\s+(?:personne|occupant)|2\s+personnes|twee\s+personen|tweede\s+(?:persoon|bewoner)|koppels?|extra\s+(?:person|occupant)", re.I)
_EXTRA = re.compile(r"additional|extra|supplement(?:ary)?|surcharge|supplément|toeslag|aanvullend|per\s+month|monthly|par\s+mois|per\s+maand|applied|applies|charged", re.I)
_UTIL_EXCL = re.compile(
    r"(?:does\s+not|doesn't|do\s+not|not)\s+include\s+(?:the\s+)?(?:utilities|charges|water|electricity|gas|internet)|"
    r"(?:utilities|charges|water|electricity|gas)\s+(?:are\s+|is\s+)?(?:not\s+included|excluded|extra|on\s+top)|"
    r"excl(?:uding|\.|usive|usief)\s+(?:of\s+)?(?:utilities|charges|water|electricity|gas|kosten|nutsvoorzieningen)|"
    r"hors\s+charges|charges\s+non\s+comprises|charges\s+en\s+sus|exclusief\s+(?:kosten|nutsvoorzieningen|energie)", re.I)
_FEE = re.compile(r"(?:agency|admin(?:istrative|istration)?|booking|contract|file|dossier|set-?up|key|cleaning|inventory|check-?in)\s+fees?|"
                  r"frais\s+(?:d'agence|de\s+dossier|d'état\s+des\s+lieux|de\s+réservation|de\s+nettoyage)|dossierkosten|administratiekosten|makelaarskosten|plaatsbeschrijving\s+kosten", re.I)


def costs(description):
    """Deposit, extra monthly charge for a couple / second person, 'utilities not included', one-off fees and the rent quoted in the text,
    each with the phrase it came from. Amounts are only taken from the text; listing data (when the site has it) overrides them elsewhere."""
    t = clean_text(description)
    out = {}
    m = re.search(r"(?:security\s+deposit|rental\s+deposit|rent\s+deposit|deposit|garantie\s+locative|caution|huurwaarborg|waarborg)[^.€\d]{0,40}?(?:of\s+|de\s+|van\s+|:\s*)?" + _EUR, t, re.I)
    if m and (_eur(m) or 0) >= 100:
        out["deposit"], out["deposit_ev"] = _eur(m), _snip(t, m.start(), m.end())
    else:
        m = re.search(r"(?:garantie\s+locative|huurwaarborg|waarborg|deposit|caution)[^.\d]{0,30}(\d(?:[.,]\d)?)\s*(?:mois|months?|maanden|maand)|(\d(?:[.,]\d)?)\s*(?:months?|mois|maanden)['’]?\s*(?:rent|loyer|huur)?[^.]{0,20}(?:deposit|garantie|caution|waarborg)", t, re.I)
        if m:
            out["deposit_months"], out["deposit_ev"] = float((m.group(1) or m.group(2)).replace(",", ".")), _snip(t, m.start(), m.end())
    for sent in re.split(r"(?<=[.!?])\s+", t):                      # a sentence about couples that names an amount and says it is extra
        am = re.search(_EUR, sent, re.I)
        if am and _COUPLE.search(sent) and _EXTRA.search(sent) and 20 <= (_eur(am) or 0) <= 600:
            out["couple_extra"], out["couple_ev"] = _eur(am), sent[:160]
            break
    mu = _UTIL_EXCL.search(t)
    if mu:
        out["utilities_excluded"], out["util_ev"] = True, _snip(t, mu.start(), mu.end())
    fees, ev = 0, ""
    for mf in _FEE.finditer(t):
        am = re.search(_EUR, t[mf.end():mf.end() + 45], re.I) or re.search(_EUR, t[max(0, mf.start() - 30):mf.start()], re.I)
        if am and 20 <= (_eur(am) or 0) <= 2000:
            fees, ev = fees + _eur(am), ev or _snip(t, mf.start(), mf.end() + 20)
    if fees:
        out["one_off"], out["one_off_ev"] = fees, ev
    mr = re.search(r"(?:monthly\s+rent|rent|loyer|huurprijs|huur)\s+(?:of|is|at|de|van|:)?\s{0,3}" + _EUR, t, re.I)
    if mr and (_eur(mr) or 0) >= 200:
        out["text_rent"] = _eur(mr)
    return out


def numbers(description, title=""):
    """Bedrooms and living area when the text says them clearly (otherwise None): 'studio', 'two bedrooms', 'surface of 38 m²'."""
    t = f"{clean_text(title)}. {clean_text(description)}"
    out = {"bedrooms": None, "m2": None}
    m = re.search(r"(?:total\s+)?(?:living\s+|habitable\s+|floor\s+)?(?:area|surface|size|superficie|oppervlakte)\s+(?:of\s+|de\s+|van\s+|:\s*)?(?:approximately\s+|about\s+|±\s*|\+/-\s*)?(\d{2,3})\s?(?:m²|m2|sqm)|"
                  r"(\d{2,3})\s?(?:m²|m2|sqm)\s+(?:apartment|studio|flat|appartement|woning)|(?:apartment|studio|flat|appartement)\s+(?:of|de|van)\s+(?:approximately\s+)?(\d{2,3})\s?(?:m²|m2)", t, re.I)
    if m:
        v = int(next(g for g in m.groups() if g))
        out["m2"] = v if 12 <= v <= 300 else None
    m = re.search(r"(\d)[\s-]*bedrooms?\b|(\d)\s+chambres?(?:\s+à\s+coucher)?\b|(\d)\s+slaapkamers?\b|\b(one|two|three|four|une|un|deux|trois|quatre|een|twee|drie|vier)[\s-]+(?:bed)?rooms?\b|"
                  r"\b(one|two|three|four|une|deux|trois|quatre|een|twee|drie|vier)[\s-]+(?:chambres?|slaapkamers?)\b", t, re.I)
    if m:
        g = next(g for g in m.groups() if g)
        out["bedrooms"] = int(g) if g.isdigit() else _WORDNUM.get(g.lower())
    elif re.search(r"\bstudio\b", t, re.I):
        out["bedrooms"] = 0
    return out
