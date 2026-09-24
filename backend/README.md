# Resolvyn backend

FastAPI service implementing the prototype slice of the architecture described in
[`../docs/architecture.md`](../docs/architecture.md). See [`../docs/claude.md`](../docs/claude.md)
for the engineering rules this codebase must follow.

## Run locally

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # or `source .venv/bin/activate` on macOS/Linux
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

API docs will be at `http://localhost:8000/docs`.

## Layout

```
app/
  api/routes/        HTTP endpoints, one file per sidebar section
  models/             SQLModel tables (project.md §39-44)
  perception/         Perception Layer (architecture.md §1 layer 2)
  judgment/            Judgment & Intelligence Core / Jev (layer 3)
  decision_engine/    Analyze -> Plan -> Evaluate -> Choose Action (layer 4)
  agents/              Orchestrator + 5 specialist agents (layer 5)
  knowledge/          Knowledge & Tools retrieval (layer 6)
  memory/              Context & Memory Engine, Solvable Rulebook (layer 3, §2.6)
  human_intelligence/ Guide / Approve / Correct / Override / Teach
  learning/           Learning Signals (layer 9)
  tools/               Simulated enterprise APIs (project.md §38)
  services/           Cross-cutting orchestration (ticket_service, demo_service)
data/                 Deterministic seed/mock data
tests/
```
