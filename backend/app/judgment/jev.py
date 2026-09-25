"""Jev — the fast Judgment model (docs/architecture.md §1 layer 3, §2.6).

Scores every caller utterance for intent/department, sentiment, urgency,
escalation intent and confidence, decides whether the caller is talking to the
agent at all, and writes the retrieval query ("JEV Written query" in
memory-rulebook-detail.png).

Two paths, merged:
  * rules  — microseconds, always available; lets the agent start speaking at once
  * model  — a tiny constrained-JSON call on the fast tier, used only when the
             rules are unsure. Failing or timing out never blocks the call.
"""

import asyncio
import re
from dataclasses import asdict, dataclass, field

from app.domain import (
    HUMAN_REQUEST,
    INTENTS,
    ON_TOPIC_CUES,
    SENTIMENT_ANGRY,
    SENTIMENT_NEGATIVE,
    SENTIMENT_POSITIVE,
    SIDE_TALK_CUES,
    URGENCY_HIGH,
)
from app.llm import LLMUnavailable, llm
from app.vocab import DEPARTMENTS

INTENT_NAMES = list(INTENTS)


@dataclass
class Judgment:
    intent: str = "General Query"
    department: str = "Other"
    sentiment: str = "Neutral"
    urgency: str = "Low"
    priority: str = "MEDIUM"
    confidence: int = 40  # 0-100
    wants_human: bool = False
    yes: bool = False
    no: bool = False
    done: bool = False
    query: str = ""
    source: str = "rules"
    carried: bool = False  # intent carried over from earlier in the call
    extras: dict = field(default_factory=dict)

    def public(self) -> dict:
        d = asdict(self)
        d.pop("extras", None)
        return d


# ── dialogue acts ────────────────────────────────────────────────────────────

_YES = re.compile(
    r"\b(yes|yeah|yep|yup|sure|ok(?:ay)?|go ahead|please do|do it|do that|correct|right|exactly|absolutely|"
    r"definitely|that's right|sounds good|please|haan|han|ji haan|kar do|theek hai|bilkul)\b", re.I)
_NO = re.compile(r"\b(no|nope|nah|don't|do not|not now|never mind|nevermind|leave it|cancel that|nahi|nahin|mat)\b", re.I)
_DONE = re.compile(
    r"\b(that'?s (?:all|it|everything)|nothing else|no,? that'?s it|that is all|i'?m good|all good|"
    r"bye|goodbye|thank(?:s| you)(?: so much| a lot)?|thanks a lot|you'?ve been (?:helpful|great)|"
    r"shukriya|dhanyavaad|dhanyavad|dhanyawad|bas itna(?: hi)?|bas yehi|bas ho gaya|that'?s helpful|that helps|great,? thanks)\b", re.I)
# "Are you a real person or a bot?" asks what Riya is; it does not ask for a person to take over.
IDENTITY_QUESTION = re.compile(
    r"\b(?:are|r) (?:you|u) (?:a |an )?(?:real |actual |live )?(?:person|human|bot|robot|ai|machine|computer|recording)|"
    r"(?:am i|is this) (?:talking|speaking) (?:to|with) (?:a |an )?(?:real |actual )?(?:person|human|bot|robot|ai|machine)|"
    r"(?:real|actual) (?:person|human) or (?:a )?(?:bot|robot|ai|machine)|kya (?:aap|tum) (?:robot|bot|insaan|real)", re.I)
PERSONAL_ORDER = re.compile(r"\b(i ordered|i placed|placed an order|my order|my parcel|my package|maine order|ordered something)\b")
_QUESTION = re.compile(r"\?|^\s*(what|when|where|why|how|can|could|will|would|do|does|is|are)\b", re.I)


_WORKED = re.compile(
    r"\b(it worked|that worked|works now|working now|it'?s working|is working now|fixed|solved|sorted|"
    r"resolved|problem is gone|all good now|light is (?:white|green|on))\b", re.I)
_FAILED = re.compile(
    r"\b(still (?:not|doesn'?t|isn'?t|blinking|flashing|same)|didn'?t work|did not work|doesn'?t work|no luck|"
    r"same (?:problem|issue|error)|not working|nothing happened|no change)\b", re.I)


def dialogue_act(text: str) -> tuple[bool, bool, bool]:
    t = text.strip()
    words = len(t.split())
    if _FAILED.search(t):
        return False, True, False
    if _WORKED.search(t):
        return True, False, bool(_DONE.search(t)) and words <= 14
    yes = bool(_YES.search(t))
    no = bool(_NO.search(t))
    done = bool(_DONE.search(t)) and words <= 14 and not _QUESTION.search(t)
    if yes and no:  # "no, don't" vs "yes please don't wait": first token wins
        first = re.search(r"\b(yes|yeah|yep|sure|ok|okay|haan|no|nope|nah|nahi)\b", t, re.I)
        yes = bool(first and first.group(1).lower() in ("yes", "yeah", "yep", "sure", "ok", "okay", "haan"))
        no = not yes
    return yes, no, done


# ── rule-based judgment ──────────────────────────────────────────────────────


def _score_intents(low: str) -> list[tuple[str, float]]:
    scores = []
    for name, (_dept, phrases) in INTENTS.items():
        s = 0.0
        for p in phrases:
            # \b misbehaves next to Devanagari vowel signs, so non-ASCII phrases use plain containment
            hit = (p in low) if not p.isascii() else re.search(rf"\b{re.escape(p)}\b", low)
            if hit:
                s += 1 + len(p.split()) * 1.2 if len(p.split()) > 1 else 1.0
        scores.append((name, s))
    scores.sort(key=lambda kv: kv[1], reverse=True)
    return scores


def _sentiment(low: str, prior: str | None) -> str:
    if any(w in low for w in SENTIMENT_ANGRY) or low.count("!") >= 3:
        return "Angry"
    neg = sum(w in low for w in SENTIMENT_NEGATIVE)
    if neg >= 2:
        return "Angry" if prior == "Frustrated" else "Frustrated"
    if neg == 1:
        return "Frustrated"
    if any(w in low for w in SENTIMENT_POSITIVE):
        return "Positive"
    return "Neutral" if prior in (None, "Positive") else prior


def rules_judge(text: str, prior: Judgment | None = None, *, plan: str | None = None) -> Judgment:
    low = text.lower()
    scores = _score_intents(low)
    top, top_s = scores[0]
    second_s = scores[1][1]
    j = Judgment(source="rules")

    if top_s > 0:
        j.intent = top
        j.department = INTENTS[top][0]
        margin = (top_s - second_s) / top_s if top_s else 0
        j.confidence = int(min(95, 52 + 9 * min(top_s, 4) + 14 * margin))
        # a generic single-word match ("order", "app") is weaker evidence
        if top_s <= 1.0:
            j.confidence = min(j.confidence, 66)
    elif prior and prior.intent != "General Query":
        j.intent, j.department, j.carried = prior.intent, prior.department, True
        j.confidence = max(60, prior.confidence - 4)
    else:
        j.intent, j.department, j.confidence = "General Query", "Other", 32

    # "I ordered something and wanted to check on it": an order question, but only when nothing stronger matched
    if j.intent == "General Query" and PERSONAL_ORDER.search(low):
        j.intent, j.department, j.confidence = "Order Issue", "Order", 62

    # A follow-up ("my name is Aarav, order ORD-83921") must not flip the department
    # because a weak keyword matched: carry the earlier intent unless evidence is strong.
    if prior and prior.intent != "General Query" and not j.carried and top != prior.intent:
        new_question = top_s >= 1.0 and bool(_QUESTION.search(text)) and len(text.split()) >= 5
        if (top_s < 3.0 or j.confidence < 78) and not new_question:
            j.intent, j.department, j.carried = prior.intent, prior.department, True
            j.confidence = max(60, prior.confidence - 4)

    j.sentiment = _sentiment(low, prior.sentiment if prior else None)
    j.wants_human = any(p in low for p in HUMAN_REQUEST) and not IDENTITY_QUESTION.search(low)
    j.urgency = "High" if any(w in low for w in URGENCY_HIGH) else ("Medium" if j.sentiment in ("Frustrated", "Angry") else "Low")
    j.yes, j.no, j.done = dialogue_act(text)

    j.priority = "MEDIUM"
    if j.sentiment == "Angry" and j.urgency == "High":
        j.priority = "CRITICAL"
    elif j.sentiment == "Angry" or j.urgency == "High" or (plan == "Premium" and j.department == "Billing"):
        j.priority = "HIGH"
    elif j.department == "Other":
        j.priority = "LOW"
    return j


# ── retrieval query ("JEV written query") ────────────────────────────────────


def write_query(text: str, j: Judgment, *, subject: str | None = None) -> str:
    """Compact query for the memory: the intent's vocabulary plus what the caller said.

    Short follow-ups ("yes please") carry no signal on their own, so the ticket's
    subject (the caller's original problem) is folded in.
    """
    words = re.findall(r"[A-Za-z0-9\-']+", text)
    body = " ".join(words)
    if len(words) < 6 and subject:
        body = f"{subject} {body}"
    return f"{j.intent} {body}".strip()


# ── model-assisted judgment ──────────────────────────────────────────────────

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": INTENT_NAMES},
        "sentiment": {"type": "string", "enum": ["Positive", "Neutral", "Frustrated", "Angry"]},
        "urgency": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "wants_human": {"type": "boolean"},
        "confidence": {"type": "integer"},
    },
    "required": ["intent", "sentiment", "urgency", "wants_human", "confidence"],
}

_JUDGE_SYSTEM = (
    "You are Jev, a fast judgment model for a customer-support phone line. Classify the caller's latest "
    "message. intents: " + ", ".join(INTENT_NAMES) + ". Billing = payments/refunds/invoices; Account = "
    "login/password/profile; Order = delivery/returns/cancel; Technical = product or app faults. "
    "confidence is 0-100 for how sure you are of the intent. Answer with JSON only."
)


async def refine_with_model(text: str, j: Judgment, history: list[dict]) -> Judgment:
    """Ask the fast tier to settle an unsure judgment. Never raises."""
    if not llm.ready("fast"):
        return j
    recent = "\n".join(f"{m['role']}: {m['content']}" for m in history[-4:])
    try:
        out = await asyncio.wait_for(
            llm.complete_json(
                [
                    {"role": "system", "content": _JUDGE_SYSTEM},
                    {"role": "user", "content": f"Recent conversation:\n{recent}\n\nLatest caller message: {text}"},
                ],
                _JUDGE_SCHEMA,
                tier="fast", max_tokens=70, temperature=0.0,
            ),
            timeout=3.5,
        )
    except (asyncio.TimeoutError, LLMUnavailable, Exception):  # noqa: BLE001
        return j
    intent = out.get("intent")
    if intent in INTENTS:
        j.intent, j.department = intent, INTENTS[intent][0]
        j.carried = False
    if out.get("sentiment") in ("Positive", "Neutral", "Frustrated", "Angry"):
        j.sentiment = out["sentiment"]
    if out.get("urgency") in ("Low", "Medium", "High"):
        j.urgency = out["urgency"]
    j.wants_human = j.wants_human or bool(out.get("wants_human"))
    try:
        j.confidence = max(35, min(97, int(out.get("confidence", j.confidence))))
    except (TypeError, ValueError):
        pass
    j.source = "rules+model"
    return j


def is_unsure(text: str, j: Judgment) -> bool:
    return j.confidence < 72 and len(text.split()) >= 4 and not j.carried


async def judge(text: str, *, prior: Judgment | None, history: list[dict], plan: str | None = None) -> Judgment:
    j = rules_judge(text, prior, plan=plan)
    if is_unsure(text, j):
        j = await refine_with_model(text, j, history)
    assert j.department in DEPARTMENTS
    return j


# ── is the caller talking to the agent? ──────────────────────────────────────

_VOCATIVE = re.compile(r"^\s*(?:hey\s+|arre\s+|oye\s+)?(mom|mum|mummy|maa|dad|papa|bhai|bhaiya|didi|beta|sis|bro|honey|babe)\b", re.I)


def addressee(text: str, *, expecting_answer: bool) -> tuple[str, str]:
    """Return ("agent" | "other" | "unsure", reason).

    The intelligent classifier from docs/architecture.md §2.1: is the person on
    the call really talking to the agent, or to someone else? Fast rules decide
    the clear cases; ambiguous ones are left to the language model, which can
    answer [SIDE_TALK] with the whole conversation in view.
    """
    low = text.lower().strip()
    if not low:
        return "other", "empty"
    side = [c for c in SIDE_TALK_CUES if c in low]
    topic = [c for c in ON_TOPIC_CUES if re.search(rf"\b{re.escape(c)}\b", low)]
    vocative = bool(_VOCATIVE.match(low))
    mentions_other = bool(re.search(r"\b(?:talking|speaking) to (?:my|the|him|her|someone)\b", low))

    if vocative and not re.search(r"\b(order|refund|payment|account|ticket)\b", low):
        return "other", "addresses a family member"
    if mentions_other and "not you" in low or "wasn't talking to you" in low or "not talking to you" in low:
        return "other", "explicitly not talking to the agent"
    if side and not topic:
        return "other", f"side-talk cue: {side[0]!r}"
    if side and topic and len(side) >= 2 and len(topic) == 1 and topic[0] in ("yes", "no", "ok", "okay", "please"):
        return "other", "mostly side-talk"
    if topic or expecting_answer:
        return "agent", "on-topic"
    if len(low.split()) <= 2:
        return "agent", "short reply"
    return "unsure", "no clear signal"


# ── grounding check for the ambiguous retrieval band ─────────────────────────

_GROUND_SCHEMA = {
    "type": "object",
    "properties": {"answers": {"type": "boolean"}},
    "required": ["answers"],
}
_CODE = re.compile(r"\b[A-Za-z]{1,3}[-_ ]?\d{2,4}\b")


async def grounded(query_text: str, hits: list) -> tuple[bool, str]:
    """Do the retrieved passages actually address this specific problem?

    Used only when the retrieval score sits between "no idea" and "confident".
    Falls back to a conservative rule when no model is running: an unfamiliar
    error code in the question that no retrieved passage mentions means the
    rulebook has no answer.
    """
    codes = {c.lower().replace(" ", "-") for c in _CODE.findall(query_text)}
    haystack = " ".join(h.text.lower() for h in hits)
    unseen_codes = [c for c in codes if c.replace("-", "") not in haystack.replace("-", "").replace(" ", "")]
    if not llm.ready("fast"):
        return (not unseen_codes), ("unseen error code " + unseen_codes[0]) if unseen_codes else "no model; score-based"
    passages = "\n".join(f"- {h.title}: {h.text[:420]}" for h in hits[:3])
    try:
        out = await asyncio.wait_for(
            llm.complete_json(
                [
                    {"role": "system", "content": (
                        "You check whether company documents help answer a customer's question. "
                        "answers=true if any passage contains information that answers it or gives the procedure to follow, "
                        "even if only in part. answers=false only if the passages are about something unrelated. "
                        "Reply with JSON only.")},
                    {"role": "user", "content": f"Customer problem: {query_text}\n\nPassages:\n{passages}"},
                ],
                _GROUND_SCHEMA, tier="fast", max_tokens=14, temperature=0.0,
            ),
            timeout=6.0,
        )
        ans = bool(out.get("answers"))
        if ans and unseen_codes:
            ans = False  # a specific error code nobody documented is never "covered"
        why = "model: passages do not address this problem" if not ans else "model: passages address this problem"
        return ans, why + (f"; unseen code {unseen_codes[0]}" if unseen_codes else "")
    except Exception:  # noqa: BLE001
        return (not unseen_codes), "grounding check unavailable"
