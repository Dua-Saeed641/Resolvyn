"""Test environment: throwaway SQLite DB, no local model (the deterministic path must work on its own)."""

import os
import sys
import tempfile
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="resolvyn-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_tmp, 'test.db').as_posix()}"
os.environ["ENGINE_ENABLED"] = "false"
os.environ["CLOUD_LLM_API_KEY"] = ""
# Tests must never send or read real email, whatever backend/.env contains.
for _k in ("EMAIL_ADDRESS", "EMAIL_PASSWORD", "EMAIL_SMTP_HOST", "EMAIL_IMAP_HOST", "EMAIL_REDIRECT_TO", "CUSTOMER_EMAILS", "EMAIL_ALIASES"):
    os.environ[_k] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c
