"""Knowledge-graph half of the memory (docs/architecture.md §2.6).

Nodes: concept, department, document, ticket, customer, rule, bug.
Edges: HAS_CONCEPT, BELONGS_TO, CONTAINS, HANDLED_BY, FOR_CUSTOMER, RESOLVED_BY,
       HAS_INTENT, SIMILAR_TO, RELATED_TO, TAUGHT_BY.

The graph is built by us — from every ingested SOP and from every solved ticket
(episodic memory) — so a new call can be answered from "what worked last time".
Stored in SQLite; traversals are plain Python because the graph is small.
"""

from collections import Counter, defaultdict

from sqlmodel import Session, select

from app.database import engine
from app.memory.text import slug, stem, tokens
from app.models import KgEdge, KgNode

GENERIC = {
    "issue", "problem", "customer", "team", "please", "ensure", "should", "must", "using", "within",
    "days", "day", "hours", "hour", "minute", "minutes", "always", "never", "case", "cases", "policy",
    "step", "steps", "agent", "support", "company", "process", "requires", "required", "detail", "details",
    "eligible", "available", "applicable", "according", "following", "provide", "confirm", "check",
}


def node_id(type_: str, label: str) -> str:
    return f"{type_}:{slug(label)}"


def upsert_node(s: Session, type_: str, label: str, store: str = "common") -> str:
    nid = node_id(type_, label)
    n = s.get(KgNode, nid)
    if n:
        n.weight += 1
    else:
        n = KgNode(node_id=nid, type=type_, label=label, weight=1, store=store)
    s.add(n)
    return nid


def upsert_edge(s: Session, src: str, dst: str, relation: str) -> None:
    if src == dst:
        return
    e = s.exec(
        select(KgEdge).where(KgEdge.src == src, KgEdge.dst == dst, KgEdge.relation == relation)
    ).first()
    if e:
        e.weight += 1
    else:
        e = KgEdge(src=src, dst=dst, relation=relation, weight=1)
    s.add(e)


def extract_concepts(text: str, k: int = 6) -> list[str]:
    """Most salient content words of a chunk (frequency, domain-generic words removed)."""
    counts = Counter(t for t in tokens(text) if len(t) >= 4 and t not in GENERIC and not t.isdigit())
    return [t for t, _ in counts.most_common(k)]


def index_chunk(s: Session, *, doc_label: str | None, department: str, text: str, store: str = "common",
                doc_type: str = "document", ref: str | None = None) -> list[str]:
    """Add a text chunk's concepts and links to the graph. Returns concept node ids."""
    dep = upsert_node(s, "department", department, store)
    concept_ids = [upsert_node(s, "concept", c, store) for c in extract_concepts(text)]
    doc_id = upsert_node(s, doc_type, doc_label, store) if doc_label else None
    for cid in concept_ids:
        upsert_edge(s, cid, dep, "BELONGS_TO")
        if doc_id:
            upsert_edge(s, doc_id, cid, "CONTAINS")
    for i, a in enumerate(concept_ids):
        for b in concept_ids[i + 1: i + 3]:
            upsert_edge(s, a, b, "RELATED_TO")
    if doc_id:
        upsert_edge(s, doc_id, dep, "BELONGS_TO")
    return concept_ids


def related_tickets(query: str, *, exclude: str | None = None, limit: int = 3) -> list[dict]:
    """Past tickets sharing concepts with the query (graph traversal, 2 hops)."""
    q_stems = {stem(t) for t in tokens(query, expand=True) if len(t) >= 3}
    if not q_stems:
        return []
    with Session(engine) as s:
        concept_ids = [f"concept:{slug(t)}" for t in q_stems]
        edges = s.exec(select(KgEdge).where(KgEdge.dst.in_(concept_ids), KgEdge.relation == "HAS_CONCEPT")).all()
        # Hop 2: concepts related to the query concepts also vote (with a discount).
        rel = s.exec(select(KgEdge).where(KgEdge.src.in_(concept_ids), KgEdge.relation == "RELATED_TO")).all()
        rel_ids = list({e.dst for e in rel} - set(concept_ids))
        edges2 = (
            s.exec(select(KgEdge).where(KgEdge.dst.in_(rel_ids), KgEdge.relation == "HAS_CONCEPT")).all()
            if rel_ids else []
        )
        degree = Counter()
        for e in s.exec(select(KgEdge).where(KgEdge.relation == "HAS_CONCEPT")).all():
            degree[e.dst] += 1
    votes: dict[str, float] = defaultdict(float)
    shared: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        votes[e.src] += 1.0 / (1 + 0.15 * degree[e.dst])
        shared[e.src].add(e.dst.split(":", 1)[1])
    for e in edges2:
        votes[e.src] += 0.25 / (1 + 0.15 * degree[e.dst])
    out = []
    for nid, v in sorted(votes.items(), key=lambda kv: kv[1], reverse=True):
        tid = nid.split(":", 1)[1].upper()
        if exclude and tid == exclude.upper():
            continue
        out.append({"ticket_id": tid, "score": v, "shared": sorted(shared[nid])})
        if len(out) >= limit:
            break
    return out


def snapshot(max_nodes: int = 140) -> dict:
    """Nodes/edges for the Memory page. Highest-weight nodes first."""
    with Session(engine) as s:
        structural = s.exec(select(KgNode).where(KgNode.type != "concept").order_by(KgNode.weight.desc()).limit(max_nodes)).all()
        room = max(0, max_nodes - len(structural))
        concepts = s.exec(select(KgNode).where(KgNode.type == "concept").order_by(KgNode.weight.desc()).limit(room)).all()
        nodes = structural + concepts
        ids = {n.node_id for n in nodes}
        edges = [
            e for e in s.exec(select(KgEdge)).all() if e.src in ids and e.dst in ids
        ]
        total_nodes = len(s.exec(select(KgNode)).all())
        total_edges = len(s.exec(select(KgEdge)).all())
    return {
        "nodes": [{"id": n.node_id, "type": n.type, "label": n.label, "weight": n.weight, "store": n.store}
                  for n in nodes],
        "edges": [{"src": e.src, "dst": e.dst, "relation": e.relation, "weight": e.weight} for e in edges],
        "stats": {"nodes": total_nodes, "edges": total_edges},
    }
