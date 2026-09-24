"""Order Agent — orders, shipping, tracking, cancellations, returns
(docs/architecture.md §1 layer 5: "Order — shipping / tracking")."""

import re

from app.agents.base_agent import BaseAgent, Plan, TurnContext, money
from app.services import ticket_service as tickets


class OrderAgent(BaseAgent):
    name = "Order"
    persona = "You are on the orders desk: upbeat and practical about deliveries."

    async def plan(self, ctx: TurnContext) -> Plan:
        st, j = ctx.state, ctx.judgment
        wants_cancel = bool(re.search(r"\bcancel", ctx.text, re.I)) or st.get("intent_cancel")
        if wants_cancel:
            st["intent_cancel"] = True

        if st.get("awaiting") == "confirm_cancel" and st.get("order_id"):
            if j.yes and not j.no:
                return await self._cancel(ctx)
            if j.no:
                st["awaiting"] = None
                st["intent_cancel"] = False
                return Plan(
                    goal="They decided not to cancel. Say okay, the order stays as it is, and ask if there's anything else.",
                    fallback="Alright, I'll leave the order exactly as it is. Anything else I can help with?",
                    agent_state="COMPLETED", operation="Waiting for caller",
                )

        order_id = st.get("order_id")
        if not order_id:
            st["awaiting"] = "order_id"
            return Plan(
                goal="Ask for the order ID so you can check it. Order IDs start with ORD.",
                fallback="Sure, let me check. Could you give me your order ID? It starts with O R D.",
                status="ACTIVE", agent_state="ANALYZING", operation="Collecting order details",
            )

        ok, order = await self.tool(ctx, "get_order", order_id=order_id)
        if not ok:
            return self._down(ctx, "the order service")
        if not order:
            st["order_id"], st["awaiting"] = None, "order_id"
            st["order_misses"] = st.get("order_misses", 0) + 1
            if st["order_misses"] >= 2:
                return Plan(goal="You couldn't find that order twice. Say you're bringing in a teammate.",
                            fallback="I'm still not finding that order, so I'm bringing in a teammate to check.",
                            escalate="Order ID could not be found twice", agent_state="WAITING", operation="Escalating")
            return Plan(
                goal=f"No order found with ID {order_id}. Ask them to read it again slowly.",
                fallback="Hmm, I can't find that one. Could you read the order ID again, slowly?",
                facts=[f"No order found with ID {order_id}"], agent_state="ANALYZING", operation="Order not found",
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
                goal="That order isn't on this caller's account. Say it isn't showing under their account and ask them to double-check the ID.",
                fallback="That order isn't showing under your account. Could you double check the ID?",
                facts=["The order does not belong to the verified caller"], agent_state="ANALYZING", operation="Order/account mismatch",
            )

        facts = [f"Order {order_id}: {order['item']}, {money(order['amount'])}, placed {order['placed']}, status {order['status']}"]
        shipment = None
        if order.get("shipment_id"):
            ok, shipment = await self.tool(ctx, "get_shipment", shipment_id=order["shipment_id"])
            if ok and shipment:
                facts.append(f"Shipment {shipment['shipment_id']} with {shipment['carrier']}: {shipment['status']}, at {shipment['location']}, expected {shipment['eta']}")
                if shipment.get("delayed"):
                    facts.append(f"The shipment is delayed: {shipment.get('delay_reason', 'carrier delay')}")

        if wants_cancel:
            if order["status"] in ("Processing", "Confirmed"):
                st["awaiting"] = "confirm_cancel"
                return Plan(
                    goal="The order hasn't shipped, so it can still be cancelled. Ask if they're sure they want to cancel it; mention the refund goes back in 3 to 5 working days.",
                    fallback="That order hasn't shipped yet, so I can cancel it. Are you sure you'd like me to? The refund would take 3 to 5 working days.",
                    facts=facts, status="ACTIVE", path="ACTION", agent_state="ACTING", operation="Awaiting cancellation confirmation",
                )
            return Plan(
                goal=f"The order is already {order['status'].lower()}, so it can't be cancelled. Explain kindly and offer a return after delivery (7-day policy).",
                fallback=f"That order is already {order['status'].lower()}, so I can't cancel it. Once it reaches you, you can return it within 7 days.",
                facts=facts, status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="Cancellation not possible",
            )

        if j.intent == "Order Issue" and re.search(r"wrong|damag|broken|missing|defect|replace", ctx.text, re.I):
            return Plan(
                goal="Apologise for the wrong or damaged item and say your team will arrange the pickup and replacement, with all the details passed on.",
                fallback="I'm so sorry about that. I'm passing this to my team right now to arrange the pickup and your replacement.",
                facts=facts, agent_state="WAITING", operation="Replacement needs team", escalate="Replacement / return pickup needs the orders team",
            )

        goal = "Tell the caller where their order is using the facts. If it is delayed, apologise once and give the new expected date. Keep it short."
        fb = f"Your {order['item']} is {order['status'].lower()}."
        if shipment:
            fb = f"Your {order['item']} is {shipment['status'].lower()} with {shipment['carrier']}, currently at {shipment['location']}, expected by {shipment['eta']}."
        return Plan(goal=goal, fallback=fb, facts=facts, status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="Order status shared",
                    resolve=False)

    async def _cancel(self, ctx: TurnContext) -> Plan:
        st = ctx.state
        ok, res = await self.tool(ctx, "cancel_order", order_id=st["order_id"])
        if not ok or not res.get("ok"):
            reason = (res or {}).get("reason", "the order service failed")
            return Plan(
                goal=f"You could not cancel the order: {reason}. Apologise and explain.",
                fallback=f"I couldn't cancel it: {reason}.", facts=[f"Cancellation failed: {reason}"],
                agent_state="ERROR", operation="Cancellation failed", escalate=f"Cancellation failed: {reason}",
            )
        tickets.update(ctx.ticket_id, status="VERIFYING")
        ok, order = await self.tool(ctx, "get_order", order_id=st["order_id"])
        if ok and order and order["status"] == "Cancelled":
            st["awaiting"] = "confirm_helped"
            st["intent_cancel"] = False
            tickets.add_event(ctx.ticket_id, self.name, "ACTION_VERIFIED", f"{order['order_id']} status re-read: Cancelled",
                              status="COMPLETED", public="Order cancelled")
            return Plan(
                goal="The order IS cancelled and verified (say it in the past tense: it has been cancelled). Tell them the refund returns in 3 to 5 working days. Ask if anything else.",
                fallback="Done, your order is cancelled and confirmed. The refund will reach you in 3 to 5 working days. Anything else?",
                facts=[f"Order {order['order_id']} cancelled and VERIFIED (status Cancelled)"], status="VERIFYING", path="ACTION",
                agent_state="VERIFYING", operation="Cancellation verified",
            )
        return self._down(ctx, "the order verification")

    def _down(self, ctx: TurnContext, what: str) -> Plan:
        ctx.state["awaiting"] = None
        return Plan(
            goal=f"{what} did not respond even after a retry. Apologise and say a teammate will finish this.",
            fallback="Sorry, my system isn't responding properly. I'm passing this to a teammate.",
            facts=[f"{what} failed twice"], agent_state="ERROR", operation=f"{what} unavailable", escalate=f"{what} unavailable after retry",
        )
