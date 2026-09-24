# Resolvyn backend

FastAPI + SQLModel (SQLite) + WebSockets. Local models through the epsilon engine in `../engine`.

```
app/
  api/            REST routes + ws.py (/ws/call for the caller, /ws/ops for the team)
  services/       conversation.py (the live pipeline), ticket_service.py (single owner of ticket state),
                  sessions.py, realtime.py (pub/sub), demo_service.py, analytics_service.py, seed_service.py
  perception/     language + entity extraction from noisy speech
  judgment/       Jev: intent, sentiment, urgency, side-talk detection, grounding check
  memory/         vector index, knowledge graph, ingestion, Solvable Rulebook
  decision_engine/  instant-resolve | tools | first-time bug | escalate
  agents/         Technical, Billing, Account, Order, Other + persona prompt
  tools/          simulated enterprise APIs + tool_service
  llm/            epsilon engine, optional cloud LLM, deterministic fallback
  voice/          edge-tts, spoken-text normalisation, fillers
  context_engine/ live case notes, context doc, deep (27B) analysis
  human_intelligence/  Guide / Approve / Correct / Override / Teach
data/sops/        seed SOPs, ingested through the same pipeline as a manager upload
scripts/          engine_smoke.py, e2e_call.py (play a caller over the WebSocket), memory_probe.py
tests/            pytest: units + real WebSocket flows on the deterministic path
```

Run: `.venv\Scripts\python -m uvicorn app.main:app --port 8000` (or `..\start.ps1`). Try a call without the UI:

```
.venv\Scripts\python scripts\e2e_call.py --customer CUS-20481 --approve "I was charged twice for the same order" "the order ID is ORD-83921" "yes please refund it"
```
