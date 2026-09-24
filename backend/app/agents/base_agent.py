"""Shared contract for the five department agents (docs/architecture.md §2.3).

An agent does not free-write: its playbook runs the tools, collects *verified
facts*, and returns a Plan. The language model only turns that plan into
natural speech, so the caller can never hear something the system has not
verified (docs/claude.md: never let the reply get ahead of a tool call).

Agent states are the fixed vocabulary from project.md §21.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.judgment.jev import Judgment
from app.memory.memory_engine import Retrieval
from app.tools import tool_service


@dataclass
class Plan:
    goal: str  # what to do this turn, in plain words for the language model
    fallback: str  # what to say if no language model is available
    facts: list[str] = field(default_factory=list)  # verified facts the reply may use
    status: str | None = None  # ticket status to set (docs/claude.md vocabulary)
    path: str | None = None  # resolution path (INSTANT | ACTION | FIRST_TIME_BUG | ESCALATED)
    agent_state: str = "COMPLETED"
    operation: str = ""
    filler: str | None = None  # kind of acknowledgement to say before the reply
    resolve: bool = False
    escalate: str | None = None  # reason, if a human must take this
    use_knowledge: bool = True  # include retrieved SOP passages in the prompt
    next_step: str | None = None  # one line for the team side


@dataclass
class TurnContext:
    session: Any  # services.sessions.CallSession
    ticket_id: str
    text: str
    entities: dict
    judgment: Judgment
    retrieval: Retrieval | None
    customer: dict | None
    state: dict  # session.state (mutable, survives across turns)
    language: str = "en"


class BaseAgent(ABC):
    name: str  # Technical | Billing | Account | Order | Other
    persona: str = ""  # one line about how this desk sounds

    async def tool(self, ctx: TurnContext, tool_name: str, **kw):
        return await tool_service.call(ctx.ticket_id, tool_name, self.name, **kw)

    async def identify(self, ctx: TurnContext, order: dict) -> bool:
        """Tie the caller to the account that owns the order.

        A name the caller gave must match the order's owner; otherwise the order
        is not used (we do not read out someone else's payments).
        """
        if ctx.customer:
            return True
        ok, cust = await self.tool(ctx, "get_customer", customer_id=order["customer_id"])
        if not ok or not cust:
            return True
        given = (ctx.state.get("name") or "").split()
        if given and given[0].lower() != cust["name"].split()[0].lower():
            ctx.state["order_id"], ctx.state["awaiting"] = None, "order_id"
            return False
        ctx.state["customer_id"] = cust["customer_id"]
        ctx.customer = cust
        ctx.session.customer = cust
        from app.services import ticket_service as tickets

        tickets.update(ctx.ticket_id, customer_id=cust["customer_id"], customer_name=cust["name"])
        return True

    @abstractmethod
    async def plan(self, ctx: TurnContext) -> Plan:
        """Run this agent's playbook for the current caller message."""

    async def resume(self, ctx: TurnContext, event: str, payload: dict) -> Plan:  # noqa: ARG002
        """Continue after an out-of-band event (human approval, human suggestion)."""
        return Plan(goal="Carry on helping the caller.", fallback="Okay, I'm still here with you.")


def money(amount: int | float) -> str:
    return f"₹{int(amount):,}"
