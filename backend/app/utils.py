"""Small shared helpers (time + JSON)."""

import json
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    """Timezone-aware UTC now (SQLModel stores/returns aware UTC datetimes)."""
    return datetime.now(timezone.utc)


def as_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return as_utc(dt).astimezone(timezone.utc).replace(microsecond=0, tzinfo=None).isoformat() + "Z"


def jdump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def jload(text: str | None, default: Any = None) -> Any:
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default
