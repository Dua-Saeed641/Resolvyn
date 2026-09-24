"""Technical Agent — product faults, app problems, diagnostics
(docs/architecture.md §1 layer 5). Knowledge-driven: the Solvable Rulebook and
the SOPs supply the fix; if there is no precedent the Decision Engine flags a
first-time bug before this agent is asked to plan."""

from app.agents.base_agent import BaseAgent, Plan, TurnContext


class TechnicalAgent(BaseAgent):
    name = "Technical"
    persona = "You are on the technical desk: patient, clear, and good at explaining steps one at a time."

    async def plan(self, ctx: TurnContext) -> Plan:
        st, j = ctx.state, ctx.judgment
        if st.get("awaiting") == "tech_feedback":
            if j.yes and not j.no:
                st["awaiting"] = "confirm_helped"
                return Plan(
                    goal="It worked! Say you're glad, and ask if there's anything else.",
                    fallback="Oh, that's great to hear! Is there anything else I can help you with?",
                    status="ACTIVE", path=st.get("tech_path", "INSTANT"), agent_state="COMPLETED", operation="Fix confirmed by caller", resolve=True,
                )
            if j.no:
                st["awaiting"] = None
                return Plan(
                    goal="The steps didn't fix it. Apologise briefly and say you're bringing in a specialist with everything already noted, so they won't need to repeat themselves.",
                    fallback="Sorry that didn't fix it. I'm bringing in a specialist and I've noted everything, so you won't have to repeat yourself.",
                    agent_state="WAITING", operation="Steps failed — specialist needed", escalate="Documented steps did not resolve the issue",
                )
        if st.get("tech_path") == "FIRST_TIME_BUG" and st.get("bug_suggestion"):
            # The caller said something other than yes/no while trying the team lead's fix.
            return Plan(
                goal="Answer what the caller just said in one short sentence, then gently bring them back to the team lead's suggestion and ask how it went.",
                fallback="Thanks for telling me. Have you had a chance to try the team lead's steps? What happened?",
                facts=[f"Team lead's suggestion (this overrides any general knowledge): {st['bug_suggestion']}"],
                status="ACTIVE", path="FIRST_TIME_BUG", agent_state="ACTING", operation="Waiting for the caller to try the suggestion",
                use_knowledge=False,
            )
        st["awaiting"] = "tech_feedback"
        st["tech_path"] = "INSTANT"
        return Plan(
            goal="Using the KNOWLEDGE, give only the first two steps in a natural spoken way, then ask them to try it and tell you what happens.",
            fallback="Let's try a quick fix. Please try restarting the device, and tell me if that changes anything.",
            status="ACTIVE", path="INSTANT", agent_state="COMPLETED", operation="Guided troubleshooting",
            next_step="Caller to try the steps and report back",
        )

    async def resume(self, ctx: TurnContext, event: str, payload: dict) -> Plan:
        if event == "suggestion":
            ctx.state["awaiting"] = "tech_feedback"
            ctx.state["tech_path"] = "FIRST_TIME_BUG"
            ctx.state["bug_suggestion"] = payload.get("suggestion", "")
            return Plan(
                goal="Your team lead just gave a suggestion for this new problem. Thank the caller for waiting, then explain the suggestion in your own words, one or two steps at a time, and ask them to try it.",
                fallback=f"Thanks for waiting. My team lead suggests this: {payload.get('suggestion', '')}. Could you try that and tell me what happens?",
                facts=[f"Team lead's suggestion: {payload.get('suggestion', '')}"], status="ACTIVE", path="FIRST_TIME_BUG",
                agent_state="ACTING", operation="Applying team-lead suggestion", filler="thanks",
                next_step="Caller to try the team lead's suggestion",
            )
        return await super().resume(ctx, event, payload)
