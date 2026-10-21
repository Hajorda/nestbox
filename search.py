"""Search behind the search bar: finds a flat from a phone number, an email address, an address, a word from the description, your notes or a mail.

`run(query, docs)`: docs is {listing id: [(label, text), ...]}. Returns {id: [(label, snippet), ...]} for every listing that matches.
- a query that looks like a phone number matches numbers written in any way ("0473 79 65 52", "+32 473 796 552", "0032473796552")
- anything else: every word must appear somewhere in the flat's texts (case and accents ignored)
"""
import re, unicodedata

PHONE_Q = re.compile(r"^[+\d\s./()-]{6,}$")
PHONE_IN_TEXT = re.compile(r"(?:\+|00)?\d[\d\s./()-]{5,}\d")


def fold(s):
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def fold_map(text):
    """The folded text and, for each folded character, where it came from in the original (accents can change the length)."""
    chars, idx = [], []
    for i, c in enumerate(text):
        f = fold(c)
        chars.append(f)
        idx.extend([i] * len(f))
    return "".join(chars), idx


def norm_phone(s):
    d = re.sub(r"\D", "", s)
    d = re.sub(r"^(00)?32", "", d)
    return d.lstrip("0")


def snippet(text, i, n):
    a, b = max(0, i - 35), min(len(text), i + n + 45)
    return ("…" if a else "") + text[a:b].replace("\n", " ").strip() + ("…" if b < len(text) else "")


def run(query, docs, limit=300):
    query = (query or "").strip()
    out = {}
    if len(query) < 3:
        return out
    if PHONE_Q.match(query) and len(norm_phone(query)) >= 6:
        qn = norm_phone(query)
        for lid, parts in docs.items():
            for label, text in parts:
                hit = next((m for m in PHONE_IN_TEXT.finditer(text or "") if len(norm_phone(m.group())) >= 6 and (qn in norm_phone(m.group()) or norm_phone(m.group()) in qn)), None)
                if hit:
                    out.setdefault(lid, []).append((label, snippet(text, hit.start(), len(hit.group()))))
                    break
            if len(out) >= limit:
                break
        return out
    words = [fold(w) for w in query.split() if w]
    for lid, parts in docs.items():
        folded = [(label, text or "") + fold_map(text or "") for label, text in parts]
        whole = " ".join(f for _l, _t, f, _m in folded)
        if not all(w in whole for w in words):
            continue
        hits = []
        for label, text, f, idx in folded:
            i = f.find(words[0])
            if i >= 0:
                hits.append((label, snippet(text, idx[i], max(1, idx[min(i + len(words[0]), len(idx)) - 1] - idx[i] + 1))))
        out[lid] = hits or [("details", "")]
        if len(out) >= limit:
            break
    return out
