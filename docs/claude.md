# Working in this repository

Read this before touching code. It exists to keep implementation from drifting away from what Resolvyn actually is. Read `[[context]]` first if you haven't (what Resolvyn is, glossary), then `[[architecture]]` (the full system design). This file is the resulting engineering rulebook.

## Ground truth order

1. **The diagrams** (`docs/resolvyn-system-flow.png`, `docs/resolvyn-ai-loop-detail.png`, `docs/memory-rulebook-detail.png`, `docs/neuroserve-reference-architecture.png`) define what the system *is*.
2. **`docs/architecture.md`** is the text transcription of (1) — treat disagreements between architecture.md and this file as a bug in this file.
3. **`docs/project.md`** defines how the *first prototype* should look and what to build first. It is scoped down on purpose (see `[[context]]`, "Project stage") — never take it as the system's architecture, only as the current build's UI/demo spec.

If you're about to add a feature, a page, or a backend module and can't tell which of these governs it: it's product behavior → check the diagrams / architecture.md; it's visual design, copy, or prototype build order → check project.md.

## Naming and copy

- The product is **Resolvyn**, spelled exactly that way, everywhere — code, UI copy, docs, commit messages. Never substitute "NEUROSERVE" or any other name as the product identity; that name belongs only to the reference diagram.
- No marketing language. Use operational language: "Payment verification in progress," "Billing Agent active," "Human approval required," not "Revolutionizing customer support with cutting-edge AI."
- No `Lorem ipsum`, `Coming soon`, `TODO`, or "Example text" left visible in any page a user can reach. Backend scaffolding for not-yet-built logic should raise `NotImplementedError` with a one-line pointer to the relevant architecture section — never silently return fake success.
- Never claim a simulated action succeeded. A refund/order/shipping call must show its real state (`NOT_STARTED → WAITING → COMPLETED / FAILED`); don't let the AI's assistant-style response get ahead of what a tool call has actually verified.

## Vocabulary — do not invent new terms

These are the only values the UI and API may use. They live in `frontend/lib/constants.ts` on the frontend; keep backend models (`backend/app/models/`) in sync with it.
- **Ticket status**: `NEW, ANALYZING, ROUTING, ACTIVE, WAITING_FOR_HUMAN, VERIFYING, RESOLVED, FAILED`
- **Agent state**: `IDLE, ANALYZING, RETRIEVING, ACTING, VERIFYING, WAITING, COMPLETED, ERROR`
- **Priority**: `LOW, MEDIUM, HIGH, CRITICAL` — color only on HIGH/CRITICAL
- **Sentiment**: `Positive, Neutral, Frustrated, Angry` — no emojis, not visually dominant
- **Confidence bands**: High ≥90%, Medium 75–89%, Low <75% (UI thresholds only, not calibration claims)
- **Human actions**: `GUIDE, APPROVE, CORRECT, OVERRIDE, TEACH` — always all five, always this order, never presented as "just an escalation"
- **Department agents** (`docs/architecture.md` §2.3 — the flow diagram is ground truth): Technical, Billing, Account, Order, Other. (An earlier prototype roster listed Logistics; shipping/tracking belongs to the Order agent, and "Other" is the catch-all from the diagram.)

## Design system

The UI is built on **shadcn/ui** (Radix primitives + Tailwind): `frontend/components/ui/*` are the shadcn components; `primitives.tsx`, `StatusBadge.tsx`, `MetricCard.tsx` are thin app wrappers over them. Use these, not hand-rolled buttons, cards, inputs or dialogs.

- One calm neutral (zinc) palette with light and dark themes, defined once as CSS variables in `frontend/app/globals.css` and mapped in `frontend/tailwind.config.ts`. Never hard-code a hex colour in a component; use tokens (`bg-card`, `text-muted-foreground`, `border`, `text-success`...). The legacy token names (`text-text-primary`, `bg-bg-secondary`) still resolve to the same palette.
- Status colours (`success`, `warning`, `danger`, `info`) are muted and used only where they communicate status, always paired with a label or icon (never colour alone). No neon, no glow effects, no decorative gradients.
- Typography: Inter. Hierarchy comes from weight and size, not colour.
- Every page needs a real empty state (`components/ui/EmptyState.tsx`), never a blank pane.
- Motion is functional: fades, state transitions, and the voice orb (`components/voice/VoiceOrb.tsx`), which reflects what the assistant is doing (listening, thinking, speaking). It respects `prefers-reduced-motion`.
- Icons: lucide-react.

## Folder structure

`engine/` is a copy of the author's epsilon engine (see `engine/README.md`): `llama-server` process management for the local
Qwen models. Resolvyn's backend reaches models only through `backend/app/llm/`.

`agents/` (repo root, sibling to `backend/`/`frontend/`/`engine/`) is the LangGraph-based ticket
orchestration layer — a standalone package, deliberately separate from `backend/app/services/conversation.py`
(the live per-call turn loop) rather than a replacement for it. See `agents/README.md` for the graph,
the human-gate/interrupt design, and why it lives in its own folder. Only `backend/app/api/routes/orchestration.py`
(an 11-line bridge) and one `include_router` line in `backend/app/api/router.py` connect it to the backend.

```
docs/            claude.md, architecture.md, context.md, project.md, source diagrams
agents/          Standalone LangGraph orchestration layer — see agents/README.md
backend/         FastAPI service
  app/
    api/routes/            HTTP endpoints — one file per sidebar section
    models/                 SQLModel tables (project.md §39-44)
    perception/             Perception Layer            (architecture.md §1 layer 2)
    judgment/                Judgment & Intelligence Core / Jev (layer 3)
    decision_engine/        Analyze → Plan → Evaluate → Choose Action (layer 4)
    agents/                  Orchestrator + 5 specialist agents (layer 5)
    knowledge/              Knowledge & Tools retrieval  (layer 6)
    memory/                  Context & Memory Engine, Solvable Rulebook (§2.6)
    human_intelligence/     Guide / Approve / Correct / Override / Teach
    learning/               Learning Signals             (layer 9)
    tools/                   Simulated enterprise APIs + tool_service (persisted NOT_STARTED→WAITING→COMPLETED/FAILED)
    llm/                     The only door to a model: epsilon engine, optional free cloud LLM, fallback
    voice/                   Gnani STT/TTS (rate-limit aware, disk-cached), edge-tts fallback, mu-law, spoken-text humaniser, fillers, sentence streamer
    context_engine/          Live one-line + detailed ticket notes, context doc, deep (27B) analysis
    integrations/            Simulated Jira/Zoho sync + autonomous monitor loop
    services/               Cross-cutting orchestration (ticket_service, demo_service)
  data/                     Deterministic seed/mock data (project.md §70: internally consistent)
  tests/
frontend/        Next.js (App Router, TypeScript, Tailwind)
  app/                      Routes — one folder per sidebar section
  components/
    layout/                  Sidebar, TopBar, AppShell
    ui/                       Design-system primitives
    tickets/ agents/ customers/ knowledge/ tools/ activity/
    human-intelligence/ learning/   Domain components  (project.md §83)
  features/                 Per-domain TypeScript types, mirroring backend/app/models
  lib/                       constants.ts (shared vocab), api.ts (fetch client), utils.ts
```

This intentionally adapts `project.md` §82's flatter suggestion (`/backend/services/{ticket,agent,knowledge,tool,human,learning}_service`) into the fuller architecture's own module names, because the diagrams — not §82 — are the priority. `services/` is kept as a thin cross-cutting layer on top of the modules above; it is not where business logic should accumulate.

## Engineering rules

- **Ticket state lives in one place**: `backend/app/services/ticket_service.py`. Routes and other services read/write tickets through it, never by touching persistence directly (project.md §58).
- **Business logic stays off the frontend.** Components render state; they don't decide it. If a component needs a decision (should this action be auto-approved?), that decision was already made by the backend.
- **Mocked services must stay obviously mocked.** `backend/app/tools/mock_apis.py` (and its callers) must never be described in UI copy or docs as a real payment/CRM/shipping integration (project.md §86-87).
- **State consistency**: a human action (Approve/Correct/Override/Teach) must (1) write the corresponding row, (2) update ticket/agent state, (3) be reflected in the activity timeline, and (4) be capable of emitting a learning signal — a UI button that only animates without changing backend state is a bug (project.md §71).
- **Data realism**: all mock data comes from `backend/data/seed_data.py`. IDs referenced in a ticket (customer, order, refund) must stay consistent everywhere they're shown — never generate random IDs inline (project.md §70).
- **No production-scale ambition creeping into the prototype**: no real CRM/payment/banking/shipping integrations, no production auth, no real RL training claims, no social-media ingestion. See `[[context]]`, "Project stage," for the full list.
- **Prototype must run without a real LLM.** Anything that calls a model goes through `backend/app/llm` and needs a deterministic fallback (Jev has rules, agents have playbooks with a `fallback` line, the context engine writes a heuristic note first). `ENGINE_ENABLED=false` plus no cloud key must leave every flow working — `pytest` runs exactly that way.
- **The model speaks, the playbook decides.** A department agent runs tools and returns verified facts (`Plan.facts`); the language model only phrases them (`agents/persona.py`). Never let the persona invent amounts, limits, policies, or claim an action that no completed tool call verified.
- **Humans never wait on the model, and the model never waits on background work.** A new caller utterance cancels in-flight summaries; the 27B deep tier only runs when no call is active; finalisation (`_spawn`) must survive a hang-up.

## Before calling something done

- `cd backend && .venv/Scripts/python -m pytest -q` should pass (no GPU needed; it runs the real WebSocket pipeline on the deterministic path).
- `cd frontend && npm run build` should succeed with no type errors.
- If you touched UI, actually run it (`.\start.ps1`, or `uvicorn app.main:app` in `backend/` and `npm run start` in `frontend/`) and look at both sides: the customer side (`/`) and the team console (`/ops`). Don't rely on the build passing alone. Don't run `next build` while `next dev` is serving the same `.next` folder.
- Re-check the vocabulary list above — a new status/state/label string is almost always a mistake.
