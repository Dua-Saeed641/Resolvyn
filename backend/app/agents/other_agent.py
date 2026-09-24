"""Other — catch-all department (docs/architecture.md §2.3: Tech, Billing,
Account, Order, *Other*). General questions, feedback and anything that does
not belong to a specialist desk."""

from app.agents.base_agent import BaseAgent, Plan, TurnContext


class OtherAgent(BaseAgent):
    name = "Other"
    persona = "You are on the general desk: friendly and helpful with any kind of question."

    async def plan(self, ctx: TurnContext) -> Plan:  # noqa: ARG002
        return Plan(
            goal="Answer the caller's question using the KNOWLEDGE, briefly and warmly. If the knowledge doesn't cover it, say so honestly.",
            fallback="Happy to help with that. Could you tell me a bit more about what you need?",
            status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="General query answered",
        )

    async def resume(self, ctx: TurnContext, event: str, payload: dict) -> Plan:
        if event == "suggestion":
            ctx.state["awaiting"] = "confirm_helped"
            return Plan(
                goal="Your team lead just gave an answer to this new question. Thank the caller for waiting and explain it in your own words, then ask if that helps.",
                fallback=f"Thanks for waiting. My team lead says: {payload.get('suggestion', '')}. Does that help?",
                facts=[f"Team lead's answer: {payload.get('suggestion', '')}"], status="ACTIVE", path="FIRST_TIME_BUG",
                agent_state="ACTING", operation="Applying team-lead suggestion", filler="thanks",
            )
        return await super().resume(ctx, event, payload)
