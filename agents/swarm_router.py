"""FruitFlySwarmRouter — the routing stage inside the orchestration graph that
decides which specialist department handles a ticket (docs/swarm-router.md has
the full write-up; the flow diagram calls this "Mixture-of-Experts routing
(inspired by fruit fly)").

IMPORTANT — read before touching this file:

    This is a SOFTWARE ABSTRACTION inspired by properties of distributed
    biological information processing (parallel evaluation by specialised
    circuits, competition, inhibition of weaker candidates, sparse activation
    of a winner). It is NOT a simulation of a Drosophila brain, connectome, or
    biological neurons, and nothing here claims biological fidelity.

What it does, concretely:

    1. Every department (Technical, Billing, Account, Order, Other —
       backend/app/vocab.py's DEPARTMENTS, the actual specialist roster; see
       docs/claude.md for why "Logistics" is not one of them) gets a cheap,
       deterministic "activation score" in [0, 1] for this ticket.
    2. Scores are built from signals already available at this point in the
       graph (Jev's own keyword tables, live agent availability, past
       correction history) — no LLM calls, so this stays microseconds-cheap
       even though five candidates are scored (spec: never call the reasoning
       engine once per specialist just to route).
    3. Candidates are ranked; the winner is the department that actually gets
       activated (`execute_agent` only ever runs the winner — sparse
       activation, not "run all five").
    4. If the winner is too weak, or too close to the runner-up, the ticket is
       routed as AMBIGUOUS instead of guessed at (see `agents/nodes.py`'s
       `route_agent` / `agents/graph.py`'s `_route_after_swarm` — this reaches
       the existing human_gate for a GUIDE resume, not a new ticket state).

Deliberately NOT built here (see docs/swarm-router.md "What this is not"):
reinforcement learning, a trained/learned weight vector, a connectome, or any
per-request LLM call. Score weights are named prototype constants, not
biologically measured thresholds.
"""

import re
from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.database import engine
from app.domain import DEPARTMENT_KEYWORDS, INTENTS
from app.models import Agent, LearningSignal
from app.vocab import DEPARTMENTS

# ── prototype routing heuristics (tune freely; not biologically measured) ────
MIN_ACTIVATION = 0.20        # SWARM_MIN_ACTIVATION — below this, the winner itself is too weak to trust alone
DOMINANCE_MARGIN = 0.15      # SWARM_DOMINANCE_MARGIN — winner must lead the runner-up by at least this much
MAX_EXPERTS = 2              # SWARM_MAX_EXPERTS — experts kept "in play" (top_k) once ambiguity triggers consultation

# Weighted sum of cheap, explainable components (spec: "engineering heuristics
# inspired by the architectural concept", not a calibrated probability model).
# Must sum to 1.0.
W_INTENT = 0.50         # phrase-level match against Jev's own INTENTS table
W_DOMAIN = 0.20         # word-level match against DEPARTMENT_KEYWORDS (a second, coarser vocabulary)
W_AVAILABILITY = 0.15   # is that department's live agent already busy on something else?
W_HISTORY = 0.15        # how often has a human corrected AI routing away from this department?

_WORD = re.compile(r"[a-zA-Z]+")


class SwarmRoutingError(RuntimeError):
    """Every expert failed to produce an activation score — never silently
    fall back to an arbitrary department (spec: "do not invent a random
    fallback agent")."""


@dataclass
class ExpertActivation:
    agent: str
    activation_score: float
    intent_match: float
    domain_match: float
    availability_factor: float
    historical_signal: float
    matched_intent: str | None
    reason: str


@dataclass
class SwarmRoutingResult:
    ticket_id: str
    candidates: list[ExpertActivation]
    winner: str
    runner_up: str | None
    winner_score: float
    runner_up_score: float
    activation_gap: float
    ambiguous: bool
    routing_reason: str
    selected_experts: list[str]
    suppressed_experts: list[str]
    failed_experts: list[str] = field(default_factory=list)


# ── cheap, parallel-in-spirit scoring (no LLM calls — see module docstring) ──


def _phrase_hit(phrase: str, low_text: str) -> bool:
    # Mirrors app.judgment.jev._score_intents exactly (same table, same rule):
    # \b misbehaves next to non-ASCII scripts, so those phrases use containment.
    return (phrase in low_text) if not phrase.isascii() else bool(re.search(rf"\b{re.escape(phrase)}\b", low_text))


def _department_intent_score(dept: str, low_text: str) -> tuple[float, str | None]:
    """One department's own phrase score, reusing Jev's own INTENTS table (the
    same keyword competition Jev runs, aggregated for this one department
    instead of collapsed to Jev's single top intent). Each department scores
    itself independently — spec §46: one expert's own evaluation failing must
    never affect the others' scores."""
    best_score, best_intent = 0.0, None
    for intent_name, (d, phrases) in INTENTS.items():
        if d != dept:
            continue
        s = 0.0
        for p in phrases:
            if _phrase_hit(p, low_text):
                s += 1 + len(p.split()) * 1.2 if len(p.split()) > 1 else 1.0
        if s > best_score:
            best_score, best_intent = s, intent_name
    return best_score, best_intent


def _department_domain_score(dept: str, low_text: str) -> float:
    """One department's own word-level score against DEPARTMENT_KEYWORDS (a
    second, coarser vocabulary than INTENTS — independent of it and of every
    other department's score)."""
    words = set(_WORD.findall(low_text))
    keywords = DEPARTMENT_KEYWORDS.get(dept, [])
    return float(sum(1 for kw in keywords if kw in words or kw in low_text))


def _availability() -> dict[str, float]:
    """1.0 = idle and ready, 0.6 = already busy on another ticket. Cheap: one query, no per-expert round-trip."""
    with Session(engine) as s:
        rows = s.exec(select(Agent)).all()
    busy = {a.name for a in rows if a.status not in ("IDLE", "COMPLETED")}
    return {d: (0.6 if d in busy else 1.0) for d in DEPARTMENTS}


def _historical_signal(lookback: int = 50) -> dict[str, float]:
    """Reads real "Wrong agent routing" learning signals if any exist (written
    by agents/nodes.py's resume_correct/resume_override when a human reroutes
    away from the swarm's pick — see docs/swarm-router.md "Learning hook").
    No such signals yet (a fresh install, or before any correction has ever
    happened) -> every department gets the same neutral 0.5, never a fabricated
    number (spec: "do not fabricate a historical success rate")."""
    with Session(engine) as s:
        rows = s.exec(
            select(LearningSignal)
            .where(LearningSignal.signal_type == "Wrong agent routing")
            .order_by(LearningSignal.signal_id.desc())
            .limit(lookback)
        ).all()
    if not rows:
        return {d: 0.5 for d in DEPARTMENTS}
    wrong_counts: dict[str, int] = {d: 0 for d in DEPARTMENTS}
    for r in rows:
        if r.expected_action in wrong_counts:
            wrong_counts[r.expected_action] += 1
    total_wrong = sum(wrong_counts.values()) or 1
    # a department that is *never* the one corrected away from keeps the neutral 0.5;
    # one that is frequently corrected away from is discounted, never below 0.2.
    return {d: max(0.2, 0.5 - 0.5 * (wrong_counts[d] / total_wrong)) for d in DEPARTMENTS}


def _reason(dept: str, intent_match: float, domain_match: float, availability: float, matched_intent: str | None) -> str:
    bits = []
    if matched_intent and intent_match > 0:
        bits.append(f'intent matched "{matched_intent}"')
    elif domain_match > 0:
        bits.append(f"{dept.lower()}-related terms detected")
    else:
        bits.append("no strong keyword match")
    bits.append(f"{dept} desk {'available' if availability >= 1.0 else 'currently busy'}")
    return "; ".join(bits)


# ── the competition itself ───────────────────────────────────────────────────


def evaluate(ticket_id: str, *, text: str) -> SwarmRoutingResult:
    """Score every department candidate, let them compete, suppress the weak
    ones, and return a sparse (usually top-1) routing decision.

    Deterministic: identical `text` always produces identical scores (spec:
    "do not use random seeds or LLM temperature to determine routing" — there
    is no randomness or model call anywhere in this function).
    """
    low = text.lower()
    try:
        availability = _availability()
    except Exception:  # noqa: BLE001 — shared infrastructure hiccup: fall back to neutral, don't block routing on it
        availability = {d: 1.0 for d in DEPARTMENTS}
    try:
        history = _historical_signal()
    except Exception:  # noqa: BLE001
        history = {d: 0.5 for d in DEPARTMENTS}

    # Each department scores itself independently (spec §46: one expert's own
    # failure must not affect the others) — raw scores first, normalized once
    # every *surviving* expert has reported in.
    raw_intent: dict[str, float] = {}
    raw_domain: dict[str, float] = {}
    matched_intent: dict[str, str | None] = {}
    failed: list[str] = []
    fail_reason: dict[str, str] = {}
    for dept in DEPARTMENTS:
        try:
            raw_intent[dept], matched_intent[dept] = _department_intent_score(dept, low)
            raw_domain[dept] = _department_domain_score(dept, low)
        except Exception as e:  # noqa: BLE001
            failed.append(dept)
            fail_reason[dept] = f"expert evaluation failed: {type(e).__name__}: {e}"

    if len(failed) == len(DEPARTMENTS):
        raise SwarmRoutingError(f"all {len(DEPARTMENTS)} routing experts failed to evaluate ticket {ticket_id}")

    peak_intent = max(raw_intent.values()) if raw_intent else 0.0
    peak_domain = max(raw_domain.values()) if raw_domain else 0.0

    candidates: list[ExpertActivation] = []
    for dept in DEPARTMENTS:
        if dept in failed:
            candidates.append(ExpertActivation(
                agent=dept, activation_score=0.0, intent_match=0.0, domain_match=0.0, availability_factor=0.0,
                historical_signal=0.0, matched_intent=None, reason=fail_reason[dept],
            ))
            continue
        im = raw_intent[dept] / peak_intent if peak_intent > 0 else 0.0
        dm = raw_domain[dept] / peak_domain if peak_domain > 0 else 0.0
        av = availability.get(dept, 1.0)
        hs = history.get(dept, 0.5)
        score = max(0.0, min(1.0, W_INTENT * im + W_DOMAIN * dm + W_AVAILABILITY * av + W_HISTORY * hs))
        candidates.append(ExpertActivation(
            agent=dept, activation_score=round(score, 4), intent_match=round(im, 4), domain_match=round(dm, 4),
            availability_factor=av, historical_signal=hs, matched_intent=matched_intent.get(dept),
            reason=_reason(dept, im, dm, av, matched_intent.get(dept)),
        ))

    valid = [c for c in candidates if c.agent not in failed]

    ranked = sorted(valid, key=lambda c: c.activation_score, reverse=True)
    winner = ranked[0]
    runner_up = ranked[1] if len(ranked) > 1 else None
    gap = winner.activation_score - (runner_up.activation_score if runner_up else 0.0)
    ambiguous = winner.activation_score < MIN_ACTIVATION or gap < DOMINANCE_MARGIN

    selected = [c.agent for c in ranked[:MAX_EXPERTS]] if ambiguous else [winner.agent]
    suppressed = [c.agent for c in ranked if c.agent not in selected]

    reason = winner.reason if not ambiguous else (
        f"{winner.agent} leads narrowly over {runner_up.agent if runner_up else 'no runner-up'} "
        f"(gap {gap:.2f}) — needs a human to confirm which desk this belongs to"
    )

    return SwarmRoutingResult(
        ticket_id=ticket_id, candidates=candidates, winner=winner.agent,
        runner_up=runner_up.agent if runner_up else None, winner_score=winner.activation_score,
        runner_up_score=runner_up.activation_score if runner_up else 0.0, activation_gap=round(gap, 4),
        ambiguous=ambiguous, routing_reason=reason, selected_experts=selected, suppressed_experts=suppressed,
        failed_experts=failed,
    )


def to_dict(result: SwarmRoutingResult) -> dict:
    """Serializable form for AgentEvent.meta_json / the API — an operational
    explanation, never raw model chain-of-thought (spec §20, §47)."""
    return {
        "ticket_id": result.ticket_id,
        "candidates": [
            {
                "agent": c.agent, "activation_score": c.activation_score, "intent_match": c.intent_match,
                "domain_match": c.domain_match, "availability_factor": c.availability_factor,
                "historical_signal": c.historical_signal, "matched_intent": c.matched_intent, "reason": c.reason,
            }
            for c in result.candidates
        ],
        "winner": result.winner, "runner_up": result.runner_up, "winner_score": result.winner_score,
        "runner_up_score": result.runner_up_score, "activation_gap": result.activation_gap,
        "ambiguous": result.ambiguous, "routing_reason": result.routing_reason,
        "selected_experts": result.selected_experts, "suppressed_experts": result.suppressed_experts,
        "failed_experts": result.failed_experts,
    }
