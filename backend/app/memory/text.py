"""Tokenisation shared by the vector index, the knowledge graph and Jev.

No ML dependency on purpose: the vector half of the memory runs anywhere the
backend runs (a 4 GB GPU is fully occupied by the language model).
"""

import re

STOPWORDS = set(
    """a an the and or but if then else when while of at by for with about against between into through during
    before after above below to from up down in out on off over under again further once here there all any both
    each few more most other some such no nor not only own same so than too very can will just don should now
    is am are was were be been being have has had having do does did doing i me my myself we our ours you your
    yours he him his she her hers it its they them their what which who whom this that these those would could
    also please hi hello hey okay ok yes yeah umm uh um hmm like get got want need know tell let say said one
    im ive dont cant wont didnt doesnt isnt wasnt thats theres youre""".split()
)

# Query-side normalisation: map how customers talk onto how SOPs are written.
SYNONYMS = {
    "twice": "duplicate", "double": "duplicate", "doubled": "duplicate", "again": "duplicate",
    "deducted": "payment", "debited": "payment", "charged": "payment", "billed": "payment",
    "paid": "payment", "money": "payment", "amount": "payment",
    "returned": "return", "refunded": "refund", "reimbursement": "refund",
    "locked": "lock", "unlock": "lock", "blocked": "lock", "login": "login", "signin": "login",
    "parcel": "shipment", "package": "shipment", "courier": "shipment", "delivered": "delivery",
    "arrived": "delivery", "arrive": "delivery", "tracking": "shipment", "track": "shipment",
    "crashing": "crash", "crashes": "crash", "crashed": "crash", "frozen": "freeze", "freezing": "freeze",
    "headphones": "headphone", "earbuds": "headphone", "earphones": "headphone",
    "flashing": "blink", "blinking": "blink", "light": "led", "lights": "led",
    "passcode": "password", "pwd": "password", "otp": "otp",
    "cancelled": "cancel", "cancelling": "cancel", "cancellation": "cancel",
    "broken": "damage", "damaged": "damage", "defective": "damage", "faulty": "damage",
}

_TOKEN = re.compile(r"[a-z0-9ऀ-ॿ]+")


def stem(w: str) -> str:
    if len(w) <= 3 or w.isdigit():
        return w
    for suf in ("ingly", "edly", "ing", "ies", "ed", "es", "s", "ly"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            base = w[: -len(suf)]
            return base + "y" if suf == "ies" else base
    return w


def tokens(text: str, *, expand: bool = False) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS or len(raw) < 2:
            continue
        w = SYNONYMS.get(raw, raw) if expand else raw
        out.append(stem(w))
    return out


def slug(label: str) -> str:
    return "-".join(_TOKEN.findall(label.lower()))[:60] or "x"
