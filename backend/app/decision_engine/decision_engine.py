"""Decision Engine — docs/architecture.md §1 layer 4 and §2.2.

Analyze → Plan → Evaluate → Choose action. Chooses one *resolution path* for the
current turn:

  INSTANT          the LLM + memory (SOPs / rulebook / past queries) can resolve it
  ACTION           a department agent runs tools (with a human gate where policy says so)
  FIRST_TIME_BUG   no precedent anywhere → flag to the manager and ask for a suggestion
  KNOWN_OPEN_BUG   the same unknown problem is already open with the team
  ESCALATED        a human must take it (asked for one, angry, unresolved, out of policy)

Decision criteria from the reference architecture: policy compliance, risk,
confidence threshold and human availability.
"""

import re
from dataclasses import dataclass, field

from app.agents.base_agent import TurnContext
from app.config import get_settings
from app.judgment import jev
from app.memory.vector_store import Hit

# Intents a department desk resolves with tools rather than with documents.
TOOL_INTENTS = {
    "Duplicate Payment", "Refund Request", "Refund Status", "Payment Failure",
    "Account Access", "Profile Update", "Shipping Delay",
}
_ORDER_ACTION = re.compile(r"cancel|wrong|damag|broken|missing|defect|replace|return|exchange", re.I)
_PERSONAL_ORDER = re.compile(r"\b(i ordered|i placed|placed an order|my order|my parcel|my package|mera order|apna order|maine order|order kiya|ordered)\b", re.I)
_ORDER_STATUS = re.compile(r"\b(where|status|track|when|arriv|deliver|shipped|dispatch|kahan|kab|puch|baare|pata|aaya|mila|pahunch)", re.I)
# Something is actually *broken* (a device, an app, an unfamiliar error): only these can be a "first-time bug".
# A question about an order, a payment or a login with nothing to look up yet is never a bug.
_DEFECT = re.compile(
    r"error|not working|doesn.?t work|stopped|crash|bug|glitch|blink|flash|light|code|fault|defect|dead|won.?t|"
    r"freez|hang|stuck|overheat|noise|smell|smoke|kharab|kaam nahi|chal nahi|band ho|काम नहीं|चल नहीं", re.I)
TOOL_DEPARTMENTS = {"Billing", "Account", "Order"}


@dataclass
class Decision:
    path: str
    reason: str
    confidence: int = 0
    knowledge: list[Hit] = field(default_factory=list)
    escalate_reason: str | None = None
    note: str | None = None  # e.g. the grounding-check explanation
    bug_suggestion: str | None = None
    small_talk: bool = False  # greeting / pleasantry: nothing to solve yet


def _has_problem(ctx: TurnContext) -> bool:
    j = ctx.judgment
    words = len(ctx.text.split())
    return (j.intent != "General Query" and j.confidence >= 50) or words >= 9 or bool(ctx.state.get("problem_stated"))


def _is_tool_flow(ctx: TurnContext) -> bool:
    st, j = ctx.state, ctx.judgment
    if st.get("awaiting") in {
        "order_id", "identity", "verification", "confirm_refund", "approval", "confirm_unlock", "confirm_reset",
        "confirm_cancel", "order_choice",
    }:
        if st.get("awaiting") == "approval" and j.department not in TOOL_DEPARTMENTS:
            return False  # e.g. a warranty or price question while the refund waits: answer it from the documents
        if st.get("awaiting", "").startswith("confirm_") and not (j.yes or j.no) and j.department not in TOOL_DEPARTMENTS:
            return False  # a different question while we wait for a yes/no: answer it, and keep the confirmation open
        return True
    if j.department not in TOOL_DEPARTMENTS:
        return False
    if ctx.entities.get("order_id") or st.get("order_id"):
        return True  # the caller gave us an order to look at
    if j.intent in TOOL_INTENTS and j.confidence >= 60:
        return True
    if j.department == "Order" and _PERSONAL_ORDER.search(ctx.text):
        return True  # "my order...": look up the caller's order, do not recite policy
    return j.intent == "Order Issue" and bool(_ORDER_ACTION.search(ctx.text) or _ORDER_STATUS.search(ctx.text))


# "P-77", "E-12", "B9": something a device displays. It is only familiar if it appears in something we know.
_ERROR_CODE = re.compile(r"\b(?!(?:ORD|RFD|TXN|SHP|PH|CUS|INR|GST|USB|IPX)\b)(?:[A-Za-z]{1,3}[-_]\d{1,4}|[A-Z]{1,2}\d{2,4})\b")


def unfamiliar_code(text: str, passages: list[str]) -> str | None:
    known = re.sub(r"[\s_-]", "", " ".join(passages).lower())
    for m in _ERROR_CODE.finditer(text):
        if re.sub(r"[\s_-]", "", m.group(0).lower()) not in known:
            return m.group(0)
    return None


RESUME = re.compile(r"\b(where were we|as i was saying|i'?m back|sorry about that|anyway,? (?:so|where)|haan toh|haan ji bataiye)\b", re.I)


def _nothing_concrete(ctx: TurnContext) -> bool:
    """No fault described and no recognisable request: never a first-time bug, ask what they need instead.

    Must agree with _has_problem's word-count signal (same >=9-word threshold): a long, specific
    description is never "nothing concrete" merely because Jev can't classify it into a known intent —
    detailed-but-unclassifiable is exactly what a first-time bug looks like, not small talk. Without this,
    a genuinely novel problem (necessarily "General Query"/low confidence, since nothing matched) would
    contradict the decision already made at _has_problem's call site (line ~113), which lets it through as
    a real problem on the same word-count basis.
    """
    j = ctx.judgment
    if len(ctx.text.split()) >= 9:
        return False
    return not _DEFECT.search(ctx.text) and (j.intent == "General Query" or j.confidence < 60)


def _desk_can_work_it(ctx: TurnContext) -> bool:
    """No document covers this, but a desk with tools can still act on it (look up the order, the payment, the account)."""
    return ctx.judgment.department in TOOL_DEPARTMENTS and not _DEFECT.search(ctx.text) and not ctx.state.get("bug_flagged")


async def decide(ctx: TurnContext) -> Decision:
    s = get_settings()
    st, j, ret = ctx.state, ctx.judgment, ctx.retrieval
    best = ret.best if ret else 0.0
    know = ret.top_hits(3) if ret else []

    if j.wants_human:
        return Decision("ESCALATED", "Caller asked for a person", int(best * 100), know,
                        escalate_reason="Caller asked to speak to a human")
    if j.sentiment == "Angry" and st.get("angry_streak", 0) >= 2:
        return Decision("ESCALATED", "Angry caller, unresolved after two exchanges", int(best * 100), know,
                        escalate_reason="Caller is angry and the issue is unresolved after two exchanges")

    # Human bug follow-up: already flagged, waiting for the manager's suggestion.
    if st.get("bug_flagged") and not st.get("bug_suggestion_given") and st.get("awaiting") == "bug_followup":
        if (_is_tool_flow(ctx) and j.confidence >= 70) or best >= s.known_path_score:
            # The caller moved on to something else we can handle now; the bug stays open with the team.
            st["bug_flagged"], st["awaiting"] = False, None
        else:
            return Decision("FIRST_TIME_BUG", "Still waiting for the team's suggestion", int(best * 100), know)

    if not _has_problem(ctx) and not st.get("awaiting"):
        return Decision("INSTANT", "No problem stated yet", 60, know, small_talk=True)
    if RESUME.search(ctx.text):
        return Decision("INSTANT", "Caller is back after talking to someone else", 60, know, small_talk=True)

    if _is_tool_flow(ctx):
        return Decision("ACTION", f"{j.department} desk with tools", max(j.confidence, int(best * 100)), know)

    # Knowledge path: consult both memories (memory-rulebook-detail.png).
    query_text = ctx.text if len(ctx.text.split()) >= 6 else f"{st.get('subject', '')} {ctx.text}"
    common_hits = sorted((ret.common + ret.graph) if ret else [], key=lambda h: h.score, reverse=True)[:3]
    if ret and ret.bugs and not _desk_can_work_it(ctx):
        top_bug = ret.bugs[0]
        # a taught fix is only reused for the SAME fault: if the caller quotes a code the taught case never mentioned, it is another problem
        same_fault = not unfamiliar_code(ctx.text, [top_bug.title + " " + top_bug.text])
        if top_bug.score >= s.known_path_score and same_fault:
            if "Human suggestion:" in top_bug.text:
                sugg = top_bug.text.split("Human suggestion:", 1)[1].strip()
                return Decision("INSTANT", "Seen before — a human already suggested the fix", int(top_bug.score * 100),
                                [top_bug] + know, bug_suggestion=sugg)
            # The same question is open with the team, but documents may have been added since (or may just be
            # relevant): if they really answer it, answer it. An unfamiliar error code is never "answered".
            if ret.best_common >= s.first_time_bug_score:
                ok, why = await jev.grounded(query_text, common_hits)
                if ok:
                    return Decision("INSTANT", "Documents answer it (an older open report matched too)",
                                    int(ret.best_common * 100), common_hits, note=why)
            return Decision("KNOWN_OPEN_BUG", "Same unknown problem already open with the team",
                            int(top_bug.score * 100), [top_bug] + know)

    code = unfamiliar_code(ctx.text, [h.title + " " + h.text for h in [*know, *(ret.bugs if ret else [])]])
    if code and not _desk_can_work_it(ctx):
        # keyword overlap ("kettle", "earbuds") must not make a new fault look known: a code seen nowhere in memory is a first-time bug
        return Decision("FIRST_TIME_BUG", f"Error code {code} appears nowhere in memory", int(best * 100), know)
    if best >= s.known_path_score:
        return Decision("INSTANT", "Known path in the rulebook", int(best * 100), know)
    if best < s.first_time_bug_score and _nothing_concrete(ctx):
        return Decision("INSTANT", "Nothing concrete to solve yet", int(best * 100), know, small_talk=True)
    if best < s.first_time_bug_score:
        if _desk_can_work_it(ctx):
            return Decision("ACTION", f"{j.department} desk with tools (nothing to look up in documents)", max(j.confidence, 55), know)
        return Decision("FIRST_TIME_BUG", f"No precedent (best match {best:.2f})", int(best * 100), know)

    # Grey zone: does the retrieved text really answer *this* problem?
    ok, why = await jev.grounded(query_text, know)
    if ok:
        return Decision("INSTANT", "Knowledge addresses the problem", int(best * 100), know, note=why)
    if _nothing_concrete(ctx):
        return Decision("INSTANT", "Nothing concrete to solve yet", int(best * 100), know, small_talk=True)
    if _desk_can_work_it(ctx):
        return Decision("ACTION", f"{j.department} desk with tools (documents do not cover it)", max(j.confidence, 55), know, note=why)
    return Decision("FIRST_TIME_BUG", "Retrieved knowledge does not cover this problem", int(best * 100), know, note=why)
