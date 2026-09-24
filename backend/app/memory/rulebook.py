"""Solvable Rulebook — docs/architecture.md §2.5-2.6.

The ruleset the Decision Engine consults before acting, divided per department
agent. Extended in exactly two ways: a human Teach/Correct action, or a
first-time-bug suggestion. Route handlers never write here directly — they go
through human_intelligence/human_service.py.
"""

from sqlmodel import Session, select

from app.database import engine
from app.memory import kg
from app.models import MemoryChunk, RulebookEntry
from app.utils import iso
from app.vocab import DEPARTMENTS

SOURCES = ("human_teach", "first_time_bug_suggestion", "human_correction", "seed")


def add_rule(topic: str, knowledge: str, department: str, source: str,
             ticket_id: str | None = None) -> RulebookEntry:
    from app.memory.memory_engine import memory

    if source not in SOURCES:
        raise ValueError(f"unknown rule source {source!r}")
    if department not in DEPARTMENTS:
        department = "Other"
    with Session(engine, expire_on_commit=False) as s:
        rule = RulebookEntry(topic=topic.strip(), knowledge=knowledge.strip(), department=department,
                             source=source, ticket_id=ticket_id)
        s.add(rule)
        s.add(MemoryChunk(
            store="common", kind="rule", department=department, title=f"Rule — {topic.strip()}",
            text=knowledge.strip(), ref_ticket_id=ticket_id, source=source,
        ))
        rid = kg.upsert_node(s, "rule", topic.strip())
        did = kg.upsert_node(s, "department", department)
        kg.upsert_edge(s, rid, did, "BELONGS_TO")
        for cid in kg.index_chunk(s, doc_label=None, department=department, text=topic + " " + knowledge):
            kg.upsert_edge(s, rid, cid, "CONTAINS")
        if ticket_id:
            tid = kg.upsert_node(s, "ticket", ticket_id)
            kg.upsert_edge(s, tid, rid, "TAUGHT_BY")
        s.commit()
    memory.reload()
    return rule


def by_department() -> dict[str, list[dict]]:
    """The rulebook, divided per department agent."""
    with Session(engine) as s:
        rows = s.exec(select(RulebookEntry).where(RulebookEntry.active == True)  # noqa: E712
                      .order_by(RulebookEntry.rule_id.desc())).all()
    out: dict[str, list[dict]] = {d: [] for d in DEPARTMENTS}
    for r in rows:
        out.setdefault(r.department, []).append({
            "rule_id": r.rule_id, "topic": r.topic, "knowledge": r.knowledge, "source": r.source,
            "ticket_id": r.ticket_id, "created_at": iso(r.created_at),
        })
    return out


def deactivate(rule_id: int) -> bool:
    from app.memory.memory_engine import memory

    with Session(engine) as s:
        r = s.get(RulebookEntry, rule_id)
        if not r:
            return False
        r.active = False
        s.add(r)
        for c in s.exec(select(MemoryChunk).where(MemoryChunk.kind == "rule", MemoryChunk.title == f"Rule — {r.topic}")).all():
            s.delete(c)
        s.commit()
    memory.reload()
    return True
