"""Context & Memory Engine — docs/architecture.md §1 layer 3, §2.6.

Two memories, each = vector half + knowledge-graph half:
  common          business logic, SOPs, product DB, solved past queries, taught rules
  first_time_bug  issues with no precedent, plus the human suggestion once given

`retrieve()` is what "Query → Rulebook" in memory-rulebook-detail.png does: the
Jev-written query goes to both memories; the decision engine reads the scores.
"""

from dataclasses import dataclass, field

from sqlmodel import Session, select

from app.database import engine
from app.memory import kg
from app.memory.vector_store import Hit, VectorIndex
from app.models import FirstTimeBug, KnowledgeDocument, MemoryChunk, RulebookEntry
from app.utils import iso, utcnow

RULE_BOOST = 1.15  # human-taught knowledge outranks a generic SOP


@dataclass
class Retrieval:
    query: str
    department: str | None
    common: list[Hit] = field(default_factory=list)
    graph: list[Hit] = field(default_factory=list)
    bugs: list[Hit] = field(default_factory=list)
    best_common: float = 0.0
    best_bug: float = 0.0

    @property
    def best(self) -> float:
        return max(self.best_common, self.best_bug)

    def top_hits(self, k: int = 4) -> list[Hit]:
        merged: dict[int, Hit] = {}
        for h in self.common + self.graph + self.bugs:
            if h.chunk_id not in merged or h.score > merged[h.chunk_id].score:
                merged[h.chunk_id] = h
        return sorted(merged.values(), key=lambda h: (h.rank or h.score), reverse=True)[:k]

    def sources(self) -> list[dict]:
        return [h.public() for h in self.top_hits(5)]


class MemoryEngine:
    def __init__(self) -> None:
        self.common = VectorIndex("common")
        self.bugs = VectorIndex("first_time_bug")

    # ── indexing ─────────────────────────────────────────────────────────────
    def reload(self) -> None:
        with Session(engine) as s:
            rows = s.exec(select(MemoryChunk)).all()
        by_store: dict[str, list[dict]] = {"common": [], "first_time_bug": []}
        for r in rows:
            by_store.setdefault(r.store, []).append(r.model_dump())
        self.common.rebuild(by_store["common"])
        self.bugs.rebuild(by_store["first_time_bug"])

    # ── retrieval ────────────────────────────────────────────────────────────
    def retrieve(self, query: str, department: str | None = None, *, exclude_ticket: str | None = None) -> Retrieval:
        """Vector search in both memories + knowledge-graph expansion."""
        r = Retrieval(query=query, department=department)
        dept = department if department and department != "Other" else None

        hits = self.common.search(query, k=6, department=dept)
        for h in hits:
            if h.kind == "rule":
                h.score = min(1.0, h.score * RULE_BOOST)
            if exclude_ticket and h.ref_ticket_id == exclude_ticket:
                h.score *= 0.3
        hits.sort(key=lambda h: (h.rank or h.score) if h.score >= 0.3 else h.score, reverse=True)
        r.common = hits[:4]

        # Graph hop: past solved tickets sharing concepts with the query.
        related = kg.related_tickets(query, exclude=exclude_ticket, limit=3)
        if related:
            wanted = {x["ticket_id"]: x for x in related}
            with Session(engine) as s:
                chunks = s.exec(select(MemoryChunk).where(
                    MemoryChunk.kind == "past_query", MemoryChunk.ref_ticket_id.in_(list(wanted)))).all()
            top_vote = max(x["score"] for x in related) or 1.0
            for c in chunks:
                vote = wanted[c.ref_ticket_id]["score"]
                # Graph evidence is corroborating, not decisive: cap its contribution.
                score = min(0.55, 0.25 + 0.3 * (vote / top_vote)) * (min(1.0, vote) if vote < 1 else 1.0)
                r.graph.append(Hit(
                    chunk_id=c.chunk_id, title=c.title, text=c.text, department=c.department, kind=c.kind,
                    store="common", score=score, source=c.source, ref_ticket_id=c.ref_ticket_id, via="graph",
                    matched=wanted[c.ref_ticket_id]["shared"],
                ))
        r.bugs = self.bugs.search(query, k=3, department=dept)

        # Only *vector* evidence decides whether the rulebook knows the answer. Graph
        # neighbours are corroboration: a small bonus, never enough to cross a threshold alone.
        best_vec = max((h.score for h in r.common), default=0.0)
        r.best_common = min(1.0, best_vec + (0.04 if r.graph and best_vec > 0.3 else 0.0))
        r.best_bug = max((h.score for h in r.bugs), default=0.0)
        return r

    # ── writing memory ───────────────────────────────────────────────────────
    def remember_ticket(self, ticket: dict, resolution: str) -> None:
        """Episodic memory: a solved query becomes retrievable + a node in the graph."""
        tid = ticket["ticket_id"]
        dept = ticket.get("assigned_agent") or "Other"
        problem = ticket.get("subject") or ticket.get("body") or ""
        text = f"Problem: {problem}\nResolution: {resolution}"
        with Session(engine) as s:
            exists = s.exec(select(MemoryChunk).where(MemoryChunk.kind == "past_query",
                                                      MemoryChunk.ref_ticket_id == tid)).first()
            if exists:
                exists.text = text
                s.add(exists)
            else:
                s.add(MemoryChunk(store="common", kind="past_query", department=dept,
                                  title=f"Solved query {tid} — {ticket.get('intent') or 'query'}",
                                  text=text, ref_ticket_id=tid, source=f"ticket {tid}"))
            t_node = kg.upsert_node(s, "ticket", tid)
            kg.upsert_edge(s, t_node, kg.upsert_node(s, "department", dept), "HANDLED_BY")
            if ticket.get("intent"):
                kg.upsert_edge(s, t_node, kg.upsert_node(s, "concept", ticket["intent"]), "HAS_INTENT")
            if ticket.get("customer_id"):
                kg.upsert_edge(s, t_node, kg.upsert_node(s, "customer", ticket["customer_id"]), "FOR_CUSTOMER")
            concepts = kg.index_chunk(s, doc_label=None, department=dept, text=text)
            for c in concepts:
                kg.upsert_edge(s, t_node, c, "HAS_CONCEPT")
            for k in ticket.get("knowledge") or []:
                if k.get("kind") in ("sop", "business_logic", "product_db"):
                    kg.upsert_edge(s, t_node, kg.upsert_node(s, "document", k["title"].split(" — ")[0]), "RESOLVED_BY")
            # ticket <-> ticket similarity via shared concepts
            others = kg.related_tickets(problem, exclude=tid, limit=2)
            for o in others:
                if len(o["shared"]) >= 2:
                    kg.upsert_edge(s, t_node, kg.upsert_node(s, "ticket", o["ticket_id"]), "SIMILAR_TO")
            s.commit()
        self.reload()

    def record_first_time_bug(self, ticket_id: str, title: str, detail: str, department: str) -> FirstTimeBug:
        with Session(engine, expire_on_commit=False) as s:
            bug = FirstTimeBug(ticket_id=ticket_id, title=title, detail=detail, department=department)
            s.add(bug)
            s.add(MemoryChunk(store="first_time_bug", kind="bug", department=department,
                              title=f"First-time bug {ticket_id} — {title}", text=detail,
                              ref_ticket_id=ticket_id, source=f"ticket {ticket_id}"))
            b = kg.upsert_node(s, "bug", ticket_id, store="first_time_bug")
            kg.upsert_edge(s, b, kg.upsert_node(s, "department", department, store="first_time_bug"), "BELONGS_TO")
            for c in kg.index_chunk(s, doc_label=None, department=department, text=title + " " + detail,
                                    store="first_time_bug"):
                kg.upsert_edge(s, b, c, "HAS_CONCEPT")
            s.commit()
        self.reload()
        return bug

    def attach_bug_suggestion(self, ticket_id: str, suggestion: str) -> None:
        """The bug memory keeps the human's answer next to the problem it solved."""
        with Session(engine) as s:
            c = s.exec(select(MemoryChunk).where(MemoryChunk.store == "first_time_bug",
                                                 MemoryChunk.ref_ticket_id == ticket_id)).first()
            if c:
                c.text = c.text + f"\nHuman suggestion: {suggestion}"
                s.add(c)
                s.commit()
        self.reload()

    # ── introspection ────────────────────────────────────────────────────────
    def stats(self) -> dict:
        with Session(engine) as s:
            chunks = s.exec(select(MemoryChunk)).all()
            docs = s.exec(select(KnowledgeDocument)).all()
            rules = s.exec(select(RulebookEntry).where(RulebookEntry.active == True)).all()  # noqa: E712
        g = kg.snapshot(1)["stats"]
        by_kind: dict[str, int] = {}
        for c in chunks:
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
        by_dept: dict[str, int] = {}
        for c in chunks:
            if c.store == "common":
                by_dept[c.department] = by_dept.get(c.department, 0) + 1
        return {
            "documents": len(docs), "chunks": len(chunks), "rules": len(rules), "by_kind": by_kind,
            "by_department": by_dept, "graph": g, "updated": iso(utcnow()),
            "common_chunks": len(self.common), "bug_chunks": len(self.bugs),
        }


memory = MemoryEngine()

