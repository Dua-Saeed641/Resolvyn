"""Test environment: throwaway SQLite DB, no local model (the deterministic path must work on its own)."""

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="resolvyn-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["ENGINE_ENABLED"] = "false"
os.environ["CLOUD_LLM_API_KEY"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
