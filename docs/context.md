# Context

## What Resolvyn is

Resolvyn is an autonomous AI customer-support system built around **resolving issues**, not just answering questions. A traditional support bot tells a customer to "contact billing." Resolvyn checks the customer, checks the order, checks the payment records, detects the duplicate charge, checks the refund policy, executes the refund, verifies it succeeded, and only then responds — with a human able to step into that loop at any point.

The product's central idea, stated directly by its author:

> **AI handles the work. Humans remain embedded in the intelligence loop.**

The visible chain the system must make legible end-to-end is:

```
UNDERSTAND → REMEMBER → REASON → ACT → VERIFY → LEARN
```

and humans enter that chain through exactly five actions: **Guide, Approve, Correct, Override, Teach**.

## Source of truth

This project is documented primarily through **diagrams, not prose**. Per explicit direction from the project owner:

> "Please keep your whole emphasis on architecture images rather than project.md — project.md just provides the summary of the project, but the whole project is properly defined in the screenshots (Excalidraw images) and the architecture generated from ChatGPT."

Concretely, `docs/` contains two kinds of evidence, and they disagree in scope on purpose:

| File | Author | What it defines |
|---|---|---|
| `resolvyn-system-flow.png` | Dua (project owner), Excalidraw | **Primary.** The real, intended Resolvyn call/ticket flow — classification, languages, instant-resolve vs. escalation, agent departments, ticket lifecycle, LLM/memory/rulebook loop, human intervention. |
| `resolvyn-ai-loop-detail.png` | Dua, Excalidraw (crop of the above) | **Primary.** Close-up of the AI ↔ ticket-context ↔ human-intervention ↔ Jira/context-engine loop. |
| `memory-rulebook-detail.png` | Dua, Excalidraw (crop of the above) | **Primary.** Close-up of the LLM/memory/rulebook subsystem, including the "first-time bug" learning path. |
| `neuroserve-reference-architecture.png` | ChatGPT-generated, embedded by Dua as "Dua's system" reference | **Secondary / reference.** A fuller enterprise-grade architecture (labeled "NEUROSERVE — Human + AI Customer Support Intelligence System") used as the structural vocabulary (layers, agent names, tech stack) that Resolvyn's own flow is expressed in. |
| `project.md` | Written as a spec for a build tool ("Antigravity") | **Supplementary, scoped down.** A prototype/hackathon UI-and-demo specification — visual design system, page layouts, mock data, demo script. It is useful for *how the dashboard should look and behave in a first prototype*, but it is not the system's architecture, and where it conflicts with the diagrams, the diagrams win. |

When in doubt: **the diagrams define what Resolvyn is; `project.md` defines how a first demo of it should look.** See `[[architecture]]` for the full breakdown of both.

## Problem framing

Traditional chatbots are answer-shaped: they classify a question and return a canned response or a hand-off. Resolvyn is resolution-shaped: it treats a support message as the start of a multi-step operational task (verify → decide → act → verify again → respond), with a specialist agent, retrieved knowledge, and a real (or, in the prototype, simulated) tool call behind every claim it makes to the customer. It must never tell a customer an action succeeded before it has verified that it did.

## Key concepts / glossary

- **Jev** — the fast "judgment model" in the NEUROSERVE core: scores sentiment, intent/topic, urgency, escalation probability, and safety/risk flags on every incoming message. Named explicitly in the reference architecture.
- **Context & Memory Engine** — holds short-term (current conversation), long-term (customer history), and episodic (past tickets) memory, plus vector + graph retrieval over policy/product knowledge.
- **Biological Learning Module** — the "fruit-fly-inspired" reward/learning circuit: reward-based learning, prediction error, adaptive decision policy, continual learning. In the prototype this is represented only as a **learning-event concept** (see Learning Signals below) — the project explicitly forbids claiming a trained reinforcement-learning model exists yet.
- **Decision Engine** — Analyze → Plan → Evaluate → Choose Action, gated by decision criteria (policy compliance, customer value, risk/fraud detection, confidence threshold, human availability).
- **Multi-Agent Support System** — an Orchestrator routes to specialist agents. NEUROSERVE names five: Billing, Technical, Order, Account, Returns. Dua's own flow diagram groups the same idea as **Agent Departments**: Tech, Billing, Account, Order, Other, chosen "on the basis of the user query."
- **Instant-resolve system** — if a query is resolvable without escalation, the LLM (grounded in the memory system) answers directly; otherwise the matter is escalated to the resolving team *in real time, before the call finishes*, by asking the customer basic account details.
- **Memory system (vector + knowledge graph)** — split into two stores: one for "a common query / a past query" (Business logic, Pure SOPs, Product DB as vectors; a parallel knowledge-graph memory), and one for **first-time bugs** — issues "completely unrelated to company" precedent. A first-time bug triggers a distinct UI/response path: *"A FIRST TIME BUG HAS BEEN REPORTED — HERE'S MORE DETAIL, PLEASE ENTER YOUR SUGGESTION"*, which feeds the **Solvable Rulebook**.
- **Solvable Rulebook** — the accumulating ruleset the LLM queries (`Query → Rulebook`) before acting; it is what gets extended when a first-time bug is resolved and taught back into the system, and what a Human Team's intervention/suggestion also updates.
- **Context engine** — real-time extraction from the live conversation into a structured ticket object (`ticket id, customer name, body, AI confidence level`), which drives both the customer-facing ticket display and the team-side Jira sync and one-line summary.
- **Human Intelligence Layer** — humans are embedded, not just an escalation destination. Five actions, consistent across the whole app: **Guide** (add context when confidence is low), **Approve** (gate high-value/risky actions), **Correct** (fix a wrong AI decision), **Override** (take control), **Teach** (add new rules/knowledge). Every one of these actions must be logged and must be able to produce a **Learning Signal**.
- **Learning Signal** — the recorded artifact of a human correction/override/teaching event: AI decision vs. human decision vs. reason vs. outcome. This is the prototype's stand-in for "prediction error" without claiming real RL training occurred.
- **Ticket status model** — exactly: `NEW, ANALYZING, ROUTING, ACTIVE, WAITING_FOR_HUMAN, VERIFYING, RESOLVED, FAILED`. Do not invent additional states.
- **Confidence** — displayed simply as a percentage + label (High ≥90%, Medium 75–89%, Low <75%). These are prototype UI thresholds, not model-calibration claims.

## Project stage

Two layers of ambition coexist on purpose:

1. **Full vision** (the diagrams): an enterprise-grade, multi-channel (chat/phone/email/social), multi-language, biologically-inspired, self-learning support intelligence system with real enterprise integrations, a vector+graph knowledge base, and a continuous human-in-the-loop learning cycle.
2. **First prototype** (`project.md`): a single, polished demonstration of *one complete operational loop* end-to-end (the PH-1042 duplicate-payment ticket), built as a dashboard, with enterprise services **mocked**, no real RL training, and no real financial/CRM integrations. `project.md` §3.2 is explicit about what NOT to attempt yet (real CRM/payment/banking/shipping integrations, production auth, production-scale vector DBs, actual RL training, actual biological-circuit simulation, neuromorphic hardware, complex voice, email/social ingestion, full enterprise deployment infra).

Do not let the full-vision terminology (NEUROSERVE's Kafka/Kubernetes/Pinecone stack) leak into prototype claims of capability — see `[[architecture]]` for how the two map onto each other, and `[[claude]]` for the resulting engineering rules.

## Naming

The product name is **Resolvyn**, always spelled exactly that way. Do not introduce or default to alternative names such as "NEUROSERVE," "Autonomous Support AI," or "Customer Support AI" as the product's own name — NEUROSERVE is the reference architecture's own label, used here only as a source diagram, not the product identity.
