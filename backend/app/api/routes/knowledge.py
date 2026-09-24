"""Knowledge, memory and the Solvable Rulebook (docs/architecture.md §2.6).

This is where "how do I get my SOPs in?" is answered: upload documents or paste
text; they are chunked, routed to the right department, and indexed into both
halves of the memory (vector + knowledge graph).
"""

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import engine
from app.memory import ingest, kg, rulebook
from app.memory.memory_engine import memory
from app.models import MemoryChunk
from app.vocab import DEPARTMENTS

router = APIRouter()

KINDS = {"sop", "business_logic", "product_db"}


class TextIn(BaseModel):
    title: str
    text: str
    kind: str | None = None
    department: str | None = None


def _check(kind: str | None, department: str | None) -> None:
    if kind and kind not in KINDS:
        raise HTTPException(400, f"kind must be one of {sorted(KINDS)}")
    if department and department not in DEPARTMENTS:
        raise HTTPException(400, f"department must be one of {list(DEPARTMENTS)}")


@router.get("")
def documents():
    return ingest.list_documents()


@router.get("/stats")
def stats():
    return memory.stats()


@router.post("/ingest")
async def ingest_files(
    files: list[UploadFile] = File(...),
    kind: str | None = Form(None),
    department: str | None = Form(None),
):
    _check(kind or None, department or None)
    out, errors = [], []
    for f in files:
        try:
            out.append(ingest.ingest_file(f.filename or "document", await f.read(), kind=kind or None,
                                          department=department or None))
        except Exception as e:  # noqa: BLE001
            errors.append({"file": f.filename, "error": str(e)})
    if not out and errors:
        raise HTTPException(400, errors[0]["error"])
    return {"ingested": out, "errors": errors}


@router.post("/ingest-text")
def ingest_pasted(body: TextIn):
    _check(body.kind, body.department)
    try:
        return ingest.ingest_text(body.title.strip() or "Untitled", body.text, kind=body.kind, department=body.department)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.delete("/{document_id}")
def delete_document(document_id: int):
    if not ingest.delete_document(document_id):
        raise HTTPException(404, "document not found")
    return {"deleted": document_id}


@router.get("/{document_id}/chunks")
def chunks(document_id: int):
    with Session(engine) as s:
        rows = s.exec(select(MemoryChunk).where(MemoryChunk.document_id == document_id)).all()
    return [{"chunk_id": c.chunk_id, "title": c.title, "department": c.department, "text": c.text} for c in rows]


@router.get("/rulebook/by-department")
def rulebook_by_department():
    """The rulebook divided per department agent, with each agent's SOP coverage."""
    with Session(engine) as s:
        chunks_ = s.exec(select(MemoryChunk).where(MemoryChunk.store == "common")).all()
    per: dict[str, dict] = {d: {"rules": [], "sop_chunks": 0, "documents": set()} for d in DEPARTMENTS}
    rules = rulebook.by_department()
    for c in chunks_:
        if c.kind in ("sop", "business_logic", "product_db"):
            per[c.department]["sop_chunks"] += 1
            if c.source:
                per[c.department]["documents"].add(c.source)
    return {
        d: {"rules": rules.get(d, []), "sop_chunks": per[d]["sop_chunks"], "documents": sorted(per[d]["documents"])}
        for d in DEPARTMENTS
    }


@router.delete("/rulebook/{rule_id}")
def delete_rule(rule_id: int):
    if not rulebook.deactivate(rule_id):
        raise HTTPException(404, "rule not found")
    return {"deleted": rule_id}


@router.get("/graph/snapshot")
def graph(limit: int = 140):
    return kg.snapshot(min(limit, 400))


@router.get("/search/test")
def search(q: str, department: str | None = None):
    """Retrieval tester: what would the AI find for this caller sentence?"""
    r = memory.retrieve(q, department)
    return {"best_common": round(r.best_common, 2), "best_bug": round(r.best_bug, 2),
            "hits": [{**h.public(), "text": h.text[:280]} for h in r.top_hits(6)]}
