# Architecture

This document is derived primarily from the Excalidraw diagrams in this folder, with the ChatGPT-generated reference diagram (`neuroserve-reference-architecture.png`) supplying structural vocabulary. `project.md` is used only for the prototype's tech-stack/build-scope decisions, never for the shape of the system itself. See `[[context]]` for why, and for the glossary of terms used below.

Two views are documented:

1. **Reference architecture** — the fuller, enterprise-grade system (`neuroserve-reference-architecture.png`).
2. **Resolvyn's own operational flow** — what Dua actually designed on top of/inside that reference (`resolvyn-system-flow.png`, `resolvyn-ai-loop-detail.png`, `memory-rulebook-detail.png`).

The prototype (`project.md`) implements a thin, mocked-backend slice of view 2, expressed using the layout/visual conventions of a dashboard.

---

## 1. Reference architecture (`neuroserve-reference-architecture.png`)

Nine numbered layers, plus a cross-cutting Human Intelligence Layer at the top.

### Human Intelligence Layer (embedded, continuous, collaborative)

Sits above the pipeline, not beside it, and interacts with every layer via real-time collaboration, feedback, corrections, and learning signals:

- **Observe** — monitor live interactions, view AI reasoning/confidence, detect risk/anomalies.
- **Guide** — provide context and judgment, add business knowledge, suggest next best action.
- **Approve** — gate high-value actions (refunds/credits), policy exceptions, final decisions on edge cases.
- **Correct** — fix AI mistakes, update the knowledge base, refine policies.
- **Override** — take control when needed, handle complex/emotional cases, ensure customer satisfaction.
- **Teach** — add new rules/FAQs, share domain expertise, train the AI with real examples.

A paired **Human Agent Workspace** shows a live ticket (id, customer, issue, AI confidence, suggested action) with **Approve / Edit / Escalate** actions.

### 1. Customer Input Channels

Web/Mobile Chat (text + voice), Phone (Voice/IVR), Email, Social Media, Product Feedback, Support Portal.

### 2. Perception Layer

- **Multimodal Processor** — text/voice/images (Whisper / GPT-4o-mini class models).
- **Pre-processing & Enrichment** — clean & normalize, language detection, entity extraction, customer-profile enrichment.

### 3. Judgment & Intelligence Core

- **Jev (Judgment Model)** — fast, lightweight scoring of sentiment/mood, intent/topic, urgency, escalation probability, safety/risk flags.
- **Context & Memory Engine** — short-term (current conversation), long-term (customer history), episodic (past tickets); vector + graph RAG over policy and product knowledge.
- **Biological Learning Module** — fruit-fly-inspired circuit: reward-based learning, prediction error, adaptive decision policy, continual learning.

### 4. Decision Engine (reasoning + planning + action selection)

`Analyze (understand context) → Plan (select tools/agents) → Evaluate (risk + confidence) → Choose Action (autonomous / clarify / human)`

Decision criteria: policy compliance, customer value (VIP/enterprise), risk/fraud detection, confidence threshold, human availability.

### 5. Multi-Agent Support System (specialized agents + orchestrator)

**Orchestrator** routes, coordinates, manages context, handles retries. Specialist agents: **Billing** (invoices/payments), **Technical** (errors/diagnostics), **Order** (shipping/tracking), **Account** (profile/settings), **Returns** (refunds/policy).

### 6. Knowledge & Tools

Enterprise Docs (FAQs/manuals), Policy DB (refunds/SLAs), Product Knowledge (features/plans), Past Tickets (vector DB), External APIs (orders/billing/CRM), Knowledge Graph (entity links).

### 7. Data & Integration Layer

Databases (orders/users/payments), APIs & Microservices (CRM/billing/inventory), File Storage (docs/logs/tickets), Enterprise Systems (Salesforce/SAP/etc.).

### 8. Storage & Compute (efficient)

Vector DB (Pinecone/Weaviate — embeddings, semantic search), Object Storage (S3/Blob — documents, compressed logs), Lightweight Models (quantized/distilled, edge deployment, low memory footprint), Cache (Redis — session data, frequent lookups), Event Stream (Kafka/PubSub — real-time updates, event-driven).

### 9. Analytics & Learning Loop

Root Cause Analysis (clustering), Churn Prediction (risk signals), Emerging Issues (trend detection), Performance Metrics (accuracy/latency/cost) — fed by Customer Feedback (clustering) and Human Correction (Kafka/PubSub), producing Outcome Signals (policy updates) and Continued Signals (policy alignment) back into the loop.

### Key innovations named in the reference diagram

Jev for fast judgment (sentiment/intent/urgency); fruit-fly-inspired reward learning (dopamine-like); prediction error for better decision-making; agentic RAG with iterative search & verification; event-driven processing (spike-like); mixture-of-experts routing (fruit-fly inspired); knowledge graph + vector search; quantized/distilled models (low storage); human-in-the-loop (embedded, not fallback).

### Reference tech stack

| Concern | Options named |
|---|---|
| Frontend | React / Next.js |
| Backend | FastAPI / Node.js |
| AI / Models | OpenAI / Llama / Mistral |
| Vector DB | Pinecone / Weaviate |
| Database | PostgreSQL / MongoDB |
| Queue / Stream | Kafka / Redis |
| Storage | S3 / Blob |
| Infra | Docker / Kubernetes |

### Expected outcomes (as stated on the diagram)

↑30–50% first-contact resolution, ↓60–80% wrong actions via better judgment, ↓60–80% compute/storage, faster enterprise deployment (SSO/RBAC), ↓40–70% response times, ↑20–40% customer satisfaction, continuous learning & self-improvement. These are the reference architecture's aspirational targets, not measured prototype results — do not present them as prototype metrics.

---

## 2. Resolvyn's operational flow (`resolvyn-system-flow.png`)

This is Dua's own design, using the reference architecture above as its vocabulary. It is triggered by one of four channel types: **Call, Text, Email, Audio**.

### 2.1 Intake & classification

1. An **intelligent classifier** first determines whether the person on a call is really talking to the agent or to someone else (liveness/attentiveness check on the call itself).
2. Language handling uses **real, native Hindi and English speakers/models**; additional languages route through **Gnani AI**.
3. The triggering message enters the **LLM in the chain**, grounded by the **Memory system** (business details + SOPs) — see §3.

### 2.2 Instant-resolve vs. escalation

- **Instant-resolve system**: if the query is resolvable from the LLM + memory system alone, Resolvyn answers directly — no ticket routing needed.
- **Escalation**: if not resolvable, the matter is escalated to the resolving team **in real time, before the call finishes**, by asking the customer for basic account details. This immediately:
  - creates a **context doc autonomously in Confluence**, and
  - creates a **ticket, assigned to a specific person on the team**.

### 2.3 Agent departments

Escalated/routable work fans out to department agents, chosen **on the basis of the user query**: **Tech, Billing, Account, Order, Other**. (These map 1:1 onto the reference architecture's specialist agents, minus "Returns," plus a catch-all "Other".)

### 2.4 Ticket lifecycle & dashboard sync

- A **ticket is created in real time** the moment escalation happens.
- **Ticket & status are displayed in real time in the customer's dashboard.**
- **Ticket status is updated in real time by the team.**
- Ticket status is **constantly monitored in Atlassian Jira or Zoho**.
- This entire monitoring process runs **autonomously**.

### 2.5 The Resolvyn AI ↔ human loop (`resolvyn-ai-loop-detail.png`)

At the center: an **AI** node with a two-way link to the **Triggering point** (the live conversation).

- The AI performs **real-time extraction from the user conversation** into a structured ticket object:
  ```
  ticket id: #0067
  customer name
  body
  AI Confidence level
  ```
- The AI derives **work/intent** and consults the **solvable rulebook/access**.
- This is explicitly a **"human combined AI"** model: **"human approval gate and betterment of the solution can be suggested."**
- Two human-facing exits: **Human intervention** and **Human Team (Intervention)** — the individual human-in-the-loop actions (Guide/Approve/Correct/Override/Teach, per the reference architecture) versus a full team escalation.
- The AI also feeds a **Context engine**, which drives:
  - **ticket display**, synced to **Jira** ("team side only"), and
  - a **one-line summary** for the team side.

### 2.6 Memory & rulebook system (`memory-rulebook-detail.png`)

This is the detail behind "LLM in the chain" / "Memory system containing business details and SOP":

```
Triggering point → Query → LLM → JEV Written Query → Query → Rulebook
```

Two memory stores sit alongside the rulebook, each split into a **vector** half and a **knowledge-graph** half:

1. **Common/past-query memory** — vector half: *Business logic, Pure SOPs, Product DB*; knowledge-graph half: *memory*. Used for "a common query / a past query."
2. **First-time-bug memory** — vector half: *First time bug*; knowledge-graph half: *memory*. Used when the issue is "completely unrelated to company" precedent.

When no known path resolves the query, the system surfaces:

> **"A FIRST TIME BUG HAS BEEN REPORTED — HERE'S MORE DETAIL, PLEASE ENTER YOUR SUGGESTION"**

That human suggestion is what feeds the **Solvable Rulebook**, which loops back into the AI ↔ human loop in §2.5 — this is Resolvyn's concrete, prototype-safe stand-in for the reference architecture's "prediction error / continual learning" concept (see `[[context]]`, Biological Learning Module).

### 2.7 End-to-end trace

Putting §2.1–§2.6 together, the full trace a single ticket produces is:

```
Channel (Call/Text/Email/Audio)
  → Classifier (talking to agent? language?)
  → LLM + Memory (instant-resolve attempt)
  → [resolved]                    → response to customer, no ticket
  → [not resolvable] → Escalate in real time
        → Context doc created (Confluence)
        → Ticket created, assigned to team member
        → Routed to Agent Department (Tech/Billing/Account/Order/Other)
        → Ticket synced to dashboard + Jira/Zoho (real time, autonomous)
        → AI extracts structured ticket (id, customer, body, confidence)
        → AI determines work/intent, consults solvable rulebook
        → Human intelligence gate (Guide/Approve/Correct/Override/Teach,
           or full Human Team intervention)
        → [known path]      → executed via rulebook, context engine updates
                               ticket display + Jira + one-line summary
        → [first-time bug]  → flagged to human for a suggestion
                               → suggestion written into the Solvable Rulebook
        → Ticket resolved / verified
```

---

## 3. Prototype scope (`project.md`)

The first build is a **dashboard-only demonstration** of the trace in §2.7, for one hero ticket (`PH-1042`, duplicate payment) plus a handful of background tickets. It deliberately narrows the two architectures above:

- **Real in the prototype**: navigation, ticket state, filtering, ticket detail, customer data, agent state, activity timeline, human actions (Guide/Approve/Correct/Override/Teach), learning-signal creation, demo-mode state transitions.
- **Simulated in the prototype**: Payment/Refund/Order/Shipping/Customer APIs (deterministic mock services, §38 of `project.md`), Jira/Zoho sync, Confluence doc creation, multilingual/voice classification.
- **Optional**: a real LLM call for response generation/intent classification/summarization — the app must still work with deterministic mock outputs if none is configured.
- **Explicitly out of scope for v1** (`project.md` §3.2): real CRM/payment/banking/shipping integrations, production auth, production-scale vector DBs, actual RL training, actual biological-circuit simulation, neuromorphic hardware, complex voice support, email/social ingestion, full enterprise deployment infrastructure.

### Prototype tech stack

```
Frontend        React / Next.js
API Layer       FastAPI
Orchestration   Support Decision Engine   (§2.5/§3 §4 of the reference arch, scoped down)
Specialist      Agents                    (Billing, Account, Technical, Order, Logistics)
Mock APIs       Customer / Order / Payment / Refund / Shipping / Account
Database        SQLite
Realtime        WebSocket (fallback: short polling)
```

Prototype ticket status model: `NEW → ANALYZING → ROUTING → ACTIVE → WAITING_FOR_HUMAN → VERIFYING → RESOLVED / FAILED`. Prototype agent states: `IDLE, ANALYZING, RETRIEVING, ACTING, VERIFYING, WAITING, COMPLETED, ERROR`. These are the only vocab the UI may use — see `[[claude]]` for the full list of naming/consistency rules.

### Mapping prototype components to the architecture

| Prototype module (`project.md` §82) | Architecture concept it implements |
|---|---|
| `backend/services/ticket_service` | Ticket lifecycle, §2.4 |
| `backend/services/agent_service` + specialist agents | §5 Multi-Agent Support System / §2.3 Agent Departments |
| `backend/services/knowledge_service` | §6 Knowledge & Tools, §2.6 common-query memory |
| `backend/services/tool_service` + mock APIs | §6 External APIs / §7 Data & Integration Layer (mocked) |
| `backend/services/human_service` | Human Intelligence Layer, §2.5 human loop |
| `backend/services/learning_service` | §9 Analytics & Learning Loop, §2.6 first-time-bug → Solvable Rulebook |
| `backend/demo` | §46–48 of `project.md`, deterministic replay of §2.7's end-to-end trace |

See `[[claude]]` for the actual repository folder layout and the engineering rules that keep the prototype from silently drifting away from this architecture.
