"""The truth guard: the last check between the language model and the customer.

A department agent's playbook runs the tools and hands the model a list of verified facts. The model only *phrases* them.
Before any sentence is spoken (or emailed) it is checked here against those facts and the retrieved knowledge:

  * a specific the facts do not contain is dropped: a date, a rupee amount, an ID, a duration ("2 days");
  * "it's done" (refunded, cancelled, unlocked...) is dropped unless a tool call VERIFIED it;
  * social-proof inventions ("already reported by other customers", "the team is fixing it") are dropped unless true.

Everything is plain rules, so it costs microseconds, behaves the same with any model, and is easy to audit. The benchmark in
benchmarks/ measures how often the raw model breaks these rules and how many of those never reach the customer.
"""

import re

# ── social-proof inventions ──────────────────────────────────────────────────
UNVERIFIED_CLAIM = re.compile(
    r"already (?:been )?(?:reported|known|logged|flagged)|reported by (?:others|other|some)|other (?:customers|people|users)|"
    r"others have|group log|actively working on|team is working on (?:a|the) fix|added your case|"
    r"pehle se (?:report|pata)|dusre (?:customers|logon)", re.I)

# ── specifics ────────────────────────────────────────────────────────────────
_MONTHS = r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?"
_DATE = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)\b|\b(\d{{1,2}})\s+(?:{_MONTHS})\b|\b(?:{_MONTHS})\s+(\d{{1,2}})\b", re.I)
_AMOUNT = re.compile(r"(?:₹|rs\.?\s?|inr\s?|rupees\s+)\s*(\d[\d,]*)|(\d[\d,]*)\s*(?:rupees|rs\b)", re.I)
_ID = re.compile(r"\b(ORD|RFD|TXN|SHP|PH|CUS)[\s\-]*(\d{3,6})\b", re.I)
_DURATION = re.compile(r"\b(\d{1,3})(?:\s*(?:to|-|or)\s*(\d{1,3}))?\s*(?:working\s+|business\s+)?(?:days?|hours?|hrs?|minutes?|mins?|weeks?)\b", re.I)

# "it's done": a completed action the customer could rely on
_COMPLETION = re.compile(
    r"\b(?:i'?ve|i have|it'?s|it is|has been|have been|been|all)\b[^.!?]{0,40}\b(?:refunded|cancell?ed|unlocked|processed|reversed|credited)\b|"
    r"\b(?:refund|cancellation|unlock(?:ing)?)\b[^.!?]{0,30}\b(?:is|was|has been)\s+(?:done|complete|completed|processed|confirmed|successful)\b|"
    r"\b(?:is|was|are)\s+(?:now\s+)?(?:refunded|cancell?ed|unlocked|processed|reversed|credited)\b", re.I)
_VERIFIED_FACT = re.compile(r"verified|completed|status cancelled|already (?:cancelled|refunded)", re.I)


def _ints(text: str) -> set[int]:
    return {int(x.replace(",", "")) for x in re.findall(r"\d[\d,]*", text or "") if x.replace(",", "").isdigit() and len(x.replace(",", "")) <= 9}


def _ids(text: str) -> set[str]:
    return {f"{m.group(1).upper()}-{m.group(2)}" for m in _ID.finditer(text or "")}


def invented_date(sentence: str, evidence: str) -> bool:
    """A specific day ("by the 27th", "28 September") may only be said if the verified facts contain that day."""
    days = {int(x) for x in re.findall(r"\d+", evidence) if len(x) <= 4}
    for m in _DATE.finditer(sentence):
        if next(int(g) for g in m.groups() if g) not in days:
            return True
    return False


def invented_amount(sentence: str, evidence: str) -> bool:
    known = _ints(evidence)
    return any(int((m.group(1) or m.group(2)).replace(",", "") or 0) not in known for m in _AMOUNT.finditer(sentence))


def invented_id(sentence: str, evidence: str) -> bool:
    known = _ids(evidence)
    return any(i not in known for i in _ids(sentence))


def invented_duration(sentence: str, evidence: str) -> bool:
    known = _ints(evidence)
    for m in _DURATION.finditer(sentence):
        if any(int(g) not in known for g in m.groups() if g):
            return True
    return False


def premature_completion(sentence: str, facts: list[str]) -> bool:
    """Says an action is done although no tool call verified it."""
    return bool(_COMPLETION.search(sentence)) and not any(_VERIFIED_FACT.search(f) for f in facts)


def evidence_text(facts: list[str], knowledge: list[str] = (), guidance: list[str] = (), caller: str = "") -> str:
    """Everything a sentence may legitimately draw a specific from: verified facts, retrieved passages, team guidance, and
    what the caller themselves said (they may have mentioned an amount or an ID)."""
    return " ".join([*facts, *knowledge, *guidance, caller])


def violation(sentence: str, evidence: str, facts: list[str], *, allow_social: bool = False) -> str | None:
    """Why this sentence must not be said (None if it is fine)."""
    if not allow_social and UNVERIFIED_CLAIM.search(sentence):
        return "claim not backed by any verified fact"
    if premature_completion(sentence, facts):
        return "says an action is done, but no tool call verified it"
    if invented_date(sentence, evidence):
        return "date not in the verified facts"
    if invented_amount(sentence, evidence):
        return "amount not in the verified facts"
    if invented_id(sentence, evidence):
        return "ID not in the verified facts"
    if invented_duration(sentence, evidence):
        return "time frame not in the verified facts"
    return None
