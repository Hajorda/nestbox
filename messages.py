"""Ready-to-send messages for a listing, in FR / NL / EN, filled from config.json.

The texts are templates with {placeholders}. The defaults are below; to change one, edit it in the control panel ("Messages"), which saves your
version in templates.json. A placeholder that does not exist stays as it is, so a typo is visible in the preview instead of breaking anything.
"""
import json, os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_FILE = os.path.join(HERE, "templates.json")

MONTHS = {
    "fr": ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"],
    "nl": ["januari", "februari", "maart", "april", "mei", "juni", "juli", "augustus", "september", "oktober", "november", "december"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
}


def _d(iso, lang):
    d = date.fromisoformat(iso)
    return f"1er {MONTHS[lang][d.month - 1]} {d.year}" if lang == "fr" and d.day == 1 else f"{d.day} {MONTHS[lang][d.month - 1]} {d.year}"


DEFAULT_VISITS = {"fr": "en semaine après 18h et le week-end", "nl": "op weekdagen na 18u en in het weekend"}

DEFAULTS = {
    "fr": ("Bonjour,\n\n{intro} en stage chez {workplace} à Haren jusqu'au {internship_end}. Votre annonce nous intéresse : {where} (€{rent}/mois).\n\n"
           "Nous cherchons un logement du {move_in} au {move_out} (date d'entrée flexible), nous sommes calmes, non-fumeurs, "
           "et nous pouvons fournir nos pièces d'identité et notre convention de stage.\n\n"
           "Questions rapides :\n1. Peut-on se domicilier à cette adresse (bail de résidence principale) ?\n"
           "2. Une location de {months} mois est-elle envisageable ?\n3. Y a-t-il un frigo / une cuisine équipée ?\n"
           "4. Quel est le montant des charges et de la garantie locative ?\n\n"
           "Nous sommes déjà à Bruxelles et disponibles pour une visite ({visits}).\n\nMerci beaucoup,\n{signature}\n{phone}\n{email}"),
    "nl": ("Goedendag,\n\n{intro} en doen een stage bij {workplace} in Haren tot {internship_end}. Uw advertentie interesseert ons: {where} (€{rent}/maand).\n\n"
           "Wij zoeken een woning van {move_in} tot {move_out} (startdatum flexibel), zijn rustig, niet-rokers, "
           "en kunnen onze identiteitsbewijzen en stageovereenkomst voorleggen.\n\n"
           "Enkele korte vragen:\n1. Is domiciliëring op dit adres mogelijk (huurovereenkomst hoofdverblijfplaats)?\n"
           "2. Is een huur van {months} maanden bespreekbaar?\n3. Is er een koelkast / ingerichte keuken?\n"
           "4. Hoeveel bedragen de kosten en de huurwaarborg?\n\n"
           "Wij zijn al in Brussel en beschikbaar voor een bezoek ({visits}).\n\nAlvast bedankt,\n{signature}\n{phone}\n{email}"),
    "en": ("Hello,\n\n{intro} doing an internship at {workplace} in Haren until {internship_end}, and we are interested in your listing: {where} (€{rent}/month).\n\n"
           "We are looking for a place from {move_in} to {move_out} (start date flexible). We are quiet non-smokers "
           "and can provide our IDs and our internship agreement.\n\n"
           "Quick questions:\n1. Can we register our address (domiciliation) with a main-residence lease?\n"
           "2. Would a {months}-month lease be possible?\n3. Is there a fridge / equipped kitchen?\n"
           "4. How much are the monthly charges and the deposit?\n\n"
           "We are already in Brussels and can visit ({visits}).\n\nThanks,\n{signature}\n{phone}\n{email}"),
    "fu_fr": ("Bonjour,\n\nJe me permets de revenir vers vous au sujet de votre annonce ({where}). Le logement est-il toujours disponible ? "
              "Nous restons très intéressés, pour {months} mois à partir du {move_in}, et pouvons visiter à votre convenance ({visits}).\n\n"
              "Merci d'avance,\n{signature}\n{phone}\n{email}"),
    "fu_nl": ("Goedendag,\n\nIk kom graag nog even terug op uw advertentie ({where}). Is de woning nog beschikbaar? "
              "Wij blijven erg geïnteresseerd, voor {months} maanden vanaf {move_in}, en kunnen bezichtigen wanneer het u past ({visits}).\n\n"
              "Alvast bedankt,\n{signature}\n{phone}\n{email}"),
    "fu_en": ("Hello,\n\nI am following up on your listing ({where}). Is the flat still available? "
              "We are still very interested, for {months} months from {move_in}, and can visit whenever suits you ({visits}).\n\n"
              "Thanks,\n{signature}\n{phone}\n{email}"),
}

PLACEHOLDERS = {
    "intro": "who you are, for example 'We are two people (Sam and Alex)'; changes with the language and with / without a second name",
    "signature": "your name", "second_name": "the second person's name (may be empty)", "phone": "your phone number", "email": "your email address",
    "workplace": "where you work, from your details (profile 'workplace', default EUROCONTROL)",
    "internship_end": "the end of your internship (profile 'internship_end', default 15 April 2027)",
    "move_in": "your move-in date, written out", "move_out": "your move-out date, written out", "months": "length of your stay in months",
    "visits": "when you can visit", "where": "the flat's street, postcode and area", "rent": "the monthly rent in euros",
    "title": "the title of the ad", "url": "the link of the ad", "agency": "the agency or seller",
}


class _Safe(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def render(template, variables):
    """Fills the {placeholders}. Unknown ones are left as typed (and any odd braces too), so a typo shows in the preview and nothing crashes."""
    try:
        return template.format_map(_Safe(variables))
    except (ValueError, IndexError, KeyError, AttributeError):
        out = template
        for k, v in variables.items():
            out = out.replace("{" + k + "}", str(v))
        return out


def overrides():
    try:
        with open(TEMPLATES_FILE) as f:
            d = json.load(f)
        return {k: v for k, v in d.items() if k in DEFAULTS and isinstance(v, str) and v.strip()}
    except (OSError, ValueError):
        return {}


def templates():
    return {**DEFAULTS, **overrides()}


def variables(item, cfg, lang):
    p = cfg["profile"]
    n = max(1, round((date.fromisoformat(p["move_out"]) - date.fromisoformat(p["move_in"])).days / 30.4))   # length of your stay in months
    visits = DEFAULT_VISITS[lang] if lang in DEFAULT_VISITS and p["visit_times"] == "weekdays after 18:00 and weekends" else p["visit_times"]
    sig, second = p["signature"], (p.get("second_name") or "").strip()
    intro = {"fr": f"Nous sommes deux personnes ({sig} et {second})" if second else f"Je m'appelle {sig} et nous sommes deux personnes",
             "nl": f"Wij zijn met twee ({sig} en {second})" if second else f"Mijn naam is {sig} en wij zijn met twee",
             "en": f"We are two people ({sig} and {second})" if second else f"My name is {sig} and we are two people"}[lang]
    where = " ".join(x for x in (item.get("street"), item.get("postal"), item.get("locality")) if x) or item.get("url", "")
    return {"intro": intro, "signature": sig, "second_name": second, "phone": p.get("phone", ""), "email": p.get("email", ""),
            "workplace": p.get("workplace") or "EUROCONTROL", "internship_end": _d(p.get("internship_end") or "2027-04-15", lang),
            "move_in": _d(p["move_in"], lang), "move_out": _d(p["move_out"], lang), "months": n, "visits": visits, "where": where,
            "rent": item.get("rent", ""), "title": item.get("title", ""), "url": item.get("url", ""), "agency": item.get("agency") or ""}


def build(item, cfg):
    t = templates()
    return {key: render(t[key], variables(item, cfg, key[-2:])) for key in DEFAULTS}


def language(item, cfg):
    return (cfg["areas"].get(item.get("postal")) or {}).get("lang", "fr")
