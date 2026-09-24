"""Bridge to the orchestration graph in /agents (repo root — a separate,
standalone package on purpose; see agents/README.md). This is the ONLY file
in `backend/` that knows `/agents` exists: it puts the repo root on
sys.path (mirroring the `backend/`-on-sys.path convention `agents/` itself
relies on to reach `app.*`, see agents/_bootstrap.py) and re-exports its
router. Nothing else under `backend/app` changed to build the orchestration
layer — see docs/claude.md, "Orchestration layer (/agents)".
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.api import router  # noqa: E402
