"""Perception Layer — docs/architecture.md §1 layer 2, §2.1.

Pre-processing & enrichment of a raw inbound utterance: clean-up, language
detection (English / Hindi / Hinglish) and entity extraction (order id, email,
last-four digits, name…). Speech-to-text output is noisy — "O R D 8 3 9 2 1",
"aarav dot sharma at example dot com" — so the extractors are forgiving.

Deterministic on purpose: it runs on every utterance in a few milliseconds and
has no dependency on a model being loaded.
"""

import re
from typing import TypedDict

HINGLISH = {
    "mera", "meri", "mere", "hai", "hain", "nahi", "nahin", "kya", "aap", "mujhe", "kar", "karo", "kijiye",
    "haan", "ji", "accha", "theek", "paisa", "paise", "wapas", "kab", "kyun", "abhi", "bhai", "yaar", "hoon",
    "chahiye", "bataiye", "batao", "samajh", "order", "ho", "gaya", "gayi", "raha", "rahi", "se", "ko", "ka", "ki",
}
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
_ORDER = re.compile(r"\bord(?:er)?[\s\-:#]*(?:id|number|no)?[\s\-:#]*(?:is\s+)?(?:ord)?[\s\-:#]*((?:\d[\s\-]*){4,6})", re.I)
_ORDER_PLAIN = re.compile(r"\bORD-?(\d{4,6})\b", re.I)
_REFUND = re.compile(r"\bRFD[\s\-]*(\d{4,6})\b", re.I)
_TICKET = re.compile(r"\bPH[\s\-]*(\d{3,5})\b", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_SPOKEN_EMAIL = re.compile(r"\b([\w.]+(?:\s+dot\s+\w+)*)\s+at\s+(?:the\s+rate\s+)?([\w]+(?:\s+dot\s+\w+)+)\b", re.I)
_LAST4 = re.compile(r"(?:last\s+(?:four|4)\s+digits?|ending\s+(?:in|with))\D{0,48}?((?:\d[\s\-]*){4})", re.I)
_NAME = re.compile(
    r"\b(?:my\s+name\s+is|this\s+is|i\s+am|i'm|im|name\s*:|mera\s+naam)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", re.I
)
_NAME_STOP = {
    "calling", "having", "trying", "not", "very", "so", "just", "a", "an", "the", "here", "sorry", "really",
    "getting", "facing", "unable", "still", "on", "in", "at", "with", "from", "looking", "wondering", "actually",
    "ready", "back", "fine", "good", "okay", "ok", "sure", "glad", "happy", "frustrated", "annoyed", "angry",
    "worried", "confused", "waiting", "afraid", "aware", "done", "going", "able", "thinking", "wanting", "hoon",
    "want", "need", "charged", "locked", "yes", "no", "please", "thank", "thanks", "dot", "at", "calling",
}
_AMOUNT = re.compile(r"(?:₹|rs\.?\s?|inr\s?|rupees\s+)(\d[\d,]*)", re.I)
_LEADING_FILLER = re.compile(r"^(?:(?:uh+|um+|umm+|hmm+|er+|like|so|well|okay|ok|actually),?\s+)+", re.I)


class EnrichedMessage(TypedDict):
    text: str
    language: str
    channel: str
    entities: dict


def detect_language(text: str) -> str:
    if len(_DEVANAGARI.findall(text)) >= 3:
        return "hi"
    words = re.findall(r"[a-z]+", text.lower())
    if len(words) >= 3 and sum(w in HINGLISH for w in words) >= 3:
        return "hi"
    return "en"


def _digits(s: str) -> str:
    return re.sub(r"\D", "", s)


_SPELLED_ORD = re.compile(r"\bo[\s.\-]+r[\s.\-]+d\b", re.I)


def extract_entities(text: str) -> dict:
    ent: dict = {}
    text = _SPELLED_ORD.sub("ORD", text)  # speech-to-text sometimes spells it: "O R D 8 3 9 2 1"
    m = _ORDER_PLAIN.search(text) or _ORDER.search(text)
    if m:
        d = _digits(m.group(1))
        if 4 <= len(d) <= 6:
            ent["order_id"] = f"ORD-{d}"
    m = _REFUND.search(text)
    if m:
        ent["refund_id"] = f"RFD-{_digits(m.group(1))}"
    m = _TICKET.search(text)
    if m:
        ent["ticket_ref"] = f"PH-{_digits(m.group(1))}"
    m = _EMAIL.search(text)
    if m:
        ent["email"] = m.group(0).lower()
    else:
        sm = _SPOKEN_EMAIL.search(text)
        if sm:
            local = re.sub(r"\s+dot\s+", ".", sm.group(1).strip(), flags=re.I).replace(" ", "")
            domain = re.sub(r"\s+dot\s+", ".", sm.group(2).strip(), flags=re.I).replace(" ", "")
            ent["email"] = f"{local}@{domain}".lower()
    m = _LAST4.search(text)
    if m:
        ent["phone_last4"] = _digits(m.group(1))[:4]
    m = _NAME.search(text)
    if m:
        words = [w for w in m.group(1).split() if w.lower() not in _NAME_STOP]
        if words:
            ent["name"] = " ".join(w.capitalize() for w in words[:2])
    m = _AMOUNT.search(text)
    if m:
        ent["amount"] = int(_digits(m.group(1)) or 0)
    return ent


def clean(text: str) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    t = _LEADING_FILLER.sub("", t)
    return t[:1].upper() + t[1:] if t else t


def enrich(raw_text: str, channel: str = "Call") -> EnrichedMessage:
    text = clean(raw_text)
    return {
        "text": text,
        "language": detect_language(text),
        "channel": channel,
        "entities": extract_entities(raw_text),
    }
