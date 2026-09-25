# The swarm router (bio-inspired mixture-of-experts routing)

`agents/swarm_router.py` is the routing stage inside the orchestration graph
(`agents/graph.py`) that decides which specialist department handles a
ticket — Technical, Billing, Account, Order, or Other (the real roster;
"Logistics" was an earlier prototype-spec entry, see "Naming" below).

## What this is

A **software abstraction** inspired by properties of distributed biological
information processing that current research on simple nervous systems
(including *Drosophila*) supports well: many specialised circuits evaluate
input in parallel, weaker candidates are suppressed, and only a sparse winner
acts. Concretely, for every ticket:

```
                    JEV (judgment)
                          │
              ┌───────────┴───────────┐
              │      EXPERT POPULATION │
              │  Technical  Billing    │   each department scores its own
              │  Account    Order      │   "how suitable am I?" independently,
              │  Other                 │   from cheap signals already on hand
              └───────────┬───────────┘
                          │
                    ACTIVATION (0.0–1.0 per department)
                          │
                     COMPETITION (rank all five)
                          │
                  INHIBITION / SUPPRESSION (weak candidates dropped)
                          │
                   SPARSE WINNER (usually exactly one)
                          │
                  SPECIALIST AGENT (only the winner does the real work)
```

## What this is not

- **Not a simulation of a *Drosophila* brain.** The real fly connectome has
  ~139,255 neurons and ~54.5 million synapses; this router has five scoring
  functions. Nothing here claims biological equivalence.
- **Not reinforcement learning.** There is no trained weight vector, no
  gradient update, no model being retrained. "Learning" here means: a human
  correction/override away from the swarm's pick is recorded as a
  `LearningSignal` (`"Wrong agent routing"`), which the router's own
  `_historical_signal()` reads back on future tickets — a simple, honest
  feedback loop, not a reinforcement-learning algorithm.
- **Not a per-request LLM ensemble.** All five departments are scored from
  keyword tables already in the repo (`app/domain.py`'s `INTENTS` and
  `DEPARTMENT_KEYWORDS` — the same tables Jev's own rules-based judgment
  uses) plus two cheap DB reads (live agent status, recent correction
  history). No model call happens during routing, so scoring five candidates
  costs about the same as scoring one.

## How activation works

Each department's `activation_score` is a weighted sum of four components,
computed independently per department (so one department's scoring failing
never affects another's — see "Failure handling" below):

```
activation = 0.50 · intent_match        (phrase match against app.domain.INTENTS)
           + 0.20 · domain_match        (word match against app.domain.DEPARTMENT_KEYWORDS)
           + 0.15 · availability_factor (1.0 idle, 0.6 already busy on another ticket)
           + 0.15 · historical_signal   (0.5 neutral by default; real data once corrections exist)
```

These are **prototype engineering heuristics**, not biologically measured
thresholds or a calibrated probability model — "activation" and "suitability"
are the right words for this number, not "probability this department is
correct." Weights and thresholds (`W_INTENT`, `W_DOMAIN`, `W_AVAILABILITY`,
`W_HISTORY`, `MIN_ACTIVATION`, `DOMINANCE_MARGIN`, `MAX_EXPERTS`) live as
named constants at the top of `agents/swarm_router.py` — change them there,
not in multiple places.

## Competition, inhibition, sparse activation

Every evaluation ranks all five candidates and picks the top one as the
winner. **Only the winner's specialist agent ever runs** (`execute_agent` in
`agents/graph.py` only calls `orchestrator.route(state["selected_agent"])`
for the winning department) — the other four are suppressed, never executed,
regardless of how close their scores were. This is the "sparse activation"
the architecture calls for: cheap parallel competition, then exactly one
expensive specialist runs.

## Ambiguity

Routing is flagged **ambiguous** when either:
- the winner's own score is below `MIN_ACTIVATION` (too weak to trust alone), or
- the gap between the winner and the runner-up is below `DOMINANCE_MARGIN`
  (too close a call to guess).

An ambiguous ticket does **not** get silently routed to whichever department
happened to score highest. It pauses at the existing human gate
(`agents/nodes.py::human_gate`) with `reason="ambiguous_routing"` — the same
interrupt/resume mechanism every other human gate in the graph uses, not a
new ticket state or a new human action. A teammate resolves it with
**GUIDE**, adding the missing context; the swarm re-scores with that context
folded into the ticket text (`agents/nodes.py::route_agent` reads
`state["human_action"]["guidance"]`), and the graph continues from there.

## Human correction / override

**CORRECT** and **OVERRIDE** (`agents/nodes.py::resume_correct` /
`resume_override`) both gained an optional `department` field
(`agents/api.py`'s `ResumeRequest.department`). If a teammate knows the
swarm's pick was wrong:

- **CORRECT** with a `department` reassigns the ticket to that department and
  hands off to its specialist agent to actually continue the work (without
  `department`, CORRECT behaves exactly as it did before this feature —
  fully backward compatible).
- **OVERRIDE** with a `department` records which desk the ticket really
  belonged to for the audit trail (the human still handles it directly
  either way — `handled_by="HUMAN"`).

In both cases the **original swarm decision is never erased** — it stays on
the earlier `AGENT_ASSIGNED` event (with its full `meta.swarm` payload), and
a `"Wrong agent routing"` `LearningSignal` records AI-vs-human
(`expected_action` = the swarm's original pick, `observed_action` = the
human's correction) for `_historical_signal()` to read back later.

## Dashboard visibility

- **Ticket detail** (`/ops/tickets/[ticketId]`) — a "Swarm routing" card
  (`frontend/components/ops/SwarmRouting.tsx`) reads the ticket's latest
  `AGENT_ASSIGNED` event and renders each department's score as a bar, the
  winner, and the routing reason.
- **Routing** (`/ops/routing`, new sidebar entry under "AI Operations") —
  every ticket's routing decision, same data, across the whole queue. Backed
  by `GET /api/routing` (`backend/app/services/routing_service.py`), which
  was previously wired to a broken, unreachable endpoint (`route(ticket.intent)`
  returning a single agent object where the old code expected a 2-tuple) —
  fixed and repointed at the real swarm data as part of this feature.

Neither page invents new operational vocabulary: color is never the only
signal (a `SELECTED`/`Ambiguous`/`FAILED` label always accompanies it), and
nothing shown is raw model reasoning — `routing_reason` is a short, structured
explanation ("intent matched X; Y desk available"), never chain-of-thought.

## Failure handling

Each department's own scoring runs independently and is individually
wrapped; if one raises, it's recorded in `failed_experts`, excluded from
ranking, and the remaining departments still compete normally. If **every**
department fails, `evaluate()` raises `SwarmRoutingError` rather than
silently defaulting to any department — routing failure is surfaced, never
hidden as a fake decision.

## Determinism

No randomness, no LLM temperature, anywhere in `agents/swarm_router.py`.
Identical ticket text always produces identical scores — this is required
for the graph to be replayable/testable and is covered directly by
`agents/tests/test_swarm_router.py::test_routing_is_deterministic`.

## Future learning compatibility

Today, `historical_signal` is a simple frequency count over recent
`"Wrong agent routing"` signals — real data, never fabricated (a fresh
install with no corrections yet gets a neutral 0.5 for every department, not
an invented "94% success rate"). The four score components and their weights
are named, separable constants specifically so a future learning system can
replace `_historical_signal()`'s frequency count with actual learned routing
weights without restructuring the graph, the state fields, or the human
correction/override paths — none of that depends on how the historical
component itself is computed.

## Naming

The department roster is **Technical, Billing, Account, Order, Other**
(`backend/app/vocab.py`'s `DEPARTMENTS`) — the same five used everywhere else
in the codebase. An earlier prototype spec (`docs/project.md` §19) listed a
sixth name, "Logistics"; `docs/claude.md` already documents that this was
retired — shipping/tracking questions route to **Order**
(`app.domain.INTENTS["Shipping Delay"]`), and **Other** is the deliberate
generic catch-all. This router does not reintroduce Logistics as a
department (`agents/tests/test_swarm_router.py::test_shipment_delay_routes_to_order_not_logistics`
asserts this directly).
