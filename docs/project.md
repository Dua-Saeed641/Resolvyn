# Resolvyn

## Autonomous AI Customer Support — Prototype Specification

**Document Type:** Product + UX + Technical Prototype Specification
**Target Builder:** Antigravity
**Prototype Goal:** Build a polished, functional demonstration of Resolvyn's autonomous customer-support control center.

---

# 1. PRODUCT OVERVIEW

## 1.1 Product Name

**Resolvyn**

The name must appear exactly as:

> Resolvyn

Do not rename the product.

Do not introduce alternative names such as NEUROSERVE, Autonomous Support AI, or Customer Support AI as the primary product name.

---

## 1.2 What We Are Building

Resolvyn is an autonomous AI customer-support system.

For this prototype, we are **not attempting to implement the entire research architecture**.

Instead, the prototype must demonstrate one complete operational loop:

```text
Customer
   ↓
Support Ticket
   ↓
AI Understanding
   ↓
Specialist Agent Selection
   ↓
Knowledge / Memory Retrieval
   ↓
Tool / API Action
   ↓
Verification
   ↓
Customer Response
   ↓
Human Intelligence Input
   ↓
Learning Event
```

The prototype must make this process visible through a professional support-operations dashboard.

The dashboard should allow a viewer to understand:

1. What customers are asking.
2. Which AI agent is handling each issue.
3. What the AI currently thinks is happening.
4. What actions the AI is taking.
5. What tools/APIs it is using.
6. Whether the action succeeded.
7. What the customer received as a response.
8. When and how a human influenced the AI.
9. How that human interaction becomes a learning signal.

---

# 2. PRIMARY PRODUCT IDEA

Traditional support bots primarily provide answers.

Resolvyn is designed around **resolving issues**.

For example:

```text
Customer:
"I was charged twice for my order."

Traditional chatbot:
"Please contact our billing department."

Resolvyn:

Understand issue
      ↓
Check customer
      ↓
Check order
      ↓
Check payment records
      ↓
Detect duplicate transaction
      ↓
Check refund policy
      ↓
Determine permitted action
      ↓
Execute refund
      ↓
Verify refund
      ↓
Respond to customer
```

The prototype must demonstrate this difference.

---

# 3. PROTOTYPE SCOPE

## 3.1 Implement

The prototype must contain:

* Live ticket dashboard
* Ticket list
* Ticket detail view
* Customer conversation
* AI agent status
* Specialist agents
* Ticket routing
* Intent detection
* Sentiment detection
* Confidence
* Customer context
* Knowledge retrieval
* Tool/API activity
* Action verification
* AI response
* Human intelligence controls
* Human correction
* Human approval
* Human guidance
* Human override
* Learning event creation
* Prediction-error-style event
* Activity/event stream
* Basic analytics
* Agent monitoring
* Search/filtering
* Realistic simulated ticket activity

---

## 3.2 Do NOT attempt in the first prototype

Do not spend time building:

* Actual enterprise CRM integrations
* Real payment systems
* Real banking APIs
* Real shipping APIs
* Production authentication
* Production-scale vector databases
* Actual reinforcement-learning model training
* Actual fruit-fly/connectome simulation
* Neuromorphic hardware
* Complex voice support
* Email ingestion
* Social-media ingestion
* Full enterprise deployment infrastructure

These are architectural directions, not requirements for the prototype.

---

# 4. CORE DEMONSTRATION

The most important demonstration should be a customer issue moving through the entire system.

Example:

### Ticket #PH-1042

Customer:

> "I was charged twice for the same order and I need one of the payments refunded."

The system should display:

```text
NEW
 ↓
ANALYZING
 ↓
ROUTING
 ↓
BILLING AGENT
 ↓
CHECKING CUSTOMER
 ↓
CHECKING PAYMENT
 ↓
CHECKING POLICY
 ↓
ACTION PROPOSED
 ↓
HUMAN APPROVAL
 ↓
REFUND EXECUTED
 ↓
VERIFICATION
 ↓
RESOLVED
```

The user should be able to follow this process visually.

---

# 5. DESIGN PHILOSOPHY

The dashboard must feel like a **serious enterprise operations product**.

It should NOT look like:

* A generic AI chatbot
* A futuristic neon AI website
* A gaming interface
* A cyberpunk dashboard
* A cryptocurrency dashboard
* A developer console
* A colorful SaaS template
* A landing page

The visual language should communicate:

**Precision.
Control.
Trust.
Clarity.
Intelligence.
Operational seriousness.**

---

# 6. COLOR SYSTEM

## 6.1 Primary Palette

The entire application must be based on:

* Black
* Near-black
* Dark grey
* Mid grey
* Light grey
* White

Suggested palette:

```text
#050505  — Primary background
#0A0A0A  — Secondary background
#111111  — Cards
#171717  — Elevated cards
#222222  — Borders
#2E2E2E  — Dividers
#666666  — Secondary text
#999999  — Muted text
#D4D4D4  — Primary secondary text
#F5F5F5  — Primary text
#FFFFFF  — Maximum emphasis
```

Do not introduce gradients.

Do not use colored backgrounds.

Do not use excessive shadows.

---

# 7. ACCENT COLORS

Solid colors are permitted **only when they communicate meaning**.

Use them sparingly.

### Green

Meaning:

* Success
* Verified
* Resolved
* Active/healthy

Suggested:

```text
#22C55E
```

### Amber

Meaning:

* Warning
* Waiting
* Approval required
* Medium confidence

Suggested:

```text
#F59E0B
```

### Red

Meaning:

* Error
* Critical
* Failed action
* High-risk intervention

Suggested:

```text
#EF4444
```

### Blue

Meaning:

* Informational
* Human guidance
* Neutral system action

Suggested:

```text
#3B82F6
```

Do NOT use all four colors simultaneously everywhere.

A typical ticket should remain almost entirely monochrome.

Color should appear only on:

* Status indicators
* Important actions
* Risk
* Errors
* Success states
* Human interventions

---

# 8. TYPOGRAPHY

Use a clean modern sans-serif.

Preferred:

**Inter**

Fallback:

```text
system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
```

Typography must be restrained.

Do not use oversized headings inside the dashboard.

Recommended hierarchy:

```text
Page title       20–24px
Section title    13–15px
Body             13–14px
Secondary text   12–13px
Metadata         11–12px
```

Use font weight rather than color wherever possible to create hierarchy.

---

# 9. LAYOUT

The main application should use a three-part structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ TOP BAR                                                      │
├──────────────┬───────────────────────────────┬───────────────┤
│              │                               │               │
│ SIDEBAR      │       MAIN WORKSPACE         │ CONTEXT       │
│              │                               │ PANEL         │
│ Navigation   │       Tickets / Detail       │ AI state      │
│              │                               │ Customer       │
│              │                               │ Human input   │
└──────────────┴───────────────────────────────┴───────────────┘
```

---

# 10. SIDEBAR

Width:

Approximately 220–240px.

Background:

Near-black.

Navigation:

```text
Resolvyn
────────────────

Overview

Tickets
Agents
Customers
Knowledge
Activity

────────────────

Learning

Human Intelligence
Learning Signals

────────────────

System

Analytics
Settings
```

Do not overcrowd the sidebar.

Use simple monochrome icons.

Icons must be subtle.

No oversized logos.

---

# 11. TOP BAR

Top bar should contain:

Left:

```text
Overview
```

or current page name.

Right:

```text
● SYSTEM OPERATIONAL

Search

Notifications

User
```

The system status should be subtle.

Example:

```text
● Operational
```

with a small green dot.

---

# 12. OVERVIEW DASHBOARD

The Overview page is the primary landing page after login.

It should immediately communicate the state of the support operation.

---

## 12.1 KPI ROW

Four to five compact cards:

```text
ACTIVE TICKETS
24

AI RESOLUTIONS
18

HUMAN INTERVENTIONS
3

AVG RESOLUTION
42s

AI CONFIDENCE
94%
```

Do not make these giant dashboard cards.

They should feel like operational metrics, not marketing statistics.

---

# 13. LIVE TICKET STREAM

This is the most important section.

Title:

**Live tickets**

Subtext:

```text
Real-time support activity
```

Each row should contain:

```text
Ticket ID
Customer
Issue
Intent
Agent
Status
Confidence
Updated
```

Example:

```text
PH-1042
Aarav Sharma
Duplicate payment
Billing
● Processing
96%
12 sec
```

Another:

```text
PH-1043
Maya Patel
Unable to access account
Account
● Resolved
98%
1 min
```

Another:

```text
PH-1044
Rohan Mehta
Refund not received
Billing
● Awaiting approval
81%
8 sec
```

---

# 14. LIVE ACTIVITY

The dashboard should feel alive.

Use simulated ticket events.

For example:

```text
19:42:08
PH-1047 entered queue

19:42:10
Intent classified as PAYMENT_FAILURE

19:42:11
Billing Agent activated

19:42:13
Payment API queried

19:42:14
Policy retrieved

19:42:15
Action verified

19:42:16
Customer response generated
```

Events should appear naturally.

Do NOT make the interface flash constantly.

Animation must be subtle.

---

# 15. TICKET DETAIL PAGE

When the user clicks a ticket, open the detailed support workspace.

Recommended structure:

```text
┌───────────────────────────────────────────────────────────────┐
│ ← Tickets     PH-1042                         ● PROCESSING    │
├──────────────────────────────┬────────────────────────────────┤
│                              │                                │
│ CUSTOMER CONVERSATION        │ AI OPERATIONS                  │
│                              │                                │
│                              │                                │
│                              │                                │
├──────────────────────────────┴────────────────────────────────┤
│ EVENT TIMELINE / ACTIVITY                                    │
└───────────────────────────────────────────────────────────────┘
```

---

# 16. CUSTOMER CONVERSATION

The conversation must feel like a real support conversation.

Example:

### Customer

> I was charged twice for the same order and only received one confirmation.

### Resolvyn

> I’m checking your payment and order records to verify whether the second charge is a duplicate.

Then the system performs actions.

After verification:

### Resolvyn

> I confirmed that two payment transactions were recorded for this order. One payment is eligible for a refund under the current billing policy.

Then:

> I’ve submitted the refund for the duplicate transaction.

The customer should never receive a statement that contradicts the system's verified state.

---

# 17. CUSTOMER CONTEXT PANEL

Show:

```text
CUSTOMER

Aarav Sharma

Customer ID
CUS-20481

Plan
Premium

Account age
2 years

Previous tickets
7

Recent sentiment
Frustrated

Open issues
1
```

This demonstrates context-aware support.

The underlying architecture document explicitly identifies customer history, profile, previous interactions, sentiment, and memory as important contextual signals.

---

# 18. AI OPERATIONS PANEL

This panel shows what the AI is doing.

Sections:

### Understanding

```text
Intent
Duplicate Payment

Confidence
96%

Sentiment
Frustrated

Urgency
Medium
```

---

### Agent

```text
Assigned Agent

Billing Agent

Reason
Payment-related issue
```

---

### Knowledge

```text
Sources Used

Billing Refund Policy
Payment Processing Guide
Previous Similar Ticket
```

Each source should be clickable.

---

### Tools

```text
get_customer()
get_order()
get_payment_transactions()
check_refund_policy()
issue_refund()
verify_refund()
```

Tool states:

```text
✓ Completed
✓ Completed
✓ Completed
✓ Completed
→ Waiting
○ Not started
```

---

# 19. AGENT SYSTEM

Create a dedicated **Agents** page.

Agents:

```text
Billing Agent
Account Agent
Technical Agent
Order Agent
Logistics Agent
```

Do not create 20 fake agents.

Five is enough for the prototype.

---

# 20. AGENT CARDS

Each agent card should contain:

```text
Billing Agent

● ACTIVE

Current tickets
3

Resolved today
28

Avg confidence
94%

Current task
PH-1042

Current operation
Verifying duplicate payment
```

The active agent should have a very subtle status indicator.

---

# 21. AGENT STATES

Every agent should support:

```text
IDLE
ANALYZING
RETRIEVING
ACTING
VERIFYING
WAITING
COMPLETED
ERROR
```

These states should be reflected consistently throughout the application.

Do not invent different terminology on different pages.

---

# 22. HUMAN INTELLIGENCE

This is a central part of Resolvyn.

Do NOT present humans merely as an escalation destination.

Instead, humans should be embedded into the AI workflow.

The prototype should support five visible actions:

```text
GUIDE
APPROVE
CORRECT
OVERRIDE
TEACH
```

---

# 23. HUMAN GUIDANCE

Suppose the AI is uncertain.

Display:

```text
AI requires guidance

Confidence: 71%

Possible interpretations:

Refund request
Payment dispute
Duplicate charge

[ GUIDE AI ]
```

Clicking Guide opens a small input:

```text
Tell Resolvyn what it should consider:

[ __________________________ ]

[ Apply guidance ]
```

The event should appear in the activity timeline.

---

# 24. HUMAN APPROVAL

For actions that require approval:

```text
ACTION REQUIRES APPROVAL

Refund amount
₹2,499

Reason
Duplicate payment detected

Policy
Eligible

Confidence
94%

[ APPROVE ]     [ REJECT ]
```

Approval must change the ticket state.

---

# 25. HUMAN CORRECTION

Example:

AI proposes:

```text
Refund ₹2,499
```

Human clicks:

```text
CORRECT
```

Then:

```text
Correct action:

Refund only after duplicate transaction confirmation.

[ Submit correction ]
```

After submission:

```text
Human correction recorded
↓
Decision mismatch detected
↓
Learning signal created
```

---

# 26. HUMAN OVERRIDE

Example:

```text
AI ACTION

Cancel order

Confidence: 87%

[ OVERRIDE ]
```

After override:

```text
Human override recorded

Reason:
Customer requested shipment continuation.
```

The system should log:

* Human action
* Previous AI decision
* New decision
* Reason
* Timestamp
* Ticket ID

---

# 27. HUMAN TEACHING

A human should be able to add operational knowledge.

Example:

```text
TEACH Resolvyn

Topic:
Refunds for duplicate transactions

Knowledge:
If two successful transactions exist for the same
order within 10 minutes, verify duplicate charge
before issuing refund.

[ SAVE KNOWLEDGE ]
```

This becomes a simulated organizational-memory event.

---

# 28. LEARNING SIGNALS

Create a dedicated page:

**Learning Signals**

Show events such as:

```text
Human correction
Wrong agent routing
Failed tool action
Policy conflict
Customer rejection
Successful resolution
```

Example:

```text
LS-0281

Human correction

Ticket
PH-1042

AI decision
Refund immediately

Human correction
Verify duplicate transaction first

Source
Human operator

Status
Recorded
```

---

# 29. PREDICTION ERROR

For the prototype, prediction error should be represented as a **learning-event concept**, not claimed to be a fully trained reinforcement-learning model.

Display:

```text
PREDICTION ERROR

Expected outcome:
Automatic refund

Observed outcome:
Human correction required

Difference detected

→ Learning signal generated
```

The exact mathematical RL implementation is not required in this prototype.

Do not claim that the system has trained itself through reinforcement learning.

---

# 30. KNOWLEDGE PAGE

Create a simple Knowledge page.

Categories:

```text
Policies
Product Information
Troubleshooting
Billing
Orders
Previous Resolutions
```

Example:

```text
Billing Refund Policy

Last updated
Today

Used by
Billing Agent

Referenced in
18 tickets
```

---

# 31. SEARCH

Global search should allow searching:

* Ticket ID
* Customer
* Agent
* Intent
* Knowledge document

Search should be fast and visually minimal.

---

# 32. FILTERS

Tickets should support:

```text
All
Active
Waiting
Resolved
Needs Human
High Risk
```

Additional filters:

```text
Agent
Intent
Sentiment
Priority
Confidence
```

---

# 33. TICKET STATUS MODEL

Use exactly these states:

```text
NEW
ANALYZING
ROUTING
ACTIVE
WAITING_FOR_HUMAN
VERIFYING
RESOLVED
FAILED
```

Do not create unnecessary states.

---

# 34. PRIORITY MODEL

Use:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Color should only appear for HIGH and CRITICAL.

---

# 35. CONFIDENCE DISPLAY

Confidence should be represented simply.

Example:

```text
96%  High
```

Avoid giant progress bars.

Use a small horizontal indicator or text.

Suggested semantic ranges:

```text
90–100%   High
75–89%    Medium
<75%      Low
```

These thresholds are prototype UI thresholds, not claims about model calibration.

---

# 36. SENTIMENT

Use:

```text
Positive
Neutral
Frustrated
Angry
```

Do not use emojis.

Do not make sentiment visually dominant.

---

# 37. ACTIVITY TIMELINE

Every ticket must have a timeline.

Example:

```text
19:42:08   Ticket created

19:42:09   Intent detected
           Duplicate payment

19:42:10   Billing Agent assigned

19:42:11   Customer history retrieved

19:42:12   Refund policy retrieved

19:42:14   Payment API queried

19:42:15   Duplicate transaction confirmed

19:42:16   Human approval requested

19:42:20   Refund approved

19:42:22   Refund executed

19:42:23   Action verified

19:42:25   Ticket resolved
```

This timeline is one of the most important parts of the demo.

---

# 38. SIMULATED BACKEND

For the hackathon prototype, enterprise services can be mocked.

Create mock services:

```text
Customer API
Order API
Payment API
Refund API
Shipping API
Account API
```

Each should return deterministic realistic data.

Example:

```text
GET /customer/CUS-20481
GET /order/ORD-83921
GET /payments/ORD-83921
POST /refund
GET /refund/RFD-28192
```

These are prototype APIs.

Do not connect to real financial systems.

---

# 39. DATABASE

Use a simple local database.

Preferred:

**SQLite**

Tables:

```text
customers
tickets
messages
agents
agent_events
tool_calls
knowledge_documents
human_actions
learning_signals
```

Keep the schema simple.

---

# 40. TICKET DATA MODEL

Example:

```text
ticket_id
customer_id
subject
status
intent
sentiment
urgency
priority
assigned_agent
confidence
created_at
updated_at
resolution_time
```

---

# 41. MESSAGE DATA MODEL

```text
message_id
ticket_id
sender
content
timestamp
```

Sender:

```text
CUSTOMER
Resolvyn
HUMAN
```

---

# 42. AGENT EVENT MODEL

```text
event_id
ticket_id
agent
event_type
description
timestamp
status
```

Event types:

```text
INTENT_DETECTED
AGENT_ASSIGNED
MEMORY_RETRIEVED
KNOWLEDGE_RETRIEVED
TOOL_CALLED
ACTION_PROPOSED
ACTION_APPROVED
ACTION_EXECUTED
ACTION_VERIFIED
RESPONSE_GENERATED
```

---

# 43. HUMAN EVENT MODEL

```text
human_event_id
ticket_id
event_type
previous_ai_action
human_action
reason
timestamp
```

Types:

```text
GUIDANCE
APPROVAL
CORRECTION
OVERRIDE
TEACHING
```

---

# 44. LEARNING SIGNAL MODEL

```text
signal_id
ticket_id
source_event
signal_type
expected_action
observed_action
description
timestamp
```

---

# 45. REAL-TIME BEHAVIOUR

The dashboard should update without requiring a full page refresh.

Use a simple real-time mechanism.

Preferred:

**WebSocket**

If WebSockets introduce unnecessary complexity, use short polling.

The visual result matters more than infrastructure sophistication.

---

# 46. DEMO MODE

The application must include a **Demo Mode**.

This is extremely important.

Create a button:

```text
▶ RUN DEMO
```

When clicked, the system should execute a predefined support scenario.

Example:

```text
0s    Create ticket
2s    Detect intent
4s    Route to Billing Agent
6s    Retrieve customer
8s    Retrieve payment
10s   Retrieve policy
12s   Detect duplicate
14s   Request human approval
17s   Human approves
19s   Execute refund
21s   Verify
23s   Resolve
```

The user must be able to watch the complete lifecycle.

There should also be:

```text
RESET DEMO
```

---

# 47. DEMO TICKET

Use one carefully designed hero scenario.

## Customer

Aarav Sharma

## Issue

Duplicate payment.

## Ticket

PH-1042

## Order

ORD-83921

## Payment

Two successful transactions.

## Agent

Billing Agent.

## Resolution

Second transaction refunded after human approval.

This should be the primary demonstration.

---

# 48. SECONDARY DEMO TICKETS

Include realistic background tickets:

### PH-1043

Account locked.

Agent:

Account Agent.

Status:

Resolved.

---

### PH-1044

Refund not received.

Agent:

Billing Agent.

Status:

Active.

---

### PH-1045

Shipment delayed.

Agent:

Logistics Agent.

Status:

Analyzing.

---

### PH-1046

Product not functioning.

Agent:

Technical Agent.

Status:

Waiting for customer.

---

# 49. RESPONSIVE DESIGN

Desktop is the primary target.

Target resolution:

```text
1440 × 900
```

The dashboard must look excellent at:

```text
1280 × 720
1440 × 900
1920 × 1080
```

Mobile is not the priority for this prototype.

However, the layout must not break on smaller widths.

---

# 50. SPACING SYSTEM

Use a consistent spacing system.

Prefer multiples of:

```text
4px
8px
12px
16px
24px
32px
```

Avoid random margins.

---

# 51. BORDER SYSTEM

Use thin borders rather than heavy shadows.

Default:

```text
1px solid #222
```

Cards should generally have:

* subtle border
* near-black background
* small radius

Suggested radius:

```text
6px
8px
```

Avoid excessive rounded cards.

Do not make every element pill-shaped.

---

# 52. BUTTON DESIGN

Primary button:

White background.

Black text.

Example:

```text
[ APPROVE ]
```

Secondary:

Dark background.

Light text.

Example:

```text
[ GUIDE ]
```

Danger:

Red text/border only when necessary.

Example:

```text
[ OVERRIDE ]
```

Buttons should be compact and professional.

---

# 53. ANIMATION

Animation must be subtle.

Allowed:

* Fade
* Slide
* Status transitions
* Number updates
* Activity insertion
* Agent state change
* Loading indicator

Do NOT use:

* Particle backgrounds
* Glowing borders
* Excessive gradients
* Floating blobs
* Rotating 3D objects
* Constant motion
* Neon effects

This is an enterprise operations interface.

---

# 54. EMPTY STATES

Every page must have a meaningful empty state.

Example:

```text
No active tickets

All current conversations have been resolved.
```

Do not leave blank white/black space.

---

# 55. ERROR STATES

Errors should be understandable.

Example:

```text
Payment verification failed

The payment service did not return a valid response.

[ Retry ]
```

Do not expose raw stack traces to the dashboard.

---

# 56. LOADING STATES

Use skeletons or subtle activity indicators.

Avoid full-page loading screens unless absolutely necessary.

---

# 57. ACCESSIBILITY

Use:

* sufficient contrast
* keyboard-accessible buttons
* visible focus states
* semantic HTML
* readable text
* descriptive labels

Do not rely solely on color to communicate status.

For example:

Bad:

```text
green = resolved
```

Better:

```text
✓ RESOLVED
```

---

# 58. TECHNICAL ARCHITECTURE

Recommended:

```text
Frontend
React / Next.js
        ↓
API Layer
FastAPI
        ↓
Orchestration
Support Decision Engine
        ↓
Specialist Agents
        ↓
Mock Enterprise APIs
        ↓
SQLite
```

Frontend should be responsible for presentation and user interaction.

Backend should own:

* ticket state
* agents
* mock tools
* events
* human actions
* learning signals
* demo orchestration

Do not put business logic entirely inside React components.

---

# 59. AI ARCHITECTURE

The prototype can use an LLM where useful.

Logical pipeline:

```text
Message
 ↓
Intent
 ↓
Sentiment
 ↓
Urgency
 ↓
Agent Routing
 ↓
Context Retrieval
 ↓
Knowledge Retrieval
 ↓
Decision
 ↓
Tool Call
 ↓
Verification
 ↓
Response
```

The architecture should remain modular so individual components can later be replaced.

---

# 60. RAG

The prototype should include a small knowledge base.

Documents:

```text
Refund Policy
Payment Processing Guide
Account Recovery Policy
Shipping Policy
Technical Troubleshooting Guide
```

When an agent handles a ticket, show which documents were retrieved.

Example:

```text
Knowledge retrieved

Refund Policy
Similarity: 0.93

Payment Processing Guide
Similarity: 0.89
```

Do not expose raw embeddings.

---

# 61. MEMORY

Demonstrate simple contextual memory.

For example:

```text
Previous interaction

PH-0911
Customer reported payment verification issue.

Resolution:
Payment gateway timeout.
```

When the current ticket arrives, show:

```text
Relevant customer history found
1 previous interaction
```

This demonstrates context-aware support.

---

# 62. DECISION ENGINE

The decision engine should conceptually perform:

```text
UNDERSTAND
     ↓
CONTEXT
     ↓
KNOWLEDGE
     ↓
PLAN
     ↓
CHECK RISK
     ↓
SELECT ACTION
     ↓
EXECUTE
     ↓
VERIFY
```

This should be reflected in the UI.

---

# 63. VERIFICATION

This is critical.

The AI must not claim an action succeeded merely because it requested it.

Example:

Bad:

```text
Refund requested
→
"Your refund has been processed."
```

Correct:

```text
Refund requested
↓
Refund API response
↓
Refund ID generated
↓
Refund status checked
↓
SUCCESS
↓
Customer notified
```

The UI should explicitly show:

**VERIFIED**

---

# 64. HUMAN EMBEDDING MODEL

Human involvement should appear as part of the operational workflow.

Use:

```text
AI
↕
HUMAN INTELLIGENCE
↕
AI
```

Humans can:

```text
Observe
Guide
Approve
Correct
Override
Teach
```

The prototype should show these interactions in real ticket workflows.

---

# 65. OBSERVABILITY

Every important action should produce an event.

The system should make it possible to trace:

```text
Ticket
 ↓
Intent
 ↓
Agent
 ↓
Knowledge
 ↓
Tool
 ↓
Decision
 ↓
Human Action
 ↓
Outcome
```

This is one of the core reasons for the Activity Timeline.

---

# 66. ANALYTICS PAGE

Keep it simple.

Show:

```text
Tickets today
124

Resolved
91

Active
24

Human interventions
9

Average resolution
38s
```

Then:

### Ticket intents

```text
Billing          34
Account          27
Orders           22
Technical        18
Logistics        15
Other             8
```

### Agent activity

```text
Billing Agent       32
Account Agent       27
Order Agent         22
Technical Agent     18
Logistics Agent     15
```

Use monochrome charts with very limited accent color.

---

# 67. DESIGN RULE FOR CHARTS

Charts should be minimal.

Use:

* thin lines
* grey bars
* white highlights
* one accent color only where meaningful

Avoid:

* rainbow charts
* gradients
* 3D charts
* unnecessary legends
* decorative graphs

---

# 68. NAVIGATION BEHAVIOUR

### Overview

Shows operation at a glance.

### Tickets

Shows all tickets.

### Agents

Shows AI agents.

### Customers

Shows customer context.

### Knowledge

Shows knowledge base.

### Activity

Shows system event stream.

### Human Intelligence

Shows human interventions.

### Learning Signals

Shows learning events.

### Analytics

Shows aggregate metrics.

---

# 69. CUSTOMER PAGE

Customer profile should show:

```text
Customer

Aarav Sharma

Plan
Premium

Joined
2024

Tickets
7

Resolved
6

Open
1

Recent sentiment
Frustrated
```

Then:

### History

```text
PH-1042
Duplicate payment
Active

PH-0911
Payment verification
Resolved

PH-0783
Order issue
Resolved
```

Clicking a ticket opens its detail page.

---

# 70. DATA REALISM

Do not populate the interface with meaningless random strings.

All mock data should be internally consistent.

For example:

If a ticket says:

```text
Customer: Aarav Sharma
Order: ORD-83921
```

Then the mock API should return the same customer/order.

If a refund is created:

```text
RFD-28192
```

that refund ID should remain consistent throughout the ticket.

---

# 71. STATE CONSISTENCY

The frontend must reflect backend state.

Example:

If human clicks:

```text
APPROVE
```

then:

* Approval event is created.
* Ticket state changes.
* Agent continues.
* Refund executes.
* Activity timeline updates.
* Resolution state updates.
* Learning event is created if applicable.

Do not merely animate a fake button click without changing application state.

---

# 72. NO PLACEHOLDER UI

Do not leave:

```text
Lorem ipsum
Coming soon
Placeholder
TODO
Example text
```

in the visible final prototype.

Everything visible should look intentional.

---

# 73. NO GENERIC AI COPY

Avoid marketing phrases such as:

> "Revolutionizing customer support with cutting-edge AI."

Instead use operational language:

> "Payment verification in progress."

> "Billing Agent active."

> "Human approval required."

> "Refund verified."

The interface should feel like a real internal operations product.

---

# 74. BRANDING

Primary wordmark:

```text
Resolvyn
```

Use uppercase.

Typography should be simple.

No complex logo is required for the first version.

A subtle geometric mark can be created if useful, but it must remain monochrome.

---

# 75. LANDING / LOGIN

Keep login extremely minimal if authentication is required.

Example:

```text
Resolvyn

Autonomous Support Operations

Email
[________________]

Password
[________________]

[ SIGN IN ]
```

Do not spend significant development time on authentication.

For the hackathon, a demo login is acceptable.

---

# 76. DEMO CREDIBILITY

The application must make it obvious that this is not just a chatbot.

The strongest visible evidence should be:

```text
Customer conversation
+
AI reasoning state
+
Specialist agent
+
Knowledge
+
Tool calls
+
Verified action
+
Human intervention
+
Learning event
```

All should be visible in one coherent workflow.

---

# 77. PRIMARY USER JOURNEY

The judge should be able to do this:

```text
Open Resolvyn

↓

See live support tickets

↓

Click PH-1042

↓

Read customer issue

↓

Watch Billing Agent activate

↓

See customer context

↓

See knowledge retrieved

↓

See payment API called

↓

See duplicate transaction detected

↓

See refund action proposed

↓

Approve action

↓

See refund executed

↓

See verification

↓

See customer response

↓

See ticket become RESOLVED

↓

Open Learning Signals

↓

See human approval recorded
```

This should take less than two minutes.

---

# 78. SECONDARY USER JOURNEY

Judge clicks a low-confidence ticket.

They see:

```text
Confidence: 68%

Possible intents:
Account issue
Payment issue
Subscription issue

Human guidance recommended.
```

They click:

**GUIDE**

Enter guidance.

The AI continues.

This demonstrates human intelligence without requiring a full escalation.

---

# 79. THIRD USER JOURNEY

Judge opens Human Intelligence.

They see:

```text
9 interventions today

6 approvals
2 corrections
1 override
```

Clicking a correction reveals:

```text
AI decision
Human decision
Reason
Outcome
Learning signal
```

This demonstrates the learning loop.

---

# 80. FOURTH USER JOURNEY

Judge opens Agents.

They see:

```text
Billing Agent
● ACTIVE

Account Agent
● IDLE

Technical Agent
● ACTIVE

Order Agent
● ACTIVE

Logistics Agent
● IDLE
```

Clicking Billing Agent reveals current tasks.

---

# 81. PERFORMANCE

The application should feel fast.

Avoid unnecessary loading.

Use optimistic UI where safe.

Do not run expensive LLM calls for every UI element.

For simulated background tickets, deterministic data is acceptable.

---

# 82. CODE ORGANIZATION

Keep code modular.

Suggested structure:

```text
/frontend
    /components
    /pages
    /features
        /tickets
        /agents
        /customers
        /knowledge
        /human-intelligence
        /learning
        /analytics
    /lib

/backend
    /api
    /models
    /services
        /ticket_service
        /agent_service
        /knowledge_service
        /tool_service
        /human_service
        /learning_service
    /data
    /demo
```

Adapt this to the chosen framework if necessary, but preserve the conceptual separation.

---

# 83. COMPONENT DESIGN

Reusable components should include:

```text
StatusBadge
ConfidenceIndicator
AgentBadge
TicketRow
TicketTimeline
ActivityEvent
CustomerCard
AgentCard
MetricCard
ToolCall
KnowledgeSource
HumanActionPanel
ApprovalDialog
CorrectionDialog
LearningSignalCard
```

Do not duplicate the same UI implementation across pages.

---

# 84. SECURITY FOR PROTOTYPE

Real production security is outside scope.

However, demonstrate the concept through:

* role-aware UI
* action confirmation
* audit logs
* human action logging
* tool permissions

For example:

```text
Refund
Risk: Medium
Approval required
```

---

# 85. AUDIT LOG

Human actions must be auditable.

Example:

```text
19:42:20

Human:
Operator 01

Action:
APPROVED REFUND

Ticket:
PH-1042

Amount:
₹2,499

Reason:
Duplicate transaction verified
```

---

# 86. IMPORTANT IMPLEMENTATION PRINCIPLE

Do not make the prototype appear more capable than it is.

If an action is simulated, the UI can say:

```text
Simulation
```

or the architecture/documentation can state that the enterprise APIs are mocked.

Do not represent a mock payment system as a real financial integration.

---

# 87. WHAT SHOULD BE REAL VS SIMULATED

## Real application behaviour

* Navigation
* Ticket state
* Ticket filtering
* Ticket details
* Customer data
* Agent state
* Activity timeline
* Human actions
* Approvals
* Corrections
* Event creation
* Learning signal creation
* Demo state transitions

## Simulated services

* Payment API
* Refund API
* Order API
* Shipping API
* Customer API

## Optional AI integration

If an LLM API is available, use it for:

* response generation
* intent classification
* summarization
* knowledge reasoning

If not available, use deterministic mock outputs.

The application must still work without an external LLM.

---

# 88. FAILURE HANDLING

The prototype should demonstrate at least one failure scenario.

Example:

```text
Payment API unavailable

Status:
FAILED

Agent response:
Retrying verification...
```

Then:

```text
Retry successful

Payment verified
```

This demonstrates that Resolvyn is an operational system rather than a static chatbot.

---

# 89. LOW-CONFIDENCE SCENARIO

Create one ticket where confidence is deliberately low.

Example:

```text
Customer:
"I've been charged but something is wrong with my order."

Intent confidence:
68%
```

The system should show:

```text
LOW CONFIDENCE

Additional context required.

[ GUIDE AI ]
```

This gives the human intelligence layer a meaningful role.

---

# 90. LEARNING SCENARIO

Create one ticket where the AI initially makes an incorrect decision.

The human corrects it.

Then the system creates:

```text
Learning Signal

Type:
Human Correction

AI decision:
Refund transaction

Human correction:
Verify duplicate transaction first

Cause:
Missing transaction context

Status:
Recorded
```

This is enough for the prototype.

Do not claim that a new machine-learning model was retrained instantly.

---

# 91. FINAL ARCHITECTURE REPRESENTED BY THE UI

The prototype should visually correspond to:

```text
                    Resolvyn

Customer
   │
   ▼
Perception
   │
   ├── Intent
   ├── Sentiment
   └── Urgency
   │
   ▼
Decision / Judgment
   │
   ├── Memory
   ├── Knowledge
   └── Policy
   │
   ▼
Specialist Agent
   │
   ▼
Tools / APIs
   │
   ▼
Verification
   │
   ▼
Customer Response
   │
   ▼
Outcome
   │
   ▼
Human Intelligence
   │
   ├── Guide
   ├── Approve
   ├── Correct
   ├── Override
   └── Teach
   │
   ▼
Learning Signal
```

---

# 92. VISUAL HIERARCHY

Every screen must answer three questions immediately:

### 1. What is happening?

Ticket / agent / status.

### 2. Why is it happening?

Intent / context / knowledge / confidence.

### 3. What happens next?

Action / approval / verification / resolution.

Do not make the user hunt for these.

---

# 93. DESIGN REFERENCE

The visual direction should feel closer to:

* Enterprise operations software
* High-end developer infrastructure dashboards
* Financial operations interfaces
* Modern observability platforms
* Professional support command centers

It should NOT feel like:

* ChatGPT clone
* Generic AI startup website
* Dribbble concept with no functionality
* Cyberpunk AI interface

---

# 94. FINAL VISUAL RULES

### DO

* Black/white/grey foundation
* Solid accent colors
* Thin borders
* Dense but readable information
* Small status indicators
* Strong typography
* Consistent spacing
* Minimal animation
* Clear hierarchy
* Professional tables
* Realistic data
* Operational language

### DO NOT

* Gradients
* Neon
* Glassmorphism
* Excessive blur
* Huge cards
* Giant headings
* Excessive rounded corners
* Random colors
* Decorative AI graphics
* Particle backgrounds
* 3D illustrations
* Fake futuristic effects
* Excessive animations
* Emoji-heavy UI

---

# 95. DEFINITION OF DONE

The prototype is considered complete when a judge can:

1. Open Resolvyn.
2. See live tickets.
3. Open a ticket.
4. Read the customer conversation.
5. See the detected intent.
6. See sentiment and urgency.
7. See the assigned specialist agent.
8. See customer context.
9. See knowledge sources.
10. See tool/API calls.
11. See the agent execute an action.
12. See the action verified.
13. See the customer receive a response.
14. Approve an action as a human.
15. Correct an AI decision.
16. Guide the AI.
17. Override an action.
18. Add knowledge.
19. See the human event recorded.
20. See a learning signal generated.
21. See agent activity.
22. See system activity.
23. Run the complete demo scenario from beginning to resolution.
24. Reset the demo and run it again.

---

# 96. BUILD PRIORITY

Antigravity must prioritize in this order.

## P0 — MUST HAVE

```text
Dashboard
Tickets
Ticket detail
Customer conversation
Agent routing
Agent states
Tool activity
Verification
Human approval
Human correction
Activity timeline
Demo mode
```

## P1 — SHOULD HAVE

```text
Knowledge
Customer history
Human guidance
Human override
Learning signals
Analytics
Agent monitoring
```

## P2 — NICE TO HAVE

```text
Real LLM integration
Advanced RAG
Real-time WebSocket events
Advanced charts
Persistent memory
More agent types
```

If time becomes limited, finish P0 completely before touching P2.

---

# 97. BUILD STRATEGY

Do not attempt to generate the entire application blindly in one pass.

Build in milestones.

### Milestone 1

Application shell.

* Sidebar
* Topbar
* Routing
* Global design system
* Typography
* Colors
* Responsive layout

### Milestone 2

Dashboard.

* KPIs
* Ticket table
* Activity stream
* Agent summary

### Milestone 3

Ticket workspace.

* Conversation
* Customer context
* AI operations
* Timeline

### Milestone 4

Agents.

* Agent page
* Agent states
* Ticket assignment

### Milestone 5

Tools.

* Mock APIs
* Tool execution
* Verification

### Milestone 6

Human Intelligence.

* Guide
* Approve
* Correct
* Override
* Teach

### Milestone 7

Learning.

* Human events
* Learning signals
* Prediction-error-style event

### Milestone 8

Demo mode.

* Predefined scenario
* Automatic state transitions
* Reset

### Milestone 9

Polish.

* Animations
* Empty states
* Loading states
* Error states
* Typography
* Spacing
* Visual consistency

---

# 98. IMPORTANT INSTRUCTION TO ANTIGRAVITY

Do not make assumptions about product behaviour that are not defined in this document.

When implementation details are unspecified, choose the simplest implementation that:

1. Preserves the described user experience.
2. Keeps the architecture modular.
3. Does not introduce unnecessary dependencies.
4. Does not change the visual language.
5. Does not invent additional product features.

Do not add features merely because they are common in AI dashboards.

Do not redesign the product into a different concept.

The objective is **Resolvyn**, not a generic AI customer-support dashboard.

---

# 99. FINAL PRODUCT PRINCIPLE

Resolvyn should communicate one central idea:

> **AI handles the work. Humans remain embedded in the intelligence loop.**

The customer should experience a single support interaction.

Behind that interaction, Resolvyn should make visible:

```text
UNDERSTAND
→
REMEMBER
→
REASON
→
ACT
→
VERIFY
→
LEARN
```

And humans should be able to enter that loop through:

```text
GUIDE
APPROVE
CORRECT
OVERRIDE
TEACH
```

The prototype does not need to prove every research component.

It needs to prove that this operational model can exist as a working system.

---

# 100. FINAL SUCCESS CRITERION

When a judge looks at the application, the immediate impression should be:

> "This is not just a chatbot. This is an AI support operations system."

When they interact with a ticket, they should be able to see the complete chain:

```text
Customer problem
      ↓
AI understanding
      ↓
Specialist agent
      ↓
Context + knowledge
      ↓
Tool action
      ↓
Verification
      ↓
Customer outcome
      ↓
Human intelligence
      ↓
Learning signal
```

That complete loop is the prototype.
