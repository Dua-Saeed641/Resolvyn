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
_ORDER_STATUS = re.compile(r"\b(where|status|track|when|arriv|deliver|shipped|dispatch)", re.I)
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
        "confirm_cancel",
    }:
        return True
    if j.department not in TOOL_DEPARTMENTS:
        return False
    if ctx.entities.get("order_id") or st.get("order_id"):
        return True  # the caller gave us an order to look at
    if j.intent in TOOL_INTENTS and j.confidence >= 60:
        return True
    return j.intent == "Order Issue" and bool(_ORDER_ACTION.search(ctx.text) or _ORDER_STATUS.search(ctx.text))


async def decide(ctx: TurnContext) -> Decision:
    s = get_settings()
    st, j, ret = ctx.state, ctx.judgment, ctx.retrieval
    best = ret.best if ret else 0.0
    know = ret.top_hits(3) if ret else []

    if j.wants_human:
        return Decision("ESCALATED", "Caller asked for a person", int(best * 100), know,
                        escalate_reason="Caller asked to speak to a human")
    if j.sentiment == "Angry" and st.get("unresolved_turns", 0) >= 2:
        return Decision("ESCALATED", "Angry caller, unresolved after two exchanges", int(best * 100), know,
                        escalate_reason="Caller is angry and the issue is unresolved after two exchanges")

    # Human bug follow-up: already flagged, waiting for the manager's suggestion.
    if st.get("bug_flagged") and not st.get("bug_suggestion_given") and st.get("awaiting") == "bug_followup":
        if _is_tool_flow(ctx) and j.confidence >= 70:
            # The caller moved on to something else we can handle now; the bug stays open with the team.
            st["bug_flagged"], st["awaiting"] = False, None
        else:
            return Decision("FIRST_TIME_BUG", "Still waiting for the team's suggestion", int(best * 100), know)

    if not _has_problem(ctx) and not st.get("awaiting"):
        return Decision("INSTANT", "No problem stated yet", 60, know, small_talk=True)

    if _is_tool_flow(ctx):
        return Decision("ACTION", f"{j.department} desk with tools", max(j.confidence, int(best * 100)), know)

    # Knowledge path: consult both memories (memory-rulebook-detail.png).
    if ret and ret.bugs:
        top_bug = ret.bugs[0]
        if top_bug.score >= s.known_path_score:
            if "Human suggestion:" in top_bug.text:
                sugg = top_bug.text.split("Human suggestion:", 1)[1].strip()
                return Decision("INSTANT", "Seen before — a human already suggested the fix", int(top_bug.score * 100),
                                [top_bug] + know, bug_suggestion=sugg)
            return Decision("KNOWN_OPEN_BUG", "Same unknown problem already open with the team",
                            int(top_bug.score * 100), [top_bug] + know)

    if best >= s.known_path_score:
        return Decision("INSTANT", "Known path in the rulebook", int(best * 100), know)
    if best < s.first_time_bug_score:
        return Decision("FIRST_TIME_BUG", f"No precedent (best match {best:.2f})", int(best * 100), know)

    # Grey zone: does the retrieved text really answer *this* problem?
    query_text = ctx.text if len(ctx.text.split()) >= 6 else f"{st.get('subject', '')} {ctx.text}"
    ok, why = await jev.grounded(query_text, know)
    if ok:
        return Decision("INSTANT", "Knowledge addresses the problem", int(best * 100), know, note=why)
    return Decision("FIRST_TIME_BUG", "Retrieved knowledge does not cover this problem", int(best * 100), know, note=why)
