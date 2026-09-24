"""Makes `backend/app/*` importable from this package.

`agents/` is a standalone top-level folder (kept isolated from `backend/`
and `frontend/` on purpose — see agents/README.md), but it reuses the real
Resolvyn services (ticket_service, tool_service, decision_engine, the
specialist agents, memory, rulebook, learning_service) rather than
duplicating them. Those live under `backend/app`, which is only on
sys.path when a process is started with `backend/` as its working
directory (how uvicorn normally runs it — see backend/app/tools/mock_apis.py's
`from data.seed_data import ...` for the same convention).

Importing this module once (every other module in this package does)
adds `backend/` to sys.path if it is not there yet, so `agents/` works
both standalone (its own pytest run) and when imported by the backend
process (backend/app/api/routes/orchestration.py).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"

for path in (BACKEND_DIR, REPO_ROOT):
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)
