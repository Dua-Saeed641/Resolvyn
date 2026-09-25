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
    must_say: list[str] = field(default_factory=list)  # words the spoken reply must contain (else the fallback line is added)
    verbatim: bool = False  # say the fallback line as written, without asking the model to rephrase it


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

    def adopt_customer(self, ctx: TurnContext, cust: dict) -> None:
        """The caller is now known: remember it for the session, the ticket and the persona."""
        from app.services import ticket_service as tickets

        ctx.state["customer_id"] = cust["customer_id"]
        ctx.customer = cust
        ctx.session.customer = cust
        tickets.update(ctx.ticket_id, customer_id=cust["customer_id"], customer_name=cust["name"])

    async def orders_of_caller(self, ctx: TurnContext, prefer=None) -> "Plan | None":
        """No order ID yet: if the caller is known (or gave email / phone digits) work from their own orders.

        Sets state["order_id"] and returns None when the order is clear; returns a Plan when something must be asked.
        `prefer(order) -> awaitable bool` picks the relevant order when there are several (e.g. the one with a duplicate charge).
        """
        st, ent = ctx.state, ctx.entities
        customer = ctx.customer
        email, last4 = ent.get("email") or st.get("email"), ent.get("phone_last4") or st.get("phone_last4")
        if not customer and (email or last4):
            ok, cust = await self.tool(ctx, "find_customer", email=email, phone_last4=last4)
            if ok and cust:
                self.adopt_customer(ctx, cust)
                customer = cust
            elif ok:
                st["email"] = st["phone_last4"] = None
                return Plan(
                    goal="Nothing matched that email or phone number. Say so kindly and ask for the order ID instead.",
                    fallback="Hmm, I couldn't find an account with that. Do you have the order ID handy?",
                    facts=["No customer matched the email / phone digits given"], agent_state="ANALYZING", operation="Customer not found",
                )
        if not customer:
            return None
        ok, orders = await self.tool(ctx, "orders_for_customer", customer_id=customer["customer_id"])
        orders = [o for o in (orders or []) if o["status"] != "Cancelled"] if ok else []
        if not orders:
            return Plan(
                goal="You checked their account and there are no orders on it. Say that and ask if the order was placed with another email or phone number.",
                fallback="I checked your account and I can't see any orders on it. Could it be under another email or phone number?",
                facts=["The caller's account has no orders"], agent_state="ANALYZING", operation="No orders on account",
            )
        if len(orders) > 1 and prefer:
            hits = [o for o in orders if await prefer(o)]
            if len(hits) == 1:
                orders = hits
        if len(orders) == 1:
            st["order_id"] = orders[0]["order_id"]
            from app.services import ticket_service as tickets

            tickets.update(ctx.ticket_id, order_id=st["order_id"])
            return None
        st["awaiting"], st["order_choices"] = "order_choice", orders[:5]
        listing = "; ".join(f"{o['item']} (order {o['order_id']}, placed {o['placed']}, {o['status']})" for o in orders[:5])
        return Plan(
            goal="They have more than one order. Name the items and ask which one they mean.",
            fallback="I can see a few orders on your account. Which one do you mean? " + ", ".join(o["item"] for o in orders[:5]) + "?",
            facts=[f"The caller's orders: {listing}"], agent_state="ANALYZING", operation="Choosing an order",
        )

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
