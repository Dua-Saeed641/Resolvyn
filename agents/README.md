# Orchestration layer

A standalone package (repo root, sibling to `backend/`, `frontend/`, `engine/`) implementing
Resolvyn's ticket-level orchestration graph with [LangGraph](https://github.com/langchain-ai/langgraph).
Everything in this task lives here — see "Why a separate folder" below.

```
                    RESOLVYN ORCHESTRATOR

                          START
                            │
                       PERCEPTION
                            │
                         JUDGMENT (Jev)
                            │
                    CONTEXT / MEMORY
                            │
                         ANALYZE
                            │
                    PLAN + ROUTING
                            │
                        EVALUATE
                            │
                ┌───────────┴───────────┐
                │                       │
         ESCALATED /              INSTANT / ACTION
       FIRST_TIME_BUG                   │
                │                 SPECIALIST AGENT
                │                       │
                │                   TOOL / API
                │                       │
                │                    VERIFY ──────┐
                │                    /      \     │
                │                RETRY    SUCCESS │
                │                  │          │   │
                │                  └──────────┘   │
                └───────────┐                     │
                             ▼                     ▼
                        HUMAN GATE ◄───────────────┘
                     (interrupt — pauses)
                             │
              GUIDE / APPROVE / CORRECT / OVERRIDE / TEACH
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        execute_agent   retrieve_context  verify
         (retry with    (TEACH: re-       (APPROVE/
          new context)   evaluate with     CORRECT/
                          the new rule)     OVERRIDE)
                             │
                      RESPONSE (deterministic —
                      Plan.fallback, never invented)
                             │
                         OUTCOME (RESOLVED/FAILED/
                          WAITING_FOR_HUMAN via
                          ticket_service vocabulary)
                             │
                      LEARNING SIGNAL
                             │
                            END
```

## 1. Why a separate folder

Per the task: build the orchestration layer in its own place, touching nothing else. The
support-operations dashboard (`frontend/`) and the real-time voice/chat pipeline
(`backend/app/services/conversation.py`, already a working, tested implementation of
UNDERSTAND→REMEMBER→REASON→ACT→VERIFY→LEARN for *live calls*) are untouched. `engine/`
(Lovekesh's Epsilon engine) is untouched and not imported here at all.

This is **not** a second engine and does not compete with `conversation.py`. `conversation.py`
handles one live call, turn by turn, with a `CallSession` and streamed speech. This package handles
the *ticket-level* question "run this ticket through the full resolution loop as an explicit,
resumable graph" — useful wherever a ticket needs to be processed without a live caller on the
line (or replayed/inspected as a graph run), and it reuses every real service `conversation.py`
already reuses, rather than reimplementing any of them.

Only one file outside this folder exists because of this work:
`backend/app/api/routes/orchestration.py` — an 11-line bridge that puts the repo root on
`sys.path` and re-exports `agents.api.router`, plus one `include_router` line in
`backend/app/api/router.py`. Nothing else in `backend/` or `frontend/` changed.

## 2. State (`state.py`)

`ResolvynState` is a `TypedDict` — the minimum the *graph* needs between nodes. It does not
duplicate domain models: `agent_state` is passed straight through as
`TurnContext.state` (`backend/app/agents/base_agent.py`), so every specialist agent's own
bookkeeping (`awaiting`, `order_id`, `refund_candidate`, `pending_action_id`, …) works
unmodified — the graph never needs to know an agent's internal vocabulary. `trace` accumulates
(via a reducer) across every node for observability (spec §26); `public_state()` strips
`agent_state` before anything is shown to an API caller (spec §50-51: domain state, not
framework internals, no raw customer scratch text).

## 3. Nodes (`nodes.py`) and the graph (`graph.py`)

Each node has one job and calls straight through to the real backend service:

| Node | Delegates to |
|---|---|
| `run_perception` | `agents.engine_provider` → `app.perception.perception_service.enrich` |
| `run_judgment` | → `app.judgment.jev.rules_judge` (deterministic — no model needed) |
| `retrieve_context` | → `app.memory.memory_engine.memory.retrieve` (vector + knowledge-graph, both memories) |
| `run_decision` | → `app.decision_engine.decision_engine.decide` (the real Analyze→Plan→Evaluate→Choose engine — reused, not reimplemented) |
| `route_agent` | → `app.agents.orchestrator.route` / `.set_state` |
| `execute_agent` | → the specialist agent's own `plan()` (`app.agents.billing_agent` etc.) — **real tool calls happen here**, via `agent.tool()` → `app.tools.tool_service.call()` |
| `handle_escalation` / `flag_first_time_bug` | → `app.memory.memory_engine.memory.record_first_time_bug` |
| `human_gate` | `langgraph.types.interrupt(...)` — pauses the graph; dispatches the resume value to `resume_guide`/`resume_approve`/`resume_correct`/`resume_override`/`resume_teach` |
| `verify` | inspects the agent's own `Plan.facts` for a `"...VERIFIED..."` marker — the same convention `backend/app/services/conversation.py::_confidence` already uses |
| `generate_response` | uses `Plan.fallback` **verbatim** — the agent playbook's own deterministic, fact-grounded response (spec §22: never generated from the planned action alone) |
| `record_outcome` | → `app.services.ticket_service.update` (vocabulary unchanged: `NEW…RESOLVED/FAILED`) |
| `emit_learning_signal` | → `app.learning.learning_service.record` |

`graph.py` wires these with explicit conditional edges (spec §49) — see the diagram above. No
node is a giant `process_everything()` (spec §48).

## 4. The human gate (`human_gate`, `service.py`)

`interrupt()` durably pauses the graph via LangGraph's SQLite checkpointer
(`langgraph-checkpoint-sqlite`, `agents/data/checkpoints.db`), keyed by `thread_id = ticket_id`.
Everything in `ResolvynState` at that point — decision, plan, pending_action_id/bug_id, retry
count, trace — survives a process restart. `ResolvynOrchestrator.resume(ticket_id, action)`
(`service.py`) is the only way back in; it rejects (`OrchestrationError`, HTTP 409) a resume on a
thread that isn't actually paused, so a duplicate/stray resume call can't replay side effects
(spec §16, §30, §42 — see `agents/tests/test_idempotency.py`).

The five human actions are genuinely distinct (spec §15), not one generic handler:

- **GUIDE** — logs a `HumanAction`, extracts entities from the guidance text (reusing
  `perception_service.enrich`) to unblock a stalled agent, then loops back to `execute_agent`.
- **APPROVE** — decides the real `PendingAction` row, then calls the specialist agent's own
  `resume(ctx, "approved"/"rejected", ...)` — the exact function `conversation.py` calls too —
  which executes and verifies for real.
- **CORRECT** — writes a `RulebookEntry` (`source="human_correction"`) and treats the human's
  correction as the resolved action directly.
- **OVERRIDE** — hands the ticket to the human (`handled_by="HUMAN"`), records the human's
  chosen outcome as-is — the AI's original plan is discarded, not merged.
- **TEACH** — writes a rulebook rule **and** calls `memory.attach_bug_suggestion` (the actual
  mechanism `decide()`'s `KNOWN_OPEN_BUG` branch checks for — a rulebook entry alone is not
  enough to close a first-time-bug loop, see `agents/tests/test_teach_first_time_bug.py`), then
  loops back to `retrieve_context` to re-evaluate with the new knowledge in place.

## 5. Why one venv, not two

`agents/` imports `app.*` from `backend/` directly (`agents/_bootstrap.py` puts `backend/` on
`sys.path`, mirroring the existing `from data.seed_data import ...` convention already used
inside `backend/app/tools/mock_apis.py`). It is not a redistributable library; it is
orchestration code for *this* backend. `agents/requirements.txt` documents the two added
packages (`langgraph`, `langgraph-checkpoint-sqlite`) but they are installed into
`backend/.venv` — the same interpreter `uvicorn app.main:app` already runs under. No new
virtual environment, no new lockfile, no change to any existing pinned version in
`backend/requirements.txt`.

## 6. Epsilon / engine boundary (`engine_provider.py`)

`DeterministicEngineProvider` wraps `perception_service.enrich`, `jev.rules_judge`,
`memory.retrieve`, and `decision_engine.decide` — all already deterministic and safe with
`ENGINE_ENABLED=false` (verified: `backend/tests` run exactly that way, and so does
`agents/tests`, `pytest.ini`-free, no API keys required). `RealEngineProvider` is the documented
extension point (spec §33) for a model-assisted path; it is intentionally identical today,
because the actual model-assisted refinement (`jev.refine_with_model`, `jev.grounded`) already
lives inside the functions this delegates to, gated on `backend/app/llm.llm.ready(...)`. There is
no Epsilon API invented here, and nothing under `engine/` is imported, read, or modified.

## 7. API (`api.py`, mounted at `/api`)

- `POST /api/tickets/{ticket_id}/process` — spec §7's entry point. Body: `{"text"?: str, "channel"?: str}`
  (defaults to the ticket's own `body`/`subject`). Starts a fresh graph run.
- `POST /api/tickets/{ticket_id}/resume` — Body: `{"action": "GUIDE"|"APPROVE"|"CORRECT"|"OVERRIDE"|"TEACH", "operator"?: str, ...}`.
- `GET /api/tickets/{ticket_id}/orchestration` — read-only current state (404 if no run exists).

The frontend, if it ever calls these, talks to plain JSON — never to LangGraph (spec §27).

## 8. Tests (`tests/`)

19 tests, `pytest agents/tests -q`, no pytest-asyncio (plain `def test_...()` driving its own
`asyncio.run`, one fewer dependency), no model, no network:

- **Unit** (`test_state_and_engine_provider.py`): state isolation between runs, the
  deterministic engine provider's judge/perceive/retrieve/reason in isolation.
- **Integration** (everything else): the full PH-1042 approve/reject flow, CORRECT, OVERRIDE,
  TEACH/first-time-bug (including the "second caller, same problem, answered from memory"
  re-evaluation path), GUIDE, transient vs. persistent tool/verification failure (the mandatory
  spec §41 test — a permanently failing `verify_refund` must never let the ticket become
  `RESOLVED` or the response claim success), and idempotency (a second `resume` on a completed
  thread is rejected, never replayed; exactly one refund, one approval log, one learning signal).

Run `cd backend && .venv/Scripts/python -m pytest ../agents/tests -q` (or from the repo root:
`backend/.venv/Scripts/python -m pytest agents/tests -q`).

## 9. Honest limits

- `execute_agent`'s auto-confirm loop (bounded, ≤3 hops) answers an agent's own
  `awaiting: confirm_*` question on the ticket's behalf, since there is no live caller to ask —
  the ticket's own text is treated as the request. This is the one place ticket-level processing
  genuinely differs in shape from a live call turn.
- Graph-level retry (`register_failure` → re-run `execute_agent`) is a coarser retry than
  `tool_service`'s own internal one: it re-runs the whole specialist-agent turn, not a single
  tool call. `mock_apis.issue_refund`'s existing idempotency (keyed on `order_id` +
  `transaction_id`) is what keeps that safe from double side effects.
- Verification only gates the `ACTION` decision path (spec §21: "for actions requiring it") —
  `INSTANT`/small-talk responses have nothing to verify and pass straight through.
