"""Order Agent — orders, shipping, tracking, cancellations, returns
(docs/architecture.md §1 layer 5: "Order — shipping / tracking")."""

import re

from app.agents.base_agent import BaseAgent, Plan, TurnContext, money
from app.services import ticket_service as tickets


class OrderAgent(BaseAgent):
    name = "Order"
    persona = "You are on the orders desk: upbeat and practical about deliveries."

    async def plan(self, ctx: TurnContext) -> Plan:
        p = await self._plan(ctx)
        p.use_knowledge = False
        return p

    async def _plan(self, ctx: TurnContext) -> Plan:
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

        # A caller we can already identify (or who gives an email / phone digits) needs no order ID: use their orders.
        if st.get("awaiting") == "order_choice" and st.get("order_choices"):
            picked = self._pick_order(ctx.text, st["order_choices"])
            if picked:
                st["order_id"], st["awaiting"], st["order_choices"] = picked["order_id"], None, None
        order_id = st.get("order_id")
        if not order_id:
            plan = await self.orders_of_caller(ctx)
            if plan:
                return plan
            order_id = st.get("order_id")
        if not order_id:
            st["awaiting"] = "order_id"
            return Plan(
                goal="Ask for the order ID so you can check it (it starts with ORD). Add that if they don't have it handy, their registered email or the last four digits of their phone number works too. Do not say anything about bugs or other customers.",
                fallback="Sure, let me check. Could you give me your order ID? It starts with O R D. If you don't have it, your registered email or the last four digits of your phone number also works.",
                status="ACTIVE", agent_state="ANALYZING", operation="Collecting order details",
            )

        ok, found = await self.tool(ctx, "lookup_order", reference=order_id)
        if not ok:
            return self._down(ctx, "the order service")
        order = found.get("order") if found.get("found") else None
        if found.get("match") == "ambiguous":
            st["order_id"], st["awaiting"] = None, "order_id"
            return Plan(
                goal="More than one order matches the digits they gave. Ask them to read out the complete order ID.",
                fallback="I'm finding a few orders with those digits. Could you read me the whole order ID?",
                facts=[f"{len(found['candidates'])} orders match the digits {order_id}"], agent_state="ANALYZING", operation="Order ID ambiguous",
            )
        if not order:
            st["order_id"], st["awaiting"] = None, "order_id"
            st["order_misses"] = st.get("order_misses", 0) + 1
            shown = order_id.replace("ORD-", "")
            if st["order_misses"] >= 2:
                return Plan(goal="You couldn't find that order twice. Say you're bringing in a teammate who will check it by hand.",
                            fallback="I'm still not finding that order, so I'm bringing in a teammate to check it for you.",
                            escalate="Order ID could not be found twice", agent_state="WAITING", operation="Escalating")
            return Plan(
                goal=f"Say you looked and there is no order {shown} in the system. Then ask them to check the ID in their confirmation message, or give their registered email so you can look it up.",
                fallback=f"Hmm, I searched but I can't find an order {shown}. Could you check the ID in your confirmation message? Or give me your registered email, or the last four digits of your phone.",
                facts=[f"No order matching {shown} exists in the order database"], agent_state="ANALYZING", operation="Order not found",
            )
        order_id = st["order_id"] = order["order_id"]  # the full ID, even if they only said the last digits
        tickets.update(ctx.ticket_id, order_id=order_id)
        if st.get("awaiting") in ("order_id", "order_choice"):
            st["awaiting"] = None
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

        if not shipment and order["status"] not in ("Delivered", "Cancelled"):
            facts.append("It has NOT shipped yet: there is no tracking and no delivery date to give (do not guess one)")

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

        goal = "Tell the caller the item and its status plainly, using only the facts (where it is, and the delivery date only if the facts give one). If it is delayed, apologise once and give the new expected date. Do not add reassurance the facts do not contain. Keep it short."
        fb = f"Your {order['item']} is {order['status'].lower()}."
        if not shipment and order["status"] not in ("Delivered", "Cancelled"):
            fb = f"Your {order['item']} is {order['status'].lower()} and hasn't shipped yet, so there's no tracking or delivery date just yet."
        if shipment:
            fb = f"Your {order['item']} is {shipment['status'].lower()} with {shipment['carrier']}, currently at {shipment['location']}, expected by {shipment['eta']}."
        key = [order["status"]] + ([shipment["status"], shipment["location"]] if shipment else [])
        return Plan(goal=goal, fallback=fb, facts=facts, status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="Order status shared",
                    resolve=False, must_say=key)

    @staticmethod
    def _pick_order(text: str, orders: list[dict]) -> dict | None:
        digits = re.sub(r"\D", "", text)
        t = text.lower()
        for o in orders:
            if len(digits) >= 3 and o["order_id"].endswith(digits):
                return o
            words = [w for w in re.findall(r"[a-z]{3,}", o["item"].lower()) if w not in ("pro", "the", "with")]
            if words and sum(w in t for w in words) >= max(1, len(words) // 2):
                return o
        return None

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
