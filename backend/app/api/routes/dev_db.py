"""TEMPORARY — raw, read-only database browser for local frontend development
without the model running (no Epsilon/LLM dependency at all — this only reads
SQLite rows).

Safe to delete later: this file, plus the one `include_router` line for it in
`app/api/router.py`, plus `frontend/app/ops/dev-db/page.tsx` on the frontend.
Nothing else in the app imports or depends on this module.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from sqlmodel import SQLModel

from app.database import engine

router = APIRouter()


def _known_tables() -> list[str]:
    import app.models  # noqa: F401 — registers every table on SQLModel.metadata

    return sorted(SQLModel.metadata.tables.keys())


@router.get("/tables")
def list_tables():
    tables = _known_tables()
    with engine.connect() as conn:
        rows = [{"name": t, "row_count": conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar_one()} for t in tables]
    return {"tables": rows}


@router.get("/tables/{table_name}")
def get_table_rows(table_name: str, limit: int = 100, offset: int = 0):
    if table_name not in _known_tables():  # whitelist against registered tables — table names can't be bind params
        raise HTTPException(404, f"unknown table {table_name!r}")
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    with engine.connect() as conn:
        total = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"')).scalar_one()
        result = conn.execute(text(f'SELECT * FROM "{table_name}" LIMIT :limit OFFSET :offset'), {"limit": limit, "offset": offset})
        columns = list(result.keys())
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
    return {"table": table_name, "columns": columns, "rows": rows, "total": total, "limit": limit, "offset": offset}
