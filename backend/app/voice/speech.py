"""Turn model text into natural *spoken* text, plus the human-sounding fillers.

Everything the agent says goes through `to_spoken()`; the on-screen transcript
keeps the original text.
"""

import random
import re

# ── acknowledgement / filler bank ────────────────────────────────────────────
# kind -> phrases. Picked by the conversation pipeline before the language model
# has produced its first word, so the caller never sits in silence.
FILLER_BANK: dict[str, dict[str, list[str]]] = {
    "en": {
        "greeting": ["Hi there!", "Hello!", "Hey, hi!"],
        "ack": ["Mm-hmm.", "Okay, right.", "Yeah, sure.", "Hmm, okay.", "Okay okay.", "Right, right."],
        "empathy": [
            "Oh no, I'm sorry about that.",
            "Ugh, that's annoying. Sorry about that.",
            "Oh, that's frustrating, sorry.",
            "Oh man, sorry about that.",
        ],
        "checking": [
            "Umm, give me just a second, let me check that.",
            "Okay, hang on, pulling that up.",
            "Hmm, one moment, let me look.",
            "Sure, let me check that for you.",
            "Okay, one sec, let me see.",
            "Right, hold on a moment.",
        ],
        "thanks": ["Of course!", "Yeah, for sure.", "Anytime!", "Thanks for waiting."],
        "nudge_side": ["Take your time, I'm right here."],
        "nudge_silence": ["Hello? Are you still there?"],
    },
    "hi": {
        "greeting": ["Namaste!", "Hello ji!"],
        "ack": ["Hmm, theek hai.", "Accha, samajh gayi.", "Haan ji.", "Ji, bilkul."],
        "empathy": ["Oh, mujhe bahut afsos hai.", "Arre, yeh toh bahut galat hua, sorry."],
        "checking": ["Ek second, main check karti hoon.", "Hmm, ruko zara, dekhti hoon.", "Acha, ek minute, dekhti hoon."],
        "thanks": ["Koi baat nahi!", "Bilkul!"],
        "nudge_side": ["Aap araam se baat kar lijiye, main yahin hoon."],
        "nudge_silence": ["Hello? Aap sun rahe hain?"],
    },
}

_last_pick: dict[str, str] = {}


def pick_filler(kind: str, lang: str = "en") -> str:
    bank = FILLER_BANK.get(lang, FILLER_BANK["en"]).get(kind) or FILLER_BANK["en"]["ack"]
    choices = [p for p in bank if p != _last_pick.get(f"{lang}:{kind}")] or bank
    pick = random.choice(choices)
    _last_pick[f"{lang}:{kind}"] = pick
    return pick


# ── spoken-text normalisation ────────────────────────────────────────────────

_ID = re.compile(r"\b([A-Z]{2,4})-(\d{3,6})\b")
_MD = re.compile(r"[*_`#>]+|\[SIDE_TALK\]")
_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿]")
_RUPEE = re.compile(r"(?:₹|Rs\.?\s?|INR\s?)(\d[\d,]*)")


def _spell_id(m: re.Match) -> str:
    letters = " ".join(m.group(1))
    digits = " ".join(m.group(2))
    return f"{letters}, {digits},"


def to_spoken(text: str) -> str:
    t = _EMOJI.sub("", text)
    t = _MD.sub("", t)
    t = _RUPEE.sub(lambda m: f"{m.group(1)} rupees", t)
    t = _ID.sub(_spell_id, t)
    t = t.replace("&", " and ").replace("%", " percent").replace("/", " or ")
    t = re.sub(r"\s*\n+\s*", ". ", t)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r",\s*([.!?])", r"\1", t)
    return t.strip()


# ── sentence streaming ───────────────────────────────────────────────────────

_END = re.compile(r"([.!?…]+[\"')\]]*)(\s+|$)")


class SentenceStreamer:
    """Turns a token stream into speakable sentences as early as possible.

    The first sentence is released aggressively (a comma after ~7 words is enough)
    because time-to-first-audio is what makes the voice feel live.
    """

    def __init__(self) -> None:
        self.buf = ""
        self.emitted = 0

    def feed(self, piece: str) -> list[str]:
        self.buf += piece
        out: list[str] = []
        while True:
            m = _END.search(self.buf)
            cut = None
            if m and m.end() <= len(self.buf) and (m.end() < len(self.buf) or self.buf.rstrip()[-1:] in ".!?…"):
                # don't split on "Mr." / decimals like 2.5
                head = self.buf[: m.start()]
                if not re.search(r"(\d|\b[A-Z][a-z]?)$", head) or head.endswith(("?", "!")):
                    cut = m.end()
            if cut is None and self.emitted == 0:
                words = len(self.buf.split())
                c = self.buf.find(",", 25)
                # never split inside a number like 2,499 (the next char must not be a digit)
                while c != -1 and c + 1 < len(self.buf) and self.buf[c + 1].isdigit():
                    c = self.buf.find(",", c + 1)
                if c != -1 and words >= 7 and len(self.buf) - c > 1:
                    cut = c + 1
            if cut is None and len(self.buf) > 220:
                sp = self.buf.rfind(" ", 0, 200)
                cut = sp if sp > 0 else 200
            if cut is None:
                break
            sentence, self.buf = self.buf[:cut].strip(), self.buf[cut:].lstrip()
            if sentence:
                out.append(sentence)
                self.emitted += 1
        return out

    def flush(self) -> str | None:
        rest = self.buf.strip()
        self.buf = ""
        if rest:
            self.emitted += 1
            return rest
        return None


# ── de-scripting: turn call-centre phrasing into how a person would say it ───

_STIFF = [
    (re.compile(r"\bI (?:completely |totally |fully )?understand (?:your|that|how|the)[^.,!?]*[.,!?]\s*", re.I), ""),
    (re.compile(r"\bI(?:'m| am) (?:really |so |truly )?sorry for the inconvenience[^.!?]*", re.I), "Sorry about that"),
    (re.compile(r"\bI apologi[sz]e for (?:the|any) inconvenience[^.!?]*", re.I), "Sorry about that"),
    (re.compile(r"\bThank you for (?:reaching out|contacting)[^.!?]*[.!?]\s*", re.I), ""),
    (re.compile(r"^\s*(?:Certainly|Absolutely|Definitely)[!,.]?\s*", re.I), "Sure, "),
    (re.compile(r"\bIs there anything else I can (?:help|assist) you with(?: today)?\?", re.I), "Anything else I can sort out for you?"),
    (re.compile(r"\bHow (?:may|can) I (?:assist|help) you(?: today)?\?", re.I), "What can I do for you?"),
    (re.compile(r"\b[Rr]est assured,?\s*", re.I), ""),
    (re.compile(r"\bplease note that\s*", re.I), ""),
    (re.compile(r"\bkindly\b", re.I), "please"),
    (re.compile(r"\bvalued customer\b", re.I), ""),
    (re.compile(r"\bI would like to\b"), "I'd like to"),
    (re.compile(r"\bI will\b"), "I'll"),
    (re.compile(r"\bI am\b"), "I'm"),
    (re.compile(r"\bdo not\b"), "don't"),
    (re.compile(r"\bcannot\b"), "can't"),
    (re.compile(r"\bwill not\b"), "won't"),
    (re.compile(r"\b([Ii])t is\b"), r"\1t's"),
    (re.compile(r"\b([Tt])hat is\b"), r"\1hat's"),
    (re.compile(r"\b([Yy])ou are\b"), r"\1ou're"),
    (re.compile(r"\b([Ww])e are\b"), r"\1e're"),
    (re.compile(r"\b([Ww])ould you like me to\b"), r"\1ant me to"),
]


_ISO_DATE = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
_MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]


def speak_dates(text: str) -> str:
    """2026-09-27 -> "27 September" (the current year is never read out)."""
    def one(m: re.Match) -> str:
        month = int(m.group(2))
        if not 1 <= month <= 12:
            return m.group(0)
        return f"{int(m.group(3))} {_MONTH_NAMES[month - 1]}"
    return _ISO_DATE.sub(one, text)


def humanize(sentence: str) -> str:
    """Replace stock call-centre phrasing with plain spoken English (Latin script only)."""
    sentence = speak_dates(sentence)
    if re.search(r"[\u0900-\u097f]", sentence):
        return sentence.strip()
    t = sentence
    for pat, rep in _STIFF:
        t = pat.sub(rep, t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,")
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t or sentence.strip()
