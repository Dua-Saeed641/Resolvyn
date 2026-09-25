"""The Resolvyn orchestration graph (spec §6, §49) — builds once, run many times.

    START → perception → judgment → context/memory → decision
      → [ESCALATED]        → handle_escalation ─┐
      → [FIRST_TIME_BUG]   → flag_first_time_bug ┤
      → [INSTANT | ACTION] → route_agent (FruitFlySwarmRouter, agents/swarm_router.py)
            → [confident]  → execute_agent → (retry | human_gate | verify)
            → [ambiguous]  → human_gate ─────┐
                                              │
    human_gate ── interrupt() ── pauses for GUIDE/APPROVE/CORRECT/OVERRIDE/TEACH
      resume → GUIDE   → route_agent (ambiguous routing: re-score with the human's clarification)
                        → execute_agent (any other GUIDE: retry with the human's context)
      resume → TEACH   → context/memory (re-evaluate with the new rule)
      resume → CORRECT → execute_agent (rerouted to a different department) | verify (same department)
      resume → APPROVE/OVERRIDE → verify
                                                             │
    verify → [ok] → generate_response → record_outcome → emit_learning_signal → END
           → [fail, retries left] → register_failure → execute_agent
           → [fail, no retries]  → generate_response → record_outcome → emit_learning_signal → END

See agents/README.md §3 for why each edge exists, docs/swarm-router.md for the routing stage.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from agents import nodes
from agents.state import ResolvynState


def _route_after_decision(state: ResolvynState) -> str:
    path = state["decision_path"]
    if path == "ESCALATED":
        return "handle_escalation"
    if path in ("FIRST_TIME_BUG", "KNOWN_OPEN_BUG"):
        return "flag_first_time_bug"
    return "route_agent"


def _route_after_execute(state: ResolvynState) -> str:
    plan = state.get("plan") or {}
    if plan.get("agent_state") == "ERROR" and state.get("retry_count", 0) < state.get("max_retries", 2):
        return "register_failure"
    return "check_human_gate"


def _route_after_gate_check(state: ResolvynState) -> str:
    return "human_gate" if state.get("human_gate_required") else "verify"


def _route_after_swarm(state: ResolvynState) -> str:
    # Ambiguous routing (agents/swarm_router.py) pauses for a human GUIDE
    # before any specialist is activated — never a silent guess between two
    # close candidates.
    return "human_gate" if state.get("swarm_ambiguous") else "execute_agent"


def _route_after_human_gate(state: ResolvynState) -> str:
    action = (state.get("human_action") or {}).get("action")
    if action == "GUIDE":
        # A GUIDE answering an ambiguous-routing gate re-runs the swarm with the
        # human's clarification folded in (agents/nodes.py's route_agent); any
        # other GUIDE (missing info mid-task) resumes the same specialist.
        return "route_agent" if state.get("human_gate_reason") == "ambiguous_routing" else "execute_agent"
    if action == "TEACH":
        return "retrieve_context"
    if action == "CORRECT":
        # A CORRECT that also rerouted the department hands off to the newly
        # assigned specialist instead of resolving on the correction text alone.
        return "execute_agent" if (state.get("human_action") or {}).get("rerouted") else "verify"
    if action in ("APPROVE", "OVERRIDE"):
        return "verify"
    return "record_outcome"  # unrecognised resume payload — still reach a terminal, never hang


def _route_after_verify(state: ResolvynState) -> str:
    if state.get("action_verified"):
        return "generate_response"
    human_action = state.get("human_action") or {}
    if human_action.get("action") == "APPROVE" and human_action.get("approved") is False:
        # A human REJECTED the action — a final decision, never a retry case.
        return "generate_response"
    if state.get("retry_count", 0) < state.get("max_retries", 2):
        return "register_failure"
    return "generate_response"  # retries exhausted — response/outcome must reflect the failure honestly


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    g = StateGraph(ResolvynState)

    g.add_node("perception", nodes.run_perception)
    g.add_node("judgment", nodes.run_judgment)
    g.add_node("retrieve_context", nodes.retrieve_context)
    g.add_node("decision", nodes.run_decision)
    g.add_node("handle_escalation", nodes.handle_escalation)
    g.add_node("flag_first_time_bug", nodes.flag_first_time_bug)
    g.add_node("route_agent", nodes.route_agent)
    g.add_node("execute_agent", nodes.execute_agent)
    g.add_node("register_failure", nodes.register_failure)
    g.add_node("check_human_gate", nodes.check_human_gate)
    g.add_node("human_gate", nodes.human_gate)
    g.add_node("verify", nodes.verify)
    g.add_node("generate_response", nodes.generate_response)
    g.add_node("record_outcome", nodes.record_outcome)
    g.add_node("emit_learning_signal", nodes.emit_learning_signal)

    g.add_edge(START, "perception")
    g.add_edge("perception", "judgment")
    g.add_edge("judgment", "retrieve_context")
    g.add_edge("retrieve_context", "decision")
    g.add_conditional_edges("decision", _route_after_decision,
                            {"handle_escalation": "handle_escalation", "flag_first_time_bug": "flag_first_time_bug",
                             "route_agent": "route_agent"})
    g.add_conditional_edges("route_agent", _route_after_swarm, {"human_gate": "human_gate", "execute_agent": "execute_agent"})
    g.add_conditional_edges("execute_agent", _route_after_execute,
                            {"register_failure": "register_failure", "check_human_gate": "check_human_gate"})
    g.add_edge("register_failure", "execute_agent")
    g.add_conditional_edges("check_human_gate", _route_after_gate_check, {"human_gate": "human_gate", "verify": "verify"})

    # ESCALATED / FIRST_TIME_BUG always require a human — straight to the gate.
    g.add_edge("handle_escalation", "human_gate")
    g.add_edge("flag_first_time_bug", "human_gate")

    g.add_conditional_edges("human_gate", _route_after_human_gate,
                            {"execute_agent": "execute_agent", "retrieve_context": "retrieve_context",
                             "route_agent": "route_agent", "verify": "verify", "record_outcome": "record_outcome"})
    g.add_conditional_edges("verify", _route_after_verify,
                            {"generate_response": "generate_response", "register_failure": "register_failure"})
    g.add_edge("generate_response", "record_outcome")
    g.add_edge("record_outcome", "emit_learning_signal")
    g.add_edge("emit_learning_signal", END)

    return g.compile(checkpointer=checkpointer)
