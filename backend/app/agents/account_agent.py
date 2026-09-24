"""Account Agent — login, lockouts, identity, profile (docs/architecture.md §1 layer 5).

Never acts on an unverified caller (Account Recovery Policy): identity must be
confirmed by registered email or the last four digits of the phone number.
"""

from app.agents.base_agent import BaseAgent, Plan, TurnContext
from app.services import ticket_service as tickets


class AccountAgent(BaseAgent):
    name = "Account"
    persona = "You are on the account desk: careful about security, friendly about it."

    async def plan(self, ctx: TurnContext) -> Plan:
        st, j, ent = ctx.state, ctx.judgment, ctx.entities

        if j.intent == "Profile Update":
            return Plan(
                goal="Profile and account-deletion changes need the account team. Say you're passing this to them with everything noted.",
                fallback="Changes like that need our account team to verify in writing, so I'm passing this to them right now with all the details.",
                status="WAITING_FOR_HUMAN", agent_state="WAITING", operation="Needs account team", escalate="Profile change needs manual verification",
            )

        # ── who is calling? ──────────────────────────────────────────────────
        customer = ctx.customer
        if not customer and (ent.get("email") or st.get("name")):
            ok, found = await self.tool(ctx, "find_customer", name=st.get("name"), email=ent.get("email") or st.get("email"))
            if ok and found:
                customer = found
                st["customer_id"] = found["customer_id"]
                tickets.update(ctx.ticket_id, customer_id=found["customer_id"], customer_name=found["name"])
        if not customer:
            st["awaiting"] = "identity"
            return Plan(
                goal="Ask for the caller's full name and the email address registered on the account.",
                fallback="Sure, I can help with that. Could you tell me your full name and the email on the account?",
                status="ACTIVE", agent_state="ANALYZING", operation="Identifying caller",
            )

        # ── verify identity (email or last four digits) ──────────────────────
        if not st.get("verified"):
            email = ent.get("email") or st.get("email")
            last4 = ent.get("phone_last4") or st.get("phone_last4")
            if email:
                st["email"] = email
            if last4:
                st["phone_last4"] = last4
            if not (email or last4):
                st["awaiting"] = "verification"
                return Plan(
                    goal="For security, ask the caller to confirm either the email registered on the account or the last four digits of the registered phone number.",
                    fallback="Just for security, could you confirm the last four digits of your registered phone number, or your email?",
                    status="ACTIVE", agent_state="ANALYZING", operation="Verifying identity",
                )
            ok, ver = await self.tool(ctx, "verify_identity", customer_id=customer["customer_id"], email=email, phone_last4=last4)
            if not ok:
                return self._down(ctx)
            if not ver["verified"]:
                st["verify_fails"] = st.get("verify_fails", 0) + 1
                st["email"] = st["phone_last4"] = None
                if st["verify_fails"] >= 2:
                    return Plan(
                        goal="Verification failed twice. Politely say you can't continue without verification and that you're bringing in a teammate.",
                        fallback="I'm sorry, I couldn't verify that, and for your security I can't go further, so I'm bringing in a teammate.",
                        facts=["Identity verification failed twice"], agent_state="WAITING", operation="Verification failed", escalate="Identity verification failed twice",
                    )
                return Plan(
                    goal="That detail didn't match our records. Say so gently and ask them to try the email or last four digits again.",
                    fallback="Hmm, that doesn't match what I have. Could you try the last four digits or the email again?",
                    facts=["Identity verification failed once"], agent_state="ANALYZING", operation="Verification mismatch",
                )
            st["verified"] = True
            tickets.add_event(ctx.ticket_id, self.name, "ACTION_VERIFIED", f"Identity verified via {ver['matched']}", status="COMPLETED",
                              public="Identity verified")

        # ── confirm-before-act ───────────────────────────────────────────────
        if st.get("awaiting") == "confirm_unlock":
            if j.yes and not j.no:
                return await self._unlock(ctx, customer)
            if j.no:
                st["awaiting"] = None
                return Plan(
                    goal="They don't want the unlock right now. Say that's fine and ask if there's anything else.",
                    fallback="No problem, I haven't changed anything. Anything else I can help with?",
                    agent_state="COMPLETED", operation="Waiting for caller",
                )

        if st.get("awaiting") == "confirm_reset":
            if j.yes and not j.no:
                ok, link = await self.tool(ctx, "send_reset_link", customer_id=customer["customer_id"])
                if ok and link.get("ok"):
                    st["awaiting"] = "confirm_helped"
                    tickets.add_event(ctx.ticket_id, self.name, "ACTION_VERIFIED", f"Reset link sent to {link['sent_to']}",
                                      status="COMPLETED", public="Password reset link sent")
                    return Plan(
                        goal="The reset link was sent. Tell the caller it went to their registered email (masked), valid for 30 minutes, and ask if there's anything else.",
                        fallback=f"Done, I've emailed a reset link to {link['sent_to']}. It's valid for 30 minutes. Anything else?",
                        facts=[f"Password reset link sent to {link['sent_to']}, expires in {link['expires_in_minutes']} minutes"],
                        status="VERIFYING", path="ACTION", agent_state="VERIFYING", operation="Reset link sent",
                    )
                return self._down(ctx)
            if j.no:
                st["awaiting"] = None
                return Plan(goal="They don't want a reset link. Say okay and ask what else you can do.",
                            fallback="Okay, no problem. What else can I help with?", agent_state="COMPLETED", operation="Waiting for caller")

        ok, acc = await self.tool(ctx, "get_account_status", customer_id=customer["customer_id"])
        if not ok:
            return self._down(ctx)
        facts = [f"Caller identity verified ({customer['name']})", f"Account status: {acc['status']}"]
        if acc["status"] == "LOCKED":
            st["awaiting"] = "confirm_unlock"
            facts.append(f"Reason: {acc.get('locked_reason', 'security lock')} ({acc.get('failed_logins', 0)} failed logins)")
            return Plan(
                goal="You found the account is locked after too many failed logins. Say that in one sentence and ask if they'd like you to unlock it and send a password reset link to their registered email.",
                fallback="I can see the account got locked after too many wrong password attempts. Shall I unlock it and email you a reset link?",
                facts=facts, status="ACTIVE", path="ACTION", agent_state="ACTING", operation="Account locked — awaiting caller's go-ahead",
            )
        if j.intent == "Account Access":
            st["awaiting"] = "confirm_reset"
            return Plan(
                goal="The account is active, so it's not locked. Ask if they'd like a password reset link sent to their registered email.",
                fallback="Your account isn't locked, so it may just be the password. Want me to send a reset link to your email?",
                facts=facts, status="ACTIVE", path="ACTION", agent_state="ACTING", operation="Offering password reset",
            )
        return Plan(
            goal="Answer the caller using the facts and knowledge, briefly.",
            fallback="Your account looks fine on my side. What exactly is happening when you try?",
            facts=facts, path="INSTANT", agent_state="COMPLETED", operation="Account checked",
        )

    async def _unlock(self, ctx: TurnContext, customer: dict) -> Plan:
        st = ctx.state
        ok, res = await self.tool(ctx, "unlock_account", customer_id=customer["customer_id"])
        if not ok or not res.get("ok"):
            return self._down(ctx)
        ok, link = await self.tool(ctx, "send_reset_link", customer_id=customer["customer_id"])
        tickets.update(ctx.ticket_id, status="VERIFYING")
        ok2, acc = await self.tool(ctx, "get_account_status", customer_id=customer["customer_id"])
        if ok2 and acc["status"] == "ACTIVE" and ok and link.get("ok"):
            st["awaiting"] = "confirm_helped"
            tickets.add_event(ctx.ticket_id, self.name, "ACTION_VERIFIED", "Account unlocked (re-read status: ACTIVE); reset link sent",
                              status="COMPLETED", public="Account unlocked and reset link sent")
            return Plan(
                goal="The account HAS BEEN unlocked and verified active, and a reset link HAS BEEN sent (past tense). Tell the caller it went to their registered email (masked) and expires in 30 minutes. Ask if there's anything else.",
                fallback=f"All done. Your account is unlocked and I've emailed a reset link to {link['sent_to']}. It's valid for 30 minutes. Anything else?",
                facts=["Account unlocked and VERIFIED ACTIVE", f"Password reset link sent to {link['sent_to']}, expires in {link['expires_in_minutes']} minutes"],
                status="VERIFYING", path="ACTION", agent_state="VERIFYING", operation="Account unlock verified",
            )
        return self._down(ctx)

    async def resume(self, ctx: TurnContext, event: str, payload: dict) -> Plan:
        return await super().resume(ctx, event, payload)

    def _down(self, ctx: TurnContext) -> Plan:
        ctx.state["awaiting"] = None
        return Plan(
            goal="The account system did not respond even after a retry. Apologise and say you're passing this to a teammate.",
            fallback="Sorry, the account system isn't responding right now. I'm passing this to a teammate so it gets done properly.",
            facts=["Account service failed twice"], agent_state="ERROR", operation="Account service unavailable",
            escalate="Account service unavailable after retry",
        )
