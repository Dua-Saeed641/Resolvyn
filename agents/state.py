"""ResolvynState — the typed state threaded through every graph node.

Kept to the minimum the graph itself needs (docs/architecture.md's own
Ticket/Judgment/Retrieval/Plan/PendingAction models already own most
domain data — this does not duplicate them, it just carries references
and the graph's own bookkeeping between nodes). See agents/README.md §2.

`agent_state` is a plain dict deliberately: it is passed straight through
as `TurnContext.state` (backend/app/agents/base_agent.py) so every
specialist agent's own conventions (`awaiting`, `order_id`,
`refund_candidate`, `pending_action_id`, ...) work unmodified — the graph
does not need to know each agent's internal vocabulary.
"""

import operator
from typing import Annotated, Any, TypedDict


class ResolvynState(TypedDict, total=False):
    # ── intake ───────────────────────────────────────────────────────────────
    ticket_id: str
    text: str
    channel: str
    language: str
    customer: dict | None

    # ── perception ───────────────────────────────────────────────────────────
    entities: dict

    # ── judgment (Jev) ───────────────────────────────────────────────────────
    judgment: dict  # serialized app.judgment.jev.Judgment

    # ── context / memory ─────────────────────────────────────────────────────
    query: str
    retrieval_best_common: float
    retrieval_best_bug: float
    is_first_time_bug: bool
    bug_id: int | None

    # ── decision engine ──────────────────────────────────────────────────────
    decision_path: str  # INSTANT | ACTION | FIRST_TIME_BUG | KNOWN_OPEN_BUG | ESCALATED
    decision_reason: str
    decision_confidence: int

    # ── routing ──────────────────────────────────────────────────────────────
    selected_agent: str
    routing_reason: str

    # ── specialist agent execution ───────────────────────────────────────────
    agent_state: dict  # TurnContext.state — the agent's own scratch space
    plan: dict | None  # serialized app.agents.base_agent.Plan
    pending_action_id: int | None

    # ── human gate ───────────────────────────────────────────────────────────
    human_gate_required: bool
    human_gate_reason: str | None
    human_action: dict | None  # last resume payload {"action": "APPROVE", ...}

    # ── verification ─────────────────────────────────────────────────────────
    action_executed: bool
    action_verified: bool

    # ── response / outcome ───────────────────────────────────────────────────
    customer_response: str | None
    outcome: str | None  # RESOLVED | FAILED | WAITING_FOR_HUMAN
    learning_signal_id: int | None  # most recent signal — for display, not idempotency (see below)
    outcome_signal_recorded: bool  # guards emit_learning_signal specifically (spec §30: no duplicate signals);
    # human-action signals (GUIDE/APPROVE/CORRECT/OVERRIDE/TEACH) are separate events and always recorded once
    # each, by construction — every resume_* node runs at most once per human action.

    # ── retry / failure ──────────────────────────────────────────────────────
    retry_count: int
    max_retries: int
    error: str | None

    # ── observability ────────────────────────────────────────────────────────
    trace: Annotated[list[str], operator.add]


def new_state(ticket_id: str, text: str, *, channel: str = "Ticket", language: str = "en") -> ResolvynState:
    return ResolvynState(
        ticket_id=ticket_id,
        text=text,
        channel=channel,
        language=language,
        customer=None,
        entities={},
        agent_state={},
        pending_action_id=None,
        bug_id=None,
        human_gate_required=False,
        human_gate_reason=None,
        human_action=None,
        action_executed=False,
        action_verified=False,
        customer_response=None,
        outcome=None,
        learning_signal_id=None,
        outcome_signal_recorded=False,
        retry_count=0,
        max_retries=2,
        error=None,
        trace=[],
    )


def public_state(state: dict[str, Any]) -> dict[str, Any]:
    """What the dashboard/API may see — domain state, not framework internals
    (spec §26, §50: "expose domain state, not framework state"; §51: never
    hidden reasoning/prompts). Drops `agent_state`, the agent playbook's own
    scratch space, which can carry raw customer-entered text.
    """
    return {k: v for k, v in state.items() if k != "agent_state"}
