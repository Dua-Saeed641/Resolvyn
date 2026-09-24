"""Billing Agent — payments, refunds, invoices (docs/architecture.md §1 layer 5).

Hero flow (project.md §4, §47): duplicate charge → verify → policy → propose
refund → human approval gate → execute → verify → tell the caller.
"""

from app.agents.base_agent import BaseAgent, Plan, TurnContext, money
from app.config import get_settings
from app.database import engine
from app.models import PendingAction
from app.services import ticket_service as tickets
from app.utils import jdump, jload
from sqlmodel import Session

REFUND_INTENTS = {"Duplicate Payment", "Refund Request"}


class BillingAgent(BaseAgent):
    name = "Billing"
    persona = "You are on the billing desk: calm, precise and reassuring about money."

    async def plan(self, ctx: TurnContext) -> Plan:
        st, j = ctx.state, ctx.judgment
        limit = get_settings().refund_auto_limit

        # ── answering a question we asked ────────────────────────────────────
        if st.get("awaiting") == "confirm_refund" and st.get("refund_candidate"):
            if j.yes and not j.no:
                return await self._request_refund(ctx, limit)
            if j.no:
                st["awaiting"] = None
                return Plan(
                    goal="The caller does not want the refund now. Say that's fine, nothing was changed, and ask if there's anything else.",
                    fallback="No problem at all, I haven't changed anything. Is there anything else I can help with?",
                    status="ACTIVE", agent_state="COMPLETED", operation="Waiting for caller",
                )
        if st.get("awaiting") == "approval":
            act = self._pending(st)
            return Plan(
                goal="The refund is with the team lead for approval and is NOT done yet. Reassure the caller, say you'll tell them the moment it's approved, and ask them to stay on the line.",
                fallback="It's with my team lead for a quick approval. I'll tell you the moment it's done, so please stay on the line.",
                facts=[f"Refund of {money(act['params']['amount'])} for {act['params']['order_id']} is waiting for human approval (not executed)"] if act else [],
                status="WAITING_FOR_HUMAN", agent_state="WAITING", operation="Awaiting human approval",
            )

        # ── need an order to look at ─────────────────────────────────────────
        order_id = st.get("order_id")
        if not order_id:
            st["awaiting"] = "order_id"
            who = "" if ctx.customer or st.get("name") else " and your name"
            return Plan(
                goal=f"Ask for the order ID{who} so you can look at the payments. Order IDs start with ORD.",
                fallback=f"Sure, I can look into that. Could you tell me your order ID{who}? It starts with O R D.",
                status="ACTIVE", agent_state="ANALYZING", operation="Collecting order details", filler="empathy" if j.sentiment in ("Frustrated", "Angry") else None,
            )

        # ── look the order up ────────────────────────────────────────────────
        ok, order = await self.tool(ctx, "get_order", order_id=order_id)
        if not ok:
            return self._service_down(ctx, "the order service")
        if not order:
            st["order_id"], st["awaiting"] = None, "order_id"
            st["order_misses"] = st.get("order_misses", 0) + 1
            if st["order_misses"] >= 2:
                return Plan(
                    goal="You couldn't find that order twice. Say you're bringing in a teammate to check it.",
                    fallback="I'm still not finding that order, so let me bring in a teammate to check it for you.",
                    escalate="Order ID could not be found twice", agent_state="WAITING", operation="Escalating",
                )
            return Plan(
                goal=f"You could not find an order with ID {order_id}. Ask them to read it out again, slowly.",
                fallback="Hmm, I can't find that one. Could you read the order ID out again for me, slowly?",
                facts=[f"No order found with ID {order_id}"], status="ACTIVE", agent_state="ANALYZING", operation="Order not found",
            )
        if not ctx.customer and not await self.identify(ctx, order):
            return Plan(
                goal="The name the caller gave doesn't match the account that owns that order. Politely say you can't find that order under their name, and ask them to double-check the order ID or their name.",
                fallback="Hmm, that order isn't showing under that name. Could you double check the order ID or the name for me?",
                facts=["The order does not belong to the name the caller gave"], agent_state="ANALYZING", operation="Order/name mismatch",
            )
        if ctx.customer and order["customer_id"] != ctx.customer["customer_id"]:
            st["order_id"], st["awaiting"] = None, "order_id"
            return Plan(
                goal="That order ID is not on this caller's account. Politely say it isn't showing under their account and ask them to double-check the ID.",
                fallback="That order isn't showing under your account. Could you double check the ID for me?",
                facts=["The order does not belong to the verified caller"], agent_state="ANALYZING", operation="Order/account mismatch",
            )

        ok, txns = await self.tool(ctx, "get_payment_transactions", order_id=order_id)
        if not ok:
            return self._service_down(ctx, "the payment service")
        facts = [f"Order {order_id}: {order['item']}, {money(order['amount'])}, status {order['status']}"]
        facts += [f"Transaction {t['transaction_id']}: {money(t['amount'])} {t['status']} on {t['method']} at {t['timestamp']}" for t in txns]

        # ── refund status question ───────────────────────────────────────────
        if j.intent == "Refund Status":
            ok, refunds = await self.tool(ctx, "refunds_for_order", order_id=order_id)
            if refunds:
                r = refunds[-1]
                facts.append(f"Refund {r['refund_id']} of {money(r['amount'])} has status {r['status']}")
                return Plan(
                    goal="Tell the caller the refund status from the facts and the usual timeline (3 to 5 working days after completion, UPI up to 5). Share the refund reference.",
                    fallback=f"Your refund {r['refund_id']} for {money(r['amount'])} shows as {r['status'].lower()}. It usually reaches you in 3 to 5 working days.",
                    facts=facts, status="ACTIVE", path="ACTION", agent_state="COMPLETED", operation="Refund status shared", resolve=r["status"] == "COMPLETED",
                )
            facts.append("There is no refund on file for this order")

        # ── duplicate charge / refund request ────────────────────────────────
        if j.intent in REFUND_INTENTS or st.get("intent") in REFUND_INTENTS:
            ok, policy = await self.tool(ctx, "check_refund_policy", order_id=order_id)
            if not ok:
                return self._service_down(ctx, "the refund policy service")
            if policy.get("eligible"):
                st["refund_candidate"] = {"order_id": order_id, "transaction_id": policy["transaction_id"], "amount": policy["amount"]}
                st["awaiting"] = "confirm_refund"
                facts.append(f"Duplicate confirmed: {policy['transaction_id']} is a second successful charge of {money(policy['amount'])} for the same order")
                facts.append(f"Policy check: eligible — {policy['policy']}")
                tickets.add_event(ctx.ticket_id, self.name, "ACTION_PROPOSED",
                                  f"Refund {money(policy['amount'])} of {policy['transaction_id']} proposed", status="WAITING")
                return Plan(
                    goal="You found the duplicate charge. Explain it in one sentence (charged twice, second one is the duplicate) and ask if they'd like you to refund the duplicate one.",
                    fallback=f"I can see you were charged {money(policy['amount'])} twice for {order_id}. Want me to refund the duplicate one?",
                    facts=facts, status="ACTIVE", path="ACTION", agent_state="ACTING", operation="Duplicate detected — awaiting caller's go-ahead",
                    next_step="Caller to confirm refund of the duplicate charge",
                )
            facts.append(f"Policy check: not eligible — {policy.get('reason')}")
            return Plan(
                goal="Explain honestly that you checked and there's no duplicate charge to refund (use the facts), then offer to escalate if they still think something is wrong.",
                fallback="I checked the payments and I can't see a duplicate charge on that order. Would you like me to get a teammate to look deeper?",
                facts=facts, status="ACTIVE", path="ACTION", agent_state="COMPLETED", operation="No refundable duplicate found",
            )

        # ── plain payment question ───────────────────────────────────────────
        return Plan(
            goal="Answer the caller's billing question using the facts and the knowledge passages. Keep it short.",
            fallback="Here's what I can see on that order. Is there anything specific you want me to check?",
            facts=facts, status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="Payment records shared",
        )

    # ── the refund request path ──────────────────────────────────────────────
    async def _request_refund(self, ctx: TurnContext, limit: int) -> Plan:
        st = ctx.state
        cand = st["refund_candidate"]
        amount = cand["amount"]
        if amount > limit:
            with Session(engine, expire_on_commit=False) as s:
                act = PendingAction(
                    ticket_id=ctx.ticket_id, action_type="refund",
                    summary=f"Refund {money(amount)} — duplicate charge on {cand['order_id']}",
                    params_json=jdump({**cand, "reason": "Duplicate payment detected"}),
                    risk="Medium", policy="Eligible",
                )
                s.add(act)
                s.commit()
            st["pending_action_id"], st["awaiting"] = act.action_id, "approval"
            tickets.add_event(
                ctx.ticket_id, self.name, "ACTION_PROPOSED",
                f"Human approval requested: {act.summary} (over the {money(limit)} auto-approval limit)",
                status="WAITING", meta={"action_id": act.action_id},
                public="Refund sent to our team for approval",
            )
            from app.services.realtime import hub
            hub.to_ops({"type": "approval_request", "action": tickets.pending_dict(act), "ticket_id": ctx.ticket_id})
            return Plan(
                goal="The caller agreed. Say you've sent the refund to your team lead for a quick approval, that nothing has been refunded yet, and you'll tell them the moment it's approved. Ask them to stay on the line. Do NOT mention any amount limit or threshold.",
                fallback=f"Done on my side. Because of the amount, my team lead has to approve the {money(amount)} refund, so nothing is refunded yet. Please stay on the line and I'll tell you the moment it's approved.",
                facts=[f"Refund of {money(amount)} submitted for human approval; NOT executed yet"],
                status="WAITING_FOR_HUMAN", path="ACTION", agent_state="WAITING", operation="Awaiting human approval",
                next_step="Manager to approve or reject the refund",
            )
        return await self._execute_refund(ctx, cand)

    async def _execute_refund(self, ctx: TurnContext, cand: dict) -> Plan:
        st = ctx.state
        ok, res = await self.tool(ctx, "issue_refund", order_id=cand["order_id"], transaction_id=cand["transaction_id"],
                                  amount=cand["amount"], for_ticket=ctx.ticket_id)
        tickets.add_event(ctx.ticket_id, self.name, "ACTION_EXECUTED", f"Refund submitted: {res.get('refund_id') if ok else 'failed'}",
                          status="COMPLETED" if ok else "FAILED", public="Refund submitted" if ok else None)
        if not ok or not res.get("ok"):
            return self._service_down(ctx, "the refund service")
        tickets.update(ctx.ticket_id, status="VERIFYING")
        ok, ver = await self.tool(ctx, "verify_refund", refund_id=res["refund_id"])
        if ok and ver.get("verified"):
            st["awaiting"] = "confirm_helped"
            st["refund_candidate"] = None
            tickets.add_event(ctx.ticket_id, self.name, "ACTION_VERIFIED",
                              f"{ver['refund_id']} verified with the refund service ({money(ver['amount'])}, {ver['status']})",
                              status="COMPLETED", public=f"Refund {ver['refund_id']} verified")
            return Plan(
                goal="The refund is done AND verified by the refund service. Tell the caller the refund reference, the amount, and that it reaches the original payment method in 3 to 5 working days. Then ask if there's anything else.",
                fallback=f"Your refund of {money(ver['amount'])} is done and confirmed. The reference is {ver['refund_id']}, and it'll reach you in 3 to 5 working days. Anything else I can help with?",
                facts=[f"Refund {ver['refund_id']} of {money(ver['amount'])} executed and VERIFIED (status {ver['status']}); {ver['eta']}"],
                status="VERIFYING", path="ACTION", agent_state="VERIFYING", operation="Refund verified", next_step="Confirm caller has nothing else",
            )
        return self._service_down(ctx, "the refund verification")

    async def resume(self, ctx: TurnContext, event: str, payload: dict) -> Plan:
        st = ctx.state
        if event == "approved":
            cand = st.get("refund_candidate") or payload.get("params")
            st["pending_action_id"] = None
            plan = await self._execute_refund(ctx, cand)
            plan.filler = "checking"
            return plan
        if event == "rejected":
            st["awaiting"], st["refund_candidate"] = None, None
            note = payload.get("reason") or "it didn't meet the approval criteria"
            return Plan(
                goal="The team lead did NOT approve the refund. Apologise sincerely, give the reason simply, say a teammate will follow up, and nothing was refunded.",
                fallback=f"I'm really sorry, my team lead couldn't approve that refund right now, because {note}. A teammate will follow up with you.",
                facts=[f"Refund was NOT approved by the team lead. Reason: {note}"],
                status="WAITING_FOR_HUMAN", agent_state="WAITING", operation="Refund rejected — team follow-up", escalate="Refund rejected by human",
            )
        return await super().resume(ctx, event, payload)

    # ── helpers ──────────────────────────────────────────────────────────────
    def _pending(self, st: dict) -> dict | None:
        aid = st.get("pending_action_id")
        if not aid:
            return None
        with Session(engine) as s:
            a = s.get(PendingAction, aid)
        return {"params": jload(a.params_json, {})} if a else None

    def _service_down(self, ctx: TurnContext, what: str) -> Plan:
        ctx.state["awaiting"] = None
        return Plan(
            goal=f"{what} did not respond even after a retry. Apologise, say you'll get a teammate to finish this so nothing goes wrong, and that you've passed on everything.",
            fallback="Sorry, my system isn't responding properly right now. I'm passing everything to a teammate so it gets sorted.",
            facts=[f"{what} failed twice"], status="WAITING_FOR_HUMAN", agent_state="ERROR", operation=f"{what} unavailable",
            escalate=f"{what} unavailable after retry",
        )


