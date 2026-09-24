"""Test environment: throwaway SQLite DB + throwaway checkpoint DB, no
model (spec §33: "no external API keys" — mirrors backend/tests/conftest.py's
isolation exactly). No pytest-asyncio: tests are plain `def test_...()`
functions that drive their own `asyncio.run(...)` (see `run_async` below) —
one fewer test-only dependency to add on top of backend/requirements.txt.
"""

import asyncio
import itertools
import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="resolvyn-agents-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["ENGINE_ENABLED"] = "false"
os.environ["CLOUD_LLM_API_KEY"] = ""

REPO_ROOT = Path(__file__).resolve().parents[2]
for p in (REPO_ROOT / "backend", REPO_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import pytest  # noqa: E402

from app.database import init_db  # noqa: E402
from app.services.seed_service import seed_all  # noqa: E402
from app.tools import mock_apis  # noqa: E402

from agents.service import ResolvynOrchestrator  # noqa: E402

_checkpoint_counter = itertools.count()


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    init_db()
    seed_all()


@pytest.fixture(autouse=True)
def reset_mock_apis():
    """Every test that touches ORD-83921 expects a fresh, un-refunded
    duplicate charge — without this, test order matters (an earlier test's
    `issue_refund` makes `check_refund_policy` correctly say "already
    refunded" for a later test, changing its decision path entirely)."""
    mock_apis.reset_state()
    yield
    mock_apis.reset_state()


def run_async(coro):
    """`asyncio.run` with a clearer name at call sites — every test uses this
    instead of pytest-asyncio (see module docstring)."""
    return asyncio.run(coro)


def new_orchestrator() -> ResolvynOrchestrator:
    """A fresh checkpoint DB per call so tests never see each other's paused
    graphs. Use as `async with new_orchestrator() as orch:`."""
    path = Path(_tmp, f"checkpoints-{next(_checkpoint_counter)}.db")
    return ResolvynOrchestrator(db_path=path)
